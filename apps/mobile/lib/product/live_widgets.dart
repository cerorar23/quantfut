import 'package:flutter/material.dart';

import 'live_api.dart';

const liveBg = Color(0xff090f1a),
    livePanel = Color(0xff132333),
    liveCyan = Color(0xff00d5ee),
    liveGold = Color(0xffffbd00),
    liveGreen = Color(0xff00d58b),
    liveMuted = Color(0xffa0adbd);
ThemeData liveTheme() => ThemeData.dark(useMaterial3: true).copyWith(
  scaffoldBackgroundColor: liveBg,
  colorScheme: const ColorScheme.dark(
    primary: liveCyan,
    secondary: liveGold,
    surface: livePanel,
  ),
  textTheme: ThemeData.dark().textTheme.apply(fontFamily: 'Gilroy Medium'),
);
Widget historyPerformance(JsonMap h, {int? maxMarkets}) {
  final markets = jsonMap(h['por_mercado']).entries.toList()
    ..sort(
      (a, b) => ((jsonMap(b.value)['acierto_real'] as num?) ?? 0).compareTo(
        (jsonMap(a.value)['acierto_real'] as num?) ?? 0,
      ),
    );
  const names = {
    'totals': 'Totales de goles',
    'h2h': 'Resultado 1X2',
    'double_chance': 'Doble oportunidad',
    'corners': 'Córners',
    'spreads': 'Hándicap',
    'team_totals_home': 'Goles del local',
    'team_totals_away': 'Goles del visitante',
    'home_to_score': 'Marca el local',
    'away_to_score': 'Marca el visitante',
  };
  return liveCard(
    border: liveGold.withValues(alpha: .3),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        liveText('Rendimiento registrado', bold: true, size: 17),
        const SizedBox(height: 14),
        liveText(
          '${decimalText(h['acierto_real'], 1)} % de acierto · ${h['aciertos'] ?? '—'}/${h['n'] ?? '—'} resueltos',
          color: liveGreen,
          bold: true,
        ),
        const SizedBox(height: 8),
        liveText(
          'Probabilidad media publicada: ${decimalText(h['acierto_prometido'], 1)} %',
          color: liveMuted,
          size: 12,
        ),
        const SizedBox(height: 14),
        ...markets.take(maxMarkets ?? markets.length).map((e) {
          final m = jsonMap(e.value);
          return Padding(
            padding: const EdgeInsets.only(bottom: 14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                liveText(
                  '${names[e.key] ?? e.key} · ${decimalText(m['acierto_real'], 1)} %',
                  color: liveCyan,
                  size: 12,
                  bold: true,
                ),
                const SizedBox(height: 5),
                LinearProgressIndicator(
                  value: m['acierto_real'] is num
                      ? (m['acierto_real'] / 100).toDouble().clamp(0, 1)
                      : 0,
                  color: liveGreen,
                  backgroundColor: Colors.white12,
                ),
                const SizedBox(height: 5),
                liveText(
                  '${m['aciertos']}/${m['n']} resueltos',
                  size: 10,
                  color: liveMuted,
                ),
              ],
            ),
          );
        }),
        liveText(
          'Historial completo de Alta Probabilidad. Las muestras pequeñas no confirman una ventaja y un pronóstico puede fallar.',
          color: liveMuted,
          size: 11,
        ),
      ],
    ),
  );
}

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
    final fallback = Icon(Icons.shield_outlined, size: size, color: liveMuted);
    return SizedBox(
      width: size,
      height: size,
      child: url is String
          ? Image.network(
              api.base.resolve(url).toString(),
              headers: const {'User-Agent': 'QuantFut/1.0 (Android; Flutter)'},
              errorBuilder: (_, error, stack) => fallback,
            )
          : fallback,
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
                    ? 'GRATUITO'
                    : 'DESBLOQUEADO',
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
            liveText('${pick['texto'] ?? ''}', color: liveGreen, bold: true),
            const SizedBox(height: 10),
            Row(
              children: [
                liveText(
                  'Probabilidad ${realPercent(pick['prob'])}',
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
              'Cuota al publicar · ${pick['ref_book'] ?? pick['book'] ?? 'Fuente no disponible'}',
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
            liveButton('Ver análisis del partido', onOpen, color: liveCyan),
          ] else ...[
            const SizedBox(height: 8),
            liveText(
              'Desbloquea el pronóstico y su cuota.',
              color: liveMuted,
              size: 12,
            ),
            const SizedBox(height: 12),
            liveButton('Desbloquear pronóstico VIP', onVip),
            if (onUnlock != null) ...[
              const SizedBox(height: 6),
              liveButton(
                'Desbloquear por $cost monedas',
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

Widget probabilityBars(JsonMap values) => Column(
  children: ['home', 'draw', 'away'].map((key) {
    final value = values[key];
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: [
          SizedBox(
            width: 38,
            child: liveText(
              key == 'home'
                  ? 'Local'
                  : key == 'draw'
                  ? 'Empate'
                  : 'Visita',
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
);
