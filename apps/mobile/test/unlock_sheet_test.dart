import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/live_widgets.dart';
import 'package:gobet/product/qf_unlock_sheet.dart';

Future<void> _pump(
  WidgetTester tester,
  Widget body, {
  Size size = const Size(390, 844),
  String code = 'es',
}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await AppLocale.instance.select(code);
  await tester.pumpWidget(
    MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      locale: AppLocale.instance.locale,
      theme: liveTheme(),
      home: Scaffold(
        body: SingleChildScrollView(
          child: body,
        ),
      ),
    ),
  );
  await tester.pump();
}

void main() {
  setUpAll(() async {
    for (final f in {
      'Gilroy Medium': 'fonts/Gilroy-Medium.ttf',
      'Gilroy Bold': 'fonts/Gilroy-Bold.otf',
      'MaterialIcons': 'fonts/MaterialIcons-Regular.otf',
      'Exo 2': 'fonts/Exo2-Regular.ttf',
      'Rajdhani': 'fonts/Rajdhani-Bold.ttf',
      'JetBrains Mono': 'fonts/JetBrainsMono-Bold.ttf',
    }.entries) {
      await (FontLoader(f.key)..addFont(rootBundle.load(f.value))).load();
    }
  });

  tearDown(() async {
    await AppLocale.instance.select('es');
  });

  final samplePick = <String, dynamic>{
    'local': 'Flamengo',
    'visitante': 'Atlético-PR',
    'liga': {'nombre': 'Brasileirão'},
    'kickoff_utc': '2026-11-15T19:30:00Z',
    'texto': 'Doble oportunidad 1X',
    'stream': 'alta_probabilidad',
    'pick_key': 'flamengo_atletico',
    'match_id': 'match-123',
  };

  testWidgets('QfUnlockSheet con saldo suficiente muestra variante con saldo y confirma', (tester) async {
    var unlockCalls = 0;
    var earnCalls = 0;
    var vipCalls = 0;

    await _pump(
      tester,
      QfUnlockSheet(
        pick: samplePick,
        cost: 40,
        saldo: 120,
        monthlyPrice: r'$99.92',
        onUnlock: () async => unlockCalls++,
        onEarnCoins: () => earnCalls++,
        onVip: () => vipCalls++,
      ),
    );

    // Titular y subtítulo
    expect(find.text('DESBLOQUEAR PRONÓSTICO'), findsOneWidget);
    expect(find.text('Se abre al instante'), findsOneWidget);

    // Tarjeta del partido
    expect(find.text('Flamengo – Atlético-PR'), findsOneWidget);
    expect(find.text('VIP'), findsOneWidget);

    // 3 viñetas de valor
    expect(find.text('El pronóstico, su probabilidad y la cuota'), findsOneWidget);
    expect(find.text('Análisis, cara a cara y alertas del partido'), findsOneWidget);
    expect(find.text('Se queda abierto para este partido'), findsOneWidget);

    // Caja de costo y saldo
    expect(find.text('COSTO'), findsOneWidget);
    expect(find.text('TU SALDO'), findsOneWidget);
    expect(find.text('120'), findsOneWidget);
    expect(find.text('Te quedarán 80 monedas'), findsOneWidget);

    // Botón verde con ValueKey('unlock-confirm')
    final confirmBtn = find.byKey(const ValueKey('unlock-confirm'));
    expect(confirmBtn, findsOneWidget);
    expect(find.text('DESBLOQUEAR · 40 MONEDAS'), findsOneWidget);

    // Tarjeta VIP
    expect(find.text('O desbloquea todos con VIP'), findsOneWidget);
    expect(find.text('Sin gastar monedas · desde \$99.92 al mes'), findsOneWidget);

    // Aviso legal al pie
    expect(find.text('Las monedas se ganan dentro de la app. No se cobra dinero.'), findsOneWidget);

    // Tap en botón verde llama a onUnlock
    await tester.tap(confirmBtn);
    await tester.pump();
    expect(unlockCalls, 1);
    expect(earnCalls, 0);
    expect(vipCalls, 0);
  });

  testWidgets('QfUnlockSheet sin saldo suficiente muestra variante sin saldo y atajos', (tester) async {
    var unlockCalls = 0;
    var earnCalls = 0;
    var vipCalls = 0;

    await _pump(
      tester,
      QfUnlockSheet(
        pick: samplePick,
        cost: 40,
        saldo: 20,
        monthlyPrice: r'$99.92',
        onUnlock: () async => unlockCalls++,
        onEarnCoins: () => earnCalls++,
        onVip: () => vipCalls++,
      ),
    );

    // Titular y subtítulo sin saldo
    expect(find.text('TE FALTAN 20 MONEDAS'), findsOneWidget);
    expect(find.text('Gana monedas en unos minutos o hazte VIP'), findsOneWidget);

    // Caja de costo y saldo muestra comparación
    expect(find.text('Necesitas 40 · tienes 20'), findsOneWidget);

    // 3 atajos visibles
    expect(find.text('+5'), findsOneWidget);
    expect(find.text('VER UN VIDEO'), findsOneWidget);
    expect(find.text('+10'), findsOneWidget);
    expect(find.text('ASISTENCIA'), findsOneWidget);
    expect(find.text('+200'), findsOneWidget);
    expect(find.text('OFERTAS'), findsOneWidget);

    // Botón ganar monedas con ValueKey('need-coins-go')
    final earnBtn = find.byKey(const ValueKey('need-coins-go'));
    expect(earnBtn, findsOneWidget);
    expect(find.text('GANAR 20 MONEDAS'), findsOneWidget);

    // No debe estar el botón unlock-confirm
    expect(find.byKey(const ValueKey('unlock-confirm')), findsNothing);

    // Tap en botón ganar llama a onEarnCoins
    await tester.tap(earnBtn);
    await tester.pump();
    expect(earnCalls, 1);
    expect(unlockCalls, 0);
  });

  testWidgets('QfUnlockSheet sin precio VIP muestra fallback sin precio', (tester) async {
    await _pump(
      tester,
      QfUnlockSheet(
        pick: samplePick,
        cost: 40,
        saldo: 100,
        monthlyPrice: null,
        onUnlock: () async {},
        onEarnCoins: () {},
        onVip: () {},
      ),
    );

    expect(find.text('O desbloquea todos con VIP'), findsOneWidget);
    expect(find.text('Sin gastar monedas'), findsOneWidget);
  });

  testWidgets('QfUnlockSheet transiciona a sin saldo si onUnlock falla con monedas_insuficientes', (tester) async {
    var unlockAttempts = 0;

    await _pump(
      tester,
      QfUnlockSheet(
        pick: samplePick,
        cost: 40,
        saldo: 50,
        monthlyPrice: r'$14.99',
        onUnlock: () async {
          unlockAttempts++;
          throw const ApiFailure('Saldo insuficiente', 400, 'monedas_insuficientes');
        },
        onEarnCoins: () {},
        onVip: () {},
      ),
    );

    // Inicia en modo con saldo
    expect(find.byKey(const ValueKey('unlock-confirm')), findsOneWidget);
    expect(find.text('DESBLOQUEAR PRONÓSTICO'), findsOneWidget);

    // Tap en desbloquear dispara fallo y cambia a modo sin saldo
    await tester.tap(find.byKey(const ValueKey('unlock-confirm')));
    await tester.pump();

    expect(unlockAttempts, 1);
    expect(find.byKey(const ValueKey('need-coins-go')), findsOneWidget);
    expect(find.text('GANAR 40 MONEDAS'), findsOneWidget);
  });

  testWidgets('QfUnlockSheet funciona en los 6 idiomas soportados', (tester) async {
    for (final (code, expectedTitle) in [
      ('es', 'DESBLOQUEAR PRONÓSTICO'),
      ('en', 'UNLOCK PREDICTION'),
      ('pt', 'DESBLOQUEAR PALPITE'),
      ('fr', 'DÉBLOQUER LE PRONOSTIC'),
      ('it', 'SBLOCCA PRONOSTICO'),
      ('de', 'PROGNOSE FREISCHALTEN'),
    ]) {
      await _pump(
        tester,
        QfUnlockSheet(
          pick: samplePick,
          cost: 40,
          saldo: 100,
          monthlyPrice: r'$10',
          onUnlock: () async {},
          onEarnCoins: () {},
          onVip: () {},
        ),
        code: code,
      );

      expect(find.text(expectedTitle), findsOneWidget, reason: 'Failed for language $code');
    }
  });

  testWidgets('QfUnlockSheet responsivo a 390x844 y 360x800 sin desbordamiento', (tester) async {
    for (final size in [const Size(390, 844), const Size(360, 800), const Size(320, 640)]) {
      await _pump(
        tester,
        QfUnlockSheet(
          pick: samplePick,
          cost: 40,
          saldo: 20,
          monthlyPrice: r'$14.99',
          onUnlock: () async {},
          onEarnCoins: () {},
          onVip: () {},
        ),
        size: size,
      );

      expect(tester.takeException(), isNull);
      expect(find.text('TE FALTAN 20 MONEDAS'), findsOneWidget);
      expect(find.byKey(const ValueKey('need-coins-go')), findsOneWidget);
    }
  });
}
