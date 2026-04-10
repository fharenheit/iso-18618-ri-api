from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent

# Load YAML config
_config_path = os.getenv("IDS_CONFIG", str(BASE_DIR / "config.yaml"))
if Path(_config_path).exists():
    with open(_config_path) as f:
        _cfg = yaml.safe_load(f) or {}
else:
    _cfg = {}

# Logging
_log = _cfg.get("logging", {})
LOG_LEVEL = _log.get("level", "INFO").upper()
LOG_FORMAT = _log.get("format", "%(asctime)s [%(levelname)s] %(name)s - %(message)s")
_sa_level = _log.get("sqlalchemy_level", "WARNING").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format=LOG_FORMAT,
    stream=sys.stdout,
)
logging.getLogger("sqlalchemy.engine").setLevel(getattr(logging, _sa_level, logging.WARNING))

logger = logging.getLogger("ids")
logger.info("Loading config from %s", _config_path)

# Server
SERVER_HOST = _cfg.get("server", {}).get("host", "0.0.0.0")
SERVER_PORT = _cfg.get("server", {}).get("port", 8000)

# Database
_db = _cfg.get("database", {})
_db_host = _db.get("host", "localhost")
_db_port = _db.get("port", 5432)
_db_name = _db.get("name", "ids_api")
_db_user = _db.get("user", "ids_user")
_db_password = _db.get("password", "ids_pass")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{_db_user}:{_db_password}@{_db_host}:{_db_port}/{_db_name}",
)
logger.info("Database: %s@%s:%s/%s", _db_user, _db_host, _db_port, _db_name)

# Storage
_storage_dir = _cfg.get("storage", {}).get("upload_dir")
if _storage_dir:
    STORAGE_DIR = Path(_storage_dir)
else:
    STORAGE_DIR = BASE_DIR / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
logger.info("Storage directory: %s", STORAGE_DIR)

# Upload limits
_upload = _cfg.get("upload", {})
MAX_XML_SIZE = _upload.get("max_xml_size_mb", 2) * 1024 * 1024
MAX_FILE_SIZE = _upload.get("max_file_size_mb", 100) * 1024 * 1024
logger.info("Upload limits: XML=%dMB, File=%dMB", MAX_XML_SIZE // (1024*1024), MAX_FILE_SIZE // (1024*1024))
