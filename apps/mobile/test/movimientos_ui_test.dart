// Pantalla Mis Movimientos: resumen de saldo/ganadas/gastadas,
// historial agrupado por día, ver más/menos y estado vacío.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/live_movimientos.dart';
import 'package:gobet/product/live_widgets.dart';

const languages = ['es', 'en', 'pt', 'fr', 'it', 'de'];

class _Api extends QuantFutApi {
  _Api(this.payload);

  final Map<String, dynamic> payload;
  final calls = <String>[];

  @override
  bool get signedIn => payload['signed_in'] == true;

  @override
  Future<dynamic> request(
    String path, {
    JsonMap? query,
    JsonMap? body,
    bool retry = true,
  }) async {
    calls.add(path);
    return payload;
  }
}

List<JsonMap> testLedger() {
  final now = DateTime.now().toUtc();
  final yesterday = now.subtract(const Duration(days: 1));
  final past = now.subtract(const Duration(days: 4));

  return [
    {
      'delta': -40,
      'kind': 'unlock',
      'created_at': now.toIso8601String(),
    },
    {
      'delta': 10,
      'kind': 'attendance',
      'created_at': now.subtract(const Duration(hours: 2)).toIso8601String(),
    },
    {
      'delta': 5,
      'kind': 'ad',
      'created_at': now.subtract(const Duration(hours: 3)).toIso8601String(),
    },
    {
      'delta': 200,
      'kind': 'offer',
      'created_at': yesterday.toIso8601String(),
    },
    {
      'delta': 50,
      'kind': 'referrer',
      'created_at': yesterday.subtract(const Duration(hours: 1)).toIso8601String(),
    },
    {
      'delta': -40,
      'kind': 'unlock',
      'created_at': yesterday.subtract(const Duration(hours: 3)).toIso8601String(),
    },
    {
      'delta': 20,
      'kind': 'invitee',
      'created_at': past.toIso8601String(),
    },
    {
      'delta': -200,
      'kind': 'reversal',
      'created_at': past.subtract(const Duration(days: 1)).toIso8601String(),
    },
  ];
}

Future<_Api> openMovimientos(
  WidgetTester tester, {
  List<JsonMap>? ledger,
  int balance = 120,
  Size size = const Size(390, 844),
  String code = 'es',
}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await AppLocale.instance.select(code);

  final payload = {
    'signed_in': true,
    'wallet': {'balance': balance},
    'ledger': ledger ?? testLedger(),
  };
  final api = _Api(payload);

  await tester.pumpWidget(
    MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      locale: AppLocale.instance.locale,
      theme: liveTheme(),
      home: MovimientosScreen(
        api: api,
        wallet: {'balance': balance},
        ledger: ledger ?? testLedger(),
      ),
    ),
  );
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 300));
  return api;
}

void main() {
  setUpAll(() async {
    for (final f in {
      'MaterialIcons': 'fonts/MaterialIcons-Regular.otf',
    }.entries) {
      await (FontLoader(f.key)..addFont(rootBundle.load(f.value))).load();
    }
  });
  tearDown(() => AppLocale.instance.reset());

  testWidgets('calcula saldo, ganadas y gastadas sumando el ledger visible', (tester) async {
    // 10 + 5 + 200 + 50 + 20 = 285 ganadas
    // 40 + 40 + 200 = 280 gastadas
    await openMovimientos(tester, balance: 120);

    expect(find.text('SALDO'), findsOneWidget);
    expect(find.text('120'), findsOneWidget);

    expect(find.text('GANADAS'), findsOneWidget);
    expect(find.text('+285'), findsOneWidget);

    expect(find.text('GASTADAS'), findsOneWidget);
    expect(find.text('−280'), findsOneWidget);
  });

  testWidgets('muestra 5 movimientos y al tocar ver más despliega todos', (tester) async {
    await openMovimientos(tester);

    // En inicio muestra 5 de 8 movimientos
    final toggle = find.byKey(const ValueKey('coins-ledger-toggle'));
    expect(toggle, findsOneWidget);
    expect(find.text('VER MÁS'), findsOneWidget);

    // Tocar ver más
    await tester.ensureVisible(toggle);
    await tester.tap(toggle);
    await tester.pump();

    expect(find.text('VER MENOS'), findsOneWidget);
  });

  testWidgets('muestra estado vacío cuando no hay movimientos', (tester) async {
    await openMovimientos(tester, ledger: []);

    expect(find.text('TODAVÍA NO HAY MOVIMIENTOS.'), findsOneWidget);
    expect(find.text('GANAR MONEDAS'), findsOneWidget);
  });

  for (final code in languages) {
    testWidgets('Movimientos se pinta en $code sin desbordes, también en 320 px', (tester) async {
      for (final size in const [Size(390, 844), Size(320, 800)]) {
        await openMovimientos(tester, size: size, code: code);
        expect(tester.takeException(), isNull, reason: '$code $size');
      }
    });
  }
}
