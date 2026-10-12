import 'dart:convert';

import 'package:flutter/services.dart';

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

  String get cutoff =>
      '${capturedAt.day.toString().padLeft(2, '0')}/${capturedAt.month.toString().padLeft(2, '0')}/${capturedAt.year}';
  String get cutoffTime =>
      '${capturedAt.hour.toString().padLeft(2, '0')}:${capturedAt.minute.toString().padLeft(2, '0')} UTC';
  MarketFamily byId(String id) =>
      families.singleWhere((family) => family.id == id);
  List<MarketFamily> forSport(String sport) =>
      families.where((f) => f.sport == sport).toList()..sort(
        (a, b) => (b.bestSupported(minimumCases)?.observed ?? -1).compareTo(
          a.bestSupported(minimumCases)?.observed ?? -1,
        ),
      );
}

String percent(double? value) =>
    value == null ? '—' : '${value.toStringAsFixed(1).replaceAll('.', ',')} %';
String caseCount(int value) => value.toString().replaceAllMapped(
  RegExp(r'(\d)(?=(\d{3})+(?!\d))'),
  (match) => '${match[1]}.',
);
