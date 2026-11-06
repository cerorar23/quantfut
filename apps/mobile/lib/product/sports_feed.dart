import 'featured_rule.dart';
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
    this.rowPlayerId,
    this.line,
    this.outcome,
    this.side,
    this.team,
    this.price,
    this.book,
    this.quotedAt,
    this.publishable,
  });

  final String id, label, selection;
  final double probability;
  final String? market, player, playerId;

  /// `player_id` CRUDO de la fila de la cohorte (en `team_points` es el id del EQUIPO). Solo sirve para
  /// unir la cuota de referencia (`sports_quotes.dart`); no se muestra ni cambia `playerId`.
  final String? rowPlayerId;
  final double? line;

  /// Instante en que se selló el pronóstico.
  final DateTime sealedAt;

  /// Solo cuenta como pronóstico previo lo sellado antes del inicio.
  final bool eligible;

  /// `win`, `loss`, `push` o null mientras no haya resultado válido.
  final String? outcome;

  /// NBA v2: lado del pronóstico (`over`/`under` o `local`/`visit`) y equipo al que se refiere.
  final String? side, team;

  /// Cuota de la casa que ya viene con el mercado (NBA v2: recibida antes del sello) y su casa y hora de recepción.
  final double? price;
  final String? book;
  final DateTime? quotedAt;

  /// NBA v2: el servidor dice si el mercado cumple la regla de publicación (`publicable`); null = no lo dijo.
  final bool? publishable;
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
    this.plannedSeal,
    this.serverFeatured = false,
    this.featuredId,
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

  /// Hora prevista del sellado del pronóstico (NBA v2); null si la API no la da.
  final DateTime? plannedSeal;

  /// El servidor mandó el campo `destacado` (probabilidad máxima segura): `featuredId` es el id del mercado elegido o
  /// null si ninguno cumple la regla. Si no lo mandó, el destacado se calcula en la app con la misma regla.
  final bool serverFeatured;
  final String? featuredId;

  /// Mismo partido con otra lista de mercados (NBA: la v2 completa de `/nba/v1/partido/{id}/mercados`).
  SportEvent withMarkets(List<SportMarket> value, {String? featured, bool serverFeaturedField = false}) =>
      SportEvent(
        id: id,
        sport: sport,
        home: home,
        away: away,
        league: league,
        start: start,
        status: status,
        seal: seal,
        sealedAt: sealedAt,
        markets: value,
        surface: surface,
        score: score,
        availability: availability,
        plannedSeal: plannedSeal,
        serverFeatured: serverFeaturedField || serverFeatured,
        featuredId: serverFeaturedField ? featured : featuredId,
      );
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

/// Formato de la v1 de NBA (`/nba/api/data`, retirada el 3-nov-2026). Ya no se pide; queda para leer los fixtures
/// históricos de las pruebas.
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
            player: isPlayer && row['player'] is String
                ? row['player'] as String
                : null,
            playerId: isPlayer && row['player_id'] != null
                ? '${row['player_id']}'
                : null,
            rowPlayerId: row['player_id'] != null
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

/// Partidos de la API v2 de NBA (`/nba/v1/cartelera`). Un partido sin pronóstico sellado sale igual, con la lista de
/// mercados vacía y la hora prevista del sellado (`plannedSeal`): la ficha explica cuándo llegará. Con pronóstico, el
/// ganador se presenta con el lado y la probabilidad publicados; un sello posterior al inicio es una revisión y no
/// cuenta como pronóstico previo. Un pronóstico mal formado se trata como ausente: no se inventa nada.
List<SportEvent> nbaV2Events(Iterable<JsonMap> games) {
  final events = <String, SportEvent>{};
  for (final game in games) {
    final id = game['id'];
    final home = jsonMap(game['local']), away = jsonMap(game['visitante']);
    final start = _stamp(game['inicio_utc']);
    if (id is! int ||
        !_text(home['nombre']) ||
        !_text(away['nombre']) ||
        start == null) {
      continue;
    }
    final pick = jsonMap(game['pronostico']);
    final sealed = _stamp(pick['sellado_en']);
    final pLocal = pick['p_local'];
    final valid = sealed != null && _text(pick['hash']) && _probability(pLocal);
    final result = jsonMap(game['resultado']);
    final homePoints = result['local'], awayPoints = result['visitante'];
    final finished = homePoints is num && awayPoints is num;
    final markets = <SportMarket>[];
    if (valid) {
      final p = (pLocal as num).toDouble();
      final homePick = p >= .5;
      final eligible = sealed.isBefore(start);
      String? outcome;
      if (eligible && finished) {
        outcome = (homePoints > awayPoints) == homePick ? 'win' : 'loss';
      }
      markets.add(
        SportMarket(
          id: 'winner-$id',
          label: 'Ganador del partido', // l10n-ignore: nombre del mercado como dato; la familia se traduce por `market`
          selection: (homePick ? home['nombre'] : away['nombre']) as String,
          probability: homePick ? p : 1 - p,
          sealedAt: sealed,
          eligible: eligible,
          outcome: outcome,
          market: 'winner',
        ),
      );
    }
    final key = '$id';
    events[key] = SportEvent(
      id: key,
      sport: SportKind.nba,
      home: home['nombre'] as String,
      away: away['nombre'] as String,
      league: 'NBA',
      start: start,
      status: finished
          ? 'finished'
          : start.add(const Duration(hours: 4)).isBefore(DateTime.now().toUtc())
          ? 'awaiting_result'
          : 'scheduled',
      markets: markets,
      sealedAt: valid ? sealed : start,
      seal: valid ? pick['hash'] as String : '',
      score: finished ? '$homePoints – $awayPoints' : null,
      plannedSeal: _stamp(game['sello_previsto']),
    );
  }
  return events.values.toList()..sort((a, b) => a.start.compareTo(b.start));
}

/// Banda de probabilidad de un pronóstico publicable en los mercados de NBA y tenis (la misma del radar NBA del
/// servidor, `apps/nba/src/nba/api/mercados.py`). El modelo da probabilidad para los DOS lados de cada línea y para
/// líneas muy lejanas (0,99 a cuota 26): fuera de esta banda no es un pronóstico útil.
const sportBandMin = .60, sportBandMax = .95;

bool inSportBand(double probability) =>
    probability >= sportBandMin && probability <= sportBandMax;

const _nbaGameFamilies = {
  'winner',
  'handicap',
  'game_total',
  'team_points',
  'player_points',
  'player_rebounds',
  'player_assists',
  'player_threes',
};

double? _finiteNum(Object? v) => v is num && v.isFinite ? v.toDouble() : null;

/// Mercados de un partido de NBA de `/nba/v1/partido/{id}/mercados` (los 8 que el motor sella, con su cuota y casa).
/// El servidor manda los DOS lados de cada línea: aquí queda el lado del pronóstico (el de mayor probabilidad) y,
/// salvo el ganador y el destacado del servidor, solo lo que cae en [inSportBand]. Una fila mal formada se descarta;
/// nunca se completa ni se inventa un dato. Lanza [FormatException] si la respuesta no es de ese partido.
List<SportMarket> nbaGameMarkets(JsonMap data, SportEvent event) {
  final raw = data['markets'];
  if ('${data['partido_id']}' != event.id || raw is! List) {
    throw const FormatException('NBA markets unavailable');
  }
  final featured = jsonMap(data['destacado'])['id'];
  final scores = (event.score ?? '')
      .split('–')
      .map((x) => num.tryParse(x.trim()))
      .toList();
  final finished =
      event.status == 'finished' &&
      scores.length == 2 &&
      scores.every((x) => x != null);
  final best = <String, SportMarket>{};
  for (final row in jsonRows(raw)) {
    final market = row['market'], side = row['side'], id = row['id'];
    final sealed = _stamp(row['sealed_at']);
    final p = _finiteNum(row['probability']);
    if (market is! String ||
        !_nbaGameFamilies.contains(market) ||
        side is! String ||
        id is! String ||
        sealed == null ||
        p == null ||
        p <= 0 ||
        p >= 1) {
      continue;
    }
    final team = row['team'] is String ? row['team'] as String : null;
    final line = _finiteNum(row['line']);
    final isPlayer = market.startsWith('player_');
    final winner = market == 'winner';
    final sides = winner || market == 'handicap'
        ? const {'local', 'visit'}
        : const {'over', 'under'};
    if (!sides.contains(side) ||
        (winner ? team == null : line == null) ||
        (isPlayer && (row['player_id'] is! int || row['player'] is! String))) {
      continue;
    }
    final eligible = sealed.isBefore(event.start);
    var outcome =
        eligible && const {'win', 'loss', 'push'}.contains(row['outcome'])
        ? row['outcome'] as String
        : null;
    if (outcome == null && eligible && finished && line != null && !isPlayer) {
      final home = scores[0]!, away = scores[1]!;
      final num? value = switch (market) {
        'handicap' => (team == event.home ? home - away : away - home) + line,
        'game_total' => home + away,
        'team_points' => team == event.home ? home : away,
        _ => null,
      };
      if (value != null) {
        final threshold = market == 'handicap' ? 0 : line;
        outcome = value == threshold
            ? 'push'
            : ((side == 'under' ? value < threshold : value > threshold)
                  ? 'win'
                  : 'loss');
      }
    }
    final priceRaw = _finiteNum(row['price']);
    final bookRaw = row['book'];
    final book = bookRaw is String && bookRaw.trim().isNotEmpty
        ? bookRaw.trim()
        : null;
    final quoted = priceRaw != null && priceRaw > 1 && book != null;
    final selection = winner
        ? team!
        : market == 'handicap'
        ? '$team ${line! > 0 ? '+' : ''}$line'
        : (team ?? 'Total'); // l10n-ignore
    final pick = SportMarket(
      id: id,
      label: _nbaFamilyLabels[market]!,
      selection: selection,
      probability: p,
      sealedAt: sealed,
      eligible: eligible,
      outcome: outcome,
      market: market,
      player: isPlayer ? row['player'] as String : null,
      playerId: isPlayer ? '${row['player_id']}' : null,
      rowPlayerId: row['player_id'] != null ? '${row['player_id']}' : null,
      line: line,
      side: side,
      team: team,
      price: quoted ? priceRaw : null,
      book: quoted ? book : null,
      quotedAt: quoted ? _stamp(row['odds_at']) : null,
      publishable: row['publicable'] is bool ? row['publicable'] as bool : null,
    );
    // Un pronóstico por línea: el lado de mayor probabilidad (hándicap: `|línea|` junta al local y al visitante).
    final key = winner
        ? 'winner'
        : '$market|${row['player_id'] ?? team}|${market == 'handicap' ? line!.abs() : line}';
    final kept = best[key];
    if (kept == null || p > kept.probability || id == featured) {
      best[key] = pick;
    }
  }
  return [
    for (final m in best.values)
      if (m.publishable == true ||
          m.market == 'winner' ||
          m.id == featured ||
          inSportBand(m.probability))
        m,
  ];
}

// Nombre del mercado como dato; la interfaz lo traduce por `market` (`sportFamilyTitle`).
const _nbaFamilyLabels = {
  'winner': 'Ganador del partido', // l10n-ignore
  'handicap': 'Hándicap', // l10n-ignore
  'game_total': 'Total del partido', // l10n-ignore
  'team_points': 'Puntos del equipo', // l10n-ignore
  'player_points': 'Puntos del jugador', // l10n-ignore
  'player_rebounds': 'Rebotes del jugador', // l10n-ignore
  'player_assists': 'Asistencias del jugador', // l10n-ignore
  'player_threes': 'Triples del jugador', // l10n-ignore
};

/// Completa los partidos de NBA con todos sus mercados. El feed base (cartelera) ya se mostró: esto lo enriquece
/// partido a partido, primero los más cercanos a hoy, y avisa en cada tanda. Un partido que falla conserva su ganador.
/// `current` dice si el feed base sigue vigente (un refresco posterior lo invalida).
Future<void> enrichNbaFeed(
  QuantFutApi api,
  SportFeed base, {
  required void Function(SportFeed feed) onUpdate,
  required bool Function() current,
  DateTime? now,
  int parallel = 6,
}) async {
  final clock = (now ?? DateTime.now()).toUtc();
  final events = List<SportEvent>.of(base.events);
  final order = [
    for (var i = 0; i < events.length; i++)
      if (events[i].markets.isNotEmpty) i,
  ]..sort(
    (a, b) => events[a].start
        .difference(clock)
        .abs()
        .compareTo(events[b].start.difference(clock).abs()),
  );
  var next = 0, done = 0;
  Future<void> worker() async {
    while (next < order.length) {
      final i = order[next++];
      final e = events[i];
      try {
        final data = jsonMap(
          await api.request('/nba/v1/partido/${e.id}/mercados'),
        );
        final rows = nbaGameMarkets(data, e);
        if (rows.isNotEmpty) {
          final id = jsonMap(data['destacado'])['id'];
          events[i] = e.withMarkets(
            rows,
            featured: id is String ? id : null,
            serverFeaturedField: data.containsKey('destacado'),
          );
        }
      } catch (_) {
        /* Ese partido se queda con su ganador. */
      }
      if (!current()) return;
      done++;
      if (done % 4 == 0 || done == order.length) {
        onUpdate(SportFeed(ready: true, events: List.of(events)));
      }
    }
  }

  await Future.wait([for (var k = 0; k < parallel; k++) worker()]);
}

/// Pide la cartelera de la API v2 de tres días atrás a tres adelante. Un día que falla no tumba a los demás; solo si
/// fallan todos el feed queda no listo.
Future<SportFeed> _loadNba(QuantFutApi api, DateTime now) async {
  final days = [
    for (var i = -3; i <= 3; i++)
      DateTime(
        now.year,
        now.month,
        now.day + i,
      ).toIso8601String().substring(0, 10),
  ];
  final games = <JsonMap>[];
  var answered = 0;
  await Future.wait([
    for (final day in days)
      () async {
        try {
          final data = jsonMap(
            await api.request('/nba/v1/cartelera', query: {'fecha': day}),
          );
          if (data['partidos'] is! List) return;
          games.addAll(jsonRows(data['partidos']));
          answered++;
        } catch (_) {
          /* Ese día queda fuera. */
        }
      }(),
  ]);
  if (answered == 0) return const SportFeed(ready: false, events: []);
  return SportFeed(ready: true, events: nbaV2Events(games));
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
        serverFeatured: event.containsKey('destacado'),
        featuredId: jsonMap(event['destacado'])['id'] is String
            ? jsonMap(event['destacado'])['id'] as String
            : null,
      ),
    );
  }
  return out;
}

/// Lee el feed del deporte; ante cualquier fallo devuelve un feed no listo.
Future<SportFeed> loadSport(QuantFutApi api, SportKind sport) async {
  try {
    if (sport == SportKind.nba) return await _loadNba(api, DateTime.now());
    final data = jsonMap(
      await api.request(switch (sport) {
        SportKind.tennis => '/web/deportes/tenis',
        SportKind.football ||
        SportKind.nba => throw const FormatException('No public feed'),
      }),
    );
    return SportFeed(ready: true, events: tennisEvents(data));
  } catch (_) {
    return const SportFeed(ready: false, events: []);
  }
}

/// Destacado de NBA y tenis entre los elegibles (sellados antes del inicio). Si el servidor mandó el suyo
/// (probabilidad máxima segura) solo se localiza; si no, se aplica la misma regla con la cuota del modelo (1 ÷ prob.).
SportMarket? featuredMarket(SportEvent e) {
  final eligible = e.markets.where((m) => m.eligible);
  if (e.serverFeatured) {
    for (final m in eligible) {
      if (m.id == e.featuredId) return m;
    }
    return null;
  }
  return bestBySafety<SportMarket>(
    eligible,
    (m) => m.probability,
    (m) => modelPrice(m.probability),
  );
}
