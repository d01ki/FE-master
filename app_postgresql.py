import os
import psycopg2
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import json
import sqlite3
import logging
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fe-exam-app-secret-key-change-in-production')

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    app.config['DATABASE_TYPE'] = 'postgresql'
    app.config['DATABASE_URL'] = DATABASE_URL
else:
    app.config['DATABASE_TYPE'] = 'sqlite'
    app.config['DATABASE'] = 'fe_exam.db'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import modules
from auth import init_auth_routes, login_required, admin_required
from database import DatabaseManager, QuestionManager

# Initialize components
db_manager = DatabaseManager(app.config)
question_manager = QuestionManager(db_manager)

# Initialize authentication routes
init_auth_routes(app, db_manager)

@app.before_first_request
def initialize_app():
    try:
        db_manager.init_database()
        
        # Create default admin
        existing_admin = db_manager.execute_query(
            'SELECT id FROM users WHERE is_admin = %s' if db_manager.db_type == 'postgresql' else 'SELECT id FROM users WHERE is_admin = ?',
            (True,) if db_manager.db_type == 'postgresql' else (1,)
        )
        
        if not existing_admin:
            admin_hash = generate_password_hash('admin123')
            db_manager.execute_query(
                'INSERT INTO users (username, password_hash, is_admin) VALUES (%s, %s, %s)' if db_manager.db_type == 'postgresql' else 'INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)',
                ('admin', admin_hash, True) if db_manager.db_type == 'postgresql' else ('admin', admin_hash, 1)
            )
            logger.info("Default admin created: admin/admin123")
        
        result = question_manager.load_json_files()
        logger.info(f"Loaded {result['total_questions']} questions")
    except Exception as e:
        logger.error(f"Init error: {e}")

# Main routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('auth/login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    total_questions = db_manager.execute_query("SELECT COUNT(*) as count FROM questions")[0]['count']
    user_answers_query = "SELECT COUNT(*) as count FROM user_answers WHERE user_id = %s" if db_manager.db_type == 'postgresql' else "SELECT COUNT(*) as count FROM user_answers WHERE user_id = ?"
    total_answers = db_manager.execute_query(user_answers_query, (user_id,))[0]['count']
    
    correct_query = "SELECT COUNT(*) as count FROM user_answers WHERE user_id = %s AND is_correct = %s" if db_manager.db_type == 'postgresql' else "SELECT COUNT(*) as count FROM user_answers WHERE user_id = ? AND is_correct = ?"
    correct_count = db_manager.execute_query(correct_query, (user_id, True if db_manager.db_type == 'postgresql' else 1))[0]['count']
    
    accuracy_rate = round((correct_count / total_answers) * 100, 1) if total_answers > 0 else 0
    
    stats = {
        'total_questions': total_questions,
        'total_answers': total_answers,
        'correct_answers': correct_count,
        'accuracy_rate': accuracy_rate
    }
    
    return render_template('dashboard.html', stats=stats)

@app.route('/random')
@login_required
def random_question():
    result = db_manager.execute_query("SELECT id FROM questions ORDER BY RANDOM() LIMIT 1")
    if not result:
        flash('問題が見つかりません。', 'warning')
        return redirect(url_for('dashboard'))
    return redirect(url_for('show_question', question_id=result[0]['id']))

@app.route('/question/<int:question_id>')
@login_required
def show_question(question_id):
    query = "SELECT * FROM questions WHERE id = %s" if db_manager.db_type == 'postgresql' else "SELECT * FROM questions WHERE id = ?"
    question = db_manager.execute_query(query, (question_id,))
    
    if not question:
        flash('問題が見つかりません。', 'error')
        return redirect(url_for('dashboard'))
    
    question_data = question[0]
    choices = json.loads(question_data['choices']) if isinstance(question_data['choices'], str) else question_data['choices']
    return render_template('question.html', question=question_data, choices=choices)

@app.route('/submit_answer', methods=['POST'])
@login_required
def submit_answer():
    try:
        question_id = request.form.get('question_id', type=int)
        user_answer = request.form.get('answer')
        user_id = session['user_id']

        if not question_id or not user_answer:
            return jsonify({'error': '無効な回答です。'}), 400

        query = "SELECT correct_answer, explanation FROM questions WHERE id = %s" if db_manager.db_type == 'postgresql' else "SELECT correct_answer, explanation FROM questions WHERE id = ?"
        result = db_manager.execute_query(query, (question_id,))
        
        if not result:
            return jsonify({'error': '問題が見つかりません。'}), 404

        correct_answer = result[0]['correct_answer']
        explanation = result[0]['explanation']
        is_correct = (user_answer == correct_answer)

        insert_query = "INSERT INTO user_answers (user_id, question_id, user_answer, is_correct) VALUES (%s, %s, %s, %s)" if db_manager.db_type == 'postgresql' else "INSERT INTO user_answers (user_id, question_id, user_answer, is_correct) VALUES (?, ?, ?, ?)"
        db_manager.execute_query(insert_query, (user_id, question_id, user_answer, is_correct))

        return jsonify({
            'is_correct': is_correct,
            'correct_answer': correct_answer,
            'explanation': explanation or ''
        })
    except Exception as e:
        logger.error(f"Answer error: {e}")
        return jsonify({'error': '処理エラー'}), 500

@app.route('/genre_practice')
@login_required
def genre_practice():
    genres = [row['genre'] for row in db_manager.execute_query("SELECT DISTINCT genre FROM questions ORDER BY genre")]
    return render_template('genre_practice.html', genres=genres)

@app.route('/genre/<path:genre_name>')
@login_required
def genre_questions(genre_name):
    query = "SELECT id, question_text FROM questions WHERE genre = %s ORDER BY id" if db_manager.db_type == 'postgresql' else "SELECT id, question_text FROM questions WHERE genre = ? ORDER BY id"
    questions = db_manager.execute_query(query, (genre_name,))
    return render_template('problem_list.html', questions=questions, title=f'{genre_name}演習')

@app.route('/history')
@login_required
def history():
    user_id = session['user_id']
    query = "SELECT q.question_text, ua.user_answer, ua.is_correct, ua.answered_at FROM user_answers ua JOIN questions q ON ua.question_id = q.id WHERE ua.user_id = %s ORDER BY ua.answered_at DESC LIMIT 50" if db_manager.db_type == 'postgresql' else "SELECT q.question_text, ua.user_answer, ua.is_correct, ua.answered_at FROM user_answers ua JOIN questions q ON ua.question_id = q.id WHERE ua.user_id = ? ORDER BY ua.answered_at DESC LIMIT 50"
    answers = db_manager.execute_query(query, (user_id,))
    return render_template('history.html', answers=answers)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
