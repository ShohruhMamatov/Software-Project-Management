import pytest

from app.hikvision import build_rtsp_url, camera_rtsp_url, channel_path, masked_rtsp_url
from app.models import Camera
from app.security import encrypt_secret
from tests.helpers import CAMERA_PASSWORD


def build(channel=1, stream="sub", username="admin", password="pass", ip="10.0.0.5", port=554):
    return build_rtsp_url(ip, port, channel, username, password, stream)


def stored_camera(**overrides):
    fields = {"ip": "10.0.0.5", "port": 554, "channel": 2, "rtsp_username": "ad@min",
              "rtsp_password_encrypted": encrypt_secret(CAMERA_PASSWORD)}
    return Camera(**{**fields, **overrides})


@pytest.mark.parametrize(
    ("channel", "stream", "path"),
    [
        (1, "sub", "/Streaming/Channels/102"),
        (1, "main", "/Streaming/Channels/101"),
        (3, "main", "/Streaming/Channels/301"),
        (12, "sub", "/Streaming/Channels/1202"),
        (64, "main", "/Streaming/Channels/6401"),
    ],
)
def test_channel_path_combines_channel_and_stream(channel, stream, path):
    assert channel_path(channel, stream) == path
    assert build(channel=channel, stream=stream).endswith(path)


def test_build_rtsp_url_full_format():
    assert build(port=8554) == "rtsp://admin:pass@10.0.0.5:8554/Streaming/Channels/102"


def test_build_rtsp_url_defaults_to_sub_stream():
    assert build_rtsp_url("10.0.0.5", 554, 1, "admin", "pass").endswith("/102")


def test_build_rtsp_url_encodes_password():
    assert build(password=CAMERA_PASSWORD).startswith("rtsp://admin:p%40ss%3Aw%2Frd%231@10.0.0.5")


def test_build_rtsp_url_encodes_username():
    assert build(username="ad@min").startswith("rtsp://ad%40min:pass@")


def test_camera_rtsp_url_decrypts_password():
    assert camera_rtsp_url(stored_camera()) == (
        "rtsp://ad%40min:p%40ss%3Aw%2Frd%231@10.0.0.5:554/Streaming/Channels/202"
    )


def test_camera_rtsp_url_builds_main_stream():
    assert camera_rtsp_url(stored_camera(), "main").endswith("/201")


def test_masked_rtsp_url_hides_password():
    assert masked_rtsp_url(stored_camera()) == "rtsp://ad%40min:****@10.0.0.5:554/Streaming/Channels/202"


def test_masked_rtsp_url_builds_main_stream():
    assert masked_rtsp_url(stored_camera(), "main").endswith("/201")
