import pytest
from cryptography.fernet import InvalidToken

from app.config import settings
from app.security import (
    decrypt_secret,
    encrypt_secret,
    hash_api_key,
    hash_password,
    new_api_key,
    verify_password,
)


def test_verify_password_accepts_correct_password():
    assert verify_password("secret123", hash_password("secret123")) is True


def test_verify_password_rejects_wrong_password():
    assert verify_password("wrong", hash_password("secret123")) is False


def test_hash_password_is_salted():
    assert hash_password("secret123") != hash_password("secret123")


def test_new_api_keys_are_prefixed_and_unique():
    first, second = new_api_key(), new_api_key()

    assert first.startswith("lumi_")
    assert first != second


def test_hash_api_key_is_stable_sha256():
    assert hash_api_key("key") == hash_api_key("key")
    assert len(hash_api_key("key")) == 64
    assert hash_api_key("key") != hash_api_key("other")


def test_encrypt_secret_round_trip():
    assert decrypt_secret(encrypt_secret("p@ss:w/rd#1")) == "p@ss:w/rd#1"


def test_encrypt_secret_does_not_contain_plain_text():
    assert "p@ss" not in encrypt_secret("p@ss:w/rd#1")


def test_decrypt_secret_with_other_key_fails(monkeypatch):
    token = encrypt_secret("secret")
    monkeypatch.setattr(settings, "camera_enc_key", "another-key")

    with pytest.raises(InvalidToken):
        decrypt_secret(token)


