# Auditoría de la web y sus imágenes — 28 de octubre de 2026

La cobertura de imágenes **no está completa**. Los 503 recursos existentes comprobados responden con HTTP 200 y firma y tipo MIME de imagen correctos, pero faltan contenidos y una vista no utiliza las fotos que ya existen.

## Alcance y resultados medidos

Web publicada: https://pronosticosdeportivos.pro/. API en ejecución: `quantfut-api:31121ba`. Código de referencia: `origin/main` `7ba7a49`. La carpeta inicial del usuario estaba en una rama antigua de NBA con cambios ajenos; las correcciones se prepararon en una copia de trabajo independiente.

Se revisaron el código de la portada, tarjetas de pronósticos, ventana de partidos, estadísticas, alineaciones, historial y carga de imágenes; se navegaron las vistas públicas de fútbol, NBA y tenis en navegador móvil. Las comprobaciones HTTP de recursos se ejecutaron dentro de la API de producción, sin modificarla. No equivalen a una prueba visual de cada equipo o jugador, ni a una auditoría completa de pagos, seguridad o modelos deportivos.

| Contenido | Cobertura comprobada | Resultado |
|---|---:|---|
| Agenda de fútbol | 193 encuentros, 306 equipos únicos | 305 equipos con escudo; uno sin escudo |
| Logos NBA | 30 de 30 franquicias | Todos los archivos disponibles |
| Tenistas de la publicación pública | 157 encuentros, 178 personas únicas | 166 con foto; 12 sin foto |
| Catálogo completo de tenis | 168 fotografías | Todos los archivos disponibles; dos personas del catálogo no aparecen en la publicación examinada |
| Recursos de imagen existentes | 305 escudos + 30 logos + 168 fotos = 503 | 503 HTTP 200 y firmas/tipos MIME correctos |
| Fotos de futbolistas | Sin integración en alineaciones | No se muestran |
| Fotos de jugadores NBA | Sin catálogo ni integración de retratos | No se muestran; el panel independiente usa iniciales |

El navegador confirmó logos NBA en la lista y el encabezado (20 y 42 px respectivamente), sin desbordamiento horizontal en la carga actualizada. La carga diferida de imágenes fuera de pantalla no se contó como error.

## Hallazgos pendientes en producción

1. **Fotos de jugadores de fútbol y NBA sin implementar.** Las alineaciones de fútbol renderizan dorsal, nombre y posición; no hay una fuente de retratos conectada. Las selecciones individuales NBA muestran texto, y el panel independiente `/nba` utiliza iniciales. Los logos de equipos no sustituyen a estas fotos.
2. **Ventana de tenis sin fotos.** En portada aparecen fotos de Jakub Mensik y Adrian Mannarino, pero al abrir el mismo encuentro el DOM de producción contiene cero imágenes y 18 marcas con iniciales. `sports-window.js` solo consultaba el apartado NBA del manifiesto. Afecta a lista y encabezado de todos los encuentros de tenis, incluso cuando la imagen existe.
3. **Escudo de fútbol ausente:** Eyüpspor, identificador interno `85064`. La agenda devuelve el campo de escudo vacío. Hace falta resolver su identificador de proveedor y descargar el archivo correcto.
4. **Doce tenistas sin foto:** Aoi Ito, Brandon Nakashima, Daniel Merida, Han Shi, Ignacio Buse, Janice Tjen, Martin Landaluce, Matteo Berrettini, Mia Pohankova, Ruien Zhang, Sebastian Sorger y Xinran Sun. Se debe verificar identidad y procedencia antes de incorporar cada imagen y sus créditos.
5. **Recuperación del manifiesto:** un fallo de red quedaba guardado durante la sesión y actualizar los pronósticos no reintentaba las imágenes. Además, el cargador aceptaba diccionarios nulos o listas como si fueran válidos.
6. **Fallo de un archivo individual:** las vistas tienen iniciales cuando falta la entrada del catálogo, pero no un tratamiento general del evento de error de descarga de cada imagen. No hubo descargas fallidas entre los 503 recursos examinados; esta observación procede del código.

En la primera carga del navegador apareció una página anterior que enlazaba `ergonomia.css`, ya inexistente en el origen, y los logos se mostraron a 200 px con desbordamiento. Una navegación nueva cargó `window.css` y corrigió el tamaño. La verificación HTTP externa posterior entregó la portada actual tanto en `/` como con parámetro de auditoría, con `CF-Cache-Status: DYNAMIC` y `Cache-Control: no-cache, must-revalidate`. No hay evidencia suficiente para atribuir el incidente a una caché persistente de Cloudflare.

## Correcciones preparadas y comprobación

En la copia aislada se corrigieron las fotos de tenis en lista y encabezado, conservando atribución y licencia; se añadió recorte circular para retratos y validación de nombres de archivo. NBA conserva sus logos. Se rechazan manifiestos nulos o con listas y se permite reintentar una carga fallida al actualizar. Se actualizaron las versiones de los archivos modificados para evitar reutilizar estáticos anteriores.

- `npm run check`: **76 pruebas aprobadas** y comprobaciones de sintaxis aprobadas.
- `tests/test_web_imagenes.py`: **4 pruebas aprobadas**, incluidas todas las entradas del catálogo, créditos y rechazo de rutas no permitidas.
- Regresión específica: tenis con acentos, fotos y créditos en ambas posiciones; logos NBA preservados; ausencia de foto y archivos inválidos con iniciales.
- Evidencia HTTP detallada: [auditoria_imagenes_web_20261028.json](auditoria_imagenes_web_20261028.json).
- Comprobador de solo lectura: [auditar_imagenes_web.py](../scripts/auditar_imagenes_web.py), ejecutable por entrada estándar dentro del contenedor API. El informe limita la salida a cobertura y metadatos de imágenes; no exporta cuentas ni valores de pronósticos.

**Estado de entrega:** correcciones locales preparadas; no se desplegaron ni se incorporaron fotografías nuevas. Sigue pendiente completar los 13 recursos ausentes, implementar retratos de futbolistas y jugadores NBA y publicar la corrección de la ventana de tenis. La evidencia refleja la publicación disponible durante esta revisión; no acredita cobertura para todos los equipos o deportistas futuros.
