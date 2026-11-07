# apps/tenis: contratos y almacén de originales (Sprint 1, parte B)

Paquete nuevo `tenis` (src/tenis). No toca `apps/tennis/` (motor actual), `src/`, ni `db/`.

## Contenido

- `src/tenis/contratos/base.py`: `Contrato` (strict, extra=forbid, frozen, sin NaN/inf), `Instante` (con zona), `Prob`, `ProbPunto` (0,1 abierto), `Hash256`, `DuracionMin`.
- `contratos/matriz.py`: covarianza 2x2 o 3x3, simétrica y definida positiva (Cholesky, sin numpy).
- `contratos/marcador.py`: física del marcador (G.6): reglas de set, partido y totales.
- `contratos/entrada.py`: `PartidoPrevio`, `EstadoJugador`, `ParametrosPunto`.
- `contratos/mercados.py`: mercados derivados y su recálculo desde la conjunta.
- `contratos/salida.py`: `DistribucionPartido`, `PronosticoSellado`.
- `contratos/validar.py`: `validar_antes_de_sellar`, `validar_antes_de_servir`, `ContratoInvalido`.
- `src/tenis/almacen.py`: `guardar_objeto`, `leer_objeto` (objetos por contenido, escritura atómica).
- `src/tenis/recibo.py`: `Recibo`, `nuevo_recibo` (rechaza parámetros con nombre de secreto).

## Supuestos

1. Reglas del set decisivo (F.3): mejor de 3 admite `tiebreak_7`, `tiebreak_10` y `ventaja`; mejor de 5 admite `tiebreak_10` y `ventaja`. Un decisivo `tiebreak_7` en mejor de 5 se rechaza porque F.3 no lo lista.
2. Los sets no decisivos siempre son con tiebreak a 7 en 6-6. El set decisivo es el 3.º en mejor de 3 y el 5.º en mejor de 5, y solo existe si se juega.
3. Set 8-6 (y 9-7, etc.): rechazado fuera del formato de ventaja, aceptado en `ventaja` (G.6 admite sets de ventaja). Con tiebreak, solo 7-6 con `tiebreak=True`; 7-6 sin tiebreak se rechaza.
4. El mínimo de 18 juegos con 3 sets en mejor de 3 se cumple por construcción (cada set ganado tiene ≥ 6 juegos). Se comprueba también con `validar_totales`, que tiene prueba directa (17 rechazado, 18 aceptado).
5. Totales de G.6 aplicados: mejor de 3, T en [12, 39]; mejor de 5, T en [18, 65], con 4 sets T ≥ 24 y con 5 sets T ≥ 30.
6. `superficie=Indoor` exige `indoor=True`. `indoor=None` (desconocido) se admite con el resto de superficies.
7. El corte debe ser estrictamente anterior al inicio programado más temprano. No se fuerza el orden canónico de `jugador_1 < jugador_2`: A.3 lo asigna a la capa de base de datos.
8. Las entradas de la distribución tienen probabilidad > 0 (sin filas con 0) y no se repiten. La suma debe ser 1 ± 1e-9.
9. Mercados declarados: ganador, 1.er set, total de sets, total de juegos y hándicap de sets. El hándicap de juegos de G.4 no está. Las líneas van como texto (`"22.5"`), porque JSON no admite float como clave.
10. `PronosticoSellado`: la posición 1 es la única sin `hash_previo`. El contrato valida el formato del hash, pero no lo recalcula: eso lo hará la capa de sellado.
11. `DuracionMin` (> 0 y ≤ 1440) es un tipo sin consumidor todavía; el resultado llega en S2.
12. Nombres de parámetros prohibidos: key, token, secret, password. Añadido `auth` por prudencia.
13. El almacén acepta cualquier contenido en bytes; el nombre `.json.gz` es convención del plan. Publica con `os.link`, que falla si el destino existe, después de fsync del temporal en el mismo directorio. Un corte deja como mucho un `.*.tmp` huérfano, nunca un objeto truncado en la ruta definitiva.
14. La prueba de corte simula el fallo inyectando una excepción antes de `os.link`, no matando un subproceso.

## Pruebas

`powershell -NoProfile -File ...\correr_pytest_tenis.ps1 apps/tenis/tests -k "contratos or recibo"`: 722 aprobadas, 0 fallidas. La prueba de física por fuerza bruta (0–8 por lado, 3 contextos de regla, con y sin tiebreak) usa una tabla escrita a mano, no el código de `src`.
