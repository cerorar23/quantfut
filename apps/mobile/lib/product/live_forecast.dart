import 'package:flutter/material.dart';

import 'live_api.dart';
import 'live_statistics.dart';
import 'live_widgets.dart';

const marketNames = {
  'totals': 'Goles',
  'h2h': 'Resultado 1X2',
  'double_chance': 'Doble oportunidad',
  'corners': 'Córners',
  'corners_home': 'Córners del local',
  'corners_away': 'Córners del visitante',
  'spreads': 'Hándicap',
  'team_totals_home': 'Goles del local',
  'team_totals_away': 'Goles del visitante',
  'home_to_score': 'Marca el local',
  'away_to_score': 'Marca el visitante',
  'btts': 'Ambos marcan',
};

String marketName(dynamic key) => marketNames['$key'] ?? '${key ?? 'Mercado'}';

/// Marcador real mientras el partido se juega (`partido.vivo`). Si el servidor
/// no lo manda, no se dibuja nada. Muestra cuánto hace de la última lectura:
/// el dato se refresca por ciclos, no es un directo.
class LiveScoreStrip extends StatelessWidget {
  const LiveScoreStrip({super.key, required this.ficha});
  final JsonMap ficha;

  static String _minute(JsonMap vivo) {
    final status = vivo['estado'];
    if (status == 'HT') return 'DESCANSO';
    final minute = vivo['minuto'];
    return minute is num ? "${minute.toInt()}'" : 'EN JUEGO';
  }

  @override
  Widget build(BuildContext context) {
    final vivo = jsonMap(jsonMap(ficha['partido'])['vivo']);
    final score = vivo['marcador'];
    if (score is! List || score.length != 2 || score.any((g) => g is! num)) {
      return const SizedBox.shrink();
    }
    final home = jsonMap(ficha['local'])['nombre'] ?? 'Local';
    final away = jsonMap(ficha['visitante'])['nombre'] ?? 'Visitante';
    final updated = dateValue(vivo['actualizado']);
    final ago = updated == null
        ? null
        : DateTime.now().difference(updated).inMinutes.clamp(0, 999);
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: statsPanel,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: liveGreen.withValues(alpha: .35)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 7,
                height: 7,
                decoration: const BoxDecoration(
                  color: liveGreen,
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 6),
              liveText(_minute(vivo), size: 12, color: liveGreen, bold: true),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: Text(
                  '$home',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  textAlign: TextAlign.right,
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: Text(
                  '${(score[0] as num).toInt()} — ${(score[1] as num).toInt()}',
                  style: const TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              Expanded(
                child: Text(
                  '$away',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          liveText(
            ago == null
                ? 'Marcador en vivo'
                : 'Marcador en vivo · actualizado hace $ago min',
            size: 10,
            color: liveMuted,
          ),
        ],
      ),
    );
  }
}

/// Pronóstico destacado + indicadores + dictamen, todo con datos entregados
/// por el servidor. Lo que no llega se muestra como «—», nunca se rellena.
class ForecastPanel extends StatelessWidget {
  const ForecastPanel({
    super.key,
    required this.pick,
    required this.ficha,
    required this.onStats,
  });
  final JsonMap pick, ficha;
  final VoidCallback onStats;

  String get dictamen {
    final local = jsonMap(ficha['local'])['nombre'] ?? 'el local';
    final away = jsonMap(ficha['visitante'])['nombre'] ?? 'el visitante';
    final parts = <String>[
      '${pick['texto'] ?? 'El pronóstico'} con probabilidad calculada de ${realPercent(pick['prob'])}.',
    ];
    final xg = jsonMap(pick['xg']);
    if (xg['total'] is num) {
      parts.add(
        'Las cuotas del mercado sin margen implican ${decimalText(xg['total'])} goles esperados ($local ${decimalText(xg['local'])} · $away ${decimalText(xg['visita'])}).',
      );
    }
    final price = pick['ref_price'] ?? pick['price'];
    final prob = pick['prob'];
    if (price is num && prob is num && prob > 0) {
      final edge = price * prob - 1;
      parts.add(
        edge >= 0
            ? 'La cuota publicada supera la cuota justa (${decimalText(1 / prob)}).'
            : 'La cuota publicada queda por debajo de la cuota justa (${decimalText(1 / prob)}); el atractivo está en la probabilidad, no en el precio.',
      );
    }
    return parts.join(' ');
  }

  Widget _resultBanner(JsonMap pick) {
    final outcome = pick['outcome'];
    final won = outcome == 'win';
    final color = outcome == null
        ? liveGold
        : won
        ? liveGreen
        : const Color(0xffe85667);
    final score = pick['home_goals'] is num && pick['away_goals'] is num
        ? ' · ${pick['home_goals']}-${pick['away_goals']}'
        : '';
    final label = outcome == null
        ? 'PARTIDO EN JUEGO · pronóstico sellado antes del inicio'
        : '${won ? 'ACERTADO' : 'FALLADO'}$score · pronóstico sellado antes del inicio';
    return _chip(label, color);
  }

  /// Porcentaje de partidos recientes con más de 2,5 goles (promedio de ambos equipos).
  double? get _trend {
    double? share(JsonMap team) {
      final v = jsonMap(jsonMap(team['promedios'])['todos'])['pct_mas_2_5'];
      return v is num && v.isFinite && v >= 0 && v <= 100 ? v.toDouble() : null;
    }

    final a = share(jsonMap(ficha['local'])), b = share(jsonMap(ficha['visitante']));
    return a != null && b != null ? (a + b) / 2 : null;
  }

  @override
  Widget build(BuildContext context) {
    final prob = pick['prob'];
    final price = pick['ref_price'] ?? pick['price'];
    final xg = jsonMap(pick['xg']);
    final modelo = jsonMap(ficha['modelo']);
    final probs = jsonMap(ficha['probabilities']);
    final local = jsonMap(ficha['local']), away = jsonMap(ficha['visitante']);
    final free = pick['free'] == true;
    final book = pick['ref_book'] ?? pick['book'];
    // Favorito 1X2: del modelo (o del 1X2 guardado), el lado con más probabilidad.
    final side = <(String, num)>[
      if ((modelo['local'] ?? probs['home']) is num)
        ('${local['nombre'] ?? 'Local'}', (modelo['local'] ?? probs['home']) as num),
      if ((modelo['visita'] ?? probs['away']) is num)
        ('${away['nombre'] ?? 'Visitante'}', (modelo['visita'] ?? probs['away']) as num),
    ]..sort((a, b) => b.$2.compareTo(a.$2));
    final over25 = modelo['mas_2_5'] is num ? (modelo['mas_2_5'] as num) * 100 : _trend;
    final level = prob is num
        ? (prob >= .75 ? 'ALTA PROB.' : prob >= .6 ? 'SÓLIDA' : 'MODERADA')
        : null;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: liveGreen.withValues(alpha: .45)),
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [liveGreen.withValues(alpha: .08), const Color(0xff0c1520)],
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: liveText(
                      'ANÁLISIS ESTADÍSTICO',
                      size: 12,
                      color: liveGreen,
                      bold: true,
                    ),
                  ),
                  _chip(
                    modelo['fuente'] == 'mercado'
                        ? 'CUOTAS DEL MERCADO'
                        : 'MODELO PROPIO',
                    liveCyan,
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: liveGreen.withValues(alpha: .07),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: liveGreen.withValues(alpha: .3)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Flexible(
                          child: _chip('DESTACADO', liveGreen),
                        ),
                        const Spacer(),
                        if (level != null) ...[
                          _chip(level, liveGold),
                          const SizedBox(width: 6),
                        ],
                        _chip(free ? 'GRATUITO' : 'DESBLOQUEADO', liveGold),
                      ],
                    ),
                    if (pick['started'] == true) ...[
                      const SizedBox(height: 10),
                      _resultBanner(pick),
                    ],
                    const SizedBox(height: 12),
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.center,
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                '${pick['texto'] ?? '—'}',
                                style: const TextStyle(
                                  fontSize: 20,
                                  fontWeight: FontWeight.w800,
                                  height: 1.15,
                                ),
                              ),
                              const SizedBox(height: 6),
                              liveText(
                                marketName(pick['market']),
                                size: 12,
                                color: liveGreen,
                                bold: true,
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 12),
                        Column(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 14,
                                vertical: 9,
                              ),
                              decoration: BoxDecoration(
                                color: liveGreen.withValues(alpha: .18),
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: liveText(
                                '@${decimalText(price)}',
                                size: 20,
                                color: liveGreen,
                                bold: true,
                              ),
                            ),
                            const SizedBox(height: 6),
                            liveText(
                              '${realPercent(prob)} prob. calculada',
                              size: 10,
                              color: liveGreen,
                            ),
                          ],
                        ),
                      ],
                    ),
                    if (book != null || pick['odds_as_of'] != null) ...[
                      const SizedBox(height: 10),
                      liveText(
                        'Cuota al publicar${book != null ? ' · $book' : ''}${pick['odds_as_of'] != null ? ' · ${kickoffText(pick['odds_as_of'])}' : ''}',
                        size: 10,
                        color: liveMuted,
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: _Tile(
                      icon: '🎯',
                      label: 'Probabilidad',
                      value: realPercent(prob),
                      color: liveCyan,
                      caption:
                          'Cuota justa ${decimalText(prob is num && prob > 0 ? 1 / prob : null)}',
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _Tile(
                      icon: '⚽',
                      label: 'xG proyectado',
                      value: decimalText(xg['total']),
                      color: liveGold,
                      caption: xg['total'] is num
                          ? '${decimalText(xg['local'])} local · ${decimalText(xg['visita'])} visita'
                          : 'Disponible en mercados de goles',
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: _Tile(
                      icon: '⚔',
                      label: 'Favorito 1X2',
                      value: side.isEmpty ? '—' : realPercent(side.first.$2),
                      color: statsPurple,
                      caption: side.isEmpty
                          ? 'Probabilidades no disponibles'
                          : '${side.first.$1}${side.length > 1 ? ' · +${((side.first.$2 - side.last.$2) * 100).round()} pts' : ''}',
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _Tile(
                      icon: '📊',
                      label: 'Tendencia goles',
                      value: over25 == null ? '—' : '${over25.round()} %',
                      color: statsLime,
                      caption: over25 == null
                          ? 'Historial insuficiente'
                          : modelo['mas_2_5'] is num
                          ? 'Más de 2,5 según el modelo'
                          : 'Más de 2,5 en sus últimos partidos',
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Colors.black.withValues(alpha: .25),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    liveText(
                      '💡  DICTAMEN DEL MODELO',
                      size: 11,
                      color: liveCyan,
                      bold: true,
                    ),
                    const SizedBox(height: 8),
                    liveText(dictamen, size: 13, color: Colors.white70),
                    if (modelo['fuente'] == 'mercado') ...[
                      const SizedBox(height: 8),
                      liveText(
                        'Probabilidades calculadas con las cuotas del mercado sin margen: esta liga no tiene modelo propio.',
                        size: 10,
                        color: liveMuted,
                      ),
                    ],
                    const SizedBox(height: 8),
                    liveText(
                      'Un pronóstico puede fallar; la probabilidad no garantiza el resultado.',
                      size: 10,
                      color: liveMuted,
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        liveButton('Ver estadísticas del partido', onStats, color: liveCyan),
        const SizedBox(height: 18),
      ],
    );
  }

  Widget _chip(String text, Color color) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
    decoration: BoxDecoration(
      color: color.withValues(alpha: .14),
      borderRadius: BorderRadius.circular(8),
      border: Border.all(color: color.withValues(alpha: .4)),
    ),
    child: Text(
      text,
      maxLines: 1,
      overflow: TextOverflow.ellipsis,
      style: TextStyle(fontSize: 9, fontWeight: FontWeight.w800, color: color),
    ),
  );
}

/// Recuadro de un indicador: icono + etiqueta, valor grande y una línea de contexto.
class _Tile extends StatelessWidget {
  const _Tile({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
    required this.caption,
  });
  final String icon, label, value, caption;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(
      color: Colors.white.withValues(alpha: .04),
      borderRadius: BorderRadius.circular(14),
      border: Border.all(color: Colors.white.withValues(alpha: .07)),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          '$icon  ${label.toUpperCase()}',
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(
            fontSize: 9,
            letterSpacing: .4,
            fontWeight: FontWeight.w700,
            color: liveMuted,
          ),
        ),
        const SizedBox(height: 8),
        FittedBox(
          fit: BoxFit.scaleDown,
          alignment: Alignment.centerLeft,
          child: Text(
            value,
            style: TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.w800,
              color: color,
            ),
          ),
        ),
        const SizedBox(height: 4),
        Text(
          caption,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontSize: 10, color: liveMuted),
        ),
      ],
    ),
  );
}
