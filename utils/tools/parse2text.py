from schemas.doc_schema import LabReportData, PrescriptionData

def lab_report_to_text(result: LabReportData) -> str:

    text = f"""
Medical Lab Report

Laboratory: {result.lab_name or "Unknown"}
Date: {result.date or "Unknown"}
Patient: {result.patient_name or "Unknown"}

"""

    for test in result.tests:

        text += f"""
Test: {test.test_name}
Value: {test.value or "Unknown"}
Unit: {test.unit or "Unknown"}
Reference Range: {test.reference_range or "Unknown"}
Status: {test.flag or "unknown"}

"""

    return text.strip()


def prescription_to_text(result: PrescriptionData) -> str:

    text = f"""
Medical Prescription

Doctor: {result.doctor_name or "Unknown"}
Hospital: {result.hospital_name or "Unknown"}
Date: {result.date or "Unknown"}
Patient: {result.patient_name or "Unknown"}

"""

    for medicine in result.medicines:

        text += f"""
Medicine: {medicine.name}
Dosage: {medicine.dosage or "Unknown"}
Frequency: {medicine.frequency or "Unknown"}
Duration: {medicine.duration or "Unknown"}
Instructions: {medicine.instructions or "Unknown"}

"""

    text += f"""
Notes: {result.notes or "None"}
"""

    return text.strip()

