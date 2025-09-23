"""
管理者ページのルーティング
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app
from auth import admin_required
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin')
@admin_required
def admin():
    """管理者ページ"""
    db_manager = current_app.db_manager
    question_manager = current_app.question_manager
    
    # 統計情報を取得
    total_questions = question_manager.get_total_questions()
    total_users = db_manager.execute_query('SELECT COUNT(*) as count FROM users')
    total_users = total_users[0]['count'] if total_users else 0
    
    # ジャンル別統計
    genres = question_manager.get_available_genres()
    genre_stats = question_manager.get_question_count_by_genre()
    
    # JSONファイル一覧を取得
    json_files = []
    json_folder = current_app.config.get('JSON_FOLDER', 'json_questions')
    if os.path.exists(json_folder):
        for filename in os.listdir(json_folder):
            if filename.endswith('.json'):
                filepath = os.path.join(json_folder, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        questions = json.load(f)
                    
                    file_stat = os.stat(filepath)
                    modified_time = datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                    
                    json_files.append({
                        'filename': filename,
                        'question_count': len(questions),
                        'size': file_stat.st_size,
                        'modified': modified_time
                    })
                except Exception as e:
                    print(f"Error reading {filename}: {e}")
    
    # データオブジェクトを作成
    data = {
        'question_count': total_questions,
        'user_count': total_users,
        'genre_count': len(genres),
        'json_files': json_files
    }
    
    return render_template('admin.html',
                         data=data,
                         total_questions=total_questions,
                         total_users=total_users,
                         genres=genres,
                         genre_stats=genre_stats)

@admin_bp.route('/admin/upload', methods=['POST'])
@admin_required
def upload_questions():
    """問題ファイルのアップロード"""
    if 'file' not in request.files:
        return jsonify({'error': 'ファイルが選択されていません'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'ファイルが選択されていません'}), 400
    
    if not file.filename.endswith('.json'):
        return jsonify({'error': 'JSONファイルのみアップロード可能です'}), 400
    
    try:
        # ファイルを保存
        filename = secure_filename(file.filename)
        json_folder = current_app.config.get('JSON_FOLDER', 'json_questions')
        filepath = os.path.join(json_folder, filename)
        file.save(filepath)
        
        # JSONファイルを読み込んで検証
        with open(filepath, 'r', encoding='utf-8') as f:
            questions = json.load(f)
        
        if not isinstance(questions, list):
            os.remove(filepath)
            return jsonify({'error': '無効なJSON形式です。配列形式である必要があります'}), 400
        
        # データベースに保存
        result = current_app.question_manager.save_questions(questions, filename)
        
        if result['saved_count'] == 0 and result.get('errors'):
            # エラーがある場合（重複など）
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({
                'success': False,
                'error': result['errors'][0] if result['errors'] else 'アップロードに失敗しました'
            }), 400
        
        return jsonify({
            'success': True,
            'message': f'{result["saved_count"]}問の問題をデータベースに保存しました',
            'saved_count': result['saved_count'],
            'total_count': result['total_count'],
            'errors': result.get('errors', [])
        })
        
    except json.JSONDecodeError:
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({'error': 'JSONファイルの解析に失敗しました'}), 400
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({'error': f'アップロード処理中にエラーが発生しました: {str(e)}'}), 500

@admin_bp.route('/admin/delete_all', methods=['POST'])
@admin_required
def delete_all_questions():
    """すべての問題を削除"""
    try:
        result = current_app.question_manager.delete_all_questions()
        if result['success']:
            return jsonify({
                'success': True,
                'message': result['message']
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', '削除に失敗しました')
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'エラーが発生しました: {str(e)}'
        }), 500
