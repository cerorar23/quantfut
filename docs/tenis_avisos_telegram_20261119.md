# Tenis v2: avisos operativos a Telegram (19-nov-2026)

Pedido del titular: terminar los pendientes. Los avisos del motor solo se registraban en el log del contenedor.

## Que fallaba (tres huecos, no uno)

1. `ejecutar_motor.sh` no pasaba `TG_BOT_TOKEN` ni `TG_ALERT_CHAT` al contenedor, asi que `enviar_alerta` caia siempre en «Telegram no configurado».
2. La deduplicacion («una alerta por tipo, partido y dia») vivia en memoria y cada pasada es un proceso nuevo: con Telegram conectado el mismo aviso se habria repetido cada 30 minutos.
3. `salud.py` (cadena de hashes rota, calendario parado, artefacto distinto del activo) **no estaba en ningun cron**: esos avisos nunca habrian salido. Su script usaba ademas la imagen vieja.

## Que cambia

- **Estado persistente** (`alertas.cargar_estado/guardar_estado`, variable `TENIS_ESTADO_ALERTAS`, fichero `/almacen/estado_alertas.json`): se carga al arrancar, se guarda de forma atomica
  tras cada aviso y solo recuerda 3 dias. Fichero ausente o corrupto = empieza vacio, sin error.
- **Menos ruido del motor** (`motor.py`):
  - `sello_tardio` solo avisa si el horario se conocia con tiempo para sellar (`programa_visto_desde` <= corte). Con el horario recibido menos de 60 min antes del corte el partido nunca pudo
    sellarse y avisar de cada uno seria ruido (el resultado lleva `evitable: false`).
  - Los motivos de omision normales (`excluido_o_equipos`, `superficie_desconocida`, `formato_desconocido`, `fuera_de_la_exportacion`) van al log; si avisan `jugador_sin_historia`, `sin_pronostico`,
    `inferencia_fallida`, `contrato_roto` y `motor_fallido`.
- **Salud** (`salud.py`, `python -m tenis.salud`): nuevo chequeo del calendario (el ultimo recibo de PropLine no debe pasar de 3 h → `colector_parado`), el artefacto activo se compara con
  una carpeta de artefactos (la imagen lleva varios) y el programa sale con codigo 1 si algo no esta bien. `ops/verificar_salud.sh` + cron cada hora (minuto 40).
- `ops/ejecutar_motor.sh.plantilla`: el motor llama a `python -m tenis.motor` (resumen JSON y codigo de salida) con las credenciales por entorno.

## Limites

- Hay un aviso por tipo, partido y dia como maximo; el estado se pierde si se borra el fichero del almacen (entonces avisaria una vez mas).
- La frescura general de recibos (36 h) sigue existiendo, pero con el calendario cada hora ya casi no puede saltar; el chequeo util es el del calendario.
- Un fallo de la red a Telegram se registra como enviado (no reintenta), igual que antes.
