"""
練習問題関連のルーティング
"""
from flask import Blueprint, render_template, request, jsonify, session, current_app
from auth import login_required
from persistent_session import persistent_login_required
import json

practice_bp = Blueprint('practice', __name__)

def get_db_manager():
    """データベースマネージャーを取得"""
    return current_app.db_manager

def get_question_manager():
    """QuestionManagerを取得"""
    return current_app.question_manager

@practice_bp.route('/practice/random')
@persistent_login_required
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
@persistent_login_required
def genre_practice():
    """ジャンル別演習のトップページ"""
    db_manager = get_db_manager()
    question_manager = get_question_manager()
    
    # ジャンル別の統計を取得
    genres = question_manager.get_available_genres()
    genre_stats = []
    
    user_id = session.get('user_id')
    
    for genre in genres:
        # ジャンル別問題数
        count = question_manager.get_question_count_by_genre().get(genre, 0)
        
        # ユーザーの正答率を計算
        if user_id:
            # ユーザーの回答履歴を取得
            if db_manager.db_type == 'postgresql':
                query = """
                    SELECT COUNT(*) as total, SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct
                    FROM user_answers ua
                    JOIN questions q ON ua.question_id = q.id
                    WHERE ua.user_id = %s AND q.genre = %s
                """
            else:
                query = """
                    SELECT COUNT(*) as total, SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct
                    FROM user_answers ua
                    JOIN questions q ON ua.question_id = q.id
                    WHERE ua.user_id = ? AND q.genre = ?
                """
            
            result = db_manager.execute_query(query, (user_id, genre))
            answered = result[0]['total'] if result else 0
            correct = result[0]['correct'] if result and result[0]['correct'] else 0
            accuracy = int((correct / answered * 100)) if answered > 0 else 0
        else:
            answered = 0
            accuracy = 0
        
        genre_stats.append({
            'name': genre,
            'count': count,
            'answered': answered,
            'accuracy': accuracy
        })
    
    return render_template('genre_practice.html', genres=genre_stats)

@practice_bp.route('/practice/genre/<genre>')
@persistent_login_required
def practice_by_genre(genre):
    """ジャンル別問題演習"""
    question_manager = get_question_manager()
    
    # 指定されたジャンルの問題を取得（これが修正箇所！）
    questions = question_manager.get_questions_by_genre(genre)
    
    if not questions:
        return render_template('error.html',
                             message=f'{genre}の問題が見つかりません',
                             detail='このジャンルの問題が登録されていません')
    
    return render_template('practice.html', questions=questions, genre=genre)

@practice_bp.route('/questions/<int:question_id>/answer', methods=['POST'])
@persistent_login_required
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
