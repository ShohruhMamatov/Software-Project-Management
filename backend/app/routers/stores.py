"""The owner's store and the API key its edge agent uses."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Store, User
from app.schemas import ApiKeyOut, StoreCreatedOut, StoreIn, StoreOut, StoreUpdate
from app.security import get_current_store, hash_api_key, new_api_key, require_owner

router = APIRouter(prefix="/stores", tags=["stores"])


def store_out(store: Store) -> StoreOut:
    return StoreOut(id=store.id, name=store.name, address=store.address,
                    has_api_key=store.api_key_hash is not None, created_at=store.created_at)


@router.post("", response_model=StoreCreatedOut, status_code=status.HTTP_201_CREATED)
def create_store(body: StoreIn, user: User = Depends(require_owner), db: Session = Depends(get_db)):
    if user.store_id is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "You already have a store")

    api_key = new_api_key()
    store = Store(name=body.name, address=body.address, api_key_hash=hash_api_key(api_key))
    db.add(store)
    db.flush()  # assigns store.id
    user.store_id = store.id
    db.commit()
    db.refresh(store)
    return StoreCreatedOut(**store_out(store).model_dump(), api_key=api_key)


@router.get("/me", response_model=StoreOut)
def get_my_store(store: Store = Depends(get_current_store)):
    return store_out(store)


@router.patch("/me", response_model=StoreOut)
def update_my_store(body: StoreUpdate, _: User = Depends(require_owner),
                    store: Store = Depends(get_current_store), db: Session = Depends(get_db)):
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(store, field, value)
    db.commit()
    db.refresh(store)
    return store_out(store)


@router.post("/me/api-key", response_model=ApiKeyOut)
def rotate_api_key(_: User = Depends(require_owner), store: Store = Depends(get_current_store),
                   db: Session = Depends(get_db)):
    """Make a new edge-agent key. The old key stops working immediately."""
    api_key = new_api_key()
    store.api_key_hash = hash_api_key(api_key)
    db.commit()
    return ApiKeyOut(api_key=api_key)
