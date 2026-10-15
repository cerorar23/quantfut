import '../core/meta_events.dart';
import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import 'live_widgets.dart';

/// Guía de pronósticos: seis temas cortos para leer probabilidades, cuotas y retos sin
/// promesas de ganancia. Todo el texto sale de las traducciones.
class GuideScreen extends StatelessWidget {
  const GuideScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final topics = [
      (l10n.guideTopic1, l10n.guideHead1, l10n.guideBody1),
      (l10n.guideTopic2, l10n.guideHead2, l10n.guideBody2),
      (l10n.guideTopic3, l10n.guideHead3, l10n.guideBody3),
      (l10n.guideTopic4, l10n.guideHead4, l10n.guideBody4),
      (l10n.guideTopic5, l10n.guideHead5, l10n.guideBody5),
      (l10n.guideTopic6, l10n.guideHead6, l10n.guideBody6),
    ];
    return Scaffold(
      backgroundColor: liveBg,
      appBar: AppBar(backgroundColor: liveBg),
      body: NotificationListener<ScrollEndNotification>(
        onNotification: (n) {
          if (n.metrics.extentAfter == 0) MetaEvents.current?.completeTutorial();
          return false;
        },
        child: ListView(
        key: const ValueKey('guide-list'),
        padding: const EdgeInsets.fromLTRB(20, 4, 20, 32),
        children: [
          Text(
            l10n.guideTitle,
            style: const TextStyle(
              color: Colors.white,
              fontFamily: 'Gilroy ExtraBold',
              fontSize: 28,
              height: 1.1,
            ),
          ),
          const SizedBox(height: 8),
          liveText(l10n.guideSubtitle, color: liveMuted),
          for (final (i, (topic, head, body)) in topics.indexed) ...[
            const SizedBox(height: 18),
            const Divider(color: Colors.white12, height: 1),
            const SizedBox(height: 18),
            Row(
              children: [
                Container(
                  width: 26,
                  height: 26,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: liveGreen.withValues(alpha: .16),
                    shape: BoxShape.circle,
                  ),
                  child: Text(
                    '${i + 1}',
                    style: const TextStyle(
                      color: liveGreen,
                      fontFamily: 'Gilroy Bold',
                      fontSize: 13,
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    topic,
                    style: const TextStyle(
                      color: liveGreen,
                      fontFamily: 'Gilroy Bold',
                      fontSize: 12,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              head,
              style: const TextStyle(
                color: Colors.white,
                fontFamily: 'Gilroy Bold',
                fontSize: 17,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              body,
              style: const TextStyle(
                color: liveMuted,
                fontSize: 14,
                height: 1.45,
              ),
            ),
          ],
        ],
      ),
      ),
    );
  }
}
