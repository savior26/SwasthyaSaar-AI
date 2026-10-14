import json
from typing import Dict, Any
from utils.prescription_safety.ddi import drug_drug_agent
from utils.prescription_safety.dai import drug_allergy_check 
from utils.prescription_safety.drug_disease_safety import drug_disease_agent 
from utils.prescription_safety.rxnorm import rxnorm_correct 
from utils.prescription_safety.tavily_brand import tavily_resolve_brand

# ==========================================
# 3. PIPELINE ORCHESTRATOR
# ==========================================
class PrescriptionSafetyPipeline:
    """Orchestrates correction, multi-agent evaluation, and safety reporting."""
    
    def __init__(self):
        self.ddi_agent = drug_drug_agent
        self.disease_agent = drug_disease_agent
        self.allergy_agent = drug_allergy_check

    def run_pipeline(self, prescription: Dict[str, Any]) -> Dict[str, Any]:
        raw_drugs = prescription.get("drugs", [])
        diseases = prescription.get("diseases", [])
        allergies = prescription.get("allergies", [])
        
        normalized_mappings = {}
        corrected_drug_list = []
        
        # Step 1: Correct and Normalize Raw Inputs via RxNorm ApproximateTerm
        for raw_drug in raw_drugs:
            correction_res = rxnorm_correct(raw_drug)
            if correction_res and correction_res["corrected_name"]:
              resolved_name = correction_res["corrected_name"]
              normalized_mappings[raw_drug] = {
                  "type": "Standard Generic/Brand",
                  "corrected_name": resolved_name,
                  "rxcui": correction_res["rxcui"],
                  "match_score": correction_res["score"]
              }
              corrected_drug_list.append(resolved_name)
            else:
              # Step 2: Fallback to Tavily Dynamic Brand Resolution for unknown/regional drugs
              brand_info = tavily_resolve_brand(raw_drug)
              if brand_info:
                  normalized_mappings[raw_drug] = {
                      "type": "Regional/Compounded Brand (Tavily Resolved)",
                      "corrected_name": raw_drug,
                      "composition": brand_info["composition_summary"],
                      "source_url": brand_info["source_url"]
                  }
                  # Keep the raw brand name or extracted components for safety checks
                  corrected_drug_list.append(raw_drug)
              else:
                  normalized_mappings[raw_drug] = {
                      "type": "Unresolved",
                      "corrected_name": None,
                      "rxcui": None
                  }
                  corrected_drug_list.append(raw_drug)
        safety_alerts = []

        # Step 2: Run Safety Agents on the Cleaned/Corrected Drug Names
        ddi_alerts = self.ddi_agent.check_interaction(corrected_drug_list)
        safety_alerts.extend(ddi_alerts)

        for drug in corrected_drug_list:
            for disease in diseases:
                disease_alerts = self.disease_agent.check_contraindications(drug, disease)
                safety_alerts.extend(disease_alerts)

            allergy_alerts = self.allergy_agent.check_allergy(drug, allergies)
            safety_alerts.extend(allergy_alerts)

        # Step 3: Synthesis & Status Determination
        severe_severities = {"high", "critical", "severe", "contraindicated"}
        has_severe_alert = any(
            str(alert.get("severity", "")).strip().lower() in severe_severities
            for alert in safety_alerts
        )
        has_failed_check = any(
            str(alert.get("type", "")).strip().lower() == "error"
            for alert in safety_alerts
        )
        status = (
            "FLAGGED_FOR_REVIEW"
            if has_severe_alert or has_failed_check
            else "APPROVED"
        )

        return {
            "prescription_status": status,
            "normalization_details": normalized_mappings,
            "total_alerts": len(safety_alerts),
            "alerts": safety_alerts
        }


safety_pipeline = PrescriptionSafetyPipeline()

