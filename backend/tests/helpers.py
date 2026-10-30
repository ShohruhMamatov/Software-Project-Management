from pathlib import Path

from app.config import settings

FAKE_JPEG = b"\xff\xd8\xff\xe0fake"
FAKE_PNG = b"\x89PNG\r\n\x1a\nfake"
FAKE_WEBM = b"\x1aE\xdf\xa3fake"
FAKE_MP4 = b"\x00\x00\x00\x18ftypfake"

SNAPSHOT = ("snap.jpg", FAKE_JPEG, "image/jpeg")
CLIP = ("clip.webm", FAKE_WEBM, "video/webm")

PASSWORD = "secret123"
CAMERA_PASSWORD = "p@ss:w/rd#1"
STARTED_AT = "2026-10-29T14:03:12+00:00"
TRIANGLE = [[0.0, 0.0], [1.0, 0.0], [0.5, 1.0]]


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def agent_key(api_key):
    return {"X-API-Key": api_key}


def register(client, email="owner@lumi.uz", password=PASSWORD, **fields):
    response = client.post("/auth/register", json={"email": email, "password": password, **fields})
    assert response.status_code == 201, response.text
    return bearer(response.json()["access_token"])


def camera_body(**overrides):
    return {
        "name": "Entrance", "ip": "192.168.1.64", "rtsp_username": "admin",
        "rtsp_password": CAMERA_PASSWORD, **overrides,
    }


def create_owner(client, email="owner@lumi.uz", store_name="Korzinka"):
    headers = register(client, email=email)
    response = client.post("/stores", json={"name": store_name}, headers=headers)
    assert response.status_code == 201, response.text
    store = response.json()
    return {"headers": headers, "api_key": store["api_key"], "store_id": store["id"]}


def create_camera(client, owner, **overrides):
    response = client.post("/cameras", json=camera_body(**overrides), headers=owner["headers"])
    assert response.status_code == 201, response.text
    return response.json()


def post_event(client, api_key, camera_id, *, started_at=STARTED_AT, score=0.9, clip=None, snapshot=None):
    data = {"camera_id": camera_id, "started_at": started_at, "score": score}
    files = {"clip": clip, "snapshot": snapshot}
    return client.post(
        "/agent/events",
        data={k: v for k, v in data.items() if v is not None},
        files={k: v for k, v in files.items() if v is not None},
        headers=agent_key(api_key),
    )


def create_event(client, owner, camera_id, **kwargs):
    response = post_event(client, owner["api_key"], camera_id, **kwargs)
    assert response.status_code == 201, response.text
    return response.json()


def heartbeat(client, api_key, camera_id, snapshot=None):
    return client.post(
        f"/agent/cameras/{camera_id}/heartbeat",
        files={"snapshot": snapshot} if snapshot else None,
        headers=agent_key(api_key),
    )


def media_files():
    return [p for p in Path(settings.media_dir).rglob("*") if p.is_file()]
