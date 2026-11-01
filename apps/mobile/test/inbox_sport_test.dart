// Avisos: etiqueta de deporte solo si el aviso trae `sport`; sin él no se inventa.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/core/firebase_preferences.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/live_widgets.dart';

class _Api extends QuantFutApi {
  @override
  Future<dynamic> request(String path, {JsonMap? query, JsonMap? body, bool retry = true}) async => {
    'notifications': [
      {'notification_id': 1, 'title': 'Aviso NBA', 'body': 'b', 'sport': 'nba', 'read_at': null},
      {'notification_id': 2, 'title': 'Aviso sin deporte', 'body': 'b', 'read_at': '2026-10-30T10:00:00Z'},
      {'notification_id': 3, 'title': 'Aviso raro', 'body': 'b', 'sport': 'curling'},
    ],
  };
}

void main() {
  tearDown(() => AppLocale.instance.reset());

  testWidgets('solo el aviso con deporte conocido lleva etiqueta', (tester) async {
    await AppLocale.instance.select('es');
    final semantics = tester.ensureSemantics();
    final api = _Api();
    addTearDown(api.dispose);
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: AppLocale.instance.locale,
        theme: liveTheme(),
        home: FirebaseInbox(api: api),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.descendant(of: find.byKey(const ValueKey('inbox-1')), matching: find.text('NBA')), findsOneWidget);
    expect(find.byKey(const ValueKey('inbox-sport-nba')), findsOneWidget);
    expect(find.bySemanticsLabel(RegExp('Deporte: NBA')), findsOneWidget);
    for (final id in [2, 3]) {
      expect(
        find.descendant(of: find.byKey(ValueKey('inbox-$id')), matching: find.byWidgetPredicate((w) => '${w.key}'.contains('inbox-sport'))),
        findsNothing,
        reason: 'aviso $id',
      );
    }
    // Sin leer: campana activa (forma, no solo color).
    expect(
      find.descendant(of: find.byKey(const ValueKey('inbox-1')), matching: find.byIcon(Icons.notifications_active_outlined)),
      findsOneWidget,
    );
    for (final id in [1, 2, 3]) {
      expect(tester.getSize(find.byKey(ValueKey('inbox-$id'))).height, greaterThanOrEqualTo(44));
    }
    semantics.dispose();
  });
}
