from pydantic import BaseModel
from datetime import datetime
from typing import List


class MedicationResponse(BaseModel):
    medication_id: str
    name: str
    rxcui: str | None = None
    ingredients: List[str]
    status: str
    start_date: datetime | None = None
    end_date: datetime | None = None
    prescription_id: str | None = None
    dosage: str | None = None
    frequency: str | None = None
    duration: str | None = None
    prescription_date: str | None = None
    document_name: str | None = None