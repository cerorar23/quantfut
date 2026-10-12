import 'dart:convert';

import 'package:flutter/services.dart';
import 'package:intl/intl.dart';

import '../l10n/app_locale.dart';
import '../l10n/pick_labels.dart';
import 'live_api.dart' show localDate, percentText;

/// Identificador del deporte en `market_evidence.json` (dato, no texto visible).
const sportFootball = 'Fútbol'; // l10n-ignore

class MarketLine {
  MarketLine.fromJson(Map<String, dynamic> json)
    : key = json['key'] as String,
      label = json['label'] as String,
      cases = (json['n'] as num).toInt(),
      observed = (json['observed'] as num).toDouble(),
      expected = (json['expected'] as num?)?.toDouble(),
      baseline = (json['baseline'] as num?)?.toDouble(),
      passed = json['passed'] as bool,
      deployed = json['deployed'] as bool,
      band = json['band'] as String,
      source = json['source'] as String;
  final String key, label, band, source;
  final int cases;
  final double observed;
  final double? expected, baseline;
  final bool passed, deployed;

  bool supported(int minimum) => passed && deployed && cases >= minimum;

  /// Etiqueta de la línea en el idioma actual, reconstruida desde `key`
  /// («corners_home over 1.5», «spreads -1»…). Si no se reconoce, la del archivo.
  String get localLabel {
    final l10n = AppLocale.instance.l10n;
    final parts = key.split(' ');
    final market = parts.first;
    final side = parts.length > 1 ? parts[1] : '';
    final line = parts.length > 2 ? num.tryParse(parts[2]) : null;
    switch (market) {
      case 'corners_home':
      case 'corners_away':
        return line == null
            ? label
            : l10n.lineTeamCorners(
                market == 'corners_home' ? l10n.commonHome : l10n.commonAway,
                side,
                lineText(line),
              );
      case 'corners':
        return line == null ? label : l10n.selCorners(side, lineText(line));
      case 'totals':
        return line == null ? label : l10n.selGoals(side, lineText(line));
      case 'cards':
        return line == null ? label : l10n.selCards(side, lineText(line));
      case 'spreads':
        final handicap = num.tryParse(side);
        if (handicap == null) return label;
        final text = handicap == 0
            ? '0'
            : '${handicap > 0 ? '+' : '\u2212'}${lineText(handicap.abs())}';
        return l10n.lineHandicap(text);
      case 'team_totals_home':
        return l10n.lineHomeScores;
      case 'team_totals_away':
        return l10n.lineAwayScores;
      case 'double_chance':
        return l10n.lineDoubleChance;
      case 'h2h':
        return l10n.lineWinner;
      case 'nba_winner':
        return l10n.famNbaWinnerTitle;
      case 'nba_team':
        return l10n.famNbaTeamTitle;
      case 'nba_total':
        return l10n.famNbaTotalTitle;
    }
    return label;
  }
}

class PublishedRecord {
  PublishedRecord(this.cases, this.won) {
    if (cases < 0 || won < 0 || won > cases) {
      throw const FormatException('Invalid published record');
    }
  }
  factory PublishedRecord.fromJson(Map<String, dynamic> json) =>
      PublishedRecord(
        (json['n'] as num).toInt(),
        ((json['won'] ?? json['aciertos']) as num).toInt(),
      );
  final int cases, won;
  double? get observed => cases == 0 ? null : 100 * won / cases;
}

class MarketFamily {
  MarketFamily.fromJson(Map<String, dynamic> json)
    : id = json['id'] as String,
      title = json['title'] as String,
      subtitle = json['subtitle'] as String,
      sport = json['sport'] as String,
      origin = json['origin'] as String,
      experimental = json['experimental'] as bool,
      published = PublishedRecord.fromJson(
        json['published'] as Map<String, dynamic>,
      ),
      lines = (json['lines'] as List)
          .map((row) => MarketLine.fromJson(row as Map<String, dynamic>))
          .toList(growable: false);
  final String id, title, subtitle, sport, origin;
  final bool experimental;
  final PublishedRecord published;
  final List<MarketLine> lines;

  /// Título y subtítulo en el idioma actual, por identificador de familia.
  String get localTitle {
    final l10n = AppLocale.instance.l10n;
    return switch (id) {
      'corners_team' => l10n.famCornersTeamTitle,
      'handicap' => l10n.famHandicapTitle,
      'team_goals' => l10n.famTeamGoalsTitle,
      'double_chance' => l10n.famDoubleChanceTitle,
      'corners' => l10n.famCornersTitle,
      'goals' => l10n.famGoalsTitle,
      'cards' => l10n.famCardsTitle,
      'winner' => l10n.famWinnerTitle,
      'nba_winner' => l10n.famNbaWinnerTitle,
      'nba_team' => l10n.famNbaTeamTitle,
      'nba_total' => l10n.famNbaTotalTitle,
      _ => title,
    };
  }

  String get localSubtitle {
    final l10n = AppLocale.instance.l10n;
    return switch (id) {
      'corners_team' => l10n.famCornersTeamSubtitle,
      'handicap' => l10n.famHandicapSubtitle,
      'team_goals' => l10n.famTeamGoalsSubtitle,
      'double_chance' => l10n.famDoubleChanceSubtitle,
      'corners' => l10n.famCornersSubtitle,
      'goals' => l10n.famGoalsSubtitle,
      'cards' => l10n.famCardsSubtitle,
      'winner' => l10n.famWinnerSubtitle,
      'nba_winner' || 'nba_team' || 'nba_total' => l10n.famNbaSubtitle,
      _ => subtitle,
    };
  }

  MarketLine? bestSupported(int minimum) {
    if (experimental) return null;
    final eligible = lines.where((line) => line.supported(minimum)).toList()
      ..sort((a, b) => b.observed.compareTo(a.observed));
    return eligible.isEmpty ? null : eligible.first;
  }
}

class MarketCatalog {
  MarketCatalog.fromJson(Map<String, dynamic> json)
    : capturedAt = DateTime.parse(json['captured_at_utc'] as String).toUtc(),
      minimumCases = (json['selection_min_cases'] as num).toInt(),
      overall = PublishedRecord.fromJson(
        json['overall'] as Map<String, dynamic>,
      ),
      families = (json['families'] as List)
          .map((row) => MarketFamily.fromJson(row as Map<String, dynamic>))
          .toList(growable: false);
  final DateTime capturedAt;
  final int minimumCases;
  final PublishedRecord overall;
  final List<MarketFamily> families;
  static Future<MarketCatalog>? _loaded;
  static MarketCatalog? current;
  static Future<MarketCatalog> load() => _loaded ??= rootBundle
      .loadString('assets/model/market_evidence.json')
      .then(
        (body) => current = MarketCatalog.fromJson(
          jsonDecode(body) as Map<String, dynamic>,
        ),
      );

  String get cutoff => localDate(DateFormat.yMd, capturedAt);
  String get cutoffTime => '${localDate(DateFormat.Hm, capturedAt)} UTC';
  MarketFamily byId(String id) =>
      families.singleWhere((family) => family.id == id);
  List<MarketFamily> forSport(String sport) =>
      families.where((f) => f.sport == sport).toList()..sort(
        (a, b) => (b.bestSupported(minimumCases)?.observed ?? -1).compareTo(
          a.bestSupported(minimumCases)?.observed ?? -1,
        ),
      );
}

String percent(double? value) => value == null ? '—' : percentText(value, 1);

/// Cantidad con separador de miles del idioma actual (1.234 / 1,234).
String caseCount(int value) =>
    NumberFormat.decimalPattern(AppLocale.instance.code).format(value);

/// «6.934 casos» en el idioma actual.
String casesLabel(int value) =>
    AppLocale.instance.l10n.casesCount(value, caseCount(value));
