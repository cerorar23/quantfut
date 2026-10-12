import 'package:flutter/foundation.dart';
import 'package:sentry_flutter/sentry_flutter.dart';

/// Informes de errores a Sentry, **solo mientras el diagnóstico esté activado**.
///
/// Es el mismo consentimiento que gobierna Crashlytics y Rendimiento. Los fallos nativos se
/// capturan antes de que Dart pueda filtrarlos, así que no basta con un `beforeSend`: el SDK
/// no se inicia sin consentimiento y se cierra (`Sentry.close`) al retirarlo.
///
/// El DSN de un cliente es público por diseño (solo permite enviar eventos); se puede
/// sustituir en una compilación con `--dart-define=SENTRY_DSN=...`.
class SentryReporting {
  const SentryReporting._();

  static const dsn = String.fromEnvironment(
    'SENTRY_DSN',
    defaultValue:
        'https://db4ad326c3da22c1be8e0a39db84a372@o4512245587836928.ingest.us.sentry.io/4512245797486592',
  );

  static Future<void> apply(bool diagnosticsAllowed) async {
    if (dsn.isEmpty) return;
    try {
      if (diagnosticsAllowed && !Sentry.isEnabled) {
        await SentryFlutter.init(_configure);
      } else if (!diagnosticsAllowed && Sentry.isEnabled) {
        await Sentry.close();
      }
    } catch (error) {
      // Un fallo del informe nunca debe romper el arranque ni el ajuste de privacidad.
      debugPrint('Sentry no disponible: $error');
    }
  }

  static void _configure(SentryFlutterOptions options) {
    options
      ..dsn = dsn
      ..environment = kReleaseMode ? 'production' : 'debug'
      ..sendDefaultPii = false
      ..attachScreenshot = false
      ..enableAutoSessionTracking = false
      ..tracesSampleRate = null
      ..maxBreadcrumbs = 30
      ..beforeBreadcrumb = scrubBreadcrumb
      ..beforeSend = (event, hint) => scrub(event);
  }

  /// Quita de un evento lo que pueda identificar a la persona.
  @visibleForTesting
  static SentryEvent scrub(SentryEvent event) {
    event.user = null;
    event.request = null;
    event.serverName = null;
    return event;
  }

  /// Las migas de pan de red llevan URLs completas: se descartan.
  @visibleForTesting
  static Breadcrumb? scrubBreadcrumb(Breadcrumb? crumb, Hint hint) {
    final category = crumb?.category;
    if (category == 'http' || category == 'xhr') return null;
    return crumb;
  }
}
