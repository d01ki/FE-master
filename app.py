@app.route('/mock_exam/submit', methods=['POST'])
@login_required
def submit_mock_exam():
    """模擬試験の採点"""
    try:
        data = request.get_json()
        answers = data.get('answers', {})
        
        # デバッグログ
        app.logger.info(f"Received answers: {answers}")
        app.logger.info(f"Session keys: {list(session.keys())}")
        
        # セッションから問題を取得
        questions = session.get('mock_exam_questions', [])
        
        app.logger.info(f"Questions from session: {len(questions) if questions else 0}")
        
        if not questions:
            # より詳細なエラー情報
            app.logger.error(f"No questions in session. Session data: {dict(session)}")
            return jsonify({'error': '試験データが見つかりません。試験を再開してください。'}), 400
        
        # 採点処理
        total_count = len(questions)
        correct_count = 0
        
        for i, question in enumerate(questions):
            question_index = str(i)
            user_answer = answers.get(question_index)
            correct_answer = question.get('correct_answer')
            
            app.logger.info(f"Q{i}: User={user_answer}, Correct={correct_answer}")
            
            if user_answer and user_answer == correct_answer:
                correct_count += 1
        
        score = round((correct_count / total_count) * 100, 1) if total_count > 0 else 0
        
        # セッションをクリア
        session.pop('mock_exam_questions', None)
        
        app.logger.info(f"Result: {correct_count}/{total_count} = {score}%")
        
        return jsonify({
            'score': score,
            'correct_count': correct_count,
            'total_count': total_count
        })
        
    except Exception as e:
        app.logger.error(f"Submit mock exam error: {e}", exc_info=True)
        return jsonify({'error': f'採点処理中にエラー: {str(e)}'}), 500
