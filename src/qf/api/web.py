"""Entrega de la maqueta pública desde el mismo proceso FastAPI.

Se exponen archivos concretos: no se publica README, package.json ni el
servidor de desarrollo de frontend/.
"""
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse


router = APIRouter(include_in_schema=False)
FRONTEND_DIR = Path(__file__).resolve().parents[3] / "frontend"


@router.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@router.get("/styles.css")
def styles() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "styles.css", media_type="text/css")


@router.get("/future.css")
def future_styles() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "future.css", media_type="text/css")


@router.get("/vendor/cybercore/cybercore.min.css")
def cybercore_styles() -> FileResponse:
    return FileResponse(
        FRONTEND_DIR / "vendor" / "cybercore" / "cybercore.min.css",
        media_type="text/css",
    )


@router.get("/app.js")
def script() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "app.js", media_type="text/javascript")


@router.get("/public-data.js")
def public_data_script() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "public-data.js", media_type="text/javascript")


@router.get("/fichas-data.js")
def fichas_data_script() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "fichas-data.js", media_type="text/javascript")


@router.get("/membership.js")
def membership_script() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "membership.js", media_type="text/javascript")


@router.get("/cuenta-api.js")
def cuenta_api_script() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "cuenta-api.js", media_type="text/javascript")


@router.get("/membership.css")
def membership_styles() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "membership.css", media_type="text/css")


@router.get("/google-auth.js")
def google_auth_script() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "google-auth.js", media_type="text/javascript")


@router.get("/meta-pixel.js")
def meta_pixel_script() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "meta-pixel.js", media_type="text/javascript")


@router.get("/whop-checkout.js")
def whop_checkout_script() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "whop-checkout.js", media_type="text/javascript")
