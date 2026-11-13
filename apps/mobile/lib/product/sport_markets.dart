import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import 'home_sport.dart';
import 'live_api.dart';
import 'market_catalog.dart' show PublishedRecord;
import 'market_hub.dart';
import 'published_history.dart';
import 'sport_contract.dart';
import 'qf_theme.dart';
import 'sport_images.dart';
import 'sports.dart';
import 'sports_feed.dart';
import 'sports_quotes.dart';

/// Clave de la familia de un mercado: `market` en NBA; en tenis el prefijo del `id`
/// anterior al «-» (`games_total-3` → `games_total`).
String marketFamily(SportMarket m) => m.family ?? m.market ?? m.id.split('-').first;

/// Aciertos y resueltos por familia. Solo cuentan los `eligible` (sellados antes del inicio)
/// con resultado `win` o `loss`; `push` y sin resultado no cuentan. Toda familia con algún
/// mercado aparece, aunque no tenga resueltos todavía.
Map<String, ({int won, int resolved})> hitRateByFamily(
  List<SportEvent> events,
) {
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

/// Familias de cada deporte, en el orden en que se ofrecen cuando aún no hay resueltos.
/// Todas salen en la pestaña aunque no tengan pronósticos todavía («Sin publicaciones aún»).
const sportFamilies = <SportId, List<String>>{
  kNba: [
    'winner',
    'handicap',
    'game_total',
    'team_points',
    'player_points',
    'player_rebounds',
    'player_assists',
    'player_threes',
  ],
  kTennis: [
    'winner',
    'games_total',
    'games_handicap',
    'set_winner',
    'sets_handicap',
    'sets_total',
    'tiebreak',
  ],
};

/// Pronóstico publicado. Manda el SERVIDOR: NBA trae `publicable` en cada mercado y tenis la lista `publicables`
/// de su overlay de cuotas (regla: cuota de referencia ≥ 1,20, probabilidad en banda, un pronóstico por familia,
/// sin props de jugador). Solo si el servidor no la manda (versión antigua) se usa la banda 60–95 % de respaldo.
bool isPublished(SportEvent e, SportMarket m, QuotesOverlay quotes) {
  if (!m.eligible) return false;
  final server = m.publishable ?? quotes.publishes(e.id, m.id);
  if (server != null) return server;
  return marketFamily(m) == 'winner' || inSportBand(m.probability);
}

/// Partido que aún no empezó: sus pronósticos están abiertos.
bool _open(SportEvent e) =>
    !const {
      'finished',
      'awaiting_result',
      'live',
      'cancelled',
      'no_result',
    }.contains(e.status) &&
    e.start.isAfter(DateTime.now().toUtc());

typedef SportPick = (SportEvent, SportMarket);

/// Pronósticos publicados de una familia, de todos los partidos del feed.
class FamilyPicks {
  FamilyPicks(this.family, this.title);
  final String family, title;
  final open = <SportPick>[];
  final settled = <SportPick>[];

  int get won => settled.where((p) => p.$2.outcome == 'win').length;
  int get resolved => settled
      .where((p) => p.$2.outcome == 'win' || p.$2.outcome == 'loss')
      .length;
  double? get percentValue => resolved == 0 ? null : won * 100 / resolved;
}

/// Agrupa por familia los pronósticos publicados del feed. Salen todas las familias del deporte (aunque estén
/// vacías) y las desconocidas que traiga el servidor; primero las de mayor acierto, luego el orden canónico.
List<FamilyPicks> familyPicks(
  AppLocalizations l10n,
  SportId sport,
  SportFeed feed, [
  QuotesOverlay quotes = QuotesOverlay.empty,
]) {
  final labels = <String, String>{};
  final byFamily = <String, FamilyPicks>{};
  final generic = isGenericSport(sport);
  // Deporte del catálogo sin pantalla propia: familias y nombres del catálogo (`otros` al final).
  final catalogOrder = generic ? catalogFamilyIds(sport) : const <String>[];
  FamilyPicks of(String key, [String? label]) => byFamily.putIfAbsent(
    key,
    () => FamilyPicks(
      key,
      generic ? contractFamilyTitle(l10n, sport, key) : sportFamilyTitle(l10n, key, fallback: label),
    ),
  );
  for (final key in sportFamilies[sport] ?? catalogOrder) {
    of(key);
  }
  for (final e in feed.events) {
    final featured = featuredMarket(e);
    for (final m in e.markets) {
      labels.putIfAbsent(marketFamily(m), () => m.label);
      final f = of(marketFamily(m), m.label);
      // El historial web cuenta el destacado del servidor, aunque la regla
      // de publicación actual no lo incluya en el overlay de cuotas.
      if (m.eligible &&
          inPublishedHistory(e.start) &&
          featured?.id == m.id &&
          (m.outcome == 'win' || m.outcome == 'loss')) {
        f.settled.add((e, m));
      }
      if (m.outcome == null && _open(e) && isPublished(e, m, quotes)) {
        f.open.add((e, m));
      }
    }
  }
  final order = sportFamilies[sport] ?? catalogOrder;
  int canon(FamilyPicks f) {
    final i = order.indexOf(f.family);
    return i < 0 ? order.length : i;
  }

  // `otros` va siempre al final de un deporte nuevo, tenga o no acierto registrado.
  int tail(FamilyPicks f) => generic && f.family == otherFamily ? 1 : 0;
  return byFamily.values.toList()..sort((a, b) {
    if (tail(a) != tail(b)) return tail(a).compareTo(tail(b));
    final ra = a.percentValue ?? -1, rb = b.percentValue ?? -1;
    return ra != rb ? rb.compareTo(ra) : canon(a).compareTo(canon(b));
  });
}

/// Mercados de NBA y tenis con el mismo diseño que los de fútbol: radar y una tarjeta por familia
/// (anillo de acierto, publicados n/m); tocar una familia abre sus pronósticos de hoy y anteriores.
class SportMarkets extends StatelessWidget {
  const SportMarkets({
    super.key,
    required this.api,
    required this.sport,
    required this.feed,
    required this.images,
    this.quotes = QuotesOverlay.empty,
    this.onOpenEvent,
    this.onRetry,
  });

  final QuantFutApi api;
  final SportId sport;
  final SportFeed feed;
  final ImageCatalog images;
  final QuotesOverlay quotes;

  /// Abre la ficha del partido al tocar un pronóstico.
  final ValueChanged<SportEvent>? onOpenEvent;
  final Future<void> Function()? onRetry;

  @override
  Widget build(BuildContext context) {
    final retry = onRetry ?? () async {};
    if (!feed.ready) return SportFeedError(onRetry: retry);
    final l10n = context.l10n;
    final families = familyPicks(l10n, sport, feed, quotes);
    final accent = sportCatalog.spec(sport).accent;
    final won = families.fold<int>(0, (s, f) => s + f.won);
    final resolved = families.fold<int>(0, (s, f) => s + f.resolved);
    final tiles = [
      for (final f in families)
        MarketTileData(
          id: f.family,
          title: f.title,
          detail: l10n.sfCounts(f.open.length, f.resolved),
          color: marketLook(f.family).$1,
          icon: marketLook(f.family).$2,
          percent: f.percentValue,
          record: PublishedRecord(f.resolved, f.won),
        ),
    ];
    return RefreshIndicator(
      onRefresh: retry,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
        children: [
          RadarClock(
            builder: (context, clock) => Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                MarketsHero(
                  clock: clock,
                  accent: accent,
                  colors: [for (final f in families) marketLook(f.family).$1],
                  evidence: resolved > 0
                      ? l10n.sportHitWindow(resolved)
                      : l10n.sfRangeNote,
                  overall: PublishedRecord(resolved, won),
                ),
                const SizedBox(height: 12),
                MarketTilesGrid(
                  clock: clock,
                  tiles: tiles,
                  onOpen: (t) {
                    final f = families.firstWhere((x) => x.family == t.id);
                    Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder: (_) => SportMarketDetailScreen(
                          api: api,
                          sport: sport,
                          picks: f,
                          color: t.color,
                          images: images,
                          quotes: quotes,
                          onOpenEvent: onOpenEvent,
                        ),
                      ),
                    );
                  },
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          Text(
            l10n.historyWebSince,
            key: const ValueKey('sport-range-note'),
            style: const TextStyle(fontSize: 11, color: QfColors.muted),
          ),
          if (sport == kTennis) ...[
            const SizedBox(height: 6),
            Text(
              l10n.imageCredits,
              style: const TextStyle(color: QfColors.muted, fontSize: 11),
            ),
          ],
        ],
      ),
    );
  }
}

/// Pantalla de una familia de NBA o tenis: Hoy (abiertos) y Anteriores (resueltos), con la misma
/// tarjeta que fútbol: avatares de los dos lados, pronóstico, probabilidad, cuota y casa.
class SportMarketDetailScreen extends StatelessWidget {
  const SportMarketDetailScreen({
    super.key,
    required this.api,
    required this.sport,
    required this.picks,
    required this.color,
    required this.images,
    required this.quotes,
    this.onOpenEvent,
  });

  final QuantFutApi api;
  final SportId sport;
  final FamilyPicks picks;
  final Color color;
  final ImageCatalog images;
  final QuotesOverlay quotes;
  final ValueChanged<SportEvent>? onOpenEvent;

  /// NBA: visitante primero («VIS @ LOC»); tenis: la lista del feed.
  MarketPick _pick(BuildContext context, SportPick p) {
    final (e, m) = p;
    final l10n = context.l10n;
    final nba = sport == kNba;
    final (first, second) = nba ? (e.away, e.home) : (e.home, e.away);
    Widget Function(double) avatar(String name) =>
        (size) => eventAvatar(api, images, e, name, size: size);
    final quote = quoteFor(e, m, quotes);
    final parts = (e.score ?? '').split(RegExp(r'\s*[–-]\s*'));
    final score = parts.length == 2 && e.status == 'finished'
        ? (nba ? '${parts[1]}-${parts[0]}' : '${parts[0]}-${parts[1]}')
        : null;
    return MarketPick(
      home: first,
      away: second,
      homeAvatar: avatar(first),
      awayAvatar: avatar(second),
      kickoff: e.start,
      league: sport == kTennis ? e.league : null,
      pick: sportPickText(l10n, m),
      probability: m.probability,
      price: quote?.price,
      book: quote?.book,
      quoteAt: quote?.asOf,
      outcome: m.outcome,
      score: score,
      onTap: onOpenEvent == null ? null : () => onOpenEvent!(e),
    );
  }

  static bool _sameDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final now = DateTime.now();
    final open = [...picks.open]
      ..sort((a, b) {
        final t = a.$1.start.compareTo(b.$1.start);
        return t != 0 ? t : b.$2.probability.compareTo(a.$2.probability);
      });
    final settled = [...picks.settled]
      ..sort((a, b) {
        final t = b.$1.start.compareTo(a.$1.start);
        return t != 0 ? t : b.$2.probability.compareTo(a.$2.probability);
      });
    final todays = settled.where(
      (p) =>
          _sameDay(p.$1.start.toLocal(), now) &&
          (p.$2.outcome == 'win' || p.$2.outcome == 'loss'),
    );
    final todayWon = todays.where((p) => p.$2.outcome == 'win').length;
    final history = <Widget>[];
    String? current;
    for (final p in settled) {
      final label = marketDayLabel(p.$1.start.toLocal());
      if (label != current) {
        current = label;
        history.add(marketDayChip(label));
      }
      history.add(MarketPickCard(color: color, data: _pick(context, p)));
    }
    return MarketScaffold(
      title: picks.title,
      color: color,
      today: PublishedRecord(todays.length, todayWon),
      overall: PublishedRecord(picks.resolved, picks.won),
      todayCount: open.length,
      todayTab: open.isEmpty
          ? marketEmptyState(l10n.mdEmptyToday)
          : ListView(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
              children: [
                for (final p in open)
                  MarketPickCard(
                    key: ValueKey('sport-open-${p.$1.id}-${p.$2.id}'),
                    color: color,
                    data: _pick(context, p),
                  ),
              ],
            ),
      historyTab: history.isEmpty
          ? marketEmptyState(l10n.mdEmptyHistory)
          : ListView(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
              children: history,
            ),
    );
  }
}
