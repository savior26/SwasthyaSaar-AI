# services/drug_drug.py

import httpx

from safety.errors import SafetyDataUnavailable


async def check_drug_drug_interactions(
    new_rxcuis: list[str],
    active_rxcuis: list[str]
) -> list[dict]:

    if not new_rxcuis or not active_rxcuis:
        return []

    conflicts = []

    async with httpx.AsyncClient(
        timeout=10.0
    ) as client:

        for new_rxcui in new_rxcuis:

            for active_rxcui in active_rxcuis:

                if new_rxcui == active_rxcui:
                    continue

                url = (
                    "https://rxnav.nlm.nih.gov/REST/"
                    "interaction/list.json"
                )

                params = {
                    "rxcuis": (
                        f"{new_rxcui}+{active_rxcui}"
                    )
                }

                try:
                    response = await client.get(
                        url,
                        params=params
                    )
                except httpx.HTTPError as exc:
                    raise SafetyDataUnavailable(
                        "RxNav interaction screening could not be reached."
                    ) from exc

                if response.status_code != 200:
                    raise SafetyDataUnavailable(
                        f"RxNav interaction screening returned HTTP {response.status_code}."
                    )

                try:
                    data = response.json()
                except ValueError as exc:
                    raise SafetyDataUnavailable(
                        "RxNav returned unreadable interaction data."
                    ) from exc

                if not isinstance(data, dict):
                    raise SafetyDataUnavailable(
                        "RxNav returned an invalid interaction response."
                    )
                groups = data.get("fullInteractionTypeGroup", [])
                if not isinstance(groups, list):
                    raise SafetyDataUnavailable(
                        "RxNav returned an invalid interaction group list."
                    )

                for group in groups:
                    if not isinstance(group, dict):
                        raise SafetyDataUnavailable(
                            "RxNav returned an invalid interaction group."
                        )

                    interaction_types = group.get("fullInteractionType", [])
                    if not isinstance(interaction_types, list):
                        raise SafetyDataUnavailable(
                            "RxNav returned an invalid interaction list."
                        )
                    for interaction_type in interaction_types:
                        if not isinstance(interaction_type, dict):
                            raise SafetyDataUnavailable(
                                "RxNav returned invalid interaction details."
                            )

                        min_concepts = (
                            interaction_type.get(
                                "minConcept",
                                []
                            )
                        )

                        for pair in interaction_type.get(
                            "interactionPair",
                            []
                        ):
                            if not isinstance(pair, dict):
                                raise SafetyDataUnavailable(
                                    "RxNav returned an invalid interaction pair."
                                )

                            drug_a = (
                                min_concepts[0].get("name")
                                if len(min_concepts) > 0
                                else new_rxcui
                            )

                            drug_b = (
                                min_concepts[1].get("name")
                                if len(min_concepts) > 1
                                else active_rxcui
                            )

                            conflicts.append({
                                "type": "DRUG_DRUG",
                                "drug_a": drug_a,
                                "drug_b": drug_b,
                                "description": pair.get(
                                    "description"
                                ),
                                "severity": (
                                    pair.get("severity") or "HIGH"
                                ).upper()
                            })

    return conflicts