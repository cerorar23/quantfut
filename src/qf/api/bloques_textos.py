"""Diccionario único de textos de los bloques de contenido (`partido.bloques` de `/deportes/v1`, Fase 4 tarea 4.1).

Un adaptador NUNCA escribe texto libre en un bloque: usa una clave de este diccionario con el prefijo `@`
(`'@forma'`) en el título, en las etiquetas, en las columnas, en las celdas de texto y en el cuerpo de un bloque
`texto`. Lo que no lleva `@` es un nombre propio (equipo, jugador) o una cifra y sale tal cual, sin traducir.
El router resuelve cada clave al idioma pedido (`?lang=`) y, si el idioma no la tiene, cae a español.
Una clave que no existe es un bloque inválido (503), no un texto en blanco.

Regla del proyecto: todo texto nuevo que pueda verse en la app lleva sus 6 idiomas en el mismo cambio;
`tests/test_bloques_textos.py` exige los 6, no vacíos, en cada clave.

Orden de las traducciones en cada tupla: es, en, pt, fr, it, de.
"""
from __future__ import annotations

IDIOMAS = ('es', 'en', 'pt', 'fr', 'it', 'de')
PREFIJO = '@'

TEXTOS: dict[str, tuple[str, str, str, str, str, str]] = {
    'estadisticas': ('Estadísticas', 'Statistics', 'Estatísticas', 'Statistiques', 'Statistiche', 'Statistiken'),
    'forma': ('Forma reciente', 'Recent form', 'Forma recente', 'Forme récente', 'Forma recente', 'Aktuelle Form'),
    'cara_a_cara': ('Cara a cara', 'Head to head', 'Confronto direto', 'Confrontations directes',
                    'Scontri diretti', 'Direkter Vergleich'),
    'ultimos_partidos': ('Últimos partidos', 'Latest matches', 'Últimas partidas', 'Derniers matchs',
                         'Ultime partite', 'Letzte Spiele'),
    'resumen': ('Resumen', 'Summary', 'Resumo', 'Résumé', 'Riepilogo', 'Zusammenfassung'),
    'probabilidades': ('Probabilidades', 'Probabilities', 'Probabilidades', 'Probabilités',
                       'Probabilità', 'Wahrscheinlichkeiten'),
    'local': ('Local', 'Home', 'Casa', 'Domicile', 'Casa', 'Heim'),
    'visitante': ('Visitante', 'Away', 'Visitante', 'Extérieur', 'Ospite', 'Gast'),
    'equipo': ('Equipo', 'Team', 'Equipe', 'Équipe', 'Squadra', 'Mannschaft'),
    'jugador': ('Jugador', 'Player', 'Jogador', 'Joueur', 'Giocatore', 'Spieler'),
    'rival': ('Rival', 'Opponent', 'Adversário', 'Adversaire', 'Avversario', 'Gegner'),
    'resultado': ('Resultado', 'Result', 'Resultado', 'Résultat', 'Risultato', 'Ergebnis'),
    'fecha': ('Fecha', 'Date', 'Data', 'Date', 'Data', 'Datum'),
    'victorias': ('Victorias', 'Wins', 'Vitórias', 'Victoires', 'Vittorie', 'Siege'),
    'derrotas': ('Derrotas', 'Losses', 'Derrotas', 'Défaites', 'Sconfitte', 'Niederlagen'),
    'empates': ('Empates', 'Draws', 'Empates', 'Matchs nuls', 'Pareggi', 'Unentschieden'),
    'promedio': ('Promedio', 'Average', 'Média', 'Moyenne', 'Media', 'Durchschnitt'),
    'total': ('Total', 'Total', 'Total', 'Total', 'Totale', 'Gesamt'),
    'muestra_pequena': (
        'La muestra es pequeña: tómalo como orientación, no como certeza.',
        'The sample is small: treat it as guidance, not certainty.',
        'A amostra é pequena: use como orientação, não como certeza.',
        "L'échantillon est petit : à prendre comme une indication, pas comme une certitude.",
        'Il campione è piccolo: consideralo un’indicazione, non una certezza.',
        'Die Stichprobe ist klein: als Orientierung verstehen, nicht als Gewissheit.'),
}


def existe(clave: str) -> bool:
    return clave in TEXTOS


def texto(clave: str, lang: str = 'es') -> str:
    """El texto de `clave` en `lang`; si el idioma no existe o está vacío, en español. Clave desconocida -> KeyError."""
    tr = TEXTOS[clave]
    i = IDIOMAS.index(lang) if lang in IDIOMAS else 0
    return tr[i].strip() and tr[i] or tr[0]


def resolver(valor: str, lang: str = 'es') -> str:
    """`'@clave'` -> su texto en `lang` (KeyError si no existe); cualquier otro texto se devuelve intacto."""
    if valor.startswith(PREFIJO):
        return texto(valor[len(PREFIJO):], lang)
    return valor
