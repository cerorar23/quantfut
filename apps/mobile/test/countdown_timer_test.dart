import 'package:clock/clock.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/widgets/countdown_timer.dart';
import 'package:gobet/l10n/app_locale.dart';

void main() {
  testWidgets('expires once and never renders negative time', (tester) async {
    var now = DateTime(2026, 10, 11);
    var ended = 0;
    await withClock(Clock(() => now), () async {
      await tester.pumpWidget(
        MaterialApp(
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          locale: AppLocale.instance.locale,

          home: CountdownTimer(
            endTime: now.add(const Duration(seconds: 2)).millisecondsSinceEpoch,
            onEnd: () => ended++,
          ),
        ),
      );
      expect(find.text('00:00:02'), findsOneWidget);
      now = now.add(const Duration(seconds: 1));
      await tester.pump(const Duration(seconds: 1));
      expect(find.text('00:00:01'), findsOneWidget);
      now = now.add(const Duration(seconds: 10));
      await tester.pump(const Duration(seconds: 10));
      expect(find.text('00:00:00'), findsOneWidget);
      expect(ended, 1);
      await tester.pump(const Duration(seconds: 2));
      expect(ended, 1);
      await tester.pumpWidget(const SizedBox());
    });
  });

  testWidgets('an expired deadline completes after the first build', (
    tester,
  ) async {
    final now = DateTime(2026, 10, 11);
    var ended = 0;
    await withClock(Clock.fixed(now), () async {
      await tester.pumpWidget(
        MaterialApp(
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          locale: AppLocale.instance.locale,

          home: CountdownTimer(
            endTime: now
                .subtract(const Duration(seconds: 1))
                .millisecondsSinceEpoch,
            onEnd: () => ended++,
          ),
        ),
      );
      expect(find.text('00:00:00'), findsOneWidget);
      expect(ended, 1);
      await tester.pump();
      expect(ended, 1);
      await tester.pumpWidget(const SizedBox());
    });
  });

  testWidgets('restarts for a new deadline and cancels on disposal', (
    tester,
  ) async {
    var now = DateTime(2026, 10, 11);
    var ended = 0;
    await withClock(Clock(() => now), () async {
      Widget countdown(int seconds) => MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: AppLocale.instance.locale,

        home: CountdownTimer(
          key: const ValueKey('countdown'),
          endTime: now.add(Duration(seconds: seconds)).millisecondsSinceEpoch,
          onEnd: () => ended++,
        ),
      );
      await tester.pumpWidget(countdown(1));
      now = now.add(const Duration(seconds: 1));
      await tester.pump(const Duration(seconds: 1));
      expect(ended, 1);
      await tester.pumpWidget(countdown(3601));
      expect(find.text('01:00:01'), findsOneWidget);
      await tester.pumpWidget(const SizedBox());
      now = now.add(const Duration(hours: 2));
      await tester.pump(const Duration(hours: 2));
      expect(ended, 1);
      expect(tester.takeException(), isNull);
    });
  });

  testWidgets('catches up after resuming the application', (tester) async {
    var now = DateTime(2026, 10, 11);
    var ended = 0;
    await withClock(Clock(() => now), () async {
      await tester.pumpWidget(
        MaterialApp(
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          locale: AppLocale.instance.locale,

          home: CountdownTimer(
            endTime: now.add(const Duration(seconds: 5)).millisecondsSinceEpoch,
            onEnd: () => ended++,
          ),
        ),
      );
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
      now = now.add(const Duration(minutes: 1));
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
      await tester.pump();
      expect(find.text('00:00:00'), findsOneWidget);
      expect(ended, 1);
      await tester.pumpWidget(const SizedBox());
    });
  });
}
