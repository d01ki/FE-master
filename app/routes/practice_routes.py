"""
練習問題関連のルーティング
"""
from flask import Blueprint, render_template, request, jsonify, session, current_app
from app.core.auth import login_required
import json

practice_bp = Blueprint('practice', __name__)

def get_db_manager():
    """データベースマネージャーを取得"""
    return current_app.db_manager

def get_question_manager():
    """QuestionManagerを取得"""
    return current_app.question_manager

@practice_bp.route('/practice/random')
@login_required
def random_practice():
    """ランダム問題練習"""
    question_manager = get_question_manager()
    question = question_manager.get_random_question()
    
    if not question:
        return render_template('error.html', 
                             message='問題が見つかりません',
                             detail='データベースに問題が登録されていません')
    
    return render_template('question.html', question=question, mode='random')

@practice_bp.route('/practice/genre')
@login_required
def genre_practice():
    """ジャンル別演習のトップページ"""
    question_manager = get_question_manager()
    
    # ジャンル一覧を取得
    genres = question_manager.get_all_genres()
    
    return render_template('genre_practice.html', genres=genres)

@practice_bp.route('/practice/genre/<genre>')
@login_required
def practice_by_genre(genre):
    """ジャンル別問題演習"""
    question_manager = get_question_manager()
    
    # 指定されたジャンルの問題を取得
    questions = question_manager.get_questions_by_genre(genre)
    
    if not questions:
        return render_template('error.html',
                             message=f'{genre}の問題が見つかりません',
                             detail='このジャンルの問題が登録されていません')
    
    # 最初の問題を表示
    question = questions[0] if questions else None
    
    return render_template('question.html', question=question, mode='genre', genre=genre)

@practice_bp.route('/questions/<int:question_id>/answer', methods=['POST'])
@login_required
def submit_answer(question_id):
    """問題の解答を送信"""
    question_manager = get_question_manager()
    
    data = request.get_json()
    user_answer = data.get('answer')
    
    if not user_answer:
        return jsonify({'error': '解答が選択されていません'}), 400
    
    # 解答をチェック
    result = question_manager.check_answer(question_id, user_answer)
    
    if 'error' in result:
        return jsonify(result), 404
    
    # 解答履歴を保存
    user_id = session.get('user_id')
    if user_id:
        question_manager.save_answer_history(
            question_id, 
            user_answer, 
            result['is_correct'],
            user_id
        )
    
    return jsonify(result)
