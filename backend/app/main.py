from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_error_handlers
from app.api.v1 import router as api_router
from app.config import settings
from app.sources.base import close_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Release the ATS adapters' shared keep-alive connection pool.
    await close_client()


app = FastAPI(title="Career Engine", version="0.1.0", lifespan=lifespan)

# Normalize every error into the shared envelope before it reaches a client.
register_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "Hello Career Engine"}


@app.get("/health")
async def health():
    return {"status": "ok"}
