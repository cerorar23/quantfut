"""Genera el icono de QuantFut: el «Q.» verde de la bienvenida sobre fondo oscuro.

    python tool/make_icon.py        (requiere Pillow)

Escribe image/quantfut_icon.png (1024², para iOS y Android clásico) y
image/quantfut_icon_foreground.png (adaptable de Android: transparente, contenido dentro
de la zona segura del 66 %). Luego: `dart run flutter_launcher_icons`.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT = ROOT / "fonts" / "Gilroy-ExtraBold.otf"
BACKGROUND = (9, 15, 26, 255)      # 0xff090f1a, el fondo de la app
GREEN = (0, 213, 139, 255)         # 0xff00d58b, el verde del «Q.»
SIZE = 1024


def draw(canvas: Image.Image, content: float) -> None:
    """Dibuja «Q.» centrado; `content` es la fracción del lienzo que ocupa el conjunto."""
    d = ImageDraw.Draw(canvas)
    # Tamaño de letra que hace que «Q.» mida `content` de ancho.
    size = 400
    while True:
        font = ImageFont.truetype(str(FONT), size)
        box = d.textbbox((0, 0), "Q.", font=font)
        if box[2] - box[0] >= SIZE * content:
            break
        size += 8
    box = d.textbbox((0, 0), "Q.", font=font)
    x = (SIZE - (box[2] - box[0])) / 2 - box[0]
    y = (SIZE - (box[3] - box[1])) / 2 - box[1]
    d.text((x, y), "Q.", font=font, fill=GREEN)


full = Image.new("RGBA", (SIZE, SIZE), BACKGROUND)
draw(full, 0.62)
full.convert("RGB").save(ROOT / "image" / "quantfut_icon.png")

foreground = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw(foreground, 0.50)   # dentro de la zona segura de los iconos adaptables
foreground.save(ROOT / "image" / "quantfut_icon_foreground.png")
print("icono generado")
