# services/clinical_reasoner.py

from pydantic import BaseModel

from services.api_call import ai_Model


class TriageReport(BaseModel):
    has_critical_issue: bool
    patient_alert_message: str
    doctor_clinical_note: str
    action_required: str


def format_clinical_triage(
    raw_conflicts: list[dict],
    language: str = "en"
) -> TriageReport:

    if not raw_conflicts:

        return TriageReport(
            has_critical_issue=False,
            patient_alert_message=(
                "No medication conflict was detected "
                "by the available safety checks."
            ),
            doctor_clinical_note=(
                "No conflict detected by the configured "
                "medication safety screening pipeline."
            ),
            action_required=(
                "Continue with routine clinical review."
            )
        )

    prompt = f"""
You are a clinical medication safety assistant.

Review ONLY the detected conflicts below.

Do not invent additional interactions,
allergies, contraindications, or diagnoses.

Conflicts:
{raw_conflicts}

Output language:
{language}

Tasks:
1. Set has_critical_issue=true if any conflict
   has severity CRITICAL or HIGH.
2. Explain the detected safety concern in
   patient-friendly language.
3. Write a concise doctor-ready clinical note.
4. Give the appropriate next action.

This is a safety screening result,
not an autonomous prescribing decision.
"""

    structured_model = ai_Model.with_structured_output(
        TriageReport
    )

    response = structured_model.invoke(prompt)

    if isinstance(response, TriageReport):
        return response

    return TriageReport.model_validate(response)
