import uuid
from sqlalchemy import  Integer,String,Text,func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base

# ============================================================
# USER
# ============================================================

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=False)
    gender: Mapped[str | None] = mapped_column(String(30), nullable=True)
    year_of_birth: Mapped[int | None] = mapped_column(Integer, nullable=True)
    medical_condition: Mapped[str | None] = mapped_column(Text, nullable=True)
    allergy: Mapped[str | None] = mapped_column(Text, nullable=True)
    blood_group: Mapped[str | None] = mapped_column(String(10), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    
    medical_documents = relationship(
        "MedicalDocument",
        back_populates="patient",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    active_medications = relationship(
            "ActiveMedication",
            back_populates="patient",
            cascade="all, delete-orphan",
            passive_deletes=True,
        )

