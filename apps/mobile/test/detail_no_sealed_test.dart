// Sin pronóstico sellado, el aviso de la pestaña Pronósticos explica que los «Mercados del partido»
// de debajo son estimaciones del modelo (abiertas o con candado VIP), en vez de decir que no hay nada.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/live_detail.dart';
import 'package:gobet/product/live_widgets.dart';

Map<String, dynamic> row({required bool locked}) => locked
    ? {'id': 'cards:under:6.5', 'grupo': 'TARJETAS', 'locked': true}
    : {
        'id': 'cards:under:6.5',
        'grupo': 'TARJETAS',
        'titulo': 'Tarjetas totales',
        'market': 'cards',
        'selection': 'under',
        'line': 6.5,
        'seleccion': 'Menos de 6,5 tarjetas',
        'prob': .80,
        'nivel': 'alta',
        'cuota': 1.26,
        'cuota_tipo': 'justa',
        'nota': 'Media esperada: 4,7',
        'locked': false,
      };

class _Api extends QuantFutApi {
  _Api(this.rows);
  final List<Map<String, dynamic>>? rows;

  @override
  Future<JsonMap> detail(String id) async => {
    'config': {
      'features': {
        for (final k in ['agenda', 'alta_probabilidad', 'escalera', 'estadisticas', 'h2h', 'vip'])
          k: {'enabled': true, 'message': ''},
      },
    },
    'picks': <Map<String, dynamic>>[],
    'locked': false,
    'ficha': {
      'partido': {'kickoff_utc': '2099-10-25T20:00:00+00:00', 'liga': {'nombre': 'Liga Profesional'}},
      'local': {'id': 1, 'nombre': 'Independiente'},
      'visitante': {'id': 2, 'nombre': 'Boca Juniors'},
      'mercados': rows == null
          ? null
          : {'filas': rows, 'marcadores': null, 'abiertas': 0, 'total': rows!.length},
    },
  };
}

Future<AppLocalizations> pump(WidgetTester tester, List<Map<String, dynamic>>? rows, {String code = 'es'}) async {
  tester.view.physicalSize = const Size(390, 1800);
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
      home: Scaffold(body: LiveMatchDetail(api: _Api(rows), id: 'm1', onVip: () {})),
    ),
  );
  await tester.pump(const Duration(milliseconds: 500));
  return AppLocale.instance.l10n;
}

void main() {
  tearDown(() => AppLocale.instance.reset());

  testWidgets('con mercados abiertos dice que abajo están las estimaciones del modelo', (tester) async {
    final l10n = await pump(tester, [row(locked: false)]);
    expect(find.text(l10n.detailNoSealedModel), findsOneWidget);
    expect(find.text(l10n.detailNoPicks), findsNothing);
  });

  testWidgets('con todos los mercados con candado lo dice con VIP', (tester) async {
    final l10n = await pump(tester, [row(locked: true)]);
    expect(find.text(l10n.detailNoSealedModelVip), findsOneWidget);
  });

  testWidgets('sin mercados mantiene el aviso de siempre', (tester) async {
    final l10n = await pump(tester, null);
    expect(find.text(l10n.detailNoPicks), findsOneWidget);
    expect(find.text(l10n.detailNoSealedModel), findsNothing);
  });

  for (final code in ['en', 'pt', 'fr', 'it', 'de']) {
    testWidgets('aviso traducido ($code)', (tester) async {
      final l10n = await pump(tester, [row(locked: false)], code: code);
      expect(find.text(l10n.detailNoSealedModel), findsOneWidget);
    });
  }
}
