"""Build an offline, traceable UI snapshot from existing evaluation evidence.

Does not train models, change eligibility rules, or access private endpoints.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MOBILE = ROOT / "apps/mobile"


def read(relative):
    path = ROOT / relative
    body = path.read_bytes()
    return json.loads(body), {"path": relative, "sha256": hashlib.sha256(body).hexdigest()}


alta, alta_source = read(".local/alta_prob_ampliacion_20261009.json")
stats, stats_source = read(".local/escalera_estadistica_20261010_fijos.json")
public, public_source = read("apps/mobile/docs/evidence/public_history_20261011.json")


def line(key, label, *, kind="alta", deployed=True):
    source = alta_source if kind == "alta" else stats_source
    table = (alta["por_mercado"] if kind == "alta" else
             stats["alta_probabilidad"] if kind == "stats_alta" else stats["por_grupo"])
    result = table[key]
    return {"key": key, "label": label, "n": result["n"],
            "observed": result["real"], "expected": result["prometido"],
            "passed": result["pasa"], "deployed": deployed,
            "band": "80–95 %" if kind != "stats" else "60–97 %",
            "source": source["path"]}


def family(identifier, title, subtitle, groups, lines, origin):
    rows = [public["history"]["por_mercado"][g] for g in groups
            if g in public["history"]["por_mercado"]]
    settled, won = sum(r["n"] for r in rows), sum(r["aciertos"] for r in rows)
    return {"id": identifier, "title": title, "subtitle": subtitle,
            "sport": "Fútbol", "experimental": False, "origin": origin,
            "published": {"n": settled, "won": won}, "lines": lines}


families = [
    family("corners_team", "Córners por equipo", "Local y visitante, con su propia línea",
           ["corners_home", "corners_away"], [
               line("corners_home over 1.5", "Local: más de 1,5 córners", kind="stats"),
               line("corners_away over 2.5", "Visitante: más de 2,5 córners", kind="stats_alta"),
               line("corners_home under 7.5", "Local: menos de 7,5 córners", kind="stats_alta"),
               line("corners_away under 6.5", "Visitante: menos de 6,5 córners", kind="stats_alta"),
               line("corners_home over 3.5", "Local: más de 3,5 córners", kind="stats_alta"),
           ], "Modelo estadístico de córners por equipo; la publicación de alta probabilidad limita la estimación con la referencia de mercado."),
    family("handicap", "Hándicap asiático", "Líneas de protección y empate con devolución",
           ["spreads"], [line(f"spreads {key}", f"Hándicap {label}")
                         for key, label in [("+2", "+2"), ("+1", "+1"), ("+1.5", "+1,5"), ("+0", "0"), ("-1", "−1")]],
           "Ajuste de goles a la referencia de Pinnacle sin margen. Las devoluciones quedan fuera del acierto y de la probabilidad condicionada."),
    family("team_goals", "Marca un equipo", "Al menos un gol del local o del visitante",
           ["team_totals_home", "team_totals_away"], [
               line("team_totals_home", "Marca el local · más de 0,5 goles"),
               line("team_totals_away", "Marca el visitante · más de 0,5 goles"),
           ], "Probabilidades de goles por equipo derivadas del ajuste de goles a Pinnacle sin margen. No es una señal de primer tiempo."),
    family("double_chance", "Doble oportunidad", "Dos resultados posibles en una selección",
           ["double_chance"], [line("double_chance", "Doble oportunidad · 1X / X2 / 12")],
           "Suma de probabilidades del 1X2 de Pinnacle sin margen, según la regla de alta probabilidad."),
    family("corners", "Córners totales", "Más y menos córners del partido completo",
           ["corners"], [line("corners over 6.5", "Más de 6,5 córners", kind="stats_alta"),
                           line("corners under 12.5", "Menos de 12,5 córners", kind="stats_alta"),
                           line("corners under 11.5", "Menos de 11,5 córners", kind="stats_alta")],
           "Modelo estadístico de equipos y liga. En alta probabilidad se limita con la probabilidad sin margen de la casa; no mide ritmo en vivo."),
    family("goals", "Goles del partido", "Totales con líneas históricamente evaluadas",
           ["totals"], [line("totals over 1.5", "Más de 1,5 goles"),
                        line("totals under 3.5", "Menos de 3,5 goles"),
                        line("totals over 2.5", "Más de 2,5 goles")],
           "Totales derivados del ajuste de goles a Pinnacle sin margen. La prueba valida probabilidades previas al partido, no alertas en vivo."),
    family("cards", "Tarjetas", "Líneas de menos tarjetas con respaldo histórico",
           [], [line("cards under 6.5", "Menos de 6,5 tarjetas", kind="stats"),
                line("cards under 5.5", "Menos de 5,5 tarjetas", kind="stats", deployed=False),
                line("cards under 4.5", "Menos de 4,5 tarjetas", kind="stats", deployed=False)],
           "Modelo estadístico de tarjetas para la escalera. Las líneas 4,5 y 5,5 pasan la revisión local del 10 de octubre, pero aún no están desplegadas. No hay evidencia de una mejora consistente al añadir árbitro."),
    family("winner", "Ganador del partido", "Resultado 1X2 de alta probabilidad",
           ["h2h"], [line("h2h", "Ganador · selección de alta probabilidad")],
           "Probabilidad de referencia de Pinnacle sin margen. Este acierto no acredita que el modelo propio supere al mercado."),
]

# NBA results are exploratory, with a different target and no settled future
# cohort. They must never enter the supported football ranking.
nba_source = "docs/nba_nueve_mercados_estadistica_20261009.md"
for identifier, title, n, observed, baseline in [
    ("nba_winner", "NBA · Ganador", 1071, 80.4, 69.5),
    ("nba_team", "NBA · Puntos de equipo", 1721, 74.3, 53.3),
    ("nba_total", "NBA · Total del partido", 583, 70.5, 52.1),
]:
    families.append({"id": identifier, "title": title,
        "subtitle": "Evaluación exploratoria · pendiente de confirmación",
        "sport": "NBA", "experimental": True,
        "origin": "Modelo NBA propio. Objetivos estadísticos de evaluación, no líneas de una casa; evaluación 2023–26 con selección ≥70 %. Sigue experimental y no accionable.",
        "published": {"n": 0, "won": 0}, "lines": [{"key": identifier,
            "label": title, "n": n, "observed": observed, "expected": None,
            "baseline": baseline, "passed": False, "deployed": True,
            "band": "Selecciones ≥70 %", "source": nba_source}]})

output = {"schema_version": 1, "captured_at_utc": public["captured_at_utc"],
          "selection_min_cases": 500, "sources": [alta_source, stats_source, public_source],
          "overall": public["history"], "families": families}
destination = MOBILE / "assets/model/market_evidence.json"
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Generated {len(families)} market families, with source hashes.")
