# Completar fútbol con soccerdata y ZenRows — 13 de octubre de 2026

El usuario sustituyó `tunjayoff/sofascore_scraper` por
[probberechts/soccerdata](https://github.com/probberechts/soccerdata), con
[su documentación](https://soccerdata.readthedocs.io/en/latest/) y el MCP de
ZenRows ya configurado. El scraper anterior quedó detenido; se reutilizan sus
respuestas públicas verificadas, no su código ni procesos.

## Fuentes y transporte

Fuente fijada: soccerdata 1.9.1, revisión
`e120471e424a173e83e8aeeaaf4d954ab9d38ee4`, licencia Apache-2.0 comprobada.
Dependencia optativa en `requirements-soccerdata.txt`, instalada en entorno
aislado de captura. La API y el worker no necesitan sus dependencias de navegador.

Los lectores conservan sus analizadores y configuración; el transporte se
subclasifica para ejecutar MCP `@zenrows/mcp@2.4.0`, con selección automática de
proxies y sin conexión deportiva directa ni navegador del paquete. Se utiliza
la ruta GB para SofaScore. Cada original lleva hash y recepción real; caché
verificada, errores conservados, máximo de consultas y reserva de 100 créditos.
No se compran créditos ni se cambia el plan. Se descuenta provisionalmente el
coste máximo de 25 por consulta porque la facturación puede aparecer con retraso.

El lector SofaScore de soccerdata 1.9.1 documenta calendario, temporadas y tabla.
Se amplía mediante `HistoricalSofascore` para últimos eventos y detalles de
estadísticas/XI; la normalización independiente valida torneo, país, categoría,
estado final, goles de 90 minutos, identidad de jugadores y recepción.
Las métricas ausentes siguen siendo NULL; no se infieren bajas exhaustivas.

FBref respondió, pero la página recuperada de competiciones solo contenía
tablas internacionales y el lector devolvió cero ligas domésticas seleccionadas.
Además, [Sports Reference anunció la retirada de datos avanzados el 20-ene-2026](https://www.sports-reference.com/blog/2026/01/fbref-stathead-data-update/).
No se atribuye xG a esa fuente. Las dos consultas ESPN para Chile/Brasil B
devolvieron errores mediante ZenRows; se conservan como fallos, no datos vacíos.

Los calendarios que fallaron con otra configuración se probaron una sola vez
con GB. Los errores de esa misma ruta se reutilizan sin reintentos. Esto permitió
recuperar Chile, LaLiga 2, Ligue 2 y Serie B; las respuestas anteriores válidas
de Championship se reutilizaron con su recepción original.

## Alcance y situación inicial

La tabla previa con cero xG/XI ya no describe la base después de importar FotMob:
22.456 originales, 1.554 partidos nuevos y 14.629 parejas xG incorporadas el
13-oct. Ver `importacion_fotmob_20261013.md`.

Instantánea actual: 22.606 partidos finalizados desde 2024 y 3.208 sin pareja xG.
Los grandes huecos están en 2024 y parte de 2025: LaLiga 2 723, Serie B 598,
Ligue 2 502, Brasil B 400 y Chile 667. Son conteos de partidos canónicos, no
conteos del archivo ni cuotas disponibles.

Muestra histórica 2023/24: LaLiga 2 y Ligue 2 devolvieron 30 eventos cada una,
ninguno anunciaba xG y la consulta estadística de un evento no contenía esa
métrica. Serie B devolvió 30 eventos sin xG anunciado, pero falló su consulta
estadística. Chile y Brasil B fallaron en esta muestra. Esto no demuestra que
todos los partidos históricos carezcan de xG; impide prometer cobertura completa
o lanzar miles de consultas como si la métrica estuviera disponible.

## Importación y evidencia

Carga completada y verificada el 13-oct a las 23:15 UTC (17:15 México).
586 originales de 17 competiciones: 574 asociados, 10 identidades de copas
pendientes y 2 conflictos en cuarentena. Se guardaron 138 XI de equipo, 2.789
registros de estadísticas de jugadores y 269 declaraciones históricas de bajas.
Hay 57 partidos con ambos XI completos. No son 586 partidos nuevos: los
resultados ya estaban cargados y se incorporaron originales y asociaciones.

De las 63 parejas xG recuperadas, 54 rellenaron huecos canónicos; siete ya tenían
xG y se conservaron sus valores, y dos pertenecen a originales sin asociación.
No se crearon clubes ni partidos canónicos; la única propuesta de partido nuevo
fue descartada tras la revisión descrita abajo. Cero cambios de conteos existentes.

| Liga | Parejas xG nuevas |
| --- | ---: |
| Championship | 11 |
| LaLiga 2 | 9 |
| Serie B (Italia) | 9 |
| Noruega | 7 |
| Turquía | 6 |
| Chile | 6 |
| Suiza | 5 |
| Brasil A | 1 |

Ligue 2 aporta XI/jugadores en esta carga, pero no xG. Brasil B, Bundesliga 2,
Dinamarca, Suecia y Europa League mantienen bloqueos de calendario en la ruta
probada. La muestra de 2024 tampoco acreditó xG completo. Siguen pendientes
3.154 partidos canónicos sin pareja xG: esta carga no completa toda la historia.
La disponibilidad de cada campo se registra separadamente de errores de acceso.

Se revisaron doce equivalencias de nombres de clubes domésticos con originales,
país, nombres alternativos y cotejo de fechas, adversarios y marcadores; no se
aceptó emparejamiento difuso. Los recibos y decisiones están en el plan revisado.
Troyes–Valenciennes del 3-may-2024 figura 1–1 en el original, pero la
[LFP declaró la derrota por penalización de Troyes](https://www.lfp.fr/article/commission-de-discipline-les-decisions-du-22-mai-2024).
Quedó como conflicto, sin crear un resultado ordinario 1–1. Catanzaro–Brescia
mantiene el conflicto entre el marcador de tiempo reglamentario del original
y el resultado existente; ninguno se sobrescribió.

Las observaciones utilizan `provider=sofascore`, IDs separados de API-Football
y FotMob, y las tablas históricas ya creadas por db/062. Solo se rellenan parejas
xG completamente vacías y conteos ausentes en partidos asociados de forma segura.
Los originales sin asociación se conservan con motivo; no se crean clubes en copas.

Antes de aplicar se recalculó cada registro contra su original y sus respuestas
HTTP. La prueba PostgreSQL repetida produjo cero escrituras adicionales y se
revirtió; después se hizo la carga atómica. Se cotejaron 22.615 registros previos,
586 hashes y la disponibilidad temporal de las 54 parejas incorporadas.
Modelo `2026.09.27-010508`, banderas, lotes sellados y tablas de jugadores/XI de
API-Football conservados. API interna y pública: HTTP 200, misma versión.
Worker respaldado antes de copiar dos módulos, sin reinicio ni reconstrucción
desde el checkout antiguo. Imagen con la ampliación persistida: `37785ec79111`.
Pruebas: 35 relevantes y arnés completo 1.033 aprobadas/24 omitidas, dos avisos.
XI/jugadores/bajas son observaciones históricas; adaptar sus consumidores queda
pendiente. El xG recibido ahora solo se usa desde esa recepción y no acredita
una mejora retrospectiva del entrenamiento.

Evidencia local: `.local/soccerdata_completion_20261013/`, con `originals/`,
`gb-route/`, `remaining-recent/`, `historical-probe/`, cuenta y revisión del repo.
La consolidación conserva cada respuesta HTTP usada por hash y cada
paquete de partido con sus recibos. Resultado, prueba reversible y comprobación
recuperados en `verified/`; archivo del VPS:
`/srv/quantfut/artifacts/imports/soccerdata-20261013/`.
Dataset normalizado SHA256:
`1b3e606c7528ed9e8ec55866c35aef4371b4cbd939a889a4d214ef26a8e244d1`.
ZenRows pasó de 2.515 a 3.751 créditos utilizados durante esta tarea, con 1.249
disponibles en la última lectura, sin compras; los límites internos descuentan
provisionalmente más para proteger la reserva ante retrasos de facturación.
Sin entrenamiento ni activación de ligas,
captura completa, publicación, cuotas o mensajes externos.
