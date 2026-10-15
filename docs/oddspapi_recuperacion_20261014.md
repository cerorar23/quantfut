# OddsPapi: resultado de la recuperación

La carga posterior, autorizada el 15-oct, incorporó 2.918 cierres reconstruidos
y conservó 25 referencias para revisión. Quedan 3.267 cierres pendientes en la
base. Ver [informe de carga](oddspapi_carga_20261015.md). Los recuentos siguientes
describen la recuperación antes de esa carga.

## Resultado final — 15-oct-2026

La cola terminó a las 03:45:56, hora de Ciudad de México; la exportación final
quedó a las 03:45:59. Se consultaron los 6.094 eventos asociados: 2.943 aportaron
una terna prepartido y 3.151 devolvieron sin histórico. De las 6.185 filas originales,
87 no tienen fixture en el índice y cuatro están canceladas en la fuente: quedan
3.242 sin recuperar con esta API. No hay consultas pendientes en esta cola.

Las 2.943 ternas son cierres reconstruidos, no certificados oficialmente;
2.920 tienen calidad `recent` y 23 requieren revisión. Se verificaron unicidad,
las tres cuotas, timestamps estrictamente anteriores al corte y correspondencia
del hash de origen con los recibos. El CSV original permanece intacto. No hubo
carga automática en producción. Los avisos periódicos se desactivan al finalizar.

Lo siguiente conserva el contexto y las decisiones del inicio del trabajo.

El usuario autorizó utilizar su clave para recuperar los cierres pendientes.
La cuenta responde, incluye Pinnacle y tiene plan gratuito con 250 consultas.
No se ha comprado ni modificado el plan.

Se descargó el catálogo y el calendario desde 2024 para las 23 competiciones,
incluidos los torneos separados de apertura/clausura de México. La asociación
inicial dio 4.983 partidos; tras revisar 48 equivalencias explícitas con los
equipos existentes, son 6.094 de 6.185. Las equivalencias se conservan con evidencia;
no se usan asociaciones difusas ni se crean equipos o partidos.

Las 91 filas restantes son 87 partidos de 2024 que no aparecen en los calendarios
consultados y cuatro de 2026 cuyo estado en OddsPapi es cancelado: Nantes–Toulouse,
Bastia–Le Mans, Sparta–NEC y Utrecht–Go Ahead Eagles. Se excluyen de la cola, con
su discrepancia explícita. No se corrigen sus resultados o fechas en producción.

El primer lote de 50 eventos, más un sondeo asociado anterior, produjo **51 ternas
Pinnacle prepartido** con calidad `recent`. Los sondeos United–City del 17-ene,
Liverpool–Newcastle del 31-ene y Brentford–Arsenal del 12-feb de 2026 devolvieron 404
(consultar sus originales para las identidades exactas); no se generaliza esa
ausencia a todos los partidos de esos meses.

Se deja una descarga continua de los 6.094 asociados, empezando por los recientes.
Por el intervalo obligatorio de cinco segundos y el tamaño de las respuestas,
el trabajo requiere varias horas. El cierre del lote se registra en el estado del
proceso; este informe no afirma que la lista ya esté completa.

## Método y límites

El histórico contiene también cuotas en vivo, incluso con una suscripción sin
cuotas en vivo en el endpoint corriente. Se usa únicamente Pinnacle, mercado
101, resultados 101/102/103, jugador 0; la última cuota no suspendida y anterior
al menor del inicio programado/real. `active=null` se permite siguiendo el ejemplo
del proveedor. No se toma la última fila sin filtrar ni se reemplazan cuotas por
las de otras casas. Se conservan diferencias de horario entre nuestra base y la fuente.

El proveedor describe este método como extracción del cierre, pero v4 no entrega
una etiqueta explícita de cierre oficial. Se registra como reconstrucción y
`close_verified=False`; no se carga automáticamente en `odds_snapshots` ni se
entrena el modelo. El ensayo y cualquier importación futura deben volver a
comprobar el estado actual de producción, respaldar y evitar cierres ya completos.

## Entrega y reproducción

CSV y recuento actualizados: `data/pinnacle_recovery/20261014_oddspapi/`.
Originales, recibos, credencial cifrada y registros del proceso:
`.local/oddspapi_20261014/`. El estado usa `running`, `completed` o `failed`;
`completed` significa que se recorrió la cola, no que todos tengan histórico.

Recolector: `scripts/recover_oddspapi_closes.py` (`index`, `match`, `run`, `report`).
La clave se pasa exclusivamente mediante `ODDSPAPI_API_KEY`. Las acciones `match`
y `report` no consultan la API; `run` reutiliza los recibos ya archivados y el
lanzador local recupera la credencial por DPAPI sin ponerla en la línea de comandos.
La entrega se refresca cada veinte eventos y al finalizar. No arrancar otra instancia
sobre la misma carpeta; hay bloqueo del sistema y los errores persistentes preservan
el último avance. No mostrar cuerpos completos de `/account`, que contienen datos
personales y la clave.

Las pruebas cubren exclusión de precios en vivo y suspendidos, cortes de inicio,
marcas horarias con desplazamiento, ternas incompletas, casa/mercado incorrectos,
integridad de originales al reanudar y asociaciones ambiguas.

Fuentes oficiales:
[histórico](https://oddspapi.io/us/docs/get-historical-odds),
[cupo](https://oddspapi.io/us/docs/requests-and-quota),
[extracción del cierre](https://oddspapi.io/blog/team-ratings-from-closing-odds/).
