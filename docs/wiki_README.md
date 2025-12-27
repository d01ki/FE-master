# Wiki: システム概要とDB構造

## DB構造（ER 図）
以下は MySQL/SQLite 共通のテーブル構成です。

```mermaid
erDiagram
    users {
        int id PK
        varchar username UNIQUE
        varchar password_hash
        boolean is_admin
        datetime created_at
    }

    questions {
        int id PK
        varchar question_id UNIQUE
        text question_text
        json choices
        varchar correct_answer
        text explanation
        varchar genre
        varchar image_url
        json choice_images
        datetime created_at
    }

    user_answers {
        int id PK
        int user_id FK
        int question_id FK
        varchar user_answer
        boolean is_correct
        datetime answered_at
    }

    user_stats {
        int id PK
        int user_id UNIQUE FK
        int total_answers
        int correct_answers
        decimal accuracy_rate
        datetime last_answered_at
    }

    users ||--o{ user_answers : "answers"
    questions ||--o{ user_answers : "is answered in"
    users ||--o| user_stats : "aggregated into"
```

### テーブル概要
- users: 認証情報と権限を保持（username は一意）。
- questions: 問題本文と選択肢（choices は JSON 文字列）、画像 URL を保持。
- user_answers: ユーザーごとの解答履歴。
- user_stats: 解答履歴から集計した総解答数・正解数・正答率・最終解答日時（回答保存時に更新、起動時に再計算）。

## システム全体構造
アプリの主要コンポーネントと依存関係を簡易図で示します。

```mermaid
graph TD
    subgraph Client
        A[Browser]
    end

    subgraph Backend[Flask App]
        B[Routes/Blueprints\n(main, practice, exam, admin, upload, auth)]
        C[Auth & Session\n(app/core/auth.py)]
        D[QuestionManager\n(app/core/question_manager.py)]
        E[DatabaseManager\n(app/core/database.py)]
        F[Templates & Static\n(app/templates, app/static)]
    end

    subgraph Data
        G[(MySQL / SQLite)]
        H[JSON Sources\n(json_questions/*.json)]
        I[Uploads\n/uploads]
    end

    A -->|HTTP| B
    B --> C
    B --> D
    B --> F
    D --> E
    C --> E
    E --> G
    D --> H
    B --> I
```

### 補足
- DB はデフォルトで MySQL（docker-compose の `db` サービス）。pymysql が無い場合は SQLite にフォールバック。
- 初回起動時にテーブルを作成し、サンプル問題 JSON を読み込んで挿入。
- 回答保存ごとに `user_stats` を更新し、ランキングで参照。
- コンテナ構成: `app` (Flask) + `db` (MySQL)。ローカル開発ではボリュームマウントでホットリロード。
