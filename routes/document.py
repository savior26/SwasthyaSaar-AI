import logging
import os
from threading import Lock
from models.doc_model import MedicalDocument,LabReport,LabTest, Prescription,PrescriptionMedicine
from models.user_model import User
from models.model import ActiveMedication, SafetyCheck, SafetyConflict
from fastapi import APIRouter, Form, status, Depends, HTTPException, UploadFile, File, BackgroundTasks, Response
from database import SessionLocal, get_db
from sqlalchemy.orm import Session
from typing import Literal
from orchestrator.document_parsing import DocumentPipeline
from orchestrator.safety_pipeline import safety_pipeline
from schemas.doc_schema import LabReportData, PrescriptionData
from utils.data_parsing.parse2text import lab_report_to_text, prescription_to_text
from utils.data_parsing.validation import validate_file
import tempfile
from pathlib import Path
from routes.auth import get_current_user
from datetime import datetime , timezone
from uuid import UUID

router= APIRouter(
    prefix="/doc",
    tags=['doc']
)

logger = logging.getLogger(__name__)
document_parser_lock = Lock()

DOCUMENT_STAGE_MESSAGES = {
    "queued": "Upload received. Waiting to start processing.",
    "parsing": "Extracting information from your document.",
    "saving_results": "Saving the parsed document details.",
    "checking_lab_results": "Reviewing lab values for reported high, low, or abnormal flags.",
    "checking_medication_safety": "Checking the prescription against available medication safety data.",
    "complete": "Document processing is complete.",
    "failed": "Document processing failed. Check that the file is readable and supported, then try again.",
    "failed_parsing": (
        "Document parsing failed. Check that the image or PDF is readable; "
        "the server log contains the diagnostic error."
    ),
    "failed_saving_results": (
        "The document was read, but its parsed results could not be saved. "
        "The server log contains the diagnostic error."
    ),
    "safety_check_failed": (
        "The document was parsed, but medication safety screening did not finish. "
        "This is not an all-clear; ask a clinician or pharmacist to review it."
    ),
    "post_parse_failed": (
        "The lab report was parsed, but result review did not finish. "
        "Review the original report with a clinician."
    ),
}


def document_processing_message(document: MedicalDocument) -> str:
    return DOCUMENT_STAGE_MESSAGES.get(
        document.processing_stage or "",
        "Document received.",
    )


def document_review_summary(db: Session, document: MedicalDocument) -> str | None:
    if document.status != "parsed" or document.processing_stage not in {
        None,
        "complete",
        "safety_check_failed",
        "post_parse_failed",
    }:
        return None

    if document.document_type == "lab_report" and document.lab_report:
        tests = document.lab_report.tests
        flagged_count = sum(
            (test.flag or "").lower() in {"high", "low", "abnormal"}
            for test in tests
        )
        if flagged_count:
            return (
                f"{flagged_count} of {len(tests)} parsed lab result(s) "
                "were flagged high, low, or abnormal for clinician review."
            )
        if tests:
            return (
                f"No high, low, or abnormal flags were reported among "
                f"{len(tests)} parsed lab result(s). Unclassified results "
                "may not have been assessed."
            )
        return "No lab values were extracted from this report."

    if document.document_type == "prescription":
        safety_check = (
            db.query(SafetyCheck)
            .filter(SafetyCheck.doc_id == document.doc_id)
            .order_by(SafetyCheck.created_at.desc())
            .first()
        )
        if safety_check is None:
            return document_processing_message(document)
        finding_count = len(safety_check.conflicts)
        if safety_check.patient_alert_message and safety_check.patient_alert_message.startswith(
            "Assessment incomplete:"
        ):
            return (
                "Medication safety screening is incomplete. "
                "No complete safety conclusion can be drawn."
            )
        if finding_count:
            return (
                f"{finding_count} potential medication safety finding(s) "
                "were recorded for clinician or pharmacist review."
            )
        return (
            "No conflict was detected by the available safety checks; "
            "this does not prove the prescription is safe."
        )

    return document_processing_message(document)


def _set_document_stage(
    db: Session,
    doc_id,
    stage: str,
    *,
    status_value: str | None = None,
    error_message: str | None = None,
) -> MedicalDocument:
    document = (
        db.query(MedicalDocument)
        .filter(MedicalDocument.doc_id == doc_id)
        .first()
    )
    if document is None:
        raise LookupError("The uploaded document record no longer exists.")

    document.processing_stage = stage
    if status_value is not None:
        document.status = status_value
    document.error_message = error_message
    db.commit()
    return document


def _split_profile_values(value: str | None) -> list[str]:
    if not value:
        return []

    return [
        item.strip()
        for line in value.splitlines()
        for item in line.replace(";", ",").split(",")
        if item.strip()
    ]


def process_uploaded_document(
    doc_id,
    patient_id,
    doc_type: Literal["PRESCRIPTION", "LAB_REPORT"],
    filename: str,
    contents: bytes,
) -> None:
    db = SessionLocal()
    temp_path = None
    current_stage = "parsing"
    try:
        _set_document_stage(db, doc_id, current_stage)
        suffix = Path(filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(contents)
            temp_path = tmp.name

        with document_parser_lock:
            result = DocumentPipeline.process_document(temp_path, doc_type)
        current_stage = "saving_results"
        _set_document_stage(db, doc_id, current_stage)

        document = (
            db.query(MedicalDocument)
            .filter(MedicalDocument.doc_id == doc_id)
            .first()
        )
        if document is None:
            raise LookupError("The uploaded document record no longer exists.")

        if doc_type == "LAB_REPORT":
            if not isinstance(result, LabReportData):
                raise ValueError("Parser returned invalid lab report data.")

            lab_report = LabReport(
                doc_id=document.doc_id,
                lab_name=result.lab_name,
                date=result.date,
                patient_name=result.patient_name,
            )
            db.add(lab_report)
            db.flush()
            for test in result.tests:
                db.add(LabTest(
                    lab_report_id=lab_report.lab_report_id,
                    test_name=test.test_name,
                    value=test.value,
                    unit=test.unit,
                    reference_range=test.reference_range,
                    flag=test.flag or "unknown",
                ))

            current_stage = "checking_lab_results"
            document.processing_stage = current_stage
            document.parsed_at = datetime.now(timezone.utc)
            db.commit()
        else:
            if not isinstance(result, PrescriptionData):
                raise ValueError("Parser returned invalid prescription data.")

            prescription = Prescription(
                doc_id=document.doc_id,
                doctor_name=result.doctor_name,
                hospital_name=result.hospital_name,
                date=result.date,
                patient_name=result.patient_name,
                notes=result.notes,
            )
            db.add(prescription)
            db.flush()
            for medicine in result.medicines:
                db.add(PrescriptionMedicine(
                    prescription_id=prescription.prescription_id,
                    name=medicine.name,
                    dosage=medicine.dosage,
                    frequency=medicine.frequency,
                    duration=medicine.duration,
                    instructions=medicine.instructions,
                ))

            current_stage = "checking_medication_safety"
            document.parsed_at = datetime.now(timezone.utc)
            document.processing_stage = current_stage
            db.commit()

            patient = (
                db.query(User)
                .filter(User.id == patient_id)
                .first()
            )
            if patient is None:
                raise LookupError("The patient for this document no longer exists.")

            safety_result = safety_pipeline.run_pipeline({
                "drugs": [medicine.name for medicine in result.medicines],
                "diseases": _split_profile_values(patient.medical_condition),
                "allergies": _split_profile_values(patient.allergy),
            })
            print("drugs", [medicine.name for medicine in result.medicines],
                "diseases", _split_profile_values(patient.medical_condition),
                "allergies", _split_profile_values(patient.allergy))
            print(safety_result)
            alerts = safety_result["alerts"]
            failed_checks = [
                alert for alert in alerts
                if alert.get("type") == "Error"
            ]
            conflicts = [
                alert for alert in alerts
                if alert.get("type") != "Error"
            ]
            has_critical_issue = any(
                str(alert.get("severity", "")).strip().lower()
                in {"high", "critical", "severe", "contraindicated"}
                for alert in conflicts
            )

            safety_check = SafetyCheck(
                patient_id=patient_id,
                doc_id=document.doc_id,
                has_critical_issue=has_critical_issue,
                patient_alert_message=(
                    "Assessment incomplete: One or more medication safety checks failed."
                    if failed_checks
                    else "Potential medication safety findings were detected. Please consult a clinician or pharmacist."
                    if conflicts
                    else "No potential medication safety conflicts were detected by the available checks."
                ),
                doctor_clinical_note=(
                    f"Pipeline status: {safety_result['prescription_status']}. "
                    f"Potential findings: {len(conflicts)}. "
                    f"Failed checks: {len(failed_checks)}."
                ),
                action_required=(
                    "Have a clinician or pharmacist review the prescription and patient profile."
                    if failed_checks or conflicts
                    else "No additional review was indicated by the available checks."
                ),
                language="en",
            )
            db.add(safety_check)
            db.flush()

            for alert in conflicts:
                db.add(SafetyConflict(
                    safety_check_id=safety_check.safety_check_id,
                    conflict_type=str(alert.get("type") or "Medication Safety Finding"),
                    severity=str(alert.get("severity") or "REVIEW"),
                    description=alert.get("description"),
                ))

            normalization_details = safety_result["normalization_details"]
            for medicine in result.medicines:
                normalization = normalization_details.get(medicine.name, {})
                db.add(ActiveMedication(
                    patient_id=patient_id,
                    prescription_id=prescription.prescription_id,
                    name=normalization.get("corrected_name") or medicine.name,
                    rxcui=normalization.get("rxcui"),
                ))

            db.commit()

        _set_document_stage(
            db,
            doc_id,
            "complete",
            status_value="parsed",
        )
    except Exception:
        db.rollback()
        document = (
            db.query(MedicalDocument)
            .filter(MedicalDocument.doc_id == doc_id)
            .first()
        )
        if document is not None:
            parsed = document.parsed_at is not None
            failure_stage = "failed"
            if parsed and doc_type == "PRESCRIPTION":
                failure_stage = "safety_check_failed"
            elif parsed:
                failure_stage = "post_parse_failed"
            elif current_stage == "saving_results":
                failure_stage = "failed_saving_results"
            elif current_stage == "parsing":
                failure_stage = "failed_parsing"
            document.processing_stage = failure_stage
            document.status = "parsed" if parsed else "failed"
            document.error_message = (
                "Medication safety screening was not completed."
                if failure_stage == "safety_check_failed"
                else "Document parsing did not complete."
            )
            if failure_stage == "post_parse_failed":
                document.error_message = "Lab result review was not completed."
            db.commit()
        logger.exception(
            "Document processing failed at stage %s (document id %s).",
            current_stage,
            doc_id,
        )
    finally:
        try:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
        except OSError:
            logger.warning("Could not remove the temporary upload file.")
        finally:
            db.close()


def format_parsed_document(document_type: str, parsed_data) -> str | None:
    if document_type == "lab_report" and parsed_data is not None:
        return lab_report_to_text(
            LabReportData.model_validate(parsed_data)
        )

    if document_type == "prescription" and parsed_data is not None:
        return prescription_to_text(
            PrescriptionData.model_validate(parsed_data)
        )

    return None


@router.get("/")
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    documents = (
        db.query(MedicalDocument)
        .filter(MedicalDocument.patient_id == current_user.id)
        .order_by(MedicalDocument.uploaded_at.desc())
        .all()
    )

    result = []
    for document in documents:
        result.append({
            "doc_id": str(document.doc_id),
            "original_filename": document.original_filename,
            "document_type": document.document_type,
            "status": document.status,
            "processing_stage": document.processing_stage,
            "processing_message": document_processing_message(document),
            "review_summary": document_review_summary(db, document),
            "uploaded_at": document.uploaded_at,
            "parsed_at": document.parsed_at,
        })
    return result


@router.get("/{doc_id}")
def get_document(
    doc_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    document = (
        db.query(MedicalDocument)
        .filter(
            MedicalDocument.doc_id == doc_id,
            MedicalDocument.patient_id == current_user.id,
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    result = {
        "doc_id": str(document.doc_id),
        "original_filename": document.original_filename,
        "document_type": document.document_type,
        "status": document.status,
        "processing_stage": document.processing_stage,
        "processing_message": document_processing_message(document),
        "uploaded_at": document.uploaded_at,
        "parsed_at": document.parsed_at,
    }

    if document.lab_report:
        parsed_data = {
            "lab_name": document.lab_report.lab_name,
            "date": document.lab_report.date,
            "patient_name": document.lab_report.patient_name,
            "tests": [
                {
                    "test_name": test.test_name,
                    "value": test.value,
                    "unit": test.unit,
                    "reference_range": test.reference_range,
                    "flag": test.flag,
                }
                for test in document.lab_report.tests
            ],
        }
        result["lab_report"] = parsed_data
        result["parsed_text"] = format_parsed_document(
            document.document_type,
            parsed_data,
        )
        flagged_tests = [
            test for test in document.lab_report.tests
            if (test.flag or "").lower() in {"high", "low", "abnormal"}
        ]
        result["lab_assessment"] = {
            "status": (
                "flagged_results"
                if flagged_tests
                else "no_flags_reported"
                if document.lab_report.tests
                else "no_results_parsed"
            ),
            "test_count": len(document.lab_report.tests),
            "flagged_count": len(flagged_tests),
        }

    if document.prescription:
        parsed_data = {
            "doctor_name": document.prescription.doctor_name,
            "hospital_name": document.prescription.hospital_name,
            "date": document.prescription.date,
            "patient_name": document.prescription.patient_name,
            "notes": document.prescription.notes,
            "medicines": [
                {
                    "name": medicine.name,
                    "dosage": medicine.dosage,
                    "frequency": medicine.frequency,
                    "duration": medicine.duration,
                    "instructions": medicine.instructions,
                }
                for medicine in document.prescription.medicines
            ],
        }
        result["prescription"] = parsed_data
        result["parsed_text"] = format_parsed_document(
            document.document_type,
            parsed_data,
        )
        safety_check = (
            db.query(SafetyCheck)
            .filter(SafetyCheck.doc_id == document.doc_id)
            .order_by(SafetyCheck.created_at.desc())
            .first()
        )
        if safety_check is not None:
            finding_count = len(safety_check.conflicts)
            incomplete = bool(
                safety_check.patient_alert_message
                and safety_check.patient_alert_message.startswith(
                    "Assessment incomplete:"
                )
            )
            result["safety_assessment"] = {
                "status": (
                    "incomplete"
                    if incomplete
                    else "findings_detected"
                    if finding_count
                    else "no_conflicts_detected"
                ),
                "finding_count": finding_count,
                "has_critical_issue": safety_check.has_critical_issue,
                "message": safety_check.patient_alert_message,
                "action_required": safety_check.action_required,
            }
        elif document.processing_stage == "safety_check_failed":
            result["safety_assessment"] = {
                "status": "screening_failed",
                "finding_count": 0,
                "has_critical_issue": False,
                "message": document_processing_message(document),
                "action_required": (
                    "Have a qualified clinician or pharmacist review the prescription."
                ),
            }
        else:
            result["safety_assessment"] = {
                "status": "pending",
                "finding_count": 0,
                "has_critical_issue": False,
                "message": "Medication safety screening has not completed.",
                "action_required": None,
            }

    return result


@router.delete(
    "/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_document(
    doc_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = (
        db.query(MedicalDocument)
        .filter(
            MedicalDocument.doc_id == doc_id,
            MedicalDocument.patient_id == current_user.id,
        )
        .first()
    )
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )
    if document.status == "processing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Wait for document processing to finish before deleting it.",
        )

    try:
        prescription_id = (
            document.prescription.prescription_id
            if document.prescription is not None
            else None
        )
        if prescription_id is not None:
            db.query(ActiveMedication).filter(
                ActiveMedication.patient_id == current_user.id,
                ActiveMedication.prescription_id == prescription_id,
            ).delete(synchronize_session=False)

        db.delete(document)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception(
            "Could not delete medical document %s for patient %s.",
            doc_id,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The document could not be deleted. Please try again.",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    '/doc_parse',
    status_code=status.HTTP_202_ACCEPTED,
)
async def parseDoc(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    doc_type: Literal["PRESCRIPTION", "LAB_REPORT"] = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    
    try:
        if not file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file uploaded.",
            )

        validate_file(file)

        # =====================================================
        # 2. Convert API document type to DB document type
        # =====================================================

        if doc_type == "LAB_REPORT":
            document_type = "lab_report"
        else:
            document_type = "prescription"

        contents = await file.read()
        if len(contents) > 10 * 1024 * 1024:
            raise ValueError("File too large. Maximum allowed size is 10 MB.")

        medical_document = MedicalDocument(
            patient_id=current_user.id,
            document_type=document_type,
            original_filename=file.filename or "unknown",
            status="processing",
            processing_stage="queued",
        )
        db.add(medical_document)
        db.commit()
        db.refresh(medical_document)
        background_tasks.add_task(
            process_uploaded_document,
            medical_document.doc_id,
            current_user.id,
            doc_type,
            file.filename or "unknown",
            contents,
        )
        return {
            "document_id": str(medical_document.doc_id),
            "doc_id": str(medical_document.doc_id),
            "status": medical_document.status,
            "processing_stage": medical_document.processing_stage,
            "processing_message": document_processing_message(medical_document),
            "message": "Upload received. Document processing has started.",
        }
    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.error(
            "Document upload could not be accepted (%s).",
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The upload could not be accepted. Please try again."
        )