
import requests
from typing import List, Dict, Any


class DrugDiseaseAgent:
    """Queries OpenFDA for contraindications and warnings across all safety sections."""
    
    @staticmethod
    def check_contraindications(drug_name: str, disease: str) -> List[Dict[str, Any]]:
        url = f'https://api.fda.gov/drug/label.json?search=openfda.generic_name:"{drug_name}"&limit=1'
        warnings = []
        
        try:
            res = requests.get(url, timeout=5).json()
            results = res.get("results", [])
            if results:
                label = results[0]
                
                # Aggregate multiple high-risk safety fields from the FDA label
                safety_fields = ["contraindications", "boxed_warning", "warnings", "pregnancy"]
                combined_text_parts = []
                
                for field in safety_fields:
                    if field in label:
                        content = label[field]
                        if isinstance(content, list):
                            combined_text_parts.extend(content)
                        elif isinstance(content, str):
                            combined_text_parts.append(content)
                
                full_label_text = " ".join(combined_text_parts).lower()
                
                # Check if the disease/condition keyword appears anywhere in the safety profile
                if disease.lower() in full_label_text:
                    warnings.append({
                        "type": "Drug-Disease Contraindication",
                        "severity": "Critical",
                        "description": f"{drug_name.capitalize()} contains explicit FDA safety or boxed warnings regarding '{disease}'."
                    })
        except Exception as e:
            pass
            
        return warnings

drug_disease_agent= DrugDiseaseAgent()