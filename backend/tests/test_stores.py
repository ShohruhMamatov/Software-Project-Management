import pytest

from app.models import Store
from app.security import hash_api_key
from tests.helpers import agent_key, register

BUG_NULL_NAME = "null name reaches a NOT NULL column: 500"


def test_create_store_returns_api_key(client):
    headers = register(client)

    response = client.post("/stores", json={"name": "Korzinka", "address": "Tashkent"}, headers=headers)

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Korzinka"
    assert body["address"] == "Tashkent"
    assert body["has_api_key"] is True
    assert body["api_key"].startswith("lumi_")


def test_create_store_assigns_it_to_user(client):
    headers = register(client)

    store_id = client.post("/stores", json={"name": "Korzinka"}, headers=headers).json()["id"]

    assert client.get("/auth/me", headers=headers).json()["store_id"] == store_id


def test_create_store_keeps_only_hash_of_api_key(client, owner, session_factory):
    with session_factory() as db:
        stored = db.get(Store, owner["store_id"]).api_key_hash

    assert stored == hash_api_key(owner["api_key"])
    assert stored != owner["api_key"]


def test_second_store_is_409(client, owner):
    response = client.post("/stores", json={"name": "Second"}, headers=owner["headers"])

    assert response.status_code == 409


def test_get_my_store_hides_api_key(client, owner):
    response = client.get("/stores/me", headers=owner["headers"])

    assert response.status_code == 200
    assert response.json()["id"] == owner["store_id"]
    assert response.json()["has_api_key"] is True
    assert "api_key" not in response.json()


def test_update_store_changes_fields(client, owner):
    response = client.patch(
        "/stores/me", json={"name": "New name", "address": "New address"}, headers=owner["headers"]
    )

    assert response.status_code == 200
    assert response.json()["name"] == "New name"
    assert response.json()["address"] == "New address"


def test_update_store_partial_keeps_other_fields(client, owner):
    client.patch("/stores/me", json={"address": "Tashkent"}, headers=owner["headers"])

    response = client.patch("/stores/me", json={"name": "New name"}, headers=owner["headers"])

    assert response.json()["address"] == "Tashkent"


def test_update_store_empty_body_changes_nothing(client, owner):
    response = client.patch("/stores/me", json={}, headers=owner["headers"])

    assert response.status_code == 200
    assert response.json()["name"] == "Korzinka"


def test_update_store_can_clear_address(client, owner):
    client.patch("/stores/me", json={"address": "Tashkent"}, headers=owner["headers"])

    response = client.patch("/stores/me", json={"address": None}, headers=owner["headers"])

    assert response.status_code == 200
    assert response.json()["address"] is None


@pytest.mark.xfail(reason=BUG_NULL_NAME)
def test_update_store_null_name_is_rejected(client, owner):
    response = client.patch("/stores/me", json={"name": None}, headers=owner["headers"])

    assert response.status_code == 422


def test_rotate_api_key_returns_new_key(client, owner):
    response = client.post("/stores/me/api-key", headers=owner["headers"])

    assert response.status_code == 200
    assert response.json()["api_key"].startswith("lumi_")
    assert response.json()["api_key"] != owner["api_key"]


def test_rotate_api_key_invalidates_old_key(client, owner):
    client.post("/stores/me/api-key", headers=owner["headers"])

    assert client.get("/agent/config", headers=agent_key(owner["api_key"])).status_code == 401


def test_rotate_api_key_activates_new_key(client, owner):
    new_key = client.post("/stores/me/api-key", headers=owner["headers"]).json()["api_key"]

    assert client.get("/agent/config", headers=agent_key(new_key)).status_code == 200
