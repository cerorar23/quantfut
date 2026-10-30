# Rediseño de la app para sumar NBA y tenis (propuesta v3, 30-oct-2026)

Estado: **propuesta para aprobar**. No se ha tocado código de la app. Al aprobarla, el siguiente paso es el plan de implementación.

Historial de decisiones del titular (30-oct):
- v2: **NBA y tenis aprobados para publicar picks**; nada de etiquetas «En validación». Estética de referencia: **CyberCore CSS** ([demo](https://sebyx07.github.io/cybercore-css/#/), [repo](https://github.com/sebyx07/cybercore-css), MIT) y skill **ui-ux-pro-max**.
- v3: **autorizado a cambiar la paleta**, eligiendo la mejor según la evidencia académica para pronósticos deportivos, atracción y conversión.

## 1. Punto de partida

- Barra inferior llena: Inicio · Predicciones · Mercados · Coins · Perfil (`live_shell.dart`).
- Tema actual (`live_widgets.dart`): fondo `#090f1a`, panel `#132333`, cian `#00d5ee`, dorado `#ffbd00`, verde `#00d58b`, gris `#a0adbd`; Gilroy; radio 16.
- `PredictionsSwitcher` dorado (Alta prob., Escalera, Parley) con deslizamiento lateral.
- Tarjetas, barras y detalle pensados solo para fútbol (local/empate/visitante).
- La web ya separa el deporte arriba (`frontend/app.js:410`).

## 2. Paleta nueva: qué dice la evidencia

### 2.1 Lo que hay (y lo que no)

No existe una tesis doctoral que defina «la paleta óptima para apps de pronósticos deportivos». Busqué y lo publicado sobre apps de apuestas son blogs de agencias sin datos. Lo que sí hay son estudios revisados por pares sobre color, confianza, excitación y riesgo, y de ahí sale la paleta:

| Estudio | Hallazgo | Consecuencia para QuantFut |
|---|---|---|
| Labrecque y Milne (2012), *J. of the Academy of Marketing Science*, 4 estudios | El azul se asocia a **competencia**; el rojo a **excitación**. El color cambia la personalidad percibida de la marca y la intención de compra. | Base y color principal **azul**: el producto vende acierto y transparencia, es decir, competencia. |
| Gorn et al., «Waiting for the web» | Pantallas **azules relajan** y hacen percibir la carga más rápida que amarillo o rojo; el **valor** (luminosidad) pesa más que el tono. | Fondos azul noche (no negro neutro) y contraste de luminosidad alto. |
| Bagchi y Cheema (2013), *J. of Consumer Research*, eBay + laboratorio | El rojo, por excitación, sube las pujas en subastas pero **baja la disposición a pagar en precio fijo**. | El VIP es precio fijo: **nada de rojo** en la venta. |
| Stark et al. (1982) vs. Spenwyn, Barrett y Griffiths (2010) vs. Pontes y Williams (2020) | Con luz roja: más riesgo en 1982; sin efecto en el riesgo por apuesta en 2010 (solo más velocidad con música rápida); más aversión al riesgo en 2020. | Resultados contradictorios: el rojo no aporta nada demostrable y sí riesgo ético. Se descarta como color de acción. |
| Elliot y Maier (color en contexto) y meta-análisis de Gnambs (2020) | El «rojo empeora el rendimiento» **no sobrevive** al corregir el sesgo de publicación. | No usar teorías populares de color sin respaldo. |
| Mehta y Zhu (2009), *Science* | Rojo → evitación y atención al detalle; azul → acercamiento. | Azul para invitar a explorar; el rojo/coral solo para fallos. |
| Piepenbrock et al. (2013-2014), tesis de Düsseldorf y *Ergonomics* | Texto oscuro sobre claro se lee mejor, sobre todo en detalle fino y cifras pequeñas. | Se mantiene el modo oscuro (marca y estilo CyberCore), pero cifras grandes, contraste muy alto, y **modo claro como opción futura**. |
| Prevalencia del daltonismo rojo-verde (~8 % de los hombres) | Verde/rojo solos no se distinguen para muchos usuarios. | Acierto/fallo **siempre con icono** (✓/✗); el par principal es azul–ámbar, que sí distinguen. |
| Revisiones sobre diseño engañoso en plataformas de apuestas (2026) | Patrones oscuros, «sludge» y empujones que explotan sesgos se asocian a juego problemático. | QuantFut es sin ánimo de lucro: **convierte con confianza, no con presión** (ver 2.4). |

### 2.2 Paleta v3 «Azul competente + ámbar de acción»

Lógica: el azul transmite competencia y calma (base); **un único** color cálido muy luminoso se reserva para la acción de conversión. El par azul–ámbar es complementario (máximo contraste de tono) y seguro para daltónicos. Contrastes WCAG medidos con script (texto ≥ 4,5:1 en los tres fondos):

| Token | Hex | Uso | Contraste fondo / panel / panel2 |
|---|---|---|---|
| `bg` | `#070B14` | Fondo (azul noche) | — |
| `surface` | `#0F1829` | Tarjetas | — |
| `surface2` | `#16223A` | Hojas, chips, campos | — |
| `border` | `#26365A` | Bordes decorativos | 1,65 / 1,49 / 1,33 (no lleva texto) |
| `text` | `#EEF3FF` | Texto principal | 17,7 / 16,0 / 14,3 |
| `text2` | `#9DACCB` | Texto secundario | 8,6 / 7,8 / 7,0 |
| `muted` | `#7F8DAD` | Metadatos | 5,9 / 5,3 / 4,8 |
| `primary` | `#4C8DFF` | Azul eléctrico: selección, navegación, probabilidades, enlaces | 6,2 / 5,6 / 5,0 |
| `cta` | `#FFB020` | **Ámbar: solo VIP, desbloquear y monedas** | 10,8 / 9,7 / 8,7 |
| `success` | `#2BD99F` | Acierto, pick gratis, «más de» cumplido (con ✓) | 10,8 / 9,8 / 8,7 |
| `danger` | `#FF6B6B` | Solo fallos y errores (con ✗) | 7,1 / 6,4 / 5,7 |

- Botón ámbar con texto `#1A1200` (10,2:1). Botón azul con texto oscuro `#04122E` (5,8:1); **no** blanco sobre azul (3,2:1, insuficiente).
- Regla de aislamiento: en cada pantalla solo hay **una** acción ámbar visible. Si todo brilla, nada destaca.

### 2.3 Acentos de deporte

Ninguno coincide con los colores con significado (azul acción, ámbar venta, verde acierto, coral fallo):

| Deporte | Hex | Contraste | Nota |
|---|---|---|---|
| Fútbol | `#22D3EE` cian | 10,9 / 9,8 / 8,8 | Continuidad con la marca actual |
| NBA | `#B58CFF` violeta | 7,7 / 6,9 / 6,2 | **No naranja**: chocaría con el ámbar de compra y le robaría aislamiento |
| Tenis | `#D4F53C` amarillo pelota | 15,9 / 14,3 / 12,8 | Reconocible al instante |

El acento solo va en el chip activo, los corchetes de esquina y la insignia de tipo; nunca en botones ni en estados de acierto.

### 2.4 Conversión sin patrones oscuros

Lo que **sí** se usa para convertir:
- **Prueba antes que promesa**: historial de acierto y sello de la cadena de hashes visibles junto al CTA («> SELLO 9f3a… VERIFICADO»).
- **Muestra gratuita real**: el 10 % gratis de Alta probabilidad ya existente, con la misma piel que el VIP; lo bloqueado se ve difuminado (decisión ya tomada en la web).
- **Una sola acción ámbar** por pantalla, con texto de verbo («Hazte VIP», «Desbloquear · 40 monedas»).
- **Probabilidad como número grande** en azul: el valor del producto es la cifra, no la emoción.

Lo que **no** se usa: contadores falsos, rojo parpadeante, «solo quedan X», confeti al perder, ni presentar cuotas como ganancia segura.

## 3. Lenguaje visual (CyberCore adaptado)

| Elemento | Decisión |
|---|---|
| Esquinas cortadas | `ShapeBorder` propio: tarjetas 14 dp, chips 8 dp (arriba-derecha y abajo-izquierda) |
| Corchetes de esquina | `CustomPainter`, 2 dp, color del deporte |
| Insignias | MAYÚSCULAS, borde 1 dp, relleno 15-20 % |
| Barras | rectas y segmentadas; la Escalera usa un segmento por escalón |
| Brillo | solo en un elemento por pantalla (chip activo o pick destacado), `BoxShadow` estático |
| Tipografía | **Rajdhani** titulares/chips, **JetBrains Mono** cifras y hashes, **Gilroy** cuerpo (OFL, empaquetadas) |
| Terminal | bloque del sello en el detalle |
| Glitch/scanlines/holograma | fuera del contenido; como mucho glitch de 300 ms al desbloquear y reflejo lento en la tarjeta VIP, apagados con `disableAnimations` |

ui-ux-pro-max (estilo `cyberpunk-ui`): solo oscuro, glitch sutil, scanlines opcionales, contraste ≥ 4,5:1, movimiento reducido. Su propuesta automática de «sistema de diseño» (rojo por bloques, para landing) no encaja y se descarta.

## 4. Navegación: el deporte es un filtro global

Fila fija bajo la cabecera con tres chips (icono + texto siempre visibles, 44 dp) que cambia Inicio, Predicciones y Mercados. Se descartan una pestaña por deporte (7 destinos) y una pantalla previa de deportes (un paso más cada vez).

Reglas:
1. Jerarquía **deporte → tipo de pronóstico → lista**. El selector de tipo pasa a **azul** (antes dorado) para dejar el ámbar solo a la compra.
2. Contador en el chip; último deporte recordado; deporte por defecto y ocultar deportes en Perfil.
3. Sin deslizamiento lateral entre deportes (ya lo usan los tipos de pronóstico).
4. Coins y Perfil sin fila. Con más de 4 deportes, fila desplazable y chip «MÁS».

## 5. Pestañas, una por una

Qué lleva fila de deportes: **Inicio, Predicciones y Mercados**. Coins, Perfil y VIP son comunes a todos los deportes. Los textos citados son los que ya existen en `app_es.arb`; los nuevos se marcan como (nuevo).

### Inicio
1. Avisos (banner y mantenimiento) igual que hoy; el banner deja el dorado y pasa a azul (es información, no compra).
2. Dos tarjetas resumen: «Mis monedas» (cifra mono, «40 para el próximo») y «Acierto histórico» **del deporte elegido** (cifra grande en azul, «142 de 200»).
3. «Boletos del día»: Alta prob. (insignia verde) y Parley (insignia azul) del deporte elegido; «Ver todo» lleva a Predicciones con ese deporte.
4. `DayStrip` con el contador por día **del deporte elegido**, y el calendario.
5. Agenda: fútbol por competición, NBA por hora, tenis por torneo → ronda. Cada fila: hora mono, partido, y a la derecha la probabilidad del pick (verde), el candado VIP (ámbar) o «—».
6. Buscador: «Busca equipos o ligas» → «Busca equipos, jugadores o torneos» (nuevo).

### Predicciones
Alta probabilidad en los tres deportes; Escalera y Parley según la pregunta 1; los segmentos que no existan se ocultan. Selector de tipo en azul.

### Mercados
1. Fila de deportes; cabecera «MODELO ACTIVO» (insignia verde) y «Evidencia al …».
2. Pestañas internas por deporte: fútbol PARTIDO | GOLES, NBA PARTIDO | JUGADORES, tenis PARTIDO | JUEGOS.
3. Una tarjeta por familia de mercado: nombre, % de acierto histórico grande en azul, barra segmentada de 10 tramos y «48/65 publicados».
4. «En revisión: sin línea confirmada» con insignia gris y reloj, sin barra.

### Detalle (hoja inferior)
Cabecera por deporte (NBA `VIS @ LOC` + disponibilidad; tenis marcador por sets + superficie/ronda/ranking/H2H), mercados del modelo, sello en bloque terminal y, si hay algo bloqueado, un único botón ámbar.

### Coins
Es la única pestaña donde el ámbar aparece más, porque toda ella trata de monedas; aun así hay **una sola acción ámbar**.
1. Saldo grande en mono, insignia «Racha de 4 días» y barra segmentada de desbloqueos («Tienes monedas para 3 desbloqueos», nuevo plural sobre `rewardsEnough`).
2. «Gana monedas hoy»:
   - «Asistencia diaria» con la semana en 7 casillas (hechas en verde con ✓, hoy con borde ámbar) y el botón ámbar «Marcar asistencia».
   - Vídeo con recompensa y «Ofertas para ganar monedas» como filas azules (+5, +n).
   - «Invita a tus amigos» con el código en mono.
3. «Mis movimientos» como fila plegada al final.

### Perfil
1. Tarjeta de cuenta: iniciales, correo enmascarado, verificación, insignia «Plan gratuito» / «Acceso VIP activo» y enlace ámbar «Ver planes VIP».
2. **«Mis deportes» (nuevo)**: lista para arrastrar y ordenar; el primero es el deporte por defecto; interruptor para ocultar cada uno.
3. «Preferencias»: Notificaciones (ahora **por deporte**, nuevo), Idioma, Formato de cuotas, Medición y errores.
4. «General»: versión, conexión.
5. Aviso fijo: «Una probabilidad no es una certeza. Decide con información y juega responsablemente.»

### VIP (pantalla desde la corona)
1. Insignia «ACCESO VIP» y la introducción, ampliada a fútbol, NBA y tenis.
2. **Acierto registrado por deporte** (tres tarjetas pequeñas con su acento y la cifra en azul), y debajo «cada pick sellado antes del partido». Es la prueba antes que la promesa.
3. Beneficios con icono azul: los cuatro actuales, más «NBA y tenis incluidos» (nuevo).
4. Planes: la tarjeta con «★ MEJOR PRECIO» con borde ámbar y precio equivalente por mes; precios siempre de la tienda (los de la maqueta son de relleno).
5. Un único botón ámbar «Suscribirme» y «Restaurar compras» como enlace azul.

### Menú lateral (☰)
Sin cambios de estructura; adopta la paleta y suma un acceso a «Mis deportes».

## 5 bis. Todas las ventanas y cómo se enlazan (prototipo navegable)

Prototipo con las 20 ventanas, cada una enlazada como en la app: [lienzo de diseño](https://claude.ai/artifact/MhCwwt744pDkBbbhJLvhr7) (modo Play para navegar). Enlaces comprobados con un script: ningún destino roto y toda ventana tiene al menos una entrada.

| Ventana (archivo Flutter actual) | Se llega desde | Lleva a |
|---|---|---|
| Idioma, primer arranque (`l10n/language_selection_screen.dart`) | arranque, botón de idioma de Acceso | Bienvenida |
| Bienvenida, 5 pantallas (`onbonding_screen/second_screen.dart`) | Idioma | Acceso (Saltar o Empezar) |
| Acceso con Google (`core/access_screen.dart`) | Bienvenida, Cerrar sesión | Inicio (solo con la casilla de consentimiento marcada; si no, error en línea), Términos y Privacidad |
| Actualización (`core/app_update.dart`) | el servidor (bloqueo de versión); en el prototipo, «Versión de la app» en Perfil | Google Play, Inicio (solo si es opcional) |
| Inicio (`product/live_home.dart`) | barra inferior | Partido (por deporte), Coins, Predicciones, Menú, VIP |
| Predicciones (`live_picks`, `live_ladder`, `live_parley`) | barra inferior, Inicio, Guía | Partido, Desbloquear, VIP; hoja de reglas del Parley |
| Mercados (`live_markets.dart`) | barra inferior | Detalle de mercado |
| Detalle de mercado (`live_market_detail.dart`) | Mercados | Partido, Desbloquear |
| Coins (`live_rewards.dart`) | barra inferior, monedas de la cabecera, Inicio, «Te faltan monedas» | asistencia, video, ofertas, invitar, movimientos |
| Perfil (`live_profile.dart`) | barra inferior, Menú | VIP, Preferencias, Idioma (hoja), Actualización, Acceso (cerrar sesión) |
| Partido · fútbol / NBA / tenis (`live_detail.dart` + `live_match_*`, `live_statistics`, `live_alerts`) | Inicio, Predicciones, Detalle de mercado, Avisos | Desbloquear, VIP, cerrar → Inicio |
| Desbloquear / Te faltan monedas (diálogos de `live_shell.dart`) | candados de Predicciones, Partido y Mercado | Partido (desbloqueado), Coins, VIP |
| VIP (`live_vip.dart`) | corona de la cabecera, Perfil, Partido, Predicciones, Desbloquear | Google Play, Restaurar compras, Términos |
| Menú Más (`live_more.dart`) | ☰ de la cabecera | Guía, Mis deportes (Perfil), evaluar, compartir, Términos, Privacidad |
| Guía (`live_guide.dart`) | Menú | Predicciones |
| Privacidad y preferencias (`core/firebase_preferences.dart`) | Perfil | Idioma, Avisos, derechos, eliminar cuenta (confirmación) |
| Avisos (`FirebaseInbox`) | Preferencias | Partido de cada aviso |
| Cambiar idioma (`l10n/language_picker.dart`) | Perfil, Preferencias | Perfil |

Novedades en ventanas que no estaban en la v3: notificaciones **por deporte** en Preferencias, avisos con etiqueta de deporte que abren su partido, Bienvenida y Acceso que nombran los tres deportes, Actualización que anuncia «NBA y tenis», y el error en línea cuando falta el consentimiento (en vez de un botón deshabilitado).

**Pantallas heredadas que no se rediseñan**: `sign_in/`, `log_in/`, `forget_password/` (plantilla original «gobet»), `product/market_screens.dart`, `product/match_detail.dart` y `product/profile_settings.dart`. Ninguna pantalla que se pueda abrir las importa. Propuesta: moverlas a `harness/archivo/` en un cambio aparte, con confirmación del titular.

## 5 ter. Miniaturas e imágenes

- **Inicio, imagen destacada**: tarjeta «Destacado del día» con dibujo de líneas de la cancha del deporte (campo, pista de baloncesto o pista de tenis) en el color del deporte, los dos escudos o jugadores grandes y la probabilidad en el centro. Se dibuja en la app con `CustomPainter`, como ya hace `welcome_art.dart`: no depende de imágenes con derechos.
- **Agenda**: cada fila lleva miniatura de 30 dp. Fútbol, escudo; NBA, logo del equipo; tenis, foto del jugador con su **bandera** en la esquina.
- **NBA, jugadores con pronóstico**: fila horizontal en Inicio con foto del jugador (56 dp), aro del color del equipo, insignia con la sigla del equipo, línea y probabilidad.
- **Origen de las imágenes: el servidor (decisión del titular, 30-oct).** El prototipo ya usa las reales del VPS:
  - Fútbol: `/web/escudos/{team_id}.png` (462 escudos en `/srv/quantfut/escudos` del contenedor de la API, fuente API-Football). La app ya los pide por el campo `escudo`.
  - NBA: logos de los 30 equipos en `frontend/imagenes/nba/{SIGLA}.png` (fuente TheSportsDB según `frontend/imagenes/manifiesto.json`). Hay que servirlos a la app con un campo `logo`, como `escudo`.
  - Tenis: 179 fotos en `frontend/imagenes/tenis/{nombre-apellido}.jpg`, de Wikimedia Commons con licencia **CC BY-SA**. El manifiesto guarda autor, licencia y página de origen: la app debe mostrar el crédito (el prototipo lo hace al pie de Inicio y en la ficha del partido). No hay foto de Sinner, Swiatek ni Gauff, entre otros: respaldo con iniciales y bandera.
  - Jugadores NBA: **sí hay retratos en el servidor**. `src/qf/api/imagenes.py` (desplegado; rama de origen `codex/imagenes-jugadores-web`) sirve `/web/imagenes/jugadores/nba/{player_id}.png`. Por identificador oficial de NBA descarga la foto de `cdn.nba.com/headshots`, la valida y la guarda en `ARTIFACT_DIR/public-images/jugadores/nba` (109 en caché el 30-oct). La caché se llena según se consultan los jugadores, así que un jugador nuevo se descarga la primera vez que se pide. Si falla: iniciales, sin usar la foto de otra persona. El prototipo usa retratos reales de esa caché (Brunson, Towns, Hart, Anunoby, Herro, Curry); por eso el partido NBA destacado pasó a ser Knicks @ Heat.
  - Fotos de futbolistas: el mismo servicio (`/web/imagenes/jugadores/futbol/{id}.png` y `sofascore/{id}.webp`), ya usado en alineaciones de la web.
  - **La app Flutter no tiene ninguna de estas fotos hoy**: sus recursos son iconos de la plantilla original. Debe pedirlas al servidor por URL, igual que `escudo`.
  - Las carpetas `frontend/imagenes/` solo están en las versiones desplegadas del VPS, no en la rama `nba/v13-disponibilidad`.
- **Iconos** (pedido del titular, 30-oct): el selector Alta prob. / Escalera / Parley recupera los iconos de la app actual (diana, escalera, boleto) encima del texto, con contador; los chips Fútbol / NBA / Tenis llevan su icono en Inicio, Predicciones y Mercados.
- **Repos de GitHub revisados el 30-oct** (complemento):
  - Banderas: [lipis/flag-icons](https://github.com/lipis/flag-icons) (MIT, SVG): **se pueden empaquetar en la app**.
  - Avatares de respaldo cuando no hay foto o logo: estilo de [boring-avatars](https://github.com/boringdesigners/boring-avatars) / [DiceBear](https://github.com/dicebear/dicebear) (MIT); en Flutter se generan con los colores del equipo y las iniciales (lo que muestra el prototipo).
  - Iconos: [Tabler](https://github.com/tabler/tabler-icons) (MIT).
  - Escudos y logos NBA: [football-logos](https://github.com/luukhopman/football-logos) y [React-NBA-Logos](https://github.com/ChrisKatsaras/React-NBA-Logos) **no tienen licencia** y además son marcas registradas: solo referencia. En la app llegan del servidor como hoy (`escudo`, se añaden `logo` y `foto`), con el avatar generado como respaldo. Las fotos de jugadores requieren una fuente con derechos (pregunta abierta 4; CLAUDE.md: derecho a la propia imagen).

## 6. Tarjetas

Base `QfCard`: `surface`, esquinas cortadas, corchetes del deporte. Estado con insignia + icono (GRATIS ✓ verde, VIP 🔒 ámbar).
- **NBA partido**: PARTIDO + estado de jugadores, `LAL @ BOS`, línea y total, barra de 2 lados, pick con probabilidad (azul) y cuota (texto).
- **NBA jugador**: mercado, «MÁS DE 24,5 · 68 %», barras de los últimos 5 partidos (verde = superó).
- **Tenis**: torneo y superficie, fila por jugador con ranking y probabilidad, H2H, pick.
- **Fútbol**: misma anatomía con la piel nueva.

Cambio de criterio: la **cuota** deja de ir en dorado (se confundía con «comprar»); va en texto principal con fuente mono. La **probabilidad** pasa a azul.

## 7. Cambios técnicos previstos (para el plan)

- `qf_theme.dart` con `ThemeExtension` de tokens (sección 2.2-2.3); las constantes `live*` pasan a ser alias temporales y luego se retiran.
- Piezas: `CutCornerShape`, `CornerBrackets`, `QfCard`, `QfBadge`, `SegmentedBar`, `ProbabilityBar` (2 o 3 resultados), `SealLine`, `SportSelector`.
- `SportKind` + registro `SportSpec` (icono, acento, segmentos, constructores); sin `if (sport == …)` dispersos.
- Icono de la app y `adaptive_icon_background` (`#090f1a` en `pubspec.yaml`) pasan a `#070B14`; revisar `image/quantfut_icon*.png` y la ficha de Play.
- Fuentes Rajdhani y JetBrains Mono en `fonts/`.
- Textos en los **6 idiomas** en el mismo cambio.
- Accesibilidad: `Semantics`, objetivos ≥ 44 dp, `disableAnimations`, color nunca como única señal.
- Servidor: `GET /mobile/v1/home?sport=…` (fútbol por defecto) y `config` con deportes activos y orden.
- Coherencia: la web (`frontend/`) debería adoptar los mismos tokens después, para que la marca sea una sola.

## 8. Orden de entrega sugerido

1. Paleta y piel nuevas sobre lo existente (fútbol se ve nuevo, funciona igual).
2. Selector de deportes + `SportSpec`.
3. NBA.
4. Tenis.
5. «HOY» y deporte por defecto.

Cada paso se prueba en el emulador (build release) y con las pruebas de traducciones. Recomendado: medir la conversión VIP antes y después del paso 1 con Firebase Analytics para comprobar el efecto con datos propios, no solo con la literatura.

## 9. Preguntas abiertas
1. ¿Escalera y Parley en NBA y tenis desde el inicio, o primero solo Alta probabilidad?
2. ¿Un Parley puede mezclar deportes?
3. ¿Chip «HOY» en la primera entrega?
4. ¿Fuente autorizada de fotos de jugadores, o iniciales y banderas?

## Fuentes
- Labrecque y Milne (2012): [Springer](https://link.springer.com/content/pdf/10.1007/s11747-010-0245-y.pdf)
- Gorn et al., «Waiting for the web»: [Bohrium](https://www.bohrium.com/en/paper-details/waiting-for-the-web-how-screen-color-affects-time-perception/812353235556761600-9605) · [EconBiz](https://econbiz.de/Record/download-times-on-the-internet-does-being-relaxed-make-time-go-faster-gorn-gerald/10014105745)
- Bagchi y Cheema (2013): [EconPapers](https://econpapers.repec.org/RePEc:oup:jconrs:doi:10.1086/666466) · [Virginia Tech](https://news.vt.edu/articles/2012/11/110812-pamplin-color.html)
- Stark et al. (1982): [Springer](https://link.springer.com/article/10.1007/BF03186749) · Spenwyn et al. (2010): [Springer](https://link.springer.com/article/10.1007%2Fs11469-009-9226-0) · Pontes y Williams (2020): [OUCI](https://ouci.dntb.gov.ua/works/42OERewl)
- Gnambs (2020), meta-análisis: [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC7704521/)
- Mehta y Zhu (2009): [PubMed](https://pubmed.ncbi.nlm.nih.gov/19197022/)
- Piepenbrock, tesis: [Düsseldorf](https://docserv.uni-duesseldorf.de/servlets/DerivateServlet/Derivate-31413)
- Diseño engañoso en apuestas: [revisión de alcance](https://revista.unifatecie.edu.br/index.php/conversas/article/download/683/524/2086)
- Navegación multideporte: [Sofascore](https://www.sofascore.com/news/sofascores-new-home-screen-a-smarter-faster-way-to-follow-sports) · [Pratt IxD](https://ixd.prattsi.org/2026/09/design-critique-sofascore-ios-app/) · [Flashscore](https://www.flashscore.com/faq/capabilities) · [MollyBet](https://www.flatstudio.co/work/mollybet)
