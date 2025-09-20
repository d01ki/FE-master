# 📊 システムダイアグラム

## E-R図 (Entity-Relationship Diagram)

### データベース構造

```mermaid
erDiagram
    USERS ||--o{ USER_ANSWERS : "解答する"
    USERS ||--o{ MOCK_EXAM_RESULTS : "受験する"
    QUESTIONS ||--o{ USER_ANSWERS : "出題される"
    QUESTIONS ||--o{ MOCK_EXAM_QUESTIONS : "含まれる"
    MOCK_EXAMS ||--o{ MOCK_EXAM_RESULTS : "結果を持つ"
    MOCK_EXAMS ||--o{ MOCK_EXAM_QUESTIONS : "問題を持つ"
    MOCK_EXAM_RESULTS ||--o{ MOCK_EXAM_ANSWERS : "回答を持つ"

    USERS {
        integer id PK
        varchar username UK
        varchar password_hash
        boolean is_admin
        timestamp created_at
    }

    QUESTIONS {
        integer id PK
        varchar question_id UK
        text question_text
        json choices
        varchar correct_answer
        text explanation
        varchar genre
        varchar image_url
        json choice_images
        timestamp created_at
    }

    USER_ANSWERS {
        integer id PK
        integer user_id FK
        integer question_id FK
        varchar user_answer
        boolean is_correct
        timestamp answered_at
    }

    MOCK_EXAMS {
        integer id PK
        varchar exam_name UK
        text description
        integer time_limit
        timestamp created_at
    }

    MOCK_EXAM_RESULTS {
        integer id PK
        integer user_id FK
        integer exam_id FK
        integer score
        integer total_questions
        integer time_taken
        timestamp started_at
        timestamp completed_at
    }

    MOCK_EXAM_QUESTIONS {
        integer id PK
        integer exam_id FK
        integer question_id FK
        integer question_order
    }

    MOCK_EXAM_ANSWERS {
        integer id PK
        integer result_id FK
        integer question_id
        varchar user_answer
        boolean is_correct
        integer time_spent
    }
```

## インフラ構成図

### Renderデプロイ構成

```mermaid
flowchart TB
    User["👤 ユーザー<br/>ブラウザ"]
    
    subgraph Render["☁️ Render Platform"]
        App["🚀 Flask App<br/>Gunicorn"]
        DB[("💾 PostgreSQL")]
        Env["🔐 環境変数<br/>SECRET_KEY<br/>ADMIN_PASSWORD"]
    end
    
    Repo["📦 GitHub<br/>Repository"]
    
    User -->|HTTPS| App
    App -->|SQL| DB
    App -.->|読み込み| Env
    Repo -->|自動デプロイ| App
    
    style User fill:#90CAF9,stroke:#1976D2,stroke-width:3px,color:#000
    style App fill:#A5D6A7,stroke:#388E3C,stroke-width:3px,color:#000
    style DB fill:#FFE082,stroke:#F57C00,stroke-width:3px,color:#000
    style Env fill:#CE93D8,stroke:#7B1FA2,stroke-width:3px,color:#fff
    style Repo fill:#F48FB1,stroke:#C2185B,stroke-width:3px,color:#000
    style Render fill:#E3F2FD,stroke:#1976D2,stroke-width:2px,color:#000
```

## システムアーキテクチャ

```mermaid
flowchart TB
    subgraph Frontend["🎨 フロントエンド"]
        HTML["HTML5<br/>Jinja2"]
        CSS["Tailwind CSS"]
        JS["JavaScript"]
    end
    
    subgraph Backend["⚙️ バックエンド"]
        Flask["Flask"]
        Auth["認証システム"]
        Routes["ルーティング"]
    end
    
    subgraph Data["💾 データ層"]
        DBMgr["DB Manager"]
        PG[("PostgreSQL")]
    end
    
    HTML --> Flask
    CSS --> HTML
    JS --> HTML
    Flask --> Auth
    Flask --> Routes
    Routes --> DBMgr
    DBMgr --> PG
    
    style HTML fill:#90CAF9,stroke:#1976D2,stroke-width:2px,color:#000
    style CSS fill:#80DEEA,stroke:#0097A7,stroke-width:2px,color:#000
    style JS fill:#FFD54F,stroke:#FFA000,stroke-width:2px,color:#000
    style Flask fill:#A5D6A7,stroke:#388E3C,stroke-width:2px,color:#000
    style Auth fill:#EF9A9A,stroke:#D32F2F,stroke-width:2px,color:#000
    style Routes fill:#9FA8DA,stroke:#303F9F,stroke-width:2px,color:#fff
    style DBMgr fill:#CE93D8,stroke:#7B1FA2,stroke-width:2px,color:#fff
    style PG fill:#FFE082,stroke:#F57C00,stroke-width:2px,color:#000
    style Frontend fill:#E3F2FD,stroke:#1976D2,stroke-width:2px,color:#000
    style Backend fill:#E8F5E9,stroke:#388E3C,stroke-width:2px,color:#000
    style Data fill:#FFF3E0,stroke:#F57C00,stroke-width:2px,color:#000
```

## データフロー図

### ユーザー登録フロー

```mermaid
sequenceDiagram
    actor User as 👤 ユーザー
    participant Browser as 🌐 ブラウザ
    participant Flask as 🚀 Flask
    participant Auth as 🔐 認証
    participant DB as 💾 DB

    User->>Browser: 登録情報入力
    Browser->>Flask: POST /register
    Flask->>Auth: ユーザー名検証
    Auth->>DB: 重複チェック
    
    alt ユーザー名が利用可能
        Auth->>Auth: パスワードハッシュ化
        Auth->>DB: ユーザー作成
        DB-->>Auth: ✅ 成功
        Auth-->>Flask: 登録完了
        Flask-->>Browser: ログイン画面へ
        Browser-->>User: ログインページ表示
    else ユーザー名が既に存在
        Auth-->>Flask: ❌ エラー
        Flask-->>Browser: エラーメッセージ
        Browser-->>User: 再入力要求
    end
```

### 問題解答フロー

```mermaid
sequenceDiagram
    actor User as 👤 ユーザー
    participant Browser as 🌐 ブラウザ
    participant Flask as 🚀 Flask
    participant QM as 📚 問題管理
    participant DB as 💾 DB

    User->>Browser: 問題ページ
    Browser->>Flask: GET /practice
    Flask->>QM: 問題取得
    QM->>DB: SELECT
    DB-->>QM: 問題データ
    QM-->>Flask: 問題
    Flask-->>Browser: HTML
    Browser-->>User: 問題表示

    User->>Browser: 解答選択
    Browser->>Flask: POST /answer
    Flask->>QM: 解答チェック
    QM->>DB: 正解確認
    DB-->>QM: 正解データ
    QM->>DB: 履歴保存
    QM-->>Flask: 判定結果
    Flask-->>Browser: 結果JSON
    Browser-->>User: 正誤表示
```

### ランキング計算フロー

```mermaid
sequenceDiagram
    actor User as 👤 ユーザー
    participant Browser as 🌐 ブラウザ
    participant Flask as 🚀 Flask
    participant RS as 🏆 ランキング
    participant DB as 💾 DB

    User->>Browser: ランキングアクセス
    Browser->>Flask: GET /ranking
    Flask->>RS: ランキング取得
    RS->>DB: ユーザー統計取得
    DB-->>RS: 解答データ
    RS->>RS: スコア計算<br/>(正答率40%+解答量35%+活動度25%)
    RS->>RS: ランキングソート
    RS-->>Flask: ランキングデータ
    Flask-->>Browser: ランキングHTML
    Browser-->>User: ランキング表示
```

## 機能モジュール図

```mermaid
flowchart TB
    subgraph Core["🎯 コア"]
        App["app.py"]
        Config["config.py"]
        DB["database.py"]
        Auth["auth.py"]
    end
    
    subgraph Logic["🧠 ビジネスロジック"]
        QM["問題管理"]
        RS["ランキング"]
        AS["達成度"]
    end
    
    subgraph Routes["🛤️ ルート"]
        Main["メイン"]
        Practice["練習"]
        Exam["試験"]
        Admin["管理"]
        Ranking["順位"]
    end
    
    App --> Config
    App --> DB
    App --> Auth
    App --> Routes
    
    Routes --> Logic
    Logic --> DB
    
    style App fill:#90CAF9,stroke:#1976D2,stroke-width:2px,color:#000
    style Config fill:#A5D6A7,stroke:#388E3C,stroke-width:2px,color:#000
    style DB fill:#FFE082,stroke:#F57C00,stroke-width:2px,color:#000
    style Auth fill:#EF9A9A,stroke:#D32F2F,stroke-width:2px,color:#000
    style QM fill:#CE93D8,stroke:#7B1FA2,stroke-width:2px,color:#fff
    style RS fill:#9FA8DA,stroke:#303F9F,stroke-width:2px,color:#fff
    style AS fill:#80DEEA,stroke:#0097A7,stroke-width:2px,color:#000
    style Core fill:#E3F2FD,stroke:#1976D2,stroke-width:2px,color:#000
    style Logic fill:#F3E5F5,stroke:#7B1FA2,stroke-width:2px,color:#000
    style Routes fill:#E8F5E9,stroke:#388E3C,stroke-width:2px,color:#000
```

## テーブル説明

### 主要テーブル

| テーブル | 説明 | 主要カラム |
|---------|------|-----------|
| **USERS** | ユーザー情報 | username (ユニーク), password_hash, is_admin |
| **QUESTIONS** | 問題マスター | question_id (ユニーク), question_text, choices (JSON), correct_answer |
| **USER_ANSWERS** | 解答履歴 | user_id, question_id, is_correct, answered_at |
| **MOCK_EXAMS** | 過去問試験 | exam_name, description, time_limit |
| **MOCK_EXAM_RESULTS** | 試験結果 | user_id, exam_id, score, time_taken |

### リレーションシップ

- 1人のユーザーが複数の解答を持つ (1:N)
- 1つの問題が複数の解答を持つ (1:N)
- 1つの試験が複数の問題を持つ (M:N - MOCK_EXAM_QUESTIONS経由)
- 1つの試験結果が複数の解答詳細を持つ (1:N)

## スケーリング構成（将来対応）

```mermaid
flowchart TB
    LB["⚖️ Load Balancer"]
    
    subgraph Apps["Application Instances"]
        App1["🚀 Instance 1"]
        App2["🚀 Instance 2"]
        App3["🚀 Instance N"]
    end
    
    Primary[("💾 Primary DB")]
    
    LB --> App1
    LB --> App2
    LB --> App3
    
    App1 --> Primary
    App2 --> Primary
    App3 --> Primary
    
    style LB fill:#64B5F6,stroke:#1976D2,stroke-width:3px,color:#000
    style App1 fill:#81C784,stroke:#388E3C,stroke-width:2px,color:#000
    style App2 fill:#81C784,stroke:#388E3C,stroke-width:2px,color:#000
    style App3 fill:#81C784,stroke:#388E3C,stroke-width:2px,color:#000
    style Primary fill:#FFD54F,stroke:#F57C00,stroke-width:3px,color:#000
    style Apps fill:#E8F5E9,stroke:#388E3C,stroke-width:2px,color:#000
```
