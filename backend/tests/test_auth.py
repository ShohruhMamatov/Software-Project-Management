from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.config import settings
from app.models import User
from app.security import JWT_ALGORITHM
from tests.helpers import PASSWORD, bearer, register

BUG_PASSWORD_BYTES = "SCRUM-63: password over 72 bytes is accepted and truncated by bcrypt"


def login(client, email="owner@lumi.uz", password=PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def token(sub="1", secret=None, algorithm=JWT_ALGORITHM, **claims):
    payload = {"exp": datetime.now(timezone.utc) + timedelta(minutes=5), **claims}
    if sub is not None:
        payload["sub"] = sub
    return jwt.encode(payload, secret if secret is not None else settings.jwt_secret, algorithm=algorithm)


def deactivate(session_factory, email="owner@lumi.uz"):
    with session_factory() as db:
        user = db.query(User).filter_by(email=email).one()
        user.is_active = False
        db.commit()


def test_register_returns_token_and_owner_without_store(client):
    response = client.post(
        "/auth/register", json={"email": "new@lumi.uz", "password": PASSWORD, "full_name": "Ali"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "new@lumi.uz"
    assert body["user"]["full_name"] == "Ali"
    assert body["user"]["role"] == "owner"
    assert body["user"]["store_id"] is None


def test_register_stores_email_lower_case(client):
    headers = register(client, email="MiXeD@Lumi.UZ")

    assert client.get("/auth/me", headers=headers).json()["email"] == "mixed@lumi.uz"


def test_register_full_name_is_optional(client):
    headers = register(client)

    assert client.get("/auth/me", headers=headers).json()["full_name"] is None


@pytest.mark.parametrize("email", ["dup@lumi.uz", "DUP@LUMI.UZ"])
def test_register_used_email_is_409(client, email):
    register(client, email="dup@lumi.uz")

    response = client.post("/auth/register", json={"email": email, "password": PASSWORD})

    assert response.status_code == 409


@pytest.mark.parametrize("password", ["a" * 8, "a" * 72])
def test_register_accepts_password_length_limits(client, password):
    register(client, password=password)

    assert login(client, password=password).status_code == 200


@pytest.mark.xfail(reason=BUG_PASSWORD_BYTES)
def test_register_password_over_72_bytes_is_422(client):
    response = client.post("/auth/register", json={"email": "new@lumi.uz", "password": "й" * 50})

    assert response.status_code == 422


def test_login_returns_token_and_user(client):
    register(client)

    response = login(client)

    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.json()["user"]["email"] == "owner@lumi.uz"


def test_login_email_is_case_insensitive(client):
    register(client)

    assert login(client, email="OWNER@LUMI.UZ").status_code == 200


def test_login_wrong_password_is_401(client):
    register(client)

    assert login(client, password="wrong-password").status_code == 401


def test_login_unknown_email_is_401(client):
    assert login(client, email="ghost@lumi.uz").status_code == 401


def test_login_errors_do_not_reveal_whether_email_exists(client):
    register(client)

    wrong_password = login(client, password="wrong-password")
    unknown_email = login(client, email="ghost@lumi.uz")

    assert wrong_password.json() == unknown_email.json()


def test_login_inactive_user_is_401(client, session_factory):
    register(client)
    deactivate(session_factory)

    assert login(client).status_code == 401


def test_me_returns_current_user(client):
    headers = register(client)

    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 200
    assert response.json()["email"] == "owner@lumi.uz"


def test_me_accepts_token_from_login(client):
    register(client)
    access_token = login(client).json()["access_token"]

    assert client.get("/auth/me", headers=bearer(access_token)).status_code == 200


def test_me_without_token_is_401(client):
    response = client.get("/auth/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("header", ["Bearer garbage", "Bearer ", "Basic dXNlcjpwYXNz", "garbage"])
def test_me_invalid_authorization_header_is_401(client, header):
    assert client.get("/auth/me", headers={"Authorization": header}).status_code == 401


def test_me_expired_token_is_401(client, monkeypatch):
    monkeypatch.setattr(settings, "jwt_expire_minutes", -1)
    headers = register(client)

    assert client.get("/auth/me", headers=headers).status_code == 401


def test_me_token_signed_with_other_secret_is_401(client):
    register(client)

    assert client.get("/auth/me", headers=bearer(token(secret="other-secret"))).status_code == 401


def test_me_token_with_other_algorithm_is_401(client):
    register(client)

    assert client.get("/auth/me", headers=bearer(token(algorithm="HS512"))).status_code == 401


def test_me_unsigned_token_is_401(client):
    register(client)
    unsigned = jwt.encode({"sub": "1"}, "", algorithm="none")

    assert client.get("/auth/me", headers=bearer(unsigned)).status_code == 401


def test_me_token_without_sub_is_401(client):
    register(client)

    assert client.get("/auth/me", headers=bearer(token(sub=None))).status_code == 401


def test_me_token_with_non_numeric_sub_is_401(client):
    register(client)

    assert client.get("/auth/me", headers=bearer(token(sub="abc"))).status_code == 401


def test_me_token_of_deleted_user_is_401(client):
    register(client)

    assert client.get("/auth/me", headers=bearer(token(sub="99999"))).status_code == 401


def test_me_inactive_user_token_stops_working(client, session_factory):
    headers = register(client)
    deactivate(session_factory)

    assert client.get("/auth/me", headers=headers).status_code == 401


def test_password_is_stored_hashed(client, session_factory):
    register(client)

    with session_factory() as db:
        stored = db.query(User).filter_by(email="owner@lumi.uz").one().password_hash

    assert stored != PASSWORD
    assert stored.startswith("$2b$")
