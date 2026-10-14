from typing import List, Dict, Any
from services.api_call import tavily_client

class DrugAllergyAgent:
    """Uses Tavily AI Search with strict entity validation to detect allergy risks."""

    # Antibiotics/drugs that genuinely share cross-reactivity risks with Penicillin
    BETA_LACTAMS = [
        "penicillin", "amoxicillin", "ampicillin", "augmentin", 
        "cephalexin", "ceftriaxone", "cef", "piperacillin", "aztreonam", "meropenem"
    ]

    @classmethod
    def check_allergy(cls, drug_name: str, allergies: List[str]) -> List[Dict[str, Any]]:
        findings = []
        drug_lower = drug_name.lower()

        for allergy in allergies:
            allergy_lower = allergy.lower()

            # --- GUARDRAIL 1: Penicillin Cross-Reactivity Rule ---
            # If checking Penicillin allergy, skip non-beta-lactams (like Neogadine, Atenolol, Lisinopril)
            if "penicillin" in allergy_lower:
                is_beta_lactam = any(b in drug_lower for b in cls.BETA_LACTAMS)
                if not is_beta_lactam:
                    continue  # Safely skip false-positive search for non-beta-lactam drugs

            query = f"Is {drug_name} cross-reactive or contraindicated for patients allergic to {allergy}?"

            try:
                search_res = tavily_client.search(
                    query=query,
                    include_domains=["fda.gov", "ncbi.nlm.nih.gov", "drugs.com"],
                    search_depth="advanced",
                    max_results=2
                )

                results = search_res.get("results", [])
                for result in results:
                    content = result.get("content", "").lower()
                    title = result.get("title", "").lower()
                    full_text = content + " " + title

                    # --- GUARDRAIL 2: Entity Mention Safeguard ---
                    # Ensure the retrieved snippet actually mentions the specific drug/supplement
                    if drug_lower in full_text:
                        if any(term in content for term in ["cross-react", "contraindicated", "severe reaction"]):
                            findings.append({
                                "type": "Drug-Allergy Risk",
                                "severity": "High",
                                "description": f"Potential cross-reactivity detected between {drug_name} and allergen '{allergy}'.",
                                "source_url": result.get("url")
                            })
                            break
            except Exception as e:
                findings.append({"type": "Error", "description": f"Tavily search failed: {str(e)}"})

        return findings


drug_allergy_check= DrugAllergyAgent()
