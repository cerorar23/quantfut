"""Ajuste por competición de la primera mitad. GENERADO por `qf.eval.ajuste_primer_tiempo`: no editar a mano.

Ajustado con 16182 partidos fuera de muestra de 21 competiciones (2024-07-02 a 2026-11-09); generado 2026-11-10T00:03Z.
logit(p') = pendiente · logit(p) + intercepto[competición]. Una competición que no figura aquí se queda con la proporción fija.
Ver docs/hipotesis_mercados_20261109.md.
"""
META = {"filas": 16182, "ligas": 21, "desde": "2024-07-02", "hasta": "2026-11-09", "min_filas_liga": 150, "generado": "2026-11-10T00:03Z"}
AJUSTE = {
    "intercepto": {
        "ar.primera": {
            "ambos": -0.9413935844814919,
            "gol": 0.11932631869760851
        },
        "br.serie_a": {
            "ambos": -0.698062327835469,
            "gol": 0.42793943004686597
        },
        "ch.super_league": {
            "ambos": -0.5834148602005216,
            "gol": 0.46222069574455754
        },
        "de.bundesliga": {
            "ambos": -0.6507455602805148,
            "gol": 0.5060978613828541
        },
        "de.bundesliga2": {
            "ambos": -0.6418680720604716,
            "gol": 0.2834708796147896
        },
        "es.laliga": {
            "ambos": -0.7740363650620335,
            "gol": 0.2740426285359827
        },
        "es.laliga2": {
            "ambos": -0.7138195005648629,
            "gol": 0.2825606615059434
        },
        "eu.ucl": {
            "ambos": -0.5189067151690615,
            "gol": 0.3082073918365141
        },
        "eu.uel": {
            "ambos": -0.6993914244005862,
            "gol": 0.44114669575015064
        },
        "fr.ligue_1": {
            "ambos": -0.741850973891454,
            "gol": 0.3341303281453316
        },
        "gb.championship": {
            "ambos": -0.7954614830851701,
            "gol": 0.40509043395552746
        },
        "gb.premier_league": {
            "ambos": -0.8368029553318361,
            "gol": 0.33055183374879815
        },
        "it.serie_a": {
            "ambos": -0.8067291013979071,
            "gol": 0.23629801781851634
        },
        "it.serie_b": {
            "ambos": -0.614432515645394,
            "gol": 0.39930017949597074
        },
        "mx.liga_mx": {
            "ambos": -0.5160396088048262,
            "gol": 0.35486837553042716
        },
        "nl.eredivisie": {
            "ambos": -0.4494721124575311,
            "gol": 0.596082535405495
        },
        "no.eliteserien": {
            "ambos": -0.6520281533102211,
            "gol": 0.49067771569256385
        },
        "pt.primeira": {
            "ambos": -0.8168727608558802,
            "gol": 0.27194929983395116
        },
        "se.allsvenskan": {
            "ambos": -0.7244900411434287,
            "gol": 0.21434124425756318
        },
        "tr.super_lig": {
            "ambos": -0.7165558044754756,
            "gol": 0.4276862176745905
        },
        "us.mls": {
            "ambos": -0.5321911326123303,
            "gol": 0.516194808570236
        }
    },
    "pendiente": {
        "ambos": 0.4727121532495786,
        "gol": 0.6540590531308967
    }
}
