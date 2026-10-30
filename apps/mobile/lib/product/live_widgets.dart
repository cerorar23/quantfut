import 'dart:ui' as ui;

import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import '../l10n/pick_labels.dart';
import 'live_api.dart';
import 'qf_theme.dart';
import 'sport_images.dart';

const liveBg = QfColors.bg,
    livePanel = QfColors.surface,
    liveCyan = QfColors.primary,
    liveGold = QfColors.cta,
    liveGreen = QfColors.success,
    liveMuted = QfColors.text2;
ThemeData liveTheme() => qfTheme();
Widget liveText(
  String text, {
  double size = 14,
  Color color = Colors.white,
  bool bold = false,
}) => Text(
  text,
  style: TextStyle(
    fontSize: size,
    color: color,
    fontWeight: bold ? FontWeight.w700 : FontWeight.w400,
  ),
);
Widget liveCard({
  required Widget child,
  Color? border,
  EdgeInsets padding = const EdgeInsets.all(16),
}) => Container(
  margin: const EdgeInsets.only(bottom: 12),
  decoration: BoxDecoration(
    color: livePanel,
    borderRadius: BorderRadius.circular(16),
    border: border == null ? null : Border.all(color: border),
  ),
  child: Material(
    color: Colors.transparent,
    borderRadius: BorderRadius.circular(16),
    child: Padding(padding: padding, child: child),
  ),
);
Widget liveHeading(String text) => Padding(
  padding: const EdgeInsets.symmetric(vertical: 14),
  child: liveText(text, size: 19, bold: true),
);
Widget training(String message) => liveCard(
  child: Row(
    children: [
      const Icon(Icons.science_outlined, color: liveGold),
      const SizedBox(width: 12),
      Expanded(child: liveText(message, color: liveMuted)),
    ],
  ),
);
Widget liveButton(
  String text,
  VoidCallback? action, {
  Color color = liveGold,
}) => SizedBox(
  width: double.infinity,
  child: FilledButton(
    style: FilledButton.styleFrom(
      backgroundColor: color,
      foregroundColor: liveBg,
      padding: const EdgeInsets.all(14),
    ),
    onPressed: action,
    child: Text(text, style: const TextStyle(fontWeight: FontWeight.bold)),
  ),
);
void liveNotice(BuildContext context, String message) =>
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(message)));

class TeamCrest extends StatelessWidget {
  const TeamCrest({
    super.key,
    required this.team,
    required this.api,
    this.size = 26,
  });
  final JsonMap team;
  final QuantFutApi api;
  final double size;
  @override
  Widget build(BuildContext context) {
    final url = team['escudo'];
    return QfAvatar(
      url: url is String && url.isNotEmpty
          ? api.base.resolve(url).toString()
          : null,
      name: '${team['name'] ?? team['nombre'] ?? ''}',
      size: size,
    );
  }
}

class RealPickCard extends StatelessWidget {
  const RealPickCard({
    super.key,
    required this.pick,
    required this.onOpen,
    required this.onVip,
    this.onUnlock,
    this.cost,
  });
  final JsonMap pick;
  final VoidCallback onOpen, onVip;
  final VoidCallback? onUnlock;
  final int? cost;
  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final locked = pick['locked'] == true;
    return liveCard(
      border: locked
          ? liveGold.withValues(alpha: .4)
          : liveGreen.withValues(alpha: .3),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                locked ? Icons.lock_outline : Icons.verified_outlined,
                color: locked ? liveGold : liveGreen,
                size: 18,
              ),
              const SizedBox(width: 7),
              liveText(
                locked
                    ? 'VIP'
                    : pick['free'] == true
                    ? l10n.forecastFree
                    : l10n.forecastUnlocked,
                color: locked ? liveGold : liveGreen,
                size: 11,
                bold: true,
              ),
              const Spacer(),
              Flexible(
                child: liveText(
                  kickoffText(pick['kickoff_utc']),
                  size: 11,
                  color: liveMuted,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          InkWell(
            onTap: onOpen,
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: liveText(
                '${pick['local'] ?? ''} · ${pick['visitante'] ?? ''}',
                bold: true,
                size: 16,
              ),
            ),
          ),
          if (!locked) ...[
            const SizedBox(height: 8),
            liveText(pickText(pick), color: liveGreen, bold: true),
            const SizedBox(height: 10),
            Row(
              children: [
                liveText(
                  l10n.pickProbability(realPercent(pick['prob'])),
                  color: liveCyan,
                  bold: true,
                ),
                const Spacer(),
                liveText(
                  '@ ${decimalText(pick['ref_price'] ?? pick['price'])}',
                  color: liveGold,
                  bold: true,
                ),
              ],
            ),
            const SizedBox(height: 5),
            liveText(
              l10n.pickOddsAtPublish(
                (pick['ref_book'] ?? pick['book']) == null
                    ? l10n.pickSourceNA
                    : bookName(pick['ref_book'] ?? pick['book']),
              ),
              size: 11,
              color: liveMuted,
            ),
            if (pick['odds_as_of'] != null)
              liveText(
                kickoffText(pick['odds_as_of']),
                size: 11,
                color: liveMuted,
              ),
            const SizedBox(height: 12),
            liveButton(l10n.pickSeeAnalysis, onOpen, color: liveCyan),
          ] else ...[
            const SizedBox(height: 8),
            const LockedBlur(),
            const SizedBox(height: 6),
            liveText(l10n.pickUnlockPrompt, color: liveMuted, size: 12),
            const SizedBox(height: 12),
            liveButton(l10n.vipAccessButton, onVip),
            if (onUnlock != null) ...[
              const SizedBox(height: 6),
              liveButton(
                l10n.pickUnlockCoins(cost ?? '—'),
                onUnlock,
                color: liveCyan,
              ),
            ],
          ],
        ],
      ),
    );
  }
}

Widget probabilityBars(JsonMap values) => Builder(
  builder: (context) => Column(
    children: ['home', 'draw', 'away'].map((key) {
      final l10n = context.l10n;
      final value = values[key];
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(
          children: [
            SizedBox(
              width: 38,
              child: liveText(
                key == 'home'
                    ? l10n.probBarHome
                    : key == 'draw'
                    ? l10n.probBarDraw
                    : l10n.probBarAway,
                size: 10,
                color: liveMuted,
              ),
            ),
            Expanded(
              child: LinearProgressIndicator(
                value: value is num ? value.toDouble().clamp(0, 1) : 0,
                color: key == 'home'
                    ? liveGreen
                    : key == 'away'
                    ? liveCyan
                    : liveMuted,
                backgroundColor: Colors.white12,
                minHeight: 4,
              ),
            ),
            const SizedBox(width: 8),
            liveText(realPercent(value), size: 11),
          ],
        ),
      );
    }).toList(),
  ),
);

/// Franja difuminada donde iría el pronóstico de un candado. Son bloques, no un texto real: el servidor no envía
/// la selección ni la probabilidad de un pronóstico bloqueado, así que quitar el filtro no revela nada.
class LockedBlur extends StatelessWidget {
  const LockedBlur({
    super.key,
    this.text = '████████ · ██ %',
    this.size = 13,
    this.blurKey = const ValueKey('locked-blur'),
  });

  final String text;
  final double size;
  final Key blurKey;

  @override
  Widget build(BuildContext context) {
    return ExcludeSemantics(
      child: ClipRect(
        child: ImageFiltered(
          key: blurKey,
          imageFilter: ui.ImageFilter.blur(sigmaX: 5, sigmaY: 5),
          child: liveText(text, size: size, bold: true, color: liveGold),
        ),
      ),
    );
  }
}
