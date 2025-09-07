@app.route('/admin/load_json_folder', methods=['POST'])
@admin_required
def load_json_folder():
    """json_questionsフォルダ内のすべてのJSONファイルをデータベースに読み込み"""
    try:
        json_folder = app.config['JSON_FOLDER']
        if not os.path.exists(json_folder):
            return jsonify({'error': 'JSONフォルダが見つかりません'}), 404
        
        loaded_files = []
        total_questions = 0
        
        # フォルダ内のすべてのJSONファイルを処理
        for filename in os.listdir(json_folder):
            if filename.endswith('.json'):
                json_filepath = os.path.join(json_folder, filename)
                try:
                    with open(json_filepath, 'r', encoding='utf-8') as json_file:
                        questions = json.load(json_file)
                    
                    # データベースに保存
                    saved_count = question_manager.save_questions(questions)
                    loaded_files.append({
                        'filename': filename,
                        'count': saved_count
                    })
                    total_questions += saved_count
                    
                except Exception as e:
                    print(f"ファイル {filename} の読み込みでエラー: {e}")
                    continue
        
        if loaded_files:
            return jsonify({
                'message': f'{len(loaded_files)}個のJSONファイルから{total_questions}問の問題を読み込みました',
                'files': loaded_files,
                'total_questions': total_questions
            })
        else:
            return jsonify({'error': '読み込み可能なJSONファイルが見つかりませんでした'}), 404
        
    except Exception as e:
        app.logger.error(f"Load JSON folder error: {e}")
        return jsonify({'error': f'JSONフォルダ読み込み中にエラーが発生しました: {str(e)}'}), 500