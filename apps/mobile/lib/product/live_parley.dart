import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../l10n/app_locale.dart';
import '../l10n/pick_labels.dart';
import 'live_api.dart';
import 'live_widgets.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';

/// Parley del día: de 1 a 5 parlays sellados antes de los partidos, el más probable de
/// cada escalón de cuota. Todo lo manda el servidor (`/parley`); mientras esté apagado
/// o sin parlays se dice tal cual, sin rellenar nada.
class ParleyTab extends StatefulWidget {
  const ParleyTab({super.key, required this.api, this.onVip});
  final QuantFutApi api;

  /// Abre la pantalla VIP desde un parley bloqueado.
  final VoidCallback? onVip;

  @override
  State<ParleyTab> createState() => _ParleyTabState();
}

class _ParleyTabState extends State<ParleyTab> {
  JsonMap? data;
  String? error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      data = null;
      error = null;
    });
    try {
      final body = jsonMap(await widget.api.request('/parley'));
      if (mounted) setState(() => data = body);
    } catch (_) {
      if (mounted) setState(() => error = context.l10n.parleyLoadError);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (error != null) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 24),
        child: Column(
          children: [
            liveText(error!, color: liveMuted),
            const SizedBox(height: 12),
            TextButton(onPressed: _load, child: Text(context.l10n.commonRetry)),
          ],
        ),
      );
    }
    final d = data;
    if (d == null) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 40),
        child: Center(child: CircularProgressIndicator()),
      );
    }
    final rules = jsonMap(d['reglas']);
    final steps = [
      for (final e in (rules['escalones'] as List? ?? const [])) jsonMap(e),
    ];
    final days = [for (final x in (d['dias'] as List? ?? const [])) jsonMap(x)];
    final latest = days.isEmpty ? null : days.first;
    final tickets = [
      for (final t in (latest?['tickets'] as List? ?? const [])) jsonMap(t),
    ];
    final past = _lastParleys(days.skip(1), 7);
    final v2days = [for (final x in (jsonMap(d['v2'])['dias'] as List? ?? const [])) jsonMap(x)];
    final v2tickets = [
      for (final t in (v2days.isEmpty ? const [] : (v2days.first['tickets'] as List? ?? const []))) jsonMap(t),
    ];
    final l10n = context.l10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _RulesStrip(
          chip: steps.isEmpty
              ? l10n.parleySealed
              : l10n.parleyChipLine(
                  steps.length,
                  decimalText(steps.first['cuota_min']),
                  decimalText(steps.last['cuota_max']),
                ),
          onInfo: () => _showRules(context, steps),
        ),
        const SizedBox(height: 14),
        if (d['activo'] != true)
          _notice(
            Icons.hourglass_empty,
            l10n.parleyInactiveTitle,
            l10n.parleyInactiveBody,
            onInfo: () => _showRules(context, steps),
          )
        else if (tickets.isEmpty)
          _notice(
            Icons.event_busy,
            l10n.parleyNoneTitle,
            l10n.parleyNoneBody,
            onInfo: () => _showRules(context, steps),
          )
        else ...[
          for (final (i, t) in tickets.indexed)
            t['locked'] == true
                ? _LockedTicket(ticket: t, onVip: widget.onVip)
                : _TicketCard(key: ValueKey('parley-ticket-$i'), ticket: t),
        ],
        if (v2tickets.isNotEmpty) ...[
          liveHeading(l10n.parleyV2Heading),
          for (final (i, t) in v2tickets.indexed)
            t['locked'] == true
                ? _LockedTicket(ticket: t, onVip: widget.onVip)
                : _TicketCard(key: ValueKey('parley-v2-ticket-$i'), ticket: t),
        ],
        if (past.isNotEmpty) ...[
          liveHeading(l10n.parleyPastDays),
          for (final day in past) _PastDay(day: day),
        ],
        if (days.isEmpty) _NoHistory(message: l10n.parleyNoHistory),
        const SizedBox(height: 18),
      ],
    );
  }

  void _showRules(BuildContext context, List<JsonMap> steps) {
    final l10n = context.l10n;
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: livePanel,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (sheet) => SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(24, 0, 24, 20),
          child: Column(
            key: const ValueKey('parley-rules'),
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              liveText(l10n.parleyInfoTitle, bold: true, size: 19),
              const SizedBox(height: 12),
              if (steps.isNotEmpty)
                liveText(
                  l10n.parleyRange(
                    steps.length,
                    decimalText(steps.first['cuota_min']),
                    decimalText(steps.last['cuota_max']),
                  ),
                  size: 13,
                )
              else
                liveText(l10n.parleySealed, size: 13),
              const SizedBox(height: 10),
              liveText(l10n.parleyFreeNote, size: 13, color: liveMuted),
              const SizedBox(height: 10),
              liveText(l10n.parleyDisclaimer, size: 12, color: liveMuted),
            ],
          ),
        ),
      ),
    );
  }

  static Widget _notice(
    IconData icon,
    String title,
    String body, {
    required VoidCallback onInfo,
  }) => Builder(
    builder: (context) => liveCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, color: liveGold, size: 28),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    liveText(title, bold: true, size: 16),
                    const SizedBox(height: 6),
                    liveText(body, size: 12, color: liveMuted),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton.icon(
              key: const ValueKey('parley-info'),
              onPressed: onInfo,
              icon: const Icon(Icons.info_outline, size: 18),
              label: Text(context.l10n.parleyInfoTitle),
            ),
          ),
        ],
      ),
    ),
  );
}

/// Resumen de las reglas en una línea, con acceso a la explicación completa.
class _RulesStrip extends StatelessWidget {
  const _RulesStrip({required this.chip, required this.onInfo});

  final String chip;
  final VoidCallback onInfo;

  @override
  Widget build(BuildContext context) => Row(
    children: [
      Expanded(
        child: Wrap(
          spacing: 8,
          runSpacing: 6,
          children: [
            _TicketCard._chip(chip, liveCyan),
            _TicketCard._chip(context.l10n.parleyFreeChip, liveGreen),
          ],
        ),
      ),
      IconButton(
        key: const ValueKey('parley-rules-button'),
        tooltip: context.l10n.parleyInfoTitle,
        onPressed: onInfo,
        icon: const Icon(Icons.info_outline, color: liveMuted),
      ),
    ],
  );
}

class _NoHistory extends StatelessWidget {
  const _NoHistory({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) => Container(
    key: const ValueKey('parley-no-history'),
    width: double.infinity,
    padding: const EdgeInsets.all(14),
    decoration: const ShapeDecoration(
      color: QfColors.surface,
      shape: CutCornerBorder(
        cut: 10,
        side: BorderSide(color: QfColors.border),
      ),
    ),
    child: liveText(message, size: 12, color: liveMuted),
  );
}

/// Los parlays liquidan como ganado/perdido/nulo y sus patas como win/loss/push/void.
(Color, String) _outcome(dynamic o) {
  final l10n = AppLocale.instance.l10n;
  return switch (o) {
    'win' || 'ganado' => (liveGreen, l10n.parleyOutcomeWin),
    'loss' || 'perdido' => (const Color(0xffe85667), l10n.parleyOutcomeLoss),
    'push' || 'void' || 'nulo' => (liveMuted, l10n.parleyOutcomeVoid),
    _ => (liveGold, l10n.parleyOutcomePending),
  };
}

/// Parley VIP: solo se ve su escalón y el rango de cuota de ese escalón.
class _LockedTicket extends StatelessWidget {
  const _LockedTicket({required this.ticket, this.onVip});
  final JsonMap ticket;
  final VoidCallback? onVip;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: InkWell(
      borderRadius: BorderRadius.circular(16),
      onTap: onVip,
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: ShapeDecoration(
          color: QfColors.surface,
          shape: CutCornerBorder(
            cut: 16,
            side: BorderSide(color: QfColors.yellow.withValues(alpha: .35)),
          ),
        ),
        child: Row(
          children: [
            _TicketCard._chip(
              context.l10n.parleyStep(ticket['escalon'] ?? '—').toUpperCase(),
              liveCyan,
            ),
            const SizedBox(width: 10),
            Expanded(
              child: liveText(
                context.l10n.parleyOddsBetween(
                  decimalText(ticket['cuota_min']),
                  decimalText(ticket['cuota_max']),
                ),
                size: 12,
                color: liveMuted,
              ),
            ),
            const Icon(Icons.lock_outline, color: liveGold, size: 18),
            const SizedBox(width: 6),
            liveText('VIP', size: 11, bold: true, color: liveGold),
          ],
        ),
      ),
    ),
  );
}

/// Un parley como boleto: arriba escalón, estado, cuota total y probabilidad conjunta;
/// abajo, las patas en una línea de tiempo.
class _TicketCard extends StatelessWidget {
  const _TicketCard({super.key, required this.ticket});
  final JsonMap ticket;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final legs = [
      for (final p in (ticket['patas'] as List? ?? const [])) jsonMap(p),
    ];
    final (color, label) = _outcome(ticket['outcome']);
    final prob = ticket['prob_total'];
    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      decoration: ShapeDecoration(
        color: QfColors.surface,
        shape: CutCornerBorder(
          cut: 16,
          side: BorderSide(color: color.withValues(alpha: .35)),
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                _chip(
                  l10n.parleyStep(ticket['escalon'] ?? '—').toUpperCase(),
                  liveCyan,
                ),
                const SizedBox(width: 6),
                _chip(label.toUpperCase(), color),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    l10n.parleyDaySelections(legs.length).toUpperCase(),
                    textAlign: TextAlign.end,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontFamily: qfDisplay,
                      fontWeight: FontWeight.w700,
                      fontSize: 11,
                      letterSpacing: 1.2,
                      color: QfColors.muted,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            for (final (i, leg) in legs.indexed)
              _Leg(leg: leg, first: i == 0, last: i == legs.length - 1),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                    decoration: const ShapeDecoration(
                      color: QfColors.surface2,
                      shape: CutCornerBorder(
                        cut: 8,
                        side: BorderSide(color: QfColors.divider),
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          l10n.parleyJointProbLabel.toUpperCase(),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            fontFamily: qfDisplay,
                            fontWeight: FontWeight.w700,
                            fontSize: 11,
                            letterSpacing: 1.4,
                            color: QfColors.muted,
                          ),
                        ),
                        const SizedBox(height: 2),
                        FittedBox(
                          fit: BoxFit.scaleDown,
                          alignment: Alignment.centerLeft,
                          child: Text(
                            prob == null ? '—' : realPercent(prob),
                            style: const TextStyle(
                              fontFamily: qfMono,
                              fontWeight: FontWeight.w700,
                              fontSize: 22,
                              color: QfColors.cyan,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                    decoration: const ShapeDecoration(
                      color: QfColors.surface2,
                      shape: CutCornerBorder(
                        cut: 8,
                        side: BorderSide(color: QfColors.divider),
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          l10n.parleyCombOddsLabel.toUpperCase(),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            fontFamily: qfDisplay,
                            fontWeight: FontWeight.w700,
                            fontSize: 11,
                            letterSpacing: 1.4,
                            color: QfColors.muted,
                          ),
                        ),
                        const SizedBox(height: 2),
                        FittedBox(
                          fit: BoxFit.scaleDown,
                          alignment: Alignment.centerLeft,
                          child: Text(
                            '@${decimalText(ticket['cuota_total'])}',
                            style: const TextStyle(
                              fontFamily: qfMono,
                              fontWeight: FontWeight.w700,
                              fontSize: 22,
                              color: QfColors.text,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
            if (prob == null && ticket['tipo'] == 'same_game') ...[
              const SizedBox(height: 6),
              Text(
                '${l10n.parleyV2SameGame}${ticket['estado'] == 'solo_referencia' ? ' · ${l10n.parleyV2Reference}' : ''}',
                style: const TextStyle(fontSize: 11, color: QfColors.muted),
              ),
            ],
            const SizedBox(height: 10),
            Text(
              l10n.parleyNotCertaintyHint,
              style: const TextStyle(
                fontSize: 11,
                color: QfColors.muted,
              ),
            ),
          ],
        ),
      ),
    );
  }

  static Widget _chip(String text, Color color) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
    decoration: ShapeDecoration(
      color: color.withValues(alpha: .12),
      shape: CutCornerBorder(
        cut: 4,
        side: BorderSide(color: color.withValues(alpha: .4)),
      ),
    ),
    child: Text(
      text,
      style: TextStyle(
        fontFamily: qfDisplay,
        fontSize: 10,
        fontWeight: FontWeight.w700,
        letterSpacing: 0.8,
        color: color,
      ),
    ),
  );
}

/// Una pata del parley en la lista: deporte, partido, pronóstico y cuota.
class _Leg extends StatelessWidget {
  const _Leg({required this.leg, required this.first, required this.last});
  final JsonMap leg;
  final bool first, last;

  @override
  Widget build(BuildContext context) {
    final (color, _) = _outcome(leg['outcome']);
    final outcome = leg['outcome'];
    final settled = outcome != null;
    final deporte = ((leg['deporte'] as String?) ?? 'fut').toLowerCase();
    final depTag = deporte == 'nba' ? 'NBA' : (deporte == 'tenis' ? 'TEN' : 'FUT');
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 8),
      decoration: BoxDecoration(
        border: Border(
          top: first ? BorderSide.none : const BorderSide(color: QfColors.divider),
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
            decoration: BoxDecoration(
              color: QfColors.surface2,
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              depTag,
              style: const TextStyle(
                fontFamily: qfMono,
                fontSize: 10,
                fontWeight: FontWeight.w700,
                color: QfColors.muted,
              ),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${leg['local'] ?? '—'} · ${leg['visitante'] ?? '—'}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: QfColors.text,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  pickText(leg),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontFamily: qfDisplay,
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    color: QfColors.cyan,
                  ),
                ),
                if (leg['marcador'] != null || leg['kickoff_utc'] != null) ...[
                  const SizedBox(height: 2),
                  liveText(
                    leg['marcador'] != null
                        ? context.l10n.parleyResultScore(leg['marcador'])
                        : kickoffText(leg['kickoff_utc']),
                    size: 10,
                    color: liveMuted,
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(width: 8),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '@${decimalText(leg['price'])}',
                style: const TextStyle(
                  fontFamily: qfMono,
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  color: QfColors.yellow,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                realPercent(leg['prob']),
                style: const TextStyle(
                  fontFamily: qfMono,
                  fontSize: 11,
                  color: QfColors.muted,
                ),
              ),
            ],
          ),
          if (settled) ...[
            const SizedBox(width: 6),
            Icon(
              outcome == 'win' || outcome == 'ganado'
                  ? Icons.check_circle
                  : (outcome == 'loss' || outcome == 'perdido'
                      ? Icons.cancel_outlined
                      : Icons.remove_circle_outline),
              size: 16,
              color: color,
            ),
          ],
        ],
      ),
    );
  }
}

/// Los últimos [max] parlays de los días anteriores (más recientes primero); el
/// día en que se llega al tope se recorta para no pasarse.
List<JsonMap> _lastParleys(Iterable<JsonMap> days, int max) {
  final out = <JsonMap>[];
  var left = max;
  for (final day in days) {
    if (left <= 0) break;
    final tickets = [
      for (final t in (day['tickets'] as List? ?? const [])) jsonMap(t),
    ];
    if (tickets.isEmpty) continue;
    out.add({...day, 'tickets': tickets.take(left).toList()});
    left -= tickets.length;
  }
  return out;
}

class _PastDay extends StatelessWidget {
  const _PastDay({required this.day});
  final JsonMap day;

  @override
  Widget build(BuildContext context) {
    final tickets = [
      for (final t in (day['tickets'] as List? ?? const [])) jsonMap(t),
    ];
    final won = tickets.where((t) => t['outcome'] == 'ganado').length;
    final settled = tickets.where((t) => t['outcome'] != null).length;
    return liveCard(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      child: Row(
        children: [
          Expanded(
            child: liveText(
              switch (dateValue(day['dia'])) {
                final DateTime date =>
                  toBeginningOfSentenceCase(localDate(DateFormat.yMMMEd, date)),
                null => '${day['dia'] ?? '—'}',
              },
              size: 13,
              bold: true,
            ),
          ),
          liveText(
            '${context.l10n.parleyDayCount(tickets.length)}${settled == 0 ? '' : ' · ${context.l10n.parleyDaySettled(won, settled)}'}',
            size: 11,
            color: liveMuted,
          ),
        ],
      ),
    );
  }
}
