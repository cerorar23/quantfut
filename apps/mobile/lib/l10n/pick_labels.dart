import 'package:intl/intl.dart';

import '../product/live_api.dart';
import 'app_locale.dart';

/// Textos descriptivos de pronósticos y mercados, generados en el idioma actual.
///
/// El servidor entrega estos textos en español, pero siempre junto a los campos
/// estructurados de los que salen (`market`, `selection`, `line`, equipos). Aquí se
/// reconstruyen desde esos campos con las plantillas de `lib/l10n`; la misma lógica
/// vive en `alta_prob.texto` y `partido_mercados` del backend. Si falta un campo o el
/// mercado es desconocido se devuelve el texto original del servidor.
///
/// Si añades un mercado nuevo en el backend, añádelo aquí y a los ARB.

/// Línea numérica sin ceros sobrantes y con el separador del idioma (2,5 / 2.5 / 1).
String lineText(num? line) => line == null
    ? ''
    : (NumberFormat(
        '0.##',
        AppLocale.instance.code,
      )..turnOffGrouping()).format(line);

/// Línea con signo explícito para hándicaps (+1,5 / -1).
String signedLine(num line) => '${line > 0 ? '+' : ''}${lineText(line)}';

String _team(Object? name, Object? fallback) =>
    '${name ?? fallback ?? ''}'.trim();

/// Nombre del mercado (la familia), a partir de su identificador.
String marketName(dynamic key) {
  final l10n = AppLocale.instance.l10n;
  return switch ('$key') {
    'totals' => l10n.marketGoals,
    'h2h' => l10n.marketResult1x2,
    'double_chance' => l10n.marketDoubleChance,
    'corners' => l10n.marketCorners,
    'corners_home' => l10n.marketCornersHome,
    'corners_away' => l10n.marketCornersAway,
    'spreads' => l10n.marketHandicap,
    'team_totals_home' => l10n.marketGoalsHome,
    'team_totals_away' => l10n.marketGoalsAway,
    'home_to_score' => l10n.marketHomeScores,
    'away_to_score' => l10n.marketAwayScores,
    'btts' => l10n.marketBtts,
    'win_to_nil' => l10n.marketWinToNil,
    'ht_btts' => l10n.marketHtBtts,
    'ht_goal' => l10n.marketHtGoal,
    'cards' => l10n.marketCards,
    'null' => l10n.marketUnknown,
    final other => other,
  };
}

num? _line(Object? v) => v is num ? v : num.tryParse('$v');

/// El pronóstico en palabras (equivale a `alta_prob.texto`). Los nombres de los
/// equipos salen de `home`/`away` si se dan, o de `local`/`visitante` del propio pick.
String pickText(JsonMap pick, {Object? home, Object? away}) {
  final l10n = AppLocale.instance.l10n;
  final market = pick['market'], selection = pick['selection'];
  final homeName = _team(home, pick['local']),
      awayName = _team(away, pick['visitante']);
  final line = _line(pick['line']);
  final fallback = '${pick['texto'] ?? '—'}';
  if (market == null || selection == null) return fallback;
  switch ('$market') {
    case 'h2h':
      return switch ('$selection') {
        'home' => l10n.selHomeWins(homeName),
        'away' => l10n.selHomeWins(awayName),
        'draw' => l10n.commonDraw,
        _ => fallback,
      };
    case 'double_chance':
      return switch ('$selection') {
        '1X' => l10n.selTeamOrDraw(homeName),
        'X2' => l10n.selTeamOrDraw(awayName),
        '12' => l10n.selEitherNoDraw(homeName, awayName),
        _ => fallback,
      };
    case 'totals':
      return line == null
          ? fallback
          : l10n.selGoals('$selection', lineText(line));
    case 'team_totals_home':
      return l10n.selTeamScores(homeName);
    case 'team_totals_away':
      return l10n.selTeamScores(awayName);
    case 'btts':
      return selection == 'yes' ? l10n.selBttsYes : l10n.selBttsNo;
    case 'spreads':
      if (line == null) return fallback;
      final team = selection == 'home' ? homeName : awayName;
      return line == 0
          ? l10n.selDrawNoBet(team)
          : l10n.selHandicapLong(team, signedLine(line));
    case 'corners':
      return line == null
          ? fallback
          : l10n.selCorners('$selection', lineText(line));
    case 'corners_home':
      return line == null
          ? fallback
          : l10n.selCornersTeam('$selection', lineText(line), homeName);
    case 'corners_away':
      return line == null
          ? fallback
          : l10n.selCornersTeam('$selection', lineText(line), awayName);
  }
  return fallback;
}

/// Selección de una fila de «Mercados del partido» (equivale a `partido_mercados`).
String rowSelection(JsonMap row, String home, String away) {
  final l10n = AppLocale.instance.l10n;
  final market = '${row['market']}', selection = '${row['selection']}';
  final line = _line(row['line']);
  final fallback = '${row['seleccion'] ?? '—'}';
  switch (market) {
    case 'spreads':
      if (line == null) return fallback;
      final team = selection == 'home' ? home : away;
      return line == 0
          ? l10n.selDrawNoBet(team)
          : l10n.selHandicapShort(team, signedLine(line));
    case 'team_totals_home':
    case 'team_totals_away':
      return line == null ? fallback : l10n.selGoals(selection, lineText(line));
    case 'win_to_nil':
      return l10n.selWinToNil(selection == 'home' ? home : away);
    case 'ht_btts':
      return selection == 'no' ? l10n.selHtBttsNo : fallback;
    case 'ht_goal':
      return selection == 'yes' ? l10n.selHtGoalYes : fallback;
    case 'cards':
      return line == null ? fallback : l10n.selCards(selection, lineText(line));
    case 'h2h':
    case 'double_chance':
    case 'totals':
    case 'btts':
    case 'corners':
      return pickText({
        ...row,
        'local': home,
        'visitante': away,
        'texto': fallback,
      });
  }
  return fallback;
}

/// Título de una fila de «Mercados del partido».
String rowTitle(JsonMap row, String home, String away) {
  final l10n = AppLocale.instance.l10n;
  final line = _line(row['line']);
  final fallback = '${row['titulo'] ?? ''}';
  return switch ('${row['market']}') {
    'h2h' => l10n.titleWinner,
    'double_chance' => l10n.marketDoubleChance,
    'spreads' => line == 0 ? l10n.titleDrawNoBet : l10n.titleAsianHandicap,
    'totals' => l10n.titleTotalGoals,
    'team_totals_home' => l10n.titleTeamGoals(home),
    'team_totals_away' => l10n.titleTeamGoals(away),
    'btts' => l10n.marketBtts,
    'win_to_nil' => l10n.marketWinToNil,
    'ht_btts' => l10n.marketHtBtts,
    'ht_goal' => l10n.marketHtGoal,
    'corners' => l10n.titleTotalCorners,
    'cards' => l10n.titleTotalCards,
    _ => fallback,
  };
}

/// Categoría de una fila. El servidor usa el nombre en español como identificador.
String groupLabel(Object? group) {
  final l10n = AppLocale.instance.l10n;
  return switch ('$group') {
    'RESULTADO' => l10n.groupResult,
    'DOBLE OPORTUNIDAD' => l10n.groupDoubleChance,
    'EMPATE NO ACCIÓN' => l10n.groupDrawNoBet,
    'GOLES' => l10n.groupGoals,
    'GOLES DE EQUIPO' => l10n.groupTeamGoals,
    'AMBOS MARCAN' => l10n.groupBtts,
    'HÁNDICAP' => l10n.groupHandicap,
    'ESPECIALES' => l10n.groupSpecials,
    '1ª MITAD' => l10n.groupFirstHalf,
    'CÓRNERS' => l10n.groupCorners,
    'TARJETAS' => l10n.groupCards,
    final other => other,
  };
}

String _number(String spanish) {
  final value = double.tryParse(spanish.replaceAll(',', '.'));
  if (value == null) return spanish;
  final decimals = spanish.contains(',') ? spanish.split(',').last.length : 0;
  return decimalText(value, decimals);
}

/// Nota de una fila («Goles esperados: 2,45», «xG: …», «Media esperada: 9,5»).
String? noteText(Object? note, String home, String away) {
  if (note == null) return null;
  final text = '$note';
  final l10n = AppLocale.instance.l10n;
  var m = RegExp(r'^Goles esperados: ([\d.,]+)$').firstMatch(text);
  if (m != null) return l10n.noteExpectedGoals(_number(m[1]!));
  m = RegExp(r'^Media esperada: ([\d.,]+)$').firstMatch(text);
  if (m != null) return l10n.noteExpectedAverage(_number(m[1]!));
  m = RegExp(
    '^xG: ${RegExp.escape(home)} ([\\d.,]+) · ${RegExp.escape(away)} ([\\d.,]+)\$',
  ).firstMatch(text);
  if (m != null) {
    return l10n.noteXg(home, _number(m[1]!), away, _number(m[2]!));
  }
  return text;
}

/// Nivel de confianza del servidor (`alta`, `solida`, `moderada`).
String levelLabel(Object? level) {
  final l10n = AppLocale.instance.l10n;
  return switch ('$level') {
    'alta' => l10n.levelHigh,
    'solida' => l10n.levelSolid,
    'moderada' => l10n.levelModerate,
    final other => other.toUpperCase(),
  };
}

/// Letra de resultado de un partido reciente. El servidor envía G/E/P (ganado,
/// empate, perdido); se muestra W/D/L, V/N/D, S/U/N… según el idioma.
String resultLetter(Object? res) {
  final l10n = AppLocale.instance.l10n;
  return switch ('$res') {
    'G' => l10n.statResWin,
    'E' => l10n.statResDraw,
    'P' => l10n.statResLoss,
    final other => other,
  };
}
