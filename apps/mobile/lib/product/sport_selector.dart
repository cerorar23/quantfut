import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';
import 'sports.dart';

/// Fila de chips de deporte: icono + texto, 44 dp, esquina cortada y acento del deporte
/// en el activo. Con más de 4 deportes se desplaza y el último chip dice «Más».
class SportSelector extends StatelessWidget {
  const SportSelector({
    super.key,
    required this.sports,
    required this.value,
    required this.onChanged,
    this.counts = const {},
  });

  final List<SportKind> sports;
  final SportKind value;
  final ValueChanged<SportKind> onChanged;

  /// Contador por deporte (solo se pinta si es mayor que cero).
  final Map<SportKind, int> counts;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final scrolls = sports.length > 4;
    final chips = <Widget>[
      for (final sport in sports)
        _Chip(
          key: ValueKey('sport-${sport.id}'),
          icon: sportSpecs[sport]!.icon,
          label: sportSpecs[sport]!.label(l10n),
          accent: sportSpecs[sport]!.accent,
          selected: sport == value,
          count: counts[sport] ?? 0,
          onTap: () => onChanged(sport),
        ),
      if (scrolls)
        _Chip(
          key: const ValueKey('sport-more'),
          icon: Icons.more_horiz,
          label: l10n.sportMore,
          accent: QfColors.muted,
          selected: false,
          count: 0,
          onTap: () {},
        ),
    ];
    return Semantics(
      container: true,
      label: l10n.sportSelectorLabel,
      child: SizedBox(
        height: 44,
        child: scrolls
            ? ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: chips.length,
                separatorBuilder: (_, _) => const SizedBox(width: 8),
                itemBuilder: (_, i) => chips[i],
              )
            : Row(
                children: [
                  for (final (i, chip) in chips.indexed) ...[
                    if (i > 0) const SizedBox(width: 8),
                    Expanded(child: chip),
                  ],
                ],
              ),
      ),
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({
    super.key,
    required this.icon,
    required this.label,
    required this.accent,
    required this.selected,
    required this.count,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final Color accent;
  final bool selected;
  final int count;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final color = selected ? accent : QfColors.text2;
    return Semantics(
      button: true,
      selected: selected,
      label: count > 0 ? '$label, $count' : label,
      child: ExcludeSemantics(
        child: Material(
          color: selected ? accent.withValues(alpha: 0.14) : QfColors.surface,
          shape: CutCornerBorder(
            cut: 8,
            side: BorderSide(color: selected ? accent : QfColors.border),
          ),
          child: InkWell(
            customBorder: const CutCornerBorder(cut: 8),
            onTap: onTap,
            child: ConstrainedBox(
              constraints: const BoxConstraints(minHeight: 44, minWidth: 44),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(icon, size: 18, color: color),
                    const SizedBox(width: 6),
                    Flexible(
                      child: Text(
                        label.toUpperCase(),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          color: color,
                          fontFamily: qfDisplay,
                          fontWeight: FontWeight.w700,
                          fontSize: 14,
                          letterSpacing: 0.6,
                        ),
                      ),
                    ),
                    if (count > 0) ...[
                      const SizedBox(width: 6),
                      Text(
                        '$count',
                        style: TextStyle(
                          color: color,
                          fontFamily: qfMono,
                          fontSize: 11,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
