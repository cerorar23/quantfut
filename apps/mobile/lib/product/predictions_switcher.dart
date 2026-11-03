import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import 'qf_theme.dart';

/// Menú de las tres secciones de Predicciones: píldora con un indicador que se desliza,
/// icono y texto por segmento, y un contador opcional. Alto cómodo para el pulgar.
class PredictionsSwitcher extends StatelessWidget {
  const PredictionsSwitcher({
    super.key,
    required this.value,
    required this.onChanged,
    required this.streams,
    this.badges = const {},
  });

  /// Orden canónico de las secciones; cada deporte ofrece un subconjunto.
  static const order = ['high', 'ladder', 'parley'];

  /// Secciones visibles, en orden; también el del deslizamiento (las ausentes no se pintan).
  final List<String> streams;

  final String value;
  final ValueChanged<String> onChanged;

  /// Contador por sección (solo se pinta si es mayor que cero).
  final Map<String, int> badges;

  /// Sección a la que lleva un deslizamiento horizontal, o la misma si fue corto o no hay más.
  /// Deslizar hacia la izquierda (velocidad negativa) avanza; hacia la derecha retrocede.
  static String swipe(
    String current,
    double velocity,
    List<String> streams, {
    double minVelocity = 300,
  }) {
    if (velocity.abs() < minVelocity) return current;
    final index = streams.indexOf(current);
    if (index < 0) return current;
    final next = (index + (velocity < 0 ? 1 : -1)).clamp(0, streams.length - 1);
    return streams[next];
  }

  static const _gap = 4.0;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final still = MediaQuery.of(context).disableAnimations;
    final all = <(String, IconData, String)>[
      ('high', Icons.track_changes, l10n.streamHighProb),
      ('ladder', Icons.stairs_outlined, l10n.streamLadder),
      ('parley', Icons.confirmation_number_outlined, l10n.streamParley),
    ];
    final items = [for (final item in all) if (streams.contains(item.$1)) item];
    final count = items.length;
    final selected = items.indexWhere((i) => i.$1 == value).clamp(0, count - 1);
    return Container(
      key: const ValueKey('streams-switcher'),
      height: 68,
      padding: const EdgeInsets.all(_gap),
      decoration: BoxDecoration(
        color: QfColors.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: QfColors.border),
      ),
      child: LayoutBuilder(
        builder: (context, box) {
          final width = (box.maxWidth - _gap * (count - 1)) / count;
          return Stack(
            children: [
              AnimatedPositioned(
                duration: still ? Duration.zero : const Duration(milliseconds: 260),
                curve: Curves.easeOutCubic,
                left: selected * (width + _gap),
                top: 0,
                bottom: 0,
                width: width,
                child: Container(
                  key: const ValueKey('streams-indicator'),
                  decoration: BoxDecoration(
                    color: QfColors.primary,
                    borderRadius: BorderRadius.circular(16),
                  ),
                ),
              ),
              Row(
                children: [
                  for (final (i, item) in items.indexed) ...[
                    if (i > 0) const SizedBox(width: _gap),
                    Expanded(
                      child: _Segment(
                        key: ValueKey('streams-${item.$1}'),
                        icon: item.$2,
                        label: item.$3,
                        selected: item.$1 == value,
                        badge: badges[item.$1] ?? 0,
                        onTap: () => onChanged(item.$1),
                      ),
                    ),
                  ],
                ],
              ),
            ],
          );
        },
      ),
    );
  }
}

class _Segment extends StatelessWidget {
  const _Segment({
    super.key,
    required this.icon,
    required this.label,
    required this.selected,
    required this.badge,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final bool selected;
  final int badge;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final color = selected ? QfColors.onPrimary : QfColors.muted;
    return Semantics(
      button: true,
      selected: selected,
      label: badge > 0 ? '$label, $badge' : label,
      child: ExcludeSemantics(
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(icon, size: 20, color: color),
                const SizedBox(height: 3),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Flexible(
                      child: FittedBox(
                        fit: BoxFit.scaleDown,
                        child: Text(
                          label,
                          maxLines: 1,
                          style: TextStyle(
                            color: color,
                            fontFamily: selected ? 'Gilroy Bold' : 'Gilroy Medium',
                            fontSize: 12,
                          ),
                        ),
                      ),
                    ),
                    if (badge > 0) ...[
                      const SizedBox(width: 4),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                        decoration: BoxDecoration(
                          color: selected ? QfColors.onPrimary : QfColors.success,
                          borderRadius: BorderRadius.circular(99),
                        ),
                        child: Text(
                          '$badge',
                          style: TextStyle(
                            color: selected ? QfColors.primary : QfColors.onPrimary,
                            fontFamily: 'Gilroy Bold',
                            fontSize: 10,
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
