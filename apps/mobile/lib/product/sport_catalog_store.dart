import 'dart:convert';

import 'package:flutter/services.dart';

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

/// Instala la copia de fábrica como catálogo vigente. Sin ella (asset ilegible) se queda [SportCatalog.builtIn].
Future<void> installFactorySportCatalog([AssetBundle? bundle]) async {
  final factory = await loadFactorySportCatalog(bundle);
  if (factory != null) sportCatalogNotifier.value = factory;
}
