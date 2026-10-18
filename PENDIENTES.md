# Pendientes de QuantFut — lista única

## Tenis local — autorizado el 16-oct-2026

Extracción pública completa y candidato matemático implementados en checkout independiente `tennis-engine`; no modifica la congelación del motor de fútbol. 214 archivos, 492.251 partidos TML consolidados y 249.938 aptos para el candidato. Modelos ATP/WTA y comparación 2025/2026 ejecutados; el candidato inicial pierde en log-loss frente a Elo y no está aprobado para publicar picks. Informe: `docs/tenis_primera_version_y_resultados_20261016.md`.

- [ ] Calendario futuro con IDs y horas verificadas, enlace a cuotas y casas/presupuesto compartido de The Odds API.
- [ ] Mejorar habilidades/calibración usando validación separada y reservar prueba nueva; 2026 ya fue observado.
- [ ] Seguimiento prospectivo y reglas de liquidación antes de afirmar valor económico.
- [x] Registro inicial de sedes por edición y vigencia: ocho recintos, siete ediciones y 102/102 encuentros ATP/WTA de la muestra enlazados. Ver `docs/tenis_sedes_verificadas_20261017.md`.
- [x] Altitudes de los ocho recintos verificados: Open-Meteo gratuito sin clave, uso no comercial confirmado por el usuario para tenis; 102 encuentros enriquecidos. Ver `docs/tenis_open_meteo_20261017.md`.
- [x] Sedes y temporadas: 37 grupos revisados, 126 encuentros pendientes enlazados y 48 temporadas corregidas por evento conservando el original; muestra 228/228 con sede principal identificada. Ver `docs/tenis_sedes_temporadas_completadas_20261018.md`.
- [x] Georreferenciados los 27 recintos nuevos y elevaciones Open-Meteo: 228/228 encuentros con coordenadas y altitud, fuentes/precision y disponibilidad sin retroactividad. Ver `docs/tenis_coordenadas_viajes_20261018.md`.
- [ ] Viajes: calculo entre ediciones implementado y probado; falta acreditar secuencia por jugador, cierre incluyendo dobles, debut y tiempos de salida. Historial candidato183/456; cero transiciones completas verificadas. No inferir itinerarios ni descanso efectivo.
- [x] Comparador Base/Base+Espaciales/Experimental y nueve escenarios implementados: 154 pruebas tenis. Auditoria real0filas aptas; faltan participaciones y muestra temporal, no hay mejora predictiva medida. Ver `docs/tenis_comparacion_espacial_20261018.md`.

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

## 1. Seguridad (Tú, ~15 minutos)
- [ ] Activar la autenticación en dos pasos en la cuenta de GitHub `cerorar23`.
- [ ] **Rotar la clave de The Odds API** (apareció en una salida de comandos de una sesión).
- [ ] Restringir la clave de Firebase de la app por paquete en la consola de Google (`google-services.json` está en el repo).
- [ ] Sentry: retención del plan, ajustes de organización (IPs, Data Scrubber, 2FA) y probar en un dispositivo real.

## 2. Hasta el 1-nov: no tocar el motor
- [ ] Claude: vigilar que el reentrenamiento corra limpio (worker idéntico a `main`, con el filtro de cierres de 60 min).

## 3. Motor y datos (Claude)
Fases de `docs/superpowers/specs/2026-10-14-senales-motor-principal-design.md`. Una señal solo entra si gana fuera de muestra.

| Fase | Estado | Depende de |
|---|---|---|
| F0 archivo a tablas principales | **Hecha** (en producción) | — |
| F1 capa de ajuste y línea base | **Hecha**: el XI simple pasa la puerta (ΔRPS −0,0013; 9 de 12 ligas) | Reejecutar tras el 1-nov |
| F2 cierres de Pinnacle | A medias: faltan 2.103 (697 en ligas modeladas; antes 6.185) | Créditos tras el 1-nov |
| **F7 sello tardío** | Sin empezar. **Siguiente fase**: deja entrar al XI al motor y usa cuotas de última hora; toca la cadena de hashes. **Plan en borrador (18-oct):** `docs/superpowers/plans/2026-10-18-f7-sello-tardio.md` | Tus 3 decisiones del plan y diseño tras el 1-nov |
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
- [ ] Comprar los **527 snapshots** de The Odds API (~5.270 créditos, tras el reset): `python -m qf.ingest.cierres_odds_api fetch ...`. Necesita tu visto bueno.
- [ ] Registrar alias de Champions y Europa League (103 partidos; Bayern München, Internazionale Milano, LOSC Lille...). Escribe en la tabla de alias: con tu visto bueno.
- [ ] Bloque `mercado` (movimiento de cuotas): cuando haya muestra propia.
- [ ] Antes de encender los picks de valor: hoy solo verían las 13 ligas con modelo y la sombra mide 22; alinear.
- [ ] Vigilar la ampliada 73–95 %: con cuota de referencia acierta 78,0 % frente a 81,4 % prometido (n=223).
- [ ] Resolver 379 identidades de copas y 21 conflictos; unos 250 huecos de tiros y córners.
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
| Elegir **procesador de pago** | Tú | **App: decidido el 15-oct** (Google Play / App Store, suscripción renovable). Web: sigue pendiente |
| **Meta (SDK + CAPI) y compras en la app** | Tú (credenciales) y Claude | **Código hecho y API desplegada el 15-oct, apagada** (rama `feat/meta-compras`, sin fusionar a `main`). Guía: `apps/mobile/docs/META_COMPRAS_TITULAR.md`. Necesito: App ID, client token, dataset y token CAPI de Meta; suscripción `quantfut_plus` (3 planes base), cuenta de servicio y Pub/Sub en Play Console. Antes de activar CAPI hay que alinear el worker (después del 1-nov). Registrar `*.lproj/InfoPlist.strings` en Xcode cuando haya Mac |
| **Avisos legales** (+18, juego responsable, privacidad/cookies, términos) y **revisión de un profesional habilitado** | Tú | Más: DPA de Contabo y Proton, atender el buzón de contacto |
| **Publicación de la cadena: comprometer-revelar** | Claude, con tu decisión | **Código y pruebas hechos el 18-oct** (`hashchain.py`, `tests/test_hashchain_revelado.py`); falta desplegar con ensayo y luego configurar `CHAIN_GIT_REMOTE` (hoy vacío). Sube solo el hash antes y el JSON al terminar los partidos |
| Quitar rutas internas de `/model-card` y añadir `Content-Security-Policy` | Claude | Prioridad baja |
| Puerta comercial (CLV ≥ 300) | Se cumple sola (~10-nov) | Aun así `PUBLISH_PICKS_ENABLED` está en 0: se enciende con tu decisión |

## 6. App y otras líneas (otras sesiones; detalle en `harness/tareas.md`)
- [ ] Cuentas de editor RevU/BitLabs para recompensas; evaluar Tapjoy/Unity, ayeT, adjoe y Torox tras el piloto.
- [ ] iOS: necesita Mac y Apple Developer (APNs y firma).
- [ ] Validar el acceso con Google y la entrega FCM con un usuario real; activar `FIREBASE_AUTH_ENABLED` cuando lo decidas.
- [ ] Proyecto NBA 2026-27: fases F0 a F9 sin empezar.

## Decisiones que dependen de ti
1. Procesador de pago de la web (el de la app ya está decidido: tiendas).
2. Ampliar fuentes para los 1.219 xG que faltan; 365Scores ya aportó tres parejas verificadas.
3. Comprar los 527 snapshots (~5.270 créditos) tras el 1-nov.
4. Registrar los alias de Champions y Europa League.
5. Pasar la cadena a comprometer-revelar y cuándo encender `PUBLISH_PICKS_ENABLED`.
6. Revisión legal por un profesional habilitado.

## Tenis retrospectivo 2024/2025 (18-oct-2026)
- Ampliado: 11.240 partidos con identidad de sede, 10.895 con coordenadas de destino y 6.414 aptos para comparación espacial; 194 pruebas de tenis aprobadas. Segundo bloque Chennai/Palermo/Riad/Hengqin/Shenzhen: 121 destinos y 170 aptos adicionales. Palermo es una referencia de complejo inferida por dirección y contexto cartográfico, tolerancia 750 m. Versiones anteriores y 12 artefactos congelados conservados. Informe docs/tenis_segundo_bloque_sedes_20261018.md.
- Comparación repetida con protocolo fijo: entrenamiento 3.306 de 2024, evaluación 3.108 de 2025; Log-Loss base 0,635571 frente a espacial 0,635581, intervalo de diferencia incluye cero. En la misma muestra original de 2.833: base 0,638733, espacial anterior 0,638682 y ajuste ampliado 0,638764. La nueva cobertura no acredita una mejora predictiva; 2025 exploratorio, sin activar corrección. Sensibilidad y calibración archivadas en historical_geography_batch2_20261018/comparison/.
- Carga por rondas ejecutada: entrenamiento2130/evaluación1957; LogLoss base0,615696 frente a cobertura+carga0,615221. Intervalos incluyen cero, variante experimental sin activar; no equivale a ventanas diarias. Informe docs/tenis_carga_rondas_resultados_20261018.md.
- Pendiente: coordenadas de 78 entradas (345 destinos), cola actual data/tennis/historical_geography_batch2_20261018/geography_priority_queue.json; siguientes cinco: Taipei Tennis Center 14, SuperTennis Arena Bolonia 14, AO Arena Manchester 12, SEB Arena Vilna 10 y Swiss Tennis Arena Biel 9. Ventanas 3/7 días bloqueadas: 152 observaciones terminales archivadas sin límite inferior de finalización acreditado. Nuevas especificaciones se eligen dentro de entrenamiento y requieren periodo futuro intacto. Sin ROI ni horas ficticias.
