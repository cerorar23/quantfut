# NBA — auditoría del motor de predicción (21-oct-2026)

Alcance: `apps/nba/src/nba/multimarket.py` (v1.1, RUN071), `multimarket_v12.py`, `availability.py`,
`multimarket_v13.py`, `multimarket_v13_live.py`, el modelo de rebotes (`model.py`) y sus protocolos.
Todo se midió sobre los datos ya descargados (`nba_f6_run71_20261009/data`, 816 reportes de lesiones),
sin gastar créditos ni tocar RUN071 ni el VPS. Suite NBA verde antes y después; arnés verde.

## Lo que está bien (no tocar)

- Disciplina punto-en-el-tiempo: cada fecha se pronostica antes de incorporar sus resultados; ventanas de
  370 días, protocolos congelados antes de correr, sellos con hash y regla T-60 en vivo.
- Comparaciones justas (misma calibración para candidato y referencia), bootstrap por fechas desde v1.2.
- La varianza Gamma-Poisson con minutos aleatorios está bien derivada.
- Los límites se documentan con honestidad (exploratorio, sin cuotas, sin CLV).

## Hallazgos, por gravedad

### 1. Alta — las bajas largas se cuentan dos veces (v1.3, retrospectivo y en vivo)
`availability.trailing_entries` valora a cada jugador listado con su media de las últimas 20 apariciones
(hasta 370 días), pero la forma del equipo (media de sus últimos 20 partidos) y el Elo **ya reflejan** esas
ausencias. Medido sobre las 24.093 entradas «Out» del histórico:

- de media, el jugador «Out» solo había jugado el 37,5 % de los últimos 20 partidos de su equipo;
- el 63 % ya se había perdido la mitad o más; el 18,5 % no había jugado ninguno;
- el **52 % de los «puntos esperados perdidos»** viene de jugadores cuya baja ya estaba en la forma.

Consecuencia: el coeficiente aprendido queda diluido (−0,66 puntos de equipo por cada 10 puntos perdidos;
una estrella de 25 puntos vale solo −1,7) y en vivo se suman bajas ya descontadas. En la cohorte de ensayo
del 21-oct, Jimmy Butler (último partido 19-ene-2026) resta 19,9 puntos a Golden State, cuyos 20 partidos
de referencia ya se jugaron sin él.

**Arreglo:** puntos perdidos = valor del jugador × (fracción jugada en la ventana de forma − probabilidad de
jugar hoy). Una baja ya incorporada aporta ~0; un regreso aporta valor positivo (hoy se ignora).

### 2. Alta — «Available» resta minutos que no se pierden
La tabla da 68-75 % de participación a «Available». El 17 % de esas filas son `G League - Two-Way` / `On
Assignment` (497 de 3.009), que mezclan dos poblaciones. Efecto en vivo: un jugador «Available» de 14 puntos
resta 2,9 puntos esperados a su equipo (Walker Kessler en el ensayo).
**Arreglo:** separar el motivo (asignación G League vs. lesión) antes de la tabla; «Available» por lesión ≈ 1.

### 3. Media — distinto momento del reporte entre entrenamiento y vivo
El histórico tiene **un solo reporte por día** (486 a las 13:00-13:45 ET, 330 a las 17:30 ET); en vivo se usa
el último ≥60 min antes del salto (p. ej. 18:15). «Questionable» a las 13:30 no tiene la misma tasa de juego
que a las 18:15, pero la tabla (≈48 %) es una sola. Además `play_table` cuenta como «no jugó» a quien no tiene
fila de box score, mientras `availability_scores` las salta: se estima y se evalúa sobre poblaciones distintas.
**Arreglo:** descargar el reporte más cercano a T-60 para cada día del histórico (los PDF son públicos y
cuestan 0 créditos) y condicionar la tabla a las horas antes del salto.

### 4. Media — puntos de jugador demasiado seguros
La calibración de RUN071 necesita pendiente 0,42 en puntos (0,64 rebotes, 0,74 asistencias): el modelo es
mucho más extremo que la realidad. El rango 80 % que se muestra sale de la pmf sin calibrar y en puntos
cubre solo el **73 %** (muestra de 3.978 apariciones 2024-26). Causa: los puntos llegan de 1, 2 y 3 en 3 y un
Poisson por minuto subestima la varianza en ≈2,3×.
**Arreglo:** modelar puntos como 2P/3P/TL (o binomial negativa con dispersión ajustada por estadística) y
derivar los rangos de la distribución calibrada.

### 5. Media — mercados incoherentes entre sí
El ganador sale del Elo y los puntos de equipo de medias móviles sin ajuste de rival. Discrepan >10 puntos
porcentuales en el 18-20 % de los partidos (la página puede dar favorito a quien proyecta menos puntos). El
margen de puntos solo predice peor (Brier 0,207 vs 0,201-0,204) y promediarlo no ayuda: lo débil es la forma.
**Arreglo:** ratings de ataque/defensa ajustados por rival y ritmo (ridge con decaimiento o filtro de Kalman,
como `src/qf/model/kalman.py` en fútbol) y derivar ganador, puntos y total de una sola distribución del marcador.

### 6. Media — arranque de temporada (la cohorte en vivo está justo aquí)
Brier del ganador en oct-nov: 0,217 / 0,214 / 0,207 frente a 0,209 / 0,201 / 0,199 el resto de la temporada.
La forma de octubre son los 20 últimos partidos de la temporada anterior (abril: descansos y tanking) y el Elo
solo regresa un 25 %. Los traspasos del verano solo entran vía reporte de lesiones.
**Arreglo:** prior de pretemporada (plantilla nueva por minutos esperados o total de victorias de mercado) que
pese más en los primeros 15-20 partidos; excluir de la forma los últimos ~10 días de la regular anterior.

### 7. Media — la operación en vivo no escala
`completed()` vuelve a descargar todos los box scores de la temporada en cada cohorte: ~1.200 páginas por
ejecución en abril, riesgo de bloqueo de nba.com. Un partido no final se salta en silencio y desplaza el
cálculo de descanso. Además el valor de los jugadores queda congelado en 2025-26 (no se añaden los box
scores de 2026-27).
**Arreglo:** caché por partido con hash (solo descargar lo nuevo), fallo explícito si un partido de un día ya
pasado no está final, y añadir filas de jugador de 2026-27 a la historia de disponibilidad.

### 8. Baja — rigor y lectura de resultados
- Las líneas `floor(media10)+0,5` no son de casas: el «acierto ≥70 %» premia estadísticas raras (tapones,
  robos) y no dice nada frente al mercado. Brier del total 0,231-0,244: casi sin señal sobre esa línea.
- 9 mercados × 3 temporadas sin corrección por comparaciones múltiples; las temporadas de test ya se vieron.
- Descanso solo como back-to-back: faltan 3 en 4 noches, viajes/zona horaria y altitud (Denver, Utah).
- Elo K=20 y ventaja 65 vienen de 538, no se ajustaron.
- La regresión por temporada se activa con `games[-1]['season']`; si una cohorte mezclase temporadas (no
  ocurre hoy) fallaría en silencio.

## Orden recomendado

1. Arreglar 1 y 2 en una v1.4 con protocolo congelado; re-evaluar contra v1.3 en 2024-25/2025-26. Es lo que
   más mueve el ganador y los puntos de equipo, y afecta ya a lo que se sella en vivo.
2. Backfill de reportes T-60 (punto 3): gratis y quita el desajuste entrenamiento/vivo.
3. Caché de `completed()` antes de desplegar el productor diario (punto 7).
4. Desde el 1-nov, cuotas históricas h2h: **la prueba que falta** es Brier y CLV contra Pinnacle sin margen.
   Orientativo, sin verificar con datos propios: el cierre NBA suele rondar Brier ~0,195-0,200; v1.3 está en
   0,201-0,204. Hasta
   tener esa comparación no hay base para vender ningún mercado NBA.
5. Ratings ajustados por rival/ritmo y distribución conjunta del marcador (punto 5), prior de pretemporada
   (punto 6).
6. Props de jugador (punto 4) solo después: sin lista de quién juega antes del salto no se pueden sellar.
