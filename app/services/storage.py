import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from app.config import STORAGE_DIR


def _submission_dir(submission_id: str) -> Path:
    return STORAGE_DIR / submission_id


def save_submission(submission_id: str, xml_bytes: bytes, parsed: dict) -> Path:
    """Save IDS XML and metadata for a submission."""
    sub_dir = _submission_dir(submission_id)
    sub_dir.mkdir(parents=True, exist_ok=True)
    files_dir = sub_dir / "files"
    files_dir.mkdir(exist_ok=True)

    # Save original XML
    (sub_dir / "document.ids").write_bytes(xml_bytes)

    # Save parsed metadata
    metadata = {
        "submission_id": submission_id,
        "ids_uuid": parsed["ids_uuid"],
        "ids_version": parsed["ids_version"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "parsed": _serialize(parsed),
    }
    (sub_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2)
    )

    return sub_dir


def save_file(submission_id: str, filename: str, content: bytes) -> Path:
    """Save an uploaded file to the submission's files directory."""
    safe_name = Path(filename).name  # prevent path traversal
    files_dir = _submission_dir(submission_id) / "files"
    files_dir.mkdir(parents=True, exist_ok=True)
    file_path = files_dir / safe_name
    file_path.write_bytes(content)
    return file_path


def get_metadata(submission_id: str) -> dict | None:
    meta_path = _submission_dir(submission_id) / "metadata.json"
    if not meta_path.exists():
        return None
    return json.loads(meta_path.read_text())


def get_xml_bytes(submission_id: str) -> bytes | None:
    xml_path = _submission_dir(submission_id) / "document.ids"
    if not xml_path.exists():
        return None
    return xml_path.read_bytes()


def list_uploaded_files(submission_id: str) -> list[dict]:
    files_dir = _submission_dir(submission_id) / "files"
    if not files_dir.exists():
        return []
    return [
        {"file_name": f.name, "file_size": f.stat().st_size}
        for f in sorted(files_dir.iterdir())
        if f.is_file()
    ]


def get_file_path(submission_id: str, filename: str) -> Path | None:
    safe_name = Path(filename).name
    file_path = _submission_dir(submission_id) / "files" / safe_name
    if not file_path.exists():
        return None
    return file_path


def list_submissions() -> list[str]:
    if not STORAGE_DIR.exists():
        return []
    return sorted(
        d.name for d in STORAGE_DIR.iterdir()
        if d.is_dir() and (d / "metadata.json").exists()
    )


def delete_submission(submission_id: str) -> bool:
    sub_dir = _submission_dir(submission_id)
    if not sub_dir.exists():
        return False
    shutil.rmtree(sub_dir)
    return True


def _serialize(obj):
    """Convert pydantic models / nested dicts for JSON serialization."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(i) for i in obj]
    return obj
