import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/core/sentry_reporting.dart';
import 'package:sentry_flutter/sentry_flutter.dart';

void main() {
  test('el evento sale sin usuario, petición ni nombre de servidor', () {
    final event = SentryEvent(
      user: SentryUser(email: 'a@b.com', ipAddress: '1.2.3.4'),
      request: SentryRequest(url: 'https://x.pro/y?token=SECRETO'),
      serverName: 'mi-telefono',
    );
    final out = SentryReporting.scrub(event);
    expect(out.user, isNull);
    expect(out.request, isNull);
    expect(out.serverName, isNull);
  });

  test('las migas de red se descartan y las demás se conservan', () {
    final hint = Hint();
    expect(
      SentryReporting.scrubBreadcrumb(
        Breadcrumb(category: 'http', message: 'GET https://x.pro?token=1'),
        hint,
      ),
      isNull,
    );
    final ui = Breadcrumb(category: 'ui.click', message: 'Reintentar');
    expect(SentryReporting.scrubBreadcrumb(ui, hint), same(ui));
  });

  test('sin consentimiento de diagnóstico Sentry no se inicia', () async {
    await SentryReporting.apply(false);
    expect(Sentry.isEnabled, isFalse);
  });
}
