import os

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  (registers tables on Base.metadata)
from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import User, UserRole
from app.security import hash_password
from tests.helpers import PASSWORD, bearer, create_camera, create_owner

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
IS_POSTGRES = bool(TEST_DATABASE_URL)

postgres_only = pytest.mark.skipif(not IS_POSTGRES, reason="needs TEST_DATABASE_URL")


def xfail_on_postgres(reason):
    return pytest.mark.xfail(IS_POSTGRES, reason=reason)


def make_engine():
    if TEST_DATABASE_URL:
        return create_engine(TEST_DATABASE_URL)
    # StaticPool + check_same_thread=False: one shared in-memory DB across TestClient threads.
    return create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)


@pytest.fixture(autouse=True)
def fast_bcrypt(monkeypatch):
    gensalt = bcrypt.gensalt
    monkeypatch.setattr(bcrypt, "gensalt", lambda: gensalt(rounds=4))


@pytest.fixture
def session_factory():
    engine = make_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(session_factory, tmp_path, monkeypatch):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(settings, "media_dir", str(tmp_path / "media"))
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def owner(client):
    return create_owner(client)


@pytest.fixture
def camera(client, owner):
    return create_camera(client, owner)


@pytest.fixture
def other_owner(client):
    return create_owner(client, email="rival@lumi.uz", store_name="Makro")


@pytest.fixture
def other_camera(client, other_owner):
    return create_camera(client, other_owner, name="Rival entrance")


@pytest.fixture
def staff(client, owner, session_factory):
    with session_factory() as db:
        db.add(User(email="staff@lumi.uz", password_hash=hash_password(PASSWORD),
                    role=UserRole.staff, store_id=owner["store_id"], is_active=True))
        db.commit()
    response = client.post("/auth/login", json={"email": "staff@lumi.uz", "password": PASSWORD})
    return bearer(response.json()["access_token"])
