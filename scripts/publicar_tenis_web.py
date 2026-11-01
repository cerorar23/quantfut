"""Actualiza solo el JSON público de tenis; no concede acceso a originales a la API.

Ejecutar en el host. El proyector vecino es una copia revisada de
src/qf/api/tenis_publico.py. No hay llamadas a proveedores ni cambios en el motor.
"""
import importlib.util
import json
from pathlib import Path
import subprocess


def main():
    import fcntl
    base = Path.home() / "quantfut-public-sports"
    base.mkdir(exist_ok=True)
    with (base / "publication.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        spec = importlib.util.spec_from_file_location("tennis_public_projection", Path(__file__).with_name("tenis_publico.py"))
        projector = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(projector)
        root = Path.home() / "quantfut-tenis/data/intake_v1"
        feed = projector.projection(root, fixture_root=root / "api_tennis/originals")
        if feed["state"] not in ("ok", "partial"):
            raise RuntimeError("No hay una fuente verificada para actualizar tenis")
        payload = json.dumps(feed, ensure_ascii=False, allow_nan=False).encode()
        # Solo la proyección explícita entra en el volumen existente. No se montan
        # directorios privados ni se copian modelos, parámetros o respuestas originales.
        writer = """import json,sys,os
from pathlib import Path
value=json.load(sys.stdin)
assert value.get('sport')=='tenis' and value.get('state') in ('ok','partial')
folder=Path('/srv/quantfut/artifacts/public-sports');folder.mkdir(parents=True,exist_ok=True)
temp=folder/('tennis-public-'+str(os.getpid())+'.tmp')
temp.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False),encoding='utf-8')
os.replace(temp,folder/'tennis.json')
"""
        subprocess.run(["docker", "exec", "-i", "quantfut-api-1", "python", "-c", writer], input=payload, check=True, timeout=30)
        print(json.dumps(dict(at=feed["generated_at"], events=len(feed["events"]), problems=feed["problems"], public_only=True)))


if __name__ == "__main__":
    main()
