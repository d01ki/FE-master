import json
from contextlib import contextmanager

import pytest
from werkzeug.security import generate_password_hash


def make_app(monkeypatch, tmp_path):
    # テスト用に一時DBへ向ける（MySQL環境が無い場合でも自己完結させる）
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("ADMIN_PASSWORD", "adminpass")
    monkeypatch.setenv("ADMIN_USERNAME", "admin")

    import importlib.util
    import pathlib
    import importlib

    # Configを環境変数で再読み込みし、古いDBファイルを消してクリーンにする
    from app.core import config as config_module

    importlib.reload(config_module)
    if db_path.exists():
        db_path.unlink()

    app_path = pathlib.Path(__file__).resolve().parents[1] / "app.py"
    spec = importlib.util.spec_from_file_location("app_main", app_path)
    app_module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(app_module)
    app = app_module.create_app()
    return app


def seed_users(db_manager):
    db_manager.execute_query("DELETE FROM users")
    db_manager.execute_query(
        "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)",
        ("admin_db", generate_password_hash("admin_db_pass"), 1),
    )
    db_manager.execute_query(
        "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)",
        ("user1", generate_password_hash("user1pass"), 0),
    )
    db_manager.execute_query(
        "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)",
        ("admin2", generate_password_hash("admin2pass"), 1),
    )


def seed_question(db_manager):
    db_manager.execute_query("DELETE FROM questions")
    choices = json.dumps({"A": "選択肢A", "B": "選択肢B", "C": "選択肢C", "D": "選択肢D"})
    db_manager.execute_query(
        """
        INSERT INTO questions (question_id, question_text, choices, correct_answer, explanation, genre)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("Q1", "サンプル問題", choices, "A", "サンプル解説", "ネットワーク"),
    )


@pytest.fixture()
def app_client(monkeypatch, tmp_path):
    app = make_app(monkeypatch, tmp_path)
    with app.app_context():
        seed_users(app.db_manager)
        seed_question(app.db_manager)
    client = app.test_client()
    return app, client


@contextmanager
def admin_session(client, user_id):
    with client.session_transaction() as sess:
        sess["admin_logged_in"] = True
        sess["user_id"] = user_id
    yield


def login_user(client, username, password):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def test_auth_login_logout(app_client):
    app, client = app_client

    res = login_user(client, "user1", "user1pass")
    assert res.status_code == 200
    # ダッシュボードへリダイレクト済みかの緩い確認
    assert b"dashboard" in res.data or "ようこそ".encode() in res.data

    res = client.get("/logout", follow_redirects=True)
    assert res.status_code == 200
    assert "ログアウト".encode() in res.data


def test_admin_toggle_and_delete_guards(app_client):
    app, client = app_client
    db = app.db_manager

    admin_id = db.execute_query("SELECT id FROM users WHERE username = ?", ("admin_db",))[0]["id"]
    user1_id = db.execute_query("SELECT id FROM users WHERE username = ?", ("user1",))[0]["id"]
    admin2_id = db.execute_query("SELECT id FROM users WHERE username = ?", ("admin2",))[0]["id"]

    with admin_session(client, admin_id):
        res = client.post(f"/admin/users/{admin_id}/toggle-admin", follow_redirects=True)
        assert res.status_code == 200
        assert "自分自身の管理者権限は変更できません".encode() in res.data

        res = client.post(f"/admin/users/{admin2_id}/delete", follow_redirects=True)
        assert res.status_code == 200
        assert "管理者アカウントは削除できません".encode() in res.data

        res = client.post(f"/admin/users/{user1_id}/toggle-admin", follow_redirects=True)
        assert res.status_code == 200
        assert "管理者権限を付与".encode() in res.data

        user1 = db.execute_query("SELECT is_admin FROM users WHERE id = ?", (user1_id,))
        assert user1[0]["is_admin"] == 1

        res = client.post(f"/admin/users/{admin_id}/delete", follow_redirects=True)
        assert res.status_code == 200
        assert "自分自身を削除することはできません".encode() in res.data


def test_main_pages_status(app_client):
    app, client = app_client

    login_user(client, "user1", "user1pass")

    paths = [
        "/dashboard",
        "/practice/random",
        "/practice/genre",
        "/practice/genre/ネットワーク",
        "/mock_exam",
        "/history",
    ]

    for path in paths:
        res = client.get(path)
        assert res.status_code == 200


def test_mysql_random_sql_generation():
    from tests.test_question_manager import DummyDB
    from app.core.question_manager import QuestionManager

    db = DummyDB(db_type="mysql")
    db.next_result = [
        {
            "id": 1,
            "choices": "{}",
            "question_id": "q1",
            "question_text": "t",
            "correct_answer": "A",
            "explanation": "",
            "image_url": None,
            "choice_images": None,
            "genre": None,
        }
    ]
    qm = QuestionManager(db)
    qm.get_random_question()
    assert "RAND()" in db.captured_query
