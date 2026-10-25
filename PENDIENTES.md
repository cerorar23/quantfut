# Pendientes de QuantFut — lista única

## Tenis local — estado consolidado 19-oct-2026

**Motor vigente v7 (19-oct):** `python -m tennis_motor` en el checkout `tennis-engine`. Corrige alias de identidad, sobredispersión por partido en todos los mercados, ranking/edad, Elo dinámico por ronda e inactividad/carga. 2026 exploratorio: acierto ATP 67,6 % y WTA 67,9 % (Elo 64,2 %/64,8 %). 17 pronósticos sellados en `data/tennis/core_v7_prospective_20261019/`. Los 990 pronósticos del estudio de diez mercados se retiraron (archivados, no borrados).

- [x] Cuotas: Tennis-Data (descarga manual, validación) y The Odds API en vivo (h2h, eu, 2 fotos/día, tope 400/mes; tarea de Windows «QuantFut tenis cuotas h2h»). Motor vigente v8: usa la cuota sin margen cuando existe.
- [x] **24-oct: cuotas de PropLine** (archivo horario compartido, solo lectura); se retiró la foto de The Odds API del cron del VPS, sin respaldo. Pendiente: comprobar en los sellados de los próximos días qué parte sale con `live_snapshot` de PropLine (nombres abreviados como «J. Vandromme» no emparejan y caen al apilador v7).
- [x] Automatización de Codex pausada (20-oct, `status = "PAUSED"`).
- [x] Motor en el VPS desde el 20-oct (imagen `quantfut-tenis`, cron de `qf`); ya no depende del PC.
- [ ] **Claude:** evaluar con resultados reales (revisión programada el 22-oct).

Motor de investigación implementado y probado en checkout independiente `tennis-engine`. 214 originales, 492.251 partidos y modelos ATP/WTA conservados. The Odds API: **plan de pago, 2.000 créditos mensuales para tenis**. Estado actual: [mercados integrados y consumos](docs/tenis_mercados_integrados_20261019.md); antecedentes: [auditoría y pronósticos](docs/tenis_auditoria_pronosticos_20261019.md), [preparación operativa](docs/tenis_preparacion_apuestas_20261018.md) y [cierre geográfico](docs/tenis_cierre_integral_20261018.md). Diez familias de mercados calculables; no hay rentabilidad futura demostrada ni apuestas automáticas.

- [x] Matemática de saque/resto y Markov, híbrido Elo, Weighted Elo, evaluación común, regularización y controles temporales implementados; ampliación de mercados: 294 pruebas específicas aprobadas.
- [x] Mercados: diez familias, trece claves documentadas, cálculo de líneas enteras/medias con pushes, comparación de cuotas, liquidación y evaluación por contrato. 624 contratos ilustrativos para ocho encuentros; modelos congelados conservados.
- [x] Pruebas ampliadas autorizadas: 500 créditos por clave suministrada y seis de la prueba previa; 12.052 ofertas en capturas repetidas, 56 casas, nueve IDs de evento. La segunda clave coincide con la principal: 500 reconciliados centralmente, 583 confirmados/595 reservados de tenis en el mes. Saldo observado principal 4.606; demo separada 0. No repetir las autorizaciones consumidas.
- [x] Evaluación exploratoria de mercados: 3.498 partidos/56.804 probabilidades, modelos anteriores a 2026; cobertura y exclusiones explícitas. No equivale a calibración completa ni validación financiera futura.
- [ ] Cobertura externa: seis claves implementadas no aparecieron en las capturas; marcador por sets/tiebreak sin oferta de tenis acreditada en The Odds API. Verificar conflictos de calendario (Sara Bejlek en dos eventos con distinto rival), identidades, reglas específicas y calibración fuera de muestra antes de cualquier aprobación.
- [x] Continuidad predictiva ACTIVA en este chat cada2h: capturas cada4h, máximo12consultasAPI-Tennis/díaUTC, espera24hante401/403/429. Diez mercados e incorporación automática de resultados:18partidos(11ATP/7WTA),990tareasrelacionadas/110grupos,0resultadosfuturos porque aún no se jugaron en comprobación19-oct18:35UTC. Histórico legible2788terminados/39grupos separado;396pruebasmotor y1315generales. Ver docs/tenis_resultados_y_evidencia_20261019.md.
- [x] Nuevo protocolo predictivo sellado por DigiCert el19-oct-2026 a10:54:10CiudaddeMéxico(16:54:10UTC), antes del estudio; firma/nonce/archivo y prueba negativa verificados. No acredita precisión ni rentabilidad: docs/tenis_sello_predictivo_20261019.md.
- [x] Calidad predictiva revisada sin cuotas: seis modelos sobre2.207 ATP/581 WTA comunes,10familias/50grupos de contrato; bandas, cobertura e intervalos por torneos/periodos.332pruebas, protocolo futuro y registro sin cuotas entregados. No se acredita superioridad ni certeza: docs/tenis_calidad_predictiva_20261019.md.
- [x] Nueva auditoría: cero fallos de integridad, 214 originales y 12 artefactos congelados conservados; API-Tennis actualizado y cuatro programas oficiales revisados. Ocho probabilidades ATP selladas, 12/20 parejas revisadas excluidas con motivo; no es cobertura universal ni servicio automático.
- [ ] Hallazgo de identidades: 50 nombres WTA y dos ATP asociados a varios IDs en el modelo tras normalizar acentos. Excluir ambigüedades; acreditar puentes de identidad y consolidar una versión nueva de datos/modelo antes de ampliar cobertura. No se fusionan por nombre ni se alteran las versiones congeladas.
- [x] Muestra contemporánea de 228 encuentros: sedes/temporadas y coordenadas revisadas; registro original conservado.
- [x] Revisión integral de las 73 entradas geográficas pendientes: 72 acreditadas, 239/240 referencias del registro y 11.237/11.240 destinos con coordenadas. Una consulta DEM de 59 puntos nuevos. No quedan bloques de cinco sedes pendientes de ejecutar.
- [x] Conjunto histórico y evaluación repetidos: 6.568 casos aptos, 3.353 entrenamiento 2024 y 3.215 evaluación 2025; sin mejora acreditada ni activación. Protocolo, predicciones, calibración y auditoría archivados.
- [ ] Palm Hills septiembre de 2025: identificar el campus de la eliminatoria Líbano–Barbados con una fuente específica; tres partidos excluidos. El propietario tiene dos campus distintos, no se fusionan por nombre.
- [ ] Evidencia temporal y viajes: 152 terminales archivados sin límite inferior finito de cierre; falta historial completo incluyendo dobles/horas/arribos para descanso exacto y carga diaria. Captura acotada implementada; API-Tennis sigue en prueba/cuota desconocida; captura programada con límites locales, sin acreditar tiempos físicos.
- [x] Clima: archivo Open-Meteo con recepción real, unidades y coordenadas verificadas; una consulta pública para cinco sedes. 66 eventos enlazados; 64 candidatos no cancelados en v3 y 58 aún futuros en v4, sin nuevas consultas.
- [ ] Clima predictivo: faltan estado de techo y muestra de entrenamiento/validación para probar su contribución. No se aplica el pronóstico exterior como exposición real desconocida ni se modifican probabilidades.
- [x] Auditoría financiera reproducible y sensibilidad a costes entregadas; 312 pruebas. Sello externo DigiCert verificado el19-oct16:22:52UTC, anterior al estudio;227 originales/11 eventos, cero órdenes prospectivas y ROI desconocido. Ver docs/tenis_acreditacion_financiera_20261019.md.
- [x] Evaluación financiera simulada: código entregado, cuotas originales y predicciones selladas, retiros incluidos, cobertura, ROI/CLV por bloques y comparación probabilística frente al mercado sin margen. Protocolo adicional v2 futuro 20-oct-2026 a 1-jul-2027, sin modificar el protocolo anterior.
- [ ] Operación financiera real: cobertura oficial fresca de eventos, cuotas/cierres/resultados prospectivos y muestra suficiente; después verificar ejecución, costes y límites de exposición. Cero selecciones prospectivas actuales, ROI desconocido, sin publicación de picks. El evaluador no coloca apuestas.

Actualizada el **2026-10-18**. Es el punto de entrada: aquí está lo que falta, quién lo hace y de qué depende.
El detalle técnico de cada fase vive en `harness/tareas.md` y en `docs/`; cuando una cosa se cierre, se marca aquí y allí.
Responsable: **Tú** = decisión o gestión del titular; **Claude** = trabajo en el repo o el servidor (siempre con ensayo y registro en `DEPLOYS.md`).

## Calendario fijo
| Fecha | Qué ocurre |
|---|---|
| ~26-oct | Termina la prueba Business de Sentry: confirmar la retención del plan |
| **1-nov, 03:00 UTC** | Reentrenamiento automático (~5 h) y reset de los 20.000 créditos de The Odds API |
| **2-nov, 9:00 (hora local)** | Revisión automática de solo lectura (tarea programada `revisar-reentrenamiento-1-nov`) |
| ~fin de oct–nov | **Puerta de CLV (aclarado 18-oct).** La cifra oficial es `publish.shadow_sharp.report()` (ofertas «publicables» de la sombra sharp), no `shadow.summary` ni `shadow_results`, que miden los retadores de XI. Hoy: n=213 con cierre justo (223 publicables), `ev_close` **+3,07 %, IC95 +1,54 a +4,67**; el +3,46 % (n=142) del 15-oct era esta misma medida con menos muestra. Bloquea: n<300 (a ~24/día desde el 15-oct, hacia el 22-oct) y **ninguna liga llega a 30** (la mayor, MLS, 18): ≥3 ligas con 30 pide ~460 en total, hacia finales de oct o noviembre según el ritmo |

## 1. Seguridad
- **Decisión del titular (18-oct): no se hace por ahora** la autenticación en dos pasos de GitHub, la rotación de la clave de The Odds API ni la
  restricción de la clave de Firebase. Quedan como riesgos aceptados; no se vuelven a pedir. Sentry (retención del plan y ajustes) sigue abierto.
- **Token de Copernicus:** el titular decidió **conservarlo** (se compartió por chat) para la descarga automática de clima de los partidos
  futuros: cron diario 06:20 UTC con candado; el token está en `/etc/environment` del worker en marcha y en el `.env` del servidor.

## 2. Hasta el 1-nov: no tocar el motor
- [ ] Claude: vigilar que el reentrenamiento corra limpio (worker idéntico a `main`, con el filtro de cierres de 60 min).

## 3. Motor y datos (Claude)
Fases de `docs/superpowers/specs/2026-10-14-senales-motor-principal-design.md`. Una señal solo entra si gana fuera de muestra.

| Fase | Estado | Depende de |
|---|---|---|
| F0 archivo a tablas principales | **Hecha** (en producción) | — |
| F1 capa de ajuste y línea base | **Hecha**: el XI simple pasa la puerta (ΔRPS −0,0013; 9 de 12 ligas) | Reejecutar tras el 1-nov |
| F2 cierres de Pinnacle | A medias: faltan 2.103 (697 en ligas modeladas; antes 6.185) | Créditos tras el 1-nov |
| **F7 sello tardío** | Sin empezar. **Siguiente fase**: deja entrar al XI al motor y usa cuotas de última hora; toca la cadena de hashes. **Plan en borrador (18-oct):** `docs/superpowers/plans/2026-10-18-f7-sello-tardio.md` | Falta confirmar la ventana de sello (propuesta T-45) y el corte; lo gratis y el difuminado VIP ya están decididos (18-oct). Diseño tras el 1-nov |
| F3 bajas como minutos perdidos | Sin empezar (poca evidencia: 173 partidos con consulta previa al inicio) | F7 |
| F6 clima y sede | Decidido (Copernicus ERA5 para historial; Open-Meteo Standard en vivo y altitud); sin código | Guardar token cifrado |
| F5 árbitro | Sin empezar; datos de F0 listos | Unificar identidades |
| F4 puente FotMob/API-Football y XI con valor | Sin empezar; las variantes con valor hoy no pasan la puerta | F7 |
| **F9 evaluación (probabilidades y selección, a volumen constante)** | Nueva (15-oct). La prueba decisiva es contra B actualizado al mismo momento | F7 |
| **F8 conectar el modelo propio con los picks** | Nueva (15-oct). Se evalúa en paralelo con F9 sin tocar picks vendidos; se activa al final | F9 y factores validados |
| F10 selección y exposición entre productos | Nueva (15-oct) | F8 |
| F11 app: fuente de cada cifra e indicador de calidad de datos (6 idiomas) | Nueva (15-oct); no toca el motor, puede adelantarse | Tu visto bueno |
| F12 factores sin fase: **descanso y calendario primero**; ida/vuelta, entrenador, estilos, córners/tarjetas ampliados | Nueva (15-oct) | Calendario de otras competiciones |

Orden tras el 1-nov: F7 (con bajas de FotMob donde API-Football no las da) → F9 con F8 en paralelo → descanso/calendario → archivo FotMob a tablas y
F3, F6, F5, F4 → activar F8 y F10. Datos que faltan descargar: calendario de copas y otras competiciones, altitud de sedes y clima
ERA5 (tu token); el XI, minutos, bajas, entrenador y estilos ya están en el archivo FotMob. Plan completo:
`docs/superpowers/specs/2026-10-15-mejoras-tres-motores-plan.md`.

Tareas sueltas:
- [ ] Comprar los cierres pendientes tras el reset del 1-nov. **Medido 18-oct:** 590 snapshots (5.900 créditos; 652 partidos, 1.380 créditos solo de Liga MX) y saldo 5.230. Comprarlos ya dejaría el saldo por debajo de lo que consume la captura en vivo (~300/día × 13 días ≈ 3.900). Orden: `python -m qf.ingest.cierres_odds_api fetch --presupuesto 5900`. Necesita tu visto bueno.
- [x] **Hecho 18-oct:** Arsenal corregido en 33 partidos de copa (`db/073`) y 4 alias de The Odds API con **+45 cierres** de copa (quedan 58 sin cierre, todos contra clubes externos). Detalle: `docs/datos_al_motor_20261018.md`. El reentrenamiento del 1-nov los incluirá; el efecto en el modelo **no está medido**.
- [x] **Hecho 18-oct** (`db/075`-`080`): archivo FotMob en tablas con `match_id` (20.331 partidos, 852.126 jugadores, 47.140 bajas), altitud de 728 estadios, calendario de 315 equipos × 4 temporadas (60.979 partidos, refresco diario 05:40 UTC), 54 equivalencias de árbitros, 7.834 puentes de jugadores y la vista de descanso `v_descanso_equipo`.
- [x] **Hecho 18-oct (autorizado):** captura recurrente de FotMob (`db/081`): referencias, instantáneas previas a ~24 h/4 h/70 min/40 min con alineación, no disponibles y **pronóstico de clima**, y archivo posterior al partido. Cron con `flock`; un bloqueo 401/403/429 la detiene 12 h.
- [x] **ERA5 histórico terminado** (20.193 partidos, 423 celdas, ninguno con estadio sin cubrir). **Pendiente: regenerar el token de Copernicus** (se compartió por chat). Los partidos nuevos se completan con `python -m qf.ingest.era5_clima` (incremental, necesita `CDS_API_TOKEN`; no está en cron porque el worker en marcha no tiene la variable: se añade al recrear el worker el 1-nov).
- [x] Sede de los partidos nuevos: `qf.ingest.sedes`, cron horario (449 asignados el 18-oct; 273 próximos la reciben con su captura de 24 h).
- [x] Open-Meteo: no se usa. El plan gratuito es solo no comercial y el producto vende suscripciones; el pronóstico lo da la captura de FotMob. Si quieres una segunda fuente, hace falta la clave del plan de pago Standard.
- [ ] Estadios duplicados por coordenadas: 182 grupos (384 estadios); revisar antes de usar sede/viaje (F6).
- [ ] F5: usar el **nombre de árbitro de FotMob** como llave (19.183 partidos frente a 2.799 de API-Football; el cruce solo suma 125).
- [ ] Bloque `mercado` (movimiento de cuotas): cuando haya muestra propia.
- [ ] Antes de encender los picks de valor: hoy solo verían las 13 ligas con modelo y la sombra mide 22; alinear.
- [ ] Vigilar la ampliada 73–95 %: con cuota de referencia acierta 78,0 % frente a 81,4 % prometido (n=223).
- [x] Las «379 identidades de copas» son 379 partidos de 110 equipos: 67 tienen id probado, 43 son clubes de ligas que no cubrimos (no se vinculan por regla del proyecto) y **ningún** partido tiene sus dos equipos probados, así que no se puede unir ninguno. Cerrado como no resoluble por diseño; ver el documento. Conflictos: 18 FotMob + 2 Sofascore, por revisar.
- [ ] Unos 250 huecos de tiros y córners.
- [ ] Ampliar fuentes para los **1.219 huecos de xG** (Serie B 588, LaLiga 2 233, Argentina 208, Ligue 2 144 y otros 46). LanusStats/365Scores aportó tres parejas de LaLiga 2, cargadas por petición del titular el 15-oct; su muestra no prueba cobertura completa. Ver `docs/lanusstats_carga_20261015.md`.
  - Verificado 18-oct: siguen siendo **1.219** (partidos terminados desde el 1-ene-2024, sin xG de alguno de los dos equipos): Serie B 588, LaLiga 2 233, Argentina 208, Ligue 2 144, Champions 14, Europa League 12, México 8, otros 12. Sin cambios desde el 15-oct. (Con una ventana desde ago-2022 salen más: Serie B 1.158, LaLiga 2 926.)

## 4. Orden del servidor (Claude, con ensayo; la API después del 1-nov)
- [ ] Alinear la **API** con `main` (24 archivos distintos; imagen `quantfut-api-admob:20261015a`). Es lo que ven tus clientes.
- [ ] Corregir `docker-compose.yml` del repo (fija una imagen antigua de la API, `tapjoy:20261012-msg`).
- [ ] Corregir `requirements.txt` de `~/quantfut` (sin `cryptography` ni `firebase-admin`) y sincronizar `~/quantfut/src`, que está desactualizada.
- [ ] Que el servidor despliegue desde GitHub (clave de despliegue de solo lectura y `git pull` de una etiqueta).
- [ ] Ampliar `scripts/deploy.sh` con `construir`, `ensayo` y `desplegar` (hoy tiene `estado` y `congelar`).
- [ ] **Una carpeta de trabajo por sesión** (`git worktree`): el 15-oct dos sesiones compartieron carpeta y una comiteó dentro de la rama de la otra.
- [ ] Limpiar entradas desactualizadas de `harness/tareas.md` (por ejemplo, dice «3.267 cierres pendientes»; hoy son 2.103).
- Ya hecho: worker alineado con `main` el 15-oct (0 archivos distintos); vuelta atrás `en-ejecucion-20261015`.

## 5. Para poder vender picks
| Qué | Responsable | Nota |
|---|---|---|
| Procesador de pago | Tú | **Decidido.** App: Google Play / App Store (suscripción renovable). Web: **Whop** (checkout embebido y webhooks firmados, ya desplegado) |
| **Meta (SDK + CAPI) y compras en la app** | Tú (credenciales) y Claude | **Código en `main`; CAPI activo desde el servidor (21-oct); app de Meta creada y vinculada al dataset, Android con hashes y registro automático de compras apagado.** Falta compra de prueba web con `META_TEST_EVENT_CODE`, build de Play con `QF_META_ENABLED=true` y app de iOS. Guía: `apps/mobile/docs/META_COMPRAS_TITULAR.md`. Necesito: App ID, client token, dataset y token CAPI de Meta; suscripción `quantfut_plus` (3 planes base), cuenta de servicio y Pub/Sub en Play Console. Antes de activar CAPI hay que alinear el worker (después del 1-nov). Registrar `*.lproj/InfoPlist.strings` en Xcode cuando haya Mac |
| **Avisos legales** y revisión de un profesional habilitado | Tú | **Revisión concluida el 18-oct, sin objeciones** (palabras del titular). Siguen siendo tareas suyas: DPA de Contabo y Proton y atender el buzón de contacto |
| **Publicación de la cadena: comprometer-revelar** | Claude, con tu decisión | **Activada el 18-oct** (worker recreado desde `main`, repositorio público `cerorar23/quantfut-registro`). Vigilar el sellado de las 08:00 UTC del 19-oct. Tu decisión pendiente: ¿publicar también el JSON de los 19 lotes históricos? Hoy están apartados en `historico_sin_publicar/`; ver `docs/registro_publico_activacion_20261018.md` |
| Quitar rutas internas de `/model-card` y añadir `Content-Security-Policy` | Claude | Prioridad baja |
| Puerta comercial (CLV ≥ 300) | Se cumple sola (~10-nov) | Aun así `PUBLISH_PICKS_ENABLED` está en 0: se enciende con tu decisión |

## 6. App y otras líneas (otras sesiones; detalle en `harness/tareas.md`)
- [ ] Cuentas de editor RevU/BitLabs para recompensas; evaluar Tapjoy/Unity, ayeT, adjoe y Torox tras el piloto.
- [ ] iOS: necesita Mac y Apple Developer (APNs y firma).
- [ ] Validar el acceso con Google y la entrega FCM con un usuario real; activar `FIREBASE_AUTH_ENABLED` cuando lo decidas.
- [ ] Proyecto NBA 2026-27: fases F0 a F9 sin empezar.
- [x] NBA — modelo de props anclado en el mercado (protocolo congelado, 2024-25 → 2025-26): sin evidencia de información sobre el consenso de las casas de EE. UU.; rebotes y triples solo calibración (el control del placebo del protocolo falla y necesita un v1.1). docs/nba_props_residual_20261024.md.
- [x] NBA — cuotas históricas h2h (The Odds API): los 325 snapshots de 2024-25 y 2025-26 ya se compraron el 23-oct (manifest en `apps/nba/.local/raw/nba_odds_h2h_202611`) y se compararon (`nba_f6_market_20261101`).
- [x] NBA — normalizado ampliado (tiros, pérdidas, rebote ofensivo, posesiones, play-in y playoffs 2022-23..2025-26): `nba_extended_box_20261024`, docs/nba_normalizado_ampliado_20261024.md.
- [x] NBA — cuotas históricas de bet365 (BetsAPI) normalizadas: 34.713 filas, 3.867 partidos de 3 temporadas, ganador/hándicap/total de partido, mitad y Q1 con apertura, cierre y trayectoria (`nba_betsapi_odds_20261024`, docs/nba_cuotas_betsapi_normalizadas_20261024.md). Matriz por mercado y continuidad pasado→futuro: docs/nba_matriz_mercados_y_estudios_20261024.md.
- [x] NBA — entrenamiento y calibración del motor en todos los mercados: 9 mercados de equipo con cuota de bet365 (sin evidencia de que el motor mejore el cierre), 12 de equipo por periodos y 9 de jugador sin cuota calibrados contra resultados (ajuste 2024-25, prueba 2025-26). En combinaciones de jugador la ley v1 cruda está sobreconfiada y recalibrar con disponibilidad y entorno la corrige. docs/nba_calibracion_motor_20261024.md.
- [x] NBA — productor vivo 1.3.2 preparado (sin desplegar): sumas de puntos, rebotes y asistencias con la calibración del productor; las cuatro pasan el chequeo congelado (Brier −0,002 a −0,009, pendiente 0,6 → 1,0). Modelo candidato idéntico al desplegado salvo las sumas. docs/nba_productor_combinaciones_20261024.md.
- [x] NBA — productor 1.3.2 desplegado el 24-oct (con el arreglo urgente del minutaje `:60`, que tenía el sellado parado). Productor 1.4.0 (reentrenado con reportes T-60, entorno del partido y triples/robos/tapones/robos+tapones; play-in/playoffs y ajuste de anotación probados y descartados): docs/nba_productor_14_20261025.md.
- [ ] NBA — robos, tapones, triples y pérdidas ya están en el vivo (1.4.0; pérdidas con RUN071 + columnas nuevas, docs/nba_productor_14b_20261025.md). Pendiente: doble-doble, Q3/Q4 y margen por rangos (faltan en el archivo normalizado), recalibración de totales por la deriva de anotación (el ajuste dentro de la temporada se probó y empeora) y postemporada 2021-22 sin fecha.

## Decisiones que dependen de ti
0. ~~API-Football en plan gratuito~~ **Decidido 24-oct: sustituido** por PropLine (resultados, calendario) y SofaScore
   (xG, estadísticas; 15 USD/mes, 40 partidos/día). Comprobado el 25-oct: clasificación y marcador en vivo parados
   (API-Football); bajas parciales, y FotMob cubre bajas y alineaciones previas solo en las 13 ligas con modelo.
   Decidir si se sustituyen clasificación y marcador en vivo.
1. (Resuelto) Procesador de pago: Whop en la web, tiendas en la app.
2. Ampliar fuentes para los 1.219 xG que faltan; 365Scores ya aportó tres parejas verificadas.
2b. (Resuelto el 18-oct) Captura de FotMob autorizada; token de CDS entregado; Open-Meteo descartada.
3. Comprar los 590 snapshots (~5.900 créditos) tras el 1-nov.
4. ~~Registrar los alias de Champions y Europa League~~: hecho el 18-oct. Verificado: Bayern München, Internazionale Milano y LOSC Lille ya están, y los 134 nombres sin resolver son clubes de ligas sin modelo (se descartan por regla).
5. Pasar la cadena a comprometer-revelar y cuándo encender `PUBLISH_PICKS_ENABLED`.
6. (Resuelto el 18-oct) Revisión legal concluida sin objeciones.

## Tenis retrospectivo 2024/2025 (18-oct-2026)
- Ampliado: 11.240 partidos con identidad de sede, 10.895 con coordenadas de destino y 6.414 aptos para comparación espacial; 194 pruebas de tenis aprobadas. Segundo bloque Chennai/Palermo/Riad/Hengqin/Shenzhen: 121 destinos y 170 aptos adicionales. Palermo es una referencia de complejo inferida por dirección y contexto cartográfico, tolerancia 750 m. Versiones anteriores y 12 artefactos congelados conservados. Informe docs/tenis_segundo_bloque_sedes_20261018.md.
- Comparación repetida con protocolo fijo: entrenamiento 3.306 de 2024, evaluación 3.108 de 2025; Log-Loss base 0,635571 frente a espacial 0,635581, intervalo de diferencia incluye cero. En la misma muestra original de 2.833: base 0,638733, espacial anterior 0,638682 y ajuste ampliado 0,638764. La nueva cobertura no acredita una mejora predictiva; 2025 exploratorio, sin activar corrección. Sensibilidad y calibración archivadas en historical_geography_batch2_20261018/comparison/.
- Carga por rondas ejecutada: entrenamiento2130/evaluación1957; LogLoss base0,615696 frente a cobertura+carga0,615221. Intervalos incluyen cero, variante experimental sin activar; no equivale a ventanas diarias. Informe docs/tenis_carga_rondas_resultados_20261018.md.
- Pendiente: coordenadas de 78 entradas (345 destinos), cola actual data/tennis/historical_geography_batch2_20261018/geography_priority_queue.json; siguientes cinco: Taipei Tennis Center 14, SuperTennis Arena Bolonia 14, AO Arena Manchester 12, SEB Arena Vilna 10 y Swiss Tennis Arena Biel 9. Ventanas 3/7 días bloqueadas: 152 observaciones terminales archivadas sin límite inferior de finalización acreditado. Nuevas especificaciones se eligen dentro de entrenamiento y requieren periodo futuro intacto. Sin ROI ni horas ficticias.
- [x] NBA v1.3 prospectivo: sección de /nba desplegada y sellado diario en marcha con el productor vivo (1.4.0 desde el 25-oct; DEPLOYS.md).
