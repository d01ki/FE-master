"""
データベース診断・修復スクリプト
SQLite の状態確認とJSON問題の強制読み込み
"""

import sqlite3
import json
import os
from datetime import datetime

def diagnose_database():
    """データベースの状態を診断"""
    print("=" * 60)
    print("📊 データベース診断開始")
    print("=" * 60)
    
    db_path = 'fe_exam.db'
    
    # データベースファイルの存在確認
    if os.path.exists(db_path):
        print(f"✅ データベースファイル発見: {db_path}")
        file_size = os.path.getsize(db_path)
        print(f"📁 ファイルサイズ: {file_size:,} bytes")
    else:
        print(f"❌ データベースファイルが見つかりません: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # テーブル存在確認
        tables = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """).fetchall()
        
        print(f"\n📋 テーブル一覧:")
        for table in tables:
            print(f"  - {table[0]}")
        
        # questions テーブルの詳細
        if any(table[0] == 'questions' for table in tables):
            print(f"\n📚 questions テーブル詳細:")
            
            # レコード数
            count = conn.execute('SELECT COUNT(*) FROM questions').fetchone()[0]
            print(f"  総問題数: {count}")
            
            # ジャンル別統計
            genres = conn.execute("""
                SELECT genre, COUNT(*) as count 
                FROM questions 
                GROUP BY genre 
                ORDER BY count DESC
            """).fetchall()
            
            print(f"  ジャンル別問題数:")
            for genre_row in genres:
                print(f"    - {genre_row[0]}: {genre_row[1]}問")
            
            # サンプルレコード
            sample = conn.execute('SELECT * FROM questions LIMIT 3').fetchall()
            print(f"\n  サンプルレコード:")
            for i, record in enumerate(sample, 1):
                print(f"    {i}. ID: {record['id']}, question_id: {record['question_id']}")
                print(f"       ジャンル: {record['genre']}")
                print(f"       問題: {record['question_text'][:50]}...")
        
        # user_answers テーブルの詳細
        if any(table[0] == 'user_answers' for table in tables):
            print(f"\n📊 user_answers テーブル詳細:")
            
            # 解答履歴数
            answer_count = conn.execute('SELECT COUNT(*) FROM user_answers').fetchone()[0]
            print(f"  総解答数: {answer_count}")
            
            if answer_count > 0:
                # 正答率
                correct_count = conn.execute('SELECT COUNT(*) FROM user_answers WHERE is_correct = 1').fetchone()[0]
                accuracy = (correct_count / answer_count * 100) if answer_count > 0 else 0
                print(f"  正答率: {accuracy:.1f}% ({correct_count}/{answer_count})")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ データベース診断エラー: {e}")
        return False

def check_json_files():
    """JSONファイルの状態確認"""
    print("\n" + "=" * 60)
    print("📁 JSONファイル確認")
    print("=" * 60)
    
    json_folder = 'json_questions'
    
    if not os.path.exists(json_folder):
        print(f"❌ JSONフォルダが見つかりません: {json_folder}")
        return []
    
    json_files = []
    for filename in os.listdir(json_folder):
        if filename.endswith('.json'):
            filepath = os.path.join(json_folder, filename)
            try:
                file_size = os.path.getsize(filepath)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                json_files.append({
                    'filename': filename,
                    'filepath': filepath,
                    'size': file_size,
                    'question_count': len(data) if isinstance(data, list) else 0,
                    'data': data
                })
                
                print(f"✅ {filename}")
                print(f"   サイズ: {file_size:,} bytes")
                print(f"   問題数: {len(data) if isinstance(data, list) else '不明'}")
                
                if isinstance(data, list) and len(data) > 0:
                    sample = data[0]
                    required_fields = ['question_text', 'choices', 'correct_answer']
                    missing_fields = [field for field in required_fields if field not in sample]
                    if missing_fields:
                        print(f"   ⚠️  不足フィールド: {missing_fields}")
                    else:
                        print(f"   ✅ 形式OK")
                
            except Exception as e:
                print(f"❌ {filename}: エラー - {e}")
    
    return json_files

def force_load_json_to_db(json_files):
    """JSONファイルを強制的にデータベースに読み込み"""
    print("\n" + "=" * 60)
    print("🔄 JSONファイル強制読み込み")
    print("=" * 60)
    
    if not json_files:
        print("読み込むJSONファイルがありません")
        return
    
    db_path = 'fe_exam.db'
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        total_inserted = 0
        
        for json_file in json_files:
            print(f"\n📂 処理中: {json_file['filename']}")
            
            questions = json_file['data']
            if not isinstance(questions, list):
                print(f"   ❌ スキップ: データが配列ではありません")
                continue
            
            inserted_count = 0
            
            for i, question in enumerate(questions):
                try:
                    # 必須フィールドの確認
                    required_fields = ['question_text', 'choices', 'correct_answer']
                    if not all(field in question for field in required_fields):
                        print(f"   ⚠️  問題 {i+1}: 必須フィールドが不足")
                        continue
                    
                    # question_id がない場合は自動生成
                    question_id = question.get('question_id', f"Q{i+1:03d}")
                    
                    # 選択肢をJSON文字列に変換
                    choices_json = json.dumps(question['choices'], ensure_ascii=False)
                    
                    # 重複チェック
                    existing = conn.execute(
                        'SELECT id FROM questions WHERE question_id = ?',
                        (question_id,)
                    ).fetchone()
                    
                    if existing:
                        print(f"   🔄 更新: {question_id}")
                        conn.execute("""
                            UPDATE questions 
                            SET question_text = ?, choices = ?, correct_answer = ?, 
                                explanation = ?, genre = ?
                            WHERE question_id = ?
                        """, (
                            question['question_text'],
                            choices_json,
                            question['correct_answer'],
                            question.get('explanation', ''),
                            question.get('genre', 'その他'),
                            question_id
                        ))
                    else:
                        print(f"   ➕ 追加: {question_id}")
                        conn.execute("""
                            INSERT INTO questions 
                            (question_id, question_text, choices, correct_answer, explanation, genre) 
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            question_id,
                            question['question_text'],
                            choices_json,
                            question['correct_answer'],
                            question.get('explanation', ''),
                            question.get('genre', 'その他')
                        ))
                    
                    inserted_count += 1
                    
                except Exception as e:
                    print(f"   ❌ 問題 {i+1} エラー: {e}")
                    continue
            
            total_inserted += inserted_count
            print(f"   ✅ {inserted_count}問を処理完了")
        
        conn.commit()
        conn.close()
        
        print(f"\n🎉 合計 {total_inserted}問をデータベースに登録しました")
        
    except Exception as e:
        print(f"❌ データベース書き込みエラー: {e}")

def main():
    """メイン実行"""
    print("🔧 基本情報技術者試験アプリ - データベース診断・修復ツール")
    print(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. データベース診断
    db_ok = diagnose_database()
    
    # 2. JSONファイル確認
    json_files = check_json_files()
    
    # 3. JSONファイルを強制読み込み
    if json_files:
        print(f"\n❓ {len(json_files)}個のJSONファイルを強制読み込みしますか？ (y/N): ", end="")
        response = input().strip().lower()
        
        if response in ['y', 'yes']:
            force_load_json_to_db(json_files)
            print("\n🔄 再診断...")
            diagnose_database()
        else:
            print("読み込みをスキップしました")
    
    print("\n✅ 診断完了")

if __name__ == "__main__":
    main()
