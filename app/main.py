from fastapi import FastAPI

from app.routers import submissions

app = FastAPI(
    title="ISO 18618 Reference Implementation API",
    description="API for receiving and managing IDS (Interface for Dental CAD/CAM Systems) XML documents per ISO 18618.",
    version="0.1.0",
)

app.include_router(submissions.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
