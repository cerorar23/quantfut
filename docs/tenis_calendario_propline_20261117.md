# Tenis v2: calendario desde el archivo de PropLine (17-nov-2026)

Pedido del titular tras el despliegue del motor con el filtro real: `tenis-db` solo recibía TML semanal y `tenis.programa` no tenía partidos
futuros, así que el motor nunca tenía qué pronosticar.

## Fuente

El archivo compartido de PropLine (`docs/propline_compartido_20261023.md`): el recolector horario (minuto 7) ya guarda `/v1/sports/tennis/odds`.
El colector **no hace peticiones** a PropLine: un extractor (`ops/exportar_calendario_propline.py`) corre dentro del worker, que ya monta el archivo, y
entrega un documento JSON con la recepción real del lote, su huella y los eventos. Un contenedor de la imagen del motor lo carga
(`python -m tenis.captura.propline_calendario --stdin`). `ops/calendario_propline.sh` encadena los dos y usa la imagen que fija `ejecutar_motor.sh`.
Cron propuesto: minuto 12 de cada hora con `flock` (`ops/cron_tenis.txt`).

## Qué carga y qué no (nunca se inventa nada)

PropLine mezcla ITF, UTR, dobles, Challenger y tour; de 518 eventos reales (17-nov 22:07 UTC) solo 67 son candidatos del modelo.

| Se carga | Se descarta (con su contador) |
|---|---|
| Individuales ATP, WTA y Challenger, a menos de 72 h y a más de 5 min de empezar | ITF, UTR, dobles, en vivo, ya empezados, Grand Slam (la ronda no viene y decide el formato), Next Gen, clasificatorios, Copa Davis, United Cup, exhibiciones |

- **Torneo y superficie.** PropLine no da superficie. El torneo se reconoce por su **ciudad** entre los torneos que TML ya conoce del mismo circuito, con una semana
  parecida (≤ 10 días) a la de sus ediciones de los últimos 3 años; la superficie y el indoor se copian de su edición más reciente. Un Challenger no se resuelve
  contra un torneo de gira con categoría (Metz es ATP 250 en TML) y la categoría vacía de TML (el nivel cambió entre años, p. ej. Montevideo) vale para ambos.
  Las Finales se reconocen por la palabra. Torneo desconocido, fuera de calendario o ambiguo (misma ciudad con superficies distintas) → `sin_resolver`.
- **Jugadores.** Solo coincidencia **exacta** de nombre dentro del circuito y única (`ResolutorMultifuente.buscar_exacto`). Nunca se crea un jugador.
- **Ronda** desconocida (`R`), mejor de 3.
- **Provenance y visibilidad.** Cada archivo es un `recibo` (`retro = false`, `recibido_en` = recepción real del lote): el dato es visible solo desde entonces.
  Edición (fuente `propline`), partido, programa y enlace del evento. Idempotente: el cursor guarda la huella del documento; un horario nuevo añade
  otra fila de `programa` (el motor usa la última); `sin_resolver` no repite.

## Cambios en lo ya validado

- **Exportación PIT** (`datos/exportar_pit.py`): `propline` pasa a ser fuente de calendario con hora real, tratada igual que SofaScore (`FUENTES_CON_HORA`).
  Sin filas de PropLine el resultado es idéntico (las pruebas de la puerta oficial pasan). En la exportación `fuente_tiempo = "sofascore"` significa «con hora real».
- **Motor** (`motor.buscar_partidos_pendientes`): usa el último horario de cada partido y solo los que no empezaron o empezaron hace menos de 45 min. Antes un partido
  con dos horarios aparecía dos veces y uno perdido se avisaba como sello tardío en cada pasada para siempre.

## Medido con datos reales (base local `tenis_dev`, sin escribir)

De 67 candidatos: 35 se resuelven (Sydney, Drummondville, Kobe…), 30 `torneo_sin_historial` y 2 `jugador_sin_resolver`. Sin historial son los torneos que TML no tiene:
Champaign, Colina (WTA 125), Metz (en TML es un ATP 250) y Montevideo, este último ya corregido por la categoría vacía. La cobertura crecerá cuando TML cargue la semana nueva
(los lunes) y se cubrirá a mano lo que falte con una tabla de alias si hace falta.

## Límites

- Sin ronda ni cuadro: no hay segmentación por ronda.
- Cuando TML cargue esos partidos (lunes siguiente) habrá dos filas del mismo partido real (la de PropLine sin resultado y la de TML); la de PropLine no genera evento
  de resultado, así que el filtro no cuenta el partido dos veces. Pueden salir como «posibles duplicados no fusionados» en la calidad de la exportación.
- Cada pasada del motor con partidos en ventana cuesta ≈ 5 min y 4,4 GB (lectura completa de la base): con partidos casi continuos en el circuito mundial, el motor
  trabajará casi todas las pasadas. Guardar el estado del filtro (plan H.2) es el siguiente paso si molesta.
- Las alertas del motor solo se registran en el log del contenedor: `ejecutar_motor.sh` no pasa `TG_BOT_TOKEN`/`TG_ALERT_CHAT`.
