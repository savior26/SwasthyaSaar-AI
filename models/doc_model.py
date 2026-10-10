import uuid
from datetime import datetime
from sqlalchemy import CheckConstraint,DateTime,ForeignKey,Index, String,Text,func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base

# from models.user_model import User
# ============================================================
# MEDICAL DOCUMENT
# ============================================================

class MedicalDocument(Base):
    __tablename__ = "medical_documents"

    doc_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="uploaded")
    processing_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    patient = relationship("User", back_populates="medical_documents")

    lab_report: Mapped["LabReport | None"] = relationship(
        "LabReport",
        back_populates="document",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    prescription: Mapped["Prescription | None"] = relationship(
        "Prescription",
        back_populates="document",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint("document_type IN ('lab_report', 'prescription')", name="check_document_type"),
        CheckConstraint("status IN ('uploaded', 'processing', 'parsed', 'failed')", name="check_document_status"),
        Index("ix_medical_documents_patient_id", "patient_id"),
        Index("ix_medical_documents_patient_type", "patient_id", "document_type"),
        Index("ix_medical_documents_uploaded_at", "uploaded_at"),
    )


# ============================================================
# LAB REPORT
# ============================================================

class LabReport(Base):
    __tablename__ = "lab_reports"

    lab_report_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doc_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("medical_documents.doc_id", ondelete="CASCADE"), nullable=False, unique=True)
    lab_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    patient_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    document: Mapped["MedicalDocument"] = relationship("MedicalDocument", back_populates="lab_report")

    tests: Mapped[list["LabTest"]] = relationship(
        "LabTest",
        back_populates="lab_report",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_lab_reports_lab_name", "lab_name"),
    )


# ============================================================
# LAB TEST
# ============================================================

class LabTest(Base):
    __tablename__ = "lab_tests"

    test_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lab_report_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("lab_reports.lab_report_id", ondelete="CASCADE"), nullable=False)
    test_name: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reference_range: Mapped[str | None] = mapped_column(String(255), nullable=True)
    flag: Mapped[str] = mapped_column(String(30), nullable=False, default="unknown")

    lab_report: Mapped["LabReport"] = relationship("LabReport", back_populates="tests")

    __table_args__ = (
        CheckConstraint("flag IN ('normal', 'high', 'low', 'abnormal', 'unknown')", name="check_lab_test_flag"),
        Index("ix_lab_tests_lab_report_id", "lab_report_id"),
        Index("ix_lab_tests_test_name", "test_name"),
        Index("ix_lab_tests_flag", "flag"),
    )


# ============================================================
# PRESCRIPTION
# ============================================================

class Prescription(Base):
    __tablename__ = "prescriptions"

    prescription_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doc_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("medical_documents.doc_id", ondelete="CASCADE"), nullable=False, unique=True)
    doctor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hospital_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    patient_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    document: Mapped["MedicalDocument"] = relationship("MedicalDocument", back_populates="prescription")

    medicines: Mapped[list["PrescriptionMedicine"]] = relationship(
        "PrescriptionMedicine",
        back_populates="prescription",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_prescriptions_doctor_name", "doctor_name"),
        Index("ix_prescriptions_hospital_name", "hospital_name"),
    )


# ============================================================
# PRESCRIPTION MEDICINE
# ============================================================

class PrescriptionMedicine(Base):
    __tablename__ = "prescription_medicines"

    medicine_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prescription_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("prescriptions.prescription_id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dosage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration: Mapped[str | None] = mapped_column(String(100), nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    prescription: Mapped["Prescription"] = relationship("Prescription", back_populates="medicines")

    __table_args__ = (
        Index("ix_prescription_medicines_prescription_id", "prescription_id"),
        Index("ix_prescription_medicines_name", "name"),
    )
