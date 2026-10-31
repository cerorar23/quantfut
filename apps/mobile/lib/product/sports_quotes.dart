import 'live_api.dart';
import 'sports.dart';
import 'sports_feed.dart';

/// Cuota de referencia (PropLine) de NBA y tenis, leída de `/web/deportes/{nba,tenis}/cuotas`.
/// Nunca entra en el pronóstico sellado: es un overlay que se une por evento y mercado.

class SportQuote {
  const SportQuote({
    required this.price,
    required this.book,
    required this.asOf,
    required this.books,
  });
  final double price;
  final String book;

  /// Recepción de la observación usada (UTC).
  final DateTime asOf;

  /// Casas que respaldan el precio.
  final int books;
}

/// Número de línea como la escribe el servidor (`repr` de Python sin `.0` final): 221.0 -> «221».
String lineKey(double? line) {
  if (line == null || !line.isFinite) return '';
  return line == line.truncateToDouble() ? line.toInt().toString() : '$line';
}

class _EventQuotes {
  const _EventQuotes(this.cohort, this.rows);

  /// Solo NBA: cohorte a la que pertenecen las cuotas (debe ser el `seal` del evento mostrado).
  final String? cohort;

  /// NBA: «mercado|id|línea» -> lado -> cuota. Tenis: id de mercado -> «-» -> cuota.
  final Map<String, Map<String, SportQuote>> rows;
}

SportQuote? _quote(Object? raw) {
  if (raw is! Map) return null;
  final price = raw['price'];
  final book = raw['book'];
  final asOf = raw['as_of'];
  if (price is! num || !price.isFinite || price <= 1) return null;
  if (book is! String || book.isEmpty) return null;
  final stamp = asOf is String ? DateTime.tryParse(asOf)?.toUtc() : null;
  if (stamp == null) return null;
  final books = raw['books'];
  return SportQuote(
    price: price.toDouble(),
    book: book,
    asOf: stamp,
    books: books is num && books.isFinite ? books.toInt() : 0,
  );
}

class QuotesOverlay {
  const QuotesOverlay._(this._sport, this._events);
  static const empty = QuotesOverlay._(null, {});

  final SportKind? _sport;
  final Map<String, _EventQuotes> _events;
  bool get isEmpty => _events.isEmpty;

  /// Tolerante: JSON nulo, listas, tipos raros o `state` distinto de ok/partial -> `empty`; lo ilegible
  /// de una entrada solo descarta esa entrada.
  factory QuotesOverlay.fromJson(SportKind sport, Object? json) {
    try {
      if (json is! Map || sport == SportKind.football) return empty;
      if (!{'ok', 'partial'}.contains(json['state'])) return empty;
      final raw = json['events'];
      if (raw is! Map) return empty;
      final out = <String, _EventQuotes>{};
      raw.forEach((id, value) {
        if (id is! String || value is! Map) return;
        final rows = <String, Map<String, SportQuote>>{};
        if (sport == SportKind.nba) {
          final quotes = value['quotes'];
          if (quotes is Map) {
            quotes.forEach((key, sides) {
              if (key is! String || sides is! Map) return;
              final bySide = <String, SportQuote>{};
              sides.forEach((side, q) {
                final parsed = _quote(q);
                if (side is String && parsed != null) bySide[side] = parsed;
              });
              if (bySide.isNotEmpty) rows[key] = bySide;
            });
          }
          final cohort = value['cohort'];
          if (rows.isNotEmpty && cohort is String) out[id] = _EventQuotes(cohort, rows);
        } else {
          value.forEach((marketId, q) {
            final parsed = _quote(q);
            if (marketId is String && parsed != null) rows[marketId] = {'-': parsed};
          });
          if (rows.isNotEmpty) out[id] = _EventQuotes(null, rows);
        }
      });
      return out.isEmpty ? empty : QuotesOverlay._(sport, out);
    } catch (_) {
      return empty;
    }
  }
}

/// Cuota de referencia del mercado mostrado, o null. Reglas del cliente:
/// - NBA: solo si la cohorte de las cuotas es el `seal` del evento; «Más de» -> `over`;
///   ganador -> `home`/`away` si la selección mostrada es exactamente el local/visitante; si no, nada.
/// - Tenis: por id de mercado (cada id tiene una única selección en el feed).
/// - Una cuota recibida DESPUÉS del sello de la fila mostrada se descarta (no es la del sello).
SportQuote? quoteFor(SportEvent e, SportMarket m, QuotesOverlay overlay) {
  final entry = overlay._events[e.id];
  if (entry == null || overlay._sport != e.sport) return null;
  SportQuote? q;
  if (e.sport == SportKind.nba) {
    final market = m.market;
    if (market == null || entry.cohort != e.seal) return null;
    final key = switch (market) {
      'winner' => 'winner||',
      'game_total' => 'game_total||${lineKey(m.line)}',
      _ => '$market|${m.rowPlayerId ?? ''}|${lineKey(m.line)}',
    };
    final String? side;
    if (market == 'winner') {
      side = m.selection == e.home ? 'home' : (m.selection == e.away ? 'away' : null);
    } else {
      side = 'over';
    }
    if (side == null) return null;
    q = entry.rows[key]?[side];
  } else if (e.sport == SportKind.tennis) {
    q = entry.rows[m.id]?['-'];
  }
  if (q == null || q.asOf.isAfter(m.sealedAt)) return null;
  return q;
}

/// Lee las cuotas del deporte; ante cualquier fallo devuelve `empty` (nunca lanza).
Future<QuotesOverlay> loadQuotes(QuantFutApi api, SportKind sport) async {
  try {
    final path = switch (sport) {
      SportKind.nba => '/web/deportes/nba/cuotas',
      SportKind.tennis => '/web/deportes/tenis/cuotas',
      SportKind.football => null,
    };
    if (path == null) return QuotesOverlay.empty;
    return QuotesOverlay.fromJson(sport, await api.request(path));
  } catch (_) {
    return QuotesOverlay.empty;
  }
}

/// Un refresco vacío (fallo o sin datos) no pisa un overlay bueno anterior.
QuotesOverlay mergeQuotes(QuotesOverlay? current, QuotesOverlay fresh) =>
    fresh.isEmpty && current != null ? current : fresh;
