# Despliegue del rediseño QuantFut

7 de octubre de 2026. Commit de producto:
`2266311fae293371a44bab4141a40812cbf337e9`.
Publicado por autorización explícita del usuario en
[pronosticosdeportivos.pro](https://pronosticosdeportivos.pro/#planes).

## Alcance ejecutado

El servidor no contiene un repositorio Git. Se transfirió un paquete generado
desde el commit local y se verificó la base de los archivos antes de reemplazar
seis archivos: portada, estilos, aplicación, módulo de membresía, sus estilos
y rutas estáticas de FastAPI. Los archivos de referencia SingleFile, secretos,
cachés y trabajos NBA pendientes quedaron fuera del paquete y del commit.

La imagen nueva deriva de la imagen API que estaba ejecutándose, incorporando
solo estos archivos. Se actualizó exclusivamente el servicio `api` con
`--no-deps --no-build`. Los identificadores de worker, base de datos, caché,
proxy y Grafana permanecieron iguales. No se modificaron variables de entorno,
gates, base de datos, modelo o procesos de predicción.

La sesión, el registro, la recuperación y los pedidos siguen siendo una demo
con identidad sintética. Elegir un plan no activa derechos; el cobro permanece
deshabilitado. Publicar el diseño no integra autenticación o pagos reales.

## Respaldo y trazabilidad

- Paquete: `/home/qf/web-2266311.tar.gz`.
- SHA-256 del paquete:
  `30687c9c117ad0184110a5322a7d4c0dc4b0ec8876c043bdfc81b384b7b6a232`.
- Copia previa: `/home/qf/web-release-2266311/backup`.
- Imagen previa preservada: `quantfut-api:web-before-2266311`.
- Imagen nueva: `quantfut-api:web-2266311`.
- Comprobante del servidor: `/home/qf/web-release-2266311/deployed.json`.
- Copias locales del comprobante y capturas: `.local/design-reference/`, ignorada.

Para una reversión, se restauran los archivos de `backup`, se vuelve a etiquetar
la imagen previa como `quantfut-api:latest` y se recrea únicamente `api`.
No es necesario restaurar bases de datos o reiniciar el worker.

## Verificación

- Arnés completo: 732 pruebas aprobadas y una advertencia de dependencia.
  Se ejecutó Git Bash con sus utilidades en PATH; la omisión de pruebas del
  entorno restringido de la fase anterior queda resuelta para este despliegue.
- Frontend: 13 pruebas aprobadas.
- API desplegada: `/health` devuelve `status: ok`; hashes exactos de los cinco
  archivos frontend publicados comparados con el paquete del commit.
- Navegador desde el dominio público: suscripciones, acceso demo, revisión del
  pedido con cobro deshabilitado y cuenta con «Sin suscripción activa».
- Cloudflare incorpora un beacon público de analítica al HTML. La comparación
  externa del HTML elimina únicamente ese elemento conocido para verificar
  el resto del documento; los otros archivos se comparan sin normalización.

El commit se creó localmente. No existe un remoto Git configurado para un push;
el despliegue al servidor se realizó por SSH con paquete y comprobante.
