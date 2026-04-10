from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


class OriginatorInfo(BaseModel):
    uuid: str
    name: str
    business_type: Optional[str] = None


class AddressInfo(BaseModel):
    street1: Optional[str] = None
    street2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None


class PatientInfo(BaseModel):
    uuid: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None


class DentistInfo(BaseModel):
    uuid: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    license_number: Optional[str] = None


class RestorationInfo(BaseModel):
    uuid: str
    tooth_number: Optional[str] = None
    type: Optional[str] = None
    material: Optional[str] = None
    shade: Optional[str] = None


class OrderInfo(BaseModel):
    uuid: str
    patient_uuid: Optional[str] = None
    dentist_uuid: Optional[str] = None
    priority: Optional[str] = None
    date_created: Optional[str] = None
    restorations: List[RestorationInfo] = []


class FileInfo(BaseModel):
    uuid: str
    file_name: str
    file_type: Optional[str] = None
    file_size: Optional[str] = None
    description: Optional[str] = None


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
    originator_address: Optional[AddressInfo] = None
    patients: List[PatientInfo] = []
    dentists: List[DentistInfo] = []
    orders: List[OrderInfo] = []
    files_expected: List[FileInfo] = []
    files_uploaded: List[str] = []
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
