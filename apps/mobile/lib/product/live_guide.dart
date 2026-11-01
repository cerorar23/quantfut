import '../core/meta_events.dart';
import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import 'live_widgets.dart';
import 'qf_theme.dart';

/// Guía de pronósticos: seis temas cortos para leer probabilidades, cuotas y retos sin
/// promesas de ganancia, en acordeón (el primero abierto). Todo el texto sale de las
/// traducciones. El tutorial cuenta como completado al abrir el último tema o al llegar
/// al final de la lista.
class GuideScreen extends StatefulWidget {
  const GuideScreen({super.key});

  @override
  State<GuideScreen> createState() => _GuideScreenState();
}

class _GuideScreenState extends State<GuideScreen> {
  final open = <int>{0};
  bool completed = false;

  void complete() {
    if (completed) return;
    completed = true;
    MetaEvents.current?.completeTutorial();
  }

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
      backgroundColor: QfColors.bg,
      appBar: AppBar(backgroundColor: QfColors.bg, foregroundColor: QfColors.text),
      body: NotificationListener<ScrollEndNotification>(
        onNotification: (n) {
          if (n.metrics.extentAfter == 0) complete();
          return false;
        },
        child: ListView(
          key: const ValueKey('guide-list'),
          padding: const EdgeInsets.fromLTRB(16, 4, 16, 32),
          children: [
            Text(
              l10n.guideTitle,
              style: const TextStyle(
                color: QfColors.text,
                fontFamily: qfDisplay,
                fontWeight: FontWeight.w700,
                fontSize: 30,
                height: 1.1,
              ),
            ),
            const SizedBox(height: 8),
            liveText(l10n.guideSubtitle, color: QfColors.text2),
            const SizedBox(height: 12),
            for (final (i, (topic, head, body)) in topics.indexed)
              _Topic(
                key: ValueKey('guide-topic-$i'),
                number: i + 1,
                topic: topic,
                head: head,
                body: body,
                open: open.contains(i),
                onToggle: () {
                  setState(() => open.contains(i) ? open.remove(i) : open.add(i));
                  if (i == topics.length - 1 && open.contains(i)) complete();
                },
              ),
          ],
        ),
      ),
    );
  }
}

class _Topic extends StatelessWidget {
  const _Topic({
    super.key,
    required this.number,
    required this.topic,
    required this.head,
    required this.body,
    required this.open,
    required this.onToggle,
  });

  final int number;
  final String topic, head, body;
  final bool open;
  final VoidCallback onToggle;

  @override
  Widget build(BuildContext context) => Container(
    decoration: const BoxDecoration(
      border: Border(top: BorderSide(color: QfColors.border)),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Semantics(
          button: true,
          expanded: open,
          child: InkWell(
            onTap: onToggle,
            child: ConstrainedBox(
              constraints: const BoxConstraints(minHeight: 56),
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 10),
                child: Row(
                  children: [
                    Container(
                      width: 28,
                      height: 28,
                      alignment: Alignment.center,
                      color: QfColors.surface2,
                      child: Text(
                        '$number',
                        style: const TextStyle(fontFamily: qfMono, fontSize: 13, color: QfColors.primary),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            topic,
                            style: const TextStyle(
                              color: QfColors.primary,
                              fontFamily: qfDisplay,
                              fontWeight: FontWeight.w700,
                              fontSize: 12,
                              letterSpacing: .8,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            head,
                            style: const TextStyle(
                              color: QfColors.text,
                              fontFamily: 'Gilroy Bold',
                              fontSize: 16,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Icon(open ? Icons.expand_less : Icons.expand_more, color: QfColors.text2),
                  ],
                ),
              ),
            ),
          ),
        ),
        if (open)
          Padding(
            padding: const EdgeInsets.fromLTRB(38, 0, 0, 14),
            child: Text(
              body,
              style: const TextStyle(color: QfColors.text2, fontSize: 14, height: 1.45),
            ),
          ),
      ],
    ),
  );
}
