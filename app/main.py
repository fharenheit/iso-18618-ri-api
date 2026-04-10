import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

from app.config import SERVER_HOST, SERVER_PORT
from app.routers import submissions, views

logger = logging.getLogger("ids.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ISO 18618 IDS API starting on %s:%s", SERVER_HOST, SERVER_PORT)
    yield
    logger.info("ISO 18618 IDS API shutting down")


app = FastAPI(
    title="ISO 18618 Reference Implementation API",
    description="API for receiving and managing IDS (Interface for Dental CAD/CAM Systems) XML documents per ISO 18618.",
    version="0.2.0",
    lifespan=lifespan,
)

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
app.state.templates = templates

app.include_router(views.router)
app.include_router(submissions.router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(">>> %s %s", request.method, request.url.path)
    response = await call_next(request)
    logger.info("<<< %s %s [%d]", request.method, request.url.path, response.status_code)
    return response


@app.get("/health")
async def health():
    return {"status": "ok"}
