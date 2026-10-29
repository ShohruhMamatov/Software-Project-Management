"""Cameras of the user's store and their checkout/exit zones."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.hikvision import masked_rtsp_url
from app.media import delete_file, file_response
from app.models import Camera, Store, User, Zone
from app.schemas import CameraIn, CameraOut, CameraUpdate, ZoneIn, ZoneOut
from app.security import encrypt_secret, get_current_store, require_owner

router = APIRouter(prefix="/cameras", tags=["cameras"])


def is_online(last_seen_at: datetime | None) -> bool:
    if last_seen_at is None:
        return False
    if last_seen_at.tzinfo is None:  # SQLite (tests) drops the timezone; values are UTC
        last_seen_at = last_seen_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - last_seen_at < timedelta(seconds=settings.camera_online_seconds)


def camera_out(camera: Camera) -> CameraOut:
    return CameraOut(
        id=camera.id, name=camera.name, ip=camera.ip, port=camera.port, channel=camera.channel,
        rtsp_username=camera.rtsp_username, threshold=camera.threshold, is_active=camera.is_active,
        online=is_online(camera.last_seen_at), last_seen_at=camera.last_seen_at,
        has_snapshot=camera.snapshot_path is not None,
        rtsp_url_sub=masked_rtsp_url(camera, "sub"), rtsp_url_main=masked_rtsp_url(camera, "main"),
        created_at=camera.created_at,
    )


def get_store_camera(camera_id: int, store: Store, db: Session) -> Camera:
    """The camera, if it belongs to this store; otherwise 404 (don't reveal other stores' cameras)."""
    camera = db.get(Camera, camera_id)
    if camera is None or camera.store_id != store.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Camera not found")
    return camera


# ---------- Cameras ----------

@router.get("", response_model=list[CameraOut])
def list_cameras(store: Store = Depends(get_current_store), db: Session = Depends(get_db)):
    cameras = db.scalars(select(Camera).where(Camera.store_id == store.id).order_by(Camera.id))
    return [camera_out(c) for c in cameras]


@router.post("", response_model=CameraOut, status_code=status.HTTP_201_CREATED)
def create_camera(body: CameraIn, _: User = Depends(require_owner),
                  store: Store = Depends(get_current_store), db: Session = Depends(get_db)):
    data = body.model_dump(exclude={"rtsp_password"})
    camera = Camera(**data, store_id=store.id, rtsp_password_encrypted=encrypt_secret(body.rtsp_password))
    db.add(camera)
    db.commit()
    db.refresh(camera)
    return camera_out(camera)


@router.get("/{camera_id}", response_model=CameraOut)
def get_camera(camera_id: int, store: Store = Depends(get_current_store), db: Session = Depends(get_db)):
    return camera_out(get_store_camera(camera_id, store, db))


@router.patch("/{camera_id}", response_model=CameraOut)
def update_camera(camera_id: int, body: CameraUpdate, _: User = Depends(require_owner),
                  store: Store = Depends(get_current_store), db: Session = Depends(get_db)):
    camera = get_store_camera(camera_id, store, db)
    data = body.model_dump(exclude_unset=True)
    if (password := data.pop("rtsp_password", None)) is not None:
        camera.rtsp_password_encrypted = encrypt_secret(password)
    for field, value in data.items():
        if value is not None:
            setattr(camera, field, value)
    db.commit()
    db.refresh(camera)
    return camera_out(camera)


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_camera(camera_id: int, _: User = Depends(require_owner),
                  store: Store = Depends(get_current_store), db: Session = Depends(get_db)):
    camera = get_store_camera(camera_id, store, db)
    # Remove media files too; the DB rows of zones/events go via ON DELETE CASCADE.
    delete_file(camera.snapshot_path)
    for event in camera.events:
        delete_file(event.clip_path)
        delete_file(event.snapshot_path)
    db.delete(camera)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{camera_id}/snapshot", response_class=Response,
            responses={200: {"content": {"image/jpeg": {}}}, 404: {"description": "No snapshot yet"}})
def get_camera_snapshot(camera_id: int, store: Store = Depends(get_current_store), db: Session = Depends(get_db)):
    """Latest frame sent by the edge agent; the background for drawing zones."""
    return file_response(get_store_camera(camera_id, store, db).snapshot_path)


# ---------- Zones ----------

@router.get("/{camera_id}/zones", response_model=list[ZoneOut])
def list_zones(camera_id: int, store: Store = Depends(get_current_store), db: Session = Depends(get_db)):
    return get_store_camera(camera_id, store, db).zones


@router.put("/{camera_id}/zones", response_model=list[ZoneOut])
def replace_zones(camera_id: int, body: list[ZoneIn], _: User = Depends(require_owner),
                  store: Store = Depends(get_current_store), db: Session = Depends(get_db)):
    """Replace all zones of the camera at once (the zone editor saves the whole drawing)."""
    camera = get_store_camera(camera_id, store, db)
    camera.zones.clear()  # delete-orphan cascade removes the old rows
    camera.zones.extend(Zone(type=z.type, name=z.name, polygon=z.polygon) for z in body)
    db.commit()
    db.refresh(camera)
    return camera.zones
