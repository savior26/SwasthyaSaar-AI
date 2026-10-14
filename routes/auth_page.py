from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from utils.medical_conditions import MEDICAL_CONDITION_GROUPS


router = APIRouter(
    tags=["Authentication UI"]
)


BASE_DIR = Path(__file__).resolve().parent.parent


templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates")
)


@router.get("/login")
def login_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="auth.html",
        context={
            "medical_condition_groups": MEDICAL_CONDITION_GROUPS,
        }
    )