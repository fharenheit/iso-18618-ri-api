import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import STORAGE_DIR
from app.main import app

client = TestClient(app)

SAMPLE_IDS_XML = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<IDS IDSVersion="2.0" IDSUUID="test-uuid-0001-0001-0001-000000000001">
  <Submission UUID="sub-00000001-0001-0001-0001-000000000001" DateUTCSubmitted="2026-04-01T09:00:00Z">
    <Originator UUID="orig-0001" Name="Test Dental Clinic" BusinessType="DOC">
      <Address Street1="123 Test St" City="Seoul" State="Seoul" PostalCode="06100" Country="KOR" />
    </Originator>
    <Catalogs>
      <PatientCatalog>
        <Patient UUID="pat-0001" FirstName="Minjun" LastName="Kim" DateOfBirth="1985-03-15" Gender="M" />
      </PatientCatalog>
      <DentistCatalog>
        <Dentist UUID="den-0001" FirstName="Seonghwan" LastName="Park" LicenseNumber="DEN-2010-5521" />
      </DentistCatalog>
      <OrderCatalog>
        <Order UUID="ord-0001" PatientUUID="pat-0001" DentistUUID="den-0001" DateUTCCreated="2026-04-01T08:30:00Z" Priority="Normal">
          <Restoration UUID="res-0001" ToothNumber="16" Type="Crown" Material="Zirconia" Shade="A2" />
        </Order>
      </OrderCatalog>
      <FileCatalog>
        <IDSFile UUID="file-0001" FileName="upper_jaw.stl" FileType="STL" FileSize="1000" Description="Upper jaw scan" />
        <IDSFile UUID="file-0002" FileName="lower_jaw.stl" FileType="STL" FileSize="900" Description="Lower jaw scan" />
      </FileCatalog>
    </Catalogs>
  </Submission>
</IDS>
"""

SUBMISSION_ID = "sub-00000001-0001-0001-0001-000000000001"


@pytest.fixture(autouse=True)
def cleanup_storage():
    """Clean up test submission data before and after each test."""
    sub_dir = STORAGE_DIR / SUBMISSION_ID
    if sub_dir.exists():
        shutil.rmtree(sub_dir)
    yield
    if sub_dir.exists():
        shutil.rmtree(sub_dir)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_create_submission_xml_only():
    resp = client.post(
        "/api/v1/submissions",
        files={"ids_xml": ("test.ids", SAMPLE_IDS_XML, "application/xml")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["submission_id"] == SUBMISSION_ID
    assert data["ids_uuid"] == "test-uuid-0001-0001-0001-000000000001"
    assert data["ids_version"] == "2.0"
    assert data["originator"]["name"] == "Test Dental Clinic"
    assert data["originator"]["business_type"] == "DOC"
    assert data["orders_count"] == 1
    assert data["files_uploaded"] == 0
    assert data["files_expected"] == 2


def test_create_submission_with_files():
    stl_content_1 = b"solid upper\nendsolid upper"
    stl_content_2 = b"solid lower\nendsolid lower"
    resp = client.post(
        "/api/v1/submissions",
        files=[
            ("ids_xml", ("test.ids", SAMPLE_IDS_XML, "application/xml")),
            ("files", ("upper_jaw.stl", stl_content_1, "application/octet-stream")),
            ("files", ("lower_jaw.stl", stl_content_2, "application/octet-stream")),
        ],
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["files_uploaded"] == 2
    assert data["files_expected"] == 2


def test_create_submission_duplicate():
    client.post(
        "/api/v1/submissions",
        files={"ids_xml": ("test.ids", SAMPLE_IDS_XML, "application/xml")},
    )
    resp = client.post(
        "/api/v1/submissions",
        files={"ids_xml": ("test.ids", SAMPLE_IDS_XML, "application/xml")},
    )
    assert resp.status_code == 409


def test_create_submission_invalid_xml():
    resp = client.post(
        "/api/v1/submissions",
        files={"ids_xml": ("bad.ids", b"<not-ids/>", "application/xml")},
    )
    assert resp.status_code == 422


def test_create_submission_malformed_xml():
    resp = client.post(
        "/api/v1/submissions",
        files={"ids_xml": ("bad.ids", b"not xml at all", "application/xml")},
    )
    assert resp.status_code == 422


def test_list_submissions():
    client.post(
        "/api/v1/submissions",
        files={"ids_xml": ("test.ids", SAMPLE_IDS_XML, "application/xml")},
    )
    resp = client.get("/api/v1/submissions")
    assert resp.status_code == 200
    items = resp.json()
    assert any(s["submission_id"] == SUBMISSION_ID for s in items)


def test_get_submission_detail():
    client.post(
        "/api/v1/submissions",
        files={"ids_xml": ("test.ids", SAMPLE_IDS_XML, "application/xml")},
    )
    resp = client.get(f"/api/v1/submissions/{SUBMISSION_ID}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["submission_id"] == SUBMISSION_ID
    assert len(data["patients"]) == 1
    assert data["patients"][0]["first_name"] == "Minjun"
    assert len(data["dentists"]) == 1
    assert len(data["orders"]) == 1
    assert data["orders"][0]["restorations"][0]["type"] == "Crown"
    assert len(data["files_expected"]) == 2
    assert data["originator_address"]["city"] == "Seoul"


def test_get_submission_not_found():
    resp = client.get("/api/v1/submissions/nonexistent-id")
    assert resp.status_code == 404


def test_get_submission_xml():
    client.post(
        "/api/v1/submissions",
        files={"ids_xml": ("test.ids", SAMPLE_IDS_XML, "application/xml")},
    )
    resp = client.get(f"/api/v1/submissions/{SUBMISSION_ID}/xml")
    assert resp.status_code == 200
    assert b"<IDS" in resp.content


def test_list_and_download_files():
    stl_data = b"solid test\nendsolid test"
    client.post(
        "/api/v1/submissions",
        files=[
            ("ids_xml", ("test.ids", SAMPLE_IDS_XML, "application/xml")),
            ("files", ("upper_jaw.stl", stl_data, "application/octet-stream")),
        ],
    )
    # List files
    resp = client.get(f"/api/v1/submissions/{SUBMISSION_ID}/files")
    assert resp.status_code == 200
    file_list = resp.json()
    assert len(file_list) == 1
    assert file_list[0]["file_name"] == "upper_jaw.stl"
    assert file_list[0]["in_catalog"] is True

    # Download file
    resp = client.get(f"/api/v1/submissions/{SUBMISSION_ID}/files/upper_jaw.stl")
    assert resp.status_code == 200
    assert resp.content == stl_data


def test_download_file_not_found():
    client.post(
        "/api/v1/submissions",
        files={"ids_xml": ("test.ids", SAMPLE_IDS_XML, "application/xml")},
    )
    resp = client.get(f"/api/v1/submissions/{SUBMISSION_ID}/files/nonexistent.stl")
    assert resp.status_code == 404


def test_delete_submission():
    client.post(
        "/api/v1/submissions",
        files={"ids_xml": ("test.ids", SAMPLE_IDS_XML, "application/xml")},
    )
    resp = client.delete(f"/api/v1/submissions/{SUBMISSION_ID}")
    assert resp.status_code == 204

    resp = client.get(f"/api/v1/submissions/{SUBMISSION_ID}")
    assert resp.status_code == 404


def test_delete_submission_not_found():
    resp = client.delete("/api/v1/submissions/nonexistent-id")
    assert resp.status_code == 404


def test_xml_size_limit():
    big_xml = b'<?xml version="1.0"?><IDS IDSVersion="2.0" IDSUUID="x">' + b"x" * (2 * 1024 * 1024) + b"</IDS>"
    resp = client.post(
        "/api/v1/submissions",
        files={"ids_xml": ("big.ids", big_xml, "application/xml")},
    )
    assert resp.status_code == 413


def test_create_with_sample_data_file():
    """Test with an actual sample IDS file from the data directory."""
    sample_path = Path(__file__).resolve().parent.parent / "data" / "01-single-crown.ids"
    if not sample_path.exists():
        pytest.skip("Sample data file not found")

    xml_bytes = sample_path.read_bytes()

    # Use a unique cleanup for this test
    from app.services.xml_parser import parse_ids_xml
    parsed = parse_ids_xml(xml_bytes)
    real_sub_id = parsed["submission"]["uuid"]
    real_sub_dir = STORAGE_DIR / real_sub_id
    if real_sub_dir.exists():
        shutil.rmtree(real_sub_dir)

    try:
        resp = client.post(
            "/api/v1/submissions",
            files=[
                ("ids_xml", ("01-single-crown.ids", xml_bytes, "application/xml")),
                ("files", ("upper_jaw_scan.stl", b"stl binary data", "application/octet-stream")),
            ],
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["originator"]["name"] == "Seoul Dental Clinic"
        assert data["orders_count"] == 1
        assert data["files_uploaded"] == 1
        assert data["files_expected"] == 3
    finally:
        if real_sub_dir.exists():
            shutil.rmtree(real_sub_dir)
