"""Request/response bodies (Pydantic). These define the API contract in docs/frontend-spec.md."""

from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import EventStatus, UserRole, ZoneType


# Timestamps in responses are always UTC with an offset ("...+00:00"). SQLite (tests) drops the
# timezone, so naive values are marked as UTC here.
UTCDateTime = Annotated[datetime, AfterValidator(lambda d: d if d.tzinfo else d.replace(tzinfo=timezone.utc))]


class ORMModel(BaseModel):
    # Lets us return SQLAlchemy objects directly: UserOut.model_validate(user)
    model_config = ConfigDict(from_attributes=True)


# ---------- Auth ----------

class RegisterIn(BaseModel):
    email: EmailStr
    # bcrypt only looks at the first 72 bytes, so cap the length.
    password: str = Field(min_length=8, max_length=72)
    full_name: str | None = Field(default=None, max_length=120)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(ORMModel):
    id: int
    email: str
    full_name: str | None
    role: UserRole
    store_id: int | None
    created_at: UTCDateTime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Stores ----------

class StoreIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    address: str | None = Field(default=None, max_length=255)


class StoreUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    address: str | None = Field(default=None, max_length=255)


class StoreOut(ORMModel):
    id: int
    name: str
    address: str | None
    has_api_key: bool
    created_at: UTCDateTime


class StoreCreatedOut(StoreOut):
    api_key: str  # shown only once, right after creating the store


class ApiKeyOut(BaseModel):
    api_key: str  # shown once; only its hash is stored


# ---------- Cameras ----------

class CameraIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    ip: str = Field(min_length=1, max_length=64)
    port: int = Field(default=554, ge=1, le=65535)
    channel: int = Field(default=1, ge=1, le=64)
    rtsp_username: str = Field(min_length=1, max_length=64)
    rtsp_password: str = Field(min_length=1, max_length=128)
    threshold: float = Field(default=0.5, ge=0, le=1)
    is_active: bool = True


class CameraUpdate(BaseModel):
    """All fields optional. Leave rtsp_password out to keep the current one."""
    name: str | None = Field(default=None, min_length=1, max_length=120)
    ip: str | None = Field(default=None, min_length=1, max_length=64)
    port: int | None = Field(default=None, ge=1, le=65535)
    channel: int | None = Field(default=None, ge=1, le=64)
    rtsp_username: str | None = Field(default=None, min_length=1, max_length=64)
    rtsp_password: str | None = Field(default=None, min_length=1, max_length=128)
    threshold: float | None = Field(default=None, ge=0, le=1)
    is_active: bool | None = None


class CameraOut(BaseModel):
    id: int
    name: str
    ip: str
    port: int
    channel: int
    rtsp_username: str
    threshold: float
    is_active: bool
    online: bool
    last_seen_at: UTCDateTime | None
    has_snapshot: bool
    rtsp_url_sub: str   # password masked as ****
    rtsp_url_main: str  # password masked as ****
    created_at: UTCDateTime


# ---------- Zones ----------

class ZoneIn(BaseModel):
    type: ZoneType
    name: str | None = Field(default=None, max_length=120)
    # [[x, y], ...] with x, y in 0..1 (fraction of image width/height); at least a triangle.
    polygon: list[list[float]] = Field(min_length=3)

    @field_validator("polygon")
    @classmethod
    def check_points(cls, polygon: list[list[float]]) -> list[list[float]]:
        for point in polygon:
            if len(point) != 2 or not all(0 <= v <= 1 for v in point):
                raise ValueError("each point must be [x, y] with values between 0 and 1")
        return polygon


class ZoneOut(ORMModel):
    id: int
    camera_id: int
    type: ZoneType
    name: str | None
    polygon: list[list[float]]


# ---------- Events ----------

class EventOut(BaseModel):
    id: int
    camera_id: int
    camera_name: str
    started_at: UTCDateTime
    score: float
    status: EventStatus
    has_clip: bool
    has_snapshot: bool
    reviewed_by: int | None
    reviewed_at: UTCDateTime | None
    created_at: UTCDateTime


class EventList(BaseModel):
    items: list[EventOut]
    total: int


class ReviewIn(BaseModel):
    status: Literal["confirmed", "dismissed"]


# ---------- Edge agent ----------

class AgentCamera(BaseModel):
    id: int
    name: str
    threshold: float
    rtsp_url_sub: str   # real password included: only the store's own agent gets this
    rtsp_url_main: str
    zones: list[ZoneOut]


class AgentConfig(BaseModel):
    store_id: int
    store_name: str
    cameras: list[AgentCamera]
