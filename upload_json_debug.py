@app.route('/admin/upload_json', methods=['POST'])
@admin_required
def upload_json():
    """JSON問題ファイルのアップロードと処理（年度別対応）"""
    print(f"=== JSONアップロード開始 ===")
    try:
        # ファイルチェック
        if 'json_file' not in request.files:
            print("ERROR: json_fileがrequest.filesにありません")
            return jsonify({'success': False, 'error': 'JSONファイルが選択されていません'}), 400
        
        file = request.files['json_file']
        print(f"アップロードファイル名: {file.filename}")
        
        if file.filename == '':
            print("ERROR: ファイル名が空です")
            return jsonify({'success': False, 'error': 'ファイルが選択されていません'}), 400
        
        if not file.filename.lower().endswith('.json'):
            print(f"ERROR: JSONファイルではありません: {file.filename}")
            return jsonify({'success': False, 'error': 'JSONファイルを選択してください'}), 400
        
        # ファイル内容を読み込み
        print("ファイル内容読み込み中...")
        try:
            content = file.read().decode('utf-8')
            print(f"ファイルサイズ: {len(content)} 文字")
            print(f"ファイル内容の最初の100文字: {content[:100]}")
            
            questions = json.loads(content)
            print(f"JSONパース成功: {len(questions)}問の問題を検出")
        except UnicodeDecodeError as e:
            print(f"ERROR: 文字エンコーディングエラー: {e}")
            return jsonify({'success': False, 'error': 'ファイルの文字エンコーディングが正しくありません。UTF-8形式のファイルを使用してください。'}), 400
        except json.JSONDecodeError as e:
            print(f"ERROR: JSONパースエラー: {e}")
            return jsonify({'success': False, 'error': f'JSONファイルの形式が正しくありません: {str(e)}'}), 400
        
        # バリデーション
        if not isinstance(questions, list):
            print(f"ERROR: questionsがリストではありません: {type(questions)}")
            return jsonify({'success': False, 'error': 'JSONファイルは問題の配列である必要があります'}), 400
        
        if len(questions) == 0:
            print("ERROR: 問題が0件です")
            return jsonify({'success': False, 'error': 'JSONファイルに問題が含まれていません'}), 400
        
        print(f"バリデーション成功: {len(questions)}問")
        
        # 各問題の形式をチェックと修正
        print("問題の形式チェック中...")
        for i, question in enumerate(questions):
            required_fields = ['question_text', 'choices', 'correct_answer']
            for field in required_fields:
                if field not in question:
                    print(f"ERROR: 問題{i+1}に必須フィールド{field}がありません")
                    return jsonify({'success': False, 'error': f'問題{i+1}: 必須フィールド "{field}" がありません'}), 400
            
            # question_idがない場合は自動生成
            if 'question_id' not in question:
                question['question_id'] = f"問{i+1}"
                print(f"問題{i+1}にquestion_id自動生成: {question['question_id']}")
                
            # ジャンルがない場合はデフォルト設定
            if 'genre' not in question:
                question['genre'] = 'その他'
                print(f"問題{i+1}にデフォルトジャンル設定: その他")
                
            # 解説がない場合は空文字列設定
            if 'explanation' not in question:
                question['explanation'] = ''
        
        print("問題の形式チェック完了")
        
        # ファイル名から年度情報を解析
        file_info = parse_filename_info(file.filename)
        print(f"ファイル名解析結果: {file_info}")
        
        # JSONファイルを保存
        print("JSONファイル保存中...")
        json_filepath = os.path.join(app.config['JSON_FOLDER'], file.filename)
        print(f"保存先パス: {json_filepath}")
        
        # ディレクトリの存在確認
        os.makedirs(app.config['JSON_FOLDER'], exist_ok=True)
        
        with open(json_filepath, 'w', encoding='utf-8') as json_file:
            json.dump(questions, json_file, ensure_ascii=False, indent=2)
        print(f"JSONファイル保存完了: {json_filepath}")
        
        # データベースに保存
        print("データベースに保存中...")
        saved_count = question_manager.save_questions(questions)
        print(f"データベース保存完了: {saved_count}問保存")
        
        message = f'{len(questions)}問の問題をJSONファイルとデータベースに正常に保存しました'
        if file_info:
            message += f' ({file_info["display_name"]})'
        
        print(f"=== JSONアップロード成功 ===")
        return jsonify({
            'success': True,
            'message': message,
            'count': len(questions),
            'saved_to_db': saved_count,
            'json_file': file.filename,
            'file_info': file_info
        })
        
    except Exception as e:
        print(f"ERROR: 予期しないエラー: {e}")
        print(f"エラー詳細: {str(e)}")
        import traceback
        print(f"スタックトレース: {traceback.format_exc()}")
        
        app.logger.error(f"Upload JSON error: {e}")
        return jsonify({'success': False, 'error': f'JSON処理中にエラーが発生しました: {str(e)}'}), 500