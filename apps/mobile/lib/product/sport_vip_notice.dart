import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';
import 'sports_feed.dart';

/// Avisos de lo que el cupo del deporte deja para VIP en un partido (menú `/control/cupos`): el destacado con
/// candado y cuántos mercados más hay. No enseña mercado, selección, probabilidad ni cuota. Vacío si no hay nada.
class SportVipNotice extends StatelessWidget {
  const SportVipNotice({super.key, required this.event, this.featured = true, this.markets = true, this.onVip});

  final SportEvent event;

  /// Qué avisos pinta: el del destacado, el del recuento de mercados o ambos.
  final bool featured, markets;
  final VoidCallback? onVip;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final lines = [
      if (featured && event.featuredVip) l10n.sportFeaturedVip,
      if (markets && event.vipCount > 0) l10n.sportVipMarkets(event.vipCount),
    ];
    if (lines.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Material(
        color: QfColors.yellow.withValues(alpha: .07),
        shape: CutCornerBorder(cut: 8, side: BorderSide(color: QfColors.yellow.withValues(alpha: .45))),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onVip,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            child: Row(
              children: [
                const Icon(Icons.lock_outline, size: 18, color: QfColors.yellow),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      for (final line in lines)
                        Text(
                          line,
                          style: const TextStyle(
                            fontFamily: qfDisplay,
                            fontWeight: FontWeight.w700,
                            fontSize: 13,
                            color: QfColors.text,
                          ),
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Etiqueta «VIP» con candado para la fila de un partido cuyo destacado no entra en el cupo del día.
class SportVipBadge extends StatelessWidget {
  const SportVipBadge({super.key});

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
    decoration: BoxDecoration(
      border: Border.all(color: QfColors.yellow.withValues(alpha: .45)),
      color: QfColors.yellow.withValues(alpha: .09),
    ),
    child: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        const Icon(Icons.lock_outline, size: 12, color: QfColors.yellow),
        const SizedBox(width: 4),
        Text(
          context.l10n.sportVipBadge,
          style: const TextStyle(fontFamily: qfMono, fontWeight: FontWeight.w700, fontSize: 12, color: QfColors.yellow),
        ),
      ],
    ),
  );
}
