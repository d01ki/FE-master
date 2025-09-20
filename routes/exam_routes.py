"""
模擬試験関連のルーティング
"""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash, current_app
from auth import login_required
from helper_functions import parse_filename_info
import os
import json
import random
import re

exam_bp = Blueprint('exam', __name__)

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
@login_required
def mock_exam():
    """模擬試験のトップページ"""
    json_folder = current_app.config['JSON_FOLDER']
    
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
@login_required
def mock_exam_start(filename):
    """指定年度の模擬試験開始"""
    try:
        file_info = parse_filename_info(filename)
        if not file_info:
            flash('無効な試験ファイルです', 'error')
            return redirect(url_for('exam.mock_exam'))
        
        json_filepath = os.path.join(current_app.config['JSON_FOLDER'], filename)
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
        
        # セッションに問題と問題数を保存
        session['mock_exam_questions'] = questions
        session['mock_exam_total'] = len(questions)
        session.modified = True
        
        print(f"📚 Saved {len(questions)} questions to session")
        print(f"📊 Session size: {len(str(questions))} bytes")
        
        return render_template('mock_exam_practice.html', 
                             questions=questions, 
                             exam_info=file_info)
        
    except Exception as e:
        print(f"❌ Mock exam start error: {e}")
        import traceback
        traceback.print_exc()
        flash(f'試験ファイルの読み込みに失敗しました: {str(e)}', 'error')
        return redirect(url_for('exam.mock_exam'))

@exam_bp.route('/mock_exam/submit', methods=['POST'])
@login_required  
def submit_mock_exam():
    """模擬試験の採点"""
    try:
        data = request.get_json()
        answers = data.get('answers', {})
        total_from_client = data.get('total_questions', 0)
        
        print(f"📝 Received answers: {len(answers)} questions")
        print(f"📊 Total from client: {total_from_client}")
        
        # セッションから問題を取得
        questions = session.get('mock_exam_questions', [])
        total_from_session = session.get('mock_exam_total', 0)
        
        print(f"📚 Questions from session: {len(questions) if questions else 0}")
        print(f"📊 Total from session: {total_from_session}")
        
        # セッションに問題がない場合、クライアントから送られた問題数を使用
        if not questions and total_from_client > 0:
            print(f"⚠️  Using total from client: {total_from_client}")
            total_count = total_from_client
            
            # 簡易採点（セッションなしの場合）
            # 注: 正解データがないため、採点不可
            return jsonify({
                'error': '試験データがセッションから失われました。正確な採点ができません。',
                'answered_count': len(answers),
                'total_count': total_count
            }), 400
        
        if not questions:
            print(f"❌ No questions in session!")
            return jsonify({'error': '試験データが見つかりません。ページを再読み込みして試験を再開してください。'}), 400
        
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
        
        # セッションをクリア
        session.pop('mock_exam_questions', None)
        session.pop('mock_exam_total', None)
        
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
