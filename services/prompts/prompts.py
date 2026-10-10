PRESCRIPTION_TEXT_PROMPT = """
Extract the prescription from the supplied document text into the
PrescriptionData schema.

Rules:
- Extract every identifiable medicine and preserve the written medicine name.
- Correct minor spelling errors only when the intended name is clear.
- Keep dosage, frequency, duration, and instructions in their respective fields.
- Preserve patient, doctor, facility, and date details when present.
- Put other relevant prescription information in notes.
- Use null for missing optional values. Never guess illegible information.
- Return only the schema output.
"""

PRESCRIPTION_VISION_PROMPT = """
Extract all information from every supplied page/image into the
PrescriptionData schema. This may be handwritten or printed.

Rules:
- Extract every identifiable medicine from every page.
- Correct minor spelling errors only when the intended name is clear.
- Keep dosage, frequency, duration, and instructions in their respective fields.
- Preserve patient, doctor, facility, and date details when present.
- Put other relevant prescription information in notes.
- Use null for missing optional values. Mark illegible medicine information
  as unclear rather than guessing.
- Extracted text may repeat the rendered pages; do not duplicate a medicine
  or instruction that appears in both.
- Return only the schema output.
"""

LAB_REPORT_PROMPT = """
Extract lab report data from the supplied document text into the LabReportData
schema.

Extract every test and preserve the reported value, unit, and reference range.
Correct minor OCR/spelling errors only when the intended test name is clear.
Set flag from the reported value and reference range when supported; otherwise
use unknown. Use null for missing optional values. Never guess or medically
interpret missing information. Extracted text may repeat the rendered pages;
do not duplicate a result that appears in both. Return only the schema output.
"""

LAB_REPORT_VISION_PROMPT = """
Extract lab report data from every supplied page/image into the LabReportData
schema.

Extract every test and preserve the reported value, unit, and reference range.
Correct minor OCR/spelling errors only when the intended test name is clear.
Set flag from the reported value and reference range when supported; otherwise
use unknown. Use null for missing optional values. Never guess or medically
interpret missing information. Extracted text may repeat the rendered pages;
do not duplicate a result that appears in both. Return only the schema output.
"""

DOCUMENT_CLASSIFICATION_PROMPT = """
Read the complete supplied medical document and return the matching structured
data.

Set document_type to lab_report for a laboratory results/report document, or
prescription for a medication prescription. Populate only the matching
lab_report or prescription field and leave the other null. Extract all
information from all supplied pages/images. Preserve reported names, values,
units, ranges, dates, doses, and instructions. Do not guess missing or
illegible medical information. Extracted text may repeat the rendered pages;
do not duplicate a value that appears in both. Use null for optional unknown
values and "unclear" only when an individual value is visibly illegible.
Return only the requested structured output.
"""

DRUG_INTERACTION_PROMPT = """
You are a medical drug safety assistant. Check potential
interactions between two drugs using ONLY the retrieved
FDA label data from ChromaDB.

Drug A: {drug_a}
Drug B: {drug_b}

Retrieved FDA Data:
{retrieved_data}

Instructions:
1. Analyze both drugs' interaction, contraindication,
   and warning sections.
2. Identify documented interactions, their clinical
   effects, and relevant precautions.
3. Assign severity only when supported by the evidence.
4. Never invent information or assume missing evidence
   means the drugs are safe together.
5. If evidence is insufficient or no interaction is
   documented, clearly state this.
6. Provide a concise, accurate, patient-friendly response.

Return ONLY valid JSON:

{
    "drug_a": "",
    "drug_b": "",
    "interaction_found": false, # true if interaction is documented, false otherwise
    "severity": "unknown",  # severe, major, moderate, minor, or unknown
    "interaction_detail": "",
    "patient_message": ""
}

Rules:
- interaction_found: true or false.
- severity: contraindicated, major, moderate, minor,
  or unknown.
- interaction_detail: explain the documented interaction,
  clinical effects, and precautions based on retrieved data.
- If no interaction is documented, set interaction_found
  to false and severity to unknown.
- If evidence is insufficient, explicitly mention it.
- Do not claim the combination is safe based on missing data.
- Return valid JSON only, without Markdown.
"""

DRUG_DISEASE_PROMPT = """
You are a medical drug safety assistant. Analyze potential
drug-disease interactions using ONLY the FDA label data
retrieved from ChromaDB.

Drug: {drug_name}
Patient's Disease: {disease}
Retrieved FDA Data:
{retrieved_data}

Instructions:
1. Check contraindications, warnings, and precautions
   relevant to the patient's disease.
2. Identify documented risks, clinical effects, and
   precautions supported by the retrieved evidence.
3. Assign severity only when supported by the evidence.
4. Never invent information or assume missing evidence
   means the drug is safe for the disease.
5. If no interaction is documented, state this clearly.
   If evidence is insufficient, mention the limitation.
6. Provide a concise, accurate, patient-friendly response.

Return ONLY valid JSON:

{
    "drug_name": "",
    "disease": "",
    "interaction_found": false,
    "severity": "unknown",
    "interaction_detail": "",
    "patient_message": ""
}

Rules:
- interaction_found: true or false.
- severity: contraindicated, major, moderate, minor,
  or unknown.
- Base all findings strictly on retrieved FDA data.
- Do not diagnose or recommend changing medication.
- Return valid JSON only, without Markdown.
"""