import 'live_api.dart';
import 'market_catalog.dart' show PublishedRecord;

/// Mismo inicio y fecha local que `frontend/sports-data.js::HISTORY_SINCE`.
const publishedHistorySince = '2026-10-26';

bool inPublishedHistory(DateTime start) =>
    !start.toLocal().isBefore(DateTime(2026, 10, 26));

PublishedRecord historyRecord(Iterable<JsonMap> rows) {
  final decided = rows.where(
    (r) => r['outcome'] == 'win' || r['outcome'] == 'loss',
  );
  return PublishedRecord(
    decided.length,
    decided.where((r) => r['outcome'] == 'win').length,
  );
}

/// Igual que el historial web: Alta probabilidad + Destacados. Se conservan las
/// publicaciones de ambos productos, incluso si coinciden en un mismo contrato.
/// Un fallo de cualquiera de las fuentes es un fallo de carga, nunca un cero.
Future<List<JsonMap>> loadFootballHistory(QuantFutApi api) async {
  final bodies = await Future.wait([
    api.request('/mobile/v1/markets/history', query: {'limit': 500}),
    api.request(
      '/mobile/v1/markets/destacados',
      query: {'desde': publishedHistorySince},
    ),
  ]);
  final rows = <JsonMap>[];
  for (final body in bodies) {
    if (body is! Map || body['items'] is! List) {
      throw const ApiFailure.kind(ApiError.invalidResponse);
    }
    for (final r in jsonRows(body['items'])) {
      final start = DateTime.tryParse('${r['kickoff_utc']}');
      if (start != null &&
          inPublishedHistory(start) &&
          (r['outcome'] == 'win' || r['outcome'] == 'loss') &&
          r['local'] is String &&
          (r['local'] as String).isNotEmpty &&
          r['visitante'] is String &&
          (r['visitante'] as String).isNotEmpty) {
        rows.add(r);
      }
    }
  }
  rows.sort(
    (a, b) =>
        DateTime.parse('${b['kickoff_utc']}')
            .compareTo(DateTime.parse('${a['kickoff_utc']}')),
  );
  return rows;
}
