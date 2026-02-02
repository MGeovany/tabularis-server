def test_import_app() -> None:
    from app.main import app

    assert app is not None
