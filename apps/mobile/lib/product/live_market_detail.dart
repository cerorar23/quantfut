import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import '../l10n/pick_labels.dart';
import 'live_api.dart';
import 'live_widgets.dart';
import 'market_catalog.dart';
import 'market_hub.dart';

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
    this.locked = const [],
    this.onVip,
    this.agenda = const [],
    this.onOpenMatch,
  });
  final QuantFutApi api;
  final MarketFamily family;
  final int minimum;
  final Color color;

  /// Mercados del servidor que componen esta familia.
  final List<String> markets;

  /// Pronósticos próximos de esta familia que el servidor entregó abiertos.
  final List<JsonMap> upcoming;

  /// Pronósticos de esta familia bloqueados (VIP): solo partido y hora.
  final List<JsonMap> locked;

  /// Abre la pantalla VIP.
  final VoidCallback? onVip;

  /// Agenda de /home: de ella salen los escudos de los partidos que aún no se juegan.
  final List<JsonMap> agenda;

  /// Abre la ficha del partido al tocar su pronóstico.
  final ValueChanged<String>? onOpenMatch;

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
          for (final row in (body['items'] as List? ?? const [])) jsonMap(row),
        ],
      );
    } catch (_) {
      if (mounted) {
        setState(() => error = context.l10n.mdLoadError);
      }
    }
  }

  static bool _sameDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;

  /// Escudo de un lado: el que trae el propio pronóstico (`local_escudo`/`visitante_escudo`), si no el de la
  /// agenda por `match_id` y, si tampoco, las iniciales del nombre.
  Widget Function(double) _crest(JsonMap p, String side) {
    final name = '${p[side] ?? ''}';
    final own = p['${side}_escudo'];
    JsonMap team = {'nombre': name};
    if (own is String && own.isNotEmpty) {
      team = {'nombre': name, 'escudo': own};
    } else {
      for (final m in widget.agenda) {
        if ('${m['match_id']}' != '${p['match_id']}') continue;
        final t = jsonMap(m[side]);
        if (t.isNotEmpty) team = {...t, 'nombre': t['nombre'] ?? name};
        break;
      }
    }
    return (size) => TeamCrest(team: team, api: widget.api, size: size);
  }

  VoidCallback? _open(JsonMap p) {
    final id = p['match_id'];
    final cb = widget.onOpenMatch;
    return id == null || cb == null ? null : () => cb('$id');
  }

  @override
  Widget build(BuildContext context) {
    final today = DateTime.now();
    final todays = (history ?? const <JsonMap>[]).where((r) {
      final d = dateValue(r['kickoff_utc'])?.toLocal();
      return d != null && _sameDay(d, today);
    }).toList();
    final todayWon = todays.where((r) => r['outcome'] == 'win').length;
    return MarketScaffold(
      title: widget.family.localTitle,
      color: widget.color,
      today: history == null ? null : PublishedRecord(todays.length, todayWon),
      overall: widget.record,
      todayCount: widget.upcoming.length + widget.locked.length,
      onLines: () => showLinesSheet(
        context,
        widget.family,
        widget.minimum,
        widget.color,
      ),
      todayTab: _todayTab(context),
      historyTab: _historyTab(context),
    );
  }

  Widget _todayTab(BuildContext context) {
    if (widget.upcoming.isEmpty && widget.locked.isEmpty) {
      return marketEmptyState(context.l10n.mdEmptyToday);
    }
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
      children: [
        for (final p in widget.upcoming)
          MarketPickCard(
            color: widget.color,
            data: MarketPick(
              home: '${p['local'] ?? '—'}',
              away: '${p['visitante'] ?? '—'}',
              homeAvatar: _crest(p, 'local'),
              awayAvatar: _crest(p, 'visitante'),
              kickoff: p['kickoff_utc'],
              pick: pickText(p),
              probability: (p['prob'] as num?)?.toDouble(),
              price: _price(p['ref_price'] ?? p['price']),
              book: p['ref_book'] ?? p['book'],
              onTap: _open(p),
            ),
          ),
        for (final p in widget.locked)
          MarketLockedCard(
            kickoff: p['kickoff_utc'],
            home: '${p['local'] ?? '—'}',
            away: '${p['visitante'] ?? '—'}',
            homeAvatar: _crest(p, 'local'),
            awayAvatar: _crest(p, 'visitante'),
            onTap: widget.onVip,
          ),
      ],
    );
  }

  static double? _price(Object? v) => v is num && v.isFinite && v > 1 ? v.toDouble() : null;

  Widget _historyTab(BuildContext context) {
    if (error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            liveText(error!, color: liveMuted),
            const SizedBox(height: 12),
            TextButton(
              onPressed: _load,
              child: Text(context.l10n.commonRetry),
            ),
          ],
        ),
      );
    }
    final rows = history;
    if (rows == null) return const Center(child: CircularProgressIndicator());
    if (rows.isEmpty) {
      return marketEmptyState(context.l10n.mdEmptyHistory);
    }
    final children = <Widget>[];
    String? current;
    for (final p in rows) {
      final d = dateValue(p['kickoff_utc'])?.toLocal();
      final label = d == null ? context.l10n.mdNoDate : marketDayLabel(d);
      if (label != current) {
        current = label;
        children.add(marketDayChip(label));
      }
      // En córners el resultado relevante son los córners, no los goles.
      final isCorners = '${p['market']}'.startsWith('corners');
      final hh = isCorners ? p['home_corners'] : p['home_goals'];
      final aa = isCorners ? p['away_corners'] : p['away_goals'];
      final hasScore = hh is num && aa is num;
      children.add(
        MarketPickCard(
          color: widget.color,
          data: MarketPick(
            home: '${p['local'] ?? '—'}',
            away: '${p['visitante'] ?? '—'}',
            homeAvatar: _crest(p, 'local'),
            awayAvatar: _crest(p, 'visitante'),
            pick: pickText(p),
            probability: (p['prob'] as num?)?.toDouble(),
            price: _price(p['ref_price'] ?? p['price']),
            book: p['ref_book'] ?? p['book'],
            outcome: p['outcome'] == 'win' ? 'win' : 'loss',
            score: hasScore ? '$hh-$aa' : null,
            scoreNote: hasScore && isCorners
                ? context.l10n.mdCornersTotal(hh + aa)
                : null,
            onTap: _open(p),
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
    final l10n = context.l10n;
    final (label, tone) = supported
        ? (l10n.mdLineConfirmed, liveGreen)
        : !line.deployed
        ? (l10n.mdLineNotDeployed, liveGold)
        : line.cases < minimum
        ? (l10n.mdLineShort, liveGold)
        : (l10n.mdLineReview, liveMuted);
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                liveText(line.localLabel, size: 13, bold: true),
                liveText(casesLabel(line.cases), size: 10, color: liveMuted),
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
            liveText(family.localTitle, size: 18, bold: true, color: color),
            const SizedBox(height: 6),
            liveText(family.localSubtitle, size: 12, color: liveMuted),
            const SizedBox(height: 14),
            for (final line in family.lines) row(line),
          ],
        ),
      ),
    ),
  );
}
