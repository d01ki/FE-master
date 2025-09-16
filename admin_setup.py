@app.route('/admin/create_sample', methods=['POST'])
@admin_required
def create_sample_data():
    """サンプルデータの作成"""
    try:
        # 簡単なサンプル問題を作成
        sample_questions = [
            {
                "question_id": "SAMPLE001",
                "question_text": "基本情報技術者試験について、正しい説明はどれか。",
                "choices": {
                    "ア": "年に1回実施される",
                    "イ": "年に2回実施される", 
                    "ウ": "年に3回実施される",
                    "エ": "年に4回実施される"
                },
                "correct_answer": "イ",
                "explanation": "基本情報技術者試験は春期（4月）と秋期（10月）の年2回実施されます。",
                "genre": "試験制度"
            },
            {
                "question_id": "SAMPLE002",
                "question_text": "2進数1011を10進数に変換すると、いくつになるか。",
                "choices": {
                    "ア": "9",
                    "イ": "10",
                    "ウ": "11", 
                    "エ": "12"
                },
                "correct_answer": "ウ",
                "explanation": "2進数1011は、1×2³ + 0×2² + 1×2¹ + 1×2⁰ = 8 + 0 + 2 + 1 = 11です。",
                "genre": "基礎理論"
            },
            {
                "question_id": "SAMPLE003",
                "question_text": "OSIモデルの第4層は何層か。",
                "choices": {
                    "ア": "ネットワーク層",
                    "イ": "データリンク層",
                    "ウ": "トランスポート層",
                    "エ": "セッション層"
                },
                "correct_answer": "ウ",
                "explanation": "OSIモデルの第4層はトランスポート層で、エンドツーエンドの通信制御を行います。",
                "genre": "ネットワーク"
            },
            {
                "question_id": "SAMPLE004",
                "question_text": "データベースの正規化について、第1正規形の条件として正しいのはどれか。",
                "choices": {
                    "ア": "すべての非キー属性が主キーに完全関数従属している",
                    "イ": "すべての属性が原子値である",
                    "ウ": "推移的関数従属が存在しない",
                    "エ": "多値従属性が存在しない"
                },
                "correct_answer": "イ",
                "explanation": "第1正規形は、すべての属性が原子値（これ以上分割できない値）であることが条件です。",
                "genre": "データベース"
            },
            {
                "question_id": "SAMPLE005",
                "question_text": "プログラムの制御構造について、最も適切な説明はどれか。",
                "choices": {
                    "ア": "順次処理、選択処理、反復処理の3つが基本構造である",
                    "イ": "GOTO文を多用することで処理の流れが明確になる",
                    "ウ": "処理の分岐は2分岐までに制限すべきである",
                    "エ": "すべての処理は1つの関数で実装すべきである"
                },
                "correct_answer": "ア",
                "explanation": "構造化プログラミングでは、順次処理、選択処理（分岐）、反復処理（ループ）の3つが基本的な制御構造です。",
                "genre": "アルゴリズムとプログラミング"
            }
        ]
        
        saved_count = question_manager.save_questions(sample_questions)
        
        return jsonify({
            'message': f'{saved_count}問のサンプル問題を作成しました',
            'count': saved_count
        })
        
    except Exception as e:
        app.logger.error(f"Create sample error: {e}")
        return jsonify({'error': f'サンプルデータ作成中にエラーが発生しました: {str(e)}'}), 500

def ensure_admin_user():
    """最初のユーザーを管理者として設定"""
    try:
        # ユーザー数をチェック
        user_count = db_manager.execute_query('SELECT COUNT(*) as count FROM users')
        if user_count and user_count[0]['count'] == 0:
            print("初回起動: 管理者ユーザーを作成するには /register でユーザー登録してください")
        
        # 最初のユーザーがいれば管理者に設定
        if user_count and user_count[0]['count'] == 1:
            if db_manager.db_type == 'postgresql':
                db_manager.execute_query('UPDATE users SET is_admin = true WHERE id = 1')
            else:
                db_manager.execute_query('UPDATE users SET is_admin = 1 WHERE id = 1')
            print("最初のユーザーを管理者に設定しました")
            
    except Exception as e:
        print(f"管理者ユーザー設定エラー: {e}")

# 起動時に管理者ユーザーを確認
ensure_admin_user()