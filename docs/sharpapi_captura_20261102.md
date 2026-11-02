# Captura de SharpAPI (plan Free) — 2-nov-2026

Autorizada por el titular el 2-nov-2026. Cubre los mercados de fútbol que PropLine no trae. Código: `scripts/sharpapi_captura.py`
(solo biblioteca estándar, como `propline_captura.py`); pruebas: `tests/test_sharpapi_captura.py`.

## Qué es el plan Free (medido el 1-nov con `/account`)
- Una clave, **12 peticiones por minuto**, **2 casas** (DraftKings y FanDuel), retraso de 60 s, **sin histórico ni cierres**.
- Por eso la única forma de tener cuotas de estos mercados es capturarlas hacia adelante, a los momentos que interesan.

## Qué captura
Cada 5 minutos (cron del usuario `qf`, con `flock`) una pasada:
1. `GET /events?sport=soccer&league=<9 ligas>&status=upcoming` (2 peticiones, 256 eventos). Se quedan los partidos con equipos y con
   DraftKings o FanDuel que empiezan en las próximas 26 h (hoy 8; ≈ 10-15 al día).
2. Para cada uno, los momentos **24 h, 6 h, 2 h, 60 min y 15 min** antes del saque: el primero que ya pasó se captura una sola vez y
   los anteriores se dan por hechos (un partido visto por primera vez a 100 min deja hechos 24 h, 6 h y 2 h).
3. `GET /odds?event_id=…&sportsbook=draftkings,fanduel&is_live=false&limit=200` con cursor hasta agotar las páginas: **todas** las
   cuotas prepartido del partido (medido: 1.676 filas, 58 mercados, 9 páginas, 11 peticiones, 16 KB comprimidos por captura).
   Mercados: descanso/final, marcador exacto (partido y mitades), primer equipo en marcar, goleadores (cualquier momento, primero,
   último, por mitad), tiros y tiros a puerta de jugador, faltas cometidas y recibidas, córners por mitad y hándicap de córners,
   tiros y faltas por equipo, goles por mitad, ambos marcan por mitad, goles exactos, margen de victoria, etc.

Consumo: ≈ 5 capturas × 11 peticiones por partido ≈ 55 peticiones por partido y ≈ 0,5-0,8 MB comprimidos al día.

## Dónde queda
- Servidor: `~/sharpapi/` (script, `.env` con la clave en modo 600, `captura.log`) y `~/sharpapi_data/AAAA-MM-DD/<evento>/<capturado>.jsonl.gz`.
- Cada archivo: primera línea = cabecera (`capturado` con la hora real de recepción, `mins_al_saque`, `momentos`, `paginas`, `filas`);
  después una fila compacta por cuota (casa, mercado, segmento, selección, línea, cuota decimal, marca de tiempo de la casa, jugador…).
- Estado de lo ya capturado: `~/sharpapi_data/estado.json`.
- **No se carga en la base**: los originales son archivos; cargarlos (p. ej. en `futbol.cuota_historica`, con `fuente = 'sharpapi'`) es un
  paso aparte cuando haya semanas de datos.

## Términos (SharpAPI, cláusulas 5.1-5.4)
Uso interno (análisis, modelado) y mostrar cuotas en la propia app con suscripción activa; desde el **1-dic-2026** hay que poner
«Data provided by SharpAPI» (con enlace a sharpapi.io) en cualquier pantalla que muestre cuotas de SharpAPI; no se redistribuyen datos en
bruto ni se ofrece la comparación de casas como producto. La cláusula 5.3 habla de datos recibidos «durante una suscripción activa»: no
queda claro si el plan gratuito cuenta; dudas a legal@sharpapi.io.

## Operación
- Ver una pasada: `ssh quantfut 'tail -20 ~/sharpapi/captura.log'`.
- En seco (2 peticiones): `cd ~ && python3 sharpapi/sharpapi_captura.py --env sharpapi/.env --out sharpapi_data --seco`.
- Parar: quitar la línea `# sharpapi-captura` del crontab. Copia del crontab anterior: `~/backups/crontab-antes-sharpapi-20261102.txt`.
- Si la clave deja de valer el script sale con «clave rechazada (HTTP 401/403)» en el registro.
