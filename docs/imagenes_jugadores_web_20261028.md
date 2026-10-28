# Imágenes visibles en fútbol, NBA y tenis

Se corrige la ventana de tenis para utilizar las fotos disponibles en lista y encabezado, y se añaden once retratos de API-Tennis vinculados por identificador de proveedor y el escudo de Eyüpspor (equipo interno 85064, proveedor 3588). Los créditos distinguen las imágenes de proveedor de las fotografías Creative Commons.

Los mercados individuales de NBA muestran el retrato del jugador por su identificador oficial, tanto en el destacado como en las tablas. El panel independiente `/nba` utiliza el mismo servicio. Las alineaciones confirmadas de fútbol incluyen fotos; cuando todavía no hay once confirmado, se puede consultar el último once registrado, claramente fechado y rotulado como pasado.

Las fotos nuevas se sirven desde el mismo dominio, mediante direcciones fijas de NBA.com, API-Football y SofaScore, con límites de tamaño, validación de PNG/WebP, tiempo máximo de descarga y caché persistente en `ARTIFACT_DIR/public-images/jugadores`. No se admiten URLs arbitrarias ni redirecciones. Un archivo ausente o una descarga fallida se sustituye visualmente por una marca accesible; no se presenta como una fotografía real. Los fallos de catálogo pueden reintentarse al actualizar la página.

Xinran Sun no tiene retrato en el proveedor: el campo de imagen está vacío y la comprobación del archivo correspondiente devuelve 404. Queda representada por iniciales con el aviso de imagen no disponible. No se usa la foto de otra persona. Esta limitación también aplica a cualquier jugador futuro que la fuente todavía no fotografíe.

Comprobación local: pruebas de la web, de la API de imágenes, de alineaciones y de caché; vista previa con datos públicos donde se verifican retratos NBA, logos y fotos de tenis sin desbordamiento. La entrega y la verificación del dominio se anotan en `DEPLOYS.md` una vez publicadas.

La comprobación posterior al primer despliegue detectó identificadores SofaScore en las alineaciones. Se restauró la API anterior antes de continuar. La corrección usa el campo `src` de cada jugador: los identificadores SofaScore van exclusivamente al CDN SofaScore; los de API-Football conservan su propio proveedor. Una fuente desconocida no produce URL de retrato. Hay pruebas de regresión para este caso.
