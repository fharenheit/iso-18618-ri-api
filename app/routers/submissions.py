from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import MAX_XML_SIZE
from app.database import get_db
from app.models.schemas import (
    FileListItem,
    SubmissionDetail,
    SubmissionListItem,
    SubmissionSummary,
    OriginatorInfo,
    AddressInfo,
    PatientInfo,
    DentistInfo,
    OrderInfo,
    RestorationInfo,
    FileInfo,
)
from app.services import storage, submission_service
from app.services.xml_parser import IDSParseError, parse_ids_xml

router = APIRouter(prefix="/api/v1/submissions", tags=["submissions"])


@router.post("", response_model=SubmissionSummary, status_code=201)
async def create_submission(
    ids_xml: UploadFile = File(..., description="IDS XML file (.ids)"),
    files: list[UploadFile] = File(default=[], description="Attached files (STL, PDF, JPG, etc.)"),
    db: Session = Depends(get_db),
):
    """Upload an IDS XML document with optional attached files."""
    xml_bytes = await ids_xml.read()
    if len(xml_bytes) > MAX_XML_SIZE:
        raise HTTPException(status_code=413, detail="IDS XML exceeds 2MB limit (ISO 18618 Clause 8)")

    try:
        parsed = parse_ids_xml(xml_bytes)
    except IDSParseError as e:
        raise HTTPException(status_code=422, detail=str(e))

    submission_data = parsed.get("submission")
    if not submission_data:
        raise HTTPException(status_code=422, detail="IDS document must contain a <Submission> element")

    submission_uuid = submission_data["uuid"]
    if not submission_uuid:
        raise HTTPException(status_code=422, detail="Submission UUID is required")

    if submission_service.get_submission_by_uuid(db, submission_uuid):
        raise HTTPException(status_code=409, detail=f"Submission {submission_uuid} already exists")

    # Save to DB
    sub = submission_service.create_submission(db, parsed, xml_bytes.decode("utf-8"))

    # Save files to disk and mark in DB
    storage.save_submission(submission_uuid, xml_bytes, parsed)
    files_uploaded = 0
    for f in files:
        if f.filename:
            content = await f.read()
            file_path = storage.save_file(submission_uuid, f.filename, content)
            submission_service.mark_file_uploaded(db, sub.id, f.filename, str(file_path), len(content))
            files_uploaded += 1

    originator = OriginatorInfo(uuid="", name="Unknown")
    if sub.originator:
        originator = OriginatorInfo(
            uuid=sub.originator.uuid,
            name=sub.originator.name,
            business_type=sub.originator.business_type,
        )

    expected_count = len(submission_data.get("files", []))

    return SubmissionSummary(
        submission_id=submission_uuid,
        ids_uuid=parsed["ids_uuid"],
        ids_version=parsed["ids_version"],
        originator=originator,
        orders_count=len(sub.orders),
        files_uploaded=files_uploaded,
        files_expected=expected_count,
        created_at=sub.created_at,
    )


@router.get("", response_model=list[SubmissionListItem])
async def list_submissions(db: Session = Depends(get_db)):
    """List all submissions."""
    subs = submission_service.list_submissions(db)
    result = []
    for s in subs:
        orig_name = s.originator.name if s.originator else "Unknown"
        uploaded_count = sum(1 for f in s.uploaded_files if f.is_uploaded) if s.uploaded_files else 0
        result.append(SubmissionListItem(
            submission_id=s.submission_uuid,
            ids_uuid=s.ids_uuid,
            ids_version=s.ids_version,
            originator_name=orig_name,
            orders_count=len(s.orders),
            files_count=uploaded_count,
            created_at=s.created_at,
        ))
    return result


@router.get("/{submission_id}", response_model=SubmissionDetail)
async def get_submission(submission_id: str, db: Session = Depends(get_db)):
    """Get detailed information about a submission."""
    sub = submission_service.get_submission_by_uuid(db, submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    originator = OriginatorInfo(uuid="", name="Unknown")
    address = None
    if sub.originator:
        originator = OriginatorInfo(
            uuid=sub.originator.uuid,
            name=sub.originator.name,
            business_type=sub.originator.business_type,
        )
        address = AddressInfo(
            street1=sub.originator.street1,
            street2=sub.originator.street2,
            city=sub.originator.city,
            state=sub.originator.state,
            postal_code=sub.originator.postal_code,
            country=sub.originator.country,
        )

    patients = [
        PatientInfo(
            uuid=p.uuid, first_name=p.first_name, last_name=p.last_name,
            date_of_birth=str(p.date_of_birth) if p.date_of_birth else None,
            gender=p.gender,
        )
        for p in sub.patients
    ]

    dentists = [
        DentistInfo(uuid=d.uuid, first_name=d.first_name, last_name=d.last_name, license_number=d.license_number)
        for d in sub.dentists
    ]

    orders = []
    for o in sub.orders:
        restorations = [
            RestorationInfo(uuid=r.uuid, tooth_number=r.tooth_number, type=r.type, material=r.material, shade=r.shade)
            for r in o.restorations
        ]
        orders.append(OrderInfo(
            uuid=o.uuid, patient_uuid=o.patient_uuid, dentist_uuid=o.dentist_uuid,
            priority=o.priority,
            date_created=str(o.date_created) if o.date_created else None,
            restorations=restorations,
        ))

    expected_files = [
        FileInfo(uuid=f.uuid, file_name=f.file_name, file_type=f.file_type,
                 file_size=str(f.file_size) if f.file_size else None, description=f.description)
        for f in sub.uploaded_files
    ]
    uploaded_names = [f.file_name for f in sub.uploaded_files if f.is_uploaded]

    return SubmissionDetail(
        submission_id=sub.submission_uuid,
        ids_uuid=sub.ids_uuid,
        ids_version=sub.ids_version,
        originator=originator,
        originator_address=address,
        patients=patients,
        dentists=dentists,
        orders=orders,
        files_expected=expected_files,
        files_uploaded=uploaded_names,
        created_at=sub.created_at,
    )


@router.get("/{submission_id}/xml")
async def get_submission_xml(submission_id: str, db: Session = Depends(get_db)):
    """Download the original IDS XML document."""
    sub = submission_service.get_submission_by_uuid(db, submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    xml_path = storage._submission_dir(submission_id) / "document.ids"
    if not xml_path.exists():
        raise HTTPException(status_code=404, detail="XML file not found on disk")
    return FileResponse(path=xml_path, media_type="application/xml", filename=f"{submission_id}.ids")


@router.get("/{submission_id}/files", response_model=list[FileListItem])
async def list_submission_files(submission_id: str, db: Session = Depends(get_db)):
    """List files attached to a submission."""
    sub = submission_service.get_submission_by_uuid(db, submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    return [
        FileListItem(
            file_name=f.file_name,
            file_size=f.file_size or 0,
            in_catalog=bool(f.uuid),
        )
        for f in sub.uploaded_files
        if f.is_uploaded
    ]


@router.get("/{submission_id}/files/{filename}")
async def get_submission_file(submission_id: str, filename: str):
    """Download a specific file from a submission."""
    file_path = storage.get_file_path(submission_id, filename)
    if not file_path:
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=file_path, filename=filename)


@router.delete("/{submission_id}", status_code=204)
async def delete_submission(submission_id: str, db: Session = Depends(get_db)):
    """Delete a submission and all associated files."""
    if not submission_service.delete_submission(db, submission_id):
        raise HTTPException(status_code=404, detail="Submission not found")
    storage.delete_submission(submission_id)
