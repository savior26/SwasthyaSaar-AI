from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.model import SafetyCheck
from models.user_model import User
from routes.auth import get_current_user


router = APIRouter(
    prefix="/safety",
    tags=["Safety"],
)


@router.get("/alerts")
def get_safety_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    checks = (
        db.query(SafetyCheck)
        .options(
            joinedload(SafetyCheck.conflicts),
            joinedload(SafetyCheck.document),
        )
        .filter(SafetyCheck.patient_id == current_user.id)
        .order_by(SafetyCheck.created_at.desc())
        .all()
    )

    alerts = []
    assessments = []

    for check in checks:
        conflicts = [
            {
                "type": conflict.conflict_type,
                "drug": conflict.drug,
                "drug_a": conflict.drug_a,
                "drug_b": conflict.drug_b,
                "allergy": conflict.allergy,
                "condition": conflict.condition,
                "description": conflict.description,
                "severity": conflict.severity,
            }
            for conflict in check.conflicts
        ]

        assessment_incomplete = bool(
            check.patient_alert_message
            and check.patient_alert_message.startswith("Assessment incomplete:")
        )
        attention_required = bool(
            conflicts or check.has_critical_issue
        )
        assessments.append(
            {
                "safety_check_id": str(check.safety_check_id),
                "doc_id": str(check.doc_id),
                "document_name": check.document.original_filename,
                "created_at": check.created_at,
                "has_critical_issue": check.has_critical_issue,
                "patient_alert_message": check.patient_alert_message,
                "action_required": check.action_required,
                "status": (
                    "incomplete"
                    if assessment_incomplete
                    else "attention_required"
                    if attention_required
                    else "no_conflicts_detected"
                ),
                "conflicts": conflicts,
            }
        )

        for conflict in check.conflicts:
            alerts.append(
                {
                    "title": conflict.conflict_type,
                    "severity": conflict.severity,
                    "description": (
                        conflict.description
                        or check.patient_alert_message
                        or ""
                    ),
                    "patient_alert_message": check.patient_alert_message,
                    "action_required": check.action_required,
                    "created_at": check.created_at,
                }
            )

        if (
            not check.conflicts
            and attention_required
        ):
            alerts.append(
                {
                    "title": (
                        "Critical safety issue"
                        if check.has_critical_issue
                        else "Action required"
                    ),
                    "severity": (
                        "CRITICAL"
                        if check.has_critical_issue
                        else "REVIEW"
                    ),
                    "description": (
                        check.action_required
                        or check.patient_alert_message
                        or ""
                    ),
                    "patient_alert_message": check.patient_alert_message,
                    "action_required": check.action_required,
                    "created_at": check.created_at,
                }
            )

    return {
        "assessment_available": bool(assessments),
        "assessments": assessments,
        "alerts": alerts,
        "assessment_incomplete": any(
            assessment["status"] == "incomplete"
            for assessment in assessments
        ),
    }
