import 'dart:async';
import 'dart:io';

import 'package:firebase_analytics/firebase_analytics.dart';
import 'package:firebase_app_check/firebase_app_check.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_crashlytics/firebase_crashlytics.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:firebase_performance/firebase_performance.dart';
import 'package:firebase_remote_config/firebase_remote_config.dart';
import 'package:flutter/foundation.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../firebase_options.dart';
import '../l10n/app_locale.dart';
import 'meta_events.dart';
import 'sentry_reporting.dart';

@pragma('vm:entry-point')
Future<void> firebaseBackgroundMessage(RemoteMessage message) async {
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
  // Background delivery must not log tokens or download protected predictions.
}

/// Seguimiento encendido por defecto en todo el mundo (decisión del titular, 2026-10-15);
/// lo que la persona eligió antes, incluido un «no», se respeta siempre.
bool consentDefault(bool? stored) => stored ?? true;

/// Motivo por el que no hay notificaciones; el texto se traduce al mostrarlo.
enum NotificationStatus { permissionDenied, iosPending }

class FirebaseServices extends ChangeNotifier {
  FirebaseServices._(this.preferences);
  static FirebaseServices? current;
  final SharedPreferencesAsync preferences;
  bool analyticsAllowed = false;
  bool diagnosticsAllowed = false;
  bool adsAllowed = true;
  bool notificationsAllowed = false;
  String language = 'es';
  NotificationStatus? notificationStatus;
  final openedMatch = ValueNotifier<String?>(null);
  final foregroundMessage = ValueNotifier<RemoteMessage?>(null);
  final List<StreamSubscription<dynamic>> _subscriptions = [];

  FirebaseAuth get auth => FirebaseAuth.instance;
  FirebaseMessaging get messaging => FirebaseMessaging.instance;
  FirebaseRemoteConfig get remoteConfig => FirebaseRemoteConfig.instance;

  static Future<FirebaseServices> initialize() async {
    if (current != null) return current!;
    final services = FirebaseServices._(SharedPreferencesAsync());
    services.analyticsAllowed = consentDefault(
      await services.preferences.getBool('analytics_consent'),
    );
    services.diagnosticsAllowed = consentDefault(
      await services.preferences.getBool('diagnostics_consent'),
    );
    services.adsAllowed = consentDefault(
      await services.preferences.getBool('ads_consent'),
    );
    services.notificationsAllowed =
        await services.preferences.getBool('push_consent') ?? false;
    // La app decide el idioma (elección guardada → dispositivo → español).
    services.language = AppLocale.instance.code;
    await FirebaseAppCheck.instance.activate(
      providerAndroid: kReleaseMode
          ? const AndroidPlayIntegrityProvider()
          : const AndroidDebugProvider(),
      providerApple: kReleaseMode
          ? const AppleAppAttestWithDeviceCheckFallbackProvider()
          : const AppleDebugProvider(),
    );
    await services.auth.setLanguageCode(services.language);
    await GoogleSignIn.instance.initialize();
    await services.applyConsent();
    services._installErrorHandlers();
    await services.remoteConfig.setConfigSettings(
      RemoteConfigSettings(
        fetchTimeout: const Duration(seconds: 8),
        minimumFetchInterval: kReleaseMode
            ? const Duration(hours: 12)
            : const Duration(minutes: 5),
      ),
    );
    await services.remoteConfig.setDefaults({
      'qf_banner_enabled': false,
      'qf_banner_text': '',
      'qf_maintenance_enabled': false,
      'qf_minimum_version': '1.0.0',
      'qf_google_auth_enabled': false,
      'qf_terms_url': '',
      'qf_privacy_url': '',
    });
    FirebaseMessaging.onBackgroundMessage(firebaseBackgroundMessage);
    await services.messaging.setAutoInitEnabled(services.notificationsAllowed);
    await services.messaging.setForegroundNotificationPresentationOptions(
      alert: false,
      badge: false,
      sound: false,
    );
    services._subscriptions.add(
      FirebaseMessaging.onMessage.listen((message) {
        services.foregroundMessage.value = message;
      }),
    );
    services._subscriptions.add(
      FirebaseMessaging.onMessageOpenedApp.listen(services._openMessage),
    );
    final initialMessage = await services.messaging.getInitialMessage();
    if (initialMessage != null) services._openMessage(initialMessage);
    current = services;
    unawaited(services.refreshRemoteConfig());
    return services;
  }

  void _installErrorHandlers() {
    final previousFlutterHandler = FlutterError.onError;
    FlutterError.onError = (details) {
      (previousFlutterHandler ?? FlutterError.presentError)(details);
      if (diagnosticsAllowed) {
        unawaited(
          FirebaseCrashlytics.instance.recordFlutterFatalError(details),
        );
      }
    };
    final previousPlatformHandler = PlatformDispatcher.instance.onError;
    PlatformDispatcher.instance.onError = (error, stack) {
      if (diagnosticsAllowed) {
        unawaited(
          FirebaseCrashlytics.instance.recordError(error, stack, fatal: true),
        );
      }
      return previousPlatformHandler?.call(error, stack) ?? false;
    };
  }

  Future<void> applyConsent() async {
    await FirebaseAnalytics.instance.setConsent(
      analyticsStorageConsentGranted: analyticsAllowed,
      adStorageConsentGranted: false,
      adUserDataConsentGranted: false,
      adPersonalizationSignalsConsentGranted: false,
    );
    await FirebaseAnalytics.instance.setAnalyticsCollectionEnabled(
      analyticsAllowed,
    );
    await FirebaseCrashlytics.instance.setCrashlyticsCollectionEnabled(
      diagnosticsAllowed,
    );
    await FirebasePerformance.instance.setPerformanceCollectionEnabled(
      diagnosticsAllowed,
    );
    await SentryReporting.apply(diagnosticsAllowed);
    if (!diagnosticsAllowed) {
      await FirebaseCrashlytics.instance.deleteUnsentReports();
    }
    if (!analyticsAllowed) {
      await FirebaseAnalytics.instance.setUserId(id: null);
      await FirebaseAnalytics.instance.resetAnalyticsData();
    }
  }

  Future<void> setConsent({
    required bool analytics,
    required bool diagnostics,
  }) async {
    analyticsAllowed = analytics;
    diagnosticsAllowed = diagnostics;
    await preferences.setBool('analytics_consent', analytics);
    await preferences.setBool('diagnostics_consent', diagnostics);
    await applyConsent();
    notifyListeners();
  }

  Future<void> setAdsConsent(bool allowed) async {
    adsAllowed = allowed;
    await preferences.setBool('ads_consent', allowed);
    await MetaEvents.current?.apply(allowed);
    notifyListeners();
  }

  Future<void> setLanguage(String value) async {
    if (!const ['es', 'en', 'pt', 'fr', 'it', 'de'].contains(value)) return;
    language = value;
    await AppLocale.instance.select(value);
    await preferences.setString('language', value);
    await auth.setLanguageCode(value);
    notifyListeners();
  }

  Future<void> refreshRemoteConfig() async {
    try {
      await remoteConfig.fetchAndActivate();
      notifyListeners();
    } catch (_) {
      // Cached/local presentation values remain usable offline.
    }
  }

  bool get maintenance => remoteConfig.getBool('qf_maintenance_enabled');
  String get banner => remoteConfig.getBool('qf_banner_enabled')
      ? remoteConfig.getString('qf_banner_text')
      : '';

  Future<void> screen(String name) async {
    if (!analyticsAllowed) return;
    try {
      await FirebaseAnalytics.instance.logScreenView(screenName: name);
    } catch (_) {
      /* Optional measurement. */
    }
  }

  Future<void> event(String name) async {
    if (!analyticsAllowed) return;
    try {
      await FirebaseAnalytics.instance.logEvent(name: name);
    } catch (_) {
      /* Optional measurement. */
    }
  }

  Future<Trace?> startTrace(String name) async {
    if (!diagnosticsAllowed) return null;
    try {
      final trace = FirebasePerformance.instance.newTrace(name);
      await trace.start();
      return trace;
    } catch (_) {
      return null;
    }
  }

  Future<String?> appCheckToken() async {
    try {
      return await FirebaseAppCheck.instance.getToken().timeout(
        const Duration(seconds: 4),
      );
    } catch (_) {
      // App Check stays in observation while production signing is prepared.
      return null;
    }
  }

  Future<String?> enableNotifications() async {
    final settings = await messaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );
    final allowed =
        settings.authorizationStatus == AuthorizationStatus.authorized ||
        settings.authorizationStatus == AuthorizationStatus.provisional;
    notificationsAllowed = allowed;
    await preferences.setBool('push_consent', allowed);
    await messaging.setAutoInitEnabled(allowed);
    notificationStatus = allowed ? null : NotificationStatus.permissionDenied;
    notifyListeners();
    return allowed ? notificationToken() : null;
  }

  Future<String?> notificationToken() async {
    if (!notificationsAllowed) return null;
    if (Platform.isIOS && await messaging.getAPNSToken() == null) {
      notificationStatus = NotificationStatus.iosPending;
      return null;
    }
    return messaging.getToken();
  }

  Future<void> disableNotifications() async {
    notificationsAllowed = false;
    await preferences.setBool('push_consent', false);
    await messaging.setAutoInitEnabled(false);
    await messaging.deleteToken();
    notifyListeners();
  }

  void _openMessage(RemoteMessage message) {
    final matchId = notificationMatchId(message.data);
    if (matchId != null) openedMatch.value = matchId;
  }

  Future<void> clearAccountData() async {
    openedMatch.value = null;
    foregroundMessage.value = null;
    await FirebaseAnalytics.instance.setUserId(id: null);
    await FirebaseCrashlytics.instance.setUserIdentifier('');
    await FirebaseAnalytics.instance.resetAnalyticsData();
    await MetaEvents.current?.forget();
  }
}

String? notificationMatchId(Map<String, dynamic> data) {
  final id = data['match_id'];
  if (data['route'] != 'match' ||
      id is! String ||
      !RegExp(r'^[A-Za-z0-9_-]{1,100}$').hasMatch(id)) {
    return null;
  }
  return id;
}
