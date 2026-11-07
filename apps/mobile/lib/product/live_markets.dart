import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show mapEquals;

import '../l10n/app_locale.dart';
import 'live_api.dart';
import 'live_market_detail.dart';
import 'market_catalog.dart';
import 'market_hub.dart';
import 'published_history.dart';

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
  'btts': ['btts'],
};

/// Fútbol: las cifras y filas vienen de la misma instantánea del historial web.
/// El catálogo empaquetado solo aporta títulos y pruebas por línea.
class MarketsDashboard extends StatefulWidget {
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
  State<MarketsDashboard> createState() => _MarketsDashboardState();
}

class _MarketsDashboardState extends State<MarketsDashboard> {
  late Future<(MarketCatalog, List<JsonMap>)> _content;

  Future<(MarketCatalog, List<JsonMap>)> _load() {
    final history = loadFootballHistory(widget.api);
    final cached = MarketCatalog.current;
    if (cached != null) return history.then((rows) => (cached, rows));
    return (MarketCatalog.load(), history).wait;
  }

  @override
  void initState() {
    super.initState();
    _content = _load();
  }

  @override
  void didUpdateWidget(covariant MarketsDashboard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.api != widget.api || !mapEquals(oldWidget.alta, widget.alta)) {
      _content = _load();
    }
  }

  @override
  Widget build(BuildContext context) => FutureBuilder<(MarketCatalog, List<JsonMap>)>(
    future: _content,
    builder: (context, snapshot) {
      if (snapshot.connectionState != ConnectionState.done) {
        return const Center(child: CircularProgressIndicator());
      }
      if (snapshot.hasError) {
        return Column(children: [
          Text(context.l10n.mdLoadError),
          TextButton(
            onPressed: () => setState(() => _content = _load()),
            child: Text(context.l10n.commonRetry),
          ),
        ]);
      }
      final (catalog, rows) = snapshot.data!;
          final families = [
            ...catalog.forSport(sportFootball),
            MarketFamily.publishedOnly(
              id: 'btts',
              title: context.l10n.marketBtts,
            ),
          ];
          final upcoming = jsonRows(widget.alta['proximos']);
          final locked = jsonRows(widget.alta['vip']);
          List<JsonMap> familyRows(String id) => [
            for (final r in rows)
              if ((familyMarkets[id] ?? const <String>[]).contains(r['market']))
                r,
          ];
          final tiles = [
            for (final f in families)
              MarketTileData(
                id: f.id,
                title: f.localTitle,
                detail: context.l10n.sfCounts(
                  [...upcoming, ...locked]
                      .where(
                        (p) => (familyMarkets[f.id] ?? const <String>[])
                            .contains(p['market']),
                      )
                      .length,
                  familyRows(f.id).length,
                ),
                color: marketLook(f.id).$1,
                icon: marketLook(f.id).$2,
                percent: historyRecord(familyRows(f.id)).observed,
                record: historyRecord(familyRows(f.id)),
              ),
          ];
          return RadarClock(
            builder: (context, clock) => Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                MarketsHero(
                  clock: clock,
                  colors: [for (final f in families) marketLook(f.id).$1],
                  evidence: context.l10n.historyWebSince,
                  overall: historyRecord(rows),
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
                          api: widget.api,
                          family: family,
                          minimum: catalog.minimumCases,
                          color: t.color,
                          markets: ids,
                          onVip: widget.onVip,
                          agenda: widget.agenda,
                          onOpenMatch: widget.onOpenMatch,
                          locked: [
                            for (final p in locked)
                              if (ids.contains(p['market'])) p,
                          ],
                          upcoming: [
                            for (final p in upcoming)
                              if (ids.contains(p['market'])) p,
                          ],
                          record: t.record,
                          historyItems: familyRows(family.id),
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
