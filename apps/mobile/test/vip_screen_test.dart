import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/live_vip.dart';
import 'package:gobet/product/live_widgets.dart';
import 'package:gobet/product/store_purchases.dart';

class FakeVipApi extends QuantFutApi {
  FakeVipApi({this.plusUser = false, this.signedInUser = true})
      : super(base: Uri.parse('https://example.invalid'));

  final bool plusUser;
  final bool signedInUser;

  @override
  bool get plus => plusUser;

  @override
  bool get signedIn => signedInUser;

  @override
  Future<void> updateAccount() async {}
}

JsonMap buildVipData({List<JsonMap>? plans}) => {
      'config': {
        'features': {
          'compras': {'enabled': false, 'message': 'Compras en preparación'},
        },
      },
      'alta_probabilidad': {
        'historial': {
          'n': 120,
          'aciertos': 96,
          'acierto_real': 80.0,
          'ayer': {'aciertos': 16, 'fallos': 5},
          'dias': [
            {'aciertos': 22, 'fallos': 6},
            {'aciertos': 46, 'fallos': 10},
            {'aciertos': 50, 'fallos': 10},
            {'aciertos': 8, 'fallos': 2},
            {'aciertos': 18, 'fallos': 6},
            {'aciertos': 24, 'fallos': 8},
            {'aciertos': 40, 'fallos': 8},
          ],
        },
        'proximos': [
          {'match_id': 'm1'},
          {'match_id': 'm2'},
        ],
      },
      'plans': plans ??
          [
            {
              'plan_code': 'mes',
              'name': 'Mensual',
              'price_cents': 25900,
              'currency': 'MXN',
              'duration_days': 30,
            },
            {
              'plan_code': 'tri',
              'name': '3 Meses',
              'price_cents': 54900,
              'currency': 'MXN',
              'duration_days': 90,
            },
            {
              'plan_code': 'anio',
              'name': 'Anual',
              'price_cents': 119900,
              'currency': 'MXN',
              'duration_days': 365,
            },
          ],
    };

Future<void> pumpVip(
  WidgetTester tester, {
  required QuantFutApi api,
  required JsonMap data,
  StoreController? store,
  String lang = 'es',
  Size size = const Size(390, 844),
}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  await AppLocale.instance.select(lang);
  await tester.pumpWidget(
    MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      locale: AppLocale.instance.locale,
      theme: liveTheme(),
      home: LiveVipScreen(
        api: api,
        data: data,
        store: store,
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  tearDown(() => AppLocale.instance.reset());

  testWidgets('3 planes: preselecciona el más largo, muestra ahorro y equivalencias', (tester) async {
    final api = FakeVipApi();
    addTearDown(api.dispose);

    await pumpVip(tester, api: api, data: buildVipData());

    expect(find.text('ACCESO VIP'), findsOneWidget);
    expect(find.textContaining('TODOS LOS PRONÓSTICOS DE HOY'), findsOneWidget);
    expect(find.text('AYER'), findsOneWidget);
    expect(find.text('7 DÍAS'), findsOneWidget);
    expect(find.text('ELIGE TU PLAN'), findsOneWidget);

    // Los 3 planes aparecen como filas
    expect(find.text('MENSUAL'), findsOneWidget);
    expect(find.text('3 MESES'), findsOneWidget);
    expect(find.text('ANUAL'), findsOneWidget);

    // Precios del servidor (con 2 decimales según decimalText)
    expect(find.text(r'$259,00'), findsOneWidget);
    expect(find.text(r'$549,00'), findsOneWidget);
    expect(find.text(r'$1199,00'), findsOneWidget);

    // Insignia de ahorro en planes multi-mes contra el mensual
    expect(find.textContaining('AHORRA'), findsWidgets);

    // Botón plegable de comparación Gratis vs VIP
    await tester.scrollUntilVisible(find.text('VER GRATIS VS VIP'), 200);
    expect(find.text('VER GRATIS VS VIP'), findsOneWidget);
    await tester.tap(find.text('VER GRATIS VS VIP'));
    await tester.pumpAndSettle();

    expect(find.text('OCULTAR COMPARACIÓN'), findsOneWidget);
    expect(find.text('GRATIS'), findsOneWidget);
    expect(find.text('VIP'), findsWidgets);
    expect(find.text('10 % del día'), findsOneWidget);

    // Sellos de confianza y FAQs
    await tester.scrollUntilVisible(find.text('PREGUNTAS FRECUENTES'), 200);
    expect(find.text('SELLADO ANTES DEL PARTIDO'), findsOneWidget);
    expect(find.text('CANCELA CUANDO QUIERAS'), findsOneWidget);
    expect(find.text('PREGUNTAS FRECUENTES'), findsOneWidget);

    // Pie fijo con CTA
    expect(find.byKey(const ValueKey('vip-subscribe')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('2 planes: mensual y anual con mejor precio en anual', (tester) async {
    final api = FakeVipApi();
    addTearDown(api.dispose);

    final data = buildVipData(plans: [
      {
        'plan_code': 'mes',
        'name': 'Mensual',
        'price_cents': 2000,
        'currency': 'USD',
        'duration_days': 30,
      },
      {
        'plan_code': 'anio',
        'name': 'Anual',
        'price_cents': 12000,
        'currency': 'USD',
        'duration_days': 365,
      },
    ]);

    await pumpVip(tester, api: api, data: data);

    expect(find.text('MENSUAL'), findsOneWidget);
    expect(find.text('ANUAL'), findsOneWidget);
    expect(find.byKey(const ValueKey('vip-plan-best')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('plan único: sin insignias de comparación relativa', (tester) async {
    final api = FakeVipApi();
    addTearDown(api.dispose);

    final data = buildVipData(plans: [
      {
        'plan_code': 'mes',
        'name': 'Mensual',
        'price_cents': 1500,
        'currency': 'USD',
        'duration_days': 30,
      },
    ]);

    await pumpVip(tester, api: api, data: data);

    expect(find.text('MENSUAL'), findsOneWidget);
    expect(find.textContaining('AHORRA'), findsNothing);
    expect(find.text('★ MEJOR PRECIO'), findsNothing);
    expect(find.byKey(const ValueKey('vip-subscribe')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('sin planes: muestra mensaje vipPlansSoon', (tester) async {
    final api = FakeVipApi();
    addTearDown(api.dispose);

    final data = buildVipData(plans: []);

    await pumpVip(tester, api: api, data: data);

    expect(find.text('Los planes se mostrarán cuando estén disponibles.'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('cuenta VIP activa: muestra botón de comprobación con texto profileRefreshAccess', (tester) async {
    final api = FakeVipApi(plusUser: true);
    addTearDown(api.dispose);

    await pumpVip(tester, api: api, data: buildVipData());

    await tester.scrollUntilVisible(find.text('Actualizar mi acceso'), 200);
    expect(find.text('Actualizar mi acceso'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('tienda no disponible: tocar CTA notifica sin crashear', (tester) async {
    final api = FakeVipApi();
    addTearDown(api.dispose);

    await pumpVip(tester, api: api, data: buildVipData(), store: null);

    final cta = find.byKey(const ValueKey('vip-subscribe'));
    expect(cta, findsOneWidget);
    await tester.tap(cta);
    await tester.pumpAndSettle();

    expect(find.text('Compras en preparación'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('6 idiomas: la pantalla VIP renderiza sin fallos ni desbordes', (tester) async {
    final api = FakeVipApi();
    addTearDown(api.dispose);

    for (final lang in ['es', 'en', 'pt', 'fr', 'it', 'de']) {
      await pumpVip(tester, api: api, data: buildVipData(), lang: lang);
      expect(tester.takeException(), isNull, reason: 'Fallo en idioma $lang');
    }
  });

  testWidgets('responsive: renderiza limpiamente en 390x844, 360x800 y 320x640', (tester) async {
    final api = FakeVipApi();
    addTearDown(api.dispose);

    for (final size in const [Size(390, 844), Size(360, 800), Size(320, 640)]) {
      await pumpVip(tester, api: api, data: buildVipData(), size: size);
      expect(tester.takeException(), isNull, reason: 'Fallo en tamaño $size');
    }
  });
}
