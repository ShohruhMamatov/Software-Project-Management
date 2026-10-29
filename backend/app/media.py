"""Clips and snapshots on disk. The DB stores only paths relative to MEDIA_DIR."""

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.config import settings

CLIP_EXTS = {".webm", ".mp4"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png"}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB is plenty for a ~10 s clip
CHUNK = 1024 * 1024


def media_root() -> Path:
    return Path(settings.media_dir).resolve()


def save_upload(upload: UploadFile, subdir: str, allowed_exts: set[str]) -> str:
    """Save an uploaded file under MEDIA_DIR/<subdir>/ with a random name; return the relative path."""
    ext = Path(upload.filename or "").suffix.lower()
    if ext not in allowed_exts:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"File type {ext or '?'} not allowed: {sorted(allowed_exts)}")

    rel_path = f"{subdir}/{uuid.uuid4().hex}{ext}"
    target = media_root() / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)

    size = 0
    with target.open("wb") as out:
        while chunk := upload.file.read(CHUNK):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                out.close()
                target.unlink(missing_ok=True)
                raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File too large")
            out.write(chunk)
    return rel_path


def delete_file(rel_path: str | None) -> None:
    if rel_path:
        (media_root() / rel_path).unlink(missing_ok=True)


def file_response(rel_path: str | None) -> FileResponse:
    """Stream a stored file, or 404 if there is none."""
    if not rel_path or not (media_root() / rel_path).is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
    return FileResponse(media_root() / rel_path)
