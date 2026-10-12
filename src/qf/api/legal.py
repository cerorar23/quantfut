"""Public legal documents; available without an account or Firebase session."""
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(prefix="/legal", include_in_schema=False)
PAGES = Path(__file__).with_name("legal_pages")


def document(slug: str) -> FileResponse:
    return FileResponse(PAGES / f"{slug}.html", media_type="text/html",
                        headers={"Cache-Control": "public, max-age=300",
                                 "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"})


@router.get("/terminos")
def terms():
    return document("terminos")


@router.get("/privacidad")
def privacy():
    return document("privacidad")


@router.get("/eliminar-cuenta")
def deletion():
    return document("eliminar-cuenta")
