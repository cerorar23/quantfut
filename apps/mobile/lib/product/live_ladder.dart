import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import '../l10n/pick_labels.dart';
import 'ladder_progress.dart';
import 'live_api.dart';
import 'live_widgets.dart';

const _track = Color(0xff243447);
const _tile = Color(0xff0e1b2a);

String _multiplierText(double? value) =>
    value == null ? '—' : '×${decimalText(value, 2)}';

/// Tarjeta de un reto vivo: avance, qué falta, si sigue en marcha y su probabilidad estimada.
/// Los escalones ya liquidados quedan plegados; el que está por jugarse (`pending`) se ve siempre.
class LadderChallengeCard extends StatefulWidget {
  const LadderChallengeCard({
    super.key,
    required this.challenge,
    required this.pending,
    this.averageProbability,
  });

  final JsonMap challenge;

  /// Tarjetas de los escalones aún sin liquidar (el gratuito y los de candado).
  final List<Widget> pending;
  final double? averageProbability;

  @override
  State<LadderChallengeCard> createState() => _LadderChallengeCardState();
}

class _LadderChallengeCardState extends State<LadderChallengeCard> {
  bool _open = false;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final c = widget.challenge;
    final p = LadderProgress.of(
      c,
      averageProbability: widget.averageProbability,
    );
    final id = c['reto_id'] ?? '—';
    final inPlay = p.phase == LadderPhase.inPlay;
    final accent = inPlay ? liveGold : liveCyan;
    final settled = jsonRows(c['pasos']).where((s) => s['outcome'] != null);
    final average = percentText(
      (widget.averageProbability ?? LadderProgress.fallbackStepProbability) *
          100,
    );
    final title = l10n.ladderTitle(id, p.goal);
    final progress =
        '${l10n.ladderWonOf(p.won, p.goal)} · ${l10n.ladderRemaining(p.remaining)}';
    final status = inPlay ? l10n.ladderStatusInPlay : l10n.ladderStatusToPick;
    return Container(
      key: ValueKey('ladder-card-$id'),
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: livePanel,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: accent.withValues(alpha: .35)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Semantics(
            container: true,
            label:
                '$title. $progress. $status. ${realPercent(p.fraction)}',
            child: ExcludeSemantics(
              child: Row(
                children: [
                  _ProgressRing(fraction: p.fraction),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        liveText(title, size: 15, bold: true),
                        const SizedBox(height: 2),
                        liveText(progress, size: 12, color: liveMuted),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  _StatusChip(label: status, color: accent, inPlay: inPlay),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          _StepBar(goal: p.goal, won: p.won, inPlay: inPlay),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: _Tile(
                  key: ValueKey('ladder-chance-$id'),
                  value: p.chance == null ? '—' : '≈ ${realPercent(p.chance)}',
                  label: l10n.ladderChance,
                  onInfo: () =>
                      liveNotice(context, l10n.ladderEstimateNote(average)),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _Tile(
                  value: _multiplierText(p.multiplier),
                  label: l10n.ladderBalance,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(
                inPlay ? Icons.schedule : Icons.hourglass_empty,
                size: 16,
                color: liveMuted,
              ),
              const SizedBox(width: 6),
              Expanded(
                child: liveText(
                  inPlay ? l10n.ladderNoteInPlay : l10n.ladderNoteToPick,
                  size: 12,
                  color: liveMuted,
                ),
              ),
            ],
          ),
          if (widget.pending.isNotEmpty) ...[
            const SizedBox(height: 12),
            ...widget.pending,
          ],
          if (settled.isNotEmpty) ...[
            InkWell(
              key: ValueKey('ladder-toggle-$id'),
              borderRadius: BorderRadius.circular(10),
              onTap: () => setState(() => _open = !_open),
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 10),
                child: Row(
                  children: [
                    Expanded(
                      child: liveText(
                        _open ? l10n.ladderHideSteps : l10n.ladderShowSteps,
                        size: 13,
                        color: liveCyan,
                        bold: true,
                      ),
                    ),
                    Icon(
                      _open ? Icons.expand_less : Icons.expand_more,
                      color: liveCyan,
                    ),
                  ],
                ),
              ),
            ),
            if (_open) ...settled.map((s) => _SettledStep(step: s)),
          ],
        ],
      ),
    );
  }
}

/// Un escalón ya liquidado.
class _SettledStep extends StatelessWidget {
  const _SettledStep({required this.step});

  final JsonMap step;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final won = step['outcome'] == 'win';
    final outcome =
        {
          'win': l10n.outcomeWin,
          'loss': l10n.outcomeLoss,
          'push': l10n.outcomePush,
        }[step['outcome']] ??
        '${step['outcome']}';
    return Container(
      margin: const EdgeInsets.only(top: 6),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: _tile,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Icon(
            won ? Icons.check_circle : Icons.cancel_outlined,
            color: won ? liveGreen : liveMuted,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: liveText(
              '${step['local']} · ${step['visitante']}\n${pickText(step)} · $outcome\n${step['marcador'] ?? ''}'
                  .trim(),
              size: 12,
            ),
          ),
        ],
      ),
    );
  }
}

/// Anillo con el porcentaje de avance en el centro.
class _ProgressRing extends StatelessWidget {
  const _ProgressRing({required this.fraction});

  final double fraction;

  @override
  Widget build(BuildContext context) {
    final still = MediaQuery.of(context).disableAnimations;
    return TweenAnimationBuilder<double>(
      tween: Tween(end: fraction),
      duration: still ? Duration.zero : const Duration(milliseconds: 700),
      curve: Curves.easeOutCubic,
      builder: (context, value, _) => SizedBox.square(
        dimension: 58,
        child: CustomPaint(
          painter: _RingPainter(value),
          child: Center(
            child: Text(
              realPercent(fraction),
              style: const TextStyle(
                color: Colors.white,
                fontFamily: 'Gilroy Bold',
                fontSize: 13,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _RingPainter extends CustomPainter {
  const _RingPainter(this.value);

  final double value;

  @override
  void paint(Canvas canvas, Size size) {
    final rect = (Offset.zero & size).deflate(4);
    final base = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 6
      ..color = _track;
    canvas.drawArc(rect, 0, 2 * math.pi, false, base);
    if (value <= 0) return;
    canvas.drawArc(
      rect,
      -math.pi / 2,
      2 * math.pi * value.clamp(0, 1),
      false,
      base
        ..strokeCap = StrokeCap.round
        ..color = liveGreen,
    );
  }

  @override
  bool shouldRepaint(_RingPainter oldDelegate) => oldDelegate.value != value;
}

/// Un tramo por escalón: ganado en verde, el que se está jugando en ámbar y el resto vacío.
class _StepBar extends StatelessWidget {
  const _StepBar({
    required this.goal,
    required this.won,
    required this.inPlay,
  });

  final int goal;
  final int won;
  final bool inPlay;

  @override
  Widget build(BuildContext context) => Row(
    children: [
      for (var i = 0; i < goal; i++) ...[
        if (i > 0) const SizedBox(width: 4),
        Expanded(
          child: Container(
            key: ValueKey('ladder-step-$i'),
            height: 8,
            decoration: BoxDecoration(
              color: i < won
                  ? liveGreen
                  : (i == won && inPlay ? liveGold : _track),
              borderRadius: BorderRadius.circular(4),
            ),
          ),
        ),
      ],
    ],
  );
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({
    required this.label,
    required this.color,
    required this.inPlay,
  });

  final String label;
  final Color color;
  final bool inPlay;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
    decoration: BoxDecoration(
      color: color.withValues(alpha: .16),
      borderRadius: BorderRadius.circular(99),
    ),
    child: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(inPlay ? Icons.schedule : Icons.hourglass_empty, size: 13, color: color),
        const SizedBox(width: 4),
        Flexible(
          child: Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              color: color,
              fontFamily: 'Gilroy Bold',
              fontSize: 11,
            ),
          ),
        ),
      ],
    ),
  );
}

class _Tile extends StatelessWidget {
  const _Tile({super.key, required this.value, required this.label, this.onInfo});

  final String value;
  final String label;
  final VoidCallback? onInfo;

  @override
  Widget build(BuildContext context) {
    final body = Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: _tile,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                FittedBox(
                  fit: BoxFit.scaleDown,
                  alignment: Alignment.centerLeft,
                  child: liveText(value, size: 17, bold: true),
                ),
                const SizedBox(height: 2),
                liveText(label, size: 11, color: liveMuted),
              ],
            ),
          ),
          if (onInfo != null)
            const Icon(Icons.info_outline, size: 16, color: liveMuted),
        ],
      ),
    );
    if (onInfo == null) return body;
    return InkWell(
      borderRadius: BorderRadius.circular(10),
      onTap: onInfo,
      child: body,
    );
  }
}

/// Tarjeta pequeña con los retos ya cerrados (cumplidos y fallidos) y su tasa de éxito.
class LadderHistoryCard extends StatefulWidget {
  const LadderHistoryCard({super.key, required this.report});

  final JsonMap report;

  @override
  State<LadderHistoryCard> createState() => _LadderHistoryCardState();
}

class _LadderHistoryCardState extends State<LadderHistoryCard> {
  /// Qué se enseña (decisión del titular, 2026-10-14): los 9 últimos retos cumplidos y el
  /// último fallido, del más reciente al más antiguo. El resumen de arriba cuenta todos.
  static const _maxDone = 9;
  static const _maxFailed = 1;

  bool _open = false;

  /// Un solo reto desplegado a la vez, para no llenar la pantalla.
  Object? _expanded;

  List<JsonMap> _selection(List<JsonMap> all) {
    var done = 0, failed = 0;
    final out = <JsonMap>[];
    for (final r in all) {
      if (r['estado'] == 'completado') {
        if (done++ < _maxDone) out.add(r);
      } else if (failed++ < _maxFailed) {
        out.add(r);
      }
    }
    return out;
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final summary = jsonMap(widget.report['resumen']);
    final closed = (summary['cerrados'] as num?)?.toInt() ?? 0;
    final done = (summary['completados'] as num?)?.toInt() ?? 0;
    final rate = summary['tasa_completados'];
    final roi = summary['roi'];
    final rows = _selection(jsonRows(widget.report['historial']));
    final empty = closed == 0;
    return Container(
      key: const ValueKey('ladder-history'),
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: livePanel,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          InkWell(
            borderRadius: BorderRadius.circular(16),
            onTap: empty ? null : () => setState(() => _open = !_open),
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Row(
                children: [
                  const Icon(Icons.emoji_events_outlined, color: liveGold, size: 26),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        liveText(l10n.ladderHistoryTitle, size: 15, bold: true),
                        const SizedBox(height: 2),
                        liveText(
                          l10n.ladderHistorySummary(done, closed),
                          size: 12,
                          color: liveMuted,
                        ),
                      ],
                    ),
                  ),
                  if (!empty)
                    Icon(
                      _open ? Icons.expand_less : Icons.expand_more,
                      color: liveMuted,
                    ),
                ],
              ),
            ),
          ),
          if (empty)
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
              child: liveText(l10n.ladderHistoryEmpty, size: 12, color: liveMuted),
            )
          else ...[
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 0, 14, 12),
              child: Wrap(
                spacing: 16,
                runSpacing: 4,
                children: [
                  if (rate is num)
                    liveText(
                      l10n.ladderHistoryRate(percentText(rate)),
                      size: 12,
                      color: liveMuted,
                    ),
                  if (roi is num)
                    liveText(
                      l10n.ladderHistoryResult(
                        '${roi > 0 ? '+' : ''}${percentText(roi, 1)}',
                      ),
                      size: 12,
                      color: liveMuted,
                    ),
                ],
              ),
            ),
            if (_open)
              Padding(
                key: const ValueKey('ladder-history-list'),
                padding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    for (final r in rows)
                      _HistoryRow(
                        challenge: r,
                        expanded: _expanded == r['reto_id'],
                        onTap: () => setState(
                          () => _expanded = _expanded == r['reto_id']
                              ? null
                              : r['reto_id'],
                        ),
                      ),
                  ],
                ),
              ),
          ],
        ],
      ),
    );
  }
}

/// Un reto cerrado: una línea con su resultado; al tocarlo enseña sus escalones.
class _HistoryRow extends StatelessWidget {
  const _HistoryRow({
    required this.challenge,
    required this.expanded,
    required this.onTap,
  });

  final JsonMap challenge;
  final bool expanded;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final id = challenge['reto_id'] ?? '—';
    final done = challenge['estado'] == 'completado';
    final goal = (challenge['pasos_objetivo'] as num?)?.toInt() ?? 0;
    final won = (challenge['ganados'] as num?)?.toInt() ?? 0;
    final detail = done
        ? '${l10n.ladderHistoryDone} · ${l10n.ladderWonOf(won, goal)}'
        : challenge['estado'] == 'expirado'
            ? '${l10n.ladderHistoryExpired} · ${l10n.ladderWonOf(won, goal)}'
            : l10n.ladderHistoryFailedAt(won + 1);
    final multiplier = LadderProgress.multiplierOf(challenge);
    final steps = jsonRows(challenge['pasos']).toList()
      ..sort(
        (a, b) => ((a['paso'] as num?) ?? 0).compareTo((b['paso'] as num?) ?? 0),
      );
    return Container(
      key: ValueKey('ladder-history-row-$id'),
      margin: const EdgeInsets.only(top: 6),
      decoration: BoxDecoration(
        color: _tile,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        children: [
          InkWell(
            borderRadius: BorderRadius.circular(12),
            onTap: steps.isEmpty ? null : onTap,
            child: Padding(
              padding: const EdgeInsets.all(10),
              child: Row(
                children: [
                  Icon(
                    done ? Icons.check_circle : Icons.cancel_outlined,
                    color: done ? liveGreen : liveMuted,
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        liveText(
                          l10n.ladderTitle(id, goal),
                          size: 13,
                          bold: true,
                        ),
                        liveText(detail, size: 12, color: liveMuted),
                      ],
                    ),
                  ),
                  liveText(
                    _multiplierText(multiplier),
                    size: 14,
                    bold: true,
                    color: done ? liveGreen : liveMuted,
                  ),
                  if (steps.isNotEmpty)
                    Icon(
                      expanded ? Icons.expand_less : Icons.expand_more,
                      color: liveMuted,
                      size: 20,
                    ),
                ],
              ),
            ),
          ),
          if (expanded)
            Padding(
              padding: const EdgeInsets.fromLTRB(10, 0, 10, 6),
              child: Column(
                children: [
                  const Divider(height: 1, color: Colors.white12),
                  for (final s in steps) _ClosedStep(step: s),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

/// Un escalón de un reto cerrado: partido, qué se eligió, a qué cuota y cómo acabó.
class _ClosedStep extends StatelessWidget {
  const _ClosedStep({required this.step});

  final JsonMap step;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final outcome = step['outcome'];
    final won = outcome == 'win';
    final lost = outcome == 'loss';
    final price = step['price'];
    final score = step['marcador'];
    final detail = [
      pickText(step),
      if (price is num) l10n.homeTicketOdds(decimalText(price)),
      if (score != null) '$score',
      if (!won && !lost) l10n.outcomePush,
    ].join(' · ');
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            won
                ? Icons.check_circle
                : (lost ? Icons.cancel_outlined : Icons.remove_circle_outline),
            size: 18,
            color: won ? liveGreen : liveMuted,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                liveText(
                  '${step['local']} · ${step['visitante']}',
                  size: 12,
                  bold: true,
                ),
                liveText(detail, size: 12, color: liveMuted),
              ],
            ),
          ),
          if (step['kickoff_utc'] != null) ...[
            const SizedBox(width: 8),
            liveText(kickoffText(step['kickoff_utc']), size: 11, color: liveMuted),
          ],
        ],
      ),
    );
  }
}
