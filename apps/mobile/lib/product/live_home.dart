import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:intl/intl.dart';

import '../l10n/app_locale.dart';
import '../l10n/pick_labels.dart';
import 'home_agenda.dart';
import 'featured_rule.dart';
import 'home_hero.dart';
import '../core/meta_events.dart';
import 'live_api.dart';
import 'live_widgets.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';
import 'sports.dart';

const _stripHeight = 136.0;

/// Inicio: avisos, resumen (monedas y acierto), boletos del día y la agenda por día con una
/// tira de días fija arriba que sigue al desplazamiento y salta al tocarla.
class HomeTab extends StatefulWidget {
  const HomeTab({
    super.key,
    required this.api,
    required this.data,
    required this.selected,
    required this.busy,
    required this.onRefresh,
    required this.onPickDate,
    required this.onOpenMatch,
    required this.onOpenPredictions,
    required this.onOpenCoins,
    this.banner = '',
    this.maintenance = false,
  });

  final QuantFutApi api;
  final JsonMap data;

  /// Primer día de la ventana que trajo el servidor.
  final DateTime selected;
  final bool busy, maintenance;
  final String banner;
  final Future<void> Function() onRefresh;
  final ValueChanged<DateTime> onPickDate;
  final ValueChanged<String> onOpenMatch;
  final ValueChanged<String> onOpenPredictions;
  final VoidCallback onOpenCoins;

  @override
  State<HomeTab> createState() => _HomeTabState();
}

class _HomeTabState extends State<HomeTab> {
  final _scroll = ScrollController();
  final _keys = <String, GlobalKey>{};
  String search = '';
  String? _active;
  bool _locked = false, _bannerClosed = false, _searching = false;
  int? coins;
  JsonMap? parley;

  @override
  void initState() {
    super.initState();
    _scroll.addListener(_track);
    unawaited(_loadExtras());
  }

  @override
  void didUpdateWidget(HomeTab old) {
    super.didUpdateWidget(old);
    if (!identical(old.data, widget.data)) {
      _active = null;
      unawaited(_loadExtras());
    }
  }

  @override
  void dispose() {
    _scroll.dispose();
    super.dispose();
  }

  /// Saldo de monedas y parley del día. Si fallan, las tarjetas se quedan en «—» o vacías.
  Future<void> _loadExtras() async {
    try {
      final wallet = jsonMap(
        jsonMap(await widget.api.request('/mobile/v1/rewards'))['wallet'],
      );
      if (mounted) setState(() => coins = (wallet['balance'] as num?)?.toInt());
    } catch (_) {}
    try {
      final body = jsonMap(await widget.api.request('/parley'));
      if (mounted) setState(() => parley = body);
    } catch (_) {}
  }

  GlobalKey _key(String day) => _keys.putIfAbsent(day, GlobalKey.new);

  String get _current => _active ?? dateKey(widget.selected);

  /// El día activo es el último cuyo encabezado ya llegó a la tira fija.
  void _track() {
    if (_locked || !_scroll.hasClients) return;
    String? found;
    for (final entry in _keys.entries) {
      final box = entry.value.currentContext?.findRenderObject();
      if (box is! RenderBox || !box.attached) continue;
      final viewport = RenderAbstractViewport.maybeOf(box);
      if (viewport == null) continue;
      final offset = viewport.getOffsetToReveal(box, 0).offset;
      if (offset <= _scroll.offset + _stripHeight + 12) found = entry.key;
    }
    final next = found ?? dateKey(widget.selected);
    if (next != _active) setState(() => _active = next);
  }

  void _jump(DateTime date, Map<String, int> counts, double viewport) {
    final key = dateKey(date);
    if ((counts[key] ?? 0) == 0) {
      setState(() => _active = key);
      liveNotice(context, context.l10n.homeNoMatchesDay);
      return;
    }
    setState(() {
      _active = key;
      _locked = true;
    });
    final target = _key(key).currentContext;
    if (target == null) return;
    unawaited(
      Scrollable.ensureVisible(
        target,
        alignment: viewport <= 0 ? 0 : (_stripHeight + 4) / viewport,
        duration: const Duration(milliseconds: 350),
        curve: Curves.easeOutCubic,
      ),
    );
  }

  void _toggleSearch() {
    // Se registra al cerrar la búsqueda con texto, no en cada tecla.
    if (_searching && search.trim().isNotEmpty) {
      MetaEvents.current?.search(search.trim());
    }
    setState(() {
      _searching = !_searching;
      if (!_searching) search = '';
    });
    if (_searching && _scroll.hasClients) {
      unawaited(
        _scroll.animateTo(
          0,
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeOut,
        ),
      );
    }
  }

  Future<void> _pick() async {
    final today = DateTime.now();
    final date = await showDatePicker(
      context: context,
      initialDate: widget.selected.isBefore(today) ? today : widget.selected,
      firstDate: DateTime(today.year, today.month, today.day),
      lastDate: today.add(const Duration(days: 365)),
    );
    if (date != null && mounted) widget.onPickDate(date);
  }

  JsonMap? _topPick() {
    final report = jsonMap(widget.data['alta_probabilidad']);
    final all = [...jsonRows(report['proximos']), ...jsonRows(report['vip'])];
    if (all.isEmpty) return null;
    final open = all.where((p) => p['locked'] != true).toList();
    final pool = open.isEmpty ? all : open;
    pool.sort(
      (a, b) => ((b['prob'] as num?) ?? 0).compareTo((a['prob'] as num?) ?? 0),
    );
    return pool.first;
  }

  /// Destacado del día: entre los pronósticos abiertos (el bloqueado no se enseña aquí), el de mayor
  /// probabilidad con cuota >= 1,20 y probabilidad >= 75 % (`featured_rule.dart`); si ninguno cumple la regla no hay tarjeta.
  JsonMap? _featuredPick() {
    final report = jsonMap(widget.data['alta_probabilidad']);
    final open = [
      ...jsonRows(report['proximos']),
      ...jsonRows(report['vip']),
    ].where((p) => p['locked'] != true);
    return bestBySafety<JsonMap>(
      open,
      (p) => p['prob'],
      (p) => p['ref_price'] ?? p['price'],
    );
  }

  Widget? _hero(BuildContext context) {
    final pick = _featuredPick();
    if (pick == null) return null;
    final id = pick['match_id'];
    JsonMap? match;
    for (final m in jsonRows(widget.data['agenda'])) {
      if (id != null && '${m['match_id']}' == '$id') match = m;
    }
    // Escudo desde la agenda; si el partido no está en ella, iniciales del nombre del pick.
    JsonMap side(String key) {
      final team = jsonMap(match?[key]);
      return team.isEmpty ? {'nombre': pick[key] ?? ''} : team;
    }

    final localName = '${pick['local'] ?? ''}';
    final awayName = '${pick['visitante'] ?? ''}';
    final league = '${jsonMap(match?['liga'])['nombre'] ?? ''}';
    final ko = dateValue(match?['kickoff_utc'])?.toLocal();
    final metaStr = [
      if (league.isNotEmpty) league,
      if (ko != null) '${localDate(DateFormat.MMMEd, ko)} ${localDate(DateFormat.Hm, ko)}',
    ].join(' · ');

    final probs = <(String, double)>[];
    final probMap = jsonMap(match?['probabilities']);
    if (probMap['home'] is num && probMap['away'] is num) {
      final h = (probMap['home'] as num).toDouble();
      final a = (probMap['away'] as num).toDouble();
      final d = (probMap['draw'] as num?)?.toDouble();
      if (d != null) {
        probs.addAll([('1', h), ('X', d), ('2', a)]);
      } else {
        probs.addAll([('1', h), ('2', a)]);
      }
    }

    return HomeHero(
      key: const ValueKey('home-hero'),
      sport: kFootball,
      left: TeamCrest(team: side('local'), api: widget.api, size: 58),
      right: TeamCrest(team: side('visitante'), api: widget.api, size: 58),
      homeName: localName,
      awayName: awayName,
      meta: metaStr.isEmpty ? null : metaStr,
      probabilities: probs.isEmpty ? null : probs,
      title: '$localName · $awayName',
      probability: realPercent(pick['prob']),
      pick: pickText(pick),
      kicker: context.l10n.homeFeatured,
      onTap: id == null ? null : () => widget.onOpenMatch('$id'),
    );
  }

  JsonMap? _parleyTicket() {
    final days = jsonRows(parley?['dias']);
    if (days.isEmpty) return null;
    final tickets = jsonRows(days.first['tickets']);
    if (tickets.isEmpty) return null;
    return tickets.firstWhere(
      (t) => t['locked'] != true,
      orElse: () => tickets.first,
    );
  }

  @override
  Widget build(BuildContext context) {
    final d = widget.data;
    final agendaOn = featureEnabled(d, 'agenda');
    final needle = search.toLowerCase();
    final rows = !agendaOn
        ? const <JsonMap>[]
        : jsonRows(d['agenda']).where((m) {
            // Un partido terminado ya no se enseña aquí: queda en los registros históricos.
            if (m['estado'] == 'finished') return false;
            final name =
                '${jsonMap(m['local'])['nombre']} ${jsonMap(m['visitante'])['nombre']} ${jsonMap(m['liga'])['nombre']}'
                    .toLowerCase();
            return name.contains(needle);
          });
    final days = groupAgenda(rows);
    final counts = {for (final day in days) day.key: day.matches.length};
    final picksByMatch = <String, List<JsonMap>>{};
    final report = jsonMap(d['alta_probabilidad']);
    for (final p in [
      ...jsonRows(report['proximos']),
      ...jsonRows(report['vip']),
    ]) {
      (picksByMatch[p['match_id'] as String? ?? ''] ??= []).add(p);
    }
    return RefreshIndicator(
      onRefresh: widget.onRefresh,
      child: LayoutBuilder(
        builder: (context, box) =>
            NotificationListener<ScrollStartNotification>(
              onNotification: (n) {
                if (n.dragDetails != null) _locked = false;
                return false;
              },
              child: CustomScrollView(
                key: const ValueKey('home-scroll'),
                controller: _scroll,
                physics: const AlwaysScrollableScrollPhysics(),
                slivers: [
                  SliverToBoxAdapter(child: _top(context)),
                  SliverPersistentHeader(
                    pinned: true,
                    delegate: _Pinned(
                      height: _stripHeight,
                      child: DayStrip(
                        start: widget.selected,
                        active: _current,
                        counts: counts,
                        onDay: (date) => _jump(date, counts, box.maxHeight),
                        onPick: _pick,
                        searching: _searching,
                        onSearch: _toggleSearch,
                      ),
                    ),
                  ),
                  if (!agendaOn)
                    SliverToBoxAdapter(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: training(featureMessage(d, 'agenda')),
                      ),
                    )
                  else if (days.isEmpty)
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
                        child: DayHeader(day: day),
                      ),
                    ),
                    SliverPadding(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      sliver: SliverList.builder(
                        itemCount: day.matches.length,
                        itemBuilder: (context, i) {
                          final m = day.matches[i];
                          return MatchRow(
                            key: ValueKey('match-${m['match_id']}'),
                            match: m,
                            api: widget.api,
                            picks: picksByMatch['${m['match_id']}'] ?? const [],
                            onOpen: () =>
                                widget.onOpenMatch('${m['match_id']}'),
                          );
                        },
                      ),
                    ),
                  ],
                  const SliverToBoxAdapter(child: SizedBox(height: 24)),
                ],
              ),
            ),
      ),
    );
  }

  Widget _top(BuildContext context) {
    final l10n = context.l10n;
    final history = jsonMap(
      jsonMap(widget.data['alta_probabilidad'])['historial'],
    );
    final real = history['acierto_real'];
    final total = (history['n'] as num?)?.toInt() ?? 0;
    final hits = (history['aciertos'] as num?)?.toInt() ?? 0;
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (widget.busy) const LinearProgressIndicator(),
          if (widget.banner.isNotEmpty && !_bannerClosed)
            _Notice(
              key: const ValueKey('home-banner'),
              text: widget.banner,
              icon: Icons.campaign_outlined,
              color: QfColors.cyan,
              closeLabel: l10n.homeBannerClose,
              onClose: () => setState(() => _bannerClosed = true),
            ),
          if (widget.maintenance)
            _Notice(
              text: l10n.maintenanceNotice,
              icon: Icons.build_circle_outlined,
              color: QfColors.cyan,
            ),
          if (_hero(context) case final hero?) ...[
            hero,
            const SizedBox(height: 12),
          ],
          IntrinsicHeight(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (real is num && total > 0) ...[
                  Expanded(
                    child: _HitCard(
                      percent: real.toDouble(),
                      label: l10n.homeHitTitle,
                      detail: l10n.picksTrustDetail(hits, total),
                      onTap: () => widget.onOpenPredictions('high'),
                    ),
                  ),
                  const SizedBox(width: 8),
                ],
                Expanded(
                  child: _CoinsCard(
                    coins: coins,
                    value: coins == null ? '—' : '$coins',
                    label: l10n.rewardsMyCoins,
                    subtitle: coins != null
                        ? (coins! >= 40
                            ? l10n.homeCoinsUnlocks(coins! ~/ 40)
                            : l10n.rewardsMissing(40 - coins!))
                        : '—',
                    onTap: widget.onOpenCoins,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          Row(
            children: [
              Expanded(
                child: Text(
                  l10n.homeTicketsTitle,
                  style: const TextStyle(
                    color: Colors.white,
                    fontFamily: 'Exo 2', fontWeight: FontWeight.w800,
                    fontSize: 18,
                  ),
                ),
              ),
              TextButton(
                onPressed: () => widget.onOpenPredictions('high'),
                child: Text(l10n.homeSeeAll),
              ),
            ],
          ),
          const SizedBox(height: 4),
          IntrinsicHeight(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Expanded(child: _pickTicket(context)),
                const SizedBox(width: 12),
                Expanded(child: _parleyTicketCard(context)),
              ],
            ),
          ),
          if (_searching) ...[
            const SizedBox(height: 16),
            TextField(
              autofocus: true,
              key: const ValueKey('home-search'),
              onChanged: (s) => setState(() => search = s),
              style: const TextStyle(color: Colors.white),
              decoration: InputDecoration(
                filled: true,
                fillColor: livePanel,
                prefixIcon: const Icon(Icons.search, color: liveMuted),
                hintText: l10n.calendarSearchHint,
                hintStyle: const TextStyle(color: liveMuted),
                contentPadding: const EdgeInsets.symmetric(vertical: 12),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(16),
                  borderSide: BorderSide.none,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _pickTicket(BuildContext context) {
    final l10n = context.l10n;
    final pick = _topPick();
    final locked = pick != null && pick['locked'] == true;
    return _TicketCard(
      key: const ValueKey('ticket-high'),
      kicker: l10n.streamHighProb,
      icon: Icons.verified_outlined,
      color: liveGreen,
      onTap: () => pick != null && pick['match_id'] != null && !locked
          ? widget.onOpenMatch('${pick['match_id']}')
          : widget.onOpenPredictions('high'),
      children: pick == null
          ? [liveText(l10n.homeTicketsEmpty, size: 12, color: liveMuted)]
          : [
              Text(
                '${pick['local'] ?? ''} · ${pick['visitante'] ?? ''}',
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: Colors.white,
                  fontFamily: 'Exo 2', fontWeight: FontWeight.w700,
                  fontSize: 13,
                ),
              ),
              const SizedBox(height: 6),
              if (locked)
                liveText(
                  l10n.vipPickLabel,
                  size: 12,
                  color: liveGold,
                  bold: true,
                )
              else ...[
                liveText(
                  pickText(pick),
                  size: 12,
                  color: liveGreen,
                  bold: true,
                ),
                const SizedBox(height: 6),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    liveText(
                      realPercent(pick['prob']),
                      size: 13,
                      color: QfColors.cyan,
                      bold: true,
                    ),
                    const SizedBox(width: 4),
                    Flexible(
                      child: FittedBox(
                        fit: BoxFit.scaleDown,
                        child: Text(
                          '@ ${decimalText(pick['ref_price'] ?? pick['price'])}',
                          style: const TextStyle(
                            fontFamily: qfMono,
                            fontSize: 13,
                            color: QfColors.text,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ],
    );
  }

  Widget _parleyTicketCard(BuildContext context) {
    final l10n = context.l10n;
    final ticket = _parleyTicket();
    final locked = ticket != null && ticket['locked'] == true;
    return _TicketCard(
      key: const ValueKey('ticket-parley'),
      kicker: l10n.streamParley,
      icon: Icons.receipt_long_outlined,
      color: liveCyan,
      onTap: () => widget.onOpenPredictions('parley'),
      children: ticket == null
          ? [liveText(l10n.homeTicketsEmpty, size: 12, color: liveMuted)]
          : locked
          ? [liveText(l10n.vipPickLabel, size: 12, color: liveGold, bold: true)]
          : [
              Text(
                l10n.homeTicketOdds(decimalText(ticket['cuota_total'])),
                style: const TextStyle(
                  color: QfColors.text,
                  fontFamily: qfMono,
                  fontSize: 18,
                ),
              ),
              const SizedBox(height: 4),
              liveText(
                l10n.homeTicketLegs(jsonRows(ticket['patas']).length),
                size: 12,
                color: Colors.white,
              ),
              const SizedBox(height: 2),
              liveText(
                l10n.homeTicketJoint(realPercent(ticket['prob_total'])),
                size: 12,
                color: liveMuted,
              ),
            ],
    );
  }
}

class _Pinned extends SliverPersistentHeaderDelegate {
  const _Pinned({required this.height, required this.child});

  final double height;
  final Widget child;

  @override
  double get minExtent => height;
  @override
  double get maxExtent => height;

  @override
  Widget build(
    BuildContext context,
    double shrinkOffset,
    bool overlapsContent,
  ) => SizedBox(
    height: height,
    // La tira tiene alto fijo: con letra muy grande no puede crecer, así que se limita.
    child: MediaQuery.withClampedTextScaling(maxScaleFactor: 1.1, child: child),
  );

  @override
  bool shouldRebuild(_Pinned old) => true;
}

class _Notice extends StatelessWidget {
  const _Notice({
    super.key,
    required this.text,
    required this.icon,
    required this.color,
    this.closeLabel,
    this.onClose,
  });

  final String text;
  final IconData icon;
  final Color color;
  final String? closeLabel;
  final VoidCallback? onClose;

  @override
  Widget build(BuildContext context) => Container(
    margin: const EdgeInsets.only(bottom: 12),
    padding: const EdgeInsets.fromLTRB(14, 10, 6, 10),
    decoration: ShapeDecoration(
      color: color.withValues(alpha: .08),
      shape: CutCornerBorder(
        cut: 8,
        side: BorderSide(color: color.withValues(alpha: .35)),
      ),
    ),
    child: Row(
      children: [
        Icon(icon, color: color, size: 20),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            text,
            style: TextStyle(color: color, fontSize: 13),
          ),
        ),
        if (onClose != null)
          IconButton(
            tooltip: closeLabel,
            visualDensity: VisualDensity.compact,
            onPressed: onClose,
            icon: const Icon(Icons.close, size: 18, color: QfColors.muted),
          ),
      ],
    ),
  );
}

class _CoinsCard extends StatelessWidget {
  const _CoinsCard({
    required this.value,
    required this.label,
    required this.subtitle,
    required this.onTap,
    this.coins,
  });

  final String value, label, subtitle;
  final int? coins;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => QfCard(
    key: const ValueKey('home-coins'),
    cut: 8,
    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
    onTap: onTap,
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Text(
          label.toUpperCase(),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(
            fontFamily: qfDisplay,
            fontWeight: FontWeight.w700,
            fontSize: 11,
            letterSpacing: 1.4,
            color: QfColors.text2,
          ),
        ),
        const SizedBox(height: 2),
        FittedBox(
          fit: BoxFit.scaleDown,
          alignment: Alignment.centerLeft,
          child: Text(
            value,
            style: const TextStyle(
              fontFamily: qfMono,
              fontWeight: FontWeight.w700,
              fontSize: 24,
              color: QfColors.yellow,
            ),
          ),
        ),
        const SizedBox(height: 2),
        Text(
          subtitle,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontSize: 11, color: QfColors.muted),
        ),
      ],
    ),
  );
}

class _HitCard extends StatelessWidget {
  const _HitCard({
    required this.percent,
    required this.label,
    required this.detail,
    required this.onTap,
  });

  final double percent;
  final String label, detail;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => QfCard(
    key: const ValueKey('home-hit'),
    cut: 8,
    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
    onTap: onTap,
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Text(
          label.toUpperCase(),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(
            fontFamily: qfDisplay,
            fontWeight: FontWeight.w700,
            fontSize: 11,
            letterSpacing: 1.4,
            color: QfColors.text2,
          ),
        ),
        const SizedBox(height: 2),
        FittedBox(
          fit: BoxFit.scaleDown,
          alignment: Alignment.centerLeft,
          child: Text(
            percentText(percent, 1),
            style: const TextStyle(
              fontFamily: qfMono,
              fontWeight: FontWeight.w700,
              fontSize: 24,
              color: QfColors.green,
            ),
          ),
        ),
        const SizedBox(height: 2),
        Text(
          detail,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontSize: 11, color: QfColors.muted),
        ),
      ],
    ),
  );
}

class _TicketCard extends StatelessWidget {
  const _TicketCard({
    super.key,
    required this.kicker,
    required this.icon,
    required this.color,
    required this.onTap,
    required this.children,
  });

  final String kicker;
  final IconData icon;
  final Color color;
  final VoidCallback onTap;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) => Material(
    color: Colors.transparent,
    shape: const CutCornerBorder(cut: 8),
    clipBehavior: Clip.antiAlias,
    child: Ink(
      decoration: ShapeDecoration(
        color: QfColors.surface,
        shape: CutCornerBorder(
          cut: 8,
          side: BorderSide(color: color.withValues(alpha: .35)),
        ),
      ),
      child: InkWell(
        customBorder: const CutCornerBorder(cut: 8),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(icon, size: 16, color: color),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      kicker.toUpperCase(),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: color,
                        fontFamily: qfDisplay,
                        fontWeight: FontWeight.w700,
                        fontSize: 11,
                        letterSpacing: 1.0,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              ...children,
            ],
          ),
        ),
      ),
    ),
  );
}
