from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import submission_service

router = APIRouter(tags=["views"])


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    stats = submission_service.get_dashboard_stats(db)
    recent = submission_service.list_submissions(db, limit=10)
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"stats": stats, "recent": recent, "active_page": "dashboard"},
    )


@router.get("/submissions", response_class=HTMLResponse)
async def submissions_list(request: Request, db: Session = Depends(get_db)):
    submissions = submission_service.list_submissions(db, limit=100)
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="submissions.html",
        context={"submissions": submissions, "active_page": "submissions"},
    )


@router.get("/submissions/{submission_uuid}", response_class=HTMLResponse)
async def submission_detail(request: Request, submission_uuid: str, db: Session = Depends(get_db)):
    sub = submission_service.get_submission_by_uuid(db, submission_uuid)
    if not sub:
        return HTMLResponse("<h1>404 Not Found</h1>", status_code=404)
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="submission_detail.html",
        context={"sub": sub, "active_page": "submissions"},
    )
