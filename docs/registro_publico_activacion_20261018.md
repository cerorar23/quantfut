# Registro público de la cadena (comprometer-revelar) — preparación y activación

Estado al 2026-10-18 22:10 UTC: **activado** (worker recreado desde `main` por orden del titular; ver `DEPLOYS.md`). Los 19 lotes históricos están apartados en `historico_sin_publicar/` y NO se publican hasta que el titular lo decida.

## Hecho (18-oct)
- Repositorio público **`cerorar23/quantfut-registro`** (README con el método y cómo verificarlo; ningún dato de lotes).
- Llave de despliegue **de lectura y escritura solo para ese repositorio** (`servidor-quantfut`), generada en el servidor:
  `/home/qf/.config/quantfut/registro/id_ed25519` (modo 600, junto a `known_hosts`, cuyas claves de host coinciden con las que GitHub publica en `/meta`).
- Comprobado desde el servidor: `git ls-remote` con esa llave responde. No se hizo ningún push.

## Por qué no está activo ya
El worker no monta la llave ni tiene `CHAIN_GIT_REMOTE`; añadirlos exige **recrear el worker**, y hasta el reentrenamiento del 1-nov no se toca (DEPLOYS.md). La imagen sí trae `git` y `ssh`.

## Activación (después del 1-nov, al alinear el worker con `main`)
1. En `docker-compose.yml`, servicio `worker`:
   ```yaml
   environment:
     - CHAIN_GIT_REMOTE=git@github.com:cerorar23/quantfut-registro.git
     - GIT_SSH_COMMAND=ssh -i /run/secrets/registro/id_ed25519 -o IdentitiesOnly=yes -o UserKnownHostsFile=/run/secrets/registro/known_hosts -o StrictHostKeyChecking=yes
   volumes:
     - /home/qf/.config/quantfut/registro:/run/secrets/registro:ro
   ```
2. Recrear solo el worker (`docker compose up -d --no-deps --force-recreate worker`) y, dentro, preparar la carpeta de la cadena:
   ```sh
   cd /srv/quantfut/chain
   git config --global --add safe.directory /srv/quantfut/chain
   git init -q -b main && git remote add origin "$CHAIN_GIT_REMOTE"
   git fetch -q origin && git reset -q origin/main      # conserva los archivos sin versionar
   git config user.name QuantFut && git config user.email registro@quantfut.invalid
   python -m qf.publish.hashchain verify
   ```
3. **Decisión previa:** en el primer sellado `seal()` subirá los recibos de los 20 lotes ya existentes y revelará el JSON de todos los que ya terminaron (es lo que hace `revelables`). Si no quieres publicar el histórico, hay que apartarlo antes (por ejemplo, listar esos JSON en `.git/info/exclude` y no se versionarán) — pero entonces esos días no serán verificables por terceros.
4. Vigilar el sellado de las 08:00 UTC del día siguiente y el commit en el repositorio público; anotar en `DEPLOYS.md`.

## Vuelta atrás
Quitar `CHAIN_GIT_REMOTE` del compose y recrear el worker; `seal()` vuelve a no tocar git. Para revocar el acceso: borrar la deploy key `servidor-quantfut` en los ajustes del repositorio. Lo ya publicado en un repositorio público no se puede retirar con fiabilidad.
