# QuantFut · guía visual de la demo

Esta guía toma como referencia el catálogo de patrones, tipografía, componentes
y comprobaciones de UX de [UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)
(consultado el 2026-09-24). No se instala ni se copia como dependencia. La
identidad, la arquitectura y el contenido son propios de QuantFut.

## Intención

**Un cuaderno de partido verificable, no una casa de apuestas.** La primera
lectura debe responder: qué partido se analiza, qué probabilidades se estiman,
cuándo se calculó y dónde se comprueba el resultado. La interfaz puede ser
atractiva sin insinuar beneficios garantizados. Hasta superar la validación,
todo dato de la demo lleva contexto de muestra ficticia; planes y acceso
premium son vistas ilustrativas, sin cobro ni autenticación real.

## Sistema visual

| Papel | Token / valor | Uso |
| --- | --- | --- |
| Fondo | `--bg-main: #0b132b` | Azul noche de la paleta aportada por el usuario |
| Navegación | `--sidebar: #101b35` | Cabecera y tablero |
| Superficie | `--bg-surface: #1c2541` | Tarjetas y paneles azul pizarra |
| Separador | `--border-color: #3a506b` | Bordes de baja intensidad |
| Texto | `--text-primary: #f8fafc` | Titulares y cifras principales |
| Texto secundario | `--text-muted: #94a3b8` | Metadatos y explicación |
| Acción | `--accent-cta: #10b981`, hover `#059669` | Verde esmeralda en acciones y estados activos |
| Comparación | `--accent-data: #38bdf8`, `--yellow: #d8b874` | Datos comparables y empate; siempre con etiqueta |
| Riesgo | `--status-loss: #ef4444` | Token de pérdidas/riesgo; texto claro para legibilidad |

Tipografía: serif Georgia en titulares editoriales de portada, paquetes, suscripciones y cuenta; sans del sistema para lectura y títulos de datos; monoespaciada del sistema
solo en porcentajes, fechas y etiquetas cortas. Escala: título de página
`clamp(30px, 3vw, 44px)`, título de panel 18–22px, texto 14–16px y metadatos
11–12px. Evitar párrafos completos en monoespaciada o texto esencial de 9px.
Espaciado en múltiplos de 4px; tarjetas con radios de 12–18px y bordes finos.
Las líneas de cancha son una textura sutil, nunca decoración sobre datos.

## Componentes y jerarquía

1. **Portada (2026-10-07):** propuesta de valor breve, resumen de agenda demo,
   estado de publicación visible, accesos rápidos y tablero con calendario de
   siete días, búsqueda, filtros por liga/estado y orden por hora o diferencia
   de precio. Filas agrupadas por competición con probabilidad 1X2, mejor cuota
   para la selección mostrada, casa, precio justo y estado. La fecha y los
   filtros afectan solo a la agenda demo. Debajo se conserva la agenda real de
   hoy y el detalle desplegable de la puerta comercial; los fallos de API se
   muestran explícitamente. No se etiqueta como finalizado un partido solo por
   haber empezado.
2. **Ficha de partido:** identidad del encuentro → probabilidades 1X2 del
   modelo y referencia de mercado en paneles separados → contexto y goles
   esperados → precio y cronología de captura/publicación/inicio. La
   diferencia no se llama ventaja sin validación.
3. **Picks:** partido, selección, cuota registrada, precio mínimo, hora y
   estado; la etiqueta «demo» permanece visible. El enlace lleva a la ficha,
   no a un boleto de apuestas.
4. **Historial:** filtros y tabla de resultados con hora de publicación,
   precio de cierre, muestra y periodo identificables. La demo indica que no
   tiene hashes reales; no es una prueba de rendimiento. No esconder pérdidas
   ni convertir un promedio aislado en promesa de rentabilidad.
5. **Suscripciones y Mi cuenta:** tarjetas seleccionables de 1/3/6 meses,
   opción Club y resumen de pedido lateral, apilado en móvil. Acceso en dos
   columnas con pestañas de login/registro y recuperación. Panel con cinco
   secciones, navegación horizontal en móvil y preferencias existentes.
   Los campos de identidad son ficticios y de solo lectura; la selección
   nunca se presenta como pago o suscripción activa.
6. **Mesa de mercados:** lista de partidos → tabla densa → detalle lateral.
   Se ordena por defecto por diferencia con el precio justo, con las
   candidatas primero y lo excluido o cerrado siempre al final. El modelo
   es una columna de diagnóstico, nunca el criterio de orden.

   Vistas rápidas encima de la mesa: **Pick del día** (el producto de pago:
   una selección, su mínimo, la hora de cierre de la venta y el historial
   completo debajo), **Todas**, **Top ventaja** (las 10 que más pagan sobre
   el justo), **Top probabilidad** (las 10 con mayor probabilidad justa, con
   aviso de que probable no es rentable) y **Combinadas** (armadas ~2X/~3X/
   cortas y manual; siempre una selección por partido y precio de una sola
   casa, porque la combinada se juega entera en una). Una combinada armada
   vacía se enseña vacía: no se rellena con selecciones bajo el justo.

Etiquetas prohibidas, aunque la competencia las use: «certera», «segura»,
«top confianza» o cualquier nota 0-100 sin calibrar. Los estados de una
selección son `Candidata ≥ +2%`, `Bajo el umbral`, `Solo referencia`,
`Sin cuota blanda`, `Excluido · Pinnacle` y `Mercado cerrado`, siempre con
texto y no solo con color.

Los estados de datos futuros deben distinguir `sin datos`, `pendiente`,
`publicado` y `liquidado`, además de `cargando` y `error`. El color nunca es
la única señal; cada estado tiene texto. El contenido privado se autorizará en
el FastAPI modular, no con CSS o secretos dentro de JavaScript.

## Móvil y accesibilidad

- Escritorio: cabecera fija (`position: sticky`) con marca y acciones en la
  primera fila y el menú por grupos en la segunda; bajo 1180px se ocultan las
  etiquetas de grupo y bajo 1000px los iconos, para que quepa sin desplazar.
  Paneles en dos columnas cuando dispongan de anchura. Hasta 760px: barra inferior con Inicio, Picks,
  Partido, Historial y «Más» para Planes y Mi espacio; las tarjetas se apilan.
  El menú adicional conserva el foco y se cierra con Escape. Hasta 570px:
  tres fechas relevantes y controles de ancho completo cuando sea necesario;
  ninguna cifra esencial debe cortarse.
- Objetivo táctil de al menos 44×44px en acciones principales. Foco visible,
  enlace para saltar al contenido, `aria-current` en la navegación y
  `aria-pressed` en filtros. Al cambiar de vista, el foco pasa al contenido.
- Las barras de probabilidad complementan porcentajes escritos; no reemplazan
  etiquetas. La tabla del historial mantiene encabezados y desplazamiento
  horizontal en pantallas estrechas. El diálogo devuelve el foco al control
  que lo abrió y se cierra con Escape.
- Respetar `prefers-reduced-motion`. Comprobar teclado, zoom al 200%, anchuras
  320/390/768/1440px y contraste antes de publicar cualquier cambio.

## Límites de esta fase

La web actual es HTML, CSS y JS servidos por FastAPI o por el servidor local
de vista previa. No añade framework ni servicios. Los equipos, porcentajes,
cuotas, resultados y CLV del prototipo siguen siendo ficticios. La web
comercial y los cobros continúan condicionados a la puerta de validación
documentada en el README principal.
