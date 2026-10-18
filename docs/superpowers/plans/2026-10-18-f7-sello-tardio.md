# F7 — Sello tardío en producción: plan de implementación (borrador)

**Estado:** diseño, sin código. Se implementa después del 1-nov (el motor está congelado hasta el reentrenamiento).
**Spec:** `docs/superpowers/specs/2026-10-14-senales-motor-principal-design.md` (sección 1) y `2026-10-15-mejoras-tres-motores-plan.md` (sección 4).
**Depende de:** comprometer-revelar ya implementado en `hashchain.py` (18-oct): el lote por partido lleva el pick minutos antes del saque, así que su JSON solo puede subirse al repo público al terminar el partido.

## Qué hay hoy (verificado el 18-oct en el repo y en producción)

- `seal()` es idempotente **por fecha**: si ya existe un `prediction_batches` con esa `batch_date`, no sella. `_collect(batch_date)` filtra por `generated_at`/`published_at`/`decided_at` del día.
- `prediction_batches` **no** tiene unicidad en `batch_date` (solo índice): varios lotes por día caben en el esquema. `chain_sha256` sí es única y la cadena avanza por `seq`.
- Los archivos del lote se nombran por fecha (`YYYY-MM-DD.json` + `.receipt.json`) y `verify()` los recorre por ese patrón.
- Cuatro lectores unen `prediction_batches` por `batch_date = (decided_at AT TIME ZONE 'UTC')::date AND decided_at <= b.created_at`: `parley_datos.py`, `escalera_datos.py`, `alta_prob_datos.py` y, vía `_sql_sellado`, `alta_prob_ext.py` y `tarjetas_seg.py`.
- `daily.run()` hace predecir → seleccionar → persistir → productos → `seal()` → publicar, una vez al día (08:00 UTC).

## Riesgos que fijan el diseño

1. **Duplicación silenciosa.** Con varios lotes por día, el `JOIN` de los cuatro lectores casaría cada fila con *todos* los lotes posteriores a su `decided_at`: un producto "sellado" se contaría varias veces. Hay que restringir esos `JOIN` a `batch_kind = 'diario'` en el mismo cambio que crea el tipo de lote.
2. **Historial intacto.** Todo lote anterior al corte `LOTE_POR_PARTIDO_DESDE` se regenera con el formato actual; `verify` debe seguir dando el mismo hash para todo lo ya sellado (patrón de `LOTE_PARLEY_DESDE`).
3. **Fuga de picks.** Un lote de partido contiene el pick de valor minutos antes del saque. Su JSON no se sube hasta que el partido termina (`revelables` ya lo exige leyendo `matches`). El recibo (hash) sí sube de inmediato: es el sello externo.
4. **Nombre de archivo.** `YYYY-MM-DD.json` no distingue lotes del mismo día. Los de partido usarán `partido/YYYY-MM-DD/<match_id>.json` (+ recibo); `verify` y `revelables` deben recorrerlos.
5. **Disparo duplicado.** El worker revisa cada 5 min; el sello de un partido debe ser idempotente por `match_id` (unicidad en la base, no solo en memoria).

## Tareas

1. **Migración `db/NNN`:** `predictions.etapa` (`diaria` | `final`, por defecto `diaria`); `prediction_batches.batch_kind` (`diario` | `partido`, por defecto `diario`) y `match_id` nullable con unicidad parcial (`WHERE batch_kind = 'partido'`). Los triggers de inmutabilidad no se tocan.
2. **Lectores:** añadir `AND b.batch_kind = 'diario'` a los cuatro `JOIN`. Prueba que falla si un lote de partido hace que una fila se cuente dos veces.
3. **`hashchain`:** `_collect_partido(match_id)` y `seal_partido(match_id)`; `LOTE_POR_PARTIDO_DESDE` con regla `lote_por_partido(dia)`. Mismo orden: predecir → seleccionar → sellar → publicar.
4. **Disparo** (`publish/sello_tardio.py`, tarea de 5 min): XI de ambos lados capturado **o** T-30, lo primero. Sin XI se sella igual y se anota en `data_completeness`.
5. **Predicción `final`:** núcleo + `ajuste.py` con los bloques que hayan pasado la puerta (hoy solo el XI simple); picks de valor solo de predicciones `final`, con las cuotas de ese momento (`odds_as_of` queda en el lote).
6. **Lote diario sin picks de valor:** sigue a las 08:00 UTC para la web y los productos de varios partidos; sus lectores siguen leyendo predicciones `diaria`.
7. **`verify`/`revelables`:** recorrer también `partido/`. Rama de pruebas: lote diario antiguo con el mismo hash que hoy, lote de partido válido, lote de partido alterado, lote sin revelar.
8. **Registro de lo publicado:** por partido, qué se publicó, a qué hora y con qué versión; una revisión posterior no reemplaza el historial vendido.
9. **Ensayo:** ejecutar contra una copia de la base (esquema aislado) antes de desplegar; anotar en `DEPLOYS.md` con su vuelta atrás.

## Decisiones del titular

1. **Ventana de disparo — SIN RESPONDER (propuesta mía, no es decisión).** Sellar cuando estén confirmados los XI de los dos lados o a
   **T-45**, lo primero. Razón: la alineación oficial suele publicarse hacia T-60 y la captura de FotMob ya toma instantáneas a ~T-70 y
   ~T-40; T-45 deja 45 min a quien apuesta y T-30 (el tope del borrador) sería muy justo. Confirmar T-45, T-30 o T-60.
2. **Qué ven los suscriptores — RESPONDIDO el 18-oct.** Sin VIP se ven gratis **4 de alta probabilidad, 1 de escalera y 1 de parley**
   (es lo que el código ya aplica: `FREE_MAX = 4`, `ladder_free_count = 1`, un parley al día en `parley_acceso.py`). El resto de los
   pronósticos bloqueados se muestra **difuminado con un botón «Acceso VIP»** que lleva a la pasarela de pago. Sigue sin responder:
   si se manda una notificación push al sellar un pick de partido.
   - Seguridad: el servidor ya NO envía selección ni probabilidad de un pronóstico bloqueado (solo categoría, equipos, hora y cuota, `mobile.metadata`),
     así que el difuminado es solo visual y no se puede quitar desde el navegador o la app.
   - Pasarela: en la **web**, Whop (checkout embebido). En la **app**, la compra de tienda (Play / App Store): Google y Apple exigen su
     sistema de compras para suscripciones digitales dentro de la app, y enviar a un cobro externo puede costar el rechazo o la baja de la ficha.
3. **Corte — SIN RESPONDER (propuesta mía).** `LOTE_POR_PARTIDO_DESDE` = el primer día sin lote sellado al desplegar, como en los demás bloques.

## Lo que este plan no hace

No reentrena ni activa ningún bloque nuevo, no toca los triggers de inmutabilidad ni `strength`, y no enciende `PUBLISH_PICKS_ENABLED`.
