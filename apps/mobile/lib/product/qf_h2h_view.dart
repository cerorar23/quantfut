import 'package:flutter/material.dart';
import '../l10n/app_locale.dart';
import 'package:gobet/product/qf_charts.dart';
import 'package:gobet/product/qf_theme.dart';
import 'package:gobet/product/sport_images.dart';

/// Elemento del resumen superior de H2H CyberCore (tarjeta de victorias/empates).
class QfH2hSummaryItem {
  const QfH2hSummaryItem({
    required this.label,
    required this.count,
    this.imageUrl,
    this.isCircle = false,
    this.isDraw = false,
  });

  final String label;
  final int count;
  final String? imageUrl;
  final bool isCircle;
  final bool isDraw;
}

/// Fila individual de partido en la lista de enfrentamientos CyberCore.
class QfH2hMatchItem {
  const QfH2hMatchItem({
    required this.date,
    required this.text,
    this.winnerBadge,
    this.winnerImageUrl,
    this.winnerName,
    this.isCircle = false,
    this.leftImageUrl,
    this.leftName,
    this.rightImageUrl,
    this.rightName,
  });

  final String date;
  final String text;
  final String? winnerBadge;
  final String? winnerImageUrl;
  final String? winnerName;
  final bool isCircle;
  final String? leftImageUrl;
  final String? leftName;
  final String? rightImageUrl;
  final String? rightName;
}

/// Vista común CyberCore para la pestaña H2H (fútbol, NBA y tenis).
///
/// Presenta:
/// 1. Resumen con imagen y número grande (2 o 3 tarjetas).
/// 2. Barra apilada proporcional [QfStackedBar].
/// 3. Cabecera «ÚLTIMOS ENFRENTAMIENTOS».
/// 4. Lista con partidos, marcador y estado «primer duelo» (0–0).
class QfH2hView extends StatelessWidget {
  const QfH2hView({
    super.key,
    required this.summary,
    this.stackedBarParts = const [],
    required this.matches,
  });

  final List<QfH2hSummaryItem> summary;
  final List<(String label, double value, Color color)> stackedBarParts;
  final List<QfH2hMatchItem> matches;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // 1. Resumen superior
        Row(
          children: [
            for (var i = 0; i < summary.length; i++) ...[
              if (i > 0) const SizedBox(width: 8),
              Expanded(
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    vertical: 10,
                    horizontal: 8,
                  ),
                  decoration: BoxDecoration(
                    border: Border.all(color: QfColors.border),
                    color: QfColors.surface,
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (summary[i].isDraw)
                        Container(
                          width: 44,
                          height: 44,
                          margin: const EdgeInsets.only(bottom: 6),
                          alignment: Alignment.center,
                          child: const Text(
                            'X',
                            style: TextStyle(
                              fontFamily: qfDisplay,
                              fontSize: 22,
                              fontWeight: FontWeight.w700,
                              color: QfColors.slate,
                            ),
                          ),
                        )
                      else
                        Padding(
                          padding: const EdgeInsets.only(bottom: 6),
                          child: QfAvatar(
                            url: summary[i].imageUrl,
                            name: summary[i].label,
                            size: 44,
                            shape: summary[i].isCircle
                                ? AvatarShape.circle
                                : AvatarShape.contain,
                          ),
                        ),
                      Text(
                        '${summary[i].count}',
                        style: const TextStyle(
                          fontFamily: qfMono,
                          fontSize: 26,
                          fontWeight: FontWeight.w700,
                          height: 1.1,
                          color: QfColors.cyan,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        summary[i].label.toUpperCase(),
                        style: const TextStyle(
                          fontFamily: qfDisplay,
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 1.4,
                          color: QfColors.slate,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ],
        ),

        // 2. QfStackedBar
        if (stackedBarParts.isNotEmpty) ...[
          const SizedBox(height: 12),
          QfStackedBar(height: 8, parts: stackedBarParts),
        ],

        // 3. Título de sección
        const SizedBox(height: 12),
        Text(
          l10n.h2hRecentMatches,
          style: const TextStyle(
            fontFamily: qfDisplay,
            fontSize: 13,
            fontWeight: FontWeight.w700,
            letterSpacing: 1.4,
            color: QfColors.text,
          ),
        ),
        const SizedBox(height: 8),

        // 4. Lista de enfrentamientos
        Container(
          decoration: BoxDecoration(
            border: Border.all(color: QfColors.border),
            color: QfColors.surface,
          ),
          child: Column(
            children: [
              for (var i = 0; i < matches.length; i++) ...[
                if (i > 0) const Divider(height: 1, color: QfColors.divider),
                _buildMatchRow(matches[i]),
              ],
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildMatchRow(QfH2hMatchItem match) {
    return Container(
      constraints: const BoxConstraints(minHeight: 48),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: Row(
        children: [
          // Fecha
          SizedBox(
            width: 64,
            child: Text(
              match.date,
              style: const TextStyle(
                fontFamily: qfMono,
                fontSize: 11,
                fontWeight: FontWeight.w500,
                color: QfColors.slate,
              ),
            ),
          ),
          const SizedBox(width: 8),

          // Imagen local opcional
          if (match.leftImageUrl != null || match.leftName != null) ...[
            QfAvatar(
              url: match.leftImageUrl,
              name: match.leftName ?? '',
              size: 20,
              shape: match.isCircle ? AvatarShape.circle : AvatarShape.contain,
            ),
            const SizedBox(width: 6),
          ],

          // Marcador / Enfrentamiento
          Expanded(
            child: Text(
              match.text,
              style: const TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: QfColors.text,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ),

          // Imagen visitante opcional
          if (match.rightImageUrl != null || match.rightName != null) ...[
            const SizedBox(width: 6),
            QfAvatar(
              url: match.rightImageUrl,
              name: match.rightName ?? '',
              size: 20,
              shape: match.isCircle ? AvatarShape.circle : AvatarShape.contain,
            ),
          ],

          // Insignia e imagen ganadora
          if (match.winnerImageUrl != null ||
              match.winnerBadge != null ||
              (match.winnerName != null && match.winnerName!.isNotEmpty)) ...[
            const SizedBox(width: 8),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (match.winnerImageUrl != null ||
                    (match.winnerName != null &&
                        match.winnerName!.isNotEmpty)) ...[
                  QfAvatar(
                    url: match.winnerImageUrl,
                    name: match.winnerName ?? '',
                    size: 28,
                    shape: match.isCircle
                        ? AvatarShape.circle
                        : AvatarShape.contain,
                  ),
                  const SizedBox(width: 6),
                ],
                if (match.winnerBadge != null &&
                    match.winnerBadge!.isNotEmpty) ...[
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 2,
                    ),
                    decoration: BoxDecoration(
                      border: Border.all(color: QfColors.border),
                    ),
                    child: Text(
                      match.winnerBadge!,
                      style: const TextStyle(
                        fontFamily: qfMono,
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        color: QfColors.cyan,
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ],
        ],
      ),
    );
  }
}
