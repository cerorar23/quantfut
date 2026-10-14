# Respaldo y cotejo con PitchAPI: despliegue

14-oct-2026, por orden del titular ("la clave en el backend, que corra en
automático"). Diseño en `harness/tareas.md`; código en
`src/qf/ingest/pitchapi_respaldo.py` y `src/qf/api/respaldo.py`.

## Qué quedó en producción

- Migraciones `db/065` y `db/066` aplicadas: 23 ligas con `pitchapi_id`, 496
  equivalencias de clubes, ajustes, discrepancias y originales.
- Clave de PitchAPI guardada **cifrada** (AES-256-GCM, `QF_SECRETS_KEY`) en
  `pitchapi_settings` y respaldo **activado**; consta en `admin_audit`
  (`despliegue:claude`). Nunca vuelve a mostrarse: el panel solo enseña «termina
  en …». Se rota o se borra desde `/control/respaldo`.
- Cron del worker, 12:40 UTC diario, tras el xG de API-Football de las 12:10.
  Se actualizó `scripts/crontab` del host en el mismo archivo y se recargó con
  `crontab /etc/cron.d/quantfut` sin reiniciar el worker.
- Panel `/control/respaldo` en la API, con entrada de menú «Respaldo PitchAPI».
  Solo se recreó el servicio `api` (`--no-deps --no-build`).
- Primera pasada real: conexión correcta (77 ligas visibles), 11 días, 0
  discrepancias, 8 votos de equipos nuevos, 0 xG elegibles. Página del panel
  comprobada con datos reales: 200, sin la clave en el HTML.

## Cómo se desplegó

El servidor no tiene Git. Archivos extraídos del commit y comparados antes de
reemplazar: `main.py` y `panel.py` de la API eran idénticos a la versión previa
del repo; `base.html` de producción tenía «Sistema y modelo» al final del menú,
así que se parcheó sobre él y el repo se alineó con lo desplegado.

Imágenes derivadas de las que corrían, solo con los archivos nuevos:

| Servicio | Imagen nueva | Imagen previa (reversión) |
| --- | --- | --- |
| api | `quantfut-api-tapjoy:20261014-pitchapi` | `quantfut-api-tapjoy:before-pitchapi-20261014` |
| worker | `quantfut-worker:latest` | `quantfut-worker:before-pitchapi-20261014` |

El worker no tenía el paquete `cryptography` ni `comercial/cifrado.py` (imagen
anterior a las claves cifradas): se añadió `cryptography==50.0.2`, la versión
que fija `requirements.txt` y que ya usa la API, además de `cifrado.py`. El
contenedor del worker en marcha se actualizó en caliente y no se reinició.

Copias previas y paquetes: `/home/qf/pitchapi-deploy-20261014/`
(`backup/crontab.antes`, `backup/docker-compose.yml.antes`, `backup/api_files/`).

Reversión: restaurar `docker-compose.yml.antes` y recrear `api`; desactivar el
respaldo desde el panel (o quitar la línea del cron y recargarla). Las tablas
nuevas son aditivas y pueden quedarse.

## Pendiente

Pasar a una clave `pk_live_` (la `pk_test_` anterior se revocó sola el 14-oct) y
preguntar al proveedor por uso comercial y almacenamiento de datos.
