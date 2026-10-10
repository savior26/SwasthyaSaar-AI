from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# ============================================================
# PATIENT INFORMATION
# ============================================================

class PatientInformation(BaseModel):
    name: str
    gender: Optional[str] = None
    age: Optional[int] = None
    medical_condition: Optional[str] = None
    allergy: Optional[str] = None


# ============================================================
# EXTRACTED SYMPTOM INFORMATION
# ============================================================

class SymptomDetails(BaseModel):
    symptom: str

    location: Optional[str] = None
    onset: Optional[str] = None
    duration: Optional[str] = None

    severity: Optional[str] = None
    character: Optional[str] = None
    frequency: Optional[str] = None

    aggravating_factors: Optional[str] = None
    relieving_factors: Optional[str] = None

    associated_symptoms: List[str] = Field(default_factory=list)
    negative_symptoms: List[str] = Field(default_factory=list)


# ============================================================
# FINAL DOCTOR REPORT
# ============================================================

class PatientSymptomReport(BaseModel):

    patient: PatientInformation

    chief_complaint: str

    symptom_details: List[SymptomDetails] = Field(
        default_factory=list
    )

    patient_description: Optional[str] = None

    additional_information: Optional[str] = None


# ============================================================
# ANSWER ANALYSIS
# ============================================================

class PatientAnswerAnalysis(BaseModel):

    language: Literal[
        "english",
        "hindi",
        "hinglish"
    ]

    extracted_information: dict = Field(
        default_factory=dict
    )


# ============================================================
# NEXT QUESTION
# ============================================================

class NextQuestion(BaseModel):

    question: str

    category: str

    complete: bool = False


# ============================================================
# AGENT RESPONSE
# ============================================================

class PatientSummaryResponse(BaseModel):

    session_id: str

    question: Optional[str] = None

    completed: bool = False

    emergency: bool = False

    emergency_message: Optional[str] = None

    report: Optional[PatientSymptomReport] = None


class PatientSummaryReportRecord(BaseModel):
    session_id: str
    completed_at: datetime
    report: PatientSymptomReport


class PatientSummaryAnswerRequest(BaseModel):
    answer: str = Field(..., min_length=1)