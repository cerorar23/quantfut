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
| Fondo | `--bg: #0b130f` | Lienzo oscuro, no negro puro |
| Navegación | `--sidebar: #101c15` | Menú lateral de escritorio |
| Superficie | `--panel: #101d15` | Tarjetas y paneles de datos |
| Separador | `--border: #294132` | Bordes de baja intensidad |
| Texto | `--text: #ecf4ed` | Titulares y cifras principales |
| Texto secundario | `--muted: #a4b4a8` | Metadatos y explicación |
| Acción | `--green: #75ba79` | Botones, foco y estado activo |
| Comparación | `--yellow: #d8b874`, `--cyan: #5cc5b2` | Empate y visitante; siempre con etiqueta |

Tipografía: sans del sistema para lectura y títulos; monoespaciada del sistema
solo en porcentajes, fechas y etiquetas cortas. Escala: título de página
`clamp(30px, 3vw, 44px)`, título de panel 18–22px, texto 14–16px y metadatos
11–12px. Evitar párrafos completos en monoespaciada o texto esencial de 9px.
Espaciado en múltiplos de 4px; tarjetas con radios de 12–18px y bordes finos.
Las líneas de cancha son una textura sutil, nunca decoración sobre datos.

## Componentes y jerarquía

1. **Portada:** propuesta de valor breve, ficha 1X2 de demostración visible
   desde el primer pantallazo y dos acciones: ver análisis y ver evidencia.
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
5. **Planes y espacio personal:** enseñar el recorrido futuro sin simular un
   pago exitoso, una cuenta real ni contenido premium recibido en el cliente.
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
