# services/active_medication.py

import calendar
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from models.active_med_model import ActiveMedication


def _prescription_datetime(value: str | None):
    if not value:
        return None

    date_text = value.strip()
    slash_date = re.fullmatch(
        r"(\d{1,2})/(\d{1,2})/(\d{2,4})",
        date_text,
    )
    if slash_date:
        first = int(slash_date.group(1))
        second = int(slash_date.group(2))
        if first <= 12 and second <= 12 and first != second:
            return None

    for date_format in (
        "%d-%m-%Y",
        "%d-%m-%y",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d/%m/%y",
        "%m/%d/%Y",
        "%m/%d/%y",
    ):
        try:
            parsed = datetime.strptime(date_text, date_format)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None


def prescription_end_date(
    start_date: datetime | None,
    duration: str | None
) -> datetime | None:
    if not start_date or not duration:
        return None

    match = re.fullmatch(
        r"\s*(?:for\s+)?(\d+)\s*(day|week|month|year)s?\s*",
        duration,
        flags=re.IGNORECASE,
    )
    if not match:
        return None

    quantity = int(match.group(1))
    if quantity <= 0:
        return None

    unit = match.group(2).lower()
    if unit == "day":
        return start_date + timedelta(days=quantity - 1)

    if unit == "week":
        return start_date + timedelta(days=(quantity * 7) - 1)

    month_offset = quantity * (12 if unit == "year" else 1)
    month_index = start_date.month - 1 + month_offset
    year = start_date.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start_date.day, calendar.monthrange(year, month)[1])

    return start_date.replace(year=year, month=month, day=day) - timedelta(days=1)


def add_active_medications(
    db: Session,
    patient_id,
    prescription,
    normalized_drugs,
    prescription_medicines=None
):

    prescription_date = _prescription_datetime(prescription.date)
    durations_by_name = {
        medicine.name.strip().casefold(): medicine.duration
        for medicine in (prescription_medicines or [])
        if medicine.name and medicine.duration
    }

    for drug in normalized_drugs:
        source_name = (drug.raw_name or "").strip().casefold()
        duration = durations_by_name.get(source_name)

        medication = ActiveMedication(
            patient_id=patient_id,
            prescription_id=prescription.prescription_id,
            name=drug.concept_name or drug.raw_name,
            rxcui=drug.rxcui,
            ingredients=drug.ingredients,
            status="ACTIVE",
            start_date=prescription_date,
            end_date=prescription_end_date(
                prescription_date,
                duration,
            )
        )

        db.add(medication)