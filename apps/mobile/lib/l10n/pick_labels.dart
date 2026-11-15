import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../product/alerts_model.dart';
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
/// Patas del parley v2 de tenis y NBA: totales, hándicap y props de jugador en el idioma actual.
String? _otherSport(AppLocalizations l10n, String sport, String market, String selection, num? line, String home,
    String away, Object? player) {
  if (line == null) return null;
  final over = selection == 'over';
  final text = lineText(line);
  switch (market) {
    case 'total_games':
      return over ? l10n.selGamesOver(text) : l10n.selGamesUnder(text);
    case 'handicap_games':
      return l10n.selGamesHandicap(selection == 'home' ? home : away, signedLine(line));
    case 'totals':
      return sport == 'nba' ? (over ? l10n.selPointsOver(text) : l10n.selPointsUnder(text)) : null;
    case 'spreads':
      return sport == 'nba' ? l10n.selSpreadPoints(selection == 'home' ? home : away, signedLine(line)) : null;
    case 'player_points' || 'player_rebounds' || 'player_assists' || 'player_threes':
      final stat = switch (market) {
        'player_points' => l10n.propStatPoints,
        'player_rebounds' => l10n.propStatRebounds,
        'player_assists' => l10n.propStatAssists,
        _ => l10n.propStatThrees,
      };
      final name = '${player ?? '—'}';
      return over ? l10n.selPlayerOver(name, text, stat) : l10n.selPlayerUnder(name, text, stat);
  }
  return null;
}

String pickText(JsonMap pick, {Object? home, Object? away}) {
  final l10n = AppLocale.instance.l10n;
  final market = pick['market'], selection = pick['selection'];
  final homeName = _team(home, pick['local']),
      awayName = _team(away, pick['visitante']);
  final line = _line(pick['line']);
  final fallback = '${pick['texto'] ?? '—'}';
  if (market == null || selection == null) return fallback;
  if (pick['deporte'] == 'tenis' || pick['deporte'] == 'nba') {
    final other = _otherSport(l10n, '${pick['deporte']}', '$market', '$selection', line, homeName, awayName,
        pick['jugador']);
    if (other != null) return other;
  }
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
    case 'team_totals_away':
      final team = market == 'team_totals_home' ? homeName : awayName;
      // «Marca X» solo equivale a «más de 0,5»; otra línea o el «menos» se dicen enteros.
      if (selection == 'over' && (line == null || line == 0.5)) {
        return l10n.selTeamScores(team);
      }
      return line == null
          ? fallback
          : l10n.selTeamGoalsLine('$selection', lineText(line), team);
    case 'cards':
      return line == null
          ? fallback
          : l10n.selCards('$selection', lineText(line));
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
    case 'corners_home':
    case 'corners_away':
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
    'corners_home' => l10n.marketCornersHome,
    'corners_away' => l10n.marketCornersAway,
    'cards' => l10n.titleTotalCards,
    _ => fallback,
  };
}

/// Nombre comercial de la casa de la cuota. El servidor manda la clave del proveedor
/// («betonlineag», «williamhill_us»); una clave desconocida se enseña tal cual.
String bookName(Object? book) {
  final key = '$book'.trim().toLowerCase();
  // l10n-ignore-start
  return switch (key) {
    'betonlineag' || 'betonline' => 'BetOnline',
    'bovada' => 'Bovada',
    'bet365' => 'bet365',
    'pinnacle' => 'Pinnacle',
    'betano' => 'Betano',
    'betfair' || 'betfair_ex_eu' || 'betfair_ex_uk' => 'Betfair',
    'williamhill' || 'williamhill_us' => 'William Hill',
    'draftkings' => 'DraftKings',
    'fanduel' => 'FanDuel',
    'betmgm' => 'BetMGM',
    'caesars' || 'williamhill_us_caesars' => 'Caesars',
    'unibet' || 'unibet_eu' => 'Unibet',
    'marathonbet' => 'Marathonbet',
    'onexbet' || '1xbet' => '1xBet',
    'sport888' || '888sport' => '888sport',
    'betway' => 'Betway',
    'mybookieag' => 'MyBookie',
    'lowvig' => 'LowVig',
    'betrivers' => 'BetRivers',
    _ => '$book',
  };
  // l10n-ignore-end
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

/// Traducción de ronda de torneo de tenis. Si la ronda no es reconocida se
/// devuelve el texto crudo original sin fallar.
String tennisRoundLabel(String rawRound) {
  final l10n = AppLocale.instance.l10n;
  final normalized = rawRound.trim().toLowerCase();
  return switch (normalized) {
    'final' => l10n.tenRoundFinal,
    'semifinals' || 'semi-finals' || 'semi finals' => l10n.tenRoundSemifinals,
    'quarterfinals' || 'quarter-finals' || 'quarter finals' => l10n.tenRoundQuarterfinals,
    'round of 16' || '1/8-finals' || '1/8' || 'r16' => l10n.tenRoundR16,
    'round of 32' || '1/16-finals' || '1/16' || 'r32' => l10n.tenRoundR32,
    'round of 64' || '1/32-finals' || '1/32' || 'r64' => l10n.tenRoundR64,
    'round of 128' || '1/64-finals' || '1/64' || 'r128' => l10n.tenRoundR128,
    'qualification final' || 'qualifying final' => l10n.tenRoundQualFinal,
    _ => rawRound,
  };
}

/// Interpreta fechas de regreso en inglés como «Early December 2026», «Mid November 2026»,
/// «Late May 2027», o formato ISO «2026-12-05».
/// Si el texto no es reconocido se devuelve tal cual sin fallar.
String interpretReturnDate(
  String raw, {
  AppLocalizations? l10n,
  String? localeCode,
  int currentYear = 2026,
}) {
  final trimmed = raw.trim();
  if (trimmed.isEmpty) return trimmed;
  final loc = l10n ?? AppLocale.instance.l10n;
  final code = localeCode ?? AppLocale.instance.code;

  // Intentar parsear ISO date
  final iso = DateTime.tryParse(trimmed);
  if (iso != null) {
    return DateFormat.MMMd(code).format(iso);
  }

  // Regex para Early / Mid / Late <Month> [<Year>]
  final match = RegExp(
    r'^(Early|Mid|Late)\s+([A-Za-z]+)(?:\s+(\d{4}))?$',
    caseSensitive: false,
  ).firstMatch(trimmed);

  if (match == null) {
    return trimmed;
  }

  final period = match.group(1)!.toLowerCase();
  final monthName = match.group(2)!.toLowerCase();
  final yearStr = match.group(3);

  final monthNum = switch (monthName) {
    'january' || 'jan' => 1,
    'february' || 'feb' => 2,
    'march' || 'mar' => 3,
    'april' || 'apr' => 4,
    'may' => 5,
    'june' || 'jun' => 6,
    'july' || 'jul' => 7,
    'august' || 'aug' => 8,
    'september' || 'sep' || 'sept' => 9,
    'october' || 'oct' => 10,
    'november' || 'nov' => 11,
    'december' || 'dec' => 12,
    _ => null,
  };

  if (monthNum == null) return trimmed;

  // Mes abreviado localizado
  var mStr = DateFormat('MMM', code).format(DateTime(2026, monthNum, 1));
  if (code == 'es' && !mStr.endsWith('.') && mStr != 'may') {
    mStr = '$mStr.';
  } else if (code == 'es' && mStr == 'may') {
    mStr = 'may.';
  }

  final periodStr = switch (period) {
    'early' => loc.alertsEarlyMonth(mStr),
    'mid' => loc.alertsMidMonth(mStr),
    'late' => loc.alertsLateMonth(mStr),
    _ => mStr,
  };

  if (yearStr != null) {
    final y = int.tryParse(yearStr);
    if (y != null && y != currentYear) {
      return '$periodStr $yearStr';
    }
  }

  return periodStr;
}

/// Devuelve el texto descriptivo de la tercera línea de la tarjeta de baja
/// (p. ej. «Con su selección · vuelve a mediados de nov.», «Vuelve a principios de dic.»,
/// «Ya entrena con el grupo», o el motivo traducido si no hay fecha de regreso).
String? absenceReturnText(
  Absence absence, {
  AppLocalizations? l10n,
  String? localeCode,
}) {
  final loc = l10n ?? AppLocale.instance.l10n;
  final code = localeCode ?? AppLocale.instance.code;

  final rawReason = absence.rawReason ?? '';
  final reasonLower = rawReason.trim().toLowerCase();
  final type = (absence.type ?? '').toLowerCase();

  if (reasonLower == 'back in training') {
    return loc.alertsBackTrainingDesc;
  }

  final isDuty = type == 'internationalduty' ||
      type.contains('international') ||
      type.contains('duty') ||
      type.contains('selec');

  final returnDate = absence.returnDate;
  if (isDuty) {
    if (returnDate != null && returnDate.isNotEmpty) {
      final interpreted = interpretReturnDate(returnDate, l10n: loc, localeCode: code);
      return loc.alertsDutyReturns(interpreted);
    }
    if (rawReason.isNotEmpty &&
        RegExp(r'^(Early|Mid|Late)\s+', caseSensitive: false).hasMatch(rawReason)) {
      final interpreted = interpretReturnDate(rawReason, l10n: loc, localeCode: code);
      return loc.alertsDutyReturns(interpreted);
    }
  }

  if (returnDate != null && returnDate.isNotEmpty) {
    final interpreted = interpretReturnDate(returnDate, l10n: loc, localeCode: code);
    return loc.alertsReturnsWhen(interpreted);
  }

  if (rawReason.isNotEmpty &&
      RegExp(r'^(Early|Mid|Late)\s+', caseSensitive: false).hasMatch(rawReason)) {
    final interpreted = interpretReturnDate(rawReason, l10n: loc, localeCode: code);
    return loc.alertsReturnsWhen(interpreted);
  }

  return null;
}

/// Etiqueta traducida de la insignia de baja
String absenceBadgeLabel(Absence absence, AppLocalizations l10n) {
  final rawReason = (absence.rawReason ?? '').trim().toLowerCase();
  final type = (absence.type ?? '').trim().toLowerCase();

  if (rawReason == 'back in training') {
    return l10n.alertsBadgeReturns;
  }
  if (rawReason == 'doubtful' ||
      absence.kind == AbsenceKind.doubt ||
      type.contains('question')) {
    return l10n.alertsBadgeDoubt;
  }
  if (type == 'internationalduty' ||
      type.contains('international') ||
      type.contains('duty') ||
      type.contains('selec')) {
    return l10n.alertsBadgeDuty;
  }
  if (absence.kind == AbsenceKind.suspended ||
      type == 'suspension' ||
      type.contains('suspen') ||
      absence.reason == AbsenceReason.suspension) {
    return l10n.alertsBadgeSuspension;
  }
  return l10n.alertsBadgeInjury;
}

/// Color de la insignia de baja
Color absenceBadgeColor(Absence absence) {
  final rawReason = (absence.rawReason ?? '').trim().toLowerCase();
  final type = (absence.type ?? '').trim().toLowerCase();

  if (rawReason == 'back in training') {
    return const Color(0xff05ffa1); // QfColors.green
  }
  if (rawReason == 'doubtful' ||
      absence.kind == AbsenceKind.doubt ||
      type.contains('question')) {
    return const Color(0xfffcee0a); // QfColors.gold
  }
  if (type == 'internationalduty' ||
      type.contains('international') ||
      type.contains('duty') ||
      type.contains('selec')) {
    return const Color(0xff00f0ff); // QfColors.cyan
  }
  if (absence.kind == AbsenceKind.suspended ||
      type == 'suspension' ||
      type.contains('suspen') ||
      absence.reason == AbsenceReason.suspension) {
    return const Color(0xffff2a6d); // QfColors.magenta
  }
  return const Color(0xffff2a6d); // QfColors.magenta
}
