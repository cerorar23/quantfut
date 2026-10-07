# Librerías de terceros del panel `/control`

Servidas desde el propio dominio para que la CSP del panel siga siendo
`'self'` (sin CDN en tiempo de ejecución). Versiones fijas; para actualizar,
descarga la nueva versión, revisa el diff y actualiza esta tabla.

| Archivo | Proyecto | Versión | Licencia | SHA-256 |
| --- | --- | --- | --- | --- |
| `tabler.min.css`, `tabler.min.js` | [tabler/tabler](https://github.com/tabler/tabler) (`@tabler/core`) | 1.6.1 | MIT | css `370a2d4e…5d65403`, js `9d26ca1a…9e09b` |
| `icons/*.svg` | [tabler/tabler-icons](https://github.com/tabler/tabler-icons) (`@tabler/icons`, outline) | 3.49.0 | MIT | — |
| `chart.umd.min.js` | [chartjs/Chart.js](https://github.com/chartjs/Chart.js) | 4.5.1 | MIT | `48444a82…c9f54a` |

Los SVG de iconos no se sirven: `panel.py` los incrusta en el HTML.
