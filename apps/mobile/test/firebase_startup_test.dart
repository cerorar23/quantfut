import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/core/firebase_startup.dart';

const content = MaterialApp(home: Scaffold(body: Text('Contenido de la app')));

void main() {
  testWidgets('waits for Firebase before mounting content', (tester) async {
    final initialization = Completer<void>();
    await tester.pumpWidget(
      FirebaseStartup(initialize: () => initialization.future, child: content),
    );
    expect(find.text('Contenido de la app'), findsNothing);
    expect(find.byType(CircularProgressIndicator), findsOneWidget);

    initialization.complete();
    await tester.pumpAndSettle();
    expect(find.text('Contenido de la app'), findsOneWidget);
  });

  testWidgets('initialization errors block content and allow retry', (
    tester,
  ) async {
    var attempts = 0;
    final retry = Completer<void>();
    await tester.pumpWidget(
      FirebaseStartup(
        initialize: () async {
          if (++attempts == 1) throw StateError('private error details');
          await retry.future;
        },
        child: content,
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Contenido de la app'), findsNothing);
    expect(find.textContaining('private error details'), findsNothing);
    expect(find.text('Reintentar'), findsOneWidget);

    await tester.tap(find.text('Reintentar'));
    await tester.pump();
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    expect(find.text('Reintentar'), findsNothing);
    expect(find.text('Contenido de la app'), findsNothing);
    retry.complete();
    await tester.pumpAndSettle();
    expect(attempts, 2);
    expect(find.text('Contenido de la app'), findsOneWidget);
  });

  testWidgets('synchronous configuration error does not open content', (
    tester,
  ) async {
    await tester.pumpWidget(
      FirebaseStartup(
        initialize: () => throw StateError('Configuration unavailable'),
        child: content,
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Contenido de la app'), findsNothing);
    expect(find.text('Reintentar'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
