import json
from typing import Any


SEVERE_INTERACTION_LEVELS = {"severe", "critical", "major", "contraindicated"}


def _to_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if not isinstance(value, str):
        return {}

    text = value.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].removesuffix("```").strip()
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return result if isinstance(result, dict) else {}


def generate_lab_report_alerts(lab_report: Any) -> list[dict[str, str]]:
    report = _to_dict(lab_report)
    alerts = []
    for test in report.get("tests", []):
        if not isinstance(test, dict):
            continue
        flag = str(test.get("flag") or "").strip().lower()
        if flag not in {"high", "low", "abnormal"}:
            continue

        test_name = str(test.get("test_name") or "Lab test")
        value = " ".join(
            part for part in (str(test.get("value") or "").strip(), str(test.get("unit") or "").strip())
            if part
        )
        reference_range = str(test.get("reference_range") or "").strip()
        details = [part for part in (value, f"Reference range: {reference_range}" if reference_range else "") if part]
        alerts.append({
            "type": "lab_result",
            "severity": "warning",
            "title": f"{flag.title()} lab result: {test_name}",
            "message": ". ".join(details) or f"The report flags {test_name} as {flag}.",
        })
    return alerts


def generate_drug_interaction_alerts(safety_analysis: Any) -> list[dict[str, str]]:
    analysis_result = _to_dict(safety_analysis)
    alerts = []
    for pair in analysis_result.get("drug_interactions", []):
        if not isinstance(pair, dict):
            continue
        finding = _to_dict(pair.get("analysis"))
        interaction_found = finding.get("interaction_found")
        if not (interaction_found is True or str(interaction_found).strip().lower() == "true"):
            continue

        severity = str(finding.get("severity") or "").strip().lower()
        if severity not in SEVERE_INTERACTION_LEVELS:
            continue

        drug_a = str(pair.get("drug_a") or finding.get("drug_a") or "Drug A")
        drug_b = str(pair.get("drug_b") or finding.get("drug_b") or "Drug B")
        message = str(
            finding.get("interaction_detail")
            or finding.get("patient_message")
            or "The analysis identified a high-severity interaction."
        )
        alerts.append({
            "type": "drug_interaction",
            "severity": severity,
            "title": f"Potential {severity} interaction: {drug_a} + {drug_b}",
            "message": message,
        })
    return alerts
