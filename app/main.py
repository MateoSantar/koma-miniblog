import asyncio
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from app.core.db import Base, engine
from app.api.v1.posts.router import router as post_router
from app.api.v1.auth.router import router as auth_router
from app.api.v1.uploads.router import router as upload_router
from app.services.file_storage import MEDIA_DIR
from app.services.noticias import actualizar_periodicamente
from fastapi.staticfiles import StaticFiles


@asynccontextmanager
async def lifespan(app: FastAPI):
    tarea = None
    if os.getenv("NOTICIAS_AUTO", "1") == "1":
        tarea = asyncio.create_task(actualizar_periodicamente())
    yield
    if tarea:
        tarea.cancel()


def create_app() -> FastAPI:
    app = FastAPI(title="Mini Blog", lifespan=lifespan)
    Base.metadata.create_all(bind=engine)  # dev

    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(post_router)
    app.include_router(upload_router)  # Add the upload router

    os.makedirs(MEDIA_DIR, exist_ok=True)  # Ensure media directory exists
    app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")
    app.mount("/", StaticFiles(directory="app/static", html=True), name="frontend")

    return app


app = create_app()
