"""
問題データアップロード機能
"""
import os
import json
import zipfile
from datetime import datetime
from flask import Blueprint, request, render_template, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename
from app.core.auth import login_required, admin_required

upload_bp = Blueprint('upload', __name__)

ALLOWED_EXTENSIONS = {'json', 'zip'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename, extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in extensions

@upload_bp.route('/admin/upload')
@admin_required
def upload_page():
    """データアップロードページ"""
    # 統計情報を取得
    db_manager = current_app.db_manager
    
    # 問題数統計
    total_questions = db_manager.execute_query("SELECT COUNT(*) as count FROM questions")[0]['count']
    
    # ジャンル数統計  
    genres_result = db_manager.execute_query("SELECT COUNT(DISTINCT genre) as count FROM questions WHERE genre IS NOT NULL AND genre != ''")
    genres_count = genres_result[0]['count'] if genres_result else 0
    
    # 画像ファイル数統計
    images_dir = os.path.join(current_app.root_path, 'static', 'images', 'questions')
    images_count = 0
    if os.path.exists(images_dir):
        images_count = len([f for f in os.listdir(images_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))])
    
    stats = {
        'total_questions': total_questions,
        'genres_count': genres_count,
        'images_count': images_count
    }
    
    return render_template('admin/upload.html', stats=stats)

@upload_bp.route('/admin/upload/questions', methods=['POST'])
@admin_required
def upload_questions():
    """JSON問題データのアップロード処理"""
    if 'file' not in request.files:
        flash('ファイルが選択されていません。', 'error')
        return redirect(url_for('upload.upload_page'))
    
    file = request.files['file']
    if file.filename == '':
        flash('ファイルが選択されていません。', 'error')
        return redirect(url_for('upload.upload_page'))
    
    if not allowed_file(file.filename, ALLOWED_EXTENSIONS):
        flash('JSON または ZIP ファイルのみアップロード可能です。', 'error')
        return redirect(url_for('upload.upload_page'))
    
    try:
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        
        # 一時保存ディレクトリの作成
        upload_dir = os.path.join(current_app.root_path, 'uploads', 'temp')
        os.makedirs(upload_dir, exist_ok=True)
        
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)
        
        # ファイル形式に応じて処理
        if filename.lower().endswith('.zip'):
            result = _process_zip_file(filepath)
        else:
            result = _process_json_file(filepath)
        
        # 一時ファイルを削除
        os.remove(filepath)
        
        if result['success']:
            flash(f'問題データを正常にアップロードしました。登録件数: {result["count"]}件', 'success')
        else:
            flash(f'アップロードエラー: {result["error"]}', 'error')
            
    except Exception as e:
        flash(f'アップロード処理中にエラーが発生しました: {str(e)}', 'error')
    
    return redirect(url_for('upload.upload_page'))

@upload_bp.route('/admin/upload/images', methods=['POST'])
@admin_required
def upload_images():
    """画像ファイルのアップロード処理"""
    if 'files' not in request.files:
        flash('ファイルが選択されていません。', 'error')
        return redirect(url_for('upload.upload_page'))
    
    files = request.files.getlist('files')
    upload_count = 0
    error_count = 0
    
    # 画像保存ディレクトリの作成
    images_dir = os.path.join(current_app.root_path, 'static', 'images', 'questions')
    os.makedirs(images_dir, exist_ok=True)
    
    for file in files:
        if file.filename == '':
            continue
            
        if not allowed_file(file.filename, ALLOWED_IMAGE_EXTENSIONS):
            error_count += 1
            continue
        
        try:
            filename = secure_filename(file.filename)
            filepath = os.path.join(images_dir, filename)
            
            # 既存ファイルがある場合はスキップまたは上書き
            if os.path.exists(filepath):
                if not request.form.get('overwrite'):
                    flash(f'{filename} は既に存在します。上書きするにはチェックボックスを有効にしてください。', 'warning')
                    continue
            
            file.save(filepath)
            upload_count += 1
            
        except Exception as e:
            error_count += 1
            flash(f'{file.filename} のアップロードに失敗しました: {str(e)}', 'error')
    
    if upload_count > 0:
        flash(f'画像ファイルを {upload_count} 件アップロードしました。', 'success')
    if error_count > 0:
        flash(f'{error_count} 件のファイルでエラーが発生しました。', 'warning')
    
    return redirect(url_for('upload.upload_page'))

def _process_json_file(filepath):
    """JSONファイルの処理"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # データ形式の検証
        if not isinstance(data, list):
            return {'success': False, 'error': 'JSONファイルは配列形式である必要があります。'}
        
        count = 0
        db_manager = current_app.db_manager
        
        for item in data:
            if _validate_question_data(item):
                _save_question_to_db(item, db_manager)
                count += 1
        
        return {'success': True, 'count': count}
        
    except json.JSONDecodeError:
        return {'success': False, 'error': 'JSONファイルの形式が正しくありません。'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def _process_zip_file(filepath):
    """ZIPファイルの処理"""
    try:
        with zipfile.ZipFile(filepath, 'r') as zip_ref:
            # ZIPファイルの内容を確認
            file_list = zip_ref.namelist()
            json_files = [f for f in file_list if f.endswith('.json')]
            
            if not json_files:
                return {'success': False, 'error': 'ZIPファイル内にJSONファイルが見つかりません。'}
            
            # 一時展開ディレクトリ
            extract_dir = filepath + '_extract'
            zip_ref.extractall(extract_dir)
            
            total_count = 0
            db_manager = current_app.db_manager
            
            # 各JSONファイルを処理
            for json_file in json_files:
                json_path = os.path.join(extract_dir, json_file)
                result = _process_json_file(json_path)
                if result['success']:
                    total_count += result['count']
            
            # 一時ディレクトリを削除
            import shutil
            shutil.rmtree(extract_dir)
            
            return {'success': True, 'count': total_count}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

def _validate_question_data(data):
    """問題データの検証"""
    required_fields = ['question_id', 'question_text', 'choices', 'correct_answer']
    
    for field in required_fields:
        if field not in data:
            return False
    
    # 選択肢の検証
    if not isinstance(data['choices'], (list, dict)):
        return False
    
    return True

def _save_question_to_db(data, db_manager):
    """問題データをデータベースに保存"""
    # 選択肢をJSON文字列に変換（SQLiteの場合）
    choices_json = json.dumps(data['choices'], ensure_ascii=False)
    choice_images_json = json.dumps(data.get('choice_images', {}), ensure_ascii=False) if data.get('choice_images') else None
    
    # 重複チェック（question_idで）
    existing = db_manager.execute_query(
        "SELECT id FROM questions WHERE question_id = ?",
        (data['question_id'],)
    )
    
    if existing:
        # 更新
        db_manager.execute_query("""
            UPDATE questions 
            SET question_text = ?, choices = ?, correct_answer = ?, 
                explanation = ?, genre = ?, image_url = ?, choice_images = ?
            WHERE question_id = ?
        """, (
            data['question_text'],
            choices_json,
            data['correct_answer'],
            data.get('explanation', ''),
            data.get('genre', ''),
            data.get('image_url', ''),
            choice_images_json,
            data['question_id']
        ))
    else:
        # 新規登録
        db_manager.execute_query("""
            INSERT INTO questions 
            (question_id, question_text, choices, correct_answer, explanation, genre, image_url, choice_images)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['question_id'],
            data['question_text'],
            choices_json,
            data['correct_answer'],
            data.get('explanation', ''),
            data.get('genre', ''),
            data.get('image_url', ''),
            choice_images_json
        ))