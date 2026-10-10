from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

from database import get_db
from routes.auth import get_current_user
from models.user_model import User
from models.doc_model import MedicalDocument, LabReport, LabTest
from schemas.lab_schema import TestGraphResponse, TestGraphPoint
from services.alerts import generate_lab_report_alerts

router = APIRouter(
    prefix="/lab-tests",
    tags=["Lab Tests"]
)


@router.get(
    "/reports",
    status_code=status.HTTP_200_OK
)
def get_lab_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rows = (
        db.query(MedicalDocument, LabReport, LabTest)
        .join(
            LabReport,
            MedicalDocument.doc_id == LabReport.doc_id
        )
        .outerjoin(
            LabTest,
            LabReport.lab_report_id == LabTest.lab_report_id
        )
        .filter(
            MedicalDocument.patient_id == current_user.id
        )
        .order_by(MedicalDocument.uploaded_at.desc())
        .all()
    )

    reports = {}
    for document, report, test in rows:
        item = reports.setdefault(
            str(document.doc_id),
            {
                "doc_id": str(document.doc_id),
                "original_filename": document.original_filename,
                "status": document.status,
                "uploaded_at": document.uploaded_at,
                "lab_name": report.lab_name,
                "date": report.date,
                "patient_name": report.patient_name,
                "tests": [],
            },
        )
        if test:
            item["tests"].append(
                {
                    "test_name": test.test_name,
                    "value": test.value,
                    "unit": test.unit,
                    "reference_range": test.reference_range,
                    "flag": test.flag,
                }
            )

    return list(reports.values())


def parse_numeric_value(value: str | None):
    if not value:
        return None

    try:
        return float(value.strip())
    except (ValueError, TypeError):
        return None


def lab_date_sort_key(value: str | None):
    if not value:
        return datetime.max

    for date_format in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value.strip(), date_format)
        except ValueError:
            continue

    return datetime.max


@router.get(
    "/alerts",
    status_code=status.HTTP_200_OK
)
def get_lab_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rows = (
        db.query(MedicalDocument, LabReport, LabTest)
        .join(
            LabReport,
            MedicalDocument.doc_id == LabReport.doc_id
        )
        .join(
            LabTest,
            LabReport.lab_report_id == LabTest.lab_report_id
        )
        .filter(
            MedicalDocument.patient_id == current_user.id,
            LabTest.flag.in_(("high", "low", "abnormal"))
        )
        .order_by(MedicalDocument.uploaded_at.desc())
        .all()
    )

    alerts = []
    for document, report, test in rows:
        report_alerts = generate_lab_report_alerts({
            "date": report.date,
            "tests": [{
                "test_name": test.test_name,
                "value": test.value,
                "unit": test.unit,
                "reference_range": test.reference_range,
                "flag": test.flag,
            }],
        })
        for alert in report_alerts:
            alert["date"] = report.date or ""
            alert["document_name"] = document.original_filename
            alerts.append(alert)

    return alerts


@router.get(
    "/dashboard",
    response_model=list[TestGraphResponse],
    status_code=status.HTTP_200_OK
)
def get_lab_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    tests = (
        db.query(
            LabTest.test_name,
            LabTest.value,
            LabTest.unit,
            LabTest.flag,
            LabReport.date
        )
        .join(
            LabReport,
            LabTest.lab_report_id == LabReport.lab_report_id
        )
        .join(
            MedicalDocument,
            LabReport.doc_id == MedicalDocument.doc_id
        )
        .filter(
            MedicalDocument.patient_id == current_user.id
        )
        .order_by(MedicalDocument.uploaded_at.asc())
        .all()
    )

    grouped_tests = {}

    for test in tests:

        if not test.test_name:
            continue

        numeric_value = parse_numeric_value(test.value)

        # Skip values such as Positive, Negative, <5, etc.
        if numeric_value is None:
            continue

        test_name = test.test_name.strip()

        if test_name not in grouped_tests:
            grouped_tests[test_name] = {
                "test_name": test_name,
                "unit": test.unit,
                "data": []
            }

        grouped_tests[test_name]["data"].append(
            TestGraphPoint(
                date=test.date,
                value=numeric_value,
                unit=test.unit,
                flag=test.flag
            )
        )

    for test in grouped_tests.values():
        test["data"].sort(key=lambda point: lab_date_sort_key(point.date))

    return list(grouped_tests.values())