import logging

import pytest
from sqlalchemy import select

from app import media
from app.models import Event
from tests.helpers import (
    CAMERA_PASSWORD,
    CLIP,
    FAKE_JPEG,
    FAKE_MP4,
    FAKE_PNG,
    FAKE_WEBM,
    SNAPSHOT,
    TRIANGLE,
    agent_key,
    create_camera,
    create_event,
    heartbeat,
    media_files,
    post_event,
)

BUG_ORPHAN_CLIP = "SCRUM-62: clip stays on disk when the snapshot is rejected"


def config(client, api_key):
    return client.get("/agent/config", headers=agent_key(api_key))


def test_config_returns_store_and_camera(client, owner, camera):
    response = config(client, owner["api_key"])

    assert response.status_code == 200
    body = response.json()
    assert body["store_id"] == owner["store_id"]
    assert body["store_name"] == "Korzinka"
    assert [c["id"] for c in body["cameras"]] == [camera["id"]]


def test_config_has_real_rtsp_urls_with_encoded_password(client, owner, camera):
    item = config(client, owner["api_key"]).json()["cameras"][0]

    assert item["rtsp_url_sub"] == "rtsp://admin:p%40ss%3Aw%2Frd%231@192.168.1.64:554/Streaming/Channels/102"
    assert item["rtsp_url_main"] == "rtsp://admin:p%40ss%3Aw%2Frd%231@192.168.1.64:554/Streaming/Channels/101"
    assert CAMERA_PASSWORD not in item["rtsp_url_sub"]


def test_config_has_threshold_and_zones(client, owner):
    camera = create_camera(client, owner, threshold=0.75)
    client.put(f"/cameras/{camera['id']}/zones", json=[{"type": "exit", "polygon": TRIANGLE}], headers=owner["headers"])

    item = config(client, owner["api_key"]).json()["cameras"][0]

    assert item["threshold"] == 0.75
    assert item["zones"][0]["type"] == "exit"
    assert item["zones"][0]["polygon"] == TRIANGLE


def test_config_leaves_out_inactive_cameras(client, owner, camera):
    inactive = create_camera(client, owner, is_active=False)

    ids = [c["id"] for c in config(client, owner["api_key"]).json()["cameras"]]

    assert camera["id"] in ids
    assert inactive["id"] not in ids


def test_config_lists_only_own_cameras(client, owner, camera, other_camera):
    ids = [c["id"] for c in config(client, owner["api_key"]).json()["cameras"]]

    assert ids == [camera["id"]]


def test_config_without_key_is_401(client):
    assert client.get("/agent/config").status_code == 401


def test_config_empty_key_is_401(client):
    assert config(client, "").status_code == 401


def test_config_wrong_key_is_401(client, owner):
    assert config(client, "lumi_wrong").status_code == 401


def test_config_rejects_user_token(client, owner):
    assert client.get("/agent/config", headers=owner["headers"]).status_code == 401


def test_heartbeat_with_snapshot_marks_camera_online(client, owner, camera):
    response = heartbeat(client, owner["api_key"], camera["id"], snapshot=SNAPSHOT)

    assert response.status_code == 204
    body = client.get(f"/cameras/{camera['id']}", headers=owner["headers"]).json()
    assert body["online"] is True
    assert body["has_snapshot"] is True
    assert body["last_seen_at"] is not None


def test_heartbeat_without_snapshot_keeps_existing_one(client, owner, camera):
    heartbeat(client, owner["api_key"], camera["id"], snapshot=SNAPSHOT)

    response = heartbeat(client, owner["api_key"], camera["id"])

    assert response.status_code == 204
    assert len(media_files()) == 1
    assert client.get(f"/cameras/{camera['id']}", headers=owner["headers"]).json()["has_snapshot"] is True


def test_heartbeat_new_snapshot_deletes_old_file(client, owner, camera):
    heartbeat(client, owner["api_key"], camera["id"], snapshot=SNAPSHOT)
    old = media_files()[0]

    heartbeat(client, owner["api_key"], camera["id"], snapshot=("new.png", FAKE_PNG, "image/png"))

    assert not old.exists()
    assert [p.read_bytes() for p in media_files()] == [FAKE_PNG]


def test_heartbeat_unknown_camera_is_404(client, owner):
    assert heartbeat(client, owner["api_key"], 99999).status_code == 404


def test_heartbeat_without_key_is_401(client, camera):
    assert client.post(f"/agent/cameras/{camera['id']}/heartbeat").status_code == 401


def test_heartbeat_bad_snapshot_type_keeps_camera_unchanged(client, owner, camera):
    heartbeat(client, owner["api_key"], camera["id"], snapshot=SNAPSHOT)
    before = client.get(f"/cameras/{camera['id']}", headers=owner["headers"]).json()

    response = heartbeat(client, owner["api_key"], camera["id"], snapshot=("a.gif", b"GIF89a", "image/gif"))

    assert response.status_code == 400
    assert client.get(f"/cameras/{camera['id']}", headers=owner["headers"]).json() == before
    assert len(media_files()) == 1


def test_heartbeat_of_other_store_camera_is_404(client, owner, other_camera):
    assert heartbeat(client, owner["api_key"], other_camera["id"]).status_code == 404


def test_event_of_other_store_camera_is_404(client, owner, other_camera):
    assert post_event(client, owner["api_key"], other_camera["id"]).status_code == 404


def test_event_is_created_pending(client, owner, camera):
    response = post_event(client, owner["api_key"], camera["id"], clip=CLIP, snapshot=SNAPSHOT)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["camera_id"] == camera["id"]
    assert body["camera_name"] == "Entrance"
    assert body["score"] == 0.9
    assert body["has_clip"] is True
    assert body["has_snapshot"] is True
    assert body["reviewed_by"] is None
    assert body["reviewed_at"] is None


def test_event_without_files_is_created(client, owner, camera):
    body = create_event(client, owner, camera["id"])

    assert body["has_clip"] is False
    assert body["has_snapshot"] is False


def test_event_marks_camera_as_seen(client, owner, camera):
    create_event(client, owner, camera["id"])

    assert client.get(f"/cameras/{camera['id']}", headers=owner["headers"]).json()["online"] is True


@pytest.mark.parametrize("score", [0, 1])
def test_event_accepts_score_limits(client, owner, camera, score):
    assert create_event(client, owner, camera["id"], score=score)["score"] == score


def test_event_without_key_is_401(client, camera):
    data = {"camera_id": camera["id"], "started_at": "2026-10-29T14:03:12+00:00", "score": 0.9}

    assert client.post("/agent/events", data=data).status_code == 401


def test_event_unknown_camera_is_404(client, owner):
    assert post_event(client, owner["api_key"], 99999).status_code == 404


def test_event_disallowed_clip_type_is_400(client, owner, camera):
    response = post_event(client, owner["api_key"], camera["id"], clip=("evil.exe", b"MZ", "application/octet-stream"))

    assert response.status_code == 400
    assert media_files() == []


def test_event_disallowed_file_type_creates_no_event(client, owner, camera, session_factory):
    post_event(client, owner["api_key"], camera["id"], clip=("evil.exe", b"MZ", "application/octet-stream"))

    with session_factory() as db:
        assert db.scalars(select(Event)).first() is None


def test_event_file_without_extension_is_400(client, owner, camera):
    assert post_event(client, owner["api_key"], camera["id"], clip=("clip", b"x", "video/mp4")).status_code == 400


def test_event_gif_snapshot_is_400(client, owner, camera):
    response = post_event(client, owner["api_key"], camera["id"], snapshot=("a.gif", b"GIF89a", "image/gif"))

    assert response.status_code == 400


@pytest.mark.parametrize(
    ("clip", "content"),
    [(("a.mp4", FAKE_MP4, "video/mp4"), FAKE_MP4), (("a.webm", FAKE_WEBM, "video/webm"), FAKE_WEBM),
     (("A.MP4", FAKE_MP4, "video/mp4"), FAKE_MP4)],
    ids=["mp4", "webm", "upper-case"],
)
def test_event_accepts_clip_types(client, owner, camera, clip, content):
    create_event(client, owner, camera["id"], clip=clip)

    assert [p.read_bytes() for p in media_files()] == [content]


@pytest.mark.parametrize("name", ["a.jpg", "a.jpeg", "a.png", "a.JPG"])
def test_event_accepts_snapshot_types(client, owner, camera, name):
    create_event(client, owner, camera["id"], snapshot=(name, FAKE_JPEG, "image/jpeg"))

    assert len(media_files()) == 1


def test_upload_ignores_path_in_file_name(client, owner, camera, tmp_path):
    create_event(client, owner, camera["id"], snapshot=("../../../evil.jpg", FAKE_JPEG, "image/jpeg"))

    assert [p.parent.name for p in media_files()] == ["events"]
    assert not (tmp_path / "evil.jpg").exists()


def test_upload_too_large_is_413(client, owner, camera, monkeypatch):
    monkeypatch.setattr("app.media.MAX_UPLOAD_BYTES", 10)

    response = post_event(client, owner["api_key"], camera["id"], clip=("a.mp4", b"x" * 11, "video/mp4"))

    assert response.status_code == 413
    assert media_files() == []


def test_upload_at_size_limit_is_accepted(client, owner, camera, monkeypatch):
    monkeypatch.setattr("app.media.MAX_UPLOAD_BYTES", 10)

    create_event(client, owner, camera["id"], clip=("a.mp4", b"x" * 10, "video/mp4"))

    assert len(media_files()) == 1


def test_upload_larger_than_one_chunk_is_stored_whole(client, owner, camera, monkeypatch):
    monkeypatch.setattr(media, "CHUNK", 4)

    create_event(client, owner, camera["id"], clip=("a.mp4", b"x" * 10, "video/mp4"))

    assert media_files()[0].read_bytes() == b"x" * 10


def test_heartbeat_upload_too_large_is_413(client, owner, camera, monkeypatch):
    monkeypatch.setattr("app.media.MAX_UPLOAD_BYTES", 2)

    assert heartbeat(client, owner["api_key"], camera["id"], snapshot=SNAPSHOT).status_code == 413


@pytest.mark.xfail(reason=BUG_ORPHAN_CLIP)
def test_rejected_snapshot_leaves_no_clip_file(client, owner, camera):
    response = post_event(client, owner["api_key"], camera["id"], clip=CLIP, snapshot=("a.gif", b"GIF89a", "image/gif"))

    assert response.status_code == 400
    assert media_files() == []


def test_new_event_triggers_notification(client, owner, camera, caplog):
    with caplog.at_level(logging.INFO, logger="lumi.notify"):
        event = create_event(client, owner, camera["id"], score=0.875)

    assert f"New event {event['id']} on camera {camera['id']} (score 0.88)" in caplog.text


