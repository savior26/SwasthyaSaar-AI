

PRESCRIPTION_TEXT_PROMPT = """
Extract the prescription from the supplied document text into the PrescriptionData schema.

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
Extract all information from every supplied page/image into the PrescriptionData schema. This may be handwritten or printed.

Rules:
- Extract every identifiable medicine from every page.
- Correct minor spelling errors only when the intended name is clear.
- Keep dosage, frequency, duration, and instructions in their respective fields.
- Preserve patient, doctor, facility, and date details when present.
- Put other relevant prescription information in notes.
- Use null for missing optional values. Mark illegible medicine information as unclear rather than guessing.
- Extracted text may repeat the rendered pages; do not duplicate a medicine or instruction that appears in both.
- Return only the schema output.
"""

LAB_REPORT_TEXT_PROMPT = """
Extract all laboratory test results and patient metadata from the supplied document text into the LabReportData schema.

Rules:
- Extract every lab test name, observed value, unit, and reference range accurately.
- Classify test status flags as 'normal', 'high', 'low', 'abnormal', or 'unknown'.
- Preserve patient, lab facility, and test date details when present.
- Use null for missing optional values.
"""

LAB_REPORT_VISION_PROMPT = """
Examine all supplied document pages/images and extract laboratory test details into the LabReportData schema.

Rules:
- Extract all test parameters across every provided page.
- Accurately parse numeric values, units, reference intervals, and flags.
- Do not duplicate tests across pages.
- Use null for missing optional values.
"""
