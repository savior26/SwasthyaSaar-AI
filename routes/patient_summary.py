from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi import Body, Query
from sqlalchemy.orm import Session

from database import get_db
from models.user_model import User
from routes.auth import get_current_user

from schemas.patient_summary_schema import (
    PatientSummaryAnswerRequest,
    PatientSummaryReportRecord,
    PatientSummaryResponse,
)
from utils.symptom_summary.summary_agent_runtime import (
    PatientSummarySessionNotFound,
    get_completed_report,
    get_interview_session,
    list_completed_reports,
    process_answer,
    start_interview,
)
from utils.symptom_summary.patient_summary_pdf import create_patient_summary_pdf


router = APIRouter(
    prefix="/patient-summary",
    tags=["Patient Summary"],
)


@router.get(
    "/reports",
    response_model=list[PatientSummaryReportRecord],
    status_code=status.HTTP_200_OK,
)
def get_patient_summary_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_completed_reports(db=db, patient=current_user)


@router.get(
    "/reports/{session_id}/pdf",
    status_code=status.HTTP_200_OK,
)
def download_patient_summary_pdf(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        report, completed_at = get_completed_report(
            db=db,
            patient=current_user,
            session_id=str(session_id),
        )
    except PatientSummarySessionNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    try:
        pdf = create_patient_summary_pdf(report, completed_at)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="symptom-summary-{session_id}.pdf"'
            ),
        },
    )


# ============================================================
# START PATIENT INTERVIEW
# ============================================================

@router.post(
    "/start",
    response_model=PatientSummaryResponse,
    status_code=status.HTTP_200_OK,
)
def start_patient_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Start a new patient symptom interview.

    The patient information is taken from the
    currently authenticated user's profile.
    """

    try:
        response = start_interview(
            db=db,
            patient=current_user,
        )

        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to start patient summary: {str(e)}",
        )


@router.get(
    "/session/{session_id}",
    response_model=PatientSummaryResponse,
    status_code=status.HTTP_200_OK,
)
def resume_patient_summary(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return get_interview_session(
            db=db,
            patient=current_user,
            session_id=str(session_id),
        )
    except PatientSummarySessionNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


# ============================================================
# SUBMIT PATIENT ANSWER
# ============================================================

@router.post(
    "/answer/{session_id}",
    response_model=PatientSummaryResponse,
    status_code=status.HTTP_200_OK,
)
def submit_patient_answer(
    session_id: UUID,
    answer: str | None = Query(default=None),
    request: PatientSummaryAnswerRequest | None = Body(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit the patient's answer for the current question.

    The session belongs to the currently authenticated user.
    """

    answer_text = request.answer if request else answer
    if not answer_text or not answer_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Answer cannot be empty.",
        )

    try:
        response = process_answer(
            db=db,
            patient=current_user,
            session_id=str(session_id),
            answer=answer_text.strip(),
        )

        return response

    except PatientSummarySessionNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to process answer: {str(e)}",
        )
