# Identidad de jugadores entre fuentes (Sprint 2b, parte B) — 5-nov-2026

Plan: `docs/tenis_plan_tecnico_20261105.md` §B.1–B.4. Base: esquema `tenis` (0001–0004, 0006–0007). Sin red, sin VPS, sin commit.

## Entregado

| Fichero | Contenido |
|---|---|
| `apps/tenis/src/tenis/identidad/normalizar.py` | Nombres: sin tildes, guion y apóstrofo pegados, partículas pegadas («De Minaur» = «Deminaur»); `nombre_clave` (igualdad sin importar el orden) y `claves_apellido` (apellido + inicial, en orden «Nombre Apellido» o «Apellido I.»). |
| `apps/tenis/src/tenis/identidad/resolver.py` | `ResolutorMultifuente.resolver(...)` con la firma pedida; `anular()` (corrige un alias con `anula_a`); `cargar_equivalencias()` (rechaza alias circulares, cadenas y filas sin evidencia). |
| `apps/tenis/src/tenis/identidad/cola.py` | `registrar()` idempotente en `sin_resolver` y `leer()`. Motivos válidos en `MOTIVOS`. |
| `apps/tenis/src/tenis/identidad/enlazar.py` | `medir()` (solo lectura), `pares_con_varios_jugadores()`, `csv_auditoria()`, `filas_tml()` (filas aceptadas por el cargador) y `edades_para_resolutor()`. |
| `apps/tenis/src/tenis/identidad/propuestas.py` | `proponer()`: equivalencias TML↔TML con evidencia fuerte. Puro, no escribe en la base. |
| `apps/tenis/ops/medir_identidad.py` | Modo medir (`--esquema`, `--fuente`, `--auditoria`) y modo propuestas (`--propuestas-tml`, `--salida`, `--puente`). |
| `apps/tenis/config/equivalencias.csv` | 35 equivalencias TML (ver abajo). |
| `apps/tenis/tests/test_identidad_*.py` | 42 pruebas: normalización (13), resolutor con esquema aislado (26), TML real con simulación (3, cada una en dos variantes). |

Resultado: suite completa `apps/tenis/tests`: **1016 pasadas, 9 omitidas** (las de roles, que necesitan un usuario que pueda crear roles), 0 fallos.

## Orden de decisión del resolutor

1. Alias vigente de (fuente, id) → se devuelve sin escribir nada.
2. Nombre + circuito + **país igual** + edad compatible. Sin país → `sin_pais`; sin fecha de nacimiento → `sin_edad`. La edad compara la fecha de nacimiento de la fuente con (a) las fechas ya asertadas de la persona y (b) la edad que TML declara en sus partidos. Compatible si ≤ 0,2 años en al menos la mitad de las comparaciones y ninguna > 1 año. Un solo candidato compatible → une (`nombre_fecha_nac`); dos o más → `ambiguo`.
3. Contexto del partido (solo si 2 no decidió): `contexto = {"rival_jugador_id", "fecha", "torneo"?}`; el candidato debe tener exactamente un partido con el rival a ±3 días → `contexto_partido`.
4. Equivalencia manual del CSV (solo si 2 y 3 no decidieron) → `manual`.
5. Si nada decide: jugador nuevo + fila en `sin_resolver`.

Motivos de cola: `ambiguo`, `sin_candidato`, `edad_contradictoria`, `edad_dudosa`, `sin_edad`, `sin_pais`, `confirmado_distinto` (mismo nombre y otro país), `manual_sin_principal`, `contexto_ambiguo`. Los tres primeros son los pedidos; el resto son añadidos y están documentados en `cola.MOTIVOS`.

## Medición sobre TML real (2025–2026, cargador real)

- **Verificación independiente:** pandas calcula las parejas (circuito, nombre normalizado, país) con más de un id a partir del CSV, excluyendo filas que el cargador rechaza. Coincide exactamente con `medir()`: **51 parejas**.
- **Simulación de SofaScore:** 150 personas reales de TML (fecha de nacimiento = fecha del torneo − edad de TML; 10 % con ruido de ±60 días; nombres con orden alterado y tildes) + 20 homónimos inventados de otro país.

| Carga | Unidos correctamente | Ambiguos | Uniones erróneas | Contradictorias | Homónimos separados |
|---|---|---|---|---|---|
| Sin equivalencias | 140 / 150 (93,3 %) | 10 | 0 | 0 | 20 / 20 |
| Con las equivalencias del repo aplicables a la muestra (34) | 148 / 150 (98,7 %) | 2 | 0 | 0 | 20 / 20 |

Los «ambiguos» son personas con dos ids de TML y edad compatible. Sin equivalencias el resolutor elige no unir: es lo correcto.

## Equivalencias propuestas (`config/equivalencias.csv`, 35)

**Evidencia exigida (todo a la vez):** mismo nombre normalizado y mismo país y circuito; al menos una fila con edad válida en cada id y al menos dos entre ambos; fecha de nacimiento estimada (fecha del torneo − edad) con diferencia ≤ 0,2 años (en las 35 la diferencia es de 0,00–0,001); el principal aparece en un fichero **anterior** al alias (requisito del cargador: si no, `jug.get` falla y la carga se aborta). Las filas se cuentan con el mismo `analizar_fila` del cargador.

Riesgo declarado: en **18 de 35** el alias tiene una sola fila con edad válida. Es evidencia fuerte por coincidencia de fecha de nacimiento, pero no es una prueba documental.

**Distintos confirmados por edad (7; no se unen):** Andy Garcia (G004/G0H9, 31,7 años), Michael Grant (36,0), Miguel Tobon (38,0), Pedro Araujo (27,3), Robert Casey (8,1), David Warren (5,9), Quentin Robert (2,9).

**Dudosas (25; no entran):**
- 21 con `sin_edad_suficiente`: Derek Schroder S243, Dan Cassidy C022, Milan Vopicka V188, Seung-Hoon Lee L404, Dekel Valtzer V385, Dayana Yastremska 324261, Jaqueline Cristian 320319, Panna Udvardy 325956, Emma Navarro 325410, Katie Volynets 327391, Alexandra Eala 330332, Nikola Bartunkova 330364, Daria Snigur 327845, Hanne Vandewinkel 331102, Daria Kasatkina 322082, Lois Boisson 328884, Polina Kudermetova 328897, Elena-Gabriela Ruse 320408, Bernd Haberleitner H376, Enrique Pena P0IZ, Andre Ilagan I0A0.
- 4 con `principal_no_carga_antes`: Mary Stoiana 223168, Kaitlin Quevedo 259733, Kamilla Rakhimova 325936 y Reese Brantmeier 329512. **El cargador no puede aplicarlas tal como están**: el principal aparece en el mismo fichero o después.

**Puente antiguo (`identity_bridge_v3`, 5 fusiones):**
- Mika Stojsavljevic 333132 → 261963: propuesta igual.
- Quevedo, Stoiana y Brantmeier: bloqueadas por el orden de carga (arriba). Brantmeier está invertida en el puente (222034 → 329512).
- Harshana Godamanna G793 → 104631: **no propuesta**. En TML el país es distinto (ECU frente a SRI) y el puente no lo exigía. Se deja como dudosa.
- Confirmados distintos del puente (14): los que aparecen en la salida de `propuestas` (Andy Garcia, 31,7 años; David Warren, 5,9 años) coinciden con la diferencia de edad. Los demás no se han contrastado uno a uno.

## Supuestos y decisiones

1. **Las edades de TML no se guardan en la evidencia** (el cargador no las persiste y no se pueden añadir migraciones). El resolutor recibe un proveedor `edades(jugador_id)`. `enlazar.edades_para_resolutor(cur, filas_tml(...))` lo reconstruye desde los CSV. **Sin ese proveedor, la regla 2 nunca une por nombre**, porque TML no trae fecha de nacimiento. Hay que decidir si se persiste la edad (requiere migración) o si el cargador de SofaScore lee los CSV.
2. Búsqueda de candidatos sin claves inversas. Una primera versión generaba «Carlos» como apellido y unía a «Carlos Alcantara» con «Carlos Alcaraz»; lo detectó una prueba y se corrigió.
3. Edad válida de TML: 14–50. Hay valores basura (p. ej. 3387 años en ids alternos).
4. Anulación: fila nueva con `anula_a`; `jugador_alias_a_las` la muestra y la vieja queda en la base. Probado.
5. Un único escritor por proceso: el índice en memoria no se relee.
6. La manual (paso 4) no sobreescribe una decisión automática de los pasos 2–3.
7. Mano y altura: se aceptan R/L/U/D/Z y altura de 2–3 dígitos.

## Pendiente y no verificado

- **El cargador de TML no consulta `jugador_alias` de otras fuentes.** Un jugador de SofaScore creado antes de cargar TML duplicaría la persona. Hay que cargar TML primero o que TML llame al resolutor. `src/tenis/carga/` no se ha tocado.
- **La carga completa con las 35 equivalencias no se ha ejecutado** (≈400 s). La comprobación de orden se hizo con el mismo criterio que el cargador, sobre el snapshot completo, y la prueba usa la muestra 2025–26 con las equivalencias aplicables.
- El cargador de SofaScore todavía no existe en el repo (el de otro agente lo usará con la firma de `resolver`).
- No se han revisado a mano las 25 dudosas.

## Cómo reproducir

```
powershell -NoProfile -File "C:\Users\huye\Documents\apuesta proyec\data\tennis\rediseno_20261104\correr_pytest_tenis.ps1" apps/tenis/tests -k identidad -s
python apps/tenis/ops/medir_identidad.py --propuestas-tml <tml/originals> --salida <csv> --puente <identity_report.json>
PG_DSN=... python apps/tenis/ops/medir_identidad.py --esquema <esquema> --fuente sofascore --auditoria <csv>
```
