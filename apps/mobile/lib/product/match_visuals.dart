import 'package:flutter/material.dart';

import 'prediction_data.dart';

const matchGreen = Color(0xff00e79a);
const matchCyan = Color(0xff00d5ee);
const matchGold = Color(0xffffc400);
const matchMuted = Color(0xff9ca9b6);
const matchSurface = Color(0xff12191f);

class MatchTeams extends StatelessWidget {
  const MatchTeams({super.key, required this.match, this.compact = false});
  final PreviewMatch match;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final names = match.teams;
    if (names.length != 2) {
      return Text(match.title, textAlign: TextAlign.center);
    }
    return Row(
      children: [
        Expanded(child: _team(names.first, matchGreen)),
        const Padding(
          padding: EdgeInsets.symmetric(horizontal: 10),
          child: Text('VS', style: TextStyle(color: matchMuted, fontSize: 12)),
        ),
        Expanded(child: _team(names.last, matchCyan)),
      ],
    );
  }

  Widget _team(String name, Color color) {
    final initials = name
        .split(' ')
        .where((word) => word.isNotEmpty)
        .take(2)
        .map((word) => word[0])
        .join()
        .toUpperCase();
    return Column(
      children: [
        // Original monograms; club crests will come from verified match data.
        Container(
          width: compact ? 32 : 48,
          height: compact ? 36 : 52,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [color.withValues(alpha: .3), matchSurface],
            ),
            border: Border.all(color: color.withValues(alpha: .55)),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text(
            initials,
            style: TextStyle(
              color: color,
              fontFamily: 'Gilroy Bold',
              fontSize: compact ? 11 : 15,
            ),
          ),
        ),
        const SizedBox(height: 8),
        Text(
          name,
          textAlign: TextAlign.center,
          style: TextStyle(
            fontFamily: 'Gilroy Bold',
            fontSize: compact ? 12 : 15,
          ),
        ),
      ],
    );
  }
}

class LockedVipMatchCard extends StatelessWidget {
  const LockedVipMatchCard({
    super.key,
    required this.match,
    required this.onVip,
  });
  final PreviewMatch match;
  final VoidCallback onVip;

  @override
  Widget build(BuildContext context) {
    final teaser = match.teaser;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(17),
        border: Border.all(color: matchGold.withValues(alpha: .35)),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xff182719), Color(0xff10151c), Color(0xff0c1823)],
        ),
      ),
      child: Column(
        children: [
          Wrap(
            alignment: WrapAlignment.center,
            spacing: 8,
            runSpacing: 5,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              const _Badge('VIP', matchGold),
              Text(
                match.league,
                style: const TextStyle(fontSize: 10, color: matchMuted),
              ),
            ],
          ),
          const SizedBox(height: 12),
          MatchTeams(match: match, compact: true),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
            decoration: BoxDecoration(
              color: matchGreen,
              borderRadius: BorderRadius.circular(25),
              boxShadow: [
                BoxShadow(
                  color: matchGreen.withValues(alpha: .18),
                  blurRadius: 15,
                ),
              ],
            ),
            child: Text(
              teaser == null
                  ? 'ANÁLISIS VIP'
                  : '${teaser.probability.toStringAsFixed(0)} % PROBABILIDAD · EJEMPLO',
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: Colors.black,
                fontSize: 11,
                fontFamily: 'Gilroy ExtraBold',
              ),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            teaser == null
                ? 'Vista gratuita pendiente de conectar'
                : 'Mercado gratuito de ejemplo: ${teaser.market}',
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 11),
          ),
          const SizedBox(height: 6),
          const Text(
            'Desbloquea el partido para ver todos sus mercados',
            textAlign: TextAlign.center,
            style: TextStyle(color: matchGold, fontSize: 10),
          ),
          const SizedBox(height: 12),
          DecoratedBox(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(32),
              gradient: const LinearGradient(
                colors: [matchGold, Color(0xffff9c00)],
              ),
              boxShadow: [
                BoxShadow(
                  color: matchGold.withValues(alpha: .15),
                  blurRadius: 14,
                ),
              ],
            ),
            child: SizedBox(
              width: double.infinity,
              child: FilledButton(
                key: const ValueKey('locked-vip-cta'),
                onPressed: onVip,
                style: FilledButton.styleFrom(
                  backgroundColor: Colors.transparent,
                  foregroundColor: Colors.black,
                  shadowColor: Colors.transparent,
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 14,
                  ),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Flexible(
                      child: Text(
                        'Desbloquear pronóstico VIP',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontFamily: 'Gilroy ExtraBold',
                          fontSize: 12,
                        ),
                      ),
                    ),
                    SizedBox(width: 7),
                    Icon(Icons.lock_outline_rounded, size: 16),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _Badge extends StatelessWidget {
  const _Badge(this.text, this.color);
  final String text;
  final Color color;
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
    decoration: BoxDecoration(
      color: color.withValues(alpha: .15),
      border: Border.all(color: color.withValues(alpha: .5)),
      borderRadius: BorderRadius.circular(8),
    ),
    child: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(Icons.star_rounded, size: 12, color: color),
        const SizedBox(width: 3),
        Text(
          text,
          style: TextStyle(
            color: color,
            fontSize: 10,
            fontFamily: 'Gilroy Bold',
          ),
        ),
      ],
    ),
  );
}
