import 'dart:io';
import 'dart:ui' as ui;

import 'package:app_tracking_transparency/app_tracking_transparency.dart';
import 'package:facebook_app_events/facebook_app_events.dart';
import 'package:flutter/services.dart';
import 'package:package_info_plus/package_info_plus.dart';

// Sin `typedef JsonMap`: live_api.dart ya lo define e importa este archivo; dos typedefs con
// el mismo nombre harían ambiguo el import en store_purchases.dart.

/// Sin App ID real no se arranca el SDK (los recursos nativos quedan vacíos).
const metaConfigured = bool.fromEnvironment('QF_META_ENABLED');

/// Lo que la app manda a Meta con el SDK: solo lo que únicamente ella conoce. Registro,
/// suscripciones, cobros y desbloqueos los manda el servidor por Conversions API.
abstract class MetaSink {
  Future<void> start({required bool tracking});
  Future<void> stop();
  Future<void> identify(String externalId, String? email);
  Future<void> forget();
  Future<void> log(
    String name,
    Map<String, Object> parameters, {
    double? valueToSum,
  });
  Future<String?> anonymousId();
}

class FacebookSink implements MetaSink {
  final _fb = FacebookAppEvents();
  bool _initialized = false;

  @override
  Future<void> start({required bool tracking}) async {
    if (!_initialized) {
      await _fb.initializeSdk();
      _initialized = true;
    }
    await _fb.setAdvertiserIdCollectionEnabled(tracking);
    await _fb.setAutoLogAppEventsEnabled(true);
    await _fb.activateApp();
  }

  @override
  Future<void> stop() async {
    if (!_initialized) return;
    await _fb.setAutoLogAppEventsEnabled(false);
    await _fb.setAdvertiserIdCollectionEnabled(false);
    await _fb.clearUserID();
    await _fb.clearUserData();
  }

  @override
  Future<void> identify(String externalId, String? email) async {
    await _fb.setUserID(externalId);
    if (email != null) await _fb.setUserData(email: email);
  }

  @override
  Future<void> forget() async {
    if (!_initialized) return;
    await _fb.clearUserID();
    await _fb.clearUserData();
  }

  @override
  Future<void> log(
    String name,
    Map<String, Object> parameters, {
    double? valueToSum,
  }) => _fb.logEvent(
    name: name,
    parameters: parameters,
    valueToSum: valueToSum,
  );

  @override
  Future<String?> anonymousId() =>
      _initialized ? _fb.getAnonymousId() : Future.value(null);
}

/// iOS: pide ATT una vez; Android: el ID de publicidad decide (canal nativo).
Future<bool> platformTracking() async {
  if (!Platform.isIOS) return true;
  var status = await AppTrackingTransparency.trackingAuthorizationStatus;
  if (status == TrackingStatus.notDetermined) {
    status = await AppTrackingTransparency.requestTrackingAuthorization();
  }
  return status == TrackingStatus.authorized;
}

class MetaEvents {
  MetaEvents(
    this.sink, {
    this.configured = metaConfigured,
    Future<bool> Function()? tracking,
  }) : _tracking = tracking ?? platformTracking;
  static MetaEvents? current;
  final MetaSink sink;
  final bool configured;
  final Future<bool> Function() _tracking;
  bool _active = false, _trackingAllowed = false;
  bool get active => _active;

  Future<void> apply(bool allowed) async {
    if (!configured) return;
    try {
      if (allowed && !_active) {
        _trackingAllowed = await _tracking();
        await sink.start(tracking: _trackingAllowed);
        _active = true;
      } else if (!allowed && _active) {
        await sink.stop();
        _active = false;
      }
    } catch (_) {
      /* La medición nunca puede impedir usar la app. */
    }
  }

  Future<void> identify(Map<String, dynamic> me) async {
    final id = me['meta_external_id'];
    if (!_active || id is! String) return;
    final email = (me['account'] as Map?)?['email'] as String?;
    try {
      await sink.identify(id, email);
    } catch (_) {}
  }

  Future<void> forget() async {
    try {
      await sink.forget();
    } catch (_) {}
  }

  Future<void> _log(
    String name,
    Map<String, Object> parameters, {
    double? valueToSum,
  }) async {
    if (!_active) return;
    try {
      await sink.log(name, parameters, valueToSum: valueToSum);
    } catch (_) {}
  }

  Future<void> viewMatch(String id) => _log('fb_mobile_content_view', {
    'fb_content_type': 'product',
    'fb_content_id': 'match:$id',
  });
  Future<void> viewVip() => _log('fb_mobile_content_view', {
    'fb_content_type': 'product_group',
    'fb_content_id': 'vip',
  });
  Future<void> search(String text) => _log('fb_mobile_search', {
    'fb_search_string': text.length > 100 ? text.substring(0, 100) : text,
    'fb_success': 1,
  });
  Future<void> initiateCheckout(
    String planCode,
    double price,
    String currency,
  ) => _log(
    'fb_mobile_initiated_checkout',
    {
      'fb_content_id': planCode,
      'fb_content_type': 'product',
      'fb_currency': currency,
      'fb_num_items': 1,
      'fb_payment_info_available': 1,
    },
    valueToSum: price,
  );
  Future<void> completeTutorial() => _log('fb_mobile_tutorial_completion', {
    'fb_success': 1,
    'fb_content_id': 'guide',
  });
  Future<void> adImpression() => _log('AdImpression', {
    'ad_type': 'rewarded_video',
  });
  Future<void> invite() => _log('Invite', {});

  /// Datos para POST /app/v1/meta/dispositivo; null si Meta no está activo.
  Future<Map<String, dynamic>?> device() async {
    if (!_active) return null;
    final anon = await sink.anonymousId();
    if (anon == null) return null;
    final info = await PackageInfo.fromPlatform();
    String? madid;
    var model = '', os = Platform.operatingSystemVersion;
    if (Platform.isAndroid) {
      final ad = await const MethodChannel(
        'quantfut/device',
      ).invokeMapMethod<String, Object?>('advertising');
      madid = ad?['id'] as String?;
      model = ad?['model'] as String? ?? '';
      os = ad?['os'] as String? ?? os;
    } else if (_trackingAllowed) {
      final idfa = await AppTrackingTransparency.getAdvertisingIdentifier();
      if (idfa != '00000000-0000-0000-0000-000000000000') madid = idfa;
    }
    final view = ui.PlatformDispatcher.instance.views.first;
    final now = DateTime.now();
    return {
      'anon_id': anon,
      'platform': Platform.isIOS ? 'ios' : 'android',
      'madid': madid,
      'advertiser_tracking_enabled': _trackingAllowed && madid != null,
      'extinfo': extinfo(
        ios: Platform.isIOS,
        package: info.packageName,
        version: info.version,
        build: info.buildNumber,
        os: os,
        model: model,
        locale: Platform.localeName,
        tzAbbr: now.timeZoneName,
        width: view.physicalSize.width,
        height: view.physicalSize.height,
        density: view.devicePixelRatio,
        cores: Platform.numberOfProcessors,
        tzName: now.timeZoneName,
      ),
    };
  }
}

/// Orden fijo de «extinfo» (Conversions API para apps); cadenas vacías donde falte.
List<String> extinfo({
  required bool ios,
  required String package,
  required String version,
  required String build,
  required String os,
  required String model,
  required String locale,
  required String tzAbbr,
  required double width,
  required double height,
  required double density,
  required int cores,
  required String tzName,
}) =>
    [
          ios ? 'i2' : 'a2',
          package,
          version,
          build,
          os,
          model,
          locale,
          tzAbbr,
          '',
          width.round().toString(),
          height.round().toString(),
          density.toStringAsFixed(2),
          '$cores',
          '',
          '',
          tzName,
        ]
        .map((v) => v.length > 100 ? v.substring(0, 100) : v)
        .toList();
