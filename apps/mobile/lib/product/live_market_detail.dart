import 'package:flutter/material.dart';

import 'live_api.dart';
import 'live_widgets.dart';
import 'market_catalog.dart';

/// Pantalla de un mercado: tasa de acierto, pronósticos de hoy (abiertos) y
/// el historial de los ya resueltos. Todo viene del servidor; lo que no llega
/// se muestra vacío o «—», nunca inventado.
class MarketDetailScreen extends StatefulWidget {
  const MarketDetailScreen({
    super.key,
    required this.api,
    required this.family,
    required this.minimum,
    required this.color,
    required this.markets,
    required this.upcoming,
    required this.record,
  });
  final QuantFutApi api;
  final MarketFamily family;
  final int minimum;
  final Color color;

  /// Mercados del servidor que componen esta familia.
  final List<String> markets;

  /// Pronósticos próximos de esta familia que el servidor entregó abiertos.
  final List<JsonMap> upcoming;

  /// Resueltos de esta familia (acertados / total).
  final PublishedRecord record;

  @override
  State<MarketDetailScreen> createState() => _MarketDetailScreenState();
}

class _MarketDetailScreenState extends State<MarketDetailScreen> {
  List<JsonMap>? history;
  String? error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      history = null;
      error = null;
    });
    if (widget.markets.isEmpty) {
      setState(() => history = const []);
      return;
    }
    try {
      final body = jsonMap(
        await widget.api.request(
          '/mobile/v1/markets/history',
          query: {'market': widget.markets.join(','), 'limit': 200},
        ),
      );
      if (!mounted) return;
      setState(
        () => history = [
          for (final row in (body['items'] as List? ?? const []))
            jsonMap(row),
        ],
      );
    } catch (_) {
      if (mounted) {
        setState(() => error = 'No se pudo cargar el historial.');
      }
    }
  }

  static bool _sameDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;

  @override
  Widget build(BuildContext context) {
    final today = DateTime.now();
    final todays = (history ?? const <JsonMap>[]).where((r) {
      final d = dateValue(r['kickoff_utc'])?.toLocal();
      return d != null && _sameDay(d, today);
    }).toList();
    final todayWon = todays.where((r) => r['outcome'] == 'win').length;
    return Theme(
      data: liveTheme(),
      child: DefaultTabController(
        length: 2,
        child: Scaffold(
          appBar: AppBar(
            backgroundColor: liveBg,
            title: liveText(widget.family.title, size: 18, bold: true),
          ),
          body: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
                child: _RateCard(
                  color: widget.color,
                  today: history == null ? null : PublishedRecord(todays.length, todayWon),
                  overall: widget.record,
                  onLines: () => showLinesSheet(
                    context,
                    widget.family,
                    widget.minimum,
                    widget.color,
                  ),
                ),
              ),
              TabBar(
                indicatorColor: widget.color,
                labelColor: Colors.white,
                unselectedLabelColor: liveMuted,
                tabs: [
                  Tab(text: 'Hoy (${widget.upcoming.length})'),
                  const Tab(text: 'Anteriores'),
                ],
              ),
              Expanded(
                child: TabBarView(
                  children: [
                    _TodayTab(picks: widget.upcoming, color: widget.color),
                    _HistoryTab(
                      history: history,
                      error: error,
                      color: widget.color,
                      onRetry: _load,
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _RateCard extends StatelessWidget {
  const _RateCard({
    required this.color,
    required this.today,
    required this.overall,
    required this.onLines,
  });
  final Color color;
  final PublishedRecord? today;
  final PublishedRecord overall;
  final VoidCallback onLines;

  Widget _stat(String label, PublishedRecord? r) => Expanded(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        liveText(label, size: 11, color: liveMuted),
        const SizedBox(height: 4),
        Wrap(
          spacing: 8,
          crossAxisAlignment: WrapCrossAlignment.end,
          children: [
            liveText(
              r == null ? '—' : '${r.won}/${r.cases}',
              size: 17,
              bold: true,
            ),
            if (r != null && r.cases > 0)
              liveText(percent(r.observed), size: 15, bold: true, color: color),
          ],
        ),
      ],
    ),
  );

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: livePanel,
      borderRadius: BorderRadius.circular(16),
      border: Border.all(color: color.withValues(alpha: .3)),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(Icons.show_chart, color: color, size: 20),
            const SizedBox(width: 8),
            Expanded(child: liveText('Tasa de acierto', size: 14, bold: true)),
            TextButton(
              onPressed: onLines,
              child: const Text('Líneas validadas', style: TextStyle(fontSize: 11)),
            ),
          ],
        ),
        const SizedBox(height: 6),
        Row(
          children: [
            _stat('Hoy', today),
            Container(width: 1, height: 36, color: Colors.white12),
            const SizedBox(width: 14),
            _stat('General', overall),
          ],
        ),
      ],
    ),
  );
}

Widget _teams(JsonMap p) => Column(
  crossAxisAlignment: CrossAxisAlignment.start,
  children: [
    Text(
      '${p['local'] ?? '—'}',
      maxLines: 1,
      overflow: TextOverflow.ellipsis,
      style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700),
    ),
    const SizedBox(height: 3),
    Text(
      '${p['visitante'] ?? '—'}',
      maxLines: 1,
      overflow: TextOverflow.ellipsis,
      style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700),
    ),
  ],
);

Widget _pickChip(String text, Color color) => Container(
  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
  decoration: BoxDecoration(
    color: color.withValues(alpha: .16),
    borderRadius: BorderRadius.circular(8),
  ),
  child: Text(
    text,
    maxLines: 2,
    overflow: TextOverflow.ellipsis,
    style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: color),
  ),
);

Widget _modelColumn(JsonMap p, {String? extra}) => Column(
  crossAxisAlignment: CrossAxisAlignment.end,
  children: [
    liveText(realPercent(p['prob']), size: 20, bold: true, color: liveGreen),
    liveText('MODELO', size: 9, color: liveMuted),
    if (extra != null) liveText(extra, size: 10, color: liveMuted),
  ],
);

Widget _emptyState(String message) => Center(
  child: Padding(
    padding: const EdgeInsets.all(28),
    child: liveText(message, size: 13, color: liveMuted),
  ),
);

class _TodayTab extends StatelessWidget {
  const _TodayTab({required this.picks, required this.color});
  final List<JsonMap> picks;
  final Color color;

  @override
  Widget build(BuildContext context) {
    if (picks.isEmpty) {
      return _emptyState(
        'No hay pronósticos disponibles ahora para este mercado. '
        'Aparecen cuando el modelo los publica, antes del partido.',
      );
    }
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
      children: [
        for (final p in picks)
          liveCard(
            border: color.withValues(alpha: .25),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                liveText(
                  kickoffText(p['kickoff_utc']),
                  size: 11,
                  color: liveMuted,
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(child: _teams(p)),
                    _modelColumn(p),
                  ],
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(child: _pickChip('${p['texto'] ?? '—'}', color)),
                    const SizedBox(width: 10),
                    if ((p['ref_price'] ?? p['price']) is num)
                      liveText(
                        '@${decimalText(p['ref_price'] ?? p['price'])}',
                        size: 15,
                        bold: true,
                        color: liveGold,
                      ),
                  ],
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _HistoryTab extends StatelessWidget {
  const _HistoryTab({
    required this.history,
    required this.error,
    required this.color,
    required this.onRetry,
  });
  final List<JsonMap>? history;
  final String? error;
  final Color color;
  final VoidCallback onRetry;

  static String _day(DateTime d) {
    final now = DateTime.now();
    final diff = DateTime(now.year, now.month, now.day)
        .difference(DateTime(d.year, d.month, d.day))
        .inDays;
    return diff == 0
        ? 'Hoy'
        : diff == 1
        ? 'Ayer'
        : '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}/${d.year}';
  }

  @override
  Widget build(BuildContext context) {
    if (error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            liveText(error!, color: liveMuted),
            const SizedBox(height: 12),
            TextButton(onPressed: onRetry, child: const Text('Reintentar')),
          ],
        ),
      );
    }
    final rows = history;
    if (rows == null) return const Center(child: CircularProgressIndicator());
    if (rows.isEmpty) {
      return _emptyState('Todavía no hay pronósticos resueltos en este mercado.');
    }
    final children = <Widget>[];
    String? current;
    for (final p in rows) {
      final d = dateValue(p['kickoff_utc'])?.toLocal();
      final label = d == null ? 'Sin fecha' : _day(d);
      if (label != current) {
        current = label;
        children.add(
          Padding(
            padding: const EdgeInsets.only(top: 8, bottom: 10),
            child: Center(
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 5),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: .06),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: liveText(label, size: 11, color: liveMuted, bold: true),
              ),
            ),
          ),
        );
      }
      final won = p['outcome'] == 'win';
      // En córners el resultado relevante son los córners, no los goles.
      final isCorners = '${p['market']}'.startsWith('corners');
      final hh = isCorners ? p['home_corners'] : p['home_goals'];
      final aa = isCorners ? p['away_corners'] : p['away_goals'];
      final hasScore = hh is num && aa is num;
      children.add(
        liveCard(
          border: (won ? liveGreen : const Color(0xffe85667)).withValues(
            alpha: .25,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(child: _teams(p)),
                  if (hasScore)
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        liveText(
                          '$hh-$aa',
                          size: 22,
                          bold: true,
                          color: liveCyan,
                        ),
                        if (isCorners)
                          liveText(
                            'córners · total ${hh + aa}',
                            size: 9,
                            color: liveMuted,
                          ),
                      ],
                    ),
                  const SizedBox(width: 10),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 6,
                    ),
                    decoration: BoxDecoration(
                      color: won ? const Color(0xff1f7a3d) : const Color(0xffc23b4d),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: liveText(
                      won ? 'Acertó' : 'Falló',
                      size: 11,
                      bold: true,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(child: _pickChip('${p['texto'] ?? '—'}', color)),
                  const SizedBox(width: 10),
                  _modelColumn(p),
                ],
              ),
            ],
          ),
        ),
      );
    }
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
      children: children,
    );
  }
}

/// Evidencia por línea de la familia: qué líneas están confirmadas.
void showLinesSheet(
  BuildContext context,
  MarketFamily family,
  int minimum,
  Color color,
) {
  Widget row(MarketLine line) {
    final supported = line.supported(minimum);
    final (label, tone) = supported
        ? ('Confirmada', liveGreen)
        : !line.deployed
        ? ('Sin desplegar', liveGold)
        : line.cases < minimum
        ? ('Muestra corta', liveGold)
        : ('En revisión', liveMuted);
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                liveText(line.label, size: 13, bold: true),
                liveText(
                  '${caseCount(line.cases)} casos',
                  size: 10,
                  color: liveMuted,
                ),
              ],
            ),
          ),
          liveText(percent(line.observed), size: 14, bold: true),
          const SizedBox(width: 10),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: tone.withValues(alpha: .15),
              borderRadius: BorderRadius.circular(8),
            ),
            child: liveText(label, size: 10, color: tone, bold: true),
          ),
        ],
      ),
    );
  }

  showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: const Color(0xff0d1522),
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(22)),
    ),
    builder: (_) => SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            liveText(family.title, size: 18, bold: true, color: color),
            const SizedBox(height: 6),
            liveText(family.subtitle, size: 12, color: liveMuted),
            const SizedBox(height: 14),
            for (final line in family.lines) row(line),
          ],
        ),
      ),
    ),
  );
}
