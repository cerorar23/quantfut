import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';

typedef JsonMap = Map<String, dynamic>;
JsonMap jsonMap(dynamic value) =>
    value is Map ? Map<String, dynamic>.from(value) : {};
List<JsonMap> jsonRows(dynamic value) =>
    value is List ? value.map(jsonMap).toList() : [];

class ApiFailure implements Exception {
  const ApiFailure(this.message, [this.status]);
  final String message;
  final int? status;
  @override
  String toString() => message;
}

class QuantFutApi extends ChangeNotifier {
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
  JsonMap? account;
  bool get signedIn => _access != null;
  bool get plus => account?['plus'] == true;

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
    try {
      final req = await _client
          .openUrl(body == null ? 'GET' : 'POST', uri)
          .timeout(const Duration(seconds: 20));
      req.headers.set(HttpHeaders.acceptHeader, 'application/json');
      if (_access != null) {
        req.headers.set(HttpHeaders.authorizationHeader, 'Bearer $_access');
      }
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
      if (signedIn) await request('/app/v1/auth/logout', body: {});
    } finally {
      _clearSession();
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
    notifyListeners();
  }

  @override
  void dispose() {
    _client.close(force: true);
    super.dispose();
  }
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
