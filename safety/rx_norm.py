# services/rx_norm.py

import httpx
from pydantic import BaseModel, Field
from typing import Optional

from safety.errors import SafetyDataUnavailable


class NormalizedDrug(BaseModel):
    raw_name: str
    rxcui: Optional[str] = None
    concept_name: Optional[str] = None
    ingredients: list[str] = Field(default_factory=list)


RXNAV_URL = "https://rxnav.nlm.nih.gov/REST"


async def normalize_drug_name(
    raw_drug_name: str
) -> NormalizedDrug:

    async with httpx.AsyncClient(timeout=10.0) as client:

        try:
            response = await client.get(
                f"{RXNAV_URL}/approximateTerm.json",
                params={
                    "term": raw_drug_name,
                    "maxEntries": 1
                }
            )
        except httpx.HTTPError as exc:
            raise SafetyDataUnavailable(
                "RxNorm drug lookup could not be reached."
            ) from exc

        if response.status_code != 200:
            raise SafetyDataUnavailable(
                f"RxNorm drug lookup returned HTTP {response.status_code}."
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise SafetyDataUnavailable(
                "RxNorm returned an unreadable drug lookup response."
            ) from exc

        if not isinstance(data, dict):
            raise SafetyDataUnavailable(
                "RxNorm returned an invalid drug lookup response."
            )

        approximate_group = data.get("approximateGroup", {})
        if not isinstance(approximate_group, dict):
            raise SafetyDataUnavailable(
                "RxNorm returned an invalid drug lookup response."
            )
        candidates = approximate_group.get("candidate", [])
        if not isinstance(candidates, list):
            raise SafetyDataUnavailable(
                "RxNorm returned an invalid drug candidate list."
            )

        if not candidates:
            return NormalizedDrug(
                raw_name=raw_drug_name
            )

        rxcui = candidates[0].get("rxcui")
        concept_name = candidates[0].get("name")

        if not rxcui:
            return NormalizedDrug(
                raw_name=raw_drug_name,
                concept_name=concept_name
            )

        try:
            ing_response = await client.get(
                f"{RXNAV_URL}/rxcui/{rxcui}/allrelated.json"
            )
        except httpx.HTTPError as exc:
            raise SafetyDataUnavailable(
                "RxNorm ingredient lookup could not be reached."
            ) from exc

        if ing_response.status_code != 200:
            raise SafetyDataUnavailable(
                "RxNorm did not return ingredient data for the matched medicine."
            )

        try:
            ing_data = ing_response.json()
        except ValueError as exc:
            raise SafetyDataUnavailable(
                "RxNorm returned unreadable ingredient data."
            ) from exc

        ingredients = []

        if not isinstance(ing_data, dict):
            raise SafetyDataUnavailable(
                "RxNorm returned invalid ingredient data."
            )
        related_group = ing_data.get("allRelatedGroup", {})
        if not isinstance(related_group, dict):
            raise SafetyDataUnavailable(
                "RxNorm returned invalid ingredient data."
            )
        concept_groups = related_group.get("conceptGroup", [])
        if not isinstance(concept_groups, list):
            raise SafetyDataUnavailable(
                "RxNorm returned an invalid ingredient group list."
            )

        for group in concept_groups:
            if not isinstance(group, dict):
                raise SafetyDataUnavailable(
                    "RxNorm returned an invalid ingredient group."
                )

            if group.get("tty") != "IN":
                continue

            concepts = group.get("conceptProperties", [])
            if not isinstance(concepts, list):
                raise SafetyDataUnavailable(
                    "RxNorm returned an invalid ingredient list."
                )
            for concept in concepts:
                if not isinstance(concept, dict):
                    raise SafetyDataUnavailable(
                        "RxNorm returned invalid ingredient details."
                    )
                name = concept.get("name")

                if name:
                    ingredients.append(
                        name.lower()
                    )

        return NormalizedDrug(
            raw_name=raw_drug_name,
            rxcui=rxcui,
            concept_name=concept_name,
            ingredients=ingredients
        )