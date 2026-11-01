"""Add verified provider photos absent from the public web (2026-10-28).

IDs/URLs were matched against the exact public event's archived API-Tennis
fixture/profile, never by a fuzzy name search. Xinran Sun has no provider photo.
"""
from pathlib import Path
import json
import urllib.request

from descargar_imagenes import extension, guardar_manifiesto, leer_manifiesto, norm, slug

ROOT = Path(__file__).resolve().parents[2] / "frontend" / "imagenes"
TENNIS = {
    "Aoi Ito": "13618_a-ito.jpg",
    "Brandon Nakashima": "2838_b-nakashima.jpg",
    "Daniel Merida": "978_d-merida-aguilar.jpg",
    "Han Shi": "38097_h-shi.jpg",
    "Ignacio Buse": "9514_i-buse.jpg",
    "Janice Tjen": "28551_j-tjen.jpg",
    "Martin Landaluce": "39864_m-landaluce.jpg",
    "Matteo Berrettini": "2844_m-berrettini.jpg",
    "Mia Pohankova": "61034_m-pohankova.jpg",
    "Ruien Zhang": "37270_r-zhang.jpg",
    "Sebastian Sorger": "22921_s-sorger.jpg",
}


def download(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 QuantFutImages/1.0"}), timeout=25) as response:
        body = response.read(300_001)
    if len(body) > 300_000 or extension(body) not in ("png", "jpg"):
        raise ValueError("Not a supported image")
    return body


def main():
    manifest = leer_manifiesto()
    for name, source in TENNIS.items():
        url = "https://api.api-tennis.com/logo-tennis/" + source
        body = download(url)
        filename = f"{slug(name)}.{extension(body)}"
        path = ROOT / "tenis" / filename
        path.write_bytes(body)
        manifest["tenis"][norm(name)] = {"n": name, "f": filename, "a": "API-Tennis", "fuente": "API-Tennis",
            "l": "Imagen del proveedor", "lu": "https://api-tennis.com/documentation", "p": url}
    folder = ROOT / "futbol"
    folder.mkdir(exist_ok=True)
    (folder / "85064.png").write_bytes(download("https://media.api-sports.io/football/teams/3588.png"))
    manifest["futbol"] = {"85064": {"n": "Ey\u00fcpspor", "f": "85064.png", "fuente": "API-Football", "provider_id": 3588}}
    guardar_manifiesto(manifest)
    print(json.dumps({"tennis_added": len(TENNIS), "football_added": 1, "tennis_total": len(manifest["tenis"])}))


if __name__ == "__main__":
    main()
