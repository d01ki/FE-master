#!/usr/bin/env python3
"""
サンプルデータ投入スクリプト
基本情報技術者試験のサンプル問題をデータベースに投入します。
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.models.user import User
from app.models.problem import Problem
from app.core.security import get_password_hash
from app.services.similarity import update_problem_embedding

# サンプル問題データ
SAMPLE_PROBLEMS = [
    {
        "source": "FE",
        "year": 2023,
        "exam_session": "autumn",
        "question_no": "Q1",
        "text_md": """
# コンピュータシステムの性能指標

コンピュータシステムの性能を表す指標である **スループット** に関する説明として、最も適切なものはどれか。
        """,
        "choices_json": {
            "a": "単位時間当たりに処理できるジョブ数であり、値が大きいほど性能が高い。",
            "b": "ジョブの到着から処理終了までの平均的な時間であり、値が小さいほど性能が高い。",
            "c": "システムが単位時間当たりに処理できるデータ量であり、値が大きいほど性能が高い。",
            "d": "システムが連続して動作する時間の割合であり、値が大きいほど性能が高い。"
        },
        "answer_index": 0,
        "explanation_md": """
**正解：a**

スループット（Throughput）は、単位時間当たりに処理できるジョブ数を表す性能指標です。

- **a：正解** - スループットの定義そのもの
- **b** - レスポンスタイムの説明
- **c** - 帯域幅の説明
- **d** - 可用率の説明
        """,
        "tags": ["システム性能", "スループット"],
        "difficulty": 0.3,
        "category": "システム構成要素"
    },
    {
        "source": "FE",
        "year": 2023,
        "exam_session": "autumn",
        "question_no": "Q10",
        "text_md": """
# データベースの正規化

関係データベースの正規化に関する説明として、適切なものはどれか。
        """,
        "choices_json": {
            "a": "第1正規形では、繰り返しグループを除去し、テーブルを分割する。",
            "b": "第2正規形では、非キー属性の一部に対する関数従属性を除去する。",
            "c": "第3正規形では、推移的関数従属性を除去する。",
            "d": "正規化を行うことで、データの一貫性が保たれ、更新異常を防ぐことができる。"
        },
        "answer_index": 3,
        "explanation_md": """
**正解：d**

データベースの正規化の目的は、データの一貫性を保ち、更新異常を防ぐことです。

- **a** - 第1正規形の説明が不正確
- **b** - 第2正規形の説明が不正確
- **c** - 第3正規形の説明が不正確
- **d：正解** - 正規化の目的を正しく説明
        """,
        "tags": ["データベース", "正規化"],
        "difficulty": 0.5,
        "category": "データベース"
    },
    {
        "source": "FE",
        "year": 2023,
        "exam_session": "spring",
        "question_no": "Q25",
        "text_md": """
# ネットワークプロトコル

TCP/IPモデルのトランスポート層で動作するプロトコルはどれか。
        """,
        "choices_json": {
            "a": "HTTP",
            "b": "IP",
            "c": "TCP",
            "d": "Ethernet"
        },
        "answer_index": 2,
        "explanation_md": """
**正解：c (TCP)**

TCP/IPモデルの各層と主要プロトコル：

- **アプリケーション層**: HTTP, HTTPS, FTP, SMTPなど
- **トランスポート層**: **TCP, UDP**
- **インターネット層**: IP, ICMPなど
- **ネットワークアクセス層**: Ethernet, Wi-Fiなど
        """,
        "tags": ["ネットワーク", "TCP/IP", "プロトコル"],
        "difficulty": 0.4,
        "category": "ネットワーク"
    },
    {
        "source": "FE",
        "year": 2023,
        "exam_session": "spring",
        "question_no": "Q35",
        "text_md": """
# アルゴリズムの計算量

データ数nのソートアルゴリズムの中で、最悪計算量O(n log n)を持つものはどれか。
        """,
        "choices_json": {
            "a": "バブルソート",
            "b": "選択ソート",
            "c": "マージソート",
            "d": "挿入ソート"
        },
        "answer_index": 2,
        "explanation_md": """
**正解：c (マージソート)**

各ソートアルゴリズムの時間計算量：

- **バブルソート**: O(n²)
- **選択ソート**: O(n²)
- **マージソート**: **O(n log n)** - 最悪でもこの計算量
- **挿入ソート**: O(n²)

マージソートは分割統治法を使用し、常にO(n log n)の時間計算量を保証します。
        """,
        "tags": ["アルゴリズム", "ソート", "計算量"],
        "difficulty": 0.6,
        "category": "アルゴリズム"
    },
    {
        "source": "FE",
        "year": 2023,
        "exam_session": "autumn",
        "question_no": "Q50",
        "text_md": """
# 情報セキュリティ

ファイアウォールの機能として、最も適切なものはどれか。
        """,
        "choices_json": {
            "a": "ネットワーク上を流れるパケットを監視し、不正なアクセスを検知する。",
            "b": "ネットワーク間でやり取りされるデータを暗号化する。",
            "c": "事前に定められたルールに基づいて、パケットの通過を制御する。",
            "d": "ウイルスやマルウェアを検知し、除去する。"
        },
        "answer_index": 2,
        "explanation_md": """
**正解：c**

ファイアウォールの主な機能は、事前に定められたルールに基づいてパケットの通過を制御することです。

- **a** - IDS/IPSの機能
- **b** - VPNやSSL/TLSの機能
- **c：正解** - ファイアウォールの基本機能
- **d** - アンチウイルスソフトの機能
        """,
        "tags": ["セキュリティ", "ファイアウォール"],
        "difficulty": 0.4,
        "category": "セキュリティ"
    }
]

def create_sample_user(db: Session):
    """サンプルユーザー作成"""
    # テストユーザーの作成
    test_user = User(
        email="test@example.com",
        password_hash=get_password_hash("password123"),
        display_name="テストユーザー",
        is_admin=True
    )
    
    # 既存ユーザーの確認
    existing_user = db.query(User).filter(User.email == test_user.email).first()
    if not existing_user:
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        print(f"テストユーザーを作成しました: {test_user.email}")
        return test_user
    else:
        print(f"テストユーザーは既に存在します: {existing_user.email}")
        return existing_user

def create_sample_problems(db: Session):
    """サンプル問題作成"""
    created_count = 0
    
    for problem_data in SAMPLE_PROBLEMS:
        # 既存問題の確認
        existing_problem = db.query(Problem).filter(
            Problem.source == problem_data["source"],
            Problem.year == problem_data["year"],
            Problem.exam_session == problem_data["exam_session"],
            Problem.question_no == problem_data["question_no"]
        ).first()
        
        if not existing_problem:
            problem = Problem(**problem_data)
            db.add(problem)
            db.commit()
            db.refresh(problem)
            
            # 埋め込み生成（OpenAI APIキーが設定されている場合）
            try:
                update_problem_embedding(db, problem)
                print(f"問題を作成しました: {problem.source} {problem.year} {problem.question_no}")
            except Exception as e:
                print(f"埋め込み生成に失敗しました ({problem.question_no}): {e}")
            
            created_count += 1
        else:
            print(f"問題は既に存在します: {problem_data['source']} {problem_data['year']} {problem_data['question_no']}")
    
    print(f"\n{created_count}個の新しい問題を作成しました。")

def main():
    """メイン処理"""
    print("サンプルデータの投入を開始します...")
    
    # データベースセッション作成
    db = SessionLocal()
    
    try:
        # サンプルユーザー作成
        user = create_sample_user(db)
        
        # サンプル問題作成
        create_sample_problems(db)
        
        print("\nサンプルデータの投入が完了しました。")
        print("\n使用方法:")
        print("1. バックエンドサーバーを起動: uvicorn app.main:app --reload")
        print("2. ブラウザで http://localhost:8000/docs にアクセス")
        print("3. /api/v1/auth/login でログイン（test@example.com / password123）")
        print("4. /api/v1/problems で問題一覧を取得")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
