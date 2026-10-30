import re

import pytest
from fastapi.routing import APIRoute

from app.main import app
from app.models import User, UserRole
from tests.helpers import CLIP, SNAPSHOT, TRIANGLE, bearer, camera_body, create_event, heartbeat, register

PUBLIC = {("GET", "/health"), ("POST", "/auth/register"), ("POST", "/auth/login")}
ROUTES = sorted(
    (method, re.sub(r"\{\w+\}", "1", route.path))
    for route in app.routes if isinstance(route, APIRoute)
    for method in route.methods - {"HEAD", "OPTIONS"}
    if (method, route.path) not in PUBLIC
)
DASHBOARD_ROUTES = [r for r in ROUTES if not r[1].startswith("/agent")]
AGENT_ROUTES = [r for r in ROUTES if r[1].startswith("/agent")]

ZONES = [{"type": "exit", "polygon": TRIANGLE}]
OWNER_ONLY = [
    ("POST", "/stores", {"name": "Second"}),
    ("PATCH", "/stores/me", {"name": "Hacked"}),
    ("POST", "/stores/me/api-key", None),
    ("POST", "/cameras", camera_body()),
    ("PATCH", "/cameras/{camera}", {"name": "Hacked"}),
    ("DELETE", "/cameras/{camera}", None),
    ("PUT", "/cameras/{camera}/zones", ZONES),
]
STORE_ENDPOINTS = [
    ("GET", "/stores/me", None),
    ("PATCH", "/stores/me", {"name": "x"}),
    ("POST", "/stores/me/api-key", None),
    ("GET", "/cameras", None),
    ("POST", "/cameras", camera_body()),
    ("GET", "/cameras/1", None),
    ("PATCH", "/cameras/1", {"name": "x"}),
    ("DELETE", "/cameras/1", None),
    ("GET", "/cameras/1/snapshot", None),
    ("GET", "/cameras/1/zones", None),
    ("PUT", "/cameras/1/zones", ZONES),
    ("GET", "/events", None),
    ("GET", "/events/1", None),
    ("POST", "/events/1/review", {"status": "confirmed"}),
    ("GET", "/events/1/clip", None),
    ("GET", "/events/1/snapshot", None),
]
FOREIGN_RESOURCES = [
    ("GET", "/cameras/{camera}", None),
    ("PATCH", "/cameras/{camera}", {"name": "Hacked"}),
    ("DELETE", "/cameras/{camera}", None),
    ("GET", "/cameras/{camera}/snapshot", None),
    ("GET", "/cameras/{camera}/zones", None),
    ("PUT", "/cameras/{camera}/zones", ZONES),
    ("GET", "/events/{event}", None),
    ("POST", "/events/{event}/review", {"status": "confirmed"}),
    ("GET", "/events/{event}/clip", None),
    ("GET", "/events/{event}/snapshot", None),
]


def call(client, method, path, body, headers):
    return client.request(method, path, json=body, headers=headers)


def route_id(value):
    return value if isinstance(value, str) else ""


def test_route_lists_are_not_empty():
    assert DASHBOARD_ROUTES and AGENT_ROUTES


@pytest.mark.parametrize(("method", "path"), DASHBOARD_ROUTES)
def test_dashboard_route_without_token_is_401(client, method, path):
    assert client.request(method, path).status_code == 401


@pytest.mark.parametrize(("method", "path"), DASHBOARD_ROUTES)
def test_dashboard_route_with_garbage_token_is_401(client, method, path):
    assert client.request(method, path, headers=bearer("garbage")).status_code == 401


@pytest.mark.parametrize(("method", "path"), AGENT_ROUTES)
def test_agent_route_without_key_is_401(client, method, path):
    assert client.request(method, path).status_code == 401


@pytest.mark.parametrize(("method", "path"), AGENT_ROUTES)
def test_agent_route_with_wrong_key_is_401(client, method, path):
    assert client.request(method, path, headers={"X-API-Key": "lumi_wrong"}).status_code == 401


@pytest.mark.parametrize(("method", "path", "body"), STORE_ENDPOINTS, ids=route_id)
def test_user_without_store_is_400(client, method, path, body):
    headers = register(client)

    response = call(client, method, path, body, headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "Create a store first"


@pytest.mark.parametrize(("method", "path", "body"), OWNER_ONLY, ids=route_id)
def test_staff_cannot_use_owner_endpoints(client, staff, camera, method, path, body):
    response = call(client, method, path.format(camera=camera["id"]), body, staff)

    assert response.status_code == 403


def test_staff_denied_requests_change_nothing(client, owner, staff, camera):
    client.delete(f"/cameras/{camera['id']}", headers=staff)
    client.patch("/stores/me", json={"name": "Hacked"}, headers=staff)

    assert client.get(f"/cameras/{camera['id']}", headers=owner["headers"]).status_code == 200
    assert client.get("/stores/me", headers=owner["headers"]).json()["name"] == "Korzinka"


def test_staff_can_read_store_data(client, staff, camera):
    assert client.get("/stores/me", headers=staff).status_code == 200
    assert [c["id"] for c in client.get("/cameras", headers=staff).json()] == [camera["id"]]
    assert client.get(f"/cameras/{camera['id']}/zones", headers=staff).status_code == 200
    assert client.get("/events", headers=staff).status_code == 200


def test_staff_can_review_event(client, owner, staff, camera):
    event = create_event(client, owner, camera["id"])

    response = client.post(f"/events/{event['id']}/review", json={"status": "confirmed"}, headers=staff)

    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"
    assert response.json()["reviewed_by"] == client.get("/auth/me", headers=staff).json()["id"]


def test_camera_password_never_appears_in_dashboard_responses(client, owner, camera):
    url = f"/cameras/{camera['id']}"
    responses = [
        client.post("/cameras", json=camera_body(name="New"), headers=owner["headers"]),
        client.get("/cameras", headers=owner["headers"]),
        client.get(url, headers=owner["headers"]),
        client.patch(url, json={"name": "Renamed"}, headers=owner["headers"]),
        client.patch(url, json={"rtsp_password": "p@ss:w/rd#1"}, headers=owner["headers"]),
    ]

    for response in responses:
        assert response.is_success
        for secret in ("p@ss", "rd#1", "p%40ss", "rd%231", "rtsp_password"):
            assert secret not in response.text


def test_hashes_never_appear_in_responses(client):
    payload = {"email": "new@lumi.uz", "password": "secret123"}
    registered = client.post("/auth/register", json=payload)
    headers = bearer(registered.json()["access_token"])
    responses = [
        registered,
        client.post("/auth/login", json=payload),
        client.get("/auth/me", headers=headers),
        client.post("/stores", json={"name": "Korzinka"}, headers=headers),
        client.get("/stores/me", headers=headers),
        client.patch("/stores/me", json={"name": "New"}, headers=headers),
        client.post("/stores/me/api-key", headers=headers),
    ]

    for response in responses:
        assert response.is_success
        assert "password_hash" not in response.text
        assert "api_key_hash" not in response.text
        assert "$2b$" not in response.text


@pytest.mark.parametrize(("method", "path", "body"), FOREIGN_RESOURCES, ids=route_id)
def test_other_store_resource_is_404(client, owner, camera, other_owner, method, path, body):
    heartbeat(client, owner["api_key"], camera["id"], snapshot=SNAPSHOT)
    event = create_event(client, owner, camera["id"], clip=CLIP, snapshot=SNAPSHOT)

    response = call(client, method, path.format(camera=camera["id"], event=event["id"]), body, other_owner["headers"])

    assert response.status_code == 404


def test_other_store_gets_same_404_as_missing_resource(client, camera, other_owner):
    foreign = client.get(f"/cameras/{camera['id']}", headers=other_owner["headers"])
    missing = client.get("/cameras/99999", headers=other_owner["headers"])

    assert foreign.json() == missing.json()


def test_other_store_lists_are_empty(client, owner, camera, other_owner):
    create_event(client, owner, camera["id"])

    assert client.get("/cameras", headers=other_owner["headers"]).json() == []
    assert client.get("/events", headers=other_owner["headers"]).json() == {"items": [], "total": 0}


def test_other_store_camera_filter_finds_nothing(client, owner, camera, other_owner):
    create_event(client, owner, camera["id"])

    body = client.get("/events", params={"camera_id": camera["id"]}, headers=other_owner["headers"]).json()

    assert body == {"items": [], "total": 0}


def test_other_store_requests_change_nothing(client, owner, camera, other_owner):
    event = create_event(client, owner, camera["id"])
    client.delete(f"/cameras/{camera['id']}", headers=other_owner["headers"])
    client.post(f"/events/{event['id']}/review", json={"status": "confirmed"}, headers=other_owner["headers"])

    assert client.get(f"/events/{event['id']}", headers=owner["headers"]).json()["status"] == "pending"


def test_staff_cannot_reach_other_store(client, staff, other_camera):
    assert client.get(f"/cameras/{other_camera['id']}", headers=staff).status_code == 404


def test_staff_without_store_is_400(client, session_factory):
    headers = register(client)
    with session_factory() as db:
        db.query(User).one().role = UserRole.staff
        db.commit()

    assert client.get("/cameras", headers=headers).status_code == 400
