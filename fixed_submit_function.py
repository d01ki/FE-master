@app.route('/mock_exam/submit', methods=['POST'])
def submit_mock_exam():
    """模擬試験の採点"""
    try:
        data = request.get_json()
        answers = data.get('answers', {})
        
        # セッション情報の確認
        if 'exam_questions' not in session and 'exam_file_questions' not in session:
            return jsonify({'error': '試験セッションが見つかりません。試験を再開してください。'}), 400
        
        results = []
        correct_count = 0
        total_questions = 0
        
        # ファイルベースの問題（JSONから読み込んだ問題）
        if 'exam_file_questions' in session:
            file_questions = session['exam_file_questions']
            total_questions = len(file_questions)
            
            for i, question_data in enumerate(file_questions):
                question_index = str(i)  # フロントエンドでのインデックスベース
                user_answer = answers.get(question_index, '')
                is_correct = user_answer == question_data['correct_answer']
                
                results.append({
                    'question_id': question_data.get('question_id', f'Q{i+1:03d}'),
                    'question_text': question_data['question_text'][:100] + '...',
                    'user_answer': user_answer,
                    'correct_answer': question_data['correct_answer'],
                    'is_correct': is_correct,
                    'explanation': question_data.get('explanation', '')
                })
                
                if is_correct:
                    correct_count += 1
        
        # データベースベースの問題
        elif 'exam_questions' in session:
            question_ids = session['exam_questions']
            total_questions = len(question_ids)
            
            for i, question_id in enumerate(question_ids):
                question_index = str(i)  # フロントエンドでのインデックスベース
                user_answer = answers.get(question_index, '')
                
                if isinstance(question_id, int):
                    question = question_manager.get_question(question_id)
                    if question:
                        is_correct = user_answer == question['correct_answer']
                        
                        # 履歴に保存
                        question_manager.save_answer_history(question_id, user_answer, is_correct)
                        
                        results.append({
                            'question_id': question_id,
                            'question_text': question['question_text'][:100] + '...',
                            'user_answer': user_answer,
                            'correct_answer': question['correct_answer'],
                            'is_correct': is_correct,
                            'explanation': question.get('explanation', '')
                        })
                        
                        if is_correct:
                            correct_count += 1
        
        if total_questions == 0:
            return jsonify({'error': '試験問題が見つかりません。'}), 400
        
        score = round((correct_count / total_questions) * 100, 1)
        
        # セッション情報をクリア
        session.pop('exam_start_time', None)
        session.pop('exam_questions', None)
        session.pop('exam_year_info', None)
        session.pop('exam_file_questions', None)
        
        return jsonify({
            'score': score,
            'correct_count': correct_count,
            'total_count': total_questions,
            'results': results
        })
        
    except Exception as e:
        app.logger.error(f"Submit mock exam error: {e}")
        return jsonify({'error': f'採点処理中にエラーが発生しました: {str(e)}'}), 500