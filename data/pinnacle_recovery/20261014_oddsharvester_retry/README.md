# Reintento OddsHarvester con ZenRows

Cuatro sesiones nuevas sobre dos partidos de la lista exacta de 6.185.
**Cero cierres Pinnacle nuevos. No es una lista de cierres completados.**

`lista_resultado.csv` conserva las columnas originales de cierre vacías y las
272 candidatas anteriores en columnas separadas. Añade el estado de este
reintento; solo dos partidos se consultaron individualmente, con cero Pinnacle.
Los otros 6.183 no se presentan como consultas individuales realizadas.

Las carpetas de prueba guardan el resultado, los precios públicos que recibe
la interfaz y sus recibos. Los archivos `*.view.json` son la representación
descifrada que usa el navegador; `*.response` conserva las respuestas originales
de precios. Cada representación tiene su hash propio.

Tres capturas confirmaron 1X2 de tiempo completo y todas las casas; la prueba de
Perú quedó limitada por idioma/fecha/filtro. Los países son los solicitados a
ZenRows: no se verificó independientemente la geolocalización de salida.

`informe.json` documenta los resultados y `manifest.json` permite comprobar
integridad. Los bytes originales se preservan con `.gitattributes`.
No se incluyen claves, cuentas ni endpoints de autenticación/sesión.

[Informe completo](../../../docs/oddsharvester_reintento_20261014.md).
