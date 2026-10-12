import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:flutter/foundation.dart';

import '../core/firebase_services.dart';

typedef JsonMap = Map<String, dynamic>;
JsonMap jsonMap(dynamic value) =>
    value is Map ? Map<String, dynamic>.from(value) : {};
List<JsonMap> jsonRows(dynamic value) =>
    value is List ? value.map(jsonMap).toList() : [];

class ApiFailure implements Exception {
  const ApiFailure(this.message, [this.status, this.code]);
  final String message;
  final int? status;
  final String? code;
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
      if (_firebaseIdentity) {
        final token = await services?.auth.currentUser?.getIdToken();
        if (token == null) {
          throw const ApiFailure('Inicia sesión de nuevo.', 401);
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
        throw ApiFailure(
          message?.toString() ??
              'No se pudo cargar la información (HTTP ${response.statusCode}).',
          response.statusCode,
          jsonMap(detail)['code']?.toString(),
        );
      }
      if (data == null && text.isNotEmpty) {
        throw const ApiFailure('Respuesta no válida del servidor.');
      }
      return data;
    } on ApiFailure {
      rethrow;
    } catch (_) {
      throw const ApiFailure(
        'No se pudo conectar. Comprueba tu conexión e inténtalo de nuevo.',
      );
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
  }

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
      throw const ApiFailure('Sesión no válida.');
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
      throw const ApiFailure('Inicia sesión con Google.', 401);
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
          if (acceptedTerms) 'terms_version': '2026-10-12',
          if (acceptedTerms) 'privacy_version': '2026-10-12',
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
  return date == null
      ? 'Horario no disponible'
      : '${date.day}/${date.month} · ${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}';
}

String realPercent(dynamic value) => value is num && value.isFinite
    ? '${(value * 100).toStringAsFixed(0)} %'
    : '—';
String decimalText(dynamic value, [int digits = 2]) =>
    value is num && value.isFinite
    ? value.toStringAsFixed(digits).replaceAll('.', ',')
    : '—';
JsonMap featureMap(JsonMap data) =>
    jsonMap(jsonMap(data['config'])['features']);
bool featureEnabled(JsonMap data, String key) =>
    jsonMap(featureMap(data)[key])['enabled'] == true;
String featureMessage(JsonMap data, String key) =>
    jsonMap(featureMap(data)[key])['message']?.toString() ??
    'Modelo en entrenamiento';
