# Tenis v2: registro del artefacto `tenis-2.1+55c17ba1c6e2` (preparado el 17-nov-2026, NO ejecutado)

El plan (§H.1) exige el OK del titular en el chat para activar un artefacto. Aquí queda todo preparado; **no se ha escrito nada en ninguna base**.

## El artefacto

| | |
|---|---|
| Fichero | `apps/tenis/artefactos/tenis-2.1-capa-edad.json` (18 KB; viaja en la imagen del motor) |
| `sha256` (huella del contenido) | `55c17ba1c6e28445b0e99b2bfab64c1d7b681766c29d6574c62089a488f41f94` |
| `version_modelo` | `tenis-2.1+55c17ba1c6e2` (plan §H.2: `tenis-2.<menor>+<sha12>`) |
| Contenido | Los hiperparámetros del 7-nov (R con σ_R = 0, c_inf, P, λ = 0,5) **más** la capa de edad (ATP b = 0,9603, β = −0,166; WTA b = 0,979, β = −0,152) |
| Informe | `data/tennis/rediseno_20261104/modelo_s3/evaluacion_wf_capa_edad.json` (walk-forward 2019-24, reserva 2025-26 intacta) |

La validación (`registrar_artefacto.py validar`) comprueba: huella íntegra, `psi_r`/`psi_p`/`lbar`/capa de ambos circuitos, que el informe corresponda al artefacto
base (huella sin la capa), `G_linea_base`, `G_cordura` y `G_capa_edad`. **Advertencia, no bloquea:** `G_calibracion` de ATP no pasa por IC (pendiente 0,902 antes de la capa,
0,961 con ella); ya estaba aceptada por el titular (Opción 1).

## Qué cambia respecto a lo que había

- `motor.cargar_artefacto_activo` ya **no** tiene ruta fija ni respaldo: solo acepta un fichero de `TENIS_ARTEFACTOS_DIR` (la imagen: `/app/apps/tenis/artefactos`)
  cuya huella recalculada coincida con la registrada. Si ninguno coincide: alerta `contrato_roto` y no se sella nada (plan §H.2).
- `python -m tenis.motor` hacía solo un `print`; ahora ejecuta una pasada real (`--dsn` o `PG_DSN`, `--esquema tenis`, `--dry-run`). Código de salida 1 si no pudo.
- La imagen copia `apps/tenis/artefactos/`.
- Las tablas `artefacto` y `artefacto_activo` son solo-anexar; el motor solo las lee. Registrar exige un rol que pueda insertar (administrador).

## Antes de activar (bloqueos reales)

1. **Fusionar el PR #505** a `main` (producción = `main`, `DEPLOYS.md`).
2. **La base `tenis` real no tiene datos cargados** (carga TML/SofaScore pendiente de tu OK, `harness/tareas.md`). Sin datos el motor omite todo con `sin_historia_ni_ranking`.
3. Construir la imagen `tenis-motor:<tag>` y ejecutar `ops/ensayo_operativo.sh` (colector y pasada `--dry-run` a mano). Anotar en `DEPLOYS.md` la imagen y su vuelta atrás
   (`imagen_actual` con el nombre completo `tenis-motor:<tag>`, nunca solo la etiqueta).
4. Una pasada cuesta ≈ 3 min (lectura de toda la base + filtro) y solo corre si hay partidos en ventana.

## Orden de ejecución (cuando des el OK)

```bash
# 1. Validar (no toca la base)
python apps/tenis/ops/registrar_artefacto.py validar \
  --json apps/tenis/artefactos/tenis-2.1-capa-edad.json --informe <evaluacion_wf_capa_edad.json>

# 2. Ver lo que haría (sin --ejecutar)
python apps/tenis/ops/registrar_artefacto.py registrar --json ... --informe ... \
  --imagen tenis-motor:<tag> --aprobado-en-chat "<texto exacto de tu OK>"

# 3. Registrar y activar (rol administrador; el DSN no se imprime)
PG_DSN=<dsn admin> python apps/tenis/ops/registrar_artefacto.py registrar ... --ejecutar

# 4. Comprobar: una pasada en seco y la salud
python -m tenis.motor --dry-run
```

## Vuelta atrás

Otra fila de activación apuntando al artefacto anterior (nunca UPDATE):

```bash
python apps/tenis/ops/registrar_artefacto.py reactivar --sha256 <sha del artefacto anterior> \
  --imagen tenis-motor:<tag anterior> --aprobado-en-chat "<OK>" --ejecutar
```

Con la imagen anterior (`imagen_actual.anterior`) el motor vuelve a cargar el fichero con la huella del artefacto anterior (ambos ficheros pueden convivir en el directorio).

## Pruebas

`tests/test_artefactos.py`: validación (rechaza informe ajeno, compuerta que falla, capa sin compuerta, fichero alterado), registro anexado con aprobación obligatoria,
imagen con formato, doble registro rechazado, vuelta atrás, carga por huella, cargador estricto, `ejecutar_pasada_motor` sin artefacto verificable y `motor.main` con código de salida.
