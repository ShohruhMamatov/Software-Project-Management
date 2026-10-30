import pytest

from tests.conftest import xfail_on_postgres
from tests.helpers import PASSWORD, TRIANGLE, agent_key, camera_body, create_event, heartbeat, post_event

BUG_NON_FINITE = "SCRUM-57: NaN or Infinity in the 422 body crashes JSONResponse: 500"
BUG_HUGE_INT = "SCRUM-58: integer outside the DB range reaches the query: 500"
BUG_NUL = "SCRUM-59: Postgres cannot store NUL characters: 500"

LONG = "x" * 121
HUGE = 10**30
JSON = {"Content-Type": "application/json"}


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"email": "new@lumi.uz"},
        {"password": PASSWORD},
        {"email": "not-an-email", "password": PASSWORD},
        {"email": "new@lumi.uz", "password": "short"},
        {"email": "new@lumi.uz", "password": "x" * 73},
        {"email": "new@lumi.uz", "password": PASSWORD, "full_name": LONG},
    ],
    ids=["empty", "no-password", "no-email", "bad-email", "short-password", "long-password", "long-name"],
)
def test_register_invalid_body_is_422(client, body):
    assert client.post("/auth/register", json=body).status_code == 422


@pytest.mark.parametrize("body", [{}, {"email": "a@lumi.uz"}, {"email": "bad", "password": PASSWORD}])
def test_login_invalid_body_is_422(client, body):
    assert client.post("/auth/login", json=body).status_code == 422


@pytest.mark.parametrize("body", [{}, {"name": ""}, {"name": LONG}, {"name": "x", "address": "a" * 256}])
def test_create_store_invalid_body_is_422(client, owner, body):
    assert client.post("/stores", json=body, headers=owner["headers"]).status_code == 422


@pytest.mark.parametrize("body", [{"name": ""}, {"name": LONG}, {"address": "a" * 256}])
def test_update_store_invalid_body_is_422(client, owner, body):
    assert client.patch("/stores/me", json=body, headers=owner["headers"]).status_code == 422


@pytest.mark.parametrize(
    "overrides",
    [
        {"port": 0}, {"port": 65536}, {"channel": 0}, {"channel": 65},
        {"threshold": -0.1}, {"threshold": 1.1},
        {"name": ""}, {"name": LONG}, {"ip": ""}, {"ip": "1" * 65},
        {"rtsp_username": ""}, {"rtsp_username": "u" * 65},
        {"rtsp_password": ""}, {"rtsp_password": "p" * 129},
    ],
    ids=str,
)
def test_create_camera_invalid_field_is_422(client, owner, overrides):
    response = client.post("/cameras", json=camera_body(**overrides), headers=owner["headers"])

    assert response.status_code == 422


@pytest.mark.parametrize("field", ["name", "ip", "rtsp_username", "rtsp_password"])
def test_create_camera_missing_field_is_422(client, owner, field):
    body = camera_body()
    del body[field]

    assert client.post("/cameras", json=body, headers=owner["headers"]).status_code == 422


@pytest.mark.parametrize("overrides", [{"port": 1}, {"port": 65535}, {"channel": 64}, {"threshold": 1}], ids=str)
def test_create_camera_accepts_limits(client, owner, overrides):
    response = client.post("/cameras", json=camera_body(**overrides), headers=owner["headers"])

    assert response.status_code == 201


@pytest.mark.parametrize(
    "body",
    [
        {"port": 0}, {"port": 65536}, {"channel": 0}, {"channel": 65}, {"threshold": -0.1}, {"threshold": 1.1},
        {"name": ""}, {"ip": ""}, {"rtsp_username": ""}, {"rtsp_password": ""},
    ],
    ids=str,
)
def test_update_camera_invalid_field_is_422(client, owner, camera, body):
    assert client.patch(f"/cameras/{camera['id']}", json=body, headers=owner["headers"]).status_code == 422


@pytest.mark.xfail(reason=BUG_NON_FINITE)
@pytest.mark.parametrize("raw", ["NaN", "Infinity"])
def test_camera_threshold_non_finite_is_422(client, owner, raw):
    content = '{"name": "x", "ip": "1.1.1.1", "rtsp_username": "a", "rtsp_password": "b", "threshold": %s}' % raw

    response = client.post("/cameras", content=content, headers={**owner["headers"], **JSON})

    assert response.status_code == 422


@pytest.mark.xfail(reason=BUG_NON_FINITE)
def test_public_endpoint_non_finite_body_is_422(client):
    response = client.post("/auth/login", content='{"email": NaN, "password": "x"}', headers=JSON)

    assert response.status_code == 422


@pytest.mark.xfail(reason=BUG_NON_FINITE)
def test_zone_non_finite_point_is_422(client, owner, camera):
    content = '[{"type": "exit", "polygon": [[NaN, 0], [0, 0], [1, 1]]}]'

    response = client.put(f"/cameras/{camera['id']}/zones", content=content, headers={**owner["headers"], **JSON})

    assert response.status_code == 422


@pytest.mark.xfail(reason=BUG_HUGE_INT)
@pytest.mark.parametrize(
    "path",
    [f"/cameras/{HUGE}", f"/events/{HUGE}", f"/events?after_id={HUGE}", f"/events?camera_id={HUGE}",
     f"/events?offset={HUGE}"],
)
def test_huge_integer_in_url_is_not_a_server_error(client, owner, path):
    assert client.get(path, headers=owner["headers"]).status_code < 500


@pytest.mark.xfail(reason=BUG_HUGE_INT)
def test_agent_event_huge_camera_id_is_not_a_server_error(client, owner):
    assert post_event(client, owner["api_key"], HUGE).status_code < 500


@pytest.mark.xfail(reason=BUG_HUGE_INT)
def test_heartbeat_huge_camera_id_is_not_a_server_error(client, owner):
    assert heartbeat(client, owner["api_key"], HUGE).status_code < 500


@xfail_on_postgres(BUG_NUL)
def test_store_name_with_nul_is_not_a_server_error(client, owner):
    assert client.patch("/stores/me", json={"name": "a\x00b"}, headers=owner["headers"]).status_code < 500


@xfail_on_postgres(BUG_NUL)
def test_camera_name_with_nul_is_not_a_server_error(client, owner):
    response = client.post("/cameras", json=camera_body(name="a\x00b"), headers=owner["headers"])

    assert response.status_code < 500


@xfail_on_postgres(BUG_NUL)
def test_register_name_with_nul_is_not_a_server_error(client):
    body = {"email": "new@lumi.uz", "password": PASSWORD, "full_name": "a\x00b"}

    assert client.post("/auth/register", json=body).status_code < 500


@pytest.mark.parametrize("path", ["/cameras/abc", "/cameras/1.5", "/events/abc"])
def test_non_integer_id_is_422(client, owner, path):
    assert client.get(path, headers=owner["headers"]).status_code == 422


@pytest.mark.parametrize(
    "zone",
    [
        {"type": "door", "polygon": TRIANGLE},
        {"polygon": TRIANGLE},
        {"type": "exit"},
        {"type": "exit", "polygon": TRIANGLE[:2]},
        {"type": "exit", "polygon": [[0.1, 0.2, 0.3], [0, 0], [1, 1]]},
        {"type": "exit", "polygon": [[0.1], [0, 0], [1, 1]]},
        {"type": "exit", "polygon": [[-0.1, 0], [0, 0], [1, 1]]},
        {"type": "exit", "polygon": [[1.1, 0], [0, 0], [1, 1]]},
        {"type": "exit", "name": LONG, "polygon": TRIANGLE},
    ],
    ids=["unknown-type", "no-type", "no-polygon", "two-points", "three-numbers", "one-number",
         "below-zero", "above-one", "long-name"],
)
def test_put_zones_invalid_body_is_422(client, owner, camera, zone):
    response = client.put(f"/cameras/{camera['id']}/zones", json=[zone], headers=owner["headers"])

    assert response.status_code == 422


def test_put_zones_invalid_body_keeps_old_zones(client, owner, camera):
    url = f"/cameras/{camera['id']}/zones"
    client.put(url, json=[{"type": "exit", "polygon": TRIANGLE}], headers=owner["headers"])

    client.put(url, json=[{"type": "door", "polygon": TRIANGLE}], headers=owner["headers"])

    assert len(client.get(url, headers=owner["headers"]).json()) == 1


@pytest.mark.parametrize(
    "params",
    [{"status": "foo"}, {"limit": 0}, {"limit": 201}, {"offset": -1}, {"camera_id": "abc"}, {"after_id": "abc"}],
    ids=str,
)
def test_list_events_invalid_query_is_422(client, owner, params):
    assert client.get("/events", params=params, headers=owner["headers"]).status_code == 422


@pytest.mark.parametrize("body", [{"status": "pending"}, {"status": "maybe"}, {}])
def test_review_invalid_status_is_422(client, owner, camera, body):
    event = create_event(client, owner, camera["id"])

    assert client.post(f"/events/{event['id']}/review", json=body, headers=owner["headers"]).status_code == 422


@pytest.mark.parametrize(
    "fields",
    [
        {"started_at": None}, {"started_at": "yesterday"}, {"score": None},
        {"score": -0.1}, {"score": 1.1}, {"score": "high"}, {"score": "nan"},
    ],
    ids=str,
)
def test_agent_event_invalid_form_is_422(client, owner, camera, fields):
    assert post_event(client, owner["api_key"], camera["id"], **fields).status_code == 422


def test_agent_event_missing_camera_id_is_422(client, owner):
    assert post_event(client, owner["api_key"], None).status_code == 422


def test_agent_event_non_integer_camera_id_is_422(client, owner):
    assert post_event(client, owner["api_key"], "abc").status_code == 422


def test_heartbeat_non_integer_camera_id_is_422(client, owner):
    response = client.post("/agent/cameras/abc/heartbeat", headers=agent_key(owner["api_key"]))

    assert response.status_code == 422
