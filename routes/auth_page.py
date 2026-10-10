from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates


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
        context={}
    )