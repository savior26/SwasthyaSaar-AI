# ==========================================
# 1. RXNORM CORRECTION & NORMALIZATION AGENT
# ==========================================
import requests

def rxnorm_correct(candidate_name: str, max_entries: int = 5):
    """
    Takes a raw OCR/vision-LLM guess at a drug name and returns
    the closest real RxNorm drug name + RxCUI + confidence score.
    """
    try:
        resp = requests.get(
            "https://rxnav.nlm.nih.gov/REST/approximateTerm.json",
            params={"term": candidate_name, "maxEntries": max_entries, "option": 1},
            timeout=5,
        )
        resp.raise_for_status()

        candidates = resp.json().get("approximateGroup", {}).get("candidate", [])
        if not candidates:
            return None  # No match found

        best = candidates[0]  # Rank 1 is the best lexical match
        rxcui = best["rxcui"]
        score = float(best["score"])

        # Resolve the rxcui back into an actual drug name string
        name_resp = requests.get(
            f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/property.json",
            params={"propName": "RxNorm Name"},
            timeout=5,
        )
        name_resp.raise_for_status()
        props = name_resp.json().get("propConceptGroup", {}).get("propConcept", [])
        resolved_name = props[0]["propValue"] if props else candidate_name

        return {"corrected_name": resolved_name, "rxcui": rxcui, "score": score}
    except Exception:
        return None
