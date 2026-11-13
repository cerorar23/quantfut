import 'dart:async';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../l10n/app_locale.dart';
import '../l10n/pick_labels.dart';
import 'home_agenda.dart';
import 'home_hero.dart';
import 'live_api.dart';
import 'live_widgets.dart';
import 'qf_shapes.dart';
import 'quote_label.dart';
import 'qf_theme.dart';
import 'screen_definition.dart';
import 'sport_contract.dart';
import 'sport_images.dart';
import 'sport_screen_blocks.dart';
import 'sports.dart';
import 'sports_feed.dart';
import 'sports_quotes.dart';

const _stripHeight = 136.0;

/// Texto del pick: ganador por nombre; mercados de línea «{jugador} · Más de {línea}».
/// El feed no trae el texto de la línea: se compone aquí con l10n.
String sportPickText(AppLocalizations l10n, SportMarket m) {
  final line = m.line;
  // Deporte del catálogo sin pantalla propia: el contrato ya trae el texto del mercado.
  if (m.family != null) return m.label;
  if (m.market == null) {
    // Tenis: el ganador es el nombre; el resto lleva el nombre de su familia y la selección que manda el feed
    // («Más de 18.5» se reescribe en el idioma actual; un nombre o un hándicap se dejan tal cual).
    if (m.id == 'winner') return m.selection;
    final family = m.id.split('-').first;
    // l10n-ignore-start: formato de datos del feed, no texto de interfaz
    final over = RegExp(r'^(Más|Menos) de (\d+(?:[.,]\d+)?)$').firstMatch(m.selection);
    final selection = over == null
        ? m.selection
        : (over.group(1) == 'Más' ? l10n.marketOverLine : l10n.marketUnderLine)(
            lineText(num.parse(over.group(2)!.replaceAll(',', '.'))),
          );
    // l10n-ignore-end
    return '${sportFamilyTitle(l10n, family, fallback: m.label)}: $selection';
  }
  if (m.market == 'winner' || line == null) return m.selection;
  // Hándicap: el equipo con su línea con signo.
  if (m.market == 'handicap') return '${m.team ?? m.selection} ${signedLine(line)}';
  final text = m.side == 'under'
      ? l10n.marketUnderLine(lineText(line))
      : l10n.marketOverLine(lineText(line));
  final who = m.player ?? (m.market == 'team_points' ? m.team : null);
  return who == null ? text : '$who · $text';
}

/// Logo NBA por sigla o foto de tenis por nombre; sin imagen, iniciales.
Widget sportAvatar(
  QuantFutApi api,
  ImageCatalog images,
  SportId sport,
  String name, {
  double size = 30,
}) {
  if (sport == kNba) {
    final code = nbaTricode(name);
    return QfAvatar(
      url: serverImageUrl(api, code == null ? null : images.nbaLogo(code)),
      name: name,
      size: size,
    );
  }
  return QfAvatar(
    url: serverImageUrl(api, images.tennisPhoto(name)?.path),
    name: name,
    size: size,
    shape: AvatarShape.circle,
  );
}

/// Avatar de un lado de un evento. En un deporte del catálogo sin pantalla propia solo vale la imagen que el servidor
/// manda para ese lado; sin ella, iniciales. NBA y tenis siguen con [sportAvatar].
Widget eventAvatar(
  QuantFutApi api,
  ImageCatalog images,
  SportEvent event,
  String name, {
  double size = 30,
}) {
  if (!event.generic) return sportAvatar(api, images, event.sport, name, size: size);
  final path = name == event.home ? event.imageHome : (name == event.away ? event.imageAway : null);
  return QfAvatar(
    url: serverImageUrl(api, path),
    name: name,
    size: size,
    shape: AvatarShape.circle,
  );
}

// Terminado, en juego o esperando resultado: ya empezó.
bool _upcoming(SportEvent e) =>
    !const {'finished', 'awaiting_result', 'live'}.contains(e.status);

/// Evento cuyo mercado destacado tiene la mayor probabilidad entre los de hoy en adelante
/// que aún no empezaron.
(SportEvent, SportMarket)? featuredEvent(
  Iterable<SportEvent> events,
  DateTime today, {
  required DateTime now,
}) {
  (SportEvent, SportMarket)? best;
  for (final e in events) {
    final m = featuredMarket(e);
    if (m == null ||
        !_upcoming(e) ||
        e.start.toLocal().isBefore(today) ||
        !e.start.isAfter(now)) {
      continue;
    }
    if (best == null || m.probability > best.$2.probability) best = (e, m);
  }
  return best;
}

/// Aviso de feed caído con «Reintentar»; vive solo en el hueco del deporte afectado.
class SportFeedError extends StatelessWidget {
  const SportFeedError({super.key, required this.onRetry});

  final Future<void> Function() onRetry;

  @override
  Widget build(BuildContext context) => RefreshIndicator(
    onRefresh: onRetry,
    child: ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(24),
      children: [
        const SizedBox(height: 40),
        const Icon(Icons.cloud_off, color: QfColors.muted, size: 40),
        const SizedBox(height: 12),
        Text(
          context.l10n.homeFeedError,
          textAlign: TextAlign.center,
          style: const TextStyle(color: QfColors.text2, fontSize: 14),
        ),
        const SizedBox(height: 16),
        Center(
          child: FilledButton(
            key: const ValueKey('sport-feed-retry'),
            style: FilledButton.styleFrom(
              backgroundColor: QfColors.primary,
              foregroundColor: QfColors.onPrimary,
              minimumSize: const Size(120, 44),
            ),
            onPressed: onRetry,
            child: Text(context.l10n.commonRetry),
          ),
        ),
      ],
    ),
  );
}

/// Inicio de NBA y tenis: destacado, jugadores con pronóstico (NBA), tira de días y agenda
/// agrupada por día local (NBA por hora, tenis por torneo). Un feed caído solo afecta a
/// este deporte: aviso y «Reintentar» en su hueco.
class HomeSport extends StatefulWidget {
  const HomeSport({
    super.key,
    required this.api,
    required this.sport,
    required this.feed,
    required this.images,
    required this.onOpen,
    required this.onRetry,
    this.quotes = QuotesOverlay.empty,
    this.now,
    this.onVip,
  });

  final QuantFutApi api;
  final SportId sport;
  final SportFeed feed;

  /// Cuotas de referencia del deporte; vacías si no llegaron (la interfaz las pinta aparte).
  final QuotesOverlay quotes;
  final ImageCatalog images;
  final ValueChanged<SportEvent> onOpen;
  final Future<void> Function() onRetry;

  /// Reloj inyectable para pruebas; por defecto, ahora.
  final DateTime? now;

  /// Abre los planes (bloque `vip` de la definición de pantallas de un deporte nuevo).
  final VoidCallback? onVip;

  @override
  State<HomeSport> createState() => _HomeSportState();
}

class _HomeSportState extends State<HomeSport> {
  final _scroll = ScrollController();
  final _keys = <String, GlobalKey>{};
  String search = '';
  bool _searching = false;
  String? _active;
  DateTime? _start;

  DateTime get _today {
    final n = widget.now ?? DateTime.now();
    return DateTime(n.year, n.month, n.day);
  }

  DateTime get _first => _start ?? _today;

  @override
  void dispose() {
    _scroll.dispose();
    super.dispose();
  }

  GlobalKey _key(String day) => _keys.putIfAbsent(day, GlobalKey.new);

  void _jump(DateTime date, Map<String, int> counts, double viewport) {
    final key = dateKey(date);
    setState(() => _active = key);
    if ((counts[key] ?? 0) == 0) {
      liveNotice(context, context.l10n.homeNoMatchesDay);
      return;
    }
    final target = _key(key).currentContext;
    if (target == null) return;
    unawaited(
      Scrollable.ensureVisible(
        target,
        alignment: viewport <= 0 ? 0 : (_stripHeight + 4) / viewport,
        duration: MediaQuery.disableAnimationsOf(context)
            ? Duration.zero
            : const Duration(milliseconds: 350),
        curve: Curves.easeOutCubic,
      ),
    );
  }

  Future<void> _pick(Map<String, int> counts, double viewport) async {
    final date = await showDatePicker(
      context: context,
      initialDate: _first,
      firstDate: _today,
      lastDate: _today.add(const Duration(days: 365)),
    );
    if (date == null || !mounted) return;
    setState(() => _start = date);
    _jump(date, counts, viewport);
  }

  bool _matches(SportEvent e, String needle) =>
      needle.isEmpty ||
      [
        e.home,
        e.away,
        e.league,
        for (final m in e.markets) m.player ?? '',
      ].join(' ').toLowerCase().contains(needle);

  @override
  Widget build(BuildContext context) {
    if (!widget.feed.ready) return _error(context);
    final today = _today;
    final needle = search.trim().toLowerCase();
    final shown = [
      for (final e in widget.feed.events)
        if (!e.start.toLocal().isBefore(today) && _matches(e, needle)) e,
    ];
    final days = groupSportAgenda(shown);
    final counts = {for (final d in days) d.key: d.count};
    return RefreshIndicator(
      onRefresh: widget.onRetry,
      child: LayoutBuilder(
        builder: (context, box) => CustomScrollView(
          key: ValueKey('sport-scroll-${widget.sport}'),
          controller: _scroll,
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: _slivers(context, shown, days, counts, box.maxHeight),
        ),
      ),
    );
  }

  /// Piezas de la pantalla en su orden. NBA y tenis: el de siempre. Un deporte del catálogo sin pantalla propia: el de
  /// la definición `deporte` (secciones `destacado`, `dias`, `resumen`, `partidos` más avisos y llamada VIP); sin
  /// definición, ese mismo orden de hoy.
  List<Widget> _slivers(
    BuildContext context,
    List<SportEvent> shown,
    List<SportAgendaDay> days,
    Map<String, int> counts,
    double viewport,
  ) {
    Widget strip() => SliverPersistentHeader(
      pinned: true,
      delegate: _PinnedStrip(
        height: _stripHeight,
        child: DayStrip(
          start: _first,
          active: _active ?? dateKey(_first),
          counts: counts,
          onDay: (date) => _jump(date, counts, viewport),
          onPick: () => _pick(counts, viewport),
          searching: _searching,
          onSearch: () => setState(() {
            _searching = !_searching;
            if (!_searching) search = '';
          }),
        ),
      ),
    );
    List<Widget> list({bool headers = true}) => [
      if (days.isEmpty)
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: training(context.l10n.calendarEmpty),
          ),
        ),
      for (final day in days) ...[
        SliverToBoxAdapter(
          child: KeyedSubtree(
            key: _key(day.key),
            child: headers ? _dayHeader(day) : const SizedBox.shrink(),
          ),
        ),
        for (final group in day.groups)
          SliverPadding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            sliver: SliverList.list(
              children: [
                _groupHeader(group),
                for (final e in group.events)
                  _EventRow(
                    key: ValueKey('sport-event-${e.id}'),
                    event: e,
                    avatar: (name) => eventAvatar(widget.api, widget.images, e, name),
                    onOpen: () => widget.onOpen(e),
                  ),
              ],
            ),
          ),
      ],
    ];
    const tail = SliverToBoxAdapter(child: SizedBox(height: 24));
    if (!isGenericSport(widget.sport)) {
      return [
        SliverToBoxAdapter(child: _top(context, shown)),
        strip(),
        ...list(),
        if (widget.sport == kTennis)
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
              child: Text(
                context.l10n.imageCredits,
                style: const TextStyle(color: QfColors.muted, fontSize: 11),
              ),
            ),
          ),
        tail,
      ];
    }
    final screen = effectiveScreen(
      sportCatalog.screens,
      'deporte',
      widget.sport,
      defaultSportSections,
      genericSportSections,
    );
    bool shows(String section) => screen.any((b) => b.isSection && b.section == section);
    final headers = shows('resumen');
    final out = <Widget>[
      // La búsqueda se abre desde la tira de días; si el destacado no se pinta, su campo va igualmente arriba.
      if (_searching && !shows('destacado')) SliverToBoxAdapter(child: _top(context, shown, hero: false)),
    ];
    var listed = false;
    for (final b in screen) {
      if (!b.isSection) {
        final extra = screenExtra(b, api: widget.api, onVip: widget.onVip);
        if (extra != null) {
          out.add(SliverToBoxAdapter(child: Padding(padding: const EdgeInsets.fromLTRB(16, 4, 16, 0), child: extra)));
        }
        continue;
      }
      switch (b.section) {
        case 'destacado':
          out.add(SliverToBoxAdapter(child: _top(context, shown)));
        case 'dias':
          out.add(strip());
        case 'partidos':
          if (!listed) out.addAll(list(headers: headers));
          listed = true;
      }
    }
    return [...out, tail];
  }

  Widget _error(BuildContext context) =>
      SportFeedError(onRetry: widget.onRetry);

  Widget _top(BuildContext context, List<SportEvent> shown, {bool hero = true}) {
    final l10n = context.l10n;
    final featured = featuredEvent(widget.feed.events, _today, now: widget.now ?? DateTime.now());
    final players = widget.sport == kNba ? _players(shown) : const <(SportEvent, SportMarket)>[];
    final nba = widget.sport == kNba;
    Widget big(SportEvent e, String name) => eventAvatar(
      widget.api,
      widget.images,
      e,
      name,
      size: 66,
    );
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (featured case (final e, final m) when hero)
            HomeHero(
              sport: widget.sport,
              // NBA: visitante @ local.
              left: big(e, nba ? e.away : e.home),
              right: big(e, nba ? e.home : e.away),
              title: nba ? '${e.away} @ ${e.home}' : '${e.home} · ${e.away}',
              probability: realPercent(m.probability),
              pick: sportPickText(l10n, m),
              kicker: l10n.homeFeatured,
              onTap: () => widget.onOpen(e),
            ),
          if (players.isNotEmpty) ...[
            const SizedBox(height: 18),
            Text(
              l10n.homePlayersWithPicks.toUpperCase(),
              style: const TextStyle(
                fontFamily: qfDisplay,
                fontWeight: FontWeight.w700,
                fontSize: 15,
                letterSpacing: 1,
                color: QfColors.text,
              ),
            ),
            const SizedBox(height: 8),
            SizedBox(
              height: 204,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: players.length,
                separatorBuilder: (_, _) => const SizedBox(width: 8),
                itemBuilder: (context, i) => _PlayerCard(
                  api: widget.api,
                  event: players[i].$1,
                  market: players[i].$2,
                  quote: quoteFor(players[i].$1, players[i].$2, widget.quotes),
                  onOpen: () => widget.onOpen(players[i].$1),
                ),
              ),
            ),
          ],
          if (_searching) ...[
            const SizedBox(height: 16),
            TextField(
              autofocus: true,
              key: const ValueKey('sport-search'),
              onChanged: (s) => setState(() => search = s),
              style: const TextStyle(color: QfColors.text),
              decoration: InputDecoration(
                filled: true,
                fillColor: QfColors.surface,
                prefixIcon: const Icon(Icons.search, color: QfColors.muted),
                hintText: l10n.calendarSearchHint,
                hintStyle: const TextStyle(color: QfColors.muted),
                contentPadding: const EdgeInsets.symmetric(vertical: 12),
                border: const OutlineInputBorder(borderSide: BorderSide.none),
              ),
            ),
          ],
        ],
      ),
    );
  }

  /// Mejor línea por jugador (con id y sellada antes del inicio) de partidos aún por jugar.
  List<(SportEvent, SportMarket)> _players(List<SportEvent> events) {
    final best = <String, (SportEvent, SportMarket)>{};
    for (final e in events) {
      if (!_upcoming(e) || !e.start.isAfter(widget.now ?? DateTime.now())) continue;
      for (final m in e.markets) {
        final id = m.playerId;
        if (id == null || !m.eligible || m.line == null) continue;
        final old = best[id];
        if (old == null || m.probability > old.$2.probability) best[id] = (e, m);
      }
    }
    return best.values.toList()
      ..sort((a, b) => b.$2.probability.compareTo(a.$2.probability));
  }

  Widget _dayHeader(SportAgendaDay day) {
    final l10n = context.l10n;
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 18, 16, 6),
      child: Row(
        children: [
          Container(width: 4, height: 18, color: sportCatalog.spec(widget.sport).accent),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              dayLabel(l10n, day.day, widget.now ?? DateTime.now()),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: QfColors.text,
                fontFamily: 'Gilroy ExtraBold',
                fontSize: 16,
              ),
            ),
          ),
          Text(
            l10n.calendarMatchesCount(day.count),
            style: const TextStyle(color: QfColors.text2, fontSize: 12),
          ),
        ],
      ),
    );
  }

  Widget _groupHeader(SportAgendaGroup g) => Padding(
    padding: const EdgeInsets.fromLTRB(2, 8, 2, 6),
    child: Text(
      g.hour != null ? localDate(DateFormat.Hm, g.hour!) : g.tournament ?? '',
      maxLines: 1,
      overflow: TextOverflow.ellipsis,
      style: TextStyle(
        fontFamily: g.hour != null ? qfMono : qfDisplay,
        fontWeight: FontWeight.w700,
        fontSize: 13,
        letterSpacing: .6,
        color: QfColors.text2,
      ),
    ),
  );
}

/// Fila de la agenda: hora mono, los dos lados con miniatura de 30 dp y la probabilidad
/// del pick (o el marcador si terminó).
class _EventRow extends StatelessWidget {
  const _EventRow({
    super.key,
    required this.event,
    required this.avatar,
    required this.onOpen,
  });

  final SportEvent event;
  final Widget Function(String name) avatar;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    final e = event;
    final m = featuredMarket(e);
    final nba = e.sport == kNba;
    final sides = nba ? [e.away, e.home] : [e.home, e.away];
    final finished = e.status == 'finished' && e.score != null;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: QfCard(
        onTap: onOpen,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        child: Row(
          children: [
            SizedBox(
              width: 50,
              child: Text(
                localDate(DateFormat.Hm, e.start.toLocal()),
                style: const TextStyle(
                  fontFamily: qfMono,
                  fontSize: 13,
                  color: QfColors.text,
                ),
              ),
            ),
            Expanded(
              child: Column(
                children: [
                  for (final name in sides)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 3),
                      child: Row(
                        children: [
                          avatar(name),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              name,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                color: QfColors.text,
                                fontFamily: 'Gilroy Bold',
                                fontSize: 13,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            SizedBox(
              width: 64,
              child: Text(
                finished ? e.score! : (m == null ? '—' : realPercent(m.probability)),
                textAlign: TextAlign.right,
                maxLines: 1,
                style: TextStyle(
                  fontFamily: qfMono,
                  fontWeight: FontWeight.w500,
                  fontSize: 15,
                  color: finished ? QfColors.text2 : QfColors.primary,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Tarjeta de 112 dp: retrato (aro neutro: el feed no dice el equipo del jugador),
/// nombre, línea, probabilidad y cuota de referencia.
class _PlayerCard extends StatelessWidget {
  const _PlayerCard({
    required this.api,
    required this.event,
    required this.market,
    required this.quote,
    required this.onOpen,
  });

  final QuantFutApi api;
  final SportEvent event;
  final SportMarket market;
  final SportQuote? quote;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    final name = market.player ?? market.selection;
    final teams = [event.away, event.home]
        .map((t) => nbaTricode(t) ?? t)
        .join(' @ ');
    return SizedBox(
      width: 112,
      child: QfCard(
        onTap: onOpen,
        padding: const EdgeInsets.all(8),
        child: Column(
          children: [
            QfAvatar(
              url: serverImageUrl(api, nbaPlayerPhoto(market.playerId ?? '')),
              name: name,
              size: 56,
              shape: AvatarShape.circle,
              ring: QfColors.border,
            ),
            const SizedBox(height: 6),
            Text(
              name,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: QfColors.text,
                fontFamily: 'Gilroy Bold',
                fontSize: 12,
              ),
            ),
            Text(
              teams,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: QfColors.muted, fontSize: 10),
            ),
            Text(
              context.l10n.marketOverLine(lineText(market.line)),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: QfColors.text2, fontSize: 11),
            ),
            const SizedBox(height: 2),
            Text(
              realPercent(market.probability),
              style: const TextStyle(
                fontFamily: qfMono,
                fontWeight: FontWeight.w500,
                fontSize: 15,
                color: QfColors.primary,
              ),
            ),
            const SizedBox(height: 4),
            QuoteLabel(quote: quote, align: CrossAxisAlignment.center),
          ],
        ),
      ),
    );
  }
}

class _PinnedStrip extends SliverPersistentHeaderDelegate {
  const _PinnedStrip({required this.height, required this.child});

  final double height;
  final Widget child;

  @override
  double get minExtent => height;
  @override
  double get maxExtent => height;

  @override
  Widget build(BuildContext context, double shrinkOffset, bool overlapsContent) =>
      SizedBox(
        height: height,
        child: MediaQuery.withClampedTextScaling(maxScaleFactor: 1.1, child: child),
      );

  @override
  bool shouldRebuild(_PinnedStrip old) => true;
}
