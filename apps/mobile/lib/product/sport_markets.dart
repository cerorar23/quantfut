import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import 'home_sport.dart';
import 'live_api.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';
import 'sports.dart';
import 'sports_feed.dart';

/// Clave de la familia de un mercado: `market` en NBA; en tenis el prefijo del `id`
/// anterior al «-» (`games_total-3` → `games_total`).
String marketFamily(SportMarket m) => m.market ?? m.id.split('-').first;

/// Aciertos y resueltos por familia. Solo cuentan los `eligible` (sellados antes del inicio)
/// con resultado `win` o `loss`; `push` y sin resultado no cuentan. Toda familia con algún
/// mercado aparece, aunque no tenga resueltos todavía.
Map<String, ({int won, int resolved})> hitRateByFamily(List<SportEvent> events) {
  final out = <String, ({int won, int resolved})>{};
  for (final e in events) {
    for (final m in e.markets) {
      final key = marketFamily(m);
      var (:won, :resolved) = out[key] ?? (won: 0, resolved: 0);
      if (m.eligible && (m.outcome == 'win' || m.outcome == 'loss')) {
        resolved++;
        if (m.outcome == 'win') won++;
      }
      out[key] = (won: won, resolved: resolved);
    }
  }
  return out;
}

// Segunda pestaña: NBA «Jugadores» (player_*), tenis «Juegos» (games_*).
bool _secondTab(SportKind sport, String family) => sport == SportKind.nba
    ? family.startsWith('player_')
    : family.startsWith('games');

/// Mercados de NBA y tenis: una tarjeta por familia con el acierto histórico sobre los
/// resueltos elegibles. Pestañas internas: NBA Partido | Jugadores, tenis Partido | Juegos.
class SportMarkets extends StatefulWidget {
  const SportMarkets({
    super.key,
    required this.sport,
    required this.feed,
    this.onRetry,
  });

  final SportKind sport;
  final SportFeed feed;
  final Future<void> Function()? onRetry;

  @override
  State<SportMarkets> createState() => _SportMarketsState();
}

class _SportMarketsState extends State<SportMarkets> {
  bool _second = false;

  @override
  Widget build(BuildContext context) {
    final retry = widget.onRetry ?? () async {};
    if (!widget.feed.ready) return SportFeedError(onRetry: retry);
    final l10n = context.l10n;
    final rates = hitRateByFamily(widget.feed.events);
    // Nombre de la familia: etiqueta del primer mercado que la trae.
    final labels = <String, String>{};
    for (final e in widget.feed.events) {
      for (final m in e.markets) {
        labels.putIfAbsent(marketFamily(m), () => m.label);
      }
    }
    final keys = [
      for (final k in rates.keys)
        if (_secondTab(widget.sport, k) == _second) k,
    ]..sort();
    final nba = widget.sport == SportKind.nba;
    return RefreshIndicator(
      onRefresh: retry,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
        children: [
          Row(
            children: [
              _tab(l10n.marketsTabGame, !_second, () => setState(() => _second = false)),
              const SizedBox(width: 8),
              _tab(
                nba ? l10n.marketsTabPlayers : l10n.marketsTabGames,
                _second,
                () => setState(() => _second = true),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (rates.values.fold<int>(0, (s, r) => s + r.resolved) > 0) ...[
            Text(
              l10n.sportHitWindow(rates.values.fold<int>(0, (s, r) => s + r.resolved)),
              key: const ValueKey('sport-hit-window'),
              style: const TextStyle(fontSize: 11, color: QfColors.muted),
            ),
            const SizedBox(height: 8),
          ],
          if (keys.isEmpty)
            Padding(
              padding: const EdgeInsets.all(16),
              child: Text(
                l10n.marketsNoPublications,
                textAlign: TextAlign.center,
                style: const TextStyle(color: QfColors.text2, fontSize: 14),
              ),
            ),
          for (final k in keys)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: _FamilyCard(
                key: ValueKey('market-family-$k'),
                name: labels[k] ?? k,
                won: rates[k]!.won,
                resolved: rates[k]!.resolved,
              ),
            ),
        ],
      ),
    );
  }

  Widget _tab(String text, bool selected, VoidCallback onTap) => Expanded(
    child: Semantics(
      button: true,
      selected: selected,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onTap,
        child: Container(
          constraints: const BoxConstraints(minHeight: 44),
          alignment: Alignment.center,
          decoration: ShapeDecoration(
            color: selected ? QfColors.primary.withValues(alpha: .13) : QfColors.surface,
            shape: CutCornerBorder(
              cut: 8,
              side: BorderSide(color: selected ? QfColors.primary : QfColors.border),
            ),
          ),
          child: Text(
            text,
            style: TextStyle(
              fontFamily: qfDisplay,
              fontWeight: FontWeight.w700,
              fontSize: 14,
              letterSpacing: .8,
              color: selected ? QfColors.primary : QfColors.text2,
            ),
          ),
        ),
      ),
    ),
  );
}

/// Familia: nombre, % de acierto grande en primary, barra de 10 tramos y «{won}/{resolved}
/// publicados». Sin resueltos: estilo neutro «En revisión» y sin barra.
class _FamilyCard extends StatelessWidget {
  const _FamilyCard({
    super.key,
    required this.name,
    required this.won,
    required this.resolved,
  });

  final String name;
  final int won, resolved;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final review = resolved == 0;
    return QfCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  name,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: QfColors.text,
                    fontFamily: 'Gilroy Bold',
                    fontSize: 14,
                  ),
                ),
              ),
              if (!review)
                Text(
                  percentText(won * 100 / resolved),
                  style: const TextStyle(
                    fontFamily: qfMono,
                    fontWeight: FontWeight.w500,
                    fontSize: 24,
                    color: QfColors.primary,
                  ),
                ),
            ],
          ),
          const SizedBox(height: 8),
          if (review)
            Row(
              children: [
                const Icon(Icons.schedule, size: 16, color: QfColors.muted),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    l10n.marketsNoResolved,
                    style: const TextStyle(color: QfColors.muted, fontSize: 12),
                  ),
                ),
              ],
            )
          else ...[
            SegmentedBar(total: 10, filled: (won * 10 / resolved).round()),
            const SizedBox(height: 6),
            Text(
              l10n.marketsHitCount(won, resolved),
              style: const TextStyle(
                fontFamily: qfMono,
                fontSize: 12,
                color: QfColors.text2,
              ),
            ),
          ],
        ],
      ),
    );
  }
}
