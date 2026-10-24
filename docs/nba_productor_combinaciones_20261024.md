# NBA — productor vivo 1.3.2: sumas de puntos, rebotes y asistencias (24-oct-2026)

Aplica al motor vivo la calibración que `docs/nba_calibracion_motor_20261024.md` mostró necesaria: la ley v1 está sobreconfiada en las
sumas de puntos, rebotes y asistencias (pendiente ≈ 0,6 a los umbrales del productor) y la misma calibración que ya usa el productor para
los conteos simples la corrige. **No desplegado.** Cambia el módulo vivo, así que exige un modelo nuevo y una imagen nueva.
Protocolo del chequeo congelado antes de correr: `apps/nba/nba_live_combos_protocol.json`. Enmienda del protocolo vivo:
`apps/nba/multimarket_v13_live_protocol.json` (versión `nba-multimarket-live-1.3.2`, `amendment_2026_10_24`).

## Qué cambia
- Cuatro mercados nuevos sobre la línea principal de PropLine, condicionados a jugar y no accionables: **puntos + rebotes, puntos + asistencias,
  rebotes + asistencias y puntos + rebotes + asistencias** (`player_points_rebounds`, `player_points_assists`, `player_rebounds_assists`,
  `player_points_rebounds_assists`). El archivo horario de PropLine ya las captura (`scripts/propline_shared_config.json`).
- Mismo método que los conteos simples: ley v1 (binomial negativa + 25 % empírico, ventana 20) aplicada a la suma por partido, y la calibración logística
  `logit p`, sesgo, estado propio (Questionable/Doubtful, Probable) y minutos perdidos de los compañeros, ajustada sobre la rejilla de umbrales `{−4, −2, −1, 0, +1, +2, +4}`.
  La tasa previa por minuto de una suma es la suma de sus partes (0,85; 0,80; 0,35; 1,00).
- Código: `prop_lines.py` (mercados leídos), `multimarket_v13_live.py` (sumas, tasas, etiquetas, la fila de entrenamiento guarda el `offset`, y un modelo sin pesos
  para un mercado nuevo lo omite y lo cuenta en `market_not_in_model` en vez de adivinar), `multimarket_live_dashboard.py` (resultado oficial de las sumas) y la página (`web/`).
- **No cambia:** el modelo de equipo, la regla de lesiones (reporte ≥ 60 min antes), el sellado, los resultados, ni nada de las cohortes ya selladas.

## Chequeo previo (2025-26, con el mismo código del productor)
`live_combos_check.py` ajusta el modelo con `fit_model` como si el objetivo fuera 2025-26 (entrena 2023-24 y 2024-25) y lo puntúa en 2025-26 a la misma rejilla de umbrales
(IC 98,75 % por fechas, Bonferroni sobre 4). Regla: se activa si gana a la ley cruda con cota superior < 0, pendiente en [0,9; 1,1] e |intercepto| ≤ 0,10.

| Suma | Unidades | Brier crudo → vivo | Diferencia (IC 98,75 %) | Pendiente | Intercepto | Sesgo |
| --- | --- | --- | --- | --- | --- | --- |
| Puntos + rebotes | 172.315 | 0,2368 → 0,2288 | −0,0080 [−0,0093; −0,0067] | 0,60 → 0,98 | −0,166 → −0,024 | +0,039 → +0,005 |
| Puntos + asistencias | 171.075 | 0,2346 → 0,2260 | −0,0086 [−0,0098; −0,0073] | 0,62 → 0,99 | −0,195 → −0,021 | +0,046 → +0,004 |
| Rebotes + asistencias | 166.083 | 0,1924 → 0,1901 | −0,0023 [−0,0033; −0,0016] | 0,85 → 1,01 | −0,116 → −0,047 | +0,018 → +0,009 |
| Puntos + rebotes + asistencias | 172.914 | 0,2402 → 0,2317 | −0,0085 [−0,0101; −0,0071] | 0,58 → 0,98 | −0,159 → −0,025 | +0,039 → +0,005 |

**Las cuatro cumplen la regla y quedan activadas.** Los pesos más grandes son los minutos perdidos de los compañeros (+0,17 a +0,20) y el estado Questionable/Doubtful (−0,06 a −0,14).

## Modelo candidato y comprobaciones
Se ajustó un modelo de verificación (`apps/nba/.local/normalized/nba_f6_live13_model_20261024/model.json`) con los mismos insumos que el modelo desplegado
(`players`, `games`, reportes y API con hashes idénticos). Comparado con `nba_f6_live13_model_20261023`:
- `fit` del modelo de equipo, `play_probability`, `observed_share`, temporadas y peso empírico: **idénticos**.
- Pesos y muestras de puntos, rebotes y asistencias: **idénticos**. Solo cambian el hash del módulo y del protocolo, y se añaden las cuatro sumas
  (343.541 / 341.078 / 331.052 / 344.769 muestras de rejilla).
- Pruebas: suite NBA completa en verde (incluye 6 nuevas del productor y 3 del chequeo).

**Ese modelo no es el que se despliega.** El productor se niega a sellar con un modelo ajustado por otro módulo (`live_module_sha256`), y el módulo fusionado en `main` tiene
otros saltos de línea que el de la prueba. Al desplegar hay que ajustar el modelo con el módulo exacto de `main` y repetir las comprobaciones de arriba:
```bash
python -m nba.multimarket_v13_live fit --output apps/nba/.local/normalized/nba_f6_live13_model_<fecha>   --data apps/nba/.local/normalized/nba_f6_run71_20261009/data   --injuries apps/nba/.local/normalized/nba_complete_injury_final_20261006/reports.jsonl.gz   --api-dir apps/nba/.local/raw/api_nba_20261006
```
Cuatro condiciones: `fit`, `play_probability`, `observed_share` y `train_seasons` iguales al modelo desplegado; los pesos de `player_points`, `player_rebounds` y `player_assists` iguales;
las cuatro sumas presentes; y los hashes de insumos iguales salvo `live_module_sha256` y `protocol_sha256`.

## Límites
- No hay líneas históricas de casas para las sumas: el chequeo es contra resultados a umbrales estadísticos. La prueba real es el registro prospectivo que empieza al desplegar.
- Una sola recalibración logística para toda la rejilla deja un sesgo residual según la distancia al centro: de −0,02 a −0,04 a −4 de la media de 10 y de +0,03 a +0,05 a +4 (el crudo tenía +0,02 a +0,08 a −4 y ≈ 0 a +4). Es menor en conjunto, pero no nulo.
- Solo entra la disponibilidad; las variables de entorno (hándicap, total, ritmo, defensa rival, minutos recientes) mejoran más en la corrida retrospectiva pero no están disponibles en el productor al sellar.
- Robos, tapones, pérdidas, triples y doble-doble **no** entran: las filas de box score vivas solo traen minutos, puntos, rebotes y asistencias. Requiere ampliar el lector del box score (siguiente paso).

## Despliegue (NO ejecutado; espera confirmación)
Requisitos (`DEPLOYS.md`): PR fusionado en `main`; una sola sesión desplegando; comparar lo que corre en el servidor con `main` antes de sobrescribir; anotar la entrada con su vuelta atrás.
**Orden: primero el panel, después el productor.** El panel nuevo lee las cohortes 1.3.1 y las 1.3.2; el panel actual (1.3.1) rechaza una cohorte que contenga un mercado que no conoce (`ValueError` en `LiveCohort.load`).

```bash
ssh quantfut
L=$HOME/nba-isolated/live13
# 0. respaldos
crontab -l > $L/crontab.before-20261024-combos
cp -a $L/model $L/model.before-20261024-combos && cp -a $L/producer.sh $L/producer.sh.before-20261024-combos
# 1. PANEL: contexto desde main con git archive y core.autocrlf=false (src/nba y web); misma receta que la entrada del 24-oct de DEPLOYS.md;
#    imagen nueva nba-dashboard-live13:<fecha>, sustituir el contenedor guardando el anterior (docker rename) para volver atrás.
#    Comprobar /nba/api/data: live_v13 ok, 0 problemas, las cohortes 1.3.1 y RUN071 intactas.
# 2. PRODUCTOR: contexto desde main (+ propline_shared.py de main), imagen nba-live13-producer:<fecha>;
#    modelo ajustado con el módulo de main (comando de arriba) y comprobado contra el desplegado, copiado a $L/model/model.json;
#    producer.sh apuntando a la imagen nueva.
install -m 755 $L/build-producer/ops/live13_producer.sh $L/producer.sh
```
Primera pasada: cohorte con `version = nba-multimarket-live-1.3.2`, `prop_lines.state = archivo_aplicado`, pronósticos de las sumas cuando haya líneas
(`player_lines` sin `market_not_in_model`), panel con las cuatro pestañas nuevas (P+R, P+A, R+A, P+R+A) y los pronósticos sellados antes del salto. Las sumas aparecen más cerca del partido porque las casas publican los props el mismo día.

**Vuelta atrás:** primero el productor: `cp $L/producer.sh.before-20261024-combos $L/producer.sh; rm -r $L/model && cp -a $L/model.before-20261024-combos $L/model`
(la imagen `nba-live13-producer:20261023` sigue en el servidor). **El panel nuevo se queda** porque lee ambas versiones. Las cohortes 1.3.2 ya selladas no se tocan.
Solo si hubiera que revertir también el panel, hacerlo después de que no se haya sellado ninguna cohorte con sumas en las últimas horas: el panel 1.3.1 las rechazará y quedarán
fuera de la página (los archivos sellados siguen intactos y vuelven a verse al restaurar el panel nuevo).

## Pendiente
- Decisión del titular para desplegar (fecha y ventana).
- Ampliar el lector del box score vivo con robos, tapones y pérdidas para llevar esos mercados y el doble-doble, ya calibrados en la corrida retrospectiva.
- Mantener los parámetros de las variables de entorno solo como referencia hasta que el productor pueda leerlas al sellar.
