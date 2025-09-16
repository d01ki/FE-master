@app.route('/mock_exam/submit', methods=['POST'])
@login_required
def submit_mock_exam():
    """模擬試験の採点"""
    try:
        data = request.get_json()
        answers = data.get('answers', {})
        
        if 'exam_questions' not in session:
            return jsonify({'error': '試験セッションが見つかりません'}), 400
        
        question_ids = session['exam_questions']
        results = []
        correct_count = 0
        
        if 'exam_file_questions' in session:
            file_questions = session['exam_file_questions']
            question_dict = {q.get('question_id', f"Q{i+1:03d}"): q for i, q in enumerate(file_questions)}
            
            for question_id in question_ids:
                question_data = question_dict.get(question_id)
                if question_data:
                    user_answer = answers.get(question_id, '')
                    is_correct = user_answer == question_data['correct_answer']
                    
                    results.append({
                        'question_id': question_id,
                        'question_text': question_data['question_text'],
                        'user_answer': user_answer,
                        'correct_answer': question_data['correct_answer'],
                        'is_correct': is_correct,
                        'explanation': question_data.get('explanation', '')
                    })
                    
                    if is_correct:
                        correct_count += 1
        else:
            for question_id in question_ids:
                if isinstance(question_id, int):
                    question = question_manager.get_question(question_id)
                    if question:
                        user_answer = answers.get(str(question_id), '')
                        is_correct = user_answer == question['correct_answer']
                        
                        question_manager.save_answer_history(question_id, user_answer, is_correct)
                        
                        results.append({
                            'question_id': question_id,
                            'question_text': question['question_text'],
                            'user_answer': user_answer,
                            'correct_answer': question['correct_answer'],
                            'is_correct': is_correct,
                            'explanation': question.get('explanation', '')
                        })
                        
                        if is_correct:
                            correct_count += 1
        
        score = round((correct_count / len(question_ids)) * 100, 1) if question_ids else 0
        
        session.pop('exam_start_time', None)
        session.pop('exam_questions', None)
        session.pop('exam_year_info', None)
        session.pop('exam_file_questions', None)
        
        return jsonify({
            'score': score,
            'correct_count': correct_count,
            'total_count': len(question_ids),
            'results': results
        })
        
    except Exception as e:
        app.logger.error(f"Submit mock exam error: {e}")
        return jsonify({'error': '採点処理中にエラーが発生しました'}), 500

@app.route('/history')
@login_required
def history():
    """学習履歴の表示"""
    try:
        with get_db_connection(app.config['DATABASE_URL'], app.config['DATABASE']) as conn:
            if is_postgresql(app.config['DATABASE_URL']):
                # PostgreSQL
                with conn.cursor() as cur:
                    cur.execute('''
                        SELECT q.question_text, q.genre, ua.user_answer, ua.is_correct, ua.answered_at,
                               q.correct_answer, q.explanation
                        FROM user_answers ua 
                        JOIN questions q ON ua.question_id = q.id 
                        ORDER BY ua.answered_at DESC 
                        LIMIT 50
                    ''')
                    detailed_history = cur.fetchall()
                    
                    cur.execute('''
                        SELECT DATE(answered_at) as date, 
                               COUNT(*) as total,
                               SUM(CASE WHEN is_correct = true THEN 1 ELSE 0 END) as correct
                        FROM user_answers 
                        GROUP BY DATE(answered_at) 
                        ORDER BY date DESC 
                        LIMIT 30
                    ''')
                    daily_stats = cur.fetchall()
            else:
                # SQLite
                detailed_history = [dict(row) for row in conn.execute('''
                    SELECT q.question_text, q.genre, ua.user_answer, ua.is_correct, ua.answered_at,
                           q.correct_answer, q.explanation
                    FROM user_answers ua 
                    JOIN questions q ON ua.question_id = q.id 
                    ORDER BY ua.answered_at DESC 
                    LIMIT 50
                ''').fetchall()]
                
                daily_stats = [dict(row) for row in conn.execute('''
                    SELECT DATE(answered_at) as date, 
                           COUNT(*) as total,
                           SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct
                    FROM user_answers 
                    GROUP BY DATE(answered_at) 
                    ORDER BY date DESC 
                    LIMIT 30
                ''').fetchall()]
            
            history_data = {
                'detailed_history': [dict(row) for row in detailed_history] if is_postgresql(app.config['DATABASE_URL']) else detailed_history,
                'daily_stats': [dict(row) for row in daily_stats] if is_postgresql(app.config['DATABASE_URL']) else daily_stats
            }
        
        return render_template('history.html', history=history_data)
    except Exception as e:
        app.logger.error(f"History error: {e}")
        return render_template('error.html', message='学習履歴の表示中にエラーが発生しました'), 500

# 管理機能
@app.route('/admin')
@old_admin_required
def admin():
    """管理画面"""
    try:
        with get_db_connection(app.config['DATABASE_URL'], app.config['DATABASE']) as conn:
            if is_postgresql(app.config['DATABASE_URL']):
                # PostgreSQL
                with conn.cursor() as cur:
                    cur.execute('SELECT COUNT(*) as count FROM questions')
                    question_count = cur.fetchone()['count']
                    cur.execute('SELECT DISTINCT genre FROM questions')
                    genres = [row['genre'] for row in cur.fetchall()]
            else:
                # SQLite
                question_count = conn.execute('SELECT COUNT(*) FROM questions').fetchone()[0]
                genres = [row[0] for row in conn.execute('SELECT DISTINCT genre FROM questions').fetchall()]
            
            json_files = []
            if os.path.exists(app.config['JSON_FOLDER']):
                for filename in os.listdir(app.config['JSON_FOLDER']):
                    if filename.endswith('.json'):
                        filepath = os.path.join(app.config['JSON_FOLDER'], filename)
                        if os.path.exists(filepath):
                            file_size = os.path.getsize(filepath)
                            file_info = parse_filename_info(filename)
                            
                            json_files.append({
                                'filename': filename,
                                'size': file_size,
                                'modified': datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%Y-%m-%d %H:%M'),
                                'info': file_info
                            })
            
            json_files.sort(key=lambda x: (x['info']['year'], x['info']['season']) if x['info'] else (0, ''), reverse=True)
            
            admin_data = {
                'question_count': question_count,
                'genres': genres,
                'json_files': json_files
            }
        
        return render_template('admin.html', data=admin_data)
    except Exception as e:
        app.logger.error(f"Admin error: {e}")
        return render_template('error.html', message='管理画面の表示中にエラーが発生しました'), 500

@app.route('/admin/upload_json', methods=['POST'])
@old_admin_required
def upload_json():
    """JSON問題ファイルのアップロードと処理"""
    try:
        if 'json_file' not in request.files:
            return jsonify({'success': False, 'error': 'JSONファイルが選択されていません'}), 400
        
        file = request.files['json_file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'ファイルが選択されていません'}), 400
        
        if not file.filename.lower().endswith('.json'):
            return jsonify({'success': False, 'error': 'JSONファイルを選択してください'}), 400
        
        try:
            content = file.read().decode('utf-8')
            questions = json.loads(content)
        except UnicodeDecodeError:
            return jsonify({'success': False, 'error': 'ファイルの文字エンコーディングが正しくありません。'}), 400
        except json.JSONDecodeError as e:
            return jsonify({'success': False, 'error': f'JSONファイルの形式が正しくありません: {str(e)}'}), 400
        
        if not isinstance(questions, list):
            return jsonify({'success': False, 'error': 'JSONファイルは問題の配列である必要があります'}), 400
        
        if len(questions) == 0:
            return jsonify({'success': False, 'error': 'JSONファイルに問題が含まれていません'}), 400
        
        for i, question in enumerate(questions):
            required_fields = ['question_text', 'choices', 'correct_answer']
            for field in required_fields:
                if field not in question:
                    return jsonify({'success': False, 'error': f'問題{i+1}: 必須フィールド "{field}" がありません'}), 400
            
            if 'question_id' not in question:
                question['question_id'] = f"問{i+1}"
                
            if 'genre' not in question:
                question['genre'] = 'その他'
                
            if 'explanation' not in question:
                question['explanation'] = ''
        
        file_info = parse_filename_info(file.filename)
        
        json_filepath = os.path.join(app.config['JSON_FOLDER'], file.filename)
        with open(json_filepath, 'w', encoding='utf-8') as json_file:
            json.dump(questions, json_file, ensure_ascii=False, indent=2)
        
        saved_count = question_manager.save_questions(questions)
        
        message = f'{len(questions)}問の問題をJSONファイルとデータベースに正常に保存しました'
        if file_info:
            message += f' ({file_info["display_name"]})'
        
        return jsonify({
            'success': True,
            'message': message,
            'count': len(questions),
            'saved_to_db': saved_count,
            'json_file': file.filename,
            'file_info': file_info
        })
        
    except Exception as e:
        app.logger.error(f"Upload JSON error: {e}")
        return jsonify({'success': False, 'error': f'JSON処理中にエラーが発生しました: {str(e)}'}), 500

@app.route('/admin/create_sample', methods=['POST'])
@old_admin_required
def create_sample_data():
    """サンプルデータの作成"""
    try:
        processor = PDFProcessor()
        sample_questions = processor.create_sample_questions()
        
        saved_count = question_manager.save_questions(sample_questions)
        
        return jsonify({
            'message': f'{saved_count}問のサンプル問題を作成しました',
            'count': saved_count
        })
        
    except Exception as e:
        app.logger.error(f"Create sample error: {e}")
        return jsonify({'error': f'サンプルデータ作成中にエラーが発生しました: {str(e)}'}), 500

@app.route('/admin/reset_database', methods=['POST'])
@old_admin_required
def reset_database():
    """データベースの初期化"""
    try:
        with get_db_connection(app.config['DATABASE_URL'], app.config['DATABASE']) as conn:
            if is_postgresql(app.config['DATABASE_URL']):
                # PostgreSQL
                with conn.cursor() as cur:
                    cur.execute('DELETE FROM user_answers')
                    cur.execute('DELETE FROM questions')
                conn.commit()
            else:
                # SQLite
                conn.execute('DELETE FROM user_answers')
                conn.execute('DELETE FROM questions')
        
        return jsonify({'message': 'データベースを初期化しました'})
        
    except Exception as e:
        app.logger.error(f"Reset database error: {e}")
        return jsonify({'error': f'データベース初期化中にエラーが発生しました: {str(e)}'}), 500

# API エンドポイント
@app.route('/api/questions/random')
@login_required
def get_random_question():
    """ランダムな問題を1問取得するAPI"""
    try:
        question = question_manager.get_random_question()
        if not question:
            return jsonify({'error': '問題が見つかりません'}), 404
        
        return jsonify(question)
    except Exception as e:
        app.logger.error(f"Get random question error: {e}")
        return jsonify({'error': 'ランダム問題の取得中にエラーが発生しました'}), 500

@app.route('/random')
@login_required
def random_question():
    """ランダム問題への直接アクセス"""
    try:
        question = question_manager.get_random_question()
        if not question:
            flash('問題が見つかりません。まず問題を登録してください。', 'error')
            return redirect(url_for('admin_login'))
        
        return redirect(url_for('show_question', question_id=question['id']))
    except Exception as e:
        app.logger.error(f"Random question error: {e}")
        flash('ランダム問題の表示中にエラーが発生しました。', 'error')
        return redirect(url_for('index'))

# エラーハンドラ
@app.errorhandler(404)
def not_found_error(error):
    """404エラーハンドラ"""
    return render_template('error.html', message='ページが見つかりません'), 404

@app.errorhandler(500)
def internal_error(error):
    """500エラーハンドラ"""
    app.logger.error(f"Internal error: {error}")
    return render_template('error.html', message='内部サーバーエラーが発生しました'), 500

# アプリケーション初期化
print("アプリケーションを初期化しています...")
initialize_app()
question_manager = QuestionManager(app.config['DATABASE_URL'], app.config['DATABASE'])
load_json_questions_on_startup()
print("✅ アプリケーション初期化完了")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
