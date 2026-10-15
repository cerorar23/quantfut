// Tarjeta «Videos con recompensa» en Coins: aviso previo, tope, pausa y sin SDK.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/live_ads.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/live_rewards.dart';
import 'package:gobet/product/live_widgets.dart';

class _Api extends QuantFutApi {
  _Api(this.ads);
  final Map<String, Object?> ads;
  final calls = <String>[];

  @override
  bool get signedIn => true;

  @override
  Future<dynamic> request(
    String path, {
    JsonMap? query,
    JsonMap? body,
    bool retry = true,
  }) async {
    calls.add(path);
    return {
      'settings': {'enabled': true, 'unlock_cost': 100},
      'signed_in': true,
      'providers': <Object>[],
      'wallet': {'balance': 0, 'spendable': 0},
      'ads': ads,
    };
  }
}

class _NoSdk implements RewardedAdGateway {
  @override
  Future<bool> prepare() async => false;

  @override
  Future<AdShow> show({
    required String unitId,
    required String userId,
    required String customData,
  }) async => AdShow.dismissed;
}

Future<void> _pump(
  WidgetTester tester,
  _Api api,
  String language, {
  bool settle = true,
}) async {
  await tester.pumpWidget(
    MaterialApp(
      locale: Locale(language),
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      theme: liveTheme(),
      home: RewardsScreen(api: api, adGateway: _NoSdk()),
    ),
  );
  if (settle) {
    await tester.pumpAndSettle();
  } else {
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));
  }
}

FilledButton _button(WidgetTester tester, String text) =>
    tester.widget<FilledButton>(find.widgetWithText(FilledButton, text));

void main() {
  final on = {
    'enabled': true,
    'coins': 10,
    'daily_cap': 5,
    'cooldown_seconds': 180,
    'used_today': 2,
    'remaining_today': 3,
    'next_at': null,
  };

  for (final language in ['es', 'en', 'pt', 'fr', 'it', 'de']) {
    testWidgets('la tarjeta dice la acción y la recompensa en $language', (
      tester,
    ) async {
      await _pump(tester, _Api(on), language);
      final l10n = lookupAppLocalizations(Locale(language));
      await tester.ensureVisible(find.text(l10n.adsCardTitle));
      expect(find.text(l10n.adsCardTitle), findsOneWidget);
      expect(
        find.widgetWithText(FilledButton, l10n.adsWatchCta(10)),
        findsOneWidget,
      );
      expect(find.text(l10n.adsProgress(2, 5)), findsOneWidget);
      expect(find.text(l10n.adsFootnote), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets('sin anuncios activos no hay tarjeta', (tester) async {
    await _pump(tester, _Api({'enabled': false}), 'es');
    final l10n = lookupAppLocalizations(const Locale('es'));
    expect(find.text(l10n.adsCardTitle), findsNothing);
  });

  testWidgets('con el tope alcanzado el botón queda desactivado y se explica', (
    tester,
  ) async {
    await _pump(
      tester,
      _Api({...on, 'used_today': 5, 'remaining_today': 0}),
      'es',
    );
    final l10n = lookupAppLocalizations(const Locale('es'));
    expect(_button(tester, l10n.adsWatchCta(10)).onPressed, isNull);
    expect(find.text(l10n.adsLimitReached), findsOneWidget);
  });

  testWidgets('en pausa hay cuenta atrás y el botón está desactivado', (
    tester,
  ) async {
    final next = DateTime.now()
        .toUtc()
        .add(const Duration(seconds: 90))
        .toIso8601String();
    await _pump(tester, _Api({...on, 'next_at': next}), 'es', settle: false);
    final l10n = lookupAppLocalizations(const Locale('es'));
    expect(_button(tester, l10n.adsWatchCta(10)).onPressed, isNull);
    expect(
      find.byWidgetPredicate(
        (w) =>
            w is Text &&
            RegExp(r'^Siguiente video en 00:0\d:\d\d$').hasMatch(w.data ?? ''),
      ),
      findsOneWidget,
    );
  });

  testWidgets('sin SDK disponible se avisa y no se pide ticket', (tester) async {
    final api = _Api(on);
    await _pump(tester, api, 'es');
    final l10n = lookupAppLocalizations(const Locale('es'));
    await tester.ensureVisible(find.widgetWithText(FilledButton, l10n.adsWatchCta(10)));
    await tester.tap(find.widgetWithText(FilledButton, l10n.adsWatchCta(10)));
    await tester.pumpAndSettle();
    expect(find.text(l10n.adsUnavailable), findsOneWidget);
    expect(api.calls, isNot(contains('/mobile/v1/rewards/ads/ticket')));
  });
}
