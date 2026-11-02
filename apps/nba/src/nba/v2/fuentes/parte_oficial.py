"""Parte oficial de lesiones de la NBA (PDF de siete columnas en ak-static.cms.nba.com).

Parser estricto: ante cualquier cambio de diseño lanza ValueError y la captura queda como fallida (nunca datos a medias).
`obtener(url)` devuelve (estado, cuerpo); el CDN responde 403 cuando el PDF de esa hora aún no existe.
"""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
import io
from pathlib import Path
import re
from zoneinfo import ZoneInfo

from .. import carga, equipos, identidad
from ..carga import DatoNuevo

FUENTE = "nba_oficial"
ET = ZoneInfo("America/New_York")
BASE = "https://ak-static.cms.nba.com/referee/injury/"
ESTADOS = {"Out", "Doubtful", "Questionable", "Probable", "Available"}
ENCABEZADO = ["Game", "Date", "Game", "Time", "Matchup", "Team", "Player", "Name", "Current", "Status", "Reason"]


@dataclass(frozen=True)
class FilaParte:
    fecha_juego: date
    local: str
    visitante: str
    equipo_txt: str
    jugador: str | None
    estado: str | None
    motivo: str
    enviado: bool


@dataclass(frozen=True)
class ReportePDF:
    encabezado: str
    emitido_utc: datetime
    filas: list[FilaParte]


def reloj_del_encabezado(encabezado: str) -> datetime:
    m = re.fullmatch(r"Injury\s+Report:\s+(\d{2}/\d{2}/\d{2})\s+(\d{2}:\d{2})\s+(AM|PM)", encabezado)
    if not m:
        raise ValueError("encabezado del parte no reconocido")
    ingenuo = datetime.strptime(" ".join(m.groups()), "%m/%d/%y %I:%M %p")
    a, b = ingenuo.replace(tzinfo=ET, fold=0), ingenuo.replace(tzinfo=ET, fold=1)
    if a.utcoffset() != b.utcoffset():
        raise ValueError("hora del parte ambigua o inexistente")
    return a.astimezone(UTC)


def nombre_directo(texto: str) -> str:
    """«Williams III, Jaylin» → «Jaylin Williams III»."""
    apellido, _, nombre = texto.partition(",")
    return f"{nombre.strip()} {apellido.strip()}".strip()


def _filas(paginas) -> list[FilaParte]:
    contexto, filas, vistos = {}, [], set()
    for celdas_pagina in paginas:
        for v in celdas_pagina:
            if len(v) != 7:
                raise ValueError("se esperaban siete columnas")
            solo_motivo = not any(v[:6]) and bool(v[6]) and v[6] != "NOT YET SUBMITTED"
            if filas and solo_motivo and filas[-1]["enviado"]:
                filas[-1]["motivo"] += " " + v[6]  # el motivo continúa en su propia fila
                continue
            fecha, hora, cruce, equipo, nombre, estado, motivo = v
            if cruce and cruce != contexto.get("cruce"):
                contexto.pop("equipo", None)
            for clave, valor in zip(("fecha", "hora", "cruce", "equipo"), (fecha, hora, cruce, equipo)):
                if valor:
                    contexto[clave] = valor
            if not all(contexto.get(k) for k in ("fecha", "hora", "cruce", "equipo")):
                raise ValueError("falta el contexto de partido o equipo")
            datetime.strptime(contexto["fecha"], "%m/%d/%Y")
            if not re.fullmatch(r"[A-Z]{2,3}@[A-Z]{2,3}", contexto["cruce"]):
                raise ValueError("cruce de equipos inválido")
            enviado = motivo != "NOT YET SUBMITTED"
            if enviado and (estado not in ESTADOS or "," not in nombre or not motivo):
                raise ValueError("estado desconocido o fila de jugador mal formada")
            if not enviado and (nombre or estado):
                raise ValueError("equipo sin enviar con jugador")
            clave = (contexto["fecha"], contexto["cruce"], contexto["equipo"], nombre)
            if clave in vistos:
                raise ValueError("entidad duplicada en el parte")
            vistos.add(clave)
            filas.append(dict(fecha=contexto["fecha"], cruce=contexto["cruce"], equipo=contexto["equipo"],
                              jugador=nombre or None, estado=estado or None, motivo=motivo, enviado=enviado))
    resultado = []
    for f in filas:
        visitante, local = (equipos.canonico(FUENTE, c) for c in f["cruce"].split("@"))
        resultado.append(FilaParte(fecha_juego=datetime.strptime(f["fecha"], "%m/%d/%Y").date(), local=local,
                                   visitante=visitante, equipo_txt=f["equipo"],
                                   jugador=nombre_directo(f["jugador"]) if f["jugador"] else None, estado=f["estado"],
                                   motivo=f["motivo"], enviado=f["enviado"]))
    return resultado


def extraer(pdf: bytes, recibido_en: datetime) -> ReportePDF:
    try:
        return _extraer(pdf, recibido_en)
    except ValueError:
        raise
    except Exception as e:  # PDF roto o truncado: pdfplumber/pdfminer lanzan excepciones propias
        raise ValueError(f"PDF ilegible: {type(e).__name__}") from e


def _extraer(pdf: bytes, recibido_en: datetime) -> ReportePDF:
    import pdfplumber

    if not pdf.startswith(b"%PDF-"):
        raise ValueError("no es un PDF")
    paginas, encabezados, limites = [], [], None
    with pdfplumber.open(io.BytesIO(pdf)) as documento:
        if not 1 <= len(documento.pages) <= 30:
            raise ValueError("número de páginas fuera de lo esperado")
        for pagina in documento.pages:
            palabras = pagina.extract_words(x_tolerance=1)
            encabezados.append(" ".join(w["text"] for w in palabras if w["top"] < 80))
            if limites is None:
                titulos = [w for w in palabras if 90 < w["top"] < 125]
                if [w["text"] for w in titulos] != ENCABEZADO:
                    raise ValueError("diseño del PDF no reconocido")
                limites = [titulos[i]["x0"] - 4 for i in (0, 2, 4, 5, 6, 8, 10)] + [pagina.width - 19]
                minimo = max(w["bottom"] for w in titulos)
            else:
                minimo = 75.4
            reglas = sorted({round(e["top"], 2) for e in pagina.edges if e["orientation"] == "h"
                             and limites[4] - 2 <= e["x0"] < limites[5] and e["x1"] - e["x0"] > 150 and e["top"] > minimo})
            if not reglas:
                raise ValueError("faltan separadores de fila")
            if pagina.page_number > 1:
                reglas.insert(0, minimo)
            celdas = []
            for arriba, abajo in zip(reglas, reglas[1:]):
                fila = []
                for izq, der in zip(limites, limites[1:]):
                    elegidas = sorted((w for w in palabras if izq <= w["x0"] < der and arriba <= (w["top"] + w["bottom"]) / 2 < abajo),
                                      key=lambda w: (round(w["top"], 1), w["x0"]))
                    fila.append(" ".join(w["text"] for w in elegidas))
                if any(fila):
                    celdas.append(fila)
            paginas.append(celdas)
    if len(set(encabezados)) != 1:
        raise ValueError("las páginas no coinciden en la hora del parte")
    emitido = reloj_del_encabezado(encabezados[0])
    if emitido > recibido_en:
        raise ValueError("el parte dice haberse emitido después de recibirlo")
    return ReportePDF(encabezados[0], emitido, _filas(paginas))


def cargar(db, reporte: ReportePDF, recibido_en: datetime, captura_id: int) -> int:
    filas = []
    for f in reporte.filas:
        local, visitante = identidad.equipo(db, f.local), identidad.equipo(db, f.visitante)
        partido = identidad.partido(db, FUENTE, f"{f.fecha_juego.isoformat()}:{f.visitante}@{f.local}", f.fecha_juego,
                                    local, visitante, identidad.temporada(f.fecha_juego))
        base = dict(partido_id=partido, fase="pre", fuente=FUENTE, recibido_en=recibido_en, captura_id=captura_id)
        if not f.enviado:
            texto = f.equipo_txt.replace(" ", "")
            if texto == equipos.TRICODES[f.local].replace(" ", ""):
                equipo = local
            elif texto == equipos.TRICODES[f.visitante].replace(" ", ""):
                equipo = visitante
            else:
                raise ValueError(f"el equipo «{f.equipo_txt}» no es ni {f.local} ni {f.visitante}")
            filas.append(DatoNuevo(entidad_id=equipo, metrica="reporte_no_enviado", valor=1.0, **base))
            continue
        jugador = identidad.jugador(db, FUENTE, "nombre:" + identidad.normalizar_nombre(f.jugador), f.jugador)
        filas.append(DatoNuevo(entidad_id=jugador, metrica="estado_disponibilidad", etiqueta=f.estado, **base))
        filas.append(DatoNuevo(entidad_id=jugador, metrica="motivo_disponibilidad", etiqueta=f.motivo[:300], **base))
    return carga.guardar_datos(db, filas, solo_cambios=True)


def _nombre_pdf(dia: date, hora: int, media: bool) -> str:
    h12 = hora % 12 or 12
    return f"Injury-Report_{dia.isoformat()}_{h12:02d}{'_30' if media else ''}{'AM' if hora < 12 else 'PM'}.pdf"


def urls_candidatas(ahora: datetime, ventana_min: int = 120) -> list[str]:
    """Horas (en punto y y media) del día ET que ya pasaron en los últimos `ventana_min` minutos."""
    ahora_et = ahora.astimezone(ET)
    urls = []
    for hora in range(9, 24):
        for media in (False, True):
            instante = datetime(ahora_et.year, ahora_et.month, ahora_et.day, hora, 30 if media else 0, tzinfo=ET)
            if timedelta(0) <= ahora_et - instante <= timedelta(minutes=ventana_min):
                urls.append(BASE + _nombre_pdf(ahora_et.date(), hora, media))
    return urls


def capturar(db, obtener: Callable[[str], tuple[int, bytes]], raiz: Path, ahora: datetime, ventana_min: int = 120,
             espera_min: float = 14) -> dict:
    nuevos, datos, fallidos = 0, 0, 0
    for url in urls_candidatas(ahora, ventana_min):
        if db.execute("SELECT EXISTS (SELECT 1 FROM nba.captura WHERE fuente = %s AND objetivo = %s AND ok)",
                      (FUENTE, url)).fetchone()[0]:
            continue
        if db.execute("SELECT EXISTS (SELECT 1 FROM nba.captura WHERE fuente = %s AND objetivo = %s AND NOT ok "
                      "AND solicitado_en > %s)", (FUENTE, url, ahora - timedelta(minutes=espera_min))).fetchone()[0]:
            continue
        try:
            estado, cuerpo = obtener(url)
        except Exception as e:
            carga.registrar_captura(db, fuente=FUENTE, objetivo=url, fase="pre", solicitado_en=ahora, ok=False,
                                    error=f"{type(e).__name__}: {e}")
            fallidos += 1
            continue
        if estado != 200:  # 403/404 = ese parte todavía no existe: se vuelve a intentar más tarde
            carga.registrar_captura(db, fuente=FUENTE, objetivo=url, fase="pre", solicitado_en=ahora, ok=False,
                                    http_status=estado, recibido_en=ahora)
            continue
        ruta, huella = carga.guardar_original(raiz, FUENTE, cuerpo, ahora)
        try:
            reporte = extraer(cuerpo, ahora)
        except ValueError as e:
            carga.registrar_captura(db, fuente=FUENTE, objetivo=url, fase="pre", solicitado_en=ahora, ok=False,
                                    recibido_en=ahora, http_status=200, sha256=huella, bytes_=len(cuerpo), ruta=ruta,
                                    error=str(e)[:300])
            fallidos += 1
            continue
        captura = carga.registrar_captura(db, fuente=FUENTE, objetivo=url, fase="pre", solicitado_en=ahora, ok=True,
                                          recibido_en=ahora, http_status=200, sha256=huella, bytes_=len(cuerpo), ruta=ruta)
        datos += cargar(db, reporte, ahora, captura)
        nuevos += 1
    return {"ok": fallidos == 0, "partes_nuevos": nuevos, "datos": datos, "fallidos": fallidos}


def obtener_http(url: str) -> tuple[int, bytes]:
    import httpx
    r = httpx.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"},
                  timeout=20, follow_redirects=True)
    return r.status_code, r.content
