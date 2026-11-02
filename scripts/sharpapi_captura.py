#!/usr/bin/env python3
"""Captura programada de cuotas de fútbol de SharpAPI (plan Free: solo DraftKings y FanDuel, 12 peticiones por minuto, retraso de 60 s,
sin histórico). Autorizada por el titular el 2-nov-2026 para los mercados que PropLine no trae: descanso/final, marcador exacto,
primer equipo en marcar, goleadores, tiros y tiros a puerta de jugador, córners por mitad, tarjetas, faltas y pases de jugador.

Cada pasada (cron cada 10 minutos):
  1. lista los partidos próximos de las 9 ligas del núcleo (`/events`, 2 peticiones);
  2. para cada partido que empieza en las próximas 26 h con DraftKings o FanDuel, mira qué momentos de captura le tocan:
     24 h, 6 h, 2 h, 60 min y 15 min antes del saque (el primero que ya pasó se captura una sola vez; los anteriores a que lo
     viéramos por primera vez se dan por hechos);
  3. pide TODAS las cuotas prepartido del partido (`/odds?event_id=…&is_live=false`, ≈ 8 páginas de 200 filas) y guarda un archivo
     `data/AAAA-MM-DD/<evento>/<capturado>.jsonl.gz` (primera línea = cabecera con la hora real de captura y los minutos al saque;
     el resto, una fila compacta por cuota). Los originales quedan como archivos; cargarlos en la base es una decisión aparte.

Estado en `estado.json` (momentos hechos por partido), registro por la salida estándar. No pide nada en vivo y nunca imprime la clave.
Términos de SharpAPI (cláusulas 5.1-5.4): uso interno y en la propia app con suscripción activa; «Data provided by SharpAPI» desde
el 1-dic-2026 si se muestran cuotas; no se redistribuyen datos en bruto.

  python sharpapi_captura.py --env sharpapi/.env --out sharpapi_data [--seco] [--evento ID]
"""
import argparse
import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = 'https://api.sharpapi.io/api/v1'
LIGAS = ['england_-_premier_league', 'spain_-_la_liga', 'italy_-_serie_a', 'germany_-_bundesliga', 'france_-_ligue_1',
         'netherlands_-_eredivisie', 'portugal_-_primeira_liga', 'brazil_-_serie_a', 'mexico_-_liga_mx']
CASAS = ('draftkings', 'fanduel')
MOMENTOS_MIN = (1440, 360, 120, 60, 15)     # minutos antes del saque
HORIZONTE_H = 26                            # no se mira más allá de este tiempo
PAUSA_S = 5.5                               # 12 peticiones por minuto
MAX_PETICIONES = 150                        # por pasada
MAX_PAGINAS = 30                            # por captura de un partido
CAMPOS = ('sportsbook', 'market_type', 'market_segment', 'selection', 'selection_type', 'team_side', 'line', 'odds_decimal',
          'timestamp', 'is_main_line', 'is_alternate_line', 'player_name', 'stat_category', 'is_stale_pregame_price')


def log(msg):
    print(datetime.now(timezone.utc).strftime('%m-%d %H:%M:%S'), msg, flush=True)


def leer_clave(env_path):
    for linea in Path(env_path).read_text(encoding='utf-8').splitlines():
        if linea.startswith('SHARPAPI_KEY='):
            return linea.split('=', 1)[1].strip()
    raise SystemExit('falta SHARPAPI_KEY en el archivo de entorno')


class Api:
    def __init__(self, clave, pausa=PAUSA_S, tope=MAX_PETICIONES):
        self.clave, self.pausa, self.tope, self.n, self._ultima = clave, pausa, tope, 0, 0.0

    def get(self, ruta, **q):
        if self.n >= self.tope:
            raise TopePeticiones()
        url = BASE + ruta + ('?' + urllib.parse.urlencode(q) if q else '')
        for intento in range(4):
            espera = self._ultima + self.pausa - time.monotonic()
            if espera > 0:
                time.sleep(espera)
            self._ultima = time.monotonic()
            self.n += 1
            req = urllib.request.Request(url, headers={'X-API-Key': self.clave, 'User-Agent': 'quantfut-captura/1'})
            try:
                with urllib.request.urlopen(req, timeout=90) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    time.sleep(min(int(e.headers.get('Retry-After', 30)), 120))
                elif e.code in (401, 403):
                    raise SystemExit(f'clave rechazada (HTTP {e.code})')
                elif e.code == 404:
                    return None
                else:
                    time.sleep(5 * (intento + 1))
            except (urllib.error.URLError, TimeoutError, ValueError, ConnectionError):
                time.sleep(5 * (intento + 1))
        return None


class TopePeticiones(Exception):
    pass


def elegir_eventos(eventos, ahora, horizonte_h=HORIZONTE_H):
    """Partidos reales (con equipos y casa admitida) que empiezan entre ahora y el horizonte. Devuelve (evento, inicio)."""
    salida = []
    for e in eventos or []:
        if not (e.get('home_team') and e.get('away_team') and e.get('start_time')):
            continue
        if not set(CASAS) & set(e.get('books') or []):
            continue
        try:
            inicio = datetime.fromisoformat(e['start_time'].replace('Z', '+00:00'))
        except ValueError:
            continue
        if ahora <= inicio <= ahora + timedelta(hours=horizonte_h):
            salida.append((e, inicio))
    return sorted(salida, key=lambda x: x[1])


def momentos_pendientes(inicio, ahora, hechos):
    """Momentos (minutos antes del saque) ya alcanzados y aún no hechos. Si hay varios, se captura una vez y todos quedan hechos."""
    mins = (inicio - ahora).total_seconds() / 60
    return [m for m in MOMENTOS_MIN if mins <= m and m not in hechos]


def marcar_hechos(hechos, pendientes):
    """Tras capturar, quedan hechos los momentos pendientes y los anteriores al primero que vimos (no se pueden recuperar)."""
    return sorted(set(hechos) | {m for m in MOMENTOS_MIN if m >= min(pendientes)}, reverse=True)


def compactar(fila):
    return {k: fila[k] for k in CAMPOS if fila.get(k) is not None}


def escribir_captura(carpeta, evento, inicio, ahora, momentos, filas, paginas):
    dia = inicio.strftime('%Y-%m-%d')
    destino = Path(carpeta) / dia / ''.join(c if c.isalnum() or c in '._-' else '_' for c in evento['id'])
    destino.mkdir(parents=True, exist_ok=True)
    cabecera = {'evento': evento['id'], 'liga': evento.get('league'), 'local': evento.get('home_team'), 'visita': evento.get('away_team'),
                'inicio': inicio.isoformat(), 'capturado': ahora.isoformat(), 'mins_al_saque': round((inicio - ahora).total_seconds() / 60, 1),
                'momentos': momentos, 'paginas': paginas, 'filas': len(filas), 'casas': list(CASAS), 'retraso_fuente_s': 60}
    final = destino / (ahora.strftime('%Y%m%dT%H%M%SZ') + '.jsonl.gz')
    tmp = final.with_suffix('.tmp')
    with gzip.open(tmp, 'wt', encoding='utf-8') as f:
        f.write(json.dumps(cabecera, ensure_ascii=False) + '\n')
        for fila in filas:
            f.write(json.dumps(fila, ensure_ascii=False, separators=(',', ':')) + '\n')
    os.replace(tmp, final)
    return final


def listar_eventos(api):
    eventos, offset = [], 0
    while True:
        j = api.get('/events', sport='soccer', league=','.join(LIGAS), status='upcoming', limit=200, offset=offset)
        if not j:
            break
        eventos += j.get('data') or []
        pag = j.get('pagination') or {}
        if not pag.get('has_more') or pag.get('next_offset') is None or offset > 2000:
            break
        offset = pag['next_offset']
    return eventos


def capturar_evento(api, evento):
    """Todas las cuotas prepartido de DraftKings y FanDuel del partido; None si alguna página falla (se reintenta en la pasada siguiente)."""
    filas, cursor, paginas = [], None, 0
    while paginas < MAX_PAGINAS:
        q = dict(event_id=evento['id'], sportsbook=','.join(CASAS), is_live='false', limit=200)
        if cursor:
            q['cursor'] = cursor
        j = api.get('/odds', **q)
        if j is None:
            return None
        paginas += 1
        filas += [compactar(f) for f in j.get('data') or []]
        pag = j.get('pagination') or {}
        cursor = pag.get('next_cursor')
        if not pag.get('has_more') or not cursor:
            return filas, paginas
    return filas, paginas


def cargar_estado(ruta):
    try:
        return json.loads(Path(ruta).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {'eventos': {}}


def guardar_estado(ruta, estado, ahora):
    corte = (ahora - timedelta(days=3)).isoformat()
    estado['eventos'] = {k: v for k, v in estado['eventos'].items() if v.get('inicio', '') >= corte}
    tmp = Path(str(ruta) + '.tmp')
    tmp.write_text(json.dumps(estado, ensure_ascii=False), encoding='utf-8')
    os.replace(tmp, ruta)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--env', required=True)
    ap.add_argument('--out', default='sharpapi_data')
    ap.add_argument('--seco', action='store_true', help='solo lista los partidos y los momentos pendientes (2 peticiones)')
    ap.add_argument('--evento', help='capturar solo este id de evento')
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    ruta_estado = out / 'estado.json'
    estado = cargar_estado(ruta_estado)
    api = Api(leer_clave(a.env))
    ahora = datetime.now(timezone.utc)
    try:
        elegidos = elegir_eventos(listar_eventos(api), ahora)
    except TopePeticiones:
        log('tope de peticiones antes de listar'); return 1
    if a.evento:
        elegidos = [(e, i) for e, i in elegidos if e['id'] == a.evento]
    log(f'{len(elegidos)} partidos en las próximas {HORIZONTE_H} h con DraftKings o FanDuel; peticiones {api.n}')
    hechas = 0
    try:
        for e, inicio in elegidos:
            hechos = estado['eventos'].get(e['id'], {}).get('hechos', [])
            pendientes = momentos_pendientes(inicio, ahora, hechos)
            if not pendientes:
                continue
            if a.seco:
                log(f"  [seco] {e['id']} inicio {inicio:%m-%d %H:%MZ} pendientes {pendientes}"); continue
            r = capturar_evento(api, e)
            if r is None:
                log(f"  ERROR {e['id']}: página sin respuesta; se reintenta en la pasada siguiente"); continue
            filas, paginas = r
            if not filas:
                log(f"  {e['id']}: sin cuotas todavía; se reintenta"); continue
            ahora_c = datetime.now(timezone.utc)
            archivo = escribir_captura(out, e, inicio, ahora_c, pendientes, filas, paginas)
            ev = estado['eventos'].setdefault(e['id'], {'inicio': inicio.isoformat(), 'hechos': []})
            ev['hechos'] = marcar_hechos(ev['hechos'], pendientes)
            ev['ultima'] = ahora_c.isoformat()
            guardar_estado(ruta_estado, estado, ahora_c)
            hechas += 1
            log(f"  {e['id']} momentos {pendientes}: {len(filas)} filas en {paginas} páginas -> {archivo.name}")
    except TopePeticiones:
        log('tope de peticiones de la pasada; el resto queda para la siguiente')
    guardar_estado(ruta_estado, estado, datetime.now(timezone.utc))
    log(f'fin: {hechas} capturas, {api.n} peticiones')
    return 0


if __name__ == '__main__':
    sys.exit(main())
