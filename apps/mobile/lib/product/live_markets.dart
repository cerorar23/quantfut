import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import 'live_api.dart';
import 'live_market_detail.dart';
import 'market_catalog.dart';
import 'market_hub.dart';

/// Mercados del servidor que componen cada familia del catálogo.
const familyMarkets = <String, List<String>>{
  'goals': ['totals'],
  'team_goals': [
    'team_totals_home',
    'team_totals_away',
    'home_to_score',
    'away_to_score',
  ],
  'corners': ['corners'],
  'corners_team': ['corners_home', 'corners_away'],
  'handicap': ['spreads'],
  'double_chance': ['double_chance'],
  'winner': ['h2h'],
  'cards': ['cards'],
};

/// Resueltos de una familia según el servidor (historial vivo). Sin datos del
/// servidor devuelve null y la pantalla usa el catálogo empaquetado.
PublishedRecord? serverRecord(JsonMap historial, String familyId) {
  final byMarket = jsonMap(historial['por_mercado']);
  var cases = 0, won = 0;
  for (final key in familyMarkets[familyId] ?? const <String>[]) {
    final m = jsonMap(byMarket[key]);
    cases += (m['n'] as num?)?.toInt() ?? 0;
    won += (m['aciertos'] as num?)?.toInt() ?? 0;
  }
  return byMarket.isEmpty || won > cases ? null : PublishedRecord(cases, won);
}

/// Pestaña Mercados de fútbol: radar animado + una tarjeta por familia de mercado.
///
/// Todo sale de [MarketCatalog] (evidencia validada y resultados publicados).
/// No hay alertas en vivo porque el modelo pronostica antes del partido; la
/// pantalla no insinúa lo contrario.
class MarketsDashboard extends StatelessWidget {
  const MarketsDashboard({
    super.key,
    required this.api,
    required this.alta,
    this.onVip,
    this.agenda = const [],
    this.onOpenMatch,
  });

  /// Cliente para pedir el historial de cada mercado.
  final QuantFutApi api;

  /// Bloque `alta_probabilidad` de /home: próximos pronósticos e historial.
  final JsonMap alta;

  /// Abre la pantalla VIP desde un candado.
  final VoidCallback? onVip;

  /// Agenda de /home: de ella salen los escudos de los partidos próximos.
  final List<JsonMap> agenda;

  /// Abre la ficha de un partido al tocar su pronóstico.
  final ValueChanged<String>? onOpenMatch;

  @override
  Widget build(BuildContext context) => FutureBuilder<MarketCatalog>(
    future: MarketCatalog.load(),
    initialData: MarketCatalog.current,
    builder: (context, snapshot) {
      final catalog = snapshot.data;
      if (catalog == null) {
        return const Padding(
          padding: EdgeInsets.symmetric(vertical: 40),
          child: Center(child: CircularProgressIndicator()),
        );
      }
      final families = catalog.forSport(sportFootball);
      final historial = jsonMap(alta['historial']);
      final upcoming = [
        for (final p in (alta['proximos'] as List? ?? const [])) jsonMap(p),
      ];
      final locked = [
        for (final p in (alta['vip'] as List? ?? const [])) jsonMap(p),
      ];
      final liveOverall = (historial['n'] as num?) == null
          ? null
          : PublishedRecord(
              (historial['n'] as num).toInt(),
              (historial['aciertos'] as num?)?.toInt() ?? 0,
            );
      MarketTileData tile(MarketFamily f) {
        final (color, icon) = marketLook(f.id);
        final best = f.bestSupported(catalog.minimumCases);
        return MarketTileData(
          id: f.id,
          title: f.localTitle,
          detail: best == null
              ? context.l10n.marketsInReview
              : '${best.localLabel} · ${casesLabel(best.cases)}',
          color: color,
          icon: icon,
          percent: best?.observed,
          record: serverRecord(historial, f.id) ?? f.published,
        );
      }

      final tiles = [for (final f in families) tile(f)];
      return RadarClock(
        builder: (context, clock) => Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            MarketsHero(
              clock: clock,
              colors: [for (final f in families) marketLook(f.id).$1],
              evidence: context.l10n.marketsEvidenceAt(catalog.cutoff),
              overall: liveOverall ?? catalog.overall,
            ),
            const SizedBox(height: 12),
            MarketTilesGrid(
              clock: clock,
              tiles: tiles,
              onOpen: (t) {
                final family = families.firstWhere((f) => f.id == t.id);
                final ids = familyMarkets[family.id] ?? const <String>[];
                Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) => MarketDetailScreen(
                      api: api,
                      family: family,
                      minimum: catalog.minimumCases,
                      color: t.color,
                      markets: ids,
                      onVip: onVip,
                      agenda: agenda,
                      onOpenMatch: onOpenMatch,
                      locked: [
                        for (final p in locked)
                          if (ids.contains(p['market'])) p,
                      ],
                      upcoming: [
                        for (final p in upcoming)
                          if (ids.contains(p['market'])) p,
                      ],
                      record: t.record,
                    ),
                  ),
                );
              },
            ),
          ],
        ),
      );
    },
  );
}
