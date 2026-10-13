import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
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
              '${step['local']} · ${step['visitante']}\n${step['texto']} · $outcome\n${step['marcador'] ?? ''}'
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
  bool _open = false;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final summary = jsonMap(widget.report['resumen']);
    final closed = (summary['cerrados'] as num?)?.toInt() ?? 0;
    final done = (summary['completados'] as num?)?.toInt() ?? 0;
    final rate = summary['tasa_completados'];
    final roi = summary['roi'];
    final rows = jsonRows(widget.report['historial']).take(10).toList();
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
                padding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
                child: Column(
                  children: [for (final r in rows) _HistoryRow(challenge: r)],
                ),
              ),
          ],
        ],
      ),
    );
  }
}

class _HistoryRow extends StatelessWidget {
  const _HistoryRow({required this.challenge});

  final JsonMap challenge;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final done = challenge['estado'] == 'completado';
    final goal = (challenge['pasos_objetivo'] as num?)?.toInt() ?? 0;
    final won = (challenge['ganados'] as num?)?.toInt() ?? 0;
    final detail = done
        ? '${l10n.ladderHistoryDone} · ${l10n.ladderWonOf(won, goal)}'
        : l10n.ladderHistoryFailedAt(won + 1);
    final multiplier = LadderProgress.multiplierOf(challenge);
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
            done ? Icons.check_circle : Icons.cancel_outlined,
            color: done ? liveGreen : liveMuted,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                liveText(
                  l10n.ladderTitle(challenge['reto_id'] ?? '—', goal),
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
        ],
      ),
    );
  }
}
