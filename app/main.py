from pathlib import Path

from fastapi import FastAPI
from fastapi.templating import Jinja2Templates

from app.routers import submissions, views

app = FastAPI(
    title="ISO 18618 Reference Implementation API",
    description="API for receiving and managing IDS (Interface for Dental CAD/CAM Systems) XML documents per ISO 18618.",
    version="0.2.0",
)

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
app.state.templates = templates

app.include_router(views.router)
app.include_router(submissions.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
