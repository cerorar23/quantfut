import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/product/market_catalog.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late MarketCatalog catalog;
  setUpAll(() async {
    catalog = await MarketCatalog.load();
  });

  test('small perfect samples cannot displace supported corner lines', () {
    final market = catalog.byId('corners');
    final tiny = market.lines.singleWhere(
      (line) => line.key == 'corners under 11.5',
    );
    expect(tiny.observed, 100);
    expect(tiny.cases, 19);
    expect(tiny.supported(catalog.minimumCases), isFalse);
    expect(market.bestSupported(catalog.minimumCases)!.key, 'corners over 6.5');
  });

  test(
    'undelployed and experimental evidence cannot become confirmed strengths',
    () {
      final cards = catalog.byId('cards');
      final pending = cards.lines.singleWhere(
        (line) => line.key == 'cards under 5.5',
      );
      expect(pending.passed, isTrue);
      expect(pending.cases, greaterThan(catalog.minimumCases));
      expect(pending.supported(catalog.minimumCases), isFalse);
      expect(
        catalog.byId('nba_winner').bestSupported(catalog.minimumCases),
        isNull,
      );
    },
  );

  test('observed published rates use exact outcomes and handle zero cases', () {
    expect(PublishedRecord(7, 6).observed, closeTo(85.7142857, .00001));
    expect(PublishedRecord(0, 0).observed, isNull);
    expect(() => PublishedRecord(3, 4), throwsFormatException);
    expect(catalog.byId('handicap').published.cases, 21);
    expect(catalog.byId('handicap').published.won, 14);
    expect(catalog.overall.cases, 96);
    expect(catalog.overall.won, 75);
  });
}
