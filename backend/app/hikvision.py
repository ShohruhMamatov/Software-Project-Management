"""Hikvision RTSP URL builder.

Hikvision format:  rtsp://<user>:<pass>@<ip>:<port>/Streaming/Channels/<channel><stream>
  stream "01" = main stream (full quality, used for saved clips)
  stream "02" = sub-stream  (low resolution, used for ML)
  e.g. channel 1 sub-stream -> /Streaming/Channels/102, channel 3 main -> /Streaming/Channels/301
"""

from typing import Literal
from urllib.parse import quote

from app.models import Camera
from app.security import decrypt_secret

Stream = Literal["main", "sub"]
STREAM_CODES: dict[str, str] = {"main": "01", "sub": "02"}


def channel_path(channel: int, stream: Stream) -> str:
    return f"/Streaming/Channels/{channel}{STREAM_CODES[stream]}"


def build_rtsp_url(ip: str, port: int, channel: int, username: str, password: str, stream: Stream = "sub") -> str:
    # Passwords often contain @ : / # which would break the URL, so percent-encode them.
    creds = f"{quote(username, safe='')}:{quote(password, safe='')}@"
    return f"rtsp://{creds}{ip}:{port}{channel_path(channel, stream)}"


def camera_rtsp_url(camera: Camera, stream: Stream = "sub") -> str:
    """Full URL with the real (decrypted) password. Only ever sent to the store's edge agent."""
    password = decrypt_secret(camera.rtsp_password_encrypted)
    return build_rtsp_url(camera.ip, camera.port, camera.channel, camera.rtsp_username, password, stream)


def masked_rtsp_url(camera: Camera, stream: Stream = "sub") -> str:
    """Same URL with the password hidden, safe to show in the dashboard."""
    user = quote(camera.rtsp_username, safe="")
    return f"rtsp://{user}:****@{camera.ip}:{camera.port}{channel_path(camera.channel, stream)}"
