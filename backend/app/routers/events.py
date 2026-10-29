"""Event log and human review (confirm / dismiss). Events themselves are created by the edge agent."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.media import file_response
from app.models import Camera, Event, EventStatus, Store, User
from app.schemas import EventList, EventOut, ReviewIn
from app.security import get_current_store, get_current_user

router = APIRouter(prefix="/events", tags=["events"])


def event_out(event: Event) -> EventOut:
    return EventOut(
        id=event.id, camera_id=event.camera_id, camera_name=event.camera.name,
        started_at=event.started_at, score=event.score, status=event.status,
        has_clip=event.clip_path is not None, has_snapshot=event.snapshot_path is not None,
        reviewed_by=event.reviewed_by, reviewed_at=event.reviewed_at, created_at=event.created_at,
    )


def get_store_event(event_id: int, store: Store, db: Session) -> Event:
    event = db.get(Event, event_id)
    if event is None or event.camera.store_id != store.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")
    return event


@router.get("", response_model=EventList)
def list_events(
    status_: EventStatus | None = Query(default=None, alias="status"),
    camera_id: int | None = None,
    after_id: int | None = Query(default=None, description="Only events with id > after_id (for live polling)"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    store: Store = Depends(get_current_store),
    db: Session = Depends(get_db),
):
    """Events of the user's store, newest first."""
    query = select(Event).join(Camera).where(Camera.store_id == store.id)
    if status_ is not None:
        query = query.where(Event.status == status_)
    if camera_id is not None:
        query = query.where(Event.camera_id == camera_id)
    if after_id is not None:
        query = query.where(Event.id > after_id)

    total = db.scalar(select(func.count()).select_from(query.subquery()))
    events = db.scalars(query.order_by(Event.started_at.desc(), Event.id.desc()).limit(limit).offset(offset))
    return EventList(items=[event_out(e) for e in events], total=total)


@router.get("/{event_id}", response_model=EventOut)
def get_event(event_id: int, store: Store = Depends(get_current_store), db: Session = Depends(get_db)):
    return event_out(get_store_event(event_id, store, db))


@router.post("/{event_id}/review", response_model=EventOut)
def review_event(event_id: int, body: ReviewIn, user: User = Depends(get_current_user),
                 store: Store = Depends(get_current_store), db: Session = Depends(get_db)):
    """Owner or staff marks the event as confirmed (real) or dismissed (false alarm). Can be changed later."""
    event = get_store_event(event_id, store, db)
    event.status = EventStatus(body.status)
    event.reviewed_by = user.id
    event.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(event)
    return event_out(event)


@router.get("/{event_id}/clip", response_class=Response,
            responses={200: {"content": {"video/webm": {}, "video/mp4": {}}}, 404: {"description": "No clip"}})
def get_event_clip(event_id: int, store: Store = Depends(get_current_store), db: Session = Depends(get_db)):
    return file_response(get_store_event(event_id, store, db).clip_path)


@router.get("/{event_id}/snapshot", response_class=Response,
            responses={200: {"content": {"image/jpeg": {}}}, 404: {"description": "No snapshot"}})
def get_event_snapshot(event_id: int, store: Store = Depends(get_current_store), db: Session = Depends(get_db)):
    return file_response(get_store_event(event_id, store, db).snapshot_path)
