import pytest
from fastapi import HTTPException

from app import media


def test_delete_file_none_does_nothing(client):
    media.delete_file(None)


def test_delete_file_missing_does_nothing(client):
    media.delete_file("events/missing.jpg")


def test_file_response_none_is_404(client):
    with pytest.raises(HTTPException) as error:
        media.file_response(None)

    assert error.value.status_code == 404


def test_file_response_directory_is_404(client):
    (media.media_root() / "events").mkdir(parents=True)

    with pytest.raises(HTTPException) as error:
        media.file_response("events")

    assert error.value.status_code == 404
