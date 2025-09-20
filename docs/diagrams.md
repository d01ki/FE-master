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
graph TB
    subgraph "ユーザー"
        User["👤 ユーザー<br/>ブラウザ"]
    end

    subgraph "Render Platform"
        subgraph "Web Service"
            App["🚀 Flask App<br/>Python 3.12<br/>Gunicorn"]
            Static["📸 Static Files<br/>CSS/JS/Images"]
        end

        subgraph "Database Service"
            DB[("💾 PostgreSQL<br/>Database")]
        end

        subgraph "Environment"
            Env["🔑 Environment Variables<br/>SECRET_KEY<br/>ADMIN_PASSWORD<br/>DATABASE_URL"]
        end
    end

    subgraph "GitHub"
        Repo["📁 GitHub Repository<br/>Source Code"]
    end

    User -->|HTTPS| App
    App -->|SQL Query| DB
    App -->|Load Config| Env
    App -->|Serve| Static
    Repo -->|Auto Deploy| App
    
    style User fill:#e1f5fe
    style App fill:#c8e6c9
    style DB fill:#fff9c4
    style Env fill:#ffe0b2
    style Repo fill:#f3e5f5
```

## システムアーキテクチャ

```mermaid
graph TB
    subgraph "Frontend Layer"
        HTML["📝 HTML5<br/>Jinja2 Templates"]
        CSS["🎨 Tailwind CSS<br/>Responsive Design"]
        JS["⚡ JavaScript<br/>Alpine.js"]
    end

    subgraph "Application Layer"
        Flask["🐍 Flask Framework"]
        Auth["🔐 Authentication<br/>Session Management"]
        Routes["🛤️ Routes & Blueprints"]
        Business["🧠 Business Logic"]
    end

    subgraph "Data Layer"
        DBManager["🔗 Database Manager"]
        DB[("💾 PostgreSQL/SQLite")]
    end

    HTML --> Flask
    CSS --> HTML
    JS --> HTML
    Flask --> Auth
    Flask --> Routes
    Routes --> Business
    Business --> DBManager
    DBManager --> DB

    style HTML fill:#e3f2fd
    style CSS fill:#f3e5f5
    style JS fill:#fff3e0
    style Flask fill:#c8e6c9
    style Auth fill:#ffcdd2
    style Routes fill:#b2dfdb
    style Business fill:#d1c4e9
    style DBManager fill:#ffecb3
    style DB fill:#fff9c4
```

## データフロー図

### ユーザー登録・ログインフロー

```mermaid
sequenceDiagram
    participant User
    participant Browser
    participant Flask
    participant Auth
    participant DB

    User->>Browser: 登録情報入力
    Browser->>Flask: POST /register
    Flask->>Auth: ユーザー名検証
    Auth->>DB: 重複チェック
    DB-->>Auth: 結果
    
    alt ユーザー名が利用可能
        Auth->>Auth: パスワードハッシュ化
        Auth->>DB: ユーザー作成
        DB-->>Auth: 成功
        Auth-->>Flask: 登録完了
        Flask-->>Browser: リダイレクト(ログイン)
        Browser-->>User: ログイン画面表示
    else ユーザー名が既に存在
        Auth-->>Flask: エラー
        Flask-->>Browser: エラーメッセージ
        Browser-->>User: 再入力要求
    end
```

### 問題解答フロー

```mermaid
sequenceDiagram
    participant User
    participant Browser
    participant Flask
    participant QM as Question Manager
    participant DB

    User->>Browser: 問題画面アクセス
    Browser->>Flask: GET /practice/random
    Flask->>QM: ランダム問題取得
    QM->>DB: SELECT問題
    DB-->>QM: 問題データ
    QM-->>Flask: 問題
    Flask-->>Browser: 問題HTML
    Browser-->>User: 問題表示

    User->>Browser: 解答選択
    Browser->>Flask: POST /answer
    Flask->>QM: 解答チェック
    QM->>DB: 正解確認
    DB-->>QM: 正解データ
    QM->>QM: 正誤判定
    QM->>DB: 解答履歴保存
    DB-->>QM: 保存完了
    QM-->>Flask: 判定結果
    Flask-->>Browser: 結果JSON
    Browser-->>User: 正誤表示
```

### ランキング計算フロー

```mermaid
sequenceDiagram
    participant User
    participant Browser
    participant Flask
    participant RS as Ranking System
    participant DB

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

## デプロイメントフロー

```mermaid
graph LR
    A["💻 Git Commit"] --> B["📤 Git Push"]
    B --> C["🐙 GitHub"]
    C --> D["🔔 Webhook"]
    D --> E["🔧 Render Build"]
    E --> F["📦 Install Dependencies"]
    F --> G["🗄️ Database Migration"]
    G --> H["🚀 Deploy"]
    H --> I["✅ Live Service"]

    style A fill:#e1f5fe
    style B fill:#f3e5f5
    style C fill:#fff3e0
    style D fill:#ffccbc
    style E fill:#c8e6c9
    style F fill:#b2dfdb
    style G fill:#ffecb3
    style H fill:#a5d6a7
    style I fill:#81c784
```

## セキュリティ層

```mermaid
graph TB
    subgraph "セキュリティ対策"
        HTTPS["🔒 HTTPS通信"]
        Session["🎫 Session管理"]
        Hash["🔐 パスワードハッシュ化"]
        Env["📦 環境変数分離"]
        Validation["✅ 入力検証"]
        CSRF["🛡️ CSRF対策"]
    end

    User["👤 ユーザー"] --> HTTPS
    HTTPS --> Session
    Session --> Hash
    Hash --> Validation
    Validation --> CSRF
    CSRF --> Env

    style HTTPS fill:#ffcdd2
    style Session fill:#f8bbd0
    style Hash fill:#e1bee7
    style Validation fill:#d1c4e9
    style CSRF fill:#c5cae9
    style Env fill:#bbdefb
```

## 機能モジュール図

```mermaid
graph TB
    subgraph "Core Modules"
        App["app.py<br/>アプリケーション"] 
        Config["config.py<br/>設定管理"]
        DB["database.py<br/>DB接続"]
        Auth["auth.py<br/>認証"]
    end

    subgraph "Business Logic"
        QM["question_manager.py<br/>問題管理"]
        RS["ranking_system.py<br/>ランキング"]
        AS["achievement_system.py<br/>達成度"]
    end

    subgraph "Routes"
        Main["main_routes.py"]
        Practice["practice_routes.py"]
        Exam["exam_routes.py"]
        Admin["admin_routes.py"]
        Ranking["ranking_routes.py"]
    end

    App --> Config
    App --> DB
    App --> Auth
    App --> Main
    App --> Practice
    App --> Exam
    App --> Admin
    App --> Ranking
    
    Main --> QM
    Practice --> QM
    Exam --> QM
    Ranking --> RS
    Ranking --> AS

    QM --> DB
    RS --> DB
    AS --> DB

    style App fill:#4fc3f7
    style Config fill:#81c784
    style DB fill:#ffb74d
    style Auth fill:#e57373
```

## スケーリング構成（将来対応）

```mermaid
graph TB
    subgraph "Load Balancer"
        LB["⚖️ Render Load Balancer"]
    end

    subgraph "Application Tier"
        App1["🚀 Instance 1"]
        App2["🚀 Instance 2"]
        App3["🚀 Instance N"]
    end

    subgraph "Database Tier"
        Primary[("💾 Primary DB")]
        Replica1[("💾 Replica 1")]
        Replica2[("💾 Replica 2")]
    end

    subgraph "Cache Layer"
        Redis["⚡ Redis Cache"]
    end

    LB --> App1
    LB --> App2
    LB --> App3

    App1 --> Redis
    App2 --> Redis
    App3 --> Redis

    App1 --> Primary
    App2 --> Primary
    App3 --> Primary

    Primary -.-> Replica1
    Primary -.-> Replica2

    style LB fill:#4fc3f7
    style App1 fill:#81c784
    style App2 fill:#81c784
    style App3 fill:#81c784
    style Primary fill:#ffb74d
    style Replica1 fill:#ffb74d,stroke-dasharray: 5 5
    style Replica2 fill:#ffb74d,stroke-dasharray: 5 5
    style Redis fill:#e57373
```
