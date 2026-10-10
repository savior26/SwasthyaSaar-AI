# services/safety_storage.py

from sqlalchemy.orm import Session

from models.model import *


def save_safety_result(
    db: Session,
    patient_id,
    doc_id,
    result: dict,
    language: str
):

    triage = result["triage"]
    assessment_limitations = result.get(
        "assessment_limitations",
        [],
    )
    patient_alert_message = triage["patient_alert_message"]
    action_required = triage["action_required"]

    if assessment_limitations:
        patient_alert_message = (
            "Assessment incomplete: "
            + " ".join(dict.fromkeys(assessment_limitations))
            + " No complete safety conclusion can be drawn from this check."
        )
        action_required = (
            "Have a qualified clinician or pharmacist manually review this prescription and the patient's current medication list."
        )

    safety_check = SafetyCheck(
        patient_id=patient_id,
        doc_id=doc_id,
        has_critical_issue=triage[
            "has_critical_issue"
        ],
        patient_alert_message=patient_alert_message,
        doctor_clinical_note=triage[
            "doctor_clinical_note"
        ],
        action_required=action_required,
        language=language
    )

    db.add(safety_check)

    db.flush()

    for conflict in result["conflicts"]:

        safety_conflict = SafetyConflict(
            safety_check_id=safety_check.safety_check_id,

            conflict_type=conflict.get(
                "type"
            ),

            drug=conflict.get(
                "drug"
            ),

            drug_a=conflict.get(
                "drug_a"
            ),

            drug_b=conflict.get(
                "drug_b"
            ),

            allergy=conflict.get(
                "allergy"
            ),

            condition=conflict.get(
                "condition"
            ),

            description=conflict.get(
                "description"
            ),

            severity=conflict.get(
                "severity",
                "UNKNOWN"
            )
        )

        db.add(safety_conflict)

    return safety_check