import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/published_history.dart';

class _Api extends QuantFutApi {
  final calls = <(String, JsonMap?)>[];
  bool failFeatured = false;
  @override
  Future<dynamic> request(
    String path, {
    JsonMap? query,
    JsonMap? body,
    bool retry = true,
  }) async {
    calls.add((path, query));
    if (path.endsWith('/destacados') && failFeatured) {
      throw const ApiFailure('offline');
    }
    JsonMap row(String id, String outcome, String date) => {
      'match_id': id,
      'local': 'A',
      'visitante': 'B',
      'market': 'totals',
      'outcome': outcome,
      'kickoff_utc': date,
    };
    return {
      'items': path.endsWith('/destacados')
          ? [row('featured', 'loss', '2026-11-04T20:00:00Z')]
          : [
              row('alta', 'win', '2026-11-05T20:00:00Z'),
              row('old', 'win', '2026-10-24T20:00:00Z'),
              row('push', 'push', '2026-11-05T20:00:00Z'),
            ],
    };
  }
}

void main() {
  test(
    'fútbol combina ambas fuentes web, con fecha, fallos y sin pushes',
    () async {
      final api = _Api();
      addTearDown(api.dispose);
      final rows = await loadFootballHistory(api);
      expect(rows.map((r) => r['match_id']), ['alta', 'featured']);
      expect(api.calls[0].$1, '/mobile/v1/markets/history');
      expect(api.calls[0].$2, {'limit': 500});
      expect(api.calls[1].$1, '/mobile/v1/markets/destacados');
      expect(api.calls[1].$2, {'desde': '2026-10-26'});
      final record = historyRecord(rows);
      expect(record.cases, 2);
      expect(record.won, 1);
      expect(record.observed, 50);
    },
  );

  test(
    'un fallo de una fuente no se presenta como historial vacío o completo',
    () async {
      final api = _Api()..failFeatured = true;
      addTearDown(api.dispose);
      await expectLater(loadFootballHistory(api), throwsA(isA<ApiFailure>()));
    },
  );

  test('sin resueltos no hay porcentaje ficticio', () {
    final record = historyRecord([
      {'outcome': 'push'},
      {'outcome': null},
    ]);
    expect(record.cases, 0);
    expect(record.observed, isNull);
  });
}
