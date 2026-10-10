import uuid
from datetime import datetime
from sqlalchemy import CheckConstraint,DateTime,ForeignKey,Index, Integer,String,Text,func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base
from models.doc_model import Prescription
# ============================================================
# ACTIVE MEDICATION
# ============================================================

class ActiveMedication(Base):
    __tablename__ = "active_medications"

    medication_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    prescription_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prescriptions.prescription_id", ondelete="SET NULL"),
        nullable=True
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    rxcui: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    ingredients: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="ACTIVE"
    )

    start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    end_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    patient= relationship("User",back_populates="active_medications")

    prescription: Mapped["Prescription | None"] = relationship("Prescription")

    

    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'COMPLETED', 'STOPPED')",
            name="check_active_medication_status"
        ),
        Index(
            "ix_active_medications_patient_id",
            "patient_id"
        ),
        Index(
            "ix_active_medications_rxcui",
            "rxcui"
        ),
    )
