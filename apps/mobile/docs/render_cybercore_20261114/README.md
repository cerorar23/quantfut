# Render CyberCore de la app (14-nov-2026)

Maqueta aprobada por el titular. **Es la referencia visual** del rediseño; el plan está en
`../PLAN_REDISENO_CYBERCORE_20261114.md` y `../PLAN_REDISENO_FASES_20261114.md`.

| Carpeta | Contenido |
|---|---|
| `capturas/` | Una captura PNG por lámina (36). Ancho 390 px; las «Completo» son pantallas largas desplegadas. |
| `pantallas/` | Fuente de cada lámina (`*.dc.html`). Sirven para **medir**: cada elemento lleva `style="…"` con tamaños, colores, tipografía y espaciados exactos. |
| `datos/` | Respuestas **reales** de la API del 14-nov-2026 (ficha de fútbol, estadísticas de NBA y de tenis, cartelera NBA, evento de tenis). Úsalas como *fixtures* de las pruebas (cópialas a `apps/mobile/test/fixtures/`). |
| `assets/`, `ASSETS.md` | Imágenes del render y su origen real. |
| `canvas.json` | Índice del lienzo (posición, tamaño y orden de las láminas). |

## Cómo leer un `.dc.html`
- **1 px = 1 dp.** El render es de 390 × 844.
- `{{campo}}` = dato; `<sc-if value="{{x}}">` = condicional; `<sc-for list="{{xs}}" as="x">` = bucle; `<dc-import name="Partido" sport="nba" tab="stats">` = la lámina reutiliza otro componente con esos parámetros. La lógica de ejemplo y los datos están en el `<script type="text/x-dc">` del final (clase `Component`, método `renderVals()`).
- Variables CSS de cada lámina (en el `div` raíz): `--cy` cian `#00f0ff`, `--gr` verde `#05ffa1`, `--ye` amarillo `#fcee0a`, `--mg` magenta `#ff2a6d`, `--p` `#12141d`, `--p2` `#181a25`, `--b` borde cian 20 %, `--bs` borde cian 48 %, `--ln` línea divisoria, `--mu` `#b2b7c7`, `--fa` `#939ab0`, `--d` Rajdhani, `--m` JetBrains Mono. `--cut`/`--cut2` = esquina cortada 10/16 px.
- Los `<img src="/_blob/<id>">` se traducen con `ASSETS.md`.
- Los archivos **no se abren solos** en un navegador (necesitan el runtime del lienzo): mira `capturas/` y mide en el código.

## Qué es dato real y qué es ejemplo
Ver §6 del plan principal. En una frase: partidos, estadísticas, tablas y alineaciones son reales; cuotas, casas, precios, saldos, avisos y la mayoría de cifras de marketing son de ejemplo.
