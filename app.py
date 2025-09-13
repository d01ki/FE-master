        return jsonify({'success': False, 'error': f'JSON処理中にエラーが発生しました: {str(e)}'}), 500

@app.route('/admin/delete_json/<filename>', methods=['POST'])
@admin_required
def delete_json(filename):
    """JSONファイル削除"""
    try:
        json_filepath = os.path.join(app.config['JSON_FOLDER'], filename)
        if os.path.exists(json_filepath):
            os.remove(json_filepath)
            return jsonify({
                'success': True,
                'message': f'ファイル "{filename}" を削除しました'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'ファイルが見つかりません'
            }), 404
    except Exception as e:
        app.logger.error(f"Delete JSON error: {e}")
        return jsonify({'success': False, 'error': f'ファイル削除中にエラーが発生しました: {str(e)}'}), 500

@app.route('/admin/reset_database', methods=['POST'])
@admin_required
def reset_database():
    """データベースの初期化"""
    try:
        with get_db_connection(app.config['DATABASE_URL']) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM user_answers')
            cursor.execute('DELETE FROM questions')
            conn.commit()
        
        return jsonify({'message': 'データベースを初期化しました'})
        
    except Exception as e:
        app.logger.error(f"Reset database error: {e}")
        return jsonify({'error': f'データベース初期化中にエラーが発生しました: {str(e)}'}), 500

@app.route('/api/questions/random')
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

@app.errorhandler(404)
def not_found_error(error):
    """404エラーハンドラ"""
    return render_template('error.html', message='ページが見つかりません'), 404

@app.errorhandler(500)
def internal_error(error):
    """500エラーハンドラ"""
    app.logger.error(f"Internal error: {error}")
    return render_template('error.html', message='内部サーバーエラーが発生しました'), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
