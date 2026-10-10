from pydantic import BaseModel, Field
from typing import Optional, List, Literal

# lab report schema
class LabTestItem(BaseModel):
    test_name: str
    value: Optional[str] = None
    unit: Optional[str] = Field(None, description="Unit of measurement, e.g., g/dL, mg/dL")
    reference_range: Optional[str] = None
    flag: Optional[Literal["normal", "high", "low", "abnormal", "unknown"]] = "unknown"

class LabReportData(BaseModel):
    lab_name: Optional[str] = None
    date: Optional[str] = Field(None, description="return datetime in format : dd-mm-yyyy")
    patient_name: Optional[str] = None
    tests: List[LabTestItem] = Field(default_factory=list)


# prescription schema
class MedicineItem(BaseModel):
    name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    instructions: Optional[str] = None

class PrescriptionData(BaseModel):
    doctor_name: Optional[str] = None
    hospital_name: Optional[str] = None
    date: Optional[str] = None
    patient_name: Optional[str] = None
    medicines: List[MedicineItem] = Field(default_factory=list)
    notes: Optional[str] = None