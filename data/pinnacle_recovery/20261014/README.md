# Datos Pinnacle encontrados el 14-oct-2026

**272 candidatas asociadas a partidos pendientes; cierre definitivo sin verificar.**
Se guardan por petición del usuario. No se cargaron en `odds_snapshots` ni se
utilizaron para entrenar modelos.

| Competición | Partidos candidatos |
| --- | ---: |
| Champions League | 147 |
| Europa League | 114 |
| Championship | 9 |
| Liga MX | 2 |
| Total | 272 |

- `pinnacle_candidatos_pendientes.csv`: las 272 filas asociadas, con nombres de
  la fuente, partido del catálogo, precios 1/X/2, horas UTC por selección,
  captura real, URL y hash del original.
- `pinnacle_ternas_historicas.csv`: las 586 ternas encontradas, incluidas las
  272 anteriores, 39 ya completas en la base, 266 sin partido exacto y nueve
  discrepancias de marcador. No sumar ambos CSV como si fueran datos distintos.
- `lista_original.csv`: copia exacta de las 6.185 filas pedidas.
- `cierres_faltantes_resultado_busqueda.csv`: estado de las 6.185 filas;
  las cuotas candidatas tienen columnas separadas de los cierres solicitados.
- `cierres_sin_candidato.csv`: 5.913 filas sin candidata.
- `cobertura_por_liga.csv`: recuentos para las 23 competiciones.
- `originals/`: 25 respuestas de OddsTrader y sus recibos (URL, recepción y hash).
- `controls/`: respuestas de contraste del proveedor y prueba de PySBR con proxy,
  con sus recibos y resultado.
- `matched_snapshot.json`: evidencia de las 272 asociaciones e identidades
  del catálogo a la hora del ensayo; contiene solo el subconjunto necesario.
- `equivalencias_*.json`: correspondencias explícitas usadas para los nombres.
- `normalization-report.json`, `resultado_lista_usuario.json`: filtros y ensayo.
- `manifest.json`: recuentos y SHA-256 del paquete versionado. Los hashes de
  `resultado_lista_usuario.json` documentan los CSV originales; `manifest.json`
  es la referencia de integridad de esta copia guardada.

La fuente `currentLines` contiene las últimas cuotas archivadas anteriores al
inicio. **No acredita que el historial esté completo ni el cierre definitivo**.
Todas las candidatas conservan `close_verified=False`. Tampoco se resolvió la
contradicción entre el catálogo antiguo de PySBR y el mapeo de sbrscrape;
se preservan los controles y limitaciones descritos en el informe.

La fecha de captura es la recepción real de 2026 y no acredita disponibilidad
histórica en ese momento previo al partido. La asociación exige competición,
nombres/alias o equivalencias explícitas, partido único dentro de ±36 horas y
marcador reglamentario coincidente. Los discrepantes quedan fuera de candidatas.

`.gitattributes` conserva los bytes exactos, incluido BOM y finales de línea,
para que un checkout de Git mantenga los hashes.

Informes completos: [PySBR y cobertura](../../../docs/pysbr_zenrows_20261014.md),
[pruebas Flashscore](../../../docs/flashscore_pinnacle_20261014.md) y
[Football-data/OddsHarvester](../../../docs/pinnacle_recuperacion_20261014.md).
Los clones, entornos, credenciales y otras cachés permanecen fuera de Git.
