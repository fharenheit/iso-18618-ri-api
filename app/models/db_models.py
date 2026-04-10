from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ids_uuid = Column(String(100), nullable=False)
    ids_version = Column(String(10), nullable=False)
    submission_uuid = Column(String(100), unique=True, nullable=False, index=True)
    date_submitted = Column(DateTime(timezone=True))
    date_received = Column(DateTime(timezone=True))
    xml_content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    originator = relationship("Originator", back_populates="submission", uselist=False, cascade="all, delete-orphan")
    patients = relationship("Patient", back_populates="submission", cascade="all, delete-orphan")
    dentists = relationship("Dentist", back_populates="submission", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="submission", cascade="all, delete-orphan")
    uploaded_files = relationship("UploadedFile", back_populates="submission", cascade="all, delete-orphan")


class Originator(Base):
    __tablename__ = "originators"

    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    uuid = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    business_type = Column(String(3))
    street1 = Column(String(125))
    street2 = Column(String(125))
    city = Column(String(125))
    state = Column(String(64))
    postal_code = Column(String(100))
    country = Column(String(3))

    submission = relationship("Submission", back_populates="originator")


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    uuid = Column(String(100), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    date_of_birth = Column(Date)
    gender = Column(String(1))

    submission = relationship("Submission", back_populates="patients")


class Dentist(Base):
    __tablename__ = "dentists"

    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    uuid = Column(String(100), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    license_number = Column(String(50))

    submission = relationship("Submission", back_populates="dentists")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    uuid = Column(String(100), nullable=False)
    patient_uuid = Column(String(100))
    dentist_uuid = Column(String(100))
    priority = Column(String(20))
    date_created = Column(DateTime(timezone=True))
    delivery_method = Column(String(50))
    delivery_date = Column(DateTime(timezone=True))

    submission = relationship("Submission", back_populates="orders")
    restorations = relationship("Restoration", back_populates="order", cascade="all, delete-orphan")


class Restoration(Base):
    __tablename__ = "restorations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    uuid = Column(String(100), nullable=False)
    tooth_number = Column(String(10))
    type = Column(String(50))
    material = Column(String(50))
    shade = Column(String(10))

    order = relationship("Order", back_populates="restorations")


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    uuid = Column(String(100))
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(20))
    file_size = Column(BigInteger)
    description = Column(Text)
    storage_path = Column(String(500))
    is_uploaded = Column(Boolean, default=False)

    submission = relationship("Submission", back_populates="uploaded_files")
