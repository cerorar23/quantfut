# Mercados de la app basados en evidencia QuantFut

Fecha: 11 de octubre de 2026. Petición: adaptar las pantallas de mercados a lo que el modelo y su estadística respaldan, en lugar de copiar radar, primer tiempo y porcentajes de la referencia.

## Entrega

La tercera pestaña cambia de En vivo a **Mercados**. Inicio incorpora accesos a Córners por equipo, Hándicap, Marca un equipo y Doble oportunidad. Predicciones sustituye Combinada/Spor Toto por Alta probabilidad/Escalera, que ya existen en la web. NBA conserva secciones independientes y su clasificación exploratoria.

Pantallas de cada mercado: cabecera de acierto, Hoy/Histórico, estado de avisos pendiente, botón Hazte VIP que abre los planes y revisión por línea. Hoy no inventa partidos ni señales: indica que falta conectar los pronósticos actuales. Histórico muestra estadísticas agregadas reales; el detalle por encuentro se conectará posteriormente. No se publican porcentajes o alertas de los ejemplos del usuario.

## Evidencia para destacar líneas

| Línea destacada | Acierto retrospectivo | Casos | Filtro de probabilidad de su prueba |
|---|---:|---:|---|
| Local: más de 1,5 córners | 93,06 % | 6.934 | 60–97 % |
| Hándicap asiático +2 | 90,37 % | 7.764 | 80–95 % |
| Marca el local | 88,52 % | 4.470 | 80–95 % |
| Doble oportunidad | 86,36 % | 8.201 | 80–95 % |
| Más de 6,5 córners totales | 85,27 % | 5.865 | 80–95 % |
| Ganador 1X2 | 84,82 % | 685 | 80–95 % |
| Más de 1,5 goles | 84,09 % | 4.355 | 80–95 % |
| Menos de 6,5 tarjetas | 83,84 % | 6.725 | 60–97 % |

Son tasas por línea y filtro, no un porcentaje de acierto de toda la familia ni de próximos partidos. No se suman las muestras retrospectivas de líneas solapadas. El hándicap mide ganar condicionado a que no haya devolución; las devoluciones no cuentan como aciertos. Mucho acierto por sí solo no prueba ventaja sobre una casa o rentabilidad.

La regla de presentación exige línea desplegada, prueba aprobada y ≥500 casos para destacar una fortaleza. Es una decisión de interfaz para no promover porcentajes llamativos con muestras pequeñas; no modifica el criterio científico del modelo, las reglas de publicación ni sus controles. Por ejemplo, menos de 11,5 córners tiene 100 % en 19 casos en la revisión reciente: se identifica como muestra limitada y no encabeza la categoría. Más de 2,5 goles y hándicap −1 tienen también muestras limitadas bajo esta regla de presentación.

## Publicado frente a retrospectivo

Consulta de lectura al VPS: API pública `/alta-probabilidad`, corte guardado el 11 de octubre. **75 aciertos / 96 liquidados = 78,1 %**, promedio prometido 82,6 %. La línea está activa, pero el control señala muestras insuficientes por grupo y menos de diez semanas. No hay confirmación prospectiva suficiente.

Las cabeceras de cada familia muestran la razón exacta de sus resultados publicados; por ejemplo, hándicap 14/21 y córners por equipo 9/10. Siempre se identifica su pequeña muestra y se presenta aparte de la tasa de la línea retrospectiva destacada. No se transforma el 100 % publicado de cuatro córners en una fortaleza confirmada.

El corte es un recurso local de la app, con fecha/hora UTC visibles. La app aún no se actualiza desde la API: no mostrar ese corte como dato actual de cada día. Las fichas generales de partidos siguen identificadas como ejemplos. No se han integrado Firebase, identidad ni compras.

## Modelo propio y referencia

- Córners y tarjetas: modelo estadístico de equipos/ligas; córners por equipo con su dispersión propia. Alta probabilidad limita córners a la probabilidad sin margen de la casa.
- Ganador/doble oportunidad: referencia Pinnacle sin margen; goles, marca un equipo y hándicap se derivan del ajuste de goles a esa referencia. No atribuir estas tasas a una superioridad demostrada del modelo propio.
- NBA: ganador 80,4 % (1.071 casos), puntos de equipo 74,3 % (1.721) y total 70,5 % (583), evaluación exploratoria. No entran en el ranking confirmado de fútbol. Puntos/rebotes individuales no se anuncian como selecciones fiables ≥70 %; robos/tapones no se destacan por un acierto alto que coincide con la referencia.

## Divergencia local / servidor registrada

Consultadas las constantes del contenedor `quantfut-api-1` sin cambiarlo. El servidor conserva la revisión previa: tarjetas solo menos de 6,5 en la escalera y córners local más de 2,5 en alta probabilidad, entre otras líneas antiguas.

La prueba local corregida del 10 de octubre elimina local más de 2,5 de alta probabilidad y añade tarjetas menos de 4,5 y 5,5 en la escalera. La app no destaca la línea que falla; marca las dos nuevas líneas de tarjetas como **pendientes de desplegar**. Desplegar esa revisión del backend es una tarea independiente; no se hizo como parte del diseño móvil. No modificar las reglas de producción para hacer coincidir un prototipo.

## Archivos y comprobación

- `assets/model/market_evidence.json`: corte trazable con familias, líneas, muestras, origen y huellas de fuentes.
- `docs/evidence/public_history_20261011.json`: únicamente estado/control/historial agregado público; sin credenciales ni análisis premium.
- `tool/build_market_snapshot.py`: genera el recurso desde evaluaciones ya existentes; no entrena ni consulta proveedores deportivos.
- `lib/product/market_catalog.dart`, `market_screens.dart`: separación de datos y pantallas, filtro de evidencia y presentación.
- Fuentes: `.local/alta_prob_ampliacion_20261009.json`, `.local/escalera_estadistica_20261010_fijos.json` y `docs/nba_nueve_mercados_estadistica_20261009.md`.

Validación: 18 pruebas Flutter aprobadas, análisis sin incidencias y APK Android debug. Pruebas nuevas verifican muestra perfecta pequeña, línea aún no desplegada, NBA experimental, cálculo exacto del historial, avisos inactivos, navegación VIP y texto ampliado. Capturas en `docs/validation/mercados_20261011/`.
