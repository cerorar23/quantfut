import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import '../l10n/pick_labels.dart';
import 'live_api.dart';
import 'live_widgets.dart';

// Los identificadores de categoría son los que envía el servidor (en español);
// no son texto visible: se traducen con `groupLabel`.
// l10n-ignore-start
const _icons = <String, String>{
  'RESULTADO': '🏆',
  'DOBLE OPORTUNIDAD': '🎯',
  'EMPATE NO ACCIÓN': '🛡',
  'GOLES': '⚽',
  'GOLES DE EQUIPO': '🥅',
  'AMBOS MARCAN': '🤝',
  'HÁNDICAP': '⚖',
  'ESPECIALES': '✨',
  '1ª MITAD': '⏱',
  'CÓRNERS': '🚩',
  'TARJETAS': '🟨',
};
// l10n-ignore-end

(Color, String) _nivel(dynamic nivel) => switch (nivel) {
  'alta' => (liveGreen, levelLabel('alta')),
  'solida' => (liveCyan, levelLabel('solida')),
  _ => (liveGold, levelLabel('moderada')),
};

/// Mercados del partido (pestaña Pronósticos): los que el usuario puede ver, con su
/// probabilidad y cuota, y los demás como candado que solo dice la categoría.
/// Todo lo manda el servidor (`ficha.mercados`); sin eso no se dibuja nada.
class MatchMarkets extends StatelessWidget {
  const MatchMarkets({
    super.key,
    required this.data,
    this.onVip,
    this.home = '',
    this.away = '',
  });
  final JsonMap data;

  /// Nombres de los equipos, para redactar títulos y selecciones.
  final String home, away;
  final VoidCallback? onVip;

  @override
  Widget build(BuildContext context) {
    final rows = [
      for (final r in (data['filas'] as List? ?? const [])) jsonMap(r),
    ];
    if (rows.isEmpty) return const SizedBox.shrink();
    final open = rows.where((r) => r['locked'] != true).toList();
    final locked = rows.where((r) => r['locked'] == true).toList();
    // Una fila por categoría con el número de mercados, en el orden que manda el servidor.
    final groups = <String, int>{};
    for (final r in locked) {
      groups.update('${r['grupo']}', (n) => n + 1, ifAbsent: () => 1);
    }
    final scores = data['marcadores'] as List?;
    final l10n = context.l10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(child: liveText(l10n.mmTitle, size: 16, bold: true)),
            liveText(
              '${l10n.mmOpen(open.length)}${locked.isEmpty ? '' : ' · ${l10n.mmLocked(locked.length)}'}',
              size: 11,
              color: liveMuted,
            ),
          ],
        ),
        const SizedBox(height: 10),
        for (final r in open) _OpenRow(row: r, home: home, away: away),
        if (locked.isNotEmpty) ...[
          const SizedBox(height: 4),
          for (final g in groups.entries)
            _LockedRow(group: g.key, count: g.value, onVip: onVip),
        ],
        const SizedBox(height: 8),
        liveText(l10n.mmDisclaimer, size: 10, color: liveMuted),
        if (scores != null || locked.isNotEmpty) ...[
          const SizedBox(height: 16),
          liveText(l10n.mmScoresTitle, size: 14, bold: true),
          const SizedBox(height: 10),
          _Scores(scores: scores, onVip: onVip),
        ],
      ],
    );
  }
}

class _OpenRow extends StatelessWidget {
  const _OpenRow({required this.row, required this.home, required this.away});
  final JsonMap row;
  final String home, away;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final (color, badge) = _nivel(row['nivel']);
    final prob = row['prob'] is num ? (row['prob'] as num).toDouble() : 0.0;
    final published = row['cuota_tipo'] == 'publicada';
    final chance = row['oportunidad'] == true;
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xff0f1925),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: chance ? liveGold : color.withValues(alpha: .28),
          width: chance ? 1.4 : 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  '${_icons[row['grupo']] ?? '•'}  ${groupLabel(row['grupo'])}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    letterSpacing: .4,
                    color: liveMuted,
                  ),
                ),
              ),
              if (chance) _tag(l10n.mmChance, liveGold),
            ],
          ),
          const SizedBox(height: 6),
          liveText(rowTitle(row, home, away), size: 11, color: liveMuted),
          const SizedBox(height: 2),
          Text(
            rowSelection(row, home, away),
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w800,
              color: color,
              height: 1.15,
            ),
          ),
          if (row['nota'] != null) ...[
            const SizedBox(height: 4),
            Text(
              noteText(row['nota'], home, away) ?? '',
              style: const TextStyle(
                fontSize: 10,
                fontStyle: FontStyle.italic,
                color: liveMuted,
              ),
            ),
          ],
          const SizedBox(height: 10),
          ClipRRect(
            borderRadius: BorderRadius.circular(3),
            child: LinearProgressIndicator(
              value: prob.clamp(0, 1),
              minHeight: 4,
              color: color,
              backgroundColor: Colors.white12,
            ),
          ),
          const SizedBox(height: 10),
          Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 7,
                ),
                decoration: BoxDecoration(
                  color: liveGreen.withValues(alpha: .13),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Column(
                  children: [
                    liveText(
                      '@${decimalText(row['cuota'])}',
                      size: 15,
                      bold: true,
                      color: liveGreen,
                    ),
                    liveText(
                      published ? l10n.mmPublishedOdds : l10n.mmFairOdds,
                      size: 8,
                      color: liveMuted,
                    ),
                  ],
                ),
              ),
              const Spacer(),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  liveText(
                    l10n.mmProb((prob * 100).round()),
                    size: 15,
                    bold: true,
                  ),
                  const SizedBox(height: 3),
                  _tag(badge, color),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }

  static Widget _tag(String text, Color color) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
    decoration: BoxDecoration(
      color: color.withValues(alpha: .15),
      borderRadius: BorderRadius.circular(6),
    ),
    child: Text(
      text,
      style: TextStyle(fontSize: 9, fontWeight: FontWeight.w800, color: color),
    ),
  );
}

class _LockedRow extends StatelessWidget {
  const _LockedRow({required this.group, required this.count, this.onVip});
  final String group;
  final int count;
  final VoidCallback? onVip;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 8),
    child: InkWell(
      borderRadius: BorderRadius.circular(14),
      onTap: onVip,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          color: const Color(0xff0c131c),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: Colors.white10),
        ),
        child: Row(
          children: [
            Expanded(
              child: Text(
                '${_icons[group] ?? '•'}  ${context.l10n.mmGroupCount(groupLabel(group), count)}',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w800,
                  letterSpacing: .4,
                  color: liveMuted,
                ),
              ),
            ),
            const Icon(Icons.lock_outline, color: liveGold, size: 18),
            const SizedBox(width: 6),
            liveText('VIP', size: 11, bold: true, color: liveGold),
          ],
        ),
      ),
    ),
  );
}

class _Scores extends StatelessWidget {
  const _Scores({required this.scores, this.onVip});
  final List? scores;
  final VoidCallback? onVip;

  @override
  Widget build(BuildContext context) {
    if (scores == null) {
      return InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: onVip,
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: const Color(0xff0c131c),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: Colors.white10),
          ),
          child: Row(
            children: [
              const Icon(Icons.lock_outline, color: liveGold, size: 18),
              const SizedBox(width: 8),
              Expanded(
                child: liveText(
                  context.l10n.mmScoresVip,
                  size: 12,
                  color: liveMuted,
                ),
              ),
            ],
          ),
        ),
      );
    }
    return SizedBox(
      height: 64,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: scores!.length,
        separatorBuilder: (_, _) => const SizedBox(width: 8),
        itemBuilder: (_, i) {
          final s = jsonMap(scores![i]);
          final top = i == 0;
          final p = s['prob'] is num
              ? ((s['prob'] as num) * 100).round()
              : null;
          return Container(
            width: 70,
            decoration: BoxDecoration(
              color: top
                  ? liveGold.withValues(alpha: .13)
                  : const Color(0xff0f1925),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: top ? liveGold : Colors.white12),
            ),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                liveText('${s['marcador'] ?? '—'}', size: 16, bold: true),
                liveText(
                  p == null ? '—' : '$p%',
                  size: 11,
                  color: top ? liveGold : liveCyan,
                  bold: true,
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
