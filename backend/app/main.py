"""FastAPI entry point. Run locally with:  uvicorn app.main:app --reload"""

from fastapi import FastAPI

from app.config import settings

app = FastAPI(title=settings.app_name)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Liveness check used by Docker/CI: returns 200 if the API process is up."""
    return {"status": "ok"}
