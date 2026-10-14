from typing import List, Dict, Any
from services.api_call import tavily_client


# ==========================================
# 2. SPECIALIZED SAFETY CHECK AGENTS
# ==========================================
class DrugDrugAgent:
    """Checks pairwise interactions between active prescriptions using Tavily AI Search with strict validation."""

    INERT_CLASSES = ["sodium chloride","hydroxypropyl methylcellulose","hydroxypropylcellulose","carboxymethycellullose", "hpmc","cmc","saline", "water", "tear", "glycerin"]
    
    @staticmethod
    def check_interaction(drugs: List[str]) -> List[Dict[str, Any]]:
        if len(drugs) < 2:
            return []
        
        interactions = []
        for i in range(len(drugs)):
            for j in range(i + 1, len(drugs)):
                drug1 = drugs[i]
                drug2 = drugs[j]

                # --- GUARDRAIL: Skip DDI checks for inert/topical vehicles ---
                if any(inert in drug1 for inert in DrugDrugAgent.INERT_CLASSES) or \
                   any(inert in drug2 for inert in DrugDrugAgent.INERT_CLASSES):
                    continue  # Saline, water, and artificial tears do not have systemic drug interactions
                
                query = f"Drug-drug interaction between {drug1} and {drug2} clinical severity and mechanism"
                
                try:
                    search_res = tavily_client.search(
                        query=query,
                        include_domains=["ncbi.nlm.nih.gov", "drugs.com", "fda.gov"],
                        search_depth="advanced",
                        max_results=3
                    )
                    
                    results = search_res.get("results", [])
                    interaction_found = False
                    
                    for result in results:
                        content = result.get("content", "").lower()
                        title = result.get("title", "").lower()
                        full_text = content + " " + title
                        
                        # --- STRICT VALIDATION GUARDRAIL ---
                        # Ensure the search page is actually discussing BOTH drugs 
                        # (Prevents pulling mismatched URLs for unmapped brand names)
                        drug1_tokens = [t for t in drug1.lower().split() if len(t) > 3]
                        drug2_tokens = [t for t in drug2.lower().split() if len(t) > 3]
                        
                        d1_present = any(token in full_text for token in drug1_tokens) or drug1.lower() in full_text
                        d2_present = any(token in full_text for token in drug2_tokens) or drug2.lower() in full_text
                        
                        if d1_present and d2_present:
                            if any(term in content for term in ["interaction", "bleed", "contraindicated", "monitor", "risk", "absorb", "decrease"]):
                                interactions.append({
                                    "type": "Drug-Drug Conflict",
                                    "severity": "High" if "bleed" in content or "contraindicated" in content else "Moderate",
                                    "description": f"Potential interaction found between {drug1} and {drug2}.",
                                    "source_url": result.get("url")
                                })
                                interaction_found = True
                                break
                                
                    # If it's a regional brand that couldn't be verified on standard clinical DBs, 
                    # we safely skip rather than posting a false mismatch (like Allopurinol).
                    
                except Exception as e:
                    interactions.append({"type": "Error", "description": f"DDI search failed: {str(e)}"})
                            
        return interactions


drug_drug_agent= DrugDrugAgent()