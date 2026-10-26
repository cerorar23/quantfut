import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:flutter/foundation.dart';

import 'package:intl/intl.dart';

import '../core/firebase_services.dart';
import '../core/meta_events.dart';
import '../l10n/app_locale.dart';

typedef JsonMap = Map<String, dynamic>;

/// Versión de términos y privacidad que acepta esta app (debe estar en el servidor).
const consentVersion = '2026-10-16';
JsonMap jsonMap(dynamic value) =>
    value is Map ? Map<String, dynamic>.from(value) : {};
List<JsonMap> jsonRows(dynamic value) =>
    value is List ? value.map(jsonMap).toList() : [];

/// Errores propios de la app, con texto en el idioma actual. Los mensajes que envía
/// el servidor (`detail`) viajan como texto libre con `ApiFailure('...')`.
enum ApiError {
  sessionExpired,
  loadFailed,
  invalidResponse,
  offline,
  invalidSession,
  signInWithGoogle,
  googleNotVerified,
}

class ApiFailure implements Exception {
  const ApiFailure(String text, [this.status, this.code])
    : _text = text,
      kind = null;
  const ApiFailure.kind(ApiError this.kind, [this.status, this.code])
    : _text = null;
  final String? _text;
  final ApiError? kind;
  final int? status;
  final String? code;

  /// Texto para mostrar, en el idioma actual.
  String get message {
    final l10n = AppLocale.instance.l10n;
    return switch (kind) {
      null => _text!,
      ApiError.sessionExpired => l10n.apiSessionExpired,
      ApiError.loadFailed => l10n.apiLoadFailed(status ?? 0),
      ApiError.invalidResponse => l10n.apiInvalidResponse,
      ApiError.offline => l10n.apiOffline,
      ApiError.invalidSession => l10n.apiInvalidSession,
      ApiError.signInWithGoogle => l10n.apiSignInWithGoogle,
      ApiError.googleNotVerified => l10n.apiGoogleNotVerified,
    };
  }

  @override
  String toString() => message;
}

class QuantFutApi extends ChangeNotifier {
  static QuantFutApi? firebaseSession;
  QuantFutApi({Uri? base})
    : base =
          base ??
          Uri.parse(
            const String.fromEnvironment(
              'QF_API_BASE_URL',
              defaultValue: 'https://pronosticosdeportivos.pro',
            ),
          );
  final Uri base;
  final _client = HttpClient()
    ..userAgent = 'QuantFut/1.0 (Android; Flutter)'
    ..connectionTimeout = const Duration(seconds: 15);
  String? _access, _refresh;
  bool _firebaseIdentity = false;
  JsonMap? account;
  bool get signedIn => _firebaseIdentity
      ? FirebaseServices.current?.auth.currentUser != null
      : _access != null;
  bool get plus => account?['plus'] == true;
  bool get firebaseConnected => _firebaseIdentity && signedIn;

  Future<dynamic> request(
    String path, {
    JsonMap? query,
    JsonMap? body,
    bool retry = true,
  }) async {
    final uri = base
        .resolve(path)
        .replace(
          queryParameters: query?.map((key, value) => MapEntry(key, '$value')),
        );
    final services = FirebaseServices.current;
    final trace = await services?.startTrace(apiTraceName(path));
    try {
      final req = await _client
          .openUrl(body == null ? 'GET' : 'POST', uri)
          .timeout(const Duration(seconds: 20));
      req.headers.set(HttpHeaders.acceptHeader, 'application/json');
      req.headers.set(
        HttpHeaders.acceptLanguageHeader,
        AppLocale.instance.code,
      );
      if (_firebaseIdentity) {
        final token = await services?.auth.currentUser?.getIdToken();
        if (token == null) {
          throw const ApiFailure.kind(ApiError.sessionExpired, 401);
        }
        req.headers.set(HttpHeaders.authorizationHeader, 'Bearer $token');
        req.headers.set('X-QF-Identity', 'firebase');
      } else if (_access != null) {
        req.headers.set(HttpHeaders.authorizationHeader, 'Bearer $_access');
      }
      final appToken = await services?.appCheckToken();
      if (appToken != null) req.headers.set('X-Firebase-AppCheck', appToken);
      if (body != null) {
        req.headers.contentType = ContentType.json;
        req.write(jsonEncode(body));
      }
      final response = await req.close().timeout(const Duration(seconds: 25));
      final text = await response
          .transform(utf8.decoder)
          .join()
          .timeout(const Duration(seconds: 25));
      dynamic data;
      try {
        data = text.isEmpty ? null : jsonDecode(text);
      } catch (_) {
        data = null;
      }
      if (response.statusCode == 401 && retry && _firebaseIdentity) {
        await services?.auth.currentUser?.getIdToken(true);
        return await request(path, query: query, body: body, retry: false);
      }
      if (response.statusCode == 401 &&
          retry &&
          _refresh != null &&
          !path.startsWith('/app/v1/auth')) {
        try {
          final tokens = jsonMap(
            await request(
              '/app/v1/auth/refresh',
              body: {'refresh_token': _refresh},
              retry: false,
            ),
          );
          _tokens(tokens);
          return await request(path, query: query, body: body, retry: false);
        } catch (_) {
          _clearSession();
        }
      }
      if (response.statusCode < 200 || response.statusCode >= 300) {
        final detail = jsonMap(data)['detail'];
        final message = detail is String ? detail : jsonMap(detail)['message'];
        final serverText = message?.toString();
        throw serverText == null
            ? ApiFailure.kind(
                ApiError.loadFailed,
                response.statusCode,
                jsonMap(detail)['code']?.toString(),
              )
            : ApiFailure(
                serverText,
                response.statusCode,
                jsonMap(detail)['code']?.toString(),
              );
      }
      if (data == null && text.isNotEmpty) {
        throw const ApiFailure.kind(ApiError.invalidResponse);
      }
      return data;
    } on ApiFailure {
      rethrow;
    } catch (_) {
      throw const ApiFailure.kind(ApiError.offline);
    } finally {
      try {
        await trace?.stop();
      } catch (_) {
        /* Optional measurement must not mask API responses. */
      }
    }
  }

  Future<JsonMap> home(DateTime date) async => jsonMap(
    await request(
      '/mobile/v1/home',
      query: {
        'fecha': dateKey(date),
        'tz': DateTime.now().timeZoneOffset.inMinutes,
      },
    ),
  );
  Future<JsonMap> detail(String id) async =>
      jsonMap(await request('/mobile/v1/matches/${Uri.encodeComponent(id)}'));
  Future<void> login(String email, String password) async {
    final tokens = jsonMap(
      await request(
        '/app/v1/auth/login',
        body: {'email': email.trim(), 'password': password},
        retry: false,
      ),
    );
    _tokens(tokens);
    try {
      await updateAccount();
    } catch (_) {
      _clearSession();
      rethrow;
    }
  }

  Future<void> updateAccount() async {
    if (!signedIn) return;
    account = jsonMap(await request('/app/v1/me'));
    notifyListeners();
    await MetaEvents.current?.identify(account!);
  }

  /// IDs del dispositivo para Conversions API (anon_id, madid, extinfo). Solo con sesión y
  /// con Meta activo; un fallo no afecta al uso de la app.
  Future<void> syncMetaDevice() async {
    if (!signedIn) return;
    final device = await MetaEvents.current?.device();
    if (device == null) return;
    try {
      await request('/app/v1/meta/dispositivo', body: device);
    } catch (_) {
      /* Se reintenta en el próximo arranque. */
    }
  }

  Future<JsonMap> verifyPurchase({
    required String store,
    required String productId,
    required String token,
  }) async => jsonMap(
    await request(
      '/app/v1/compras/verificar',
      body: {
        'store': store,
        'product_id': productId,
        if (store == 'google_play') 'purchase_token': token else 'jws': token,
      },
    ),
  );

  Future<void> register(String email, String password) async {
    final tokens = jsonMap(
      await request(
        '/app/v1/auth/register',
        body: {'email': email.trim(), 'password': password},
        retry: false,
      ),
    );
    _tokens(tokens);
    try {
      await updateAccount();
    } catch (_) {
      _clearSession();
      rethrow;
    }
  }

  Future<void> resendVerification() async {
    await request('/app/v1/auth/verify/resend', body: {});
  }

  Future<void> forgotPassword(String email) async {
    await request(
      '/app/v1/auth/password/forgot',
      body: {'email': email.trim()},
      retry: false,
    );
  }

  Future<void> logout() async {
    try {
      if (FirebaseServices.current != null && signedIn) {
        await unregisterDevice();
      }
      if (signedIn) await request('/app/v1/auth/logout', body: {});
    } finally {
      _clearSession();
      final services = FirebaseServices.current;
      if (services != null) {
        try {
          await services.disableNotifications();
        } finally {
          await services.auth.signOut();
          await services.clearAccountData();
        }
      }
    }
  }

  void _tokens(JsonMap tokens) {
    if (tokens['access_token'] is! String ||
        tokens['refresh_token'] is! String) {
      throw const ApiFailure.kind(ApiError.invalidSession);
    }
    _access = tokens['access_token'];
    _refresh = tokens['refresh_token'];
  }

  void _clearSession() {
    _access = null;
    _refresh = null;
    account = null;
    _firebaseIdentity = false;
    if (firebaseSession == this) firebaseSession = null;
    notifyListeners();
  }

  Future<void> connectFirebase({bool acceptedTerms = false}) async {
    final services = FirebaseServices.current;
    final user = services?.auth.currentUser;
    if (services == null || user == null) {
      throw const ApiFailure.kind(ApiError.signInWithGoogle, 401);
    }
    if (_firebaseIdentity) {
      await updateAccount();
      return;
    }
    final token = await user.getIdToken();
    final result = jsonMap(
      await request(
        '/app/v1/firebase/connect',
        body: {
          'id_token': token,
          'language': services.language,
          if (acceptedTerms) 'terms_version': consentVersion,
          if (acceptedTerms) 'privacy_version': consentVersion,
        },
      ),
    );
    if (_access != null) {
      try {
        await request('/app/v1/auth/logout', body: {});
      } catch (_) {
        /* Linking succeeded. */
      }
    }
    _access = null;
    _refresh = null;
    _firebaseIdentity = true;
    firebaseSession = this;
    account = result;
    notifyListeners();
    try {
      await syncPreferences();
      if (services.notificationsAllowed) await registerDevice();
    } catch (_) {
      /* Preferences retry when opened; the authenticated account stays usable. */
    }
  }

  Future<void> syncPreferences() async {
    final services = FirebaseServices.current;
    if (!signedIn || services == null) return;
    await request(
      '/app/v1/firebase/preferences',
      body: {
        'language': services.language,
        'analytics': services.analyticsAllowed,
        'diagnostics': services.diagnosticsAllowed,
        'push_enabled': services.notificationsAllowed,
        'ads_measurement': services.adsAllowed,
      },
    );
  }

  Future<String> installationId() async {
    final preferences = FirebaseServices.current!.preferences;
    final stored = await preferences.getString('push_installation');
    if (stored != null) return stored;
    final random = Random.secure();
    final bytes = List<int>.generate(16, (_) => random.nextInt(256));
    bytes[6] = (bytes[6] & 15) | 64;
    bytes[8] = (bytes[8] & 63) | 128;
    final hex = bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
    final id =
        '${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20)}';
    await preferences.setString('push_installation', id);
    return id;
  }

  Future<void> registerDevice([String? refreshedToken]) async {
    final services = FirebaseServices.current;
    if (!signedIn || services == null || !services.notificationsAllowed) return;
    final token = refreshedToken ?? await services.notificationToken();
    if (token == null) return;
    await syncPreferences();
    await request(
      '/app/v1/firebase/devices',
      body: {
        'installation_id': await installationId(),
        'token': token,
        'platform': Platform.isIOS ? 'ios' : 'android',
        'language': services.language,
      },
    );
  }

  Future<void> unregisterDevice() async {
    if (!signedIn || FirebaseServices.current == null) return;
    await request(
      '/app/v1/firebase/devices/unregister',
      body: {'installation_id': await installationId()},
    );
  }

  @override
  void dispose() {
    _client.close(force: true);
    super.dispose();
  }
}

String apiTraceName(String path) {
  if (path.startsWith('/mobile/v1/home')) return 'qf_load_home';
  if (path.startsWith('/mobile/v1/matches/')) return 'qf_load_match';
  if (path == '/app/v1/me') return 'qf_load_profile';
  if (path.startsWith('/app/v1/firebase/')) return 'qf_firebase_request';
  if (path.startsWith('/app/v1/compras/')) return 'qf_store_request';
  return 'qf_api_request';
}

String dateKey(DateTime date) =>
    '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
DateTime? dateValue(dynamic value) => value is String
    ? DateTime.tryParse(value)
    : value is DateTime
    ? value
    : null;
String kickoffText(dynamic value) {
  final date = dateValue(value)?.toLocal();
  if (date == null) return AppLocale.instance.l10n.formatScheduleUnavailable;
  return '${localDate(DateFormat.Md, date)} · ${localDate(DateFormat.Hm, date)}';
}

/// Duración con la que un partido ya debería haber terminado (90' + descanso + añadido).
const matchSpan = Duration(minutes: 130);

/// El partido ya debería haber terminado y el resultado aún no consta. El resultado
/// llega por ciclos: pasado [matchSpan] se dice «esperando resultado», no «en juego».
bool awaitingResult(dynamic kickoff, [DateTime? now]) {
  final ko = dateValue(kickoff);
  return ko != null && (now ?? DateTime.now()).difference(ko) >= matchSpan;
}

/// Formatea una fecha con el idioma actual. Si los datos de ese idioma aún no
/// están cargados, usa inglés (siempre disponible) en lugar de fallar.
String localDate(DateFormat Function(String locale) pattern, DateTime date) {
  try {
    return pattern(AppLocale.instance.code).format(date);
  } on Exception {
    return pattern('en_US').format(date);
  }
}

/// Separador entre el número y «%»: es/fr/de llevan espacio («65 %»); en/pt/it no.
String _percentSeparator() =>
    const {'es', 'fr', 'de'}.contains(AppLocale.instance.code) ? ' ' : '';

/// Porcentaje ya escalado (65,4 → «65 %») con el formato del idioma actual.
String percentText(num value, [int digits = 0]) =>
    '${decimalText(value, digits)}${_percentSeparator()}%';

/// Probabilidad (0–1) como porcentaje entero con el formato del idioma actual.
String realPercent(dynamic value) =>
    value is num && value.isFinite ? percentText(value * 100) : '—';

/// Número decimal con el separador del idioma actual (coma o punto), sin miles.
String decimalText(dynamic value, [int digits = 2]) =>
    value is num && value.isFinite
    ? (NumberFormat.decimalPatternDigits(
        locale: AppLocale.instance.code,
        decimalDigits: digits,
      )..turnOffGrouping()).format(value)
    : '—';
JsonMap featureMap(JsonMap data) =>
    jsonMap(jsonMap(data['config'])['features']);
bool featureEnabled(JsonMap data, String key) =>
    jsonMap(featureMap(data)[key])['enabled'] == true;

/// Mensaje de una sección desactivada. El servidor guarda textos por defecto en
/// español: se muestran traducidos; un texto personalizado del administrador se
/// respeta tal cual.
String featureMessage(JsonMap data, String key) {
  final text = jsonMap(featureMap(data)[key])['message']?.toString();
  final l10n = AppLocale.instance.l10n;
  if (text == null || text.isEmpty) return l10n.featureTraining;
  // l10n-ignore-start
  return switch (text) {
    'Modelo en entrenamiento' => l10n.featureTraining,
    'Agenda temporalmente no disponible' => l10n.featAgenda,
    'Seguimiento en preparación' => l10n.featBalance,
    'Compras en preparación' => l10n.featPurchases,
    'Comunidad en preparación' => l10n.featCommunity,
    'Estadísticas temporalmente no disponibles' => l10n.featStats,
    'Datos del partido temporalmente no disponibles' => l10n.featMatchData,
    'Traducciones en preparación' => l10n.featLanguages,
    'Medición en preparación' => l10n.featMeasurement,
    'Modelo NBA en entrenamiento' => l10n.featNba,
    'Notificaciones en preparación' => l10n.featNotifications,
    'Acceso VIP temporalmente no disponible' => l10n.featVip,
    _ => text,
  };
  // l10n-ignore-end
}
