import 'package:flutter/material.dart';

import 'qf_shapes.dart';
import 'qf_theme.dart';

/// Datos de una fila en la tabla de clasificación (§4 y §5.9).
class QfStandingRow {
  const QfStandingRow({
    required this.position,
    required this.teamId,
    required this.teamName,
    this.crestUrl,
    required this.played,
    required this.diffGoals,
    required this.points,
    this.form = '',
    this.zoneColor,
  });

  final int position;
  final String teamId;
  final String teamName;
  final String? crestUrl;
  final int played;
  final int diffGoals;
  final int points;
  final String form; // Más reciente primero de la API, ej: "GEPEG" o "WDDWD"
  final Color? zoneColor;
}

/// Mini tabla de clasificación CyberCore con zonas laterales, forma en 5 barritas y filas destacadas.
class QfStandingsTable extends StatelessWidget {
  const QfStandingsTable({
    super.key,
    required this.rows,
    this.highlightIds = const {},
    this.calloutText,
  });

  final List<QfStandingRow> rows;
  final Set<String> highlightIds;
  final String? calloutText;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (calloutText != null && calloutText!.isNotEmpty) ...[
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: ShapeDecoration(
              color: QfColors.cyan.withValues(alpha: .08),
              shape: CutCornerBorder(
                cut: 6,
                side: BorderSide(color: QfColors.cyan.withValues(alpha: .3)),
              ),
            ),
            child: Row(
              children: [
                const Icon(Icons.info_outline, size: 16, color: QfColors.cyan),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    calloutText!,
                    style: const TextStyle(
                      fontFamily: qfBody,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: QfColors.text,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 10),
        ],
        // Cabecera de tabla
        const Padding(
          padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          child: Row(
            children: [
              SizedBox(
                width: 28,
                child: Text(
                  'POS',
                  style: TextStyle(
                    fontFamily: qfDisplay,
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    color: QfColors.muted,
                  ),
                ),
              ),
              Expanded(
                child: Text(
                  'EQUIPO',
                  style: TextStyle(
                    fontFamily: qfDisplay,
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    color: QfColors.muted,
                  ),
                ),
              ),
              SizedBox(
                width: 24,
                child: Text(
                  'PJ',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontFamily: qfDisplay,
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    color: QfColors.muted,
                  ),
                ),
              ),
              SizedBox(
                width: 28,
                child: Text(
                  'DG',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontFamily: qfDisplay,
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    color: QfColors.muted,
                  ),
                ),
              ),
              SizedBox(
                width: 32,
                child: Text(
                  'PTS',
                  textAlign: TextAlign.right,
                  style: TextStyle(
                    fontFamily: qfDisplay,
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    color: QfColors.muted,
                  ),
                ),
              ),
              SizedBox(width: 6),
              SizedBox(
                width: 44,
                child: Text(
                  'FORMA',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontFamily: qfDisplay,
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    color: QfColors.muted,
                  ),
                ),
              ),
            ],
          ),
        ),
        const Divider(height: 1, thickness: 1, color: QfColors.surface2),
        // Filas
        for (var i = 0; i < rows.length; i++) ...[
          if (i > 0 && (rows[i].position - rows[i - 1].position > 1))
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 4),
              child: Center(
                child: Text(
                  '· · ·',
                  style: TextStyle(
                    fontFamily: qfMono,
                    fontSize: 12,
                    color: QfColors.muted,
                    letterSpacing: 2,
                  ),
                ),
              ),
            ),
          _StandingRowWidget(
            row: rows[i],
            isHighlighted: highlightIds.contains(rows[i].teamId),
          ),
        ],
      ],
    );
  }
}

class _StandingRowWidget extends StatelessWidget {
  const _StandingRowWidget({
    required this.row,
    required this.isHighlighted,
  });

  final QfStandingRow row;
  final bool isHighlighted;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 38,
      margin: const EdgeInsets.symmetric(vertical: 2),
      padding: const EdgeInsets.symmetric(horizontal: 8),
      decoration: BoxDecoration(
        color: isHighlighted ? QfColors.surface2 : Colors.transparent,
        border: isHighlighted
            ? Border(
                left: BorderSide(color: QfColors.cyan, width: 3),
              )
            : (row.zoneColor != null
                ? Border(
                    left: BorderSide(color: row.zoneColor!, width: 3),
                  )
                : null),
      ),
      child: Row(
        children: [
          SizedBox(
            width: 28,
            child: Text(
              '${row.position}',
              style: TextStyle(
                fontFamily: qfMono,
                fontSize: 12,
                fontWeight: isHighlighted ? FontWeight.w700 : FontWeight.w500,
                color: isHighlighted ? QfColors.cyan : QfColors.text2,
              ),
            ),
          ),
          Expanded(
            child: Text(
              row.teamName,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontFamily: qfBody,
                fontSize: 13,
                fontWeight: isHighlighted ? FontWeight.w700 : FontWeight.w500,
                color: isHighlighted ? QfColors.text : QfColors.text2,
              ),
            ),
          ),
          SizedBox(
            width: 24,
            child: Text(
              '${row.played}',
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontFamily: qfMono,
                fontSize: 11,
                color: QfColors.text2,
              ),
            ),
          ),
          SizedBox(
            width: 28,
            child: Text(
              '${row.diffGoals > 0 ? "+" : ""}${row.diffGoals}',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontFamily: qfMono,
                fontSize: 11,
                color: row.diffGoals > 0
                    ? QfColors.green
                    : (row.diffGoals < 0 ? QfColors.magenta : QfColors.muted),
              ),
            ),
          ),
          SizedBox(
            width: 32,
            child: Text(
              '${row.points}',
              textAlign: TextAlign.right,
              style: TextStyle(
                fontFamily: qfMono,
                fontSize: 13,
                fontWeight: FontWeight.w700,
                color: isHighlighted ? QfColors.cyan : QfColors.text,
              ),
            ),
          ),
          const SizedBox(width: 6),
          SizedBox(
            width: 44,
            child: _FormMiniBars(form: row.form),
          ),
        ],
      ),
    );
  }
}

class _FormMiniBars extends StatelessWidget {
  const _FormMiniBars({required this.form});
  final String form;

  @override
  Widget build(BuildContext context) {
    if (form.isEmpty) return const SizedBox.shrink();

    // La API entrega el más reciente PRIMERO ("WDDWD").
    // Para pintar de izquierda (antiguo) a derecha (reciente), invertimos:
    final chars = form.split('').reversed.toList();
    final displayChars = chars.length > 5 ? chars.sublist(chars.length - 5) : chars;

    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        for (final ch in displayChars) ...[
          Container(
            width: 5,
            height: 14,
            margin: const EdgeInsets.symmetric(horizontal: 1),
            decoration: BoxDecoration(
              color: _colorFor(ch),
              borderRadius: BorderRadius.circular(1.5),
            ),
          ),
        ],
      ],
    );
  }

  Color _colorFor(String ch) {
    final c = ch.toUpperCase();
    if (c == 'G' || c == 'W') return QfColors.green;
    if (c == 'E' || c == 'D') return QfColors.slate;
    return QfColors.magenta;
  }
}
