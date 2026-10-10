from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models.model import User, ActiveMedication


def _split_patient_values(value: str | None) -> list[str]:
    if not value:
        return []

    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


def get_patient_clinical_profile(
    db: Session,
    patient_id
):
    now = datetime.now(timezone.utc)

    active_meds = (
        db.query(ActiveMedication)
        .filter(
            ActiveMedication.patient_id == patient_id,
            ActiveMedication.status == "ACTIVE",
            ActiveMedication.prescription_id.is_(None),
            (
                ActiveMedication.end_date.is_(None)
                | (ActiveMedication.end_date > now)
            )
        )
        .all()
    )

    unverified_prescription_meds = (
        db.query(ActiveMedication)
        .filter(
            ActiveMedication.patient_id == patient_id,
            ActiveMedication.status == "ACTIVE",
            ActiveMedication.prescription_id.is_not(None),
            (
                ActiveMedication.end_date.is_(None)
                | (ActiveMedication.end_date > now)
            )
        )
        .all()
    )

    profile = (
        db.query(User)
        .filter(User.id == patient_id)
        .first()
    )

    if profile is None:
        raise ValueError("Patient not found")

    return {
        "active_rxcuis": [
            med.rxcui
            for med in active_meds
            if med.rxcui
        ],

        "active_ingredients": [
            ingredient
            for med in active_meds
            for ingredient in (med.ingredients or [])
        ],

        "unresolved_active_medications": [
            med.name
            for med in active_meds
            if not med.rxcui
        ],

        "unverified_prescription_medications": [
            med.name for med in unverified_prescription_meds
        ],

        "conditions": _split_patient_values(
            profile.medical_condition
        ),

        "allergies": _split_patient_values(
            profile.allergy
        ),
    }