# QuantFut · frontend de demostración

Prototipo navegable para revisar la dirección visual de la futura web. Usa
HTML, CSS y JavaScript nativos; no requiere instalación. Al servirlo desde
FastAPI, los paneles señalados como reales consultan únicamente endpoints
públicos del mismo origen; el servidor Node local no simula la API.
Se inspira en la distribución de Pitchverse (menú lateral, navegación clara,
tarjetas sobrias y verde sobre fondo oscuro), pero emplea marca, textos y
componentes propios de QuantFut.

La guía de colores, tipografía, componentes, comportamiento móvil y
accesibilidad está en [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md). Se consultó el
catálogo público de UI UX Pro Max como referencia de criterios; no se añadió
como dependencia ni se copió una plantilla.

## Abrir

Con Node.js instalado:

```bash
cd frontend
npm run dev
```

Abrir `http://127.0.0.1:5173`. `npm run check` valida la sintaxis JavaScript
y comprueba los estados de carga, vacío y error de la integración pública.
El servidor solo escucha en `127.0.0.1`: **no es un despliegue de producción**.

También se sirve desde el FastAPI existente en `/` al levantar `uvicorn
qf.api.main:app` o el servicio `api` de Docker Compose. El servidor Node
anterior queda como vista previa local, no como un segundo backend.

## Qué funciona en la demo

- Siete vistas: inicio, mesa de mercados, picks, ficha de partido, historial,
  planes y espacio personal.
- **Mesa de mercados** (composición inspirada en propsbr.app, contenido
  propio): partidos por fecha y liga a la izquierda, tabla ordenable de ~20
  selecciones por partido (1X2, doble oportunidad, totales, ambos marcan,
  goles por equipo, hándicap asiático ±1) con modelo, precio justo de
  Pinnacle sin margen, mejor casa de la lista, % sobre el justo, cuota
  mínima, minigráfico y estado; columna con la sombra del criterio. Cada
  fila abre un panel lateral con pestañas Resumen / Casas / Modelo /
  Registro.
- Vistas rápidas en la mesa (estructura copiada de PropsBR tras revisar sus
  nueve botones): **Pick del día** (la mejor candidata 1X2, ventana de venta
  que se cierra al inicio, métricas y su historial con ✓/✗, unidades y
  CLV), **Todas**, **Top ventaja**, **Top probabilidad** y **Combinadas**.
- Combinadas con pestañas Todas / ~2X / ~3X / Cortas 1,50–2,30 / Arma la
  tuya. Las armadas se generan solas: 2 a 5 partidos distintos cuyas
  selecciones pagan el justo o más en la MISMA casa. «Arma la tuya» usa el
  «+» de cada fila (una por partido, máximo 6) y compara la cuota combinada
  en cada casa.
- Los precios demo salen de dos lambdas por partido (Poisson) y del mismo
  criterio que `publish/picks.py`: candidata solo en 1X2 con ≥ +2% sobre el
  justo en el mismo snapshot, partido excluido si Pinnacle se aparta más de
  un 3% del consenso, un pick por partido. Así mesa, picks y ficha cuadran.
- Picks con casa, cuota, mínimo, % bruto y esperado al cierre; los Plus se
  muestran bloqueados sin contenido. La ficha tiene pestañas Resumen /
  Mercados / Casas 1X2 / Modelo (marcador exacto) / Registro.
- Formato de cuota decimal o americana y «Mis ligas», guardados solo en el
  navegador (`localStorage`, con respaldo si no está disponible).
- Cabecera fija arriba con el menú ordenado por grupos (Explorar · Evidencia ·
  Acceso); en móvil, barra inferior con menú «Más».
- En inicio, picks e historial aparece primero un panel de datos reales:
  `/model-card`, `/picks/free`, `/track-record`, `/calibration` y `/chain`.
  Cada fuente informa por separado si está vacía o no disponible. La portada
  distingue ofertas capturadas, primeras candidatas y candidatas con cierre
  justo: solo estas últimas cuentan para la puerta comercial. La web
  verifica tanto la autorización de la sombra del criterio como la publicación activa antes
  de mostrar un pick público; nunca consulta `/v1/*`.
- Historial ficticio, claramente separado del real, con periodo y tamaño de muestra visibles, pérdidas sin
  ocultar, cuotas registradas y de cierre y CLV calculado sobre esos ejemplos.
  RPS, calibración y hashes reales figuran como pendientes, no simulados.
- Diálogo explicativo del futuro acceso premium y sesión visual de invitado.
- Recorrido interactivo de identidad ficticia, evidencia y checkout bloqueado
  en Planes; muestra el estado de acceso en Mi espacio sin pedir correo o
  tarjeta ni entregar picks privados. El contrato para las futuras cuentas,
  sesiones y webhook está en [ACCESS_FLOW.md](ACCESS_FLOW.md).

Las cifras de los paneles marcados «API pública» vienen del servidor. Todos
los equipos, porcentajes, picks y resultados de las demás secciones siguen
siendo **ficticios**. El prototipo no autentica usuarios, no cobra, no coloca
apuestas y no desbloquea contenido privado. Si la API no está disponible, los
paneles reales muestran un error; no sustituyen el vacío con datos de demo.

## Integración posterior

Decisión actualizada (2026-09-23): QuantFut usará un único FastAPI modular
para la API, las páginas y el futuro control de suscripciones. El panel
interno inicial está en `/control`, solo lectura y con credenciales separadas;
además, Caddy restringe `/control` y `/admin` por IP. Configura
`ADMIN_CONSOLE_USER` y `ADMIN_CONSOLE_PASSWORD_HASH` en `.env`; genera el hash
interactivamente con `python scripts/hash_admin_password.py`. Usa una clave
ASCII de al menos 16 caracteres. No pongas la contraseña ni su hash en JS.

La mayor parte de la web sigue siendo una demo de datos ficticios. Las cuentas de suscriptor,
pagos y autorización de picks premium se implementarán en módulos servidor
después de la validación comercial. Los endpoints `/v1/*` conservan
`SERVICE_TOKEN` y nunca se consumen desde el navegador.

Nota histórica (2026-09-22; sustituida por la decisión anterior):

El navegador deberá hablar con un backend web propio (BFF), no con `/v1/*`
de FastAPI. Ese BFF comprobará cuentas y suscripciones, mantendrá
`SERVICE_TOKEN` exclusivamente en servidor y solicitará los picks autorizados.
Las páginas públicas podrán presentar el historial, la calibración y la
cadena de hashes de la API actual. La activación comercial queda supeditada
a la puerta de CLV documentada en el README principal.
