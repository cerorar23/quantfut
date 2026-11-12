import 'dart:async';
import 'dart:convert';

import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../l10n/app_locale.dart';
import 'live_api.dart';
import 'sports.dart';

/// Copia de fábrica del catálogo de deportes: la misma forma que `GET /cliente/v1/config` (contrato 1),
/// generada por `scripts/generar_catalogo_defecto.py` a partir de la semilla del servidor.
const factorySportCatalogAsset = 'assets/model/cliente_config_defecto.json';

/// Lee la copia de fábrica. `null` si el asset falta o no se puede usar (no debería pasar: va empaquetado).
Future<SportCatalog?> loadFactorySportCatalog([AssetBundle? bundle]) async {
  try {
    final body = await (bundle ?? rootBundle).loadString(factorySportCatalogAsset);
    return SportCatalog.fromJson(jsonDecode(body));
  } catch (_) {
    return null;
  }
}

/// Respuesta de la red: `status` 200 con cuerpo y ETag, o 304 si lo guardado sigue vigente.
class SportCatalogReply {
  const SportCatalogReply(this.status, {this.body, this.etag});
  final int status;
  final Object? body;
  final String? etag;
}

typedef SportCatalogFetch = Future<SportCatalogReply> Function({required String lang, String? etag});

/// `GET /cliente/v1/config?cliente=app&contrato=1&lang=…` con `If-None-Match`. Lanza si no hay red o el
/// servidor falla; quien llama ([SportCatalogStore.refresh]) lo trata como «no hay novedades».
Future<SportCatalogReply> fetchSportCatalogFromApi({required String lang, String? etag}) async {
  final api = QuantFutApi();
  try {
    final reply = await api
        .requestConditional(
          '/cliente/v1/config',
          query: {'cliente': 'app', 'contrato': 1, 'lang': lang},
          etag: etag,
        )
        .timeout(const Duration(seconds: 8));
    return SportCatalogReply(reply.status, body: reply.data, etag: reply.etag);
  } finally {
    api.dispose();
  }
}

/// Mantiene [sportCatalogNotifier]. Orden de preferencia: **red → disco → copia de fábrica**.
///
/// Al arrancar instala la copia de fábrica y, encima, la última respuesta válida del disco; la red se pide
/// aparte (sin bloquear el arranque) y solo reemplaza lo anterior si trae al menos un deporte utilizable. Una
/// respuesta inválida, vacía o sin `deportes` conserva lo que había: la app nunca se queda sin deportes. Nada de
/// esto muestra errores al usuario.
class SportCatalogStore with WidgetsBindingObserver {
  SportCatalogStore({
    ValueNotifier<SportCatalog>? target,
    Future<String?> Function(String key)? read,
    Future<void> Function(String key, String value)? write,
    SportCatalogFetch? fetch,
    Future<SportCatalog?> Function()? loadFactory,
    String Function()? currentLang,
    DateTime Function()? clock,
  }) : _target = target ?? sportCatalogNotifier,
       _read = read ?? ((key) => SharedPreferencesAsync().getString(key)),
       _write = write ?? ((key, value) => SharedPreferencesAsync().setString(key, value)),
       _fetch = fetch ?? fetchSportCatalogFromApi,
       _loadFactory = loadFactory ?? loadFactorySportCatalog,
       _lang = currentLang ?? (() => AppLocale.instance.code),
       _clock = clock ?? DateTime.now;

  /// Almacén vigente de la app (el que arranca `main`).
  static final instance = SportCatalogStore();

  static const bodyKey = 'sport_catalog_body';
  static const etagKey = 'sport_catalog_etag';
  static const langKey = 'sport_catalog_lang';

  /// Reintento al volver a primer plano: no antes de este tiempo desde el último intento.
  static const resumeEvery = Duration(minutes: 10);

  final ValueNotifier<SportCatalog> _target;
  final Future<String?> Function(String key) _read;
  final Future<void> Function(String key, String value) _write;
  final SportCatalogFetch _fetch;
  final Future<SportCatalog?> Function() _loadFactory;
  final String Function() _lang;
  final DateTime Function() _clock;

  String? _appliedBody;
  String? _etag;
  String? _etagLang;
  DateTime? _lastAttempt;
  bool _fetching = false;

  /// Copia de fábrica y disco, en ese orden (el disco gana). No lanza ni toca la red.
  Future<void> loadLocal() async {
    final factory = await _loadFactory();
    if (factory != null) _target.value = factory;
    try {
      final raw = await _read(bodyKey);
      final disk = raw == null ? null : SportCatalog.fromJson(jsonDecode(raw));
      if (disk != null) {
        _target.value = disk;
        _appliedBody = raw;
        final etag = await _read(etagKey);
        _etag = etag == null || etag.isEmpty ? null : etag;
        _etagLang = await _read(langKey);
      }
    } catch (_) {
      /* Disco ilegible: se queda con la copia de fábrica. */
    }
  }

  /// Arranque: lo local ya aplicado, la red en segundo plano y vigilancia del primer plano.
  Future<void> start() async {
    await loadLocal();
    WidgetsBinding.instance.addObserver(this);
    unawaited(refresh());
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final last = _lastAttempt;
    if (state == AppLifecycleState.resumed && (last == null || _clock().difference(last) >= resumeEvery)) {
      unawaited(refresh());
    }
  }

  /// Pide el catálogo a la red. `true` si cambió el catálogo vigente. Nunca lanza.
  Future<bool> refresh() async {
    if (_fetching) return false;
    _fetching = true;
    _lastAttempt = _clock();
    try {
      final lang = _lang();
      // El ETag solo vale si lo guardado es del mismo idioma y hay un cuerpo aplicado que conservar.
      final etag = _appliedBody != null && _etagLang == lang ? _etag : null;
      final reply = await _fetch(lang: lang, etag: etag);
      if (reply.status == 304) return false;
      if (reply.status != 200) return false;
      final catalog = SportCatalog.fromJson(reply.body);
      if (catalog == null) return false; // inválida, vacía o sin deportes: se conserva lo anterior
      final body = jsonEncode(reply.body);
      final changed = body != _appliedBody;
      if (changed) _target.value = catalog;
      _appliedBody = body;
      _etag = reply.etag;
      _etagLang = lang;
      try {
        await _write(bodyKey, body);
        await _write(etagKey, reply.etag ?? '');
        await _write(langKey, lang);
      } catch (_) {
        /* Sin disco solo se pierde la copia para el próximo arranque. */
      }
      return changed;
    } catch (_) {
      return false; // sin red o error del servidor: se conserva lo anterior
    } finally {
      _fetching = false;
    }
  }
}
