"""SQLAlchemy models for LUMI. See docs/db-schema.md for the ER diagram.

Enums are stored as VARCHAR + CHECK constraint (native_enum=False) instead of
Postgres ENUM types, because those are awkward to change in Alembic migrations.
"""

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ---------- Enums ----------

class UserRole(str, enum.Enum):
    owner = "owner"  # manages the store, cameras and staff
    staff = "staff"  # reviews alerts


class ZoneType(str, enum.Enum):
    checkout = "checkout"
    exit = "exit"


class EventStatus(str, enum.Enum):
    pending = "pending"      # waiting for a human to review
    confirmed = "confirmed"  # staff agreed it is suspicious
    dismissed = "dismissed"  # false alarm


def _enum(enum_cls: type[enum.Enum], name: str) -> Enum:
    """VARCHAR column limited to the enum's values (stores the value, e.g. 'owner')."""
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=20,
        values_callable=lambda e: [m.value for m in e],
    )


# ---------- Tables ----------

class Store(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    address: Mapped[str | None] = mapped_column(String(255))
    # Hash of the API key the store's edge agent sends in X-API-Key (never store the raw key).
    api_key_hash: Mapped[str | None] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[list["User"]] = relationship(back_populates="store")
    cameras: Mapped[list["Camera"]] = relationship(back_populates="store", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(120))
    role: Mapped[UserRole] = mapped_column(_enum(UserRole, "user_role"), default=UserRole.owner)
    # The store this user works at. Nullable: an owner registers first, then creates a store.
    # (Multiple stores per account is a backlog item -> a store_members table later.)
    store_id: Mapped[int | None] = mapped_column(ForeignKey("stores.id", ondelete="SET NULL"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    store: Mapped[Store | None] = relationship(back_populates="users")


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))  # e.g. "Entrance"

    # Parts of the Hikvision RTSP URL:
    #   rtsp://<user>:<pass>@<ip>:<port>/Streaming/Channels/<channel><stream>
    # stream 02 (sub) is used for ML, 01 (main) for saved clips, so both are built from `channel`.
    ip: Mapped[str] = mapped_column(String(64))
    port: Mapped[int] = mapped_column(Integer, default=554)
    channel: Mapped[int] = mapped_column(Integer, default=1)
    rtsp_username: Mapped[str] = mapped_column(String(64))
    rtsp_password_encrypted: Mapped[str] = mapped_column(String(512))  # Fernet-encrypted, never plain text

    # Alert if the classifier score is >= threshold (adjustable sensitivity per camera).
    threshold: Mapped[float] = mapped_column(Float, default=0.5)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    store: Mapped[Store] = relationship(back_populates="cameras")
    zones: Mapped[list["Zone"]] = relationship(back_populates="camera", cascade="all, delete-orphan")
    events: Mapped[list["Event"]] = relationship(back_populates="camera", cascade="all, delete-orphan")


class Zone(Base):
    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id", ondelete="CASCADE"), index=True)
    type: Mapped[ZoneType] = mapped_column(_enum(ZoneType, "zone_type"))
    name: Mapped[str | None] = mapped_column(String(120))
    # Polygon points normalised to 0..1 so they work at any resolution: [[x, y], [x, y], ...]
    polygon: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    camera: Mapped[Camera] = relationship(back_populates="zones")


class Event(Base):
    """One flagged person/moment that a human must review."""

    __tablename__ = "events"
    __table_args__ = (
        # The event log is usually "events of camera X, newest first".
        Index("ix_events_camera_id_started_at", "camera_id", "started_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id", ondelete="CASCADE"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))  # when the behaviour was seen
    score: Mapped[float] = mapped_column(Float)  # VideoMAE "shoplifting" probability, 0..1
    status: Mapped[EventStatus] = mapped_column(
        _enum(EventStatus, "event_status"), default=EventStatus.pending, index=True
    )
    # Paths relative to MEDIA_DIR (files live on disk, not in the DB).
    clip_path: Mapped[str | None] = mapped_column(String(512))
    snapshot_path: Mapped[str | None] = mapped_column(String(512))

    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    camera: Mapped[Camera] = relationship(back_populates="events")
    reviewer: Mapped[User | None] = relationship()
