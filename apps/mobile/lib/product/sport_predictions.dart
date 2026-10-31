import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import 'home_agenda.dart';
import 'home_sport.dart';
import 'live_api.dart';
import 'live_widgets.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';
import 'sport_images.dart';
import 'sport_markets.dart';
import 'sports.dart';
import 'sports_feed.dart';

/// Alta probabilidad de NBA y tenis: pronósticos elegibles agrupados por día local, con
/// avatares, selección, probabilidad y fecha de sello; nunca cuota. Arriba, la tarjeta de
/// acierto (solo si hay al menos un resuelto). Un feed caído solo avisa en este hueco.
class SportPredictions extends StatelessWidget {
  const SportPredictions({
    super.key,
    required this.api,
    required this.sport,
    required this.feed,
    required this.images,
    required this.onOpen,
    this.onRetry,
    this.now,
  });

  final QuantFutApi api;
  final SportKind sport;
  final SportFeed feed;
  final ImageCatalog images;
  final ValueChanged<SportEvent> onOpen;
  final Future<void> Function()? onRetry;

  /// Reloj inyectable para pruebas; por defecto, ahora.
  final DateTime? now;

  @override
  Widget build(BuildContext context) {
    final retry = onRetry ?? () async {};
    if (!feed.ready) return SportFeedError(onRetry: retry);
    final clock = now ?? DateTime.now();
    final today = DateTime(clock.year, clock.month, clock.day);
    // Día local -> (evento, pick) elegibles, de mayor a menor probabilidad.
    final byDay = <DateTime, List<(SportEvent, SportMarket)>>{};
    for (final e in feed.events) {
      final local = e.start.toLocal();
      if (local.isBefore(today)) continue;
      final day = DateTime(local.year, local.month, local.day);
      for (final m in e.markets) {
        if (m.eligible) (byDay[day] ??= []).add((e, m));
      }
    }
    final days = byDay.keys.toList()..sort();
    for (final list in byDay.values) {
      list.sort((a, b) => b.$2.probability.compareTo(a.$2.probability));
    }
    final rates = hitRateByFamily(feed.events).values;
    final won = rates.fold<int>(0, (s, r) => s + r.won);
    final resolved = rates.fold<int>(0, (s, r) => s + r.resolved);
    final items = <Widget>[
      if (resolved > 0) _HitRateCard(won: won, resolved: resolved),
      if (days.isEmpty)
        Padding(
          padding: const EdgeInsets.all(16),
          child: training(context.l10n.calendarEmpty),
        ),
      for (final day in days) ...[
        _DayHeader(day: day, now: clock, sport: sport),
        for (final (e, m) in byDay[day]!)
          _PickCard(
            key: ValueKey('sport-pick-${e.id}-${m.id}'),
            api: api,
            images: images,
            event: e,
            market: m,
            onOpen: () => onOpen(e),
          ),
      ],
      if (sport == SportKind.tennis)
        Padding(
          padding: const EdgeInsets.only(top: 4),
          child: Text(
            context.l10n.imageCredits,
            style: const TextStyle(color: QfColors.muted, fontSize: 11),
          ),
        ),
    ];
    return RefreshIndicator(
      onRefresh: retry,
      child: ListView.builder(
        key: ValueKey('sport-predictions-${sport.id}'),
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
        itemCount: items.length,
        itemBuilder: (_, i) => items[i],
      ),
    );
  }
}

class _HitRateCard extends StatelessWidget {
  const _HitRateCard({required this.won, required this.resolved});

  final int won, resolved;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: QfCard(
        key: const ValueKey('sport-hit-rate'),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    l10n.picksTrustTitle,
                    style: const TextStyle(
                      color: QfColors.text,
                      fontFamily: 'Gilroy Bold',
                      fontSize: 14,
                    ),
                  ),
                ),
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
            const SizedBox(height: 2),
            Text(
              l10n.sportHitWindow(resolved),
              key: const ValueKey('sport-hit-window'),
              style: const TextStyle(fontSize: 11, color: QfColors.muted),
            ),
          ],
        ),
      ),
    );
  }
}

class _DayHeader extends StatelessWidget {
  const _DayHeader({required this.day, required this.now, required this.sport});

  final DateTime day, now;
  final SportKind sport;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: 10, bottom: 8),
    child: Row(
      children: [
        Container(width: 4, height: 18, color: sportSpecs[sport]!.accent),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            dayLabel(context.l10n, day, now),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: QfColors.text,
              fontFamily: 'Gilroy ExtraBold',
              fontSize: 16,
            ),
          ),
        ),
      ],
    ),
  );
}

class _PickCard extends StatelessWidget {
  const _PickCard({
    super.key,
    required this.api,
    required this.images,
    required this.event,
    required this.market,
    required this.onOpen,
  });

  final QuantFutApi api;
  final ImageCatalog images;
  final SportEvent event;
  final SportMarket market;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final e = event;
    final nba = e.sport == SportKind.nba;
    final sides = nba ? [e.away, e.home] : [e.home, e.away];
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: QfCard(
        onTap: onOpen,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        child: Row(
          children: [
            Column(
              children: [
                for (final name in sides)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 2),
                    child: sportAvatar(api, images, e.sport, name, size: 30),
                  ),
              ],
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    sportPickText(l10n, market),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: QfColors.success,
                      fontFamily: 'Gilroy Bold',
                      fontSize: 14,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    sides.join(' · '),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: QfColors.text2, fontSize: 12),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    l10n.predictionsSealedAt(kickoffText(market.sealedAt.toLocal())),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: QfColors.muted, fontSize: 11),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            Text(
              realPercent(market.probability),
              style: const TextStyle(
                fontFamily: qfMono,
                fontWeight: FontWeight.w500,
                fontSize: 18,
                color: QfColors.primary,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
