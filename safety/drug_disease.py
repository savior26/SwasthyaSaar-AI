# services/drug_disease.py

import httpx

from safety.errors import SafetyDataUnavailable


async def check_drug_disease_conflicts(
    drug_ingredients: list[str],
    patient_conditions: list[str]
) -> list[dict]:

    if not drug_ingredients or not patient_conditions:
        return []

    conflicts = []

    async with httpx.AsyncClient(timeout=10.0) as client:

        for ingredient in drug_ingredients:

            url = "https://api.fda.gov/drug/label.json"

            try:
                response = await client.get(
                    url,
                    params={
                        "search": f'openfda.substance_name:"{ingredient}"',
                        "limit": 1,
                    },
                )
            except httpx.HTTPError as exc:
                raise SafetyDataUnavailable(
                    "FDA drug-label screening could not be reached."
                ) from exc

            if response.status_code != 200:
                raise SafetyDataUnavailable(
                    f"FDA drug-label screening returned HTTP {response.status_code}."
                )

            try:
                payload = response.json()
            except ValueError as exc:
                raise SafetyDataUnavailable(
                    "FDA returned unreadable drug-label data."
                ) from exc

            if not isinstance(payload, dict):
                raise SafetyDataUnavailable(
                    "FDA returned invalid drug-label data."
                )
            results = payload.get("results", [])
            if not isinstance(results, list):
                raise SafetyDataUnavailable(
                    "FDA returned an invalid drug-label result list."
                )
            if not results:
                raise SafetyDataUnavailable(
                    f"No FDA drug-label record was available for {ingredient}."
                )

            label_data = results[0]
            if not isinstance(label_data, dict):
                raise SafetyDataUnavailable(
                    "FDA returned invalid drug-label details."
                )

            warning_sections = [
                label_data.get("warnings", []),
                label_data.get("contraindications", []),
                label_data.get("boxed_warning", []),
            ]
            if any(not isinstance(section, list) for section in warning_sections):
                raise SafetyDataUnavailable(
                    "FDA returned invalid drug-label warning data."
                )

            warnings_text = " ".join(
                warning_sections[0]
                + warning_sections[1]
                + warning_sections[2]
            ).lower()

            for condition in patient_conditions:

                if condition.lower() in warnings_text:

                    conflicts.append({
                        "type": "DRUG_DISEASE",
                        "drug": ingredient,
                        "condition": condition,
                        "description": (
                            f"{ingredient.title()} carries "
                            f"contraindications/warnings for "
                            f"patients with {condition}."
                        ),
                        "severity": "HIGH"
                    })

    return conflicts