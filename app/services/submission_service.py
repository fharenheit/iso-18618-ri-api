from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload, subqueryload

from app.models.db_models import (
    Dentist,
    Order,
    Originator,
    Patient,
    Restoration,
    Submission,
    UploadedFile,
)


def create_submission(
    db: Session,
    parsed: dict,
    xml_content: str,
) -> Submission:
    """Create a Submission and all related records from parsed IDS XML."""
    sub_data = parsed["submission"]

    submission = Submission(
        ids_uuid=parsed["ids_uuid"],
        ids_version=parsed["ids_version"],
        submission_uuid=sub_data["uuid"],
        date_submitted=_parse_dt(sub_data.get("date_submitted")),
        date_received=_parse_dt(sub_data.get("date_received")),
        xml_content=xml_content,
    )
    db.add(submission)
    db.flush()  # get submission.id

    # Originator
    orig = sub_data.get("originator", {})
    orig_info = orig.get("info")
    if orig_info:
        info = _to_dict(orig_info)
        addr = _to_dict(orig.get("address")) or {}
        db.add(Originator(
            submission_id=submission.id,
            uuid=info.get("uuid", ""),
            name=info.get("name", ""),
            business_type=info.get("business_type"),
            street1=addr.get("street1"),
            street2=addr.get("street2"),
            city=addr.get("city"),
            state=addr.get("state"),
            postal_code=addr.get("postal_code"),
            country=addr.get("country"),
        ))

    # Patients
    for p in sub_data.get("patients", []):
        p = _to_dict(p)
        db.add(Patient(
            submission_id=submission.id,
            uuid=p.get("uuid", ""),
            first_name=p.get("first_name"),
            last_name=p.get("last_name"),
            date_of_birth=_parse_date(p.get("date_of_birth")),
            gender=p.get("gender"),
        ))

    # Dentists
    for d in sub_data.get("dentists", []):
        d = _to_dict(d)
        db.add(Dentist(
            submission_id=submission.id,
            uuid=d.get("uuid", ""),
            first_name=d.get("first_name"),
            last_name=d.get("last_name"),
            license_number=d.get("license_number"),
        ))

    # Orders + Restorations
    for o in sub_data.get("orders", []):
        o = _to_dict(o)
        order = Order(
            submission_id=submission.id,
            uuid=o.get("uuid", ""),
            patient_uuid=o.get("patient_uuid"),
            dentist_uuid=o.get("dentist_uuid"),
            priority=o.get("priority"),
            date_created=_parse_dt(o.get("date_created")),
        )
        db.add(order)
        db.flush()

        for r in o.get("restorations", []):
            r = _to_dict(r)
            db.add(Restoration(
                order_id=order.id,
                uuid=r.get("uuid", ""),
                tooth_number=r.get("tooth_number"),
                type=r.get("type"),
                material=r.get("material"),
                shade=r.get("shade"),
            ))

    # Files from FileCatalog (expected files, not yet uploaded)
    for f in sub_data.get("files", []):
        f = _to_dict(f)
        db.add(UploadedFile(
            submission_id=submission.id,
            uuid=f.get("uuid", ""),
            file_name=f.get("file_name", ""),
            file_type=f.get("file_type"),
            file_size=int(f["file_size"]) if f.get("file_size") else None,
            description=f.get("description"),
            is_uploaded=False,
        ))

    db.commit()
    db.refresh(submission)
    return submission


def mark_file_uploaded(db: Session, submission_id: int, file_name: str, storage_path: str, actual_size: int):
    """Mark a catalog file as uploaded, or create a new record if not in catalog."""
    file_rec = (
        db.query(UploadedFile)
        .filter(UploadedFile.submission_id == submission_id, UploadedFile.file_name == file_name)
        .first()
    )
    if file_rec:
        file_rec.is_uploaded = True
        file_rec.storage_path = storage_path
        file_rec.file_size = actual_size
    else:
        db.add(UploadedFile(
            submission_id=submission_id,
            uuid="",
            file_name=file_name,
            file_size=actual_size,
            storage_path=storage_path,
            is_uploaded=True,
        ))
    db.commit()


def get_submission_by_uuid(db: Session, submission_uuid: str) -> Submission | None:
    return (
        db.query(Submission)
        .options(
            joinedload(Submission.originator),
            joinedload(Submission.patients),
            joinedload(Submission.dentists),
            joinedload(Submission.orders).joinedload(Order.restorations),
            joinedload(Submission.uploaded_files),
        )
        .filter(Submission.submission_uuid == submission_uuid)
        .first()
    )


def list_submissions(db: Session, offset: int = 0, limit: int = 50) -> list[Submission]:
    return (
        db.query(Submission)
        .options(
            joinedload(Submission.originator),
            subqueryload(Submission.orders),
            subqueryload(Submission.uploaded_files),
        )
        .order_by(Submission.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def count_submissions(db: Session) -> int:
    return db.query(func.count(Submission.id)).scalar()


def delete_submission(db: Session, submission_uuid: str) -> bool:
    sub = db.query(Submission).filter(Submission.submission_uuid == submission_uuid).first()
    if not sub:
        return False
    db.delete(sub)
    db.commit()
    return True


def get_dashboard_stats(db: Session) -> dict:
    total_submissions = db.query(func.count(Submission.id)).scalar()
    total_orders = db.query(func.count(Order.id)).scalar()
    total_restorations = db.query(func.count(Restoration.id)).scalar()
    total_files = db.query(func.count(UploadedFile.id)).scalar()
    files_uploaded = db.query(func.count(UploadedFile.id)).filter(UploadedFile.is_uploaded.is_(True)).scalar()
    return {
        "total_submissions": total_submissions,
        "total_orders": total_orders,
        "total_restorations": total_restorations,
        "total_files": total_files,
        "files_uploaded": files_uploaded,
    }


def _to_dict(obj):
    if obj is None:
        return {}
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, dict):
        return obj
    return {}


def _parse_dt(val) -> datetime | None:
    if not val:
        return None
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _parse_date(val) -> date | None:
    if not val:
        return None
    try:
        return date.fromisoformat(val)
    except (ValueError, AttributeError):
        return None
