import 'package:flutter/material.dart';

import 'live_api.dart';
import 'live_widgets.dart';

/// Parley del día: de 1 a 5 parlays sellados antes de los partidos, el más probable de
/// cada escalón de cuota. Todo lo manda el servidor (`/parley`); mientras esté apagado
/// o sin parlays se dice tal cual, sin rellenar nada.
class ParleyTab extends StatefulWidget {
  const ParleyTab({super.key, required this.api});
  final QuantFutApi api;

  @override
  State<ParleyTab> createState() => _ParleyTabState();
}

class _ParleyTabState extends State<ParleyTab> {
  JsonMap? data;
  String? error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      data = null;
      error = null;
    });
    try {
      final body = jsonMap(await widget.api.request('/parley'));
      if (mounted) setState(() => data = body);
    } catch (_) {
      if (mounted) setState(() => error = 'No se pudo cargar el Parley.');
    }
  }

  @override
  Widget build(BuildContext context) {
    if (error != null) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 24),
        child: Column(
          children: [
            liveText(error!, color: liveMuted),
            const SizedBox(height: 12),
            TextButton(onPressed: _load, child: const Text('Reintentar')),
          ],
        ),
      );
    }
    final d = data;
    if (d == null) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 40),
        child: Center(child: CircularProgressIndicator()),
      );
    }
    final rules = jsonMap(d['reglas']);
    final steps = [
      for (final e in (rules['escalones'] as List? ?? const [])) jsonMap(e),
    ];
    final days = [
      for (final x in (d['dias'] as List? ?? const [])) jsonMap(x),
    ];
    final latest = days.isEmpty ? null : days.first;
    final tickets = [
      for (final t in (latest?['tickets'] as List? ?? const [])) jsonMap(t),
    ];
    final total = jsonMap(jsonMap(d['resumen'])['total']);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        liveText(
          steps.isEmpty
              ? 'Parlays sellados antes de los partidos'
              : 'De 1 a ${steps.length} parlays · cuota entre ${decimalText(steps.first['cuota_min'])} y ${decimalText(steps.last['cuota_max'])} · el más probable de cada escalón',
          size: 12,
          color: liveMuted,
        ),
        const SizedBox(height: 14),
        if (d['activo'] != true)
          _notice(
            Icons.hourglass_empty,
            'El Parley todavía no está activo',
            'Cuando se active verás aquí los parlays del día, sellados antes de que empiecen los partidos.',
          )
        else if (tickets.isEmpty)
          _notice(
            Icons.event_busy,
            'Hoy no hay parlays',
            'El modelo no publica un parley si no encuentra uno dentro de las reglas.',
          )
        else ...[
          for (final t in tickets) _TicketCard(ticket: t),
        ],
        if (days.length > 1) ...[
          liveHeading('Días anteriores'),
          for (final day in days.skip(1).take(7)) _PastDay(day: day),
        ],
        if ((total['n'] as num? ?? 0) > 0) _Summary(total: total),
        const SizedBox(height: 8),
        liveText(
          'Se elige por probabilidad, no por valor, y cada pata resta margen. Un parley puede fallar: '
          'multiplicar cuotas también multiplica el riesgo.',
          size: 10,
          color: liveMuted,
        ),
        const SizedBox(height: 18),
      ],
    );
  }

  static Widget _notice(IconData icon, String title, String body) => liveCard(
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: liveGold),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              liveText(title, bold: true, size: 15),
              const SizedBox(height: 6),
              liveText(body, size: 12, color: liveMuted),
            ],
          ),
        ),
      ],
    ),
  );
}

/// Los parlays liquidan como ganado/perdido/nulo y sus patas como win/loss/push/void.
(Color, String) _outcome(dynamic o) => switch (o) {
  'win' || 'ganado' => (liveGreen, 'Acertó'),
  'loss' || 'perdido' => (const Color(0xffe85667), 'Falló'),
  'push' || 'void' || 'nulo' => (liveMuted, 'Anulado'),
  _ => (liveGold, 'Pendiente'),
};

class _TicketCard extends StatelessWidget {
  const _TicketCard({required this.ticket});
  final JsonMap ticket;

  @override
  Widget build(BuildContext context) {
    final legs = [
      for (final p in (ticket['patas'] as List? ?? const [])) jsonMap(p),
    ];
    final (color, label) = _outcome(ticket['outcome']);
    return liveCard(
      border: color.withValues(alpha: .35),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _chip('ESCALÓN ${ticket['escalon'] ?? '—'}', liveCyan),
              const SizedBox(width: 6),
              _chip(label.toUpperCase(), color),
              const Spacer(),
              liveText(
                '@${decimalText(ticket['cuota_total'])}',
                size: 22,
                bold: true,
                color: liveGold,
              ),
            ],
          ),
          const SizedBox(height: 6),
          liveText(
            '${realPercent(ticket['prob_total'])} de probabilidad conjunta · ${legs.length} ${legs.length == 1 ? 'pata' : 'patas'}',
            size: 11,
            color: liveMuted,
          ),
          const SizedBox(height: 10),
          for (final leg in legs) _Leg(leg: leg),
        ],
      ),
    );
  }

  static Widget _chip(String text, Color color) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
    decoration: BoxDecoration(
      color: color.withValues(alpha: .15),
      borderRadius: BorderRadius.circular(8),
    ),
    child: Text(
      text,
      style: TextStyle(fontSize: 9, fontWeight: FontWeight.w800, color: color),
    ),
  );
}

class _Leg extends StatelessWidget {
  const _Leg({required this.leg});
  final JsonMap leg;

  @override
  Widget build(BuildContext context) {
    final (color, _) = _outcome(leg['outcome']);
    final done = leg['outcome'] != null;
    return Container(
      margin: const EdgeInsets.only(top: 6),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: .04),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Icon(
            done
                ? (leg['outcome'] == 'win'
                      ? Icons.check_circle
                      : leg['outcome'] == 'loss'
                      ? Icons.cancel
                      : Icons.remove_circle_outline)
                : Icons.schedule,
            color: color,
            size: 18,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${leg['local'] ?? '—'} · ${leg['visitante'] ?? '—'}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  '${leg['texto'] ?? '—'}',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: color == liveMuted ? Colors.white70 : liveGreen,
                  ),
                ),
                liveText(
                  leg['marcador'] != null
                      ? 'Resultado ${leg['marcador']}'
                      : kickoffText(leg['kickoff_utc']),
                  size: 10,
                  color: liveMuted,
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              liveText(
                '@${decimalText(leg['price'])}',
                size: 14,
                bold: true,
                color: liveGold,
              ),
              liveText(
                realPercent(leg['prob']),
                size: 10,
                color: liveMuted,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _PastDay extends StatelessWidget {
  const _PastDay({required this.day});
  final JsonMap day;

  @override
  Widget build(BuildContext context) {
    final tickets = [
      for (final t in (day['tickets'] as List? ?? const [])) jsonMap(t),
    ];
    final won = tickets.where((t) => t['outcome'] == 'ganado').length;
    final settled = tickets.where((t) => t['outcome'] != null).length;
    return liveCard(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      child: Row(
        children: [
          Expanded(
            child: liveText('${day['dia'] ?? '—'}', size: 13, bold: true),
          ),
          liveText(
            '${tickets.length} parlays${settled == 0 ? '' : ' · $won/$settled acertados'}',
            size: 11,
            color: liveMuted,
          ),
        ],
      ),
    );
  }
}

class _Summary extends StatelessWidget {
  const _Summary({required this.total});
  final JsonMap total;

  @override
  Widget build(BuildContext context) {
    final real = total['acierto_real'];
    final promised = total['prob_media'];
    return liveCard(
      border: liveGold.withValues(alpha: .3),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          liveText('Historial del Parley', bold: true, size: 15),
          const SizedBox(height: 8),
          liveText(
            '${total['aciertos'] ?? 0}/${total['n']} parlays acertados'
            '${real is num ? ' · ${decimalText(real, 1)} % real' : ''}'
            '${promised is num ? ' frente a ${decimalText(promised, 1)} % prometido' : ''}',
            size: 12,
            color: liveGreen,
            bold: true,
          ),
          const SizedBox(height: 6),
          liveText(
            'Con pocos parlays la tasa real no demuestra nada todavía.',
            size: 10,
            color: liveMuted,
          ),
        ],
      ),
    );
  }
}
