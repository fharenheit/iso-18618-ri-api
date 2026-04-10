from datetime import datetime
from pydantic import BaseModel


class OriginatorInfo(BaseModel):
    uuid: str
    name: str
    business_type: str | None = None


class AddressInfo(BaseModel):
    street1: str | None = None
    street2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None


class PatientInfo(BaseModel):
    uuid: str
    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: str | None = None
    gender: str | None = None


class DentistInfo(BaseModel):
    uuid: str
    first_name: str | None = None
    last_name: str | None = None
    license_number: str | None = None


class RestorationInfo(BaseModel):
    uuid: str
    tooth_number: str | None = None
    type: str | None = None
    material: str | None = None
    shade: str | None = None


class OrderInfo(BaseModel):
    uuid: str
    patient_uuid: str | None = None
    dentist_uuid: str | None = None
    priority: str | None = None
    date_created: str | None = None
    restorations: list[RestorationInfo] = []


class FileInfo(BaseModel):
    uuid: str
    file_name: str
    file_type: str | None = None
    file_size: str | None = None
    description: str | None = None


class SubmissionSummary(BaseModel):
    submission_id: str
    ids_uuid: str
    ids_version: str
    originator: OriginatorInfo
    orders_count: int
    files_uploaded: int
    files_expected: int
    created_at: datetime


class SubmissionDetail(BaseModel):
    submission_id: str
    ids_uuid: str
    ids_version: str
    originator: OriginatorInfo
    originator_address: AddressInfo | None = None
    patients: list[PatientInfo] = []
    dentists: list[DentistInfo] = []
    orders: list[OrderInfo] = []
    files_expected: list[FileInfo] = []
    files_uploaded: list[str] = []
    created_at: datetime


class SubmissionListItem(BaseModel):
    submission_id: str
    ids_uuid: str
    ids_version: str
    originator_name: str
    orders_count: int
    files_count: int
    created_at: datetime


class FileListItem(BaseModel):
    file_name: str
    file_size: int
    in_catalog: bool


class ErrorResponse(BaseModel):
    detail: str
