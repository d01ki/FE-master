@app.route('/random')
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

@app.route('/mock_exam/<filename>')
def mock_exam_start(filename):
    """指定年度の模擬試験開始"""
    try:
        file_info = parse_filename_info(filename)
        if not file_info:
            flash('無効な試験ファイルです', 'error')
            return redirect(url_for('mock_exam'))
        
        json_filepath = os.path.join(app.config['JSON_FOLDER'], filename)
        if not os.path.exists(json_filepath):
            flash('試験ファイルが見つかりません', 'error')
            return redirect(url_for('mock_exam'))
        
        with open(json_filepath, 'r', encoding='utf-8') as f:
            questions = json.load(f)
        
        if len(questions) > 20:
            questions = random.sample(questions, 20)
        
        session['exam_start_time'] = datetime.now().isoformat()
        session['exam_questions'] = [q.get('question_id', f"Q{i+1:03d}") for i, q in enumerate(questions)]
        session['exam_year_info'] = file_info
        session['exam_file_questions'] = questions
        
        return render_template('mock_exam_practice.html', 
                             questions=questions, 
                             exam_info=file_info)
        
    except Exception as e:
        app.logger.error(f"Mock exam start error: {e}")
        flash(f'試験ファイルの読み込みに失敗しました: {str(e)}', 'error')
        return redirect(url_for('mock_exam'))

@app.route('/mock_exam/submit', methods=['POST'])
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
                        
                        if current_user.is_authenticated:
                            question_manager.save_answer_history(question_id, user_answer, is_correct, current_user.id)
                        
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
