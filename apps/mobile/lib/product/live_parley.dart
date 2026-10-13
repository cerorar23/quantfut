import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import 'live_api.dart';
import 'live_widgets.dart';

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
    final total = jsonMap(jsonMap(d['resumen'])['total']);
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
        if (days.length > 1) ...[
          liveHeading(l10n.parleyPastDays),
          for (final day in days.skip(1).take(7)) _PastDay(day: day),
        ],
        if ((total['n'] as num? ?? 0) > 0)
          _Summary(total: total)
        else if (days.isEmpty)
          _NoHistory(message: l10n.parleyNoHistory),
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
    decoration: BoxDecoration(
      color: const Color(0xff0f1a28),
      borderRadius: BorderRadius.circular(16),
      border: Border.all(color: Colors.white12),
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
        decoration: BoxDecoration(
          color: const Color(0xff0c131c),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white12),
        ),
        child: Row(
          children: [
            _TicketCard._chip(
              context.l10n.parleyStep(ticket['escalon'] ?? '—'),
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
/// abajo, las patas en una línea de tiempo. Las muescas y la línea punteada separan ambas partes.
class _TicketCard extends StatelessWidget {
  const _TicketCard({super.key, required this.ticket});
  final JsonMap ticket;

  @override
  Widget build(BuildContext context) {
    final legs = [
      for (final p in (ticket['patas'] as List? ?? const [])) jsonMap(p),
    ];
    final (color, label) = _outcome(ticket['outcome']);
    final prob = ticket['prob_total'];
    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      decoration: BoxDecoration(
        color: livePanel,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: color.withValues(alpha: .35)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Wrap(
                        spacing: 6,
                        runSpacing: 6,
                        children: [
                          _chip(
                            context.l10n.parleyStep(ticket['escalon'] ?? '—'),
                            liveCyan,
                          ),
                          _chip(label.toUpperCase(), color),
                        ],
                      ),
                      const SizedBox(height: 10),
                      liveText(
                        context.l10n.parleyJointProb(
                          realPercent(prob),
                          legs.length,
                        ),
                        size: 12,
                        color: liveMuted,
                      ),
                      const SizedBox(height: 6),
                      _Bar(value: prob is num ? prob.toDouble() : 0),
                    ],
                  ),
                ),
                const SizedBox(width: 14),
                Text(
                  '@${decimalText(ticket['cuota_total'])}',
                  style: const TextStyle(
                    fontSize: 28,
                    fontFamily: 'Gilroy ExtraBold',
                    color: liveGold,
                  ),
                ),
              ],
            ),
          ),
          const _TearLine(),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
            child: Column(
              children: [
                for (final (i, leg) in legs.indexed)
                  _Leg(leg: leg, first: i == 0, last: i == legs.length - 1),
              ],
            ),
          ),
        ],
      ),
    );
  }

  static Widget _chip(String text, Color color) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
    decoration: BoxDecoration(
      color: color.withValues(alpha: .15),
      borderRadius: BorderRadius.circular(8),
    ),
    child: Text(
      text,
      style: TextStyle(fontSize: 9, fontWeight: FontWeight.w800, color: color),
    ),
  );
}

class _Bar extends StatelessWidget {
  const _Bar({required this.value});
  final double value;

  @override
  Widget build(BuildContext context) => ClipRRect(
    borderRadius: BorderRadius.circular(3),
    child: Stack(
      children: [
        Container(height: 6, color: const Color(0xff243447)),
        FractionallySizedBox(
          widthFactor: value.clamp(0, 1).toDouble(),
          child: Container(height: 6, color: liveGold),
        ),
      ],
    ),
  );
}

/// Línea punteada con una muesca a cada lado, como el corte de un boleto.
class _TearLine extends StatelessWidget {
  const _TearLine();

  @override
  Widget build(BuildContext context) => SizedBox(
    height: 16,
    child: Stack(
      clipBehavior: Clip.none,
      children: [
        Positioned.fill(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14),
            child: LayoutBuilder(
              builder: (context, box) => Row(
                children: [
                  for (var i = 0; i < (box.maxWidth / 9).floor(); i++) ...[
                    Expanded(
                      child: Container(
                        height: 1.5,
                        color: const Color(0xff2f4258),
                      ),
                    ),
                    const SizedBox(width: 5),
                  ],
                ],
              ),
            ),
          ),
        ),
        for (final left in [true, false])
          Positioned(
            left: left ? -9 : null,
            right: left ? null : -9,
            top: 0,
            child: Container(
              width: 16,
              height: 16,
              decoration: const BoxDecoration(
                color: liveBg,
                shape: BoxShape.circle,
              ),
            ),
          ),
      ],
    ),
  );
}

/// Una pata del parley en la línea de tiempo: punto de estado, partido, pronóstico y cuota.
class _Leg extends StatelessWidget {
  const _Leg({required this.leg, required this.first, required this.last});
  final JsonMap leg;
  final bool first, last;

  @override
  Widget build(BuildContext context) {
    final (color, _) = _outcome(leg['outcome']);
    final outcome = leg['outcome'];
    final settled = outcome != null;
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            width: 20,
            child: Column(
              children: [
                Container(
                  width: 2,
                  height: 6,
                  color: first ? Colors.transparent : const Color(0xff243447),
                ),
                Container(
                  width: 12,
                  height: 12,
                  decoration: BoxDecoration(
                    color: settled ? color : Colors.transparent,
                    shape: BoxShape.circle,
                    border: Border.all(color: color, width: 2),
                  ),
                  child: settled
                      ? Icon(
                          outcome == 'win'
                              ? Icons.check
                              : outcome == 'loss'
                              ? Icons.close
                              : Icons.remove,
                          size: 8,
                          color: liveBg,
                        )
                      : null,
                ),
                Expanded(
                  child: Container(
                    width: 2,
                    color: last ? Colors.transparent : const Color(0xff243447),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Padding(
              padding: EdgeInsets.only(bottom: last ? 4 : 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '${leg['local'] ?? '—'} · ${leg['visitante'] ?? '—'}',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    '${leg['texto'] ?? '—'}',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      color: color == liveMuted ? Colors.white70 : liveGreen,
                    ),
                  ),
                  liveText(
                    leg['marcador'] != null
                        ? context.l10n.parleyResultScore(leg['marcador'])
                        : kickoffText(leg['kickoff_utc']),
                    size: 10,
                    color: liveMuted,
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(width: 8),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              const SizedBox(height: 4),
              liveText(
                '@${decimalText(leg['price'])}',
                size: 14,
                bold: true,
                color: liveGold,
              ),
              liveText(realPercent(leg['prob']), size: 10, color: liveMuted),
            ],
          ),
        ],
      ),
    );
  }
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
            child: liveText('${day['dia'] ?? '—'}', size: 13, bold: true),
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

class _Summary extends StatelessWidget {
  const _Summary({required this.total});
  final JsonMap total;

  @override
  Widget build(BuildContext context) {
    final real = total['acierto_real'];
    final promised = total['prob_media'];
    return liveCard(
      border: liveGold.withValues(alpha: .3),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          liveText(context.l10n.parleyHistoryTitle, bold: true, size: 15),
          const SizedBox(height: 8),
          liveText(
            context.l10n.parleySummary(
                  total['aciertos'] ?? 0,
                  total['n'] ?? 0,
                ) +
                (real is num
                    ? context.l10n.parleySummaryReal(decimalText(real, 1))
                    : '') +
                (promised is num
                    ? context.l10n.parleySummaryPromised(
                        decimalText(promised, 1),
                      )
                    : ''),
            size: 12,
            color: liveGreen,
            bold: true,
          ),
          const SizedBox(height: 6),
          liveText(context.l10n.parleyFewNote, size: 10, color: liveMuted),
        ],
      ),
    );
  }
}
