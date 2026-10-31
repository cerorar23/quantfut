import 'live_api.dart';
import 'sports.dart';

/// Adaptadores de los feeds públicos de NBA y tenis. No calculan ni completan
/// pronósticos: solo leen lo ya sellado y publicado (port de `frontend/sports-data.js`).

class SportMarket {
  const SportMarket({
    required this.id,
    required this.label,
    required this.selection,
    required this.probability,
    required this.sealedAt,
    required this.eligible,
    this.market,
    this.player,
    this.playerId,
    this.line,
    this.outcome,
  });

  final String id, label, selection;
  final double probability;
  final String? market, player, playerId;
  final double? line;

  /// Instante en que se selló el pronóstico.
  final DateTime sealedAt;

  /// Solo cuenta como pronóstico previo lo sellado antes del inicio.
  final bool eligible;

  /// `win`, `loss`, `push` o null mientras no haya resultado válido.
  final String? outcome;
}

class SportEvent {
  const SportEvent({
    required this.id,
    required this.sport,
    required this.home,
    required this.away,
    required this.league,
    required this.start,
    required this.status,
    required this.seal,
    required this.sealedAt,
    required this.markets,
    this.surface,
    this.score,
    this.availability,
  });

  final String id;
  final SportKind sport;
  final String home, away, league;
  final String? surface, score;
  final DateTime start;
  final String status;
  final String seal;
  final DateTime sealedAt;
  final List<SportMarket> markets;
  final JsonMap? availability;
}

class SportFeed {
  const SportFeed({required this.ready, required this.events});
  final bool ready;
  final List<SportEvent> events;
}

DateTime? _stamp(dynamic s) =>
    s is String ? DateTime.tryParse(s)?.toUtc() : null;
bool _probability(dynamic p) => p is num && p.isFinite && p > 0 && p < 1;
bool _text(dynamic s) => s is String && s.isNotEmpty;

String _string(dynamic v, String field) {
  if (v is String) return v;
  throw FormatException('Invalid field: $field');
}

List<SportEvent> nbaEvents(JsonMap data) {
  final live = data['live_v13'];
  final raw = live is Map ? live['cohorts'] : null;
  if (raw is! List) throw const FormatException('NBA feed unavailable');
  final events = <String, SportEvent>{};
  String order(JsonMap c) =>
      '${c['recalculated_at_utc'] ?? c['created_at_utc']}';
  final cohorts = jsonRows(raw)..sort((a, b) => order(a).compareTo(order(b)));
  for (final cohort in cohorts) {
    for (final game in jsonRows(cohort['events'])) {
      final tipoff = _stamp(game['tipoff_utc']);
      if (game['status'] == 'validation_hold' ||
          tipoff == null ||
          !_text(game['home_team']) ||
          !_text(game['away_team'])) {
        continue;
      }
      final markets = <SportMarket>[];
      for (final row in jsonRows(cohort['predictions'])) {
        final result = jsonMap(row['result']);
        final sealed = _stamp(row['sealed_at_utc']);
        if (row['event_id'] != game['event_id'] ||
            result['status'] == 'validation_hold' ||
            !_probability(row['probability_over']) ||
            sealed == null) {
          continue;
        }
        final market = _string(row['market'], 'market');
        final p = (row['probability_over'] as num).toDouble();
        final winner = market == 'winner';
        final rawLine = row['line'];
        final line = rawLine is num ? rawLine.toDouble() : null;
        final selection = winner
            ? (p >= .5 ? game['home_team'] : game['away_team']) as String
            // Sin texto de línea: la interfaz compone «Más de {línea}» con l10n a partir de `line`.
            : '${market == 'game_total' ? 'Total' : row['player']}';
        // Un recálculo posterior al salto no se presenta como pronóstico previo ni se cuenta en resultados.
        final eligible =
            row['performance_eligible'] != false && sealed.isBefore(tipoff);
        final actual = result['actual'];
        String? outcome;
        if (eligible && result['status'] == 'evaluated' && actual is num) {
          if (winner) {
            outcome = (actual == 1) == (p >= .5) ? 'win' : 'loss';
          } else if (line != null) {
            // Sin línea numérica no se inventa un resultado.
            outcome = actual == line
                ? 'push'
                : (actual > line ? 'win' : 'loss');
          }
        }
        final isPlayer = market.startsWith('player_');
        markets.add(
          SportMarket(
            // El índice es el de la fila dentro de las filas válidas del evento.
            id: '$market-${row['player_id']}-${markets.length}',
            label: '${row['market_label']}',
            selection: selection,
            probability: winner && p < .5 ? 1 - p : p,
            sealedAt: sealed,
            eligible: eligible,
            outcome: outcome,
            market: market,
            player: isPlayer && row['player'] is String ? row['player'] as String : null,
            playerId: isPlayer && row['player_id'] != null
                ? '${row['player_id']}'
                : null,
            line: line,
          ),
        );
      }
      if (markets.isEmpty) continue;
      final status = game['status'];
      final fin = game['final'];
      final id = '${game['event_id']}';
      events[id] = SportEvent(
        id: id,
        sport: SportKind.nba,
        home: game['home_team'] as String,
        away: game['away_team'] as String,
        league: 'NBA',
        start: tipoff,
        status: status == 'evaluated'
            ? 'finished'
            : status == 'awaiting_result'
            ? 'awaiting_result'
            : 'scheduled',
        markets: markets,
        sealedAt: _stamp(cohort['created_at_utc']) ?? tipoff,
        seal: '${cohort['cohort']}',
        score: fin is Map ? '${fin['home']} – ${fin['away']}' : null,
        availability: game['availability'] is Map
            ? jsonMap(game['availability'])
            : null,
      );
    }
  }
  return events.values.toList()..sort((a, b) => a.start.compareTo(b.start));
}

List<SportEvent> tennisEvents(JsonMap data) {
  final raw = data['events'];
  if (!{'ok', 'partial'}.contains(data['state']) || raw is! List) {
    throw const FormatException('Tennis feed unavailable');
  }
  final out = <SportEvent>[];
  for (final event in jsonRows(raw)) {
    final start = _stamp(event['start']);
    final id = event['id'];
    if (event['sport'] != 'tenis' ||
        id == null ||
        '$id'.isEmpty ||
        !_text(event['home']) ||
        !_text(event['away']) ||
        start == null ||
        !_text(event['seal']) ||
        event['markets'] is! List) {
      continue;
    }
    // Si el feed no trae `sealed_at` válido se usa el inicio (el campo es obligatorio en la app).
    final sealedAt = _stamp(event['sealed_at']) ?? start;
    final markets = [
      for (final m in jsonRows(event['markets']))
        if (_probability(m['probability']))
          SportMarket(
            id: '${m['id']}',
            label: '${m['label']}',
            selection: '${m['selection']}',
            probability: (m['probability'] as num).toDouble(),
            sealedAt: sealedAt,
            // El feed solo publica pronósticos ya sellados.
            eligible: true,
            outcome: m['outcome'] is String ? m['outcome'] as String : null,
          ),
    ];
    if (markets.isEmpty) continue;
    out.add(
      SportEvent(
        id: '$id',
        sport: SportKind.tennis,
        home: event['home'] as String,
        away: event['away'] as String,
        league: '${event['league'] ?? ''}',
        surface: event['surface'] is String ? event['surface'] as String : null,
        score: event['score'] is String ? event['score'] as String : null,
        start: start,
        status: '${event['status'] ?? 'scheduled'}',
        seal: event['seal'] as String,
        sealedAt: sealedAt,
        markets: markets,
      ),
    );
  }
  return out;
}

/// Lee el feed del deporte; ante cualquier fallo devuelve un feed no listo.
Future<SportFeed> loadSport(QuantFutApi api, SportKind sport) async {
  try {
    final data = jsonMap(
      await api.request(switch (sport) {
        SportKind.nba => '/nba/api/data',
        SportKind.tennis => '/web/deportes/tenis',
        SportKind.football => throw const FormatException('No public feed'),
      }),
    );
    final events = sport == SportKind.nba
        ? nbaEvents(data)
        : tennisEvents(data);
    return SportFeed(ready: true, events: events);
  } catch (_) {
    return const SportFeed(ready: false, events: []);
  }
}

/// Mercado de mayor probabilidad entre los elegibles (sellados antes del inicio).
SportMarket? featuredMarket(SportEvent e) {
  SportMarket? best;
  for (final m in e.markets) {
    if (m.eligible && (best == null || m.probability > best.probability)) {
      best = m;
    }
  }
  return best;
}
