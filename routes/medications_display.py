from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from routes.auth import get_current_user

from models.user_model import User
from models.active_med_model import ActiveMedication
from models.doc_model import MedicalDocument, Prescription, PrescriptionMedicine
from schemas.medication_schema import MedicationResponse
from safety.active_medication import (
    _prescription_datetime,
    prescription_end_date,
)

router = APIRouter(
    prefix="/medicine",
    tags=["medicine"]
)

# GET /medications?status=ACTIVE
# GET /medications?status=COMPLETED
# GET /medications?status=STOPPED
# GET /medications

@router.get(
    "/display",
    response_model=list[MedicationResponse],
    status_code=status.HTTP_200_OK
)
def get_medications(
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    query = (
        db.query(ActiveMedication)
        .filter(
            ActiveMedication.patient_id == current_user.id
        )
    )

    if status_filter:
        allowed_status = {
            "ACTIVE",
            "COMPLETED",
            "STOPPED"
        }

        status_filter = status_filter.upper()

        if status_filter not in allowed_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid medication status"
            )

        query = query.filter(
            ActiveMedication.status == status_filter
        )
        if status_filter == "ACTIVE":
            query = query.filter(
                ActiveMedication.prescription_id.is_(None)
            )

    medications = query.order_by(
        ActiveMedication.start_date.desc()
    ).all()

    results = [
        {
            "medication_id": str(medication.medication_id),
            "name": medication.name,
            "rxcui": medication.rxcui,
            "ingredients": medication.ingredients,
            "status": (
                "PRESCRIPTION"
                if medication.prescription_id
                else medication.status
            ),
            "start_date": medication.start_date,
            "end_date": medication.end_date,
            "prescription_id": (
                str(medication.prescription_id)
                if medication.prescription_id
                else None
            ),
            "dosage": None,
            "frequency": None,
            "duration": None,
            "prescription_date": None,
            "document_name": None,
        }
        for medication in medications
    ]

    linked_prescriptions = {
        medication.prescription_id
        for medication in medications
        if medication.prescription_id
    }
    prescription_metadata = {}
    if linked_prescriptions:
        metadata_rows = (
            db.query(Prescription, MedicalDocument, PrescriptionMedicine)
            .outerjoin(
                MedicalDocument,
                Prescription.doc_id == MedicalDocument.doc_id
            )
            .outerjoin(
                PrescriptionMedicine,
                PrescriptionMedicine.prescription_id
                == Prescription.prescription_id
            )
            .filter(
                Prescription.prescription_id.in_(linked_prescriptions),
                MedicalDocument.patient_id == current_user.id
            )
            .all()
        )
        for prescription, document, medicine in metadata_rows:
            metadata = prescription_metadata.setdefault(
                prescription.prescription_id,
                {
                    "date": prescription.date,
                    "document_name": (
                        document.original_filename if document else None
                    ),
                    "medicines": [],
                },
            )
            if medicine:
                metadata["medicines"].append(medicine)

    for item, medication in zip(results, medications):
        if medication.prescription_id in prescription_metadata:
            metadata = prescription_metadata[
                medication.prescription_id
            ]
            item["prescription_date"] = metadata["date"]
            item["document_name"] = metadata["document_name"]
            item["start_date"] = _prescription_datetime(metadata["date"])
            prescribed_medicines = metadata["medicines"]
            matched_medicine = next(
                (
                    prescribed_medicine
                    for prescribed_medicine in prescribed_medicines
                    if prescribed_medicine.name.strip().casefold()
                    == medication.name.strip().casefold()
                ),
                None,
            )
            if matched_medicine is None and len(prescribed_medicines) == 1:
                matched_medicine = prescribed_medicines[0]
            if matched_medicine:
                item["dosage"] = matched_medicine.dosage
                item["frequency"] = matched_medicine.frequency
                item["duration"] = matched_medicine.duration
                item["end_date"] = medication.end_date or prescription_end_date(
                    _prescription_datetime(metadata["date"]),
                    matched_medicine.duration,
                )

    if status_filter:
        return results

    prescription_rows = (
        db.query(PrescriptionMedicine, Prescription, MedicalDocument)
        .join(
            Prescription,
            PrescriptionMedicine.prescription_id == Prescription.prescription_id
        )
        .join(
            MedicalDocument,
            Prescription.doc_id == MedicalDocument.doc_id
        )
        .filter(
            MedicalDocument.patient_id == current_user.id,
            MedicalDocument.status == "parsed"
        )
        .order_by(MedicalDocument.uploaded_at.desc())
        .all()
    )

    for medicine, prescription, document in prescription_rows:
        if prescription.prescription_id in linked_prescriptions:
            continue

        results.append({
            "medication_id": str(medicine.medicine_id),
            "name": medicine.name,
            "rxcui": None,
            "ingredients": [],
            "status": "PRESCRIPTION",
            "start_date": _prescription_datetime(prescription.date),
            "end_date": prescription_end_date(
                _prescription_datetime(prescription.date),
                medicine.duration,
            ),
            "prescription_id": str(prescription.prescription_id),
            "dosage": medicine.dosage,
            "frequency": medicine.frequency,
            "duration": medicine.duration,
            "prescription_date": prescription.date,
            "document_name": document.original_filename,
        })

    return results