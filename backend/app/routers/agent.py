"""Endpoints for the store's edge agent. Authenticated with the store API key (X-API-Key header)."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.hikvision import camera_rtsp_url
from app.media import CLIP_EXTS, IMAGE_EXTS, delete_file, save_upload
from app.models import Camera, Event, EventStatus, Store
from app.notify import notify_new_event
from app.routers.cameras import get_store_camera
from app.routers.events import event_out
from app.schemas import AgentCamera, AgentConfig, EventOut, ZoneOut
from app.security import get_agent_store

router = APIRouter(prefix="/agent", tags=["edge agent"])


@router.get("/config", response_model=AgentConfig)
def get_config(store: Store = Depends(get_agent_store), db: Session = Depends(get_db)):
    """Everything the agent needs to start: active cameras, their RTSP URLs, thresholds and zones."""
    cameras = db.scalars(
        select(Camera).where(Camera.store_id == store.id, Camera.is_active.is_(True)).order_by(Camera.id)
    )
    return AgentConfig(
        store_id=store.id,
        store_name=store.name,
        cameras=[
            AgentCamera(
                id=c.id, name=c.name, threshold=c.threshold,
                rtsp_url_sub=camera_rtsp_url(c, "sub"), rtsp_url_main=camera_rtsp_url(c, "main"),
                zones=[ZoneOut.model_validate(z) for z in c.zones],
            )
            for c in cameras
        ],
    )


@router.post("/cameras/{camera_id}/heartbeat", status_code=status.HTTP_204_NO_CONTENT)
def heartbeat(camera_id: int, snapshot: UploadFile | None = File(default=None),
              store: Store = Depends(get_agent_store), db: Session = Depends(get_db)):
    """'This camera is streaming.' Send every ~30 s; attach a fresh JPEG now and then for the zone editor."""
    camera = get_store_camera(camera_id, store, db)
    camera.last_seen_at = datetime.now(timezone.utc)
    if snapshot is not None:
        old = camera.snapshot_path
        camera.snapshot_path = save_upload(snapshot, "snapshots", IMAGE_EXTS)
        delete_file(old)
    db.commit()


@router.post("/events", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def create_event(
    camera_id: int = Form(...),
    started_at: datetime = Form(..., description="ISO 8601 with timezone, e.g. 2026-10-29T14:03:12+05:00"),
    score: float = Form(..., ge=0, le=1),
    clip: UploadFile | None = File(default=None, description=".webm or .mp4"),
    snapshot: UploadFile | None = File(default=None, description=".jpg or .png"),
    store: Store = Depends(get_agent_store),
    db: Session = Depends(get_db),
):
    """The agent flagged something: store it as a pending event and send alerts."""
    camera = get_store_camera(camera_id, store, db)
    event = Event(
        camera_id=camera.id, started_at=started_at, score=score, status=EventStatus.pending,
        clip_path=save_upload(clip, "clips", CLIP_EXTS) if clip else None,
        snapshot_path=save_upload(snapshot, "events", IMAGE_EXTS) if snapshot else None,
    )
    camera.last_seen_at = datetime.now(timezone.utc)
    db.add(event)
    db.commit()
    db.refresh(event)
    notify_new_event(event)
    return event_out(event)
