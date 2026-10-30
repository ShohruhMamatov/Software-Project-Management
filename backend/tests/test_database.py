from unittest.mock import MagicMock

from app import database
from app.config import Settings


def test_get_db_yields_session_and_closes_it(monkeypatch):
    session = MagicMock()
    monkeypatch.setattr(database, "SessionLocal", lambda: session)

    dependency = database.get_db()

    assert next(dependency) is session
    session.close.assert_not_called()
    dependency.close()
    session.close.assert_called_once()


def test_settings_read_environment(monkeypatch):
    monkeypatch.setenv("CAMERA_ONLINE_SECONDS", "5")

    assert Settings(_env_file=None).camera_online_seconds == 5
