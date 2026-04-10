from datetime import datetime, timezone

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import MAX_XML_SIZE
from app.models.schemas import (
    AddressInfo,
    DentistInfo,
    FileListItem,
    OrderInfo,
    OriginatorInfo,
    PatientInfo,
    SubmissionDetail,
    SubmissionListItem,
    SubmissionSummary,
)
from app.services import storage
from app.services.xml_parser import IDSParseError, parse_ids_xml

router = APIRouter(prefix="/api/v1/submissions", tags=["submissions"])


@router.post("", response_model=SubmissionSummary, status_code=201)
async def create_submission(
    ids_xml: UploadFile = File(..., description="IDS XML file (.ids)"),
    files: list[UploadFile] = File(default=[], description="Attached files (STL, PDF, JPG, etc.)"),
):
    """Upload an IDS XML document with optional attached files."""
    # Read and validate XML size
    xml_bytes = await ids_xml.read()
    if len(xml_bytes) > MAX_XML_SIZE:
        raise HTTPException(status_code=413, detail="IDS XML exceeds 2MB limit (ISO 18618 Clause 8)")

    # Parse XML
    try:
        parsed = parse_ids_xml(xml_bytes)
    except IDSParseError as e:
        raise HTTPException(status_code=422, detail=str(e))

    submission = parsed.get("submission")
    if not submission:
        raise HTTPException(status_code=422, detail="IDS document must contain a <Submission> element")

    submission_id = submission["uuid"]
    if not submission_id:
        raise HTTPException(status_code=422, detail="Submission UUID is required")

    # Check for duplicate
    if storage.get_metadata(submission_id):
        raise HTTPException(status_code=409, detail=f"Submission {submission_id} already exists")

    # Save XML and metadata
    storage.save_submission(submission_id, xml_bytes, parsed)

    # Save attached files
    files_uploaded = 0
    for f in files:
        if f.filename:
            content = await f.read()
            storage.save_file(submission_id, f.filename, content)
            files_uploaded += 1

    originator_data = submission.get("originator", {})
    originator_info = originator_data.get("info")
    if isinstance(originator_info, OriginatorInfo):
        originator = originator_info
    else:
        originator = OriginatorInfo(uuid="", name="Unknown")

    expected_files = submission.get("files", [])

    return SubmissionSummary(
        submission_id=submission_id,
        ids_uuid=parsed["ids_uuid"],
        ids_version=parsed["ids_version"],
        originator=originator,
        orders_count=len(submission.get("orders", [])),
        files_uploaded=files_uploaded,
        files_expected=len(expected_files),
        created_at=datetime.now(timezone.utc),
    )


@router.get("", response_model=list[SubmissionListItem])
async def list_submissions():
    """List all submissions."""
    result = []
    for sid in storage.list_submissions():
        meta = storage.get_metadata(sid)
        if not meta:
            continue
        parsed = meta.get("parsed", {})
        sub = parsed.get("submission", {})
        originator = sub.get("originator", {}).get("info", {})
        files_on_disk = storage.list_uploaded_files(sid)
        result.append(SubmissionListItem(
            submission_id=sid,
            ids_uuid=parsed.get("ids_uuid", ""),
            ids_version=parsed.get("ids_version", ""),
            originator_name=originator.get("name", "Unknown"),
            orders_count=len(sub.get("orders", [])),
            files_count=len(files_on_disk),
            created_at=meta.get("created_at", datetime.now(timezone.utc).isoformat()),
        ))
    return result


@router.get("/{submission_id}", response_model=SubmissionDetail)
async def get_submission(submission_id: str):
    """Get detailed information about a submission."""
    meta = storage.get_metadata(submission_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Submission not found")

    parsed = meta.get("parsed", {})
    sub = parsed.get("submission", {})
    originator_data = sub.get("originator", {})

    originator = OriginatorInfo(**originator_data.get("info", {"uuid": "", "name": "Unknown"}))
    addr_data = originator_data.get("address")
    address = AddressInfo(**addr_data) if addr_data else None

    patients = [PatientInfo(**p) for p in sub.get("patients", [])]
    dentists = [DentistInfo(**d) for d in sub.get("dentists", [])]

    orders = []
    for o in sub.get("orders", []):
        order = OrderInfo(**{k: v for k, v in o.items() if k != "restorations"})
        order.restorations = [
            _restoration_from_dict(r) for r in o.get("restorations", [])
        ]
        orders.append(order)

    from app.models.schemas import FileInfo
    expected_files = [FileInfo(**f) for f in sub.get("files", [])]
    uploaded = [f["file_name"] for f in storage.list_uploaded_files(submission_id)]

    return SubmissionDetail(
        submission_id=submission_id,
        ids_uuid=parsed.get("ids_uuid", ""),
        ids_version=parsed.get("ids_version", ""),
        originator=originator,
        originator_address=address,
        patients=patients,
        dentists=dentists,
        orders=orders,
        files_expected=expected_files,
        files_uploaded=uploaded,
        created_at=meta.get("created_at", datetime.now(timezone.utc).isoformat()),
    )


@router.get("/{submission_id}/xml")
async def get_submission_xml(submission_id: str):
    """Download the original IDS XML document."""
    xml_bytes = storage.get_xml_bytes(submission_id)
    if not xml_bytes:
        raise HTTPException(status_code=404, detail="Submission not found")
    return FileResponse(
        path=storage._submission_dir(submission_id) / "document.ids",
        media_type="application/xml",
        filename=f"{submission_id}.ids",
    )


@router.get("/{submission_id}/files", response_model=list[FileListItem])
async def list_submission_files(submission_id: str):
    """List files attached to a submission."""
    meta = storage.get_metadata(submission_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Submission not found")

    sub = meta.get("parsed", {}).get("submission", {})
    catalog_names = {f["file_name"] for f in sub.get("files", [])}
    uploaded = storage.list_uploaded_files(submission_id)

    return [
        FileListItem(
            file_name=f["file_name"],
            file_size=f["file_size"],
            in_catalog=f["file_name"] in catalog_names,
        )
        for f in uploaded
    ]


@router.get("/{submission_id}/files/{filename}")
async def get_submission_file(submission_id: str, filename: str):
    """Download a specific file from a submission."""
    file_path = storage.get_file_path(submission_id, filename)
    if not file_path:
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=file_path, filename=filename)


@router.delete("/{submission_id}", status_code=204)
async def delete_submission(submission_id: str):
    """Delete a submission and all associated files."""
    if not storage.delete_submission(submission_id):
        raise HTTPException(status_code=404, detail="Submission not found")


def _restoration_from_dict(data: dict):
    from app.models.schemas import RestorationInfo
    return RestorationInfo(**data)
