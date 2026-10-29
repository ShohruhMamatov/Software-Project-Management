"""FastAPI entry point. Run locally with:  uvicorn app.main:app --reload
Interactive API docs: http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import agent, auth, cameras, events, stores

app = FastAPI(title=settings.app_name)

# Let the React dev server (another origin) call the API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(stores.router)
app.include_router(cameras.router)
app.include_router(events.router)
app.include_router(agent.router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Liveness check used by Docker/CI: returns 200 if the API process is up."""
    return {"status": "ok"}
