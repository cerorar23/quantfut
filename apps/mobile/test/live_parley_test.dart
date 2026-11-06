import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/intl.dart';
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

/// Fecha de un día anterior como la enseña la app (idioma actual, no «2026-10-11»).
String dayText(String iso) =>
    toBeginningOfSentenceCase(localDate(DateFormat.yMMMEd, DateTime.parse(iso)));

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
    // Las reglas van en una línea corta y la explicación completa en una hoja.
    expect(find.text('Hasta 2 parlays · cuota 1,90–5,00'), findsOneWidget);
    expect(find.text('1 gratis al día'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('parley-rules-button')));
    await tester.pumpAndSettle();
    expect(find.text('Cómo se elige un parley'), findsWidgets);
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
    expect(find.text(dayText('2026-10-11')), findsOneWidget);
    expect(find.textContaining('1/2 acertados'), findsOneWidget);
    expect(find.text('1 gratis al día'), findsOneWidget);
    expect(find.text('Historial del Parley'), findsNothing);
    expect(find.textContaining('prometido'), findsNothing);
  });

  testWidgets('días anteriores: solo los últimos 7 parlays', (tester) async {
    Map<String, dynamic> day(String dia, int n) => {
      'dia': dia,
      'tickets': [
        for (var i = 0; i < n; i++)
          {'escalon': i + 1, 'outcome': i.isEven ? 'ganado' : 'perdido'},
      ],
    };
    await open(tester, {
      'activo': true,
      'reglas': rules,
      'resumen': {
        'total': {'n': 15, 'aciertos': 7},
      },
      'dias': [
        day('2026-10-21', 1),
        day('2026-10-20', 4),
        day('2026-10-19', 5),
        day('2026-10-18', 5),
      ],
    });
    expect(find.text('Días anteriores'), findsOneWidget);
    expect(find.text(dayText('2026-10-20')), findsOneWidget);
    expect(find.textContaining('4 parlays'), findsOneWidget);
    expect(find.text(dayText('2026-10-19')), findsOneWidget);
    expect(find.textContaining('3 parlays'), findsOneWidget);
    expect(find.text(dayText('2026-10-18')), findsNothing);
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

  testWidgets('parley v2: lote sellado con tenis y NBA, sin inventar probabilidad en un solo partido', (tester) async {
    Map<String, dynamic> pata(String market, String sel, num? line, {String? jugador, String deporte = 'tenis'}) => {
          'deporte': deporte, 'market': market, 'selection': sel, 'line': line, 'jugador': jugador,
          'local': 'Ana', 'visitante': 'Eva', 'kickoff_utc': '2026-11-07T14:00:00Z', 'texto': 'x',
          'prob': 0.6, 'price': 1.9, 'book': 'bet365', 'outcome': null,
        };
    await open(tester, {
      'activo': true, 'reglas': rules, 'dias': [], 'resumen': {'total': {'n': 0}},
      'v2': {
        'dias': [
          {
            'dia': '2026-11-07', 'chain_sha256': 'a' * 64,
            'tickets': [
              {'escalon': 1, 'target': 2.1, 'tipo': 'multievento', 'estado': 'publicado', 'n_patas': 2, 'cuota_total': 2.07,
               'prob_total': 0.47, 'locked': false, 'outcome': null,
               'patas': [pata('total_games', 'over', 22.5), pata('player_points', 'under', 24.5, jugador: 'A. Jugador', deporte: 'nba')]},
              {'escalon': 2, 'target': 3.1, 'tipo': 'same_game', 'estado': 'solo_referencia', 'n_patas': 2, 'cuota_total': 3.0,
               'prob_total': null, 'locked': false, 'outcome': null, 'patas': [pata('handicap_games', 'home', -3.5)]},
            ],
          },
        ],
      },
    });
    expect(find.text('Parley v2 · fútbol, tenis y NBA'), findsOneWidget);
    expect(find.text('Más de 22,5 juegos'), findsOneWidget);
    expect(find.text('A. Jugador: menos de 24,5 puntos'), findsOneWidget);
    expect(find.textContaining('juegos'), findsNWidgets(2));
    expect(find.textContaining('Un solo partido · Solo referencia'), findsOneWidget);
  });
}
