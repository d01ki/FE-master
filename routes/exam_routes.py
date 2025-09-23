"""
模擬試験関連のルーティング
"""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash, current_app
from auth import login_required
from persistent_session import persistent_login_required
from helper_functions import parse_filename_info
import os
import json
import random
import re
import uuid

exam_bp = Blueprint('exam', __name__)

# メモリ内に試験データを保存（本番ではRedisなど使用）
exam_sessions = {}

def is_image_url(text):
    """テキストが画像URLかどうかを判定"""
    if not text or not isinstance(text, str):
        return False
    
    image_patterns = [
        r'/static/images/',
        r'\.png$',
        r'\.jpg$',
        r'\.jpeg$',
        r'\.gif$',
        r'\.svg$',
        r'\.webp$'
    ]
    
    text_lower = text.lower()
    return any(re.search(pattern, text_lower) for pattern in image_patterns)

def add_image_choice_flags(questions):
    """問題リストに has_image_choices フラグを追加"""
    for question in questions:
        question['has_image_choices'] = False
        if question.get('choices'):
            # 最初の選択肢をチェック
            first_choice = list(question['choices'].values())[0]
            question['has_image_choices'] = is_image_url(first_choice)
    return questions

@exam_bp.route('/mock_exam')
@persistent_login_required
def mock_exam():
    """模擬試験のトップページ"""
    json_folder = current_app.config.get('JSON_FOLDER', 'json_questions')
    
    if not os.path.exists(json_folder):
        return render_template('error.html',
                             message='試験ファイルが見つかりません',
                             detail='JSONフォルダが存在しません')
    
    files = []
    for filename in os.listdir(json_folder):
        if filename.endswith('.json'):
            print(f"Processing file: {filename}")
            file_info = parse_filename_info(filename)
            print(f"File info: {file_info}")
            if file_info:
                files.append(file_info)
            else:
                print(f"Warning: Could not parse filename: {filename}")
    
    print(f"Total files found: {len(files)}")
    files.sort(key=lambda x: x['sort_key'], reverse=True)
    
    return render_template('mock_exam.html', files=files)

@exam_bp.route('/mock_exam/<filename>')
@persistent_login_required
def mock_exam_start(filename):
    """指定年度の模擬試験開始"""
    try:
        file_info = parse_filename_info(filename)
        if not file_info:
            flash('無効な試験ファイルです', 'error')
            return redirect(url_for('exam.mock_exam'))
        
        json_folder = current_app.config.get('JSON_FOLDER', 'json_questions')
        json_filepath = os.path.join(json_folder, filename)
        if not os.path.exists(json_filepath):
            flash('試験ファイルが見つかりません', 'error')
            return redirect(url_for('exam.mock_exam'))
        
        with open(json_filepath, 'r', encoding='utf-8') as f:
            questions = json.load(f)
        
        # 20問に制限
        if len(questions) > 20:
            questions = random.sample(questions, 20)
        
        # 画像選択肢フラグを追加
        questions = add_image_choice_flags(questions)
        
        # 試験セッションIDを生成
        exam_session_id = str(uuid.uuid4())
        
        # メモリに保存（セッションではなく）
        exam_sessions[exam_session_id] = {
            'questions': questions,
            'user_id': session.get('user_id')
        }
        
        # セッションにはIDだけ保存
        session['exam_session_id'] = exam_session_id
        session.modified = True
        
        print(f"📚 Created exam session: {exam_session_id} with {len(questions)} questions")
        
        return render_template('mock_exam_practice.html', 
                             questions=questions, 
                             exam_info=file_info,
                             exam_session_id=exam_session_id)
        
    except Exception as e:
        print(f"❌ Mock exam start error: {e}")
        import traceback
        traceback.print_exc()
        flash(f'試験ファイルの読み込みに失敗しました: {str(e)}', 'error')
        return redirect(url_for('exam.mock_exam'))

@exam_bp.route('/mock_exam/submit', methods=['POST'])
@persistent_login_required
def submit_mock_exam():
    """模擬試験の採点"""
    try:
        data = request.get_json()
        answers = data.get('answers', {})
        exam_session_id = data.get('exam_session_id')
        
        print(f"📝 Received answers: {len(answers)} questions")
        print(f"📊 Exam session ID: {exam_session_id}")
        
        # メモリから問題を取得
        if not exam_session_id or exam_session_id not in exam_sessions:
            print(f"❌ No exam session found for ID: {exam_session_id}")
            return jsonify({'error': '試験セッションが見つかりません。ページを再読み込みして試験を再開してください。'}), 400
        
        exam_data = exam_sessions[exam_session_id]
        questions = exam_data['questions']
        
        print(f"📚 Questions from session: {len(questions)}")
        
        # 採点処理
        total_count = len(questions)
        correct_count = 0
        
        for i, question in enumerate(questions):
            question_index = str(i)
            user_answer = answers.get(question_index)
            correct_answer = question.get('correct_answer')
            
            if user_answer and user_answer == correct_answer:
                correct_count += 1
        
        score = round((correct_count / total_count) * 100, 1) if total_count > 0 else 0
        
        # 試験セッションを削除
        del exam_sessions[exam_session_id]
        session.pop('exam_session_id', None)
        
        print(f"✅ Result: {correct_count}/{total_count} = {score}%")
        
        return jsonify({
            'score': score,
            'correct_count': correct_count,
            'total_count': total_count
        })
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'採点処理中にエラー: {str(e)}'}), 500
