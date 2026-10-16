"""Recursos de Play Store con la tipografia y el logo nativos de QuantFut."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "play_store" / "20261015"
OUT.mkdir(parents=True, exist_ok=True)
FONT = ROOT / "fonts" / "Gilroy-ExtraBold.otf"
REGULAR = ROOT / "fonts" / "Gilroy-Medium.ttf"
BG = "#090f1a"
GREEN = "#00d58b"
S = 3

def font(size, regular=False):
    return ImageFont.truetype(str(REGULAR if regular else FONT), size * S)

icon = Image.new("RGB", (512 * S, 512 * S), BG)
d = ImageDraw.Draw(icon)
size = 200
while True:
    f = font(size)
    box = d.textbbox((0, 0), "Q.", font=f)
    if box[2] - box[0] >= 512 * S * .62:
        break
    size += 4
x = (512 * S - (box[2] - box[0])) / 2 - box[0]
y = (512 * S - (box[3] - box[1])) / 2 - box[1]
d.text((x, y), "Q.", font=f, fill=GREEN)
icon.resize((512, 512), Image.Resampling.LANCZOS).save(OUT / "icono-512.png")

banner = Image.new("RGB", (1024 * S, 500 * S), BG)
d = ImageDraw.Draw(banner)
def text_at(x, y, text, size, fill="#ffffff", regular=False):
    d.text((x * S, y * S), text, font=font(size, regular), fill=fill)

d.rounded_rectangle((45*S, 91*S, 306*S, 409*S), radius=34*S, fill="#101e2d")
f = font(220)
box = d.textbbox((0, 0), "Q.", font=f)
d.text((175*S-(box[2]-box[0])/2-box[0], 250*S-(box[3]-box[1])/2-box[1]), "Q.", font=f, fill=GREEN)
text_at(351, 116, "FÚTBOL · DATOS · PROBABILIDADES", 17, GREEN)
text_at(345, 165, "QuantFut", 79)
text_at(350, 276, "Pronósticos y estadísticas", 31, "#e8edf3", True)
text_at(351, 337, "Calendario · Análisis · Historial", 20, "#9caec0", True)
d.line((351*S, 391*S, 935*S, 391*S), fill="#20384a", width=2*S)
d.line((351*S, 391*S, 506*S, 391*S), fill=GREEN, width=3*S)
banner.resize((1024, 500), Image.Resampling.LANCZOS).save(OUT / "grafico-destacado-1024x500.png")
print(OUT)
