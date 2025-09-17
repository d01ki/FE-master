@app.route('/dashboard')
@login_required
def dashboard():
    """メインページ - ダッシュボード表示（ログイン後）"""
    try:
        user_id = session['user_id']
        
        # 基本統計を取得
        total_questions = db_manager.execute_query('SELECT COUNT(*) as count FROM questions')
        total_q_count = total_questions[0]['count'] if total_questions else 0
        
        user_answers = db_manager.execute_query(
            'SELECT COUNT(*) as count FROM user_answers WHERE user_id = %s' if db_manager.db_type == 'postgresql' else 'SELECT COUNT(*) as count FROM user_answers WHERE user_id = ?',
            (user_id,)
        )
        answered_count = user_answers[0]['count'] if user_answers else 0
        
        # SQLiteとPostgreSQLで条件文を分ける
        if db_manager.db_type == 'postgresql':
            correct_answers = db_manager.execute_query(
                'SELECT COUNT(*) as count FROM user_answers WHERE user_id = %s AND is_correct = %s',
                (user_id, True)
            )
        else:
            correct_answers = db_manager.execute_query(
                'SELECT COUNT(*) as count FROM user_answers WHERE user_id = ? AND is_correct = 1',
                (user_id,)
            )
        correct_count = correct_answers[0]['count'] if correct_answers else 0
        
        accuracy_rate = round((correct_count / answered_count * 100), 1) if answered_count > 0 else 0
        
        # 最近の履歴
        recent_history = db_manager.execute_query('''
            SELECT q.question_text, ua.is_correct, ua.answered_at 
            FROM user_answers ua 
            JOIN questions q ON ua.question_id = q.id 
            WHERE ua.user_id = %s
            ORDER BY ua.answered_at DESC 
            LIMIT 10
        ''' if db_manager.db_type == 'postgresql' else '''
            SELECT q.question_text, ua.is_correct, ua.answered_at 
            FROM user_answers ua 
            JOIN questions q ON ua.question_id = q.id 
            WHERE ua.user_id = ?
            ORDER BY ua.answered_at DESC 
            LIMIT 10
        ''', (user_id,))
        
        # ジャンル別統計
        if db_manager.db_type == 'postgresql':
            genre_stats = db_manager.execute_query('''
                SELECT q.genre, 
                       COUNT(*) as total,
                       SUM(CASE WHEN ua.is_correct = %s THEN 1 ELSE 0 END) as correct
                FROM user_answers ua 
                JOIN questions q ON ua.question_id = q.id 
                WHERE ua.user_id = %s AND q.genre IS NOT NULL
                GROUP BY q.genre
            ''', (True, user_id))
        else:
            genre_stats = db_manager.execute_query('''
                SELECT q.genre, 
                       COUNT(*) as total,
                       SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) as correct
                FROM user_answers ua 
                JOIN questions q ON ua.question_id = q.id 
                WHERE ua.user_id = ? AND q.genre IS NOT NULL
                GROUP BY q.genre
            ''', (user_id,))
        
        stats = {
            'total_questions': total_q_count,
            'total_answers': answered_count,
            'correct_answers': correct_count,
            'accuracy_rate': accuracy_rate,
            'recent_history': recent_history or [],
            'genre_stats': genre_stats or []
        }
        
        return render_template('dashboard.html', stats=stats)
    except Exception as e:
        app.logger.error(f"Dashboard error: {e}")
        stats = {
            'total_questions': 0,
            'total_answers': 0,
            'correct_answers': 0,
            'accuracy_rate': 0,
            'recent_history': [],
            'genre_stats': []
        }
        return render_template('dashboard.html', stats=stats)