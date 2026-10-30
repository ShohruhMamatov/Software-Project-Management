from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.config import settings
from app.models import Camera, Event, Zone
from app.routers.cameras import is_online
from tests.conftest import xfail_on_postgres
from tests.helpers import (
    CAMERA_PASSWORD,
    CLIP,
    FAKE_JPEG,
    SNAPSHOT,
    TRIANGLE,
    agent_key,
    camera_body,
    create_camera,
    create_event,
    heartbeat,
    media_files,
)

BUG_LONG_PASSWORD = "SCRUM-61: encrypted password does not fit String(512): 500"


def agent_camera(client, owner, camera_id):
    cameras = client.get("/agent/config", headers=agent_key(owner["api_key"])).json()["cameras"]
    return next(c for c in cameras if c["id"] == camera_id)


def test_create_camera_returns_masked_urls(client, owner):
    response = client.post("/cameras", json=camera_body(channel=3, port=8554), headers=owner["headers"])

    assert response.status_code == 201
    body = response.json()
    assert body["rtsp_url_sub"] == "rtsp://admin:****@192.168.1.64:8554/Streaming/Channels/302"
    assert body["rtsp_url_main"] == "rtsp://admin:****@192.168.1.64:8554/Streaming/Channels/301"


def test_create_camera_applies_defaults(camera):
    assert camera["port"] == 554
    assert camera["channel"] == 1
    assert camera["threshold"] == 0.5
    assert camera["is_active"] is True
    assert camera["online"] is False
    assert camera["has_snapshot"] is False
    assert camera["last_seen_at"] is None


def test_create_camera_encrypts_password(camera, session_factory):
    with session_factory() as db:
        stored = db.get(Camera, camera["id"]).rtsp_password_encrypted

    assert CAMERA_PASSWORD not in stored


@xfail_on_postgres(BUG_LONG_PASSWORD)
def test_create_camera_longest_unicode_password_is_stored(client, owner):
    response = client.post("/cameras", json=camera_body(rtsp_password="😀" * 128), headers=owner["headers"])

    assert response.status_code == 201


def test_list_cameras_returns_store_cameras_in_id_order(client, owner):
    first = create_camera(client, owner, name="First")
    second = create_camera(client, owner, name="Second")

    response = client.get("/cameras", headers=owner["headers"])

    assert response.status_code == 200
    assert [c["id"] for c in response.json()] == [first["id"], second["id"]]


def test_get_camera_returns_it(client, owner, camera):
    response = client.get(f"/cameras/{camera['id']}", headers=owner["headers"])

    assert response.status_code == 200
    assert response.json()["name"] == "Entrance"


def test_get_unknown_camera_is_404(client, owner):
    assert client.get("/cameras/99999", headers=owner["headers"]).status_code == 404


def test_update_camera_channel_updates_urls(client, owner, camera):
    response = client.patch(f"/cameras/{camera['id']}", json={"channel": 5}, headers=owner["headers"])

    assert response.status_code == 200
    assert response.json()["channel"] == 5
    assert response.json()["rtsp_url_sub"].endswith("/Streaming/Channels/502")


def test_update_camera_empty_body_changes_nothing(client, owner, camera):
    response = client.patch(f"/cameras/{camera['id']}", json={}, headers=owner["headers"])

    assert response.status_code == 200
    assert response.json() == camera


def test_update_camera_null_fields_are_ignored(client, owner, camera):
    response = client.patch(
        f"/cameras/{camera['id']}", json={"name": None, "rtsp_password": None}, headers=owner["headers"]
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Entrance"
    assert "p%40ss" in agent_camera(client, owner, camera["id"])["rtsp_url_sub"]


def test_update_camera_password_changes_agent_url_only(client, owner, camera):
    response = client.patch(f"/cameras/{camera['id']}", json={"rtsp_password": "n3w@pw"}, headers=owner["headers"])

    assert response.status_code == 200
    assert response.json() == camera
    assert "n3w%40pw" in agent_camera(client, owner, camera["id"])["rtsp_url_sub"]
    assert "p%40ss" not in agent_camera(client, owner, camera["id"])["rtsp_url_sub"]


def test_update_camera_can_deactivate(client, owner, camera):
    response = client.patch(f"/cameras/{camera['id']}", json={"is_active": False}, headers=owner["headers"])

    assert response.json()["is_active"] is False


def test_update_camera_threshold_can_be_zero(client, owner, camera):
    response = client.patch(f"/cameras/{camera['id']}", json={"threshold": 0}, headers=owner["headers"])

    assert response.json()["threshold"] == 0


def test_update_unknown_camera_is_404(client, owner):
    assert client.patch("/cameras/99999", json={"name": "x"}, headers=owner["headers"]).status_code == 404


def test_delete_camera_removes_it(client, owner, camera):
    response = client.delete(f"/cameras/{camera['id']}", headers=owner["headers"])

    assert response.status_code == 204
    assert client.get(f"/cameras/{camera['id']}", headers=owner["headers"]).status_code == 404


def test_delete_unknown_camera_is_404(client, owner):
    assert client.delete("/cameras/99999", headers=owner["headers"]).status_code == 404


def test_delete_camera_removes_events_zones_and_files(client, owner, camera, session_factory):
    camera_id = camera["id"]
    client.put(f"/cameras/{camera_id}/zones", json=[{"type": "exit", "polygon": TRIANGLE}], headers=owner["headers"])
    heartbeat(client, owner["api_key"], camera_id, snapshot=SNAPSHOT)
    create_event(client, owner, camera_id, clip=CLIP, snapshot=SNAPSHOT)
    assert len(media_files()) == 3

    client.delete(f"/cameras/{camera_id}", headers=owner["headers"])

    assert media_files() == []
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Event)) == 0
        assert db.scalar(select(func.count()).select_from(Zone)) == 0


def test_delete_camera_keeps_other_camera_files(client, owner, camera):
    other = create_camera(client, owner, name="Other")
    heartbeat(client, owner["api_key"], other["id"], snapshot=SNAPSHOT)
    create_event(client, owner, other["id"], clip=CLIP)

    client.delete(f"/cameras/{camera['id']}", headers=owner["headers"])

    assert len(media_files()) == 2


def test_delete_camera_with_missing_files_still_works(client, owner, camera):
    create_event(client, owner, camera["id"], clip=CLIP, snapshot=SNAPSHOT)
    for path in media_files():
        path.unlink()

    assert client.delete(f"/cameras/{camera['id']}", headers=owner["headers"]).status_code == 204


def test_camera_snapshot_without_heartbeat_is_404(client, owner, camera):
    assert client.get(f"/cameras/{camera['id']}/snapshot", headers=owner["headers"]).status_code == 404


def test_camera_snapshot_returns_latest_frame(client, owner, camera):
    heartbeat(client, owner["api_key"], camera["id"], snapshot=SNAPSHOT)

    response = client.get(f"/cameras/{camera['id']}/snapshot", headers=owner["headers"])

    assert response.status_code == 200
    assert response.content == FAKE_JPEG
    assert response.headers["content-type"] == "image/jpeg"


def test_camera_snapshot_file_missing_on_disk_is_404(client, owner, camera):
    heartbeat(client, owner["api_key"], camera["id"], snapshot=SNAPSHOT)
    media_files()[0].unlink()

    assert client.get(f"/cameras/{camera['id']}/snapshot", headers=owner["headers"]).status_code == 404


def test_camera_is_online_after_heartbeat(client, owner, camera):
    heartbeat(client, owner["api_key"], camera["id"])

    assert client.get(f"/cameras/{camera['id']}", headers=owner["headers"]).json()["online"] is True


def test_camera_is_offline_when_last_seen_is_too_old(client, owner, camera, monkeypatch):
    heartbeat(client, owner["api_key"], camera["id"])
    monkeypatch.setattr(settings, "camera_online_seconds", 0)

    body = client.get(f"/cameras/{camera['id']}", headers=owner["headers"]).json()

    assert body["online"] is False
    assert body["last_seen_at"] is not None


def test_is_online_never_seen_is_false():
    assert is_online(None) is False


def test_is_online_treats_naive_time_as_utc():
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    assert is_online(now) is True
    assert is_online(now - timedelta(seconds=settings.camera_online_seconds + 1)) is False


def test_is_online_at_limit_is_false():
    limit = datetime.now(timezone.utc) - timedelta(seconds=settings.camera_online_seconds)

    assert is_online(limit) is False


def test_zones_of_new_camera_are_empty(client, owner, camera):
    response = client.get(f"/cameras/{camera['id']}/zones", headers=owner["headers"])

    assert response.status_code == 200
    assert response.json() == []


def test_put_zones_returns_them(client, owner, camera):
    zones = [
        {"type": "checkout", "name": "Till 1", "polygon": TRIANGLE},
        {"type": "exit", "polygon": TRIANGLE},
    ]

    response = client.put(f"/cameras/{camera['id']}/zones", json=zones, headers=owner["headers"])

    assert response.status_code == 200
    assert sorted(z["type"] for z in response.json()) == ["checkout", "exit"]
    assert all(z["camera_id"] == camera["id"] for z in response.json())
    assert all(z["polygon"] == TRIANGLE for z in response.json())


def test_put_zones_replaces_existing(client, owner, camera):
    url = f"/cameras/{camera['id']}/zones"
    two = [{"type": "checkout", "polygon": TRIANGLE}, {"type": "exit", "polygon": TRIANGLE}]
    client.put(url, json=two, headers=owner["headers"])

    client.put(url, json=[{"type": "exit", "polygon": TRIANGLE}], headers=owner["headers"])

    zones = client.get(url, headers=owner["headers"]).json()
    assert [z["type"] for z in zones] == ["exit"]


def test_put_empty_list_clears_zones(client, owner, camera):
    url = f"/cameras/{camera['id']}/zones"
    client.put(url, json=[{"type": "exit", "polygon": TRIANGLE}], headers=owner["headers"])

    response = client.put(url, json=[], headers=owner["headers"])

    assert response.status_code == 200
    assert response.json() == []
    assert client.get(url, headers=owner["headers"]).json() == []


def test_put_zones_replace_removes_old_rows(client, owner, camera, session_factory):
    url = f"/cameras/{camera['id']}/zones"
    client.put(url, json=[{"type": "exit", "polygon": TRIANGLE}], headers=owner["headers"])

    client.put(url, json=[{"type": "checkout", "polygon": TRIANGLE}], headers=owner["headers"])

    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Zone)) == 1


def test_put_zones_unknown_camera_is_404(client, owner):
    assert client.put("/cameras/99999/zones", json=[], headers=owner["headers"]).status_code == 404


def test_get_zones_unknown_camera_is_404(client, owner):
    assert client.get("/cameras/99999/zones", headers=owner["headers"]).status_code == 404


@pytest.mark.parametrize("point", [[0, 0], [1, 1], [0.5, 0.25]])
def test_put_zones_accepts_points_within_bounds(client, owner, camera, point):
    zone = {"type": "exit", "polygon": [point, [0.1, 0.2], [0.3, 0.4]]}

    response = client.put(f"/cameras/{camera['id']}/zones", json=[zone], headers=owner["headers"])

    assert response.status_code == 200
