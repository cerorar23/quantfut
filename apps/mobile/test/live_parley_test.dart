import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/live_parley.dart';
import 'package:gobet/l10n/app_locale.dart';

class _Api extends QuantFutApi {
  _Api(this.body, {this.fail = false});
  final dynamic body;
  final bool fail;
  final paths = <String>[];
  @override
  Future<dynamic> request(
    String path, {
    JsonMap? query,
    JsonMap? body,
    bool retry = true,
  }) async {
    paths.add(path);
    if (fail) throw const ApiFailure('sin red');
    return this.body;
  }
}

Future<_Api> open(
  WidgetTester tester,
  dynamic body, {
  bool fail = false,
  VoidCallback? onVip,
}) async {
  final api = _Api(body, fail: fail);
  tester.view.physicalSize = const Size(390, 2400);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      locale: AppLocale.instance.locale,

      home: Scaffold(
        body: SingleChildScrollView(
          child: ParleyTab(api: api, onVip: onVip),
        ),
      ),
    ),
  );
  await tester.pump(const Duration(milliseconds: 300));
  return api;
}

const rules = {
  'escalones': [
    {'escalon': 1, 'cuota_min': 1.9, 'cuota_max': 2.2},
    {'escalon': 5, 'cuota_min': 4.3, 'cuota_max': 5.0},
  ],
};

void main() {
  testWidgets('apagado: lo dice y no inventa parlays', (tester) async {
    final api = await open(tester, {
      'activo': false,
      'reglas': rules,
      'dias': [],
      'resumen': {
        'total': {'n': 0},
      },
    });
    expect(api.paths, ['/parley']);
    expect(find.text('El Parley todavía no está activo'), findsOneWidget);
    expect(find.textContaining('ESCALÓN'), findsNothing);
    expect(find.textContaining('cuota entre 1,90 y 5,00'), findsOneWidget);
  });

  testWidgets('activo sin parlays hoy', (tester) async {
    await open(tester, {
      'activo': true,
      'reglas': rules,
      'dias': [],
      'resumen': {
        'total': {'n': 0},
      },
    });
    expect(find.text('Hoy no hay parlays'), findsOneWidget);
  });

  testWidgets('activo: parlays del día con sus patas y resultados', (
    tester,
  ) async {
    await open(tester, {
      'activo': true,
      'reglas': rules,
      'resumen': {
        'total': {
          'n': 4,
          'aciertos': 1,
          'prob_media': 41.5,
          'acierto_real': 25.0,
        },
      },
      'dias': [
        {
          'dia': '2026-10-12',
          'tickets': [
            {
              'escalon': 1,
              'cuota_total': 2.05,
              'prob_total': .47,
              'n_patas': 2,
              'outcome': null,
              'patas': [
                {
                  'local': 'Pumas',
                  'visitante': 'Cruz Azul',
                  'texto': 'Más de 1,5 goles',
                  'price': 1.3,
                  'prob': .8,
                  'outcome': 'win',
                  'marcador': '2-1',
                  'kickoff_utc': '2026-10-12T01:00:00Z',
                },
                {
                  'local': 'Tigres',
                  'visitante': 'Leon',
                  'texto': 'Gana Tigres',
                  'price': 1.58,
                  'prob': .6,
                  'outcome': null,
                  'kickoff_utc': '2026-10-12T23:00:00Z',
                },
              ],
            },
          ],
        },
        {
          'dia': '2026-10-11',
          'tickets': [
            {
              'escalon': 1,
              'cuota_total': 2.0,
              'prob_total': .5,
              'n_patas': 2,
              'outcome': 'ganado',
              'patas': [],
            },
            {
              'escalon': 2,
              'cuota_total': 2.5,
              'prob_total': .4,
              'n_patas': 2,
              'outcome': 'perdido',
              'patas': [],
            },
          ],
        },
      ],
    });
    expect(find.text('ESCALÓN 1'), findsOneWidget);
    expect(find.text('@2,05'), findsOneWidget);
    expect(find.text('PENDIENTE'), findsOneWidget);
    expect(find.text('Pumas · Cruz Azul'), findsOneWidget);
    expect(find.text('Resultado 2-1'), findsOneWidget);
    expect(find.text('Días anteriores'), findsOneWidget);
    expect(find.text('2026-10-11'), findsOneWidget);
    expect(find.textContaining('1/2 acertados'), findsOneWidget);
    expect(
      find.text('Uno gratis al día (el de menor cuota); el resto, VIP.'),
      findsOneWidget,
    );
    expect(find.text('Historial del Parley'), findsOneWidget);
    expect(
      find.textContaining('25,0 % real frente a 41,5 % prometido'),
      findsOneWidget,
    );
  });

  testWidgets('si falla la carga se ofrece reintentar', (tester) async {
    await open(tester, null, fail: true);
    expect(find.text('No se pudo cargar el Parley.'), findsOneWidget);
    expect(find.text('Reintentar'), findsOneWidget);
  });
  testWidgets(
    'el parley VIP sale bloqueado, sin patas ni cuota exacta, y abre VIP',
    (tester) async {
      var vip = 0;
      await open(tester, {
        'activo': true,
        'reglas': rules,
        'resumen': {
          'total': {'n': 0},
        },
        'dias': [
          {
            'dia': '2026-10-13',
            'tickets': [
              {
                'escalon': 1,
                'locked': false,
                'gratis': true,
                'cuota_total': 1.92,
                'prob_total': .54,
                'n_patas': 2,
                'outcome': null,
                'patas': [
                  {
                    'local': 'Pumas',
                    'visitante': 'Cruz Azul',
                    'texto': 'Más de 1,5 goles',
                    'price': 1.3,
                    'prob': .8,
                    'outcome': null,
                    'kickoff_utc': '2026-10-13T01:00:00Z',
                  },
                ],
              },
              {
                'escalon': 3,
                'locked': true,
                'cuota_min': 2.7,
                'cuota_max': 3.4,
              },
            ],
          },
        ],
      }, onVip: () => vip++);
      expect(find.text('@1,92'), findsOneWidget); // el gratis, abierto
      expect(find.text('ESCALÓN 3'), findsOneWidget);
      expect(find.text('Cuota entre 2,70 y 3,40'), findsOneWidget);
      expect(find.byIcon(Icons.lock_outline), findsOneWidget);
      await tester.tap(find.text('Cuota entre 2,70 y 3,40'));
      expect(vip, 1);
    },
  );
}
