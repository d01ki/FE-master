def test_create_app_with_temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("ADMIN_PASSWORD", "test-admin-password")
    import importlib.util
    import pathlib

    app_path = pathlib.Path(__file__).resolve().parents[1] / "app.py"
    spec = importlib.util.spec_from_file_location("app_main", app_path)
    app_module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(app_module)

    flask_app = app_module.create_app()

    assert flask_app is not None
    assert flask_app.config.get("DATABASE_URL") == f"sqlite:///{db_path}"
    assert flask_app.secret_key
