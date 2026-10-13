import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/live_rewards.dart';
import 'package:gobet/product/live_widgets.dart';

class _Api extends QuantFutApi {
  int launches = 0;

  @override
  bool get signedIn => true;

  @override
  Future<dynamic> request(
    String path, {
    JsonMap? query,
    JsonMap? body,
    bool retry = true,
  }) async {
    if (path == '/mobile/v1/rewards/offers/tapjoy') {
      launches++;
      return {'sdk': 'tapjoy', 'sdk_key': 'test-key', 'user_id': 'test-user'};
    }
    return {
      'settings': {'enabled': true, 'unlock_cost': 100},
      'signed_in': true,
      'providers': [
        {'provider': 'tapjoy', 'name': 'Tapjoy', 'available': true},
      ],
      'wallet': {'balance': 0, 'spendable': 0},
    };
  }
}

Future<void> _pump(WidgetTester tester, _Api api, String language) async {
  await tester.pumpWidget(
    MaterialApp(
      locale: Locale(language),
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      theme: liveTheme(),
      home: RewardsScreen(api: api),
    ),
  );
  await tester.pumpAndSettle();
  await tester.ensureVisible(
    find.widgetWithText(
      FilledButton,
      lookupAppLocalizations(Locale(language)).rewardsOffersCta,
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  const channel = MethodChannel('quantfut/offers');
  const html = '<!doctype html><html><head><title>Tapjoy</title></head></html>';
  final messenger =
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;

  tearDown(() => messenger.setMockMethodCallHandler(channel, null));

  for (final language in ['es', 'en', 'pt', 'fr', 'it', 'de']) {
    testWidgets('SDK HTML is never displayed in $language', (tester) async {
      messenger.setMockMethodCallHandler(channel, (call) async {
        expect(call.method, 'tapjoy');
        expect(call.arguments['user_id'], 'test-user');
        expect(call.arguments['placement'], 'coins_offerwall');
        // También cubre el error recibido desde un puente nativo antiguo.
        throw PlatformException(code: 'tapjoy', message: html);
      });
      await _pump(tester, _Api(), language);
      final l10n = lookupAppLocalizations(Locale(language));
      await tester.tap(find.widgetWithText(FilledButton, l10n.rewardsOffersCta));
      await tester.pumpAndSettle();
      expect(find.text(l10n.rewardsOffersLoadFailed), findsOneWidget);
      expect(find.textContaining('<!doctype'), findsNothing);
      expect(find.textContaining('PlatformException'), findsNothing);
      expect(tester.takeException(), isNull);
    });
  }

  for (final code in [
    'tapjoy_unavailable',
    'tapjoy_timeout',
    'tapjoy_config',
  ]) {
    testWidgets('$code shows an actionable message and allows retry', (
      tester,
    ) async {
      messenger.setMockMethodCallHandler(channel, (_) async {
        throw PlatformException(code: code, message: html);
      });
      await _pump(tester, _Api(), 'es');
      final l10n = lookupAppLocalizations(const Locale('es'));
      await tester.tap(find.widgetWithText(FilledButton, l10n.rewardsOffersCta));
      await tester.pumpAndSettle();
      final expected = switch (code) {
        'tapjoy_unavailable' => l10n.rewardsOffersUnavailable,
        'tapjoy_timeout' => l10n.rewardsOffersTimeout,
        _ => l10n.rewardsOffersConfig,
      };
      expect(find.text(expected), findsOneWidget);
      expect(
        tester
            .widget<FilledButton>(
              find.widgetWithText(FilledButton, l10n.rewardsOffersCta),
            )
            .onPressed,
        isNotNull,
      );
    });
  }

  testWidgets('only one offer request runs while the SDK opens', (
    tester,
  ) async {
    final pending = Completer<bool>();
    var calls = 0;
    messenger.setMockMethodCallHandler(channel, (_) {
      calls++;
      return pending.future;
    });
    final api = _Api();
    await _pump(tester, api, 'es');
    final go = find.widgetWithText(
      FilledButton,
      lookupAppLocalizations(const Locale('es')).rewardsOffersCta,
    );
    await tester.tap(go);
    await tester.pump();
    expect(tester.widget<FilledButton>(go).onPressed, isNull);
    await tester.tap(go);
    await tester.pump();
    expect(api.launches, 1);
    expect(calls, 1);
    pending.complete(true);
    await tester.pumpAndSettle();
    expect(tester.widget<FilledButton>(go).onPressed, isNotNull);
  });
}
