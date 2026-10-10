from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates


router = APIRouter(
    tags=["Dashboard UI"]
)


# =====================================================
# BASE DIRECTORY
# =====================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# =====================================================
# JINJA TEMPLATES
# =====================================================

templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates")
)


# =====================================================
# API ENDPOINT CONFIGURATION
# =====================================================

API_ENDPOINTS = {

    # -------------------------
    # User
    # -------------------------

    "profile": "/user/getUser",

    "profileUpdate": "/user/update",


    # -------------------------
    # Medication
    # -------------------------

    "medications": "/medicine/display",


    # -------------------------
    # Lab
    # -------------------------

    "labDashboard": "/lab-tests/dashboard",

    "labAlerts": "/lab-tests/alerts",


    # -------------------------
    # Safety
    # -------------------------

    "alerts": "/safety/alerts",


    # -------------------------
    # Documents
    # -------------------------

    "documents": "/doc/",

    "uploadDocument": "/doc/doc_parse",

    "documentDetail": "/doc/{doc_id}",

    "labReports": "/lab-tests/reports",

    "updatePassword": "/user/updatePassword",


    # -------------------------
    # Patient Summary
    # -------------------------

    "summaryStart": "/patient-summary/start",

    "summaryAnswer": "/patient-summary/answer/{session_id}",

    "summaryReports": "/patient-summary/reports",

    "summaryPdf": "/patient-summary/reports/{session_id}/pdf",
}

WORKSPACE_PAGES = {
    "profile": ("My profile", "profile"),
    "profile-edit": ("Update profile", "profile-edit"),
    "lab-reports": ("Lab reports", "lab-reports"),
    "medications": ("Medications", "medications"),
    "documents": ("Medical documents", "documents"),
    "symptom-summary": ("Symptom summary", "symptom-summary"),
    "safety-alerts": ("Safety alerts", "safety-alerts"),
}


def render_workspace(request: Request, page: str):
    title, key = WORKSPACE_PAGES[page]
    return templates.TemplateResponse(
        request=request,
        name="workspace.html",
        context={
            "title": title,
            "page": key,
            "api_base": "",
            "api_endpoints": API_ENDPOINTS,
        },
    )


# =====================================================
# DASHBOARD PAGE
# =====================================================

@router.get(
    "/",
    name="dashboard"
)
def dashboard(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "api_base": "",
            "api_endpoints": API_ENDPOINTS
        }
    )


@router.get("/profile", name="profile")
def profile_page(request: Request):
    return render_workspace(request, "profile")


@router.get("/profile/edit", name="profile-edit")
def profile_edit_page(request: Request):
    return render_workspace(request, "profile-edit")


@router.get("/lab-reports", name="lab-reports")
def lab_reports_page(request: Request):
    return render_workspace(request, "lab-reports")


@router.get("/medications", name="medications")
def medications_page(request: Request):
    return render_workspace(request, "medications")


@router.get("/documents", name="documents")
def documents_page(request: Request):
    return render_workspace(request, "documents")


@router.get("/symptom-summary", name="symptom-summary")
def symptom_summary_page(request: Request):
    return render_workspace(request, "symptom-summary")


@router.get("/safety-alerts", name="safety-alerts")
def safety_alerts_page(request: Request):
    return render_workspace(request, "safety-alerts")
