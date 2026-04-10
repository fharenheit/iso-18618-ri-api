from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
STORAGE_DIR.mkdir(exist_ok=True)

MAX_XML_SIZE = 2 * 1024 * 1024  # 2MB per ISO 18618 Clause 8
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB per attached file
