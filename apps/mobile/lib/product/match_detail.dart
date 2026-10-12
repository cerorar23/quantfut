import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'match_visuals.dart';
import 'prediction_data.dart';

/// Optional match metrics. Missing values stay missing, never inferred from
/// a market's aggregate backtest or substituted with a reference screenshot.
class MatchStatistics {
  const MatchStatistics({
    this.resultProbabilities,
    this.homeRadar,
    this.awayRadar,
    this.homeGoalMean,
    this.awayGoalMean,
    this.projectedGoals,
    this.eloDifference,
  });
  final List<double>? resultProbabilities;
  final List<double>? homeRadar, awayRadar;
  final double? homeGoalMean, awayGoalMean, projectedGoals;
  final int? eloDifference;
}

Future<void> openMatchDetail(BuildContext context, PreviewMatch match) {
  if (match.locked) {
    throw ArgumentError('A locked match has no authorized analysis');
  }
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    backgroundColor: const Color(0xff080d10),
    constraints: const BoxConstraints(maxWidth: 650),
    shape: const RoundedRectangleBorder(
      side: BorderSide(color: matchGreen),
      borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
    ),
    clipBehavior: Clip.antiAlias,
    builder: (_) => MatchDetailWindow(match: match),
  );
}

class MatchDetailWindow extends StatefulWidget {
  const MatchDetailWindow({super.key, required this.match, this.statistics});
  final PreviewMatch match;
  final MatchStatistics? statistics;
  @override
  State<MatchDetailWindow> createState() => _MatchDetailWindowState();
}

class _MatchDetailWindowState extends State<MatchDetailWindow> {
  int _tab = 0;
  String _filter = 'Todos';
  bool _favorite = false;
  final _scroll = ScrollController();
  PreviewMatch get match => widget.match;

  @override
  void dispose() {
    _scroll.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // A second guard also protects direct construction of the detail window.
    if (match.locked) {
      return const SafeArea(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Text('Este pronóstico requiere acceso VIP.'),
        ),
      );
    }
    return Material(
      color: const Color(0xff080d10),
      child: SizedBox(
        height: MediaQuery.sizeOf(context).height * .94,
        child: SafeArea(
          top: false,
          child: Column(
            children: [
              Container(
                margin: const EdgeInsets.only(top: 10),
                width: 34,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.white24,
                  borderRadius: BorderRadius.circular(4),
                ),
              ),
              Padding(
                padding: const EdgeInsets.only(left: 16, right: 4),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        match.league,
                        style: const TextStyle(color: matchMuted, fontSize: 11),
                      ),
                    ),
                    IconButton(
                      tooltip: _favorite
                          ? 'Quitar favorito de esta sesión'
                          : 'Guardar favorito en esta sesión',
                      onPressed: () => setState(() => _favorite = !_favorite),
                      icon: Icon(
                        _favorite
                            ? Icons.star_rounded
                            : Icons.star_border_rounded,
                        color: matchGold,
                      ),
                    ),
                    IconButton(
                      tooltip: 'Copiar resumen',
                      icon: const Icon(
                        Icons.copy_rounded,
                        color: matchGreen,
                        size: 20,
                      ),
                      onPressed: () async {
                        await Clipboard.setData(
                          ClipboardData(
                            text:
                                '${match.title}\n${match.selection}\nVista de ejemplo · QuantFut',
                          ),
                        );
                        if (!context.mounted) return;
                        ScaffoldMessenger.maybeOf(context)?.showSnackBar(
                          const SnackBar(
                            content: Text('Resumen de ejemplo copiado'),
                          ),
                        );
                      },
                    ),
                    IconButton(
                      tooltip: 'Cerrar pronóstico',
                      icon: const Icon(Icons.close),
                      onPressed: () => Navigator.pop(context),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: SingleChildScrollView(
                  controller: _scroll,
                  padding: const EdgeInsets.fromLTRB(14, 4, 14, 24),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      MatchTeams(match: match),
                      const SizedBox(height: 14),
                      const Text(
                        'FICHA DE EJEMPLO · DATOS DEL PARTIDO POR CONECTAR',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: matchGold, fontSize: 10),
                      ),
                      const SizedBox(height: 18),
                      Wrap(
                        spacing: 5,
                        runSpacing: 5,
                        alignment: WrapAlignment.center,
                        children: [
                          for (var i = 0; i < 3; i++)
                            ChoiceChip(
                              key: ValueKey('match-tab-$i'),
                              label: Text(
                                [
                                  'Pronósticos',
                                  'Estadísticas',
                                  'H2H y táctica',
                                ][i],
                                style: const TextStyle(fontSize: 11),
                              ),
                              selected: _tab == i,
                              showCheckmark: false,
                              selectedColor: [
                                matchGreen,
                                matchCyan,
                                const Color(0xffb58aff),
                              ][i].withValues(alpha: .15),
                              labelStyle: TextStyle(
                                color: _tab == i
                                    ? [
                                        matchGreen,
                                        matchCyan,
                                        const Color(0xffb58aff),
                                      ][i]
                                    : matchMuted,
                              ),
                              onSelected: (_) => setState(() => _tab = i),
                            ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      if (_tab == 0)
                        ..._predictions()
                      else if (_tab == 1)
                        ..._statistics()
                      else
                        ..._tactics(),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  List<({String category, String title, double probability})> get _picks {
    final probabilities = match.probabilities!;
    final football = match.sport == 'Fútbol';
    if (!football) {
      return [
        (
          category: 'Puntos',
          title: match.selection!,
          probability: probabilities[0],
        ),
        (
          category: 'Rebotes',
          title: 'Rebotes · Ejemplo visual',
          probability: probabilities[1],
        ),
        (
          category: 'Asistencias',
          title: 'Asistencias · Ejemplo visual',
          probability: probabilities[2],
        ),
        (
          category: 'Ganador',
          title: 'Ganador · Ejemplo visual',
          probability: probabilities[3],
        ),
      ];
    }
    return [
      (
        category: match.selection!.startsWith('Marca') ? 'Goles' : 'Hándicap',
        title: match.selection!,
        probability:
            probabilities[football && match.selection!.startsWith('Marca')
                ? 2
                : football
                ? 1
                : 0],
      ),
      (
        category: football ? 'Córners' : 'Estadísticas',
        title: match.secondary!,
        probability: probabilities[3],
      ),
      if (football)
        (
          category: 'Doble oportunidad',
          title: 'Doble oportunidad · Ejemplo visual',
          probability: probabilities[0],
        ),
      if (football && !match.selection!.startsWith('Marca'))
        (
          category: 'Goles',
          title: 'Marca un equipo · Ejemplo visual',
          probability: probabilities[2],
        ),
    ];
  }

  List<Widget> _predictions() {
    final highlighted = _picks.first;
    return [
      _panel(
        'ANÁLISIS DEL PRONÓSTICO',
        color: matchGreen,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'PRONÓSTICO DESTACADO · EJEMPLO',
              style: TextStyle(color: matchGreen, fontSize: 10),
            ),
            const SizedBox(height: 12),
            Text(
              highlighted.title,
              style: const TextStyle(
                fontSize: 23,
                fontFamily: 'Gilroy ExtraBold',
              ),
            ),
            const SizedBox(height: 10),
            Text(
              '${highlighted.probability.toStringAsFixed(0)} % · Probabilidad de ejemplo',
              style: const TextStyle(
                color: matchGreen,
                fontFamily: 'Gilroy Bold',
              ),
            ),
            const SizedBox(height: 14),
            _metrics([
              (
                'Probabilidad del pick',
                '${highlighted.probability.toStringAsFixed(0)} %',
                matchCyan,
              ),
              (
                match.sport == 'NBA' ? 'Puntos proyectados' : 'xG proyectado',
                _value(widget.statistics?.projectedGoals),
                matchGold,
              ),
              (
                'Diferencia ELO',
                widget.statistics?.eloDifference?.toString() ?? '—',
                Colors.white,
              ),
              ('Cuota disponible', '—', const Color(0xffb58aff)),
            ]),
            const SizedBox(height: 12),
            _note(
              'Lectura del modelo',
              'Aquí se mostrará la explicación correspondiente al pronóstico publicado. La probabilidad de un pick y el acierto histórico se presentarán por separado.',
            ),
          ],
        ),
      ),
      const SizedBox(height: 12),
      SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: [
            for (final category in [
              'Todos',
              ..._picks.map((pick) => pick.category).toSet(),
            ])
              Padding(
                padding: const EdgeInsets.only(right: 6),
                child: ChoiceChip(
                  key: ValueKey('pick-filter-$category'),
                  label: Text(category, style: const TextStyle(fontSize: 11)),
                  selected: _filter == category,
                  showCheckmark: false,
                  selectedColor: matchGreen.withValues(alpha: .17),
                  onSelected: (_) => setState(() => _filter = category),
                ),
              ),
          ],
        ),
      ),
      const SizedBox(height: 8),
      for (final pick in _picks.where(
        (pick) => _filter == 'Todos' || pick.category == _filter,
      ))
        Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: _panel(
            pick.category.toUpperCase(),
            color: pick == highlighted ? matchGold : matchGreen,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  pick.title,
                  style: const TextStyle(
                    fontFamily: 'Gilroy Bold',
                    fontSize: 17,
                  ),
                ),
                const SizedBox(height: 12),
                ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: LinearProgressIndicator(
                    value: pick.probability / 100,
                    color: matchGreen,
                    backgroundColor: Colors.white10,
                    minHeight: 4,
                  ),
                ),
                const SizedBox(height: 10),
                Wrap(
                  alignment: WrapAlignment.spaceBetween,
                  spacing: 10,
                  runSpacing: 6,
                  children: [
                    const Text(
                      'Cuota: pendiente',
                      style: TextStyle(color: matchMuted, fontSize: 11),
                    ),
                    Text(
                      '${pick.probability.toStringAsFixed(0)} % · Ejemplo',
                      style: const TextStyle(
                        color: matchGreen,
                        fontFamily: 'Gilroy Bold',
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      if (match.sport == 'Fútbol')
        _note(
          'Marcadores más probables',
          'Pendientes de la distribución del modelo para este partido.',
        ),
    ];
  }

  List<Widget> _statistics() {
    final stats = widget.statistics;
    final names = match.teams;
    final result = stats?.resultProbabilities;
    return [
      _metrics([
        (
          names.first,
          result == null ? '—' : '${result[0].toStringAsFixed(0)} %',
          matchGreen,
        ),
        if (match.sport == 'Fútbol')
          (
            'Empate',
            match.sport == 'NBA' || result == null
                ? '—'
                : '${result[1].toStringAsFixed(0)} %',
            matchMuted,
          ),
        (
          names.length > 1 ? names.last : 'Visitante',
          result == null ? '—' : '${result[2].toStringAsFixed(0)} %',
          matchCyan,
        ),
      ]),
      const SizedBox(height: 12),
      _panel(
        'COMPARATIVA ENTRE EQUIPOS',
        color: matchCyan,
        child: Column(
          children: [
            Semantics(
              label: stats?.homeRadar == null || stats?.awayRadar == null
                  ? 'Comparativa pendiente de datos del partido'
                  : 'Comparativa de seis indicadores entre los equipos',
              child: SizedBox(
                height: 210,
                width: double.infinity,
                child: CustomPaint(
                  painter: _RadarPainter(stats?.homeRadar, stats?.awayRadar),
                ),
              ),
            ),
            if (stats?.homeRadar == null || stats?.awayRadar == null)
              const Text(
                'Comparativa pendiente de datos',
                style: TextStyle(color: matchMuted, fontSize: 12),
              ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 14,
              runSpacing: 6,
              alignment: WrapAlignment.center,
              children: [
                Text(
                  names.first,
                  style: const TextStyle(color: matchGreen, fontSize: 11),
                ),
                if (names.length > 1)
                  Text(
                    names.last,
                    style: const TextStyle(color: matchCyan, fontSize: 11),
                  ),
              ],
            ),
          ],
        ),
      ),
      const SizedBox(height: 12),
      if (match.sport == 'Fútbol')
        _panel(
          'DISTRIBUCIÓN DE GOLES',
          color: matchGreen,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'Probabilidad de 0, 1, 2 o 3+ goles por equipo. Se mostrará cuando el backend entregue el modelo y sus parámetros.',
                style: TextStyle(color: matchMuted, fontSize: 12, height: 1.5),
              ),
              const SizedBox(height: 12),
              LayoutBuilder(
                builder: (context, constraints) {
                  final columns = [
                    _distribution(names.first, stats?.homeGoalMean, matchGreen),
                    _distribution(
                      names.length > 1 ? names.last : 'Visitante',
                      stats?.awayGoalMean,
                      matchCyan,
                    ),
                  ];
                  if (constraints.maxWidth < 330 ||
                      MediaQuery.textScalerOf(context).scale(12) > 16) {
                    return Column(
                      children: [
                        columns.first,
                        const SizedBox(height: 12),
                        columns.last,
                      ],
                    );
                  }
                  return Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(child: columns.first),
                      const SizedBox(width: 12),
                      Expanded(child: columns.last),
                    ],
                  );
                },
              ),
            ],
          ),
        )
      else
        _note(
          'Estadísticas NBA',
          'Puntos, rebotes y asistencias se conectarán al modelo NBA. La distribución de goles corresponde únicamente a fútbol.',
        ),
    ];
  }

  List<Widget> _tactics() => [
    _panel(
      'HISTORIAL DIRECTO (H2H)',
      color: const Color(0xffb58aff),
      child: const Text(
        'H2H no disponible para este partido.',
        style: TextStyle(color: matchMuted),
      ),
    ),
    const SizedBox(height: 12),
    _panel(
      'ALINEACIONES',
      color: matchCyan,
      child: const Text(
        'Alineaciones no confirmadas. Se actualizarán cuando estén disponibles en la fuente del partido.',
        style: TextStyle(color: matchMuted, height: 1.5),
      ),
    ),
    const SizedBox(height: 12),
    for (final name in match.teams)
      Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: _panel(
          name,
          color: matchMuted,
          child: const Text(
            'Bajas: información pendiente.',
            style: TextStyle(color: matchMuted),
          ),
        ),
      ),
    _panel(
      'ÁRBITRO ASIGNADO',
      color: matchGold,
      child: const Text(
        'Por confirmar',
        style: TextStyle(fontFamily: 'Gilroy Bold'),
      ),
    ),
    const SizedBox(height: 12),
    _note(
      'Contexto táctico',
      'Aquí se mostrará el contexto disponible del partido, con su fuente y fecha de actualización.',
    ),
  ];

  Widget _distribution(String team, double? mean, Color color) {
    final available = mean != null && mean.isFinite && mean >= 0;
    final probabilities = available ? poissonGoals(mean) : null;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          team,
          style: TextStyle(
            color: color,
            fontFamily: 'Gilroy Bold',
            fontSize: 12,
          ),
        ),
        const SizedBox(height: 8),
        for (var i = 0; i < 4; i++)
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: Column(
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        i == 3 ? '3+ goles' : '$i goles',
                        style: const TextStyle(color: matchMuted, fontSize: 11),
                      ),
                    ),
                    Text(
                      probabilities == null
                          ? '—'
                          : '${(probabilities[i] * 100).toStringAsFixed(0)} %',
                      style: const TextStyle(fontSize: 11),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                LinearProgressIndicator(
                  value: probabilities?[i] ?? 0,
                  minHeight: 3,
                  color: color,
                  backgroundColor: Colors.white10,
                ),
              ],
            ),
          ),
      ],
    );
  }

  Widget _metrics(List<(String, String, Color)> metrics) => LayoutBuilder(
    builder: (context, constraints) {
      final columns =
          constraints.maxWidth < 270 ||
              MediaQuery.textScalerOf(context).scale(12) > 18
          ? 1
          : 2;
      return Wrap(
        spacing: 8,
        runSpacing: 8,
        children: [
          for (final metric in metrics)
            SizedBox(
              width: (constraints.maxWidth - (columns - 1) * 8) / columns,
              child: Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: matchSurface,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.white10),
                ),
                child: Column(
                  children: [
                    Text(
                      metric.$1,
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: matchMuted, fontSize: 11),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      metric.$2,
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: metric.$3,
                        fontSize: 24,
                        fontFamily: 'Gilroy ExtraBold',
                      ),
                    ),
                  ],
                ),
              ),
            ),
        ],
      );
    },
  );

  Widget _note(String title, String text) => _panel(
    title,
    color: matchCyan,
    child: Text(
      text,
      style: const TextStyle(color: matchMuted, height: 1.5, fontSize: 12),
    ),
  );
  String _value(double? value) => value?.toStringAsFixed(2) ?? '—';
}

List<double> poissonGoals(double mean) {
  if (!mean.isFinite || mean < 0) throw ArgumentError.value(mean, 'mean');
  final p0 = math.exp(-mean), p1 = math.exp(-mean) * mean;
  final p2 = p1 * mean / 2;
  return [p0, p1, p2, (1 - p0 - p1 - p2).clamp(0.0, 1.0)];
}

Widget _panel(String title, {required Color color, required Widget child}) =>
    Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: matchSurface,
        borderRadius: BorderRadius.circular(15),
        border: Border.all(color: color.withValues(alpha: .2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            title,
            style: TextStyle(
              color: color,
              fontFamily: 'Gilroy Bold',
              fontSize: 11,
            ),
          ),
          const SizedBox(height: 12),
          child,
        ],
      ),
    );

class _RadarPainter extends CustomPainter {
  const _RadarPainter(this.home, this.away);
  final List<double>? home, away;
  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = math.min(size.width / 2 - 45, size.height / 2 - 28);
    Offset point(int i, double scale) =>
        center +
        Offset(
              math.cos(-math.pi / 2 + i * math.pi / 3),
              math.sin(-math.pi / 2 + i * math.pi / 3),
            ) *
            (radius * scale);
    Path polygon(List<double> values) {
      final path = Path()
        ..moveTo(point(0, values[0]).dx, point(0, values[0]).dy);
      for (var i = 1; i < 6; i++) {
        path.lineTo(point(i, values[i]).dx, point(i, values[i]).dy);
      }
      return path..close();
    }

    final grid = Paint()
      ..color = Colors.white10
      ..style = PaintingStyle.stroke;
    for (var ring = 1; ring <= 4; ring++) {
      canvas.drawPath(polygon(List.filled(6, ring / 4)), grid);
    }
    for (var i = 0; i < 6; i++) {
      canvas.drawLine(center, point(i, 1), grid);
      final label = TextPainter(
        text: TextSpan(
          text: ['Ataque', 'Defensa', 'Posesión', 'Acierto', 'Tiros', 'xG'][i],
          style: const TextStyle(
            color: matchMuted,
            fontSize: 10,
            fontFamily: 'Gilroy Medium',
          ),
        ),
        textDirection: TextDirection.ltr,
      )..layout();
      final position = point(i, 1.25);
      label.paint(canvas, position - Offset(label.width / 2, label.height / 2));
    }
    for (final entry in [(home, matchGreen), (away, matchCyan)]) {
      final values = entry.$1;
      if (values == null ||
          values.length != 6 ||
          values.any((v) => !v.isFinite || v < 0 || v > 1)) {
        continue;
      }
      final path = polygon(values);
      canvas.drawPath(path, Paint()..color = entry.$2.withValues(alpha: .15));
      canvas.drawPath(
        path,
        Paint()
          ..color = entry.$2
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2,
      );
    }
  }

  @override
  bool shouldRepaint(_RadarPainter oldDelegate) =>
      home != oldDelegate.home || away != oldDelegate.away;
}
