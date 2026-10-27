"""Entrega de la maqueta pública desde el mismo proceso FastAPI.

Se exponen archivos concretos: no se publica README, package.json ni el
servidor de desarrollo de frontend/.
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from fastapi import Response


router = APIRouter(include_in_schema=False)
FRONTEND_DIR = Path(__file__).resolve().parents[3] / "frontend"


@router.get("/web/deportes/tenis")
def tennis_forecasts(response: Response):
    from .tenis_publico import public_data
    response.headers["Cache-Control"] = "no-store"
    return public_data()


@router.get("/web/deportes/tenis/estadisticas/{event_id}")
def tennis_event_stats(event_id: str, response: Response):
    from .tenis_estadisticas import public_event
    response.headers["Cache-Control"] = "no-store"
    data = public_event(event_id) if event_id.isdigit() and len(event_id) <= 12 else None
    if data is None:
        raise HTTPException(404, "Sin estadísticas para este partido")
    return data


@router.get("/web/deportes/nba/estadisticas/{event_id}")
def nba_event_stats(event_id: str, response: Response):
    from .nba_estadisticas import public_event
    response.headers["Cache-Control"] = "no-store"
    data = public_event(event_id) if event_id.isdigit() and len(event_id) == 10 else None
    if data is None:
        raise HTTPException(404, "Sin estadísticas para este partido")
    return data


@router.get("/sports-data.js")
def sports_script() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "sports-data.js", media_type="text/javascript")


@router.get("/sports-window.js")
def sports_window_script() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "sports-window.js", media_type="text/javascript")


@router.get("/ergonomic-views.js")
def ergonomic_script() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "ergonomic-views.js", media_type="text/javascript")


@router.get("/real-views.js")
def real_views_script() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "real-views.js", media_type="text/javascript")


@router.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html", headers={"Cache-Control": "no-cache, must-revalidate"})


@router.get("/styles.css")
def styles() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "styles.css", media_type="text/css")


@router.get("/future.css")
def future_styles() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "future.css", media_type="text/css")


@router.get("/window.css")
def window_styles() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "window.css", media_type="text/css")


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
