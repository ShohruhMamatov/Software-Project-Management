import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.models import User
from tests.conftest import postgres_only
from tests.helpers import create_event

pytestmark = postgres_only


def execute(session_factory, sql, **params):
    with session_factory() as db:
        result = db.execute(text(sql), params)
        db.commit()
        return result


def test_deleting_store_cascades_to_cameras_zones_and_events(client, owner, camera, session_factory):
    create_event(client, owner, camera["id"])

    execute(session_factory, "DELETE FROM stores WHERE id = :id", id=owner["store_id"])

    with session_factory() as db:
        assert db.execute(text("SELECT count(*) FROM cameras")).scalar() == 0
        assert db.execute(text("SELECT count(*) FROM events")).scalar() == 0
        assert db.query(User).one().store_id is None


def test_deleting_reviewer_keeps_event(client, owner, camera, session_factory):
    event = create_event(client, owner, camera["id"])
    client.post(f"/events/{event['id']}/review", json={"status": "confirmed"}, headers=owner["headers"])

    execute(session_factory, "DELETE FROM users")

    with session_factory() as db:
        assert db.execute(text("SELECT reviewed_by FROM events")).scalar() is None


def test_event_status_check_constraint_rejects_unknown_value(client, owner, camera, session_factory):
    create_event(client, owner, camera["id"])

    with pytest.raises(IntegrityError):
        execute(session_factory, "UPDATE events SET status = 'maybe'")


def test_user_email_is_unique_in_database(client, owner, session_factory):
    with pytest.raises(IntegrityError):
        execute(
            session_factory,
            "INSERT INTO users (email, password_hash, role, is_active) VALUES ('owner@lumi.uz', 'x', 'owner', true)",
        )
