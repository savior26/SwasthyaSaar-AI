# app/services/checker_dai.py
from typing import List, Dict

def check_drug_allergy_conflicts(new_drug_ingredients: List[str], patient_allergies: List[str]) -> List[Dict]:
    conflicts = []
    normalized_allergies = [a.lower() for a in patient_allergies]

    for ingredient in new_drug_ingredients:
        ing_lower = ingredient.lower()
        for allergy in normalized_allergies:
            if allergy in ing_lower or ing_lower in allergy:
                conflicts.append({
                    "type": "DRUG_ALLERGY",
                    "drug": ingredient,
                    "allergy": allergy,
                    "description": f"Potential severe allergic reaction: {ingredient} matches patient's documented allergy to {allergy}.",
                    "severity": "CRITICAL"
                })
    return conflicts