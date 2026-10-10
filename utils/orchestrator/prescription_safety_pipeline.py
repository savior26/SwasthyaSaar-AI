from sqlalchemy.orm import Session
from safety.rx_norm import NormalizedDrug, normalize_drug_name
from safety.patient_context import get_patient_clinical_profile
from safety.drug_allergy import check_drug_allergy_conflicts
from safety.drug_drug import check_drug_drug_interactions
from safety.drug_disease import check_drug_disease_conflicts
from safety.clinical_reasoner import TriageReport, format_clinical_triage
from safety.errors import SafetyDataUnavailable
import logging

from langchain_core.exceptions import OutputParserException
from langchain_google_genai.chat_models import GoogleAPIError
from pydantic import ValidationError


logger = logging.getLogger(__name__)

async def run_safety_pipeline(
    db: Session,
    patient_id,
    new_drug_names: list[str],
    language: str = "en"
):

    # ========================================================
    # 1. GET PATIENT CONTEXT
    # ========================================================

    patient = get_patient_clinical_profile(
        db=db,
        patient_id=patient_id
    )


    # ========================================================
    # 2. NORMALIZE NEW MEDICINES WITH RXNORM
    # ========================================================

    normalized_drugs = []
    assessment_limitations = []

    if not new_drug_names:
        assessment_limitations.append(
            "No medicine names were extracted from the prescription."
        )

    for raw_name in new_drug_names:

        if not raw_name or not raw_name.strip():
            assessment_limitations.append(
                "A medicine name was empty and could not be checked."
            )
            continue

        try:
            normalized = await normalize_drug_name(raw_name.strip())
        except SafetyDataUnavailable as exc:
            assessment_limitations.append(str(exc))
            normalized = NormalizedDrug(raw_name=raw_name.strip())

        normalized_drugs.append(normalized)

        if not normalized.rxcui:
            assessment_limitations.append(
                f"Could not identify '{raw_name.strip()}' in RxNorm."
            )
        elif not normalized.ingredients:
            assessment_limitations.append(
                f"Ingredient data could not be confirmed for '{raw_name.strip()}'."
            )

    print('*'*50)
    print("normalized response:\n",normalized_drugs)

    # ========================================================
    # 3. KEEP ONLY DRUGS SUCCESSFULLY NORMALIZED
    # ========================================================

    valid_drugs = [
        drug
        for drug in normalized_drugs
        if drug.rxcui
    ]

    new_rxcuis = [
        drug.rxcui
        for drug in valid_drugs
    ]

    new_ingredients = [
        ingredient
        for drug in valid_drugs
        for ingredient in drug.ingredients
    ]

    if patient["unresolved_active_medications"]:
        assessment_limitations.append(
            "Some recorded active medicines could not be matched to RxNorm for interaction screening."
        )

    if patient["unverified_prescription_medications"]:
        assessment_limitations.append(
            "Prescription-recorded medicines have not been confirmed as currently used and were excluded from interaction screening."
        )

    # ========================================================
    # 4. DRUG-ALLERGY CHECK
    # ========================================================

    allergy_conflicts = (
        check_drug_allergy_conflicts(
            new_drug_ingredients=new_ingredients,
            patient_allergies=patient["allergies"]
        )
    )

    print('*'*50)
    print("allergy_confict:\n",allergy_conflicts)

    # ========================================================
    # 5. DRUG-DRUG CHECK
    # ========================================================

    try:
        drug_drug_conflicts = (
            await check_drug_drug_interactions(
                new_rxcuis=new_rxcuis,
                active_rxcuis=patient["active_rxcuis"]
            )
        )
    except SafetyDataUnavailable as exc:
        drug_drug_conflicts = []
        assessment_limitations.append(str(exc))

    print('*'*50)
    print("drug_drug_conflicts:\n",drug_drug_conflicts)

    # ========================================================
    # 6. DRUG-DISEASE CHECK
    # ========================================================

    try:
        disease_conflicts = (
            await check_drug_disease_conflicts(
                drug_ingredients=new_ingredients,
                patient_conditions=patient["conditions"]
            )
        )
    except SafetyDataUnavailable as exc:
        disease_conflicts = []
        assessment_limitations.append(str(exc))

    print('*'*50)
    print("disease_conflicts:\n",disease_conflicts)
    
    # ========================================================
    # 7. COMBINE RAW CONFLICTS
    # ========================================================

    raw_conflicts = (
        allergy_conflicts
        + drug_drug_conflicts
        + disease_conflicts
    )

    # ========================================================
    # 8. CLINICAL REASONER
    # ========================================================

    try:
        triage = format_clinical_triage(
            raw_conflicts=raw_conflicts,
            language=language
        )
    except (GoogleAPIError, OutputParserException, ValidationError, ValueError):
        logger.exception("Clinical triage generation failed.")
        assessment_limitations.append(
            "Clinical triage could not be generated."
        )
        triage = TriageReport(
            has_critical_issue=any(
                str(conflict.get("severity", "")).upper()
                in {"HIGH", "CRITICAL"}
                for conflict in raw_conflicts
            ),
            patient_alert_message=(
                "Known safety findings were detected, but the clinical summary is unavailable."
                if raw_conflicts
                else "Assessment incomplete: clinical triage could not be generated."
            ),
            doctor_clinical_note=(
                "Review the recorded medication safety findings directly."
            ),
            action_required=(
                "Have a qualified clinician or pharmacist review this prescription and the patient's current medication list."
            ),
        )

    if assessment_limitations:
        limitation_text = " ".join(dict.fromkeys(assessment_limitations))
        triage.patient_alert_message = (
            f"Assessment incomplete: {limitation_text} "
            "No complete safety conclusion can be drawn from this check."
        )
        triage.action_required = (
            "Have a qualified clinician or pharmacist manually review this prescription and the patient's current medication list."
        )

    print('*'*50)
    print("triage:\n",triage)

    # ========================================================
    # 9. RETURN RESULT
    # ========================================================

    return {
        "normalized_drugs": [
            {
                "raw_name": drug.raw_name,
                "rxcui": drug.rxcui,
                "concept_name": drug.concept_name,
                "ingredients": drug.ingredients
            }
            for drug in normalized_drugs
        ],

        "conflicts": raw_conflicts,
        "assessment_complete": not assessment_limitations,
        "assessment_limitations": list(dict.fromkeys(assessment_limitations)),

        "triage": triage.model_dump()
    }
