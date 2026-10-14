import os
from datetime import datetime
from pathlib import Path
from typing import Any

import pymupdf as fitz


PAGE_WIDTH = 595
PAGE_HEIGHT = 842
LEFT_MARGIN = 52
RIGHT_MARGIN = 52
TOP_MARGIN = 58
BOTTOM_MARGIN = 54


def _font_path() -> Path | None:
    windows_fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    candidates = (
        windows_fonts / "Nirmala.ttc",
        windows_fonts / "arial.ttf",
        windows_fonts / "segoeui.ttf",
        windows_fonts / "arialuni.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),
        Path("/usr/share/fonts/truetype/freefont/FreeSans.ttf"),
    )
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def _report_lines(report: dict[str, Any], completed_at: datetime) -> list[tuple[str, float]]:
    lines: list[tuple[str, float]] = [
        ("DOCTOR-READY SYMPTOM SUMMARY", 18),
        (f"Prepared: {completed_at.strftime('%d %b %Y')}", 10),
        ("", 8),
        ("PATIENT", 13),
    ]

    patient = report.get("patient") or {}
    for label, key in (
        ("Name", "name"),
        ("Age", "age"),
        ("Gender", "gender"),
        ("Medical conditions", "medical_condition"),
        ("Allergies", "allergy"),
    ):
        value = patient.get(key)
        if value not in (None, ""):
            lines.append((f"{label}: {value}", 10))

    lines.extend((("", 8), ("MAIN CONCERN", 13)))
    for label, key in (
        ("Chief complaint", "chief_complaint"),
        ("Patient description", "patient_description"),
        ("Additional information", "additional_information"),
    ):
        value = report.get(key)
        if value not in (None, ""):
            lines.append((f"{label}: {value}", 10))

    symptoms = report.get("symptom_details") or []
    lines.extend((("", 8), ("REPORTED SYMPTOMS", 13)))
    if not symptoms:
        lines.append(("No structured symptom details were recorded.", 10))

    symptom_fields = (
        ("Location", "location"),
        ("Onset", "onset"),
        ("Duration", "duration"),
        ("Severity", "severity"),
        ("Character", "character"),
        ("Frequency", "frequency"),
        ("Aggravating factors", "aggravating_factors"),
        ("Relieving factors", "relieving_factors"),
        ("Associated symptoms", "associated_symptoms"),
        ("Symptoms explicitly denied", "negative_symptoms"),
    )
    for index, symptom in enumerate(symptoms, start=1):
        lines.extend((
            ("", 6),
            (f"Symptom {index}: {symptom.get('symptom') or 'Not specified'}", 11),
        ))
        for label, key in symptom_fields:
            value = symptom.get(key)
            if isinstance(value, list):
                value = ", ".join(str(item) for item in value)
            if value not in (None, ""):
                lines.append((f"{label}: {value}", 10))

    lines.extend((
        ("", 10),
        (
            "This summary records patient-reported information. It is not a "
            "diagnosis or a substitute for clinical assessment.",
            9,
        ),
    ))
    return lines


def create_patient_summary_pdf(
    report: dict[str, Any],
    completed_at: datetime,
) -> bytes:
    font_path = _font_path()
    font = fitz.Font(fontfile=str(font_path)) if font_path else fitz.Font("helv")
    lines = _report_lines(report, completed_at)

    if any(ord(character) > 255 for text, _ in lines for character in text):
        raise ValueError(
            "This report contains non-Latin text. Use the browser print dialog "
            "to save it as a PDF without losing characters."
        )

    unsupported = {
        character
        for text, _ in lines
        for character in text
        if not character.isspace() and not font.has_glyph(ord(character))
    }
    if unsupported:
        raise ValueError(
            "The available PDF font cannot render all characters in this report."
        )

    document = fitz.open()
    font_name = "SummaryFont" if font_path else "helv"
    body_color = (0.16, 0.22, 0.32)

    def create_page():
        new_page = document.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        if font_path:
            new_page.insert_font(
                fontname=font_name,
                fontfile=str(font_path),
            )
        return new_page

    page = create_page()
    page_number = 1
    y = TOP_MARGIN

    def new_page():
        nonlocal page, page_number, y
        page_number += 1
        page = create_page()
        y = TOP_MARGIN

    def draw_line(text: str, font_size: float):
        nonlocal y
        if not text:
            y += font_size
            return

        max_width = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN
        words = text.split()
        wrapped: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if current and font.text_length(candidate, fontsize=font_size) > max_width:
                wrapped.append(current)
                current = word
            else:
                current = candidate
        if current:
            wrapped.append(current)

        line_height = font_size * 1.5
        for wrapped_line in wrapped:
            if y + line_height > PAGE_HEIGHT - BOTTOM_MARGIN:
                new_page()
            page.insert_text(
                (LEFT_MARGIN, y + font_size),
                wrapped_line,
                fontname=font_name,
                fontsize=font_size,
                color=body_color,
            )
            y += line_height

    for text, size in lines:
        draw_line(text, size)

    for index, page in enumerate(document, start=1):
        page.insert_text(
            (PAGE_WIDTH - RIGHT_MARGIN - 45, PAGE_HEIGHT - 24),
            f"Page {index}",
            fontname="helv",
            fontsize=9,
            color=(0.4, 0.45, 0.53),
        )

    return document.tobytes()
