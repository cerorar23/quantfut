# Historial web y Flutter: auditoría del 5 de noviembre de 2026

Consulta de la web pública `https://pronosticosdeportivos.pro/#historial` y de sus API, sin cambiar producción. Evidencia numérica completa en `auditoria_historial_mercados_20261105.json`. Zona de comparación: America/Mexico_City. Los datos cambian con cada liquidación; las cifras siguientes pertenecen a la instantánea guardada.

## Hallazgo y corrección

El historial web cuenta **Alta probabilidad y Destacados de fútbol**, y **solo Destacados de NBA y tenis**, desde el 26/10/2026 en la fecha local del dispositivo. Flutter mezclaba conteos históricos empaquetados con el feed actual y, en NBA/tenis, filtraba los resueltos usando la regla actual de publicación. Esa regla excluía destacados históricos que la web sí mostraba.

Cambios preparados en la rama `codex/app-historial-mercados`, basada en la versión multideporte `31007840`:

- Fútbol consulta las dos fuentes web una vez; tarjetas, porcentaje y detalle usan la misma instantánea, con aciertos y fallos. Un error de cualquiera de las fuentes ofrece reintentar.
- NBA y tenis agrupan el destacado del servidor por familia, con resultado win/loss y sellado previo. Las reglas actuales de cuotas siguen decidiendo los pronósticos abiertos; no borran destacados históricos.
- NBA consulta cuatro días atrás y cuatro adelante, igual que la web, en lugar de tres.
- Se añade **Ambos marcan**: había dos resultados web y la app no tenía esa familia. Los anillos de fútbol reflejan el historial publicado, no el acierto de un backtest diferente.
- Los datos de líneas del catálogo siguen disponibles por separado. No se usan como respaldo de resultados publicados.
- Texto nuevo traducido a español, inglés, portugués, francés, italiano y alemán.

Las ventanas del servidor siguen limitando lo visible: NBA usa su cartelera reciente y tenis exporta siete días. La fecha inicial del historial no implica que esos feeds contengan toda la temporada. Las dos publicaciones de un mismo contrato en productos de fútbol distintos se conservan, igual que en la web.

## Resultados observados en la web, por mercado

Estos son registros de pantalla, **no una certificación de rendimiento futuro**. En particular, `destacados` de fútbol reconstruye resultados; la auditoría previa `docs/auditoria_futbol_20261103/INFORME.md` ya señala el riesgo de usar datos posteriores al partido (H01). Igualar web/app no resuelve esa acreditación temporal.

| Deporte | Mercado | Aciertos / resueltos | Acierto observado |
|---|---|---:|---:|
| Fútbol | Ganador | 8/9 | 88,9 % |
| Fútbol | Goles del partido | 126/166 | 75,9 % |
| Fútbol | Hándicap | 173/206 | 84,0 % |
| Fútbol | Goles del local | 55/62 | 88,7 % |
| Fútbol | Goles del visitante | 28/35 | 80,0 % |
| Fútbol | Córners totales | 16/16 | 100 % |
| Fútbol | Doble oportunidad | 20/22 | 90,9 % |
| Fútbol | Ambos marcan | 2/2 | 100 % |
| Fútbol | Tarjetas | 1/2 | 50 % |
| NBA | Ganador | 1/1 | 100 % |
| NBA | Total de puntos | 1/1 | 100 % |
| NBA | Puntos por equipo | 9/12 | 75 % |
| NBA | Hándicap | 2/2 | 100 % |
| NBA | Puntos del jugador | 1/1 | 100 % |
| NBA | Rebotes del jugador | 1/1 | 100 % |
| Tenis | Ganador | 15/16 | 93,8 % |
| Tenis | Juegos totales | 17/20 | 85 % |
| Tenis | Hándicap de juegos | 35/44 | 79,5 % |
| Tenis | Hándicap de sets | 20/21 | 95,2 % |

Una tasa de 100 % con 1 o 2 casos aporta muy poca evidencia. El JSON incluye intervalos Wilson descriptivos; no corrigen la dependencia entre selecciones del mismo partido ni el sesgo de selección. Por ejemplo, 20/21 en hándicap de sets tiene un intervalo aproximado de 77,3–99,2 %; no demuestra un acierto futuro de 95 %.

## Mercados vacíos y cómo completarlos

| Deporte | Familia vacía en el historial web | Diagnóstico / acción |
|---|---|---|
| Fútbol | Córners por equipo | No llegaron resultados de esa familia en la instantánea de las dos fuentes. Se mantiene visible y se llenará al llegar publicaciones reales; no se sustituye por córners totales. |
| NBA | Asistencias y triples del jugador | Existen filas del modelo, pero ninguna publicación elegible de esas familias en esta consulta. La regla vigente excluye props de jugador de la publicación por familia. No se modifica esa puerta para llenar una tarjeta. |
| Tenis | Ganador del set | El overlay tenía una publicación liquidada, pero ningún destacado web de esa familia. Con la comparación exacta de #historial su contador es cero. |
| Tenis | Total de sets y tie-break | El tablero de publicación ofrece una sola orientación: over y yes. Esas probabilidades alcanzaron como máximo 39,9 % y 58,2 %, respectivamente; por eso quedan fuera de la banda publicable. |

Se preparó en el motor de tenis una ampliación **solo para próximos sellados**: añadir los contratos under de sets totales y no de tie-break con la misma distribución conjunta y reglas de devolución. Se anexan al final, conservando contratos e índices anteriores; el tablero de investigación permanece intacto. La regla del servidor seguirá eligiendo una selección por familia y exigiendo una cuota del contrato exacto recibida antes del sello.

La ampliación queda **desactivada por defecto** (`publish_complementary_markets: false` / ausente). La medición no permite presentarla como alto acierto:

| Complemento, estudio retrospectivo separado | Filtro de probabilidad estimada | Aciertos / casos | Observado |
|---|---:|---:|---:|
| Menos de 2,5 sets | 60–95 % | 86/131 | 65,6 % |
| Menos de 2,5 sets | 75–95 % | 1/2 | 50 % |
| No hay tie-break | 60–95 % | 62/101 | 61,4 % |
| No hay tie-break | 75–95 % | 33/50 | 66 % |

Este estudio transforma probabilidades de pronósticos previos, pero no acredita una cuota del lado opuesto. **No son publicaciones históricas nuevas y no se añaden a los contadores.** Hace falta validar calibración y resultados prospectivos antes de activar esos candidatos. Una probabilidad alta y el acierto observado son cantidades distintas; tampoco acreditan rentabilidad.

En NBA sí se encontraron selecciones abiertas ya publicadas con probabilidades estimadas de 86,6–89,5 % y cuotas de referencia 1,20–1,211 en total, hándicap y puntos por equipo. Ya pertenecen a sus mercados: no se trasladan a asistencias o triples. Su disponibilidad queda sujeta al inicio y a la cuota efectiva.

## Validación y entrega

- 45 pruebas dirigidas de Flutter aprobadas: fuentes, mercados, traducciones, destacados, fallos de red y ventana NBA.
- 2 pruebas matemáticas aprobadas para complementos en partidos al mejor de 3 y de 5 sets, conservando probabilidades, pushes y contratos previos.
- Verificaciones completas y artefacto Android: resultado final registrado en `harness/progreso.md`.
- No se desplegó el motor ni se activaron complementos. El código Flutter requiere instalar la nueva compilación; el cambio del motor necesita su despliegue y validación posteriores.

Para repetir la consulta pública desde la raíz, con Node disponible:

```powershell
$env:TZ = 'America/Mexico_City'
node scripts/auditar_historial_mercados.mjs . 2026-11-05
```

Fuentes: [historial web](https://pronosticosdeportivos.pro/#historial), [alta probabilidad](https://pronosticosdeportivos.pro/mobile/v1/markets/history?limit=500), [destacados de fútbol](https://pronosticosdeportivos.pro/mobile/v1/markets/destacados?desde=2026-10-26), [feed de tenis](https://pronosticosdeportivos.pro/web/deportes/tenis), [cuotas de tenis](https://pronosticosdeportivos.pro/web/deportes/tenis/cuotas) y cartelera/mercados de NBA por partido (URLs consultadas en el JSON).
