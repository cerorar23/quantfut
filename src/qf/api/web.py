"""Entrega de la maqueta pública desde el mismo proceso FastAPI.

Se exponen archivos concretos: no se publica README, package.json ni el
servidor de desarrollo de frontend/.
"""
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from fastapi import Response


router = APIRouter(include_in_schema=False)
FRONTEND_DIR = Path(__file__).resolve().parents[3] / "frontend"
IMAGES_DIR = FRONTEND_DIR / "imagenes"
_IMAGE_FOLDERS = {"nba", "tenis", "futbol"}
_IMAGE_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,79}\.(png|jpg)$", re.IGNORECASE)
_IMAGE_TYPES = {"png": "image/png", "jpg": "image/jpeg"}


@router.get("/web/deportes/tenis")
def tennis_forecasts(response: Response):
    from .tenis_publico import public_data
    response.headers["Cache-Control"] = "no-store"
    return public_data()


@router.get("/web/deportes/tenis/cuotas")
def tennis_quotes(response: Response):
    from .cuotas_web import tennis_response
    response.headers["Cache-Control"] = "no-store"
    return tennis_response()


@router.get("/web/deportes/nba/cuotas")
def nba_quotes(response: Response):
    from .cuotas_web import nba_response
    response.headers["Cache-Control"] = "no-store"
    return nba_response()


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


@router.get("/sport-images.js")
def sport_images_script() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "sport-images.js", media_type="text/javascript")


@router.get("/sport-images.css")
def sport_images_styles() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "sport-images.css", media_type="text/css")


@router.get("/web/imagenes/jugadores/{sport}/{player_id}.{extension}")
def player_portrait(sport: str, player_id: str, extension: str):
    from .imagenes import cached_portrait, EXTENSIONS
    from ..config import settings
    if EXTENSIONS.get(sport) != extension:
        raise HTTPException(404, "Foto no disponible", headers={"Cache-Control": "no-store"})
    path = cached_portrait(sport, player_id, Path(settings.artifact_dir) / "public-images" / "jugadores")
    if path is None:
        raise HTTPException(404, "Foto no disponible", headers={"Cache-Control": "no-store"})
    return FileResponse(path, media_type="image/" + extension, headers={"Cache-Control": "public, max-age=86400"})


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


@router.get("/conversion.css")
def conversion_styles() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "conversion.css", media_type="text/css")


@router.get("/conversion-views.js")
def conversion_views_script() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "conversion-views.js", media_type="text/javascript")


@router.get("/historial-views.js")
def historial_views_script() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "historial-views.js", media_type="text/javascript")


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


# Logos NBA y fotos de tenis, descargados una vez a `frontend/imagenes/` (scripts/imagenes/): la web
# no enlaza a dominios externos. Las rutas fijas van antes que la de archivos.
@router.get("/web/imagenes/manifiesto.json")
def images_manifest() -> FileResponse:
    return FileResponse(IMAGES_DIR / "manifiesto.json", media_type="application/json",
                        headers={"Cache-Control": "public, max-age=300"})


@router.get("/web/imagenes/creditos")
def images_credits() -> FileResponse:
    return FileResponse(IMAGES_DIR / "creditos.html", media_type="text/html",
                        headers={"Cache-Control": "public, max-age=300",
                                 "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"})


@router.get("/web/imagenes/{carpeta}/{archivo}")
def image_file(carpeta: str, archivo: str) -> FileResponse:
    if carpeta not in _IMAGE_FOLDERS or not _IMAGE_NAME.match(archivo):
        raise HTTPException(404, "Sin imagen")
    ruta = IMAGES_DIR / carpeta / archivo
    if not ruta.is_file():
        raise HTTPException(404, "Sin imagen")
    return FileResponse(ruta, media_type=_IMAGE_TYPES[archivo.rsplit(".", 1)[1].lower()],
                        headers={"Cache-Control": "public, max-age=86400"})
