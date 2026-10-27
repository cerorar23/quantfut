# Web: publicaciones reales con el diseño anterior — 27-oct-2026

La portada seguía enseñando un catálogo ficticio aunque el motor real ya estaba activo. Comprobación de producción a las 13:43 UTC: modelo `2026.10.26-020600`; corrida diaria 09:00 UTC del 27-oct con cuatro predicciones, alta probabilidad, escalera y parley sellados en el lote `fa382d6b342e0d591938c57713610d0d788f6b8173488ccc0a0fa4a16222a929`. El contrato público de la app devuelve cuatro pronósticos gratuitos y cinco bloqueados.

## Corrección

La web lee `/mobile/v1/home` y `/mobile/v1/matches/{id}` con el mismo recorte por sesión que la app. Las probabilidades 1X2, selecciones, cuotas, casas, horas y hashes proceden del servidor. Se conservan CYBERCORE CSS 0.3.0, `styles.css`, `future.css` y `membership.css` sin cambios. Se retira el catálogo ficticio y se reemplazan sus vistas de inicio, mercados, pronósticos e historial. Se conservan estadísticas, cuentas, planes, alta probabilidad, escalera y parley existentes.

Una fuente caída o un pronóstico futuro sin calcular queda explícitamente sin datos. No se generan precios, no se calcula una ventaja sobre probabilidades inventadas y los campos VIP no se renderizan aunque llegasen datos adicionales por error. Los cambios de sesión invalidan la caché y se actualizan los datos cada 90 segundos mientras la web está visible y no se está editando un formulario.

## Estado del motor

No hace falta encender ni reentrenar el modelo: ya generó y selló la jornada. La publicación del producto de alta probabilidad está activa. Los picks de valor son un producto separado: la puerta de CLV sigue con 264 resultados con cierre justo, por debajo del mínimo de 300; no se modifica el interruptor ni se evita esa puerta. No se altera el orden de sellado, la base, el cron, los productores NBA/tenis ni se consumen créditos de proveedores.

## Verificación

- 44 pruebas frontend aprobadas, incluidas las de inicialización, fuentes reales, vacío/error, probabilidades, sellos, escapes y bloqueo VIP.
- Vista local conectada solo a los endpoints públicos reales: cuatro selecciones visibles, cuatro filas de agenda del día con probabilidades, ficha con un mercado abierto y los restantes protegidos; consola sin errores.
- Publicación prevista únicamente de los archivos frontend afectados y la ruta estática de `real-views.js` en `web.py`, sobre la imagen API actual. Antes: verificar hashes contra main y respaldar. Ensayo aislado y vuelta atrás según `DEPLOYS.md`.
