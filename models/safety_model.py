import uuid
from datetime import datetime
from sqlalchemy import DateTime,ForeignKey,Index,String,Text,func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base
from models.user_model import User
from models.doc_model import MedicalDocument
# ============================================================
# SAFETY CHECK
# ============================================================

class SafetyCheck(Base):
    __tablename__ = "safety_checks"

    safety_check_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    doc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("medical_documents.doc_id", ondelete="CASCADE"),
        nullable=False
    )

    has_critical_issue: Mapped[bool] = mapped_column(
        nullable=False,
        default=False
    )

    patient_alert_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    doctor_clinical_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    action_required: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    language: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="en"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    patient: Mapped["User"] = relationship(
        "User"
    )

    document: Mapped["MedicalDocument"] = relationship(
        "MedicalDocument"
    )

    conflicts: Mapped[list["SafetyConflict"]] = relationship(
        "SafetyConflict",
        back_populates="safety_check",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

# ============================================================
# SAFETY CONFLICT
# ============================================================

class SafetyConflict(Base):
    __tablename__ = "safety_conflicts"

    conflict_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    safety_check_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("safety_checks.safety_check_id", ondelete="CASCADE"),
        nullable=False
    )

    conflict_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    drug: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    drug_a: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    drug_b: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    allergy: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    condition: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    severity: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    safety_check: Mapped["SafetyCheck"] = relationship(
        "SafetyCheck",
        back_populates="conflicts"
    )

    __table_args__ = (
        Index(
            "ix_safety_conflicts_safety_check_id",
            "safety_check_id"
        ),
        Index(
            "ix_safety_conflicts_severity",
            "severity"
        ),
    )