# ISO 18618 Reference Implementation API

ISO 18618 (Dentistry - Interoperability of CAD/CAM systems) 표준의 IDS XML을 수신하고 관리하는 Reference Implementation API입니다.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  Client                                                          │
│  (Dental CAD/CAM System, Scanner, Lab Software)                  │
└────────────┬──────────────────────────────────┬──────────────────┘
             │ multipart/form-data              │ browser
             │ (IDS XML + files)                │
             ▼                                  ▼
┌────────────────────────┐     ┌──────────────────────────────────┐
│  REST API              │     │  Web UI                          │
│  /api/v1/submissions   │     │  / (dashboard)                   │
│                        │     │  /submissions (list)             │
│  FastAPI + Pydantic    │     │  /submissions/{id} (detail)      │
└────────┬───────────────┘     │  Jinja2 Templates                │
         │                     └──────────┬───────────────────────┘
         │                                │
         ▼                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Service Layer                                                   │
│  ┌─────────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │  xml_parser.py   │  │  storage.py  │  │ submission_service │  │
│  │  (lxml)          │  │  (filesystem)│  │ (SQLAlchemy CRUD)  │  │
│  └─────────────────┘  └──────────────┘  └────────────────────┘  │
└────────────┬──────────────────┬──────────────────┬──────────────┘
             │                  │                  │
             ▼                  ▼                  ▼
      ┌────────────┐    ┌────────────┐    ┌──────────────┐
      │ IDS XML    │    │ File       │    │ PostgreSQL   │
      │ Validation │    │ Storage    │    │ Database     │
      └────────────┘    │ (storage/) │    │ (7 tables)   │
                        └────────────┘    └──────────────┘
```

### Technology Stack

| Component | Technology |
|-----------|-----------|
| Framework | FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2.0 |
| Migration | Alembic |
| XML Parsing | lxml |
| Template Engine | Jinja2 |
| Testing | pytest + httpx |

## Project Structure

```
iso-18618-ri-api/
├── app/
│   ├── main.py                  # FastAPI application entry point
│   ├── config.py                # Configuration (DB URL, limits)
│   ├── database.py              # SQLAlchemy engine & session
│   ├── models/
│   │   ├── db_models.py         # SQLAlchemy ORM models (7 tables)
│   │   └── schemas.py           # Pydantic response models
│   ├── routers/
│   │   ├── submissions.py       # REST API endpoints
│   │   └── views.py             # HTML page endpoints
│   ├── services/
│   │   ├── xml_parser.py        # IDS XML parsing (lxml)
│   │   ├── storage.py           # File system storage
│   │   └── submission_service.py # DB CRUD operations
│   └── templates/
│       ├── base.html            # Base layout
│       ├── dashboard.html       # Dashboard page
│       ├── submissions.html     # Submissions list page
│       └── submission_detail.html # Submission detail page
├── alembic/                     # Database migrations
│   ├── env.py
│   └── versions/
├── data/                        # Sample IDS XML files (10)
├── storage/                     # Uploaded file storage (runtime)
├── tests/
│   ├── conftest.py              # Test fixtures (DB isolation)
│   └── test_submissions.py      # 20 test cases
├── alembic.ini
└── requirements.txt
```

## Database Schema

### ER Diagram

```
submissions ──1:1── originators
     │
     ├──1:N── patients
     ├──1:N── dentists
     ├──1:N── orders ──1:N── restorations
     └──1:N── uploaded_files
```

All child tables use `ON DELETE CASCADE` to ensure cleanup when a submission is deleted.

### Table Definitions

#### submissions

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PK | Internal ID |
| ids_uuid | VARCHAR(100) | NOT NULL | IDS message UUID (`<IDS IDSUUID>`) |
| ids_version | VARCHAR(10) | NOT NULL | IDS schema version (`<IDS IDSVersion>`) |
| submission_uuid | VARCHAR(100) | UNIQUE, NOT NULL, INDEX | Submission UUID (`<Submission UUID>`) |
| date_submitted | TIMESTAMPTZ | | Submission date from XML |
| date_received | TIMESTAMPTZ | | Reception date |
| xml_content | TEXT | NOT NULL | Original IDS XML content |
| created_at | TIMESTAMPTZ | DEFAULT now() | Record creation time |
| updated_at | TIMESTAMPTZ | DEFAULT now() | Record update time |

#### originators

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PK | Internal ID |
| submission_id | INTEGER | FK → submissions(id) CASCADE | Parent submission |
| uuid | VARCHAR(100) | NOT NULL | Originator UUID |
| name | VARCHAR(255) | NOT NULL | Originator name |
| business_type | VARCHAR(3) | | `DOC` (Dentist), `LAB` (Lab), `SRV` (Broker), `OTH` (Other) |
| street1 | VARCHAR(125) | | Address line 1 |
| street2 | VARCHAR(125) | | Address line 2 |
| city | VARCHAR(125) | | City |
| state | VARCHAR(64) | | State/Province |
| postal_code | VARCHAR(100) | | Postal code |
| country | VARCHAR(3) | | Country code (ISO 3166-1 Alpha-3) |

#### patients

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PK | Internal ID |
| submission_id | INTEGER | FK → submissions(id) CASCADE | Parent submission |
| uuid | VARCHAR(100) | NOT NULL | Patient UUID |
| first_name | VARCHAR(100) | | First name |
| last_name | VARCHAR(100) | | Last name |
| date_of_birth | DATE | | Date of birth |
| gender | VARCHAR(1) | | `M` or `F` |

#### dentists

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PK | Internal ID |
| submission_id | INTEGER | FK → submissions(id) CASCADE | Parent submission |
| uuid | VARCHAR(100) | NOT NULL | Dentist UUID |
| first_name | VARCHAR(100) | | First name |
| last_name | VARCHAR(100) | | Last name |
| license_number | VARCHAR(50) | | License number |

#### orders

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PK | Internal ID |
| submission_id | INTEGER | FK → submissions(id) CASCADE | Parent submission |
| uuid | VARCHAR(100) | NOT NULL | Order UUID |
| patient_uuid | VARCHAR(100) | | Reference to patient |
| dentist_uuid | VARCHAR(100) | | Reference to dentist |
| priority | VARCHAR(20) | | `Normal`, `High` |
| date_created | TIMESTAMPTZ | | Order creation date |
| delivery_method | VARCHAR(50) | | `Physical`, `Chairside`, `Electronic` |
| delivery_date | TIMESTAMPTZ | | Requested delivery date |

#### restorations

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PK | Internal ID |
| order_id | INTEGER | FK → orders(id) CASCADE | Parent order |
| uuid | VARCHAR(100) | NOT NULL | Restoration UUID |
| tooth_number | VARCHAR(10) | | Tooth number (ISO 3950) |
| type | VARCHAR(50) | | `Crown`, `Veneer`, `Inlay`, `Onlay`, `BridgeAbutment`, etc. |
| material | VARCHAR(50) | | `Zirconia`, `LithiumDisilicate`, `PMMA`, `Titanium`, etc. |
| shade | VARCHAR(10) | | `A1`, `A2`, `A3`, `BL2`, etc. |

#### uploaded_files

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PK | Internal ID |
| submission_id | INTEGER | FK → submissions(id) CASCADE | Parent submission |
| uuid | VARCHAR(100) | | File UUID from `<FileCatalog>` |
| file_name | VARCHAR(255) | NOT NULL | File name |
| file_type | VARCHAR(20) | | `STL`, `PDF`, `JPG`, `ZIP`, etc. |
| file_size | BIGINT | | File size in bytes |
| description | TEXT | | File description |
| storage_path | VARCHAR(500) | | Path on disk |
| is_uploaded | BOOLEAN | DEFAULT false | Whether file has been uploaded |

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 14+

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create PostgreSQL Database and User

```sql
CREATE DATABASE ids_api;
CREATE USER ids_user WITH PASSWORD 'ids_pass';
GRANT ALL PRIVILEGES ON DATABASE ids_api TO ids_user;
-- Connect to ids_api database, then:
GRANT ALL ON SCHEMA public TO ids_user;
```

Or set a custom connection string via environment variable:

```bash
export DATABASE_URL="postgresql://user:password@host:5432/dbname"
```

### 3. Run Database Migrations

```bash
python -m alembic upgrade head
```

This creates all 7 tables in the database.

### 4. Run the Application

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Web UI: http://localhost:8000
- Swagger API Docs: http://localhost:8000/docs

## Configuration

Configuration is managed in `app/config.py` and can be overridden via environment variables:

| Setting | Default | Env Variable | Description |
|---------|---------|-------------|-------------|
| Database URL | `postgresql://ids_user:ids_pass@localhost:5432/ids_api` | `DATABASE_URL` | PostgreSQL connection string |
| Storage Directory | `./storage/` | - | File upload storage path |
| Max XML Size | 2 MB | - | ISO 18618 Clause 8 limit |
| Max File Size | 100 MB | - | Per-file upload limit |

Alembic uses the database URL from `alembic.ini`. Update both if changing the database connection.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/submissions` | Upload IDS XML + files (multipart/form-data) |
| `GET` | `/api/v1/submissions` | List all submissions |
| `GET` | `/api/v1/submissions/{id}` | Get submission detail |
| `GET` | `/api/v1/submissions/{id}/xml` | Download original IDS XML |
| `GET` | `/api/v1/submissions/{id}/files` | List attached files |
| `GET` | `/api/v1/submissions/{id}/files/{name}` | Download a file |
| `DELETE` | `/api/v1/submissions/{id}` | Delete a submission |

### Upload Example

```bash
curl -X POST http://localhost:8000/api/v1/submissions \
  -F "ids_xml=@data/01-single-crown.ids" \
  -F "files=@upper_jaw_scan.stl" \
  -F "files=@lower_jaw_scan.stl"
```

## Testing

### Setup Test Database

```sql
CREATE DATABASE ids_api_test OWNER ids_user;
```

### Run Tests

```bash
python -m pytest tests/ -v
```

The test suite (20 tests) uses transaction-level isolation with savepoint rollback, so no test data persists between tests.

## Sample Data

The `data/` directory contains 10 sample IDS XML files covering various dental scenarios:

| File | Scenario |
|------|----------|
| `01-single-crown.ids` | Single zirconia crown (#16) |
| `02-bridge-three-unit.ids` | 3-unit bridge (#35-37) |
| `03-implant-abutment.ids` | Implant custom abutment + crown (#46) |
| `04-veneer-case.ids` | 6 anterior veneers (#11-13, 21-23) |
| `05-inlay-onlay.ids` | Inlay + onlay chairside milling |
| `06-removable-partial-denture.ids` | Removable partial denture framework |
| `07-orthodontic-appliance.ids` | Orthodontic clear aligner |
| `08-full-denture.ids` | Upper + lower complete denture set |
| `09-multi-case-broker.ids` | Broker with 3 patients, 3 orders |
| `10-notification-status-update.ids` | Production status + delivery notification |

## References

- [ISO 18618:2022 - Dentistry - Interoperability of CAD/CAM systems](https://www.iso.org/standard/79923.html)
- [ISO/TC 106/SC 9 - Dental CAD/CAM systems](https://www.iso.org/committee/653079.html)
- [ISO 3950 - Dentistry - Designation system for teeth](https://www.iso.org/standard/68292.html)
