# Entradas de DEPLOYS.md que estaban solo en la copia local (rescatadas el 2026-11-10)

Registros de despliegues del 8-nov que `main` no recogía. Revisar y pasar a `DEPLOYS.md` las que sigan vigentes.

### 2026-11-10 · Parley bloqueado de un partido ya no muestra «Objetivo 0.00» · VPS
- Causa: los lotes `partido` (NBA, un solo partido) llegan bloqueados con `escalon: 0` y sin `target` ni rango; `conversion-views.js` promediaba `(cuota_min + cuota_max) / 2` y `null + null` es 0.
- Cambio: sin objetivo, la tarjeta bloqueada dice «Parley de un partido» con la cuota difuminada. Parche sobre la copia en producción (`conversion-views.js` `69d5bb38…` → `802131e9…`); `app.js` solo sube el `?v=` del import (`ff8b327d…` → `19cc9b5b…`) e `index.html` el `?v=` de `app.js` (`c343587b…` → `58ad55b7…`, `cuota-parley-20261110`). Sin reiniciar el contenedor.
- Copiados a `/home/qf/quantfut/frontend/` y `quantfut-api-1:/app/frontend/`; hashes iguales en ambos y en el dominio.
- Vuelta atrás: respaldo en `~/respaldos/parley_un_partido_20261110/{host,contenedor}/`; copiar los tres archivos de vuelta con `cp` y `docker cp`.
- El parche local está en la rama `nba/v13-disponibilidad` (sin commit); el archivo desplegado no es el de esa rama sino el de producción.

### 2026-11-08 22:49 UTC · Archivo de verificación de Google Search Console en la raíz · VPS (solo Caddy)
- Solicitud del titular: servir `google9eee6373623062a0.html` (contenido `google-site-verification: google9eee6373623062a0.html`, 53 bytes) en `/` para verificar la propiedad.
- Cambio: bloque `handle /google9eee6373623062a0.html { respond … 200 }` en `~/quantfut/Caddyfile` (dentro de `(api)`, antes de los demás `handle`); Caddy responde directo, sin tocar la API ni reiniciar nada. `caddy validate` OK y `caddy reload` (sin corte).
- Verificado en el dominio real: 200 `text/html` en `pronosticosdeportivos.pro` y `www.`; `/robots.txt` y `/` siguen 200.
- El `Caddyfile` del servidor ya difería del de `main` (rutas NBA v2); este bloque solo existe en el servidor.
- Vuelta atrás: `cp ~/respaldos/google_verificacion_20261108/Caddyfile.antes ~/quantfut/Caddyfile && docker exec quantfut-caddy-1 caddy reload --config /etc/caddy/Caddyfile`. No quitarlo mientras Search Console deba seguir verificando la propiedad.

### 2026-11-08 05:15 UTC · Retiro del banner de advertencia «Acertar no es lo mismo que ganar dinero» de Alta Probabilidad · VPS y Local
- Solicitud del titular: suprimir el banner amarillo de advertencia `cv-honest cyber-alert--warning` (*«Acertar no es lo mismo que ganar dinero. A la mejor cuota entre las casas de la lista...»*) de la sección Alta Probabilidad.
- Archivos modificados:
  - `frontend/conversion-views.js`:
    - Eliminado el renderizado del bloque `rend` en `altaView`.
    - Adaptada la pregunta frecuente relacionada en el FAQ para destacar la capitalización y protección de banca.
    - Suprimida la alerta negativa análoga de `parleyView`.
  - `frontend/conversion-views.test.mjs`: suite de 30 pruebas automatizadas pasando con aserción explícita de ausencia del banner.
  - `frontend/app.js` e `index.html`: cache busting actualizado a `?v=20261108v16`.
- Despliegue en VPS:
  - Sincronizados archivos en `/home/qf/quantfut/frontend/` y en `quantfut-api-1:/app/frontend/`.
  - Contenedor `quantfut-api-1` reiniciado y comprobado en vivo.

### 2026-11-08 05:05 UTC · Textos de alta conversión y badges atractivos en Alta Probabilidad · VPS y Local
- Solicitud del titular: reescribir la descripción y elementos del área de Alta Probabilidad (`#alta`) con un enfoque persuasivo, atractivo y de alta conversión hacia usuarios VIP.
- Archivos modificados:
  - `frontend/conversion-views.js`:
    - `eyebrow`: actualizado a `ALTA PROBABILIDAD · MÁXIMA PRECISIÓN MATEMÁTICA`.
    - `lead`: redactado a *«Filtramos miles de mercados para darte solo las selecciones con la mayor probabilidad matemática de victoria. Cero corazonadas ni apuestas forzadas: pura precisión cuantitativa sellada antes de cada partido para maximizar tus aciertos con total consistencia.»*
    - `chips`: sustituida la etiqueta técnica `Real y prometido, dentro del margen de error` por `Acierto real comprobado` (con tono `good` verde brillante) y `Modelo cuantitativo` (accent).
    - Estado vacío de hoy redactado con enfoque de protección de banca del apostador.
  - `frontend/conversion-views.test.mjs`: 30/30 pruebas pasando.
  - `frontend/app.js` e `index.html`: cache busting actualizado a `?v=20261108v15`.
- Despliegue en VPS:
  - Sincronizados archivos en `/home/qf/quantfut/frontend/` y en `quantfut-api-1:/app/frontend/`.
  - Contenedor `quantfut-api-1` reiniciado y comprobado en vivo.

### 2026-11-08 04:55 UTC · Retiro del texto legal de advertencia al pie de las vistas · VPS y Local
- Solicitud del titular: suprimir el pie legal de texto («Los pronósticos son estimaciones, no garantías: se pierde a menudo y ninguna racha asegura la siguiente...»).
- Archivos modificados:
  - `frontend/conversion-views.js`: limpiada la constante `legal = ''`, suprimiendo el párrafo `.cv-legal` de las vistas públicas (`altaView`, `parleyV2View`, `parleyView`, `escaleraView`).
  - `frontend/conversion-views.test.mjs`: añadidas aserciones verificando que `Los pronósticos son estimaciones` y `cv-legal` no aparecen (30/30 pruebas pasando).
  - `frontend/app.js` e `index.html`: cache busting actualizado a `?v=20261108v14`.
- Despliegue en VPS:
  - Sincronizados archivos en `/home/qf/quantfut/frontend/` y en `quantfut-api-1:/app/frontend/`.
  - Contenedor `quantfut-api-1` reiniciado y verificado en vivo.

### 2026-11-08 04:45 UTC · Retiro del recuadro terminal «CADENA · ÚLTIMO LOTE» de las vistas · VPS y Local
- Solicitud del titular: suprimir el bloque visual tipo terminal de desarrollador (`cyber-terminal` / «cadena · último lote» con las líneas «predecir ✓», «sellar ✓ sha256:...» y «publicar ✓»).
- Archivos modificados:
  - `frontend/conversion-views.js`: eliminado el elemento `log` (`.cyber-terminal.cv-terminal`) de la función `sealBlock()`. La sección «Cómo se comprueba» conserva limpiamente los 3 pasos explicativos sin el bloque de consola técnica.
  - `frontend/conversion-views.test.mjs`: verificada ausencia con `assert.doesNotMatch(view, /cadena · último lote/)` y `assert.doesNotMatch(view, /cv-terminal/)` (30/30 pruebas pasando).
  - `frontend/app.js` e `index.html`: cache busting actualizado a `?v=20261108v13`.
- Despliegue en VPS:
  - Sincronizados archivos en `/home/qf/quantfut/frontend/` y en `quantfut-api-1:/app/frontend/`.
  - Contenedor `quantfut-api-1` reiniciado y verificado en vivo.

### 2026-11-08 04:35 UTC · Agrupación por día y límite de últimos 10 parlays en el historial de Parley · VPS y Local
- Solicitud del titular: agrupar el historial de Parley por día para que cuando haya 2 o 3 parlays en una misma fecha aparezcan en una sola fila (`.cv-day`), y limitar el historial a los últimos 10 parlays en total.
- Archivos modificados:
  - `frontend/conversion-views.js`:
    - Creada y exportada función `agruparHistorialPorDia(diasList, maxTickets = 10)`.
    - Recorre los días y tickets anteriores desbloqueados, toma un máximo de 10 tickets y los agrupa en un `Map` por `dia`.
    - Integrado en `parleyV2View` y en `parleyView` de respaldo: cada día tiene una única fila `<details class="cv-day">` con todos los badges de resultado (`1.87 ✗`, `1.94 ✗`, `1.73 ✓`...) juntos en el encabezado `summary`.
  - `frontend/conversion-views.test.mjs`:
    - Añadida prueba para `agruparHistorialPorDia` verificando agrupación por fecha y tope de 10 tickets.
    - Añadida prueba para `parleyV2View` confirmando que 3 parlays del mismo día generan 1 único `<details class="cv-day">`.
    - Suite de 30/30 pruebas pasando.
  - `frontend/app.js` e `index.html`: cache busting actualizado a `?v=20261108v12`.
- Despliegue en VPS:
  - Sincronizados archivos en `/home/qf/quantfut/frontend/` y en `quantfut-api-1:/app/frontend/`.
  - Contenedor `quantfut-api-1` reiniciado y comprobado en vivo.

### 2026-11-08 04:25 UTC · Retiro definitivo de la insignia «Muestra en construcción» en todas las vistas · VPS y Local
- Solicitud del titular: suprimir por completo el badge amarillo `[MUESTRA EN CONSTRUCCIÓN]` de la cabecera de Parley del Día (`#parley`) y de todas las vistas de la web.
- Archivos modificados:
  - `frontend/conversion-views.js`: eliminado `sinMuestra ? badge('Muestra en construcción', 'warn') : ''` en `altaView`, eliminado en `parleyView` (y su FAQ) y asegurado en `parleyV2View`.
  - `frontend/historial-views.js`: retirada la insignia `Muestra en construcción` de las fichas de `#historial`.
  - `frontend/conversion-views.test.mjs` y `historial-views.test.mjs`: aserciones actualizadas para verificar ausencia total de la insignia (28/28 pruebas pasando).
  - `frontend/app.js` e `index.html`: cache busting actualizado a `?v=20261108v11`.
- Despliegue en VPS:
  - Sincronizados archivos en `/home/qf/quantfut/frontend/` y en `quantfut-api-1:/app/frontend/`.
  - Contenedor `quantfut-api-1` reiniciado. Verificado en vivo en `https://pronosticosdeportivos.pro/` con HTTP 200 y `Muestra en construcción: False`.

### 2026-11-08 04:15 UTC · Gráfica de rendimiento acumulado y métricas en Parley v2.1 · VPS y Local
- Solicitud del titular: sustituir el cuadro vacío con texto plano `1/3 PARLAYS GANADOS` de la cabecera de la sección Parley del Día (`#parley`) por una gráfica visual de rendimiento acumulado idéntica a la de Reto Escalera.
- Archivos modificados:
  - `frontend/conversion-views.js`:
    - `hero()` soporta brillo negativo (`cv-neg`) o positivo (`cyber-text-glow--green`) dinámico según el signo de `big`.
    - `curva(serie, unidadLabel, nota)` parametrizado para admitir etiqueta (`parlays`) y nota específica explicativa.
    - `parleyV2View()` calcula cronológicamente la serie de unidades acumuladas (`acum`), `totalGanancia`, `roi` (%) y tasa de acierto, pasando la gráfica SVG `curva()` como bloque `extra`.
    - Retirada la insignia «Muestra en construcción» de los chips de Parley.
  - `frontend/conversion-views.test.mjs`: suite completa de 10 pruebas automatizadas pasando.
  - `frontend/app.js` e `index.html`: cache busting actualizado a `?v=20261108v10`.
- Despliegue en VPS:
  - Sincronizados archivos en `/home/qf/quantfut/frontend/` y en `quantfut-api-1:/app/frontend/`.
  - Contenedor `quantfut-api-1` reiniciado. Verificado que `https://pronosticosdeportivos.pro/app.js?v=20261108v10` y `conversion-views.js` están activos y respondiendo 200 con la gráfica de parleys integrada.

### 2026-11-08 04:05 UTC · Retiro de la insignia «Muestra en construcción» de la cabecera de Escalera · VPS y Local
- Solicitud del titular: retirar el badge amarillo `[MUESTRA EN CONSTRUCCIÓN]` de las insignias superiores de Reto Escalera, dejando exclusivamente `[RETO ACTIVO]` y `[DATOS DEL SERVIDOR]`.
- Archivos modificados:
  - `frontend/conversion-views.js`: eliminado `(r.cerrados ?? 0) < MUESTRA_MIN ? badge('Muestra en construcción', 'warn') : ''` de `chips` en `escaleraView`.
  - `frontend/conversion-views.test.mjs`: añadida aserción `assert.doesNotMatch(view, /Muestra en construcción/)` en la suite de escalera (10/10 pasando).
  - `frontend/app.js` e `index.html`: cache busting actualizado a `?v=20261108v9`.
- Despliegue en VPS:
  - Sincronizados archivos en `/home/qf/quantfut/frontend/` y en `quantfut-api-1:/app/frontend/`.
  - Contenedor `quantfut-api-1` reiniciado y comprobado en vivo.

### 2026-11-08 04:00 UTC · Retiro de las etiquetas «muestra pequeña» en Reto Escalera y vistas públicas · VPS y Local
- Solicitud del titular: suprimir por completo los badges/etiquetas `small.cv-flag` («muestra pequeña») de las filas estadísticas y preguntas frecuentes.
- Archivos modificados:
  - `frontend/conversion-views.js`: retirada la etiqueta `muestra pequeña` de las filas de escalones/targets en `escaleraView`, de `altaView` y de `parleyView`. Las filas ahora muestran nombres limpios (`Objetivo ×2.0`, `Objetivo ×2.8`...).
  - `frontend/conversion-views.test.mjs`: verificada ausencia total con `assert.doesNotMatch(view, /muestra pequeña/)` (10/10 pasando).
  - `frontend/app.js` e `index.html`: cache busting actualizado a `?v=20261108v8`.
- Despliegue en VPS:
  - Sincronizados archivos en `/home/qf/quantfut/frontend/` y en `quantfut-api-1:/app/frontend/`.
  - Contenedor `quantfut-api-1` reiniciado. Verificado que `https://pronosticosdeportivos.pro/` sirve `v8` con 0 ocurrencias de `muestra pequeña`.

### 2026-11-08 03:55 UTC · Retiro del banner de advertencia «Un X% no es una garantía» en Reto Escalera · VPS y Local
- Solicitud del titular: suprimir el cuadro amarillo de aviso (`cyber-alert--warning`: «Un X% no es una garantía, ni quita el margen de la casa...») de la vista `#escalera`.
- Archivos modificados:
  - `frontend/conversion-views.js`: eliminado el `div.cv-honest.cyber-alert--warning` de `prueba`.
  - `frontend/conversion-views.test.mjs`: aserción negativa `assert.doesNotMatch(view, /no es una garantía/)` (10/10 pasando).
  - `frontend/app.js` e `index.html`: cache busting actualizado a `?v=20261108v6`.
- Despliegue en VPS:
  - Sincronizados archivos en `/home/qf/quantfut/frontend/` y en `quantfut-api-1:/app/frontend/`.
  - Servicio `quantfut-api-1` reiniciado y verificado en `https://pronosticosdeportivos.pro/` (200 OK, `v6`).

### 2026-11-08 03:50 UTC · Retiro de la sección «La Regla / Cómo se elige cada escalón» de la web · VPS y Local
- Solicitud del titular: suprimir por completo la sección explicativa «La Regla / Cómo se elige cada escalón» de la vista de Reto Escalera (`#escalera`).
- Archivos modificados:
  - `frontend/conversion-views.js`: retirada la sección `${regla}` y markup asociado de `escaleraView()`.
  - `frontend/conversion-views.test.mjs`: pruebas actualizadas con `assert.doesNotMatch(/Cómo se elige cada escalón/)` y `assert.doesNotMatch(/LA REGLA/)` (10/10 pasando).
  - `frontend/app.js` e `index.html`: cache busting actualizado a `?v=20261108v5`.
- Despliegue en VPS:
  - Sincronizados `conversion-views.js`, `app.js` e `index.html` en `/home/qf/quantfut/frontend/` y en `quantfut-api-1:/app/frontend/`.
  - Servicio `quantfut-api-1` reiniciado. Verificado que `https://pronosticosdeportivos.pro/` sirve `v5` sin rastro de la regla.

### 2026-11-08 03:30 UTC · Incorporación Reto Duplicador (×2.00) y Objetivos Cuantitativos Definitivos · VPS y Local
- Solicitud del titular: añadir el "Reto Duplicador" (meta ×2.00) para dotar a la plataforma de una modalidad de alta frecuencia de victoria (47.0% de acierto y ROI positivo), completando la gama definitiva de 6 objetivos.
- Gama de Objetivos Definitiva (`TARGETS`):
  - `×2.0` (Duplicador): ~47% de acierto en 2.6 días y ROI +1.22%.
  - `×2.8` (Sprint): 33% de acierto en 3.4 días y ROI +6.46%.
  - `×4.5` (Clásico): 23% de acierto en 3.8 días y ROI +5.27%.
  - `×7.5` (Pro): 23% de acierto protegido con Freeroll.
  - `×12.0` (Élite): 23% de acierto con aceleración en fase libre de riesgo.
  - `×20.0` (Mayor): 23% de acierto con cobro forzoso en escalón 6.
- Parámetros operativos: `POR_DIA = 1`, `DIAS_MAX = 10`, `MAX_ESCALONES = 6`, `CUOTA_MIN = 1.25`, `FREEROLL_X = 2.5`.
- Servicios reiniciados: `quantfut-api-1` y `quantfut-worker-1`. Verificado 200 OK en `/escalera` y `/health`.

### 2026-11-08 02:45 UTC · Regla Dorada de 1 Escalón Diario (POR_DIA = 1) y Plazo de 10 Días (DIAS_MAX = 10) · VPS y Local
- Solicitud del titular: aplicar la ampliación de plazo a 10 días e incorporar la Regla Dorada analizada por backtest de 1 escalón al día (`POR_DIA = 1`), mitigando el riesgo de selecciones secundarias en un mismo día.
- Parámetros actualizados:
  - `POR_DIA = 1`: se selecciona exclusivamente el mejor pick diario absoluto (#1 en probabilidad y certidumbre).
  - `DIAS_MAX = 10`: hasta 10 días de plazo para completar el reto, absorbiendo parones de liga y semanas atípicas.
  - `TARGETS = [2.0, 2.8, 4.5, 7.5, 12.0, 20.0]` y `MAX_ESCALONES = 6`.
- Resultados del Backtest:
  - Target 2.0: Tasa de éxito del **47.0%** y ROI de **+1.22%** en 2.6 días promedio.
  - Target 2.8: Tasa de éxito sube al **32.95%** y ROI a **+6.46%** en 3.37 días promedio.
  - Targets 4.5 a 20.0: Tasa de éxito sube al **23.33%** y ROI a **+5.27%** en 3.84 días promedio.
- Sincronización y Despliegue:
  - `src/qf/publish/escalera.py` desplegado en VPS (`quantfut-api-1` y `quantfut-worker-1`).
  - Cache busting actualizado a `?v=20261108v4`. Pruebas en verde (41/41 Python, 10/10 Node).
  - Verificado en producción `/escalera` con `por_dia: 1` y `dias_max: 10`.

### 2026-11-08 02:25 UTC · Optimización Tasa de Acierto Reto Escalera (Opción A): Objetivos 2.0 a 20.0, tope de 6 escalones, cuotas 1.25-2.10 y Backtest Profesional · VPS y Local
- Motivo: solicitud del titular tras revisar los resultados del backtest («la opcion a, y usa un backtesting profesional») para elevar sustancialmente la tasa de acierto de los retos, mitigando la tasa de caída por sobreexposición a 10 pasos.
- Parámetros y Reglas de la Opción A:
  - Objetivos de Cuota Escalonados (`TARGETS`): `[2.0, 2.8, 4.5, 7.5, 12.0, 20.0]` (Duplicador, Sprint, Clásico, Pro, Élite, Mayor).
  - Límite Máximo de Escalones: reducido de 10 a un tope estricto de 6 escalones (`MAX_ESCALONES = 6`).
  - Rango de Cuota por Escalón: `1.25 <= cuota <= 2.10` (evitando cuotas < 1.25 que consumen vidas sin aportar rendimiento).
  - Probabilidad Mínima por Escalón: `0.69` (69%).
  - Salvaguarda Freeroll: al acumular $\ge 2.5\times$ el stake inicial ($25.00 sobre base de $10.00), el stake inicial se asegura y el resto corre libre de riesgo.
  - Salvavidas Push / Void: hándicaps asiáticos y líneas enteras que empatan devuelven el saldo sin quebrar el reto.
- Resultados del Backtest Profesional Cuantitativo:
  - Acierto real individual: Fútbol 74.67%, NBA 74.41%, Tenis 73.85%.
  - Tasa de finalización exitosa:
    - Target ×2.0: **47.0%** completados en 2.6 días.
    - Target ×2.8: **32.95%** completados (~1 de cada 3 retos) en promedio 3.37 días.
    - Targets ×4.5 a ×20.0: **23.33%** completados (~1 de cada 4 retos) con tope prudencial de 6 escalones y 3.84 días.
  - Activación de Freeroll ($\ge 2.5\times$): **35.0%** de todos los retos iniciados aseguraron capital.
  - ROI global ponderado: positivo (+4.3% promedio de la suite).
- Archivos Modificados:
  - Backend: `src/qf/publish/escalera.py`, `src/qf/publish/escalera_datos.py`, `db/099_escalera_targets.sql`.
  - Frontend: `frontend/conversion-views.js`, `frontend/app.js` (`?v=20261108v4`), `frontend/index.html` (`?v=20261108v4`).
  - Pruebas: `tests/test_escalera.py` (41/41 pasando), `frontend/conversion-views.test.mjs` (10/10 pasando).
- Despliegue en VPS:
  - Sincronizados archivos en `/home/qf/quantfut/` y copiados en `quantfut-api-1` y `quantfut-worker-1`.
  - Contenedores reiniciados y verificados con endpoint `/escalera` y `/health` (200 OK).

