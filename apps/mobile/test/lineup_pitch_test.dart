import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/product/lineup_pitch.dart';
import 'package:gobet/product/live_api.dart';

List<JsonMap> makeTitulares(int count) => [
  for (var i = 1; i <= count; i++)
    {
      'nombre': 'Jugador $i',
      'numero': i,
      'pos': i == 1 ? 'G' : (i <= 5 ? 'D' : (i <= 9 ? 'M' : 'F')),
    },
];

void main() {
  group('PitchPlayer.layoutPlayers', () {
    test('formación 4-3-3 distribuye 11 jugadores en 4 líneas (GK + 4 + 3 + 3)', () {
      final titulares = makeTitulares(11);
      final players = PitchPlayer.layoutPlayers(
        formation: '4-3-3',
        titulares: titulares,
      );

      expect(players.length, 11);
      // Portero (línea 0)
      expect(players[0].name, 'Jugador 1');
      expect(players[0].y, 89.0);
      expect(players[0].x, closeTo(50.0, 0.1));

      // Defensas (línea 1): 4 jugadores
      for (var i = 1; i <= 4; i++) {
        expect(players[i].y, closeTo(89.0 - (76.0 / 3), 0.1));
      }
      expect(players[1].x, closeTo(20.0, 0.1));
      expect(players[4].x, closeTo(80.0, 0.1));

      // Medios (línea 2): 3 jugadores
      for (var i = 5; i <= 7; i++) {
        expect(players[i].y, closeTo(89.0 - 2 * (76.0 / 3), 0.1));
      }
      expect(players[5].x, closeTo(25.0, 0.1));
      expect(players[7].x, closeTo(75.0, 0.1));

      // Delanteros (línea 3): 3 jugadores
      for (var i = 8; i <= 10; i++) {
        expect(players[i].y, closeTo(13.0, 0.1));
      }
    });

    test('formación 4-4-2 distribuye 11 jugadores en 4 líneas (GK + 4 + 4 + 2)', () {
      final titulares = makeTitulares(11);
      final players = PitchPlayer.layoutPlayers(
        formation: '4-4-2',
        titulares: titulares,
      );

      expect(players.length, 11);
      expect(players[0].y, 89.0);
      // Delanteros (2) en y = 13.0
      expect(players[9].y, closeTo(13.0, 0.1));
      expect(players[10].y, closeTo(13.0, 0.1));
      expect(players[9].x, closeTo(33.33, 0.1));
      expect(players[10].x, closeTo(66.66, 0.1));
    });

    test('formación 3-5-2 distribuye 11 jugadores en 4 líneas (GK + 3 + 5 + 2)', () {
      final titulares = makeTitulares(11);
      final players = PitchPlayer.layoutPlayers(
        formation: '3-5-2',
        titulares: titulares,
      );

      expect(players.length, 11);
      // 3 defensas
      expect(players[1].x, closeTo(25.0, 0.1));
      expect(players[3].x, closeTo(75.0, 0.1));
      // 5 medios
      expect(players[4].x, closeTo(16.66, 0.1));
      expect(players[8].x, closeTo(83.33, 0.1));
    });

    test('formación 4-2-3-1 distribuye 11 jugadores en 5 líneas', () {
      final titulares = makeTitulares(11);
      final players = PitchPlayer.layoutPlayers(
        formation: '4-2-3-1',
        titulares: titulares,
      );

      expect(players.length, 11);
      expect(players[0].y, 89.0); // GK
      expect(players[10].y, closeTo(13.0, 0.1)); // 1 delantero centro
      expect(players[10].x, closeTo(50.0, 0.1));
    });

    test('formación 4-3-1-2 distribuye 11 jugadores en 5 líneas', () {
      final titulares = makeTitulares(11);
      final players = PitchPlayer.layoutPlayers(
        formation: '4-3-1-2',
        titulares: titulares,
      );

      expect(players.length, 11);
      expect(players[0].y, 89.0); // GK
      expect(players[8].name, 'Jugador 9'); // Mediapunta (1)
      expect(players[8].x, closeTo(50.0, 0.1));
      expect(players[9].y, closeTo(13.0, 0.1)); // Delantero 1
      expect(players[10].y, closeTo(13.0, 0.1)); // Delantero 2
    });

    test('menos de 11 jugadores se colocan sin errores y no fallan', () {
      final titulares = makeTitulares(7); // Por ejemplo 7 jugadores
      final players = PitchPlayer.layoutPlayers(
        formation: '4-3-3',
        titulares: titulares,
      );

      expect(players.length, 7);
      expect(players[0].name, 'Jugador 1');
      expect(players[6].name, 'Jugador 7');
    });

    test('lista vacía devuelve lista vacía', () {
      final players = PitchPlayer.layoutPlayers(
        formation: '4-3-3',
        titulares: const [],
      );
      expect(players, isEmpty);
    });

    test('soporta claves en inglés de FotMob (name, number) y genera iniciales', () {
      final fotmobPlayer = PitchPlayer.fromJson(
        const {
          'name': 'Dani Fernández',
          'number': 2,
          'player_id': 12345,
          'src': 'fotmob',
        },
        x: 50.0,
        y: 89.0,
      );
      expect(fotmobPlayer.name, 'Dani Fernández');
      expect(fotmobPlayer.number, 2);
      expect(PitchPlayer.initials(fotmobPlayer.name), 'DF');

      final singleNamePlayer = PitchPlayer.fromJson(
        const {
          'name': 'Adilson',
          'number': null,
        },
        x: 20.0,
        y: 50.0,
      );
      expect(singleNamePlayer.name, 'Adilson');
      expect(singleNamePlayer.number, 0);
      expect(PitchPlayer.initials(singleNamePlayer.name), 'AD');
    });
  });

  group('QfPitch widget', () {
    testWidgets('renderiza campo 400 dp con marcas y jugadores', (tester) async {
      final titulares = makeTitulares(11);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SizedBox(
              width: 390,
              child: QfPitch(
                formation: '4-3-1-2',
                titulares: titulares,
              ),
            ),
          ),
        ),
      );

      expect(find.byKey(const ValueKey('qf-pitch')), findsOneWidget);
      expect(find.text('Jugador 1'), findsOneWidget);
      expect(find.text('Jugador 11'), findsOneWidget);
      expect(find.text('1'), findsOneWidget); // Dorsal
      expect(find.text('11'), findsOneWidget); // Dorsal
    });

    testWidgets('renderiza sin desbordes a 320 px y 360 px', (tester) async {
      final titulares = makeTitulares(11);

      for (final width in [320.0, 360.0, 390.0]) {
        tester.view.physicalSize = Size(width, 600);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);

        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: SizedBox(
                width: width,
                child: QfPitch(
                  formation: '4-3-3',
                  titulares: titulares,
                ),
              ),
            ),
          ),
        );
        expect(tester.takeException(), isNull);
      }
    });
  });
}
