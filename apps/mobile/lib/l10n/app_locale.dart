import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'app_localizations.dart';

export 'app_localizations.dart';

/// Idiomas de la app. Los códigos coinciden con los del backend y de Firebase.
const appLanguages = <String, String>{
  'es': 'Español',
  'en': 'English',
  'pt': 'Português',
  'fr': 'Français',
  'it': 'Italiano',
  'de': 'Deutsch',
};

const _preferenceKey = 'language';

/// Idioma elegido. Funciona sin Firebase: se guarda en el dispositivo y, si hay
/// cuenta, `FirebaseServices` lo sincroniza como preferencia.
///
/// Orden de decisión al arrancar: elección guardada → idioma del dispositivo si la
/// app lo soporta → español.
class AppLocale extends ChangeNotifier {
  AppLocale._();

  static final AppLocale instance = AppLocale._();

  Locale _locale = const Locale('es');
  bool _chosen = false;

  Locale get locale => _locale;

  /// Textos en el idioma actual para código sin `BuildContext` (errores, formatos).
  /// En widgets usa `context.l10n`, que además reconstruye la pantalla al cambiar.
  AppLocalizations get l10n => lookupAppLocalizations(_locale);
  String get code => _locale.languageCode;

  /// `true` si la persona eligió un idioma (frente a la sugerencia del dispositivo).
  bool get chosen => _chosen;

  /// Lee la elección guardada. Se llama una vez antes de `runApp`.
  Future<void> load({Locale? device}) async {
    String? saved;
    try {
      saved = await SharedPreferencesAsync().getString(_preferenceKey);
    } catch (_) {
      saved = null;
    }
    if (saved != null && appLanguages.containsKey(saved)) {
      _locale = Locale(saved);
      _chosen = true;
    } else {
      final code = (device ?? WidgetsBinding.instance.platformDispatcher.locale)
          .languageCode;
      _locale = Locale(appLanguages.containsKey(code) ? code : 'es');
      _chosen = false;
    }
    notifyListeners();
  }

  /// Aplica y guarda un idioma. Devuelve `false` si no está soportado.
  Future<bool> select(String code) async {
    if (!appLanguages.containsKey(code)) return false;
    _locale = Locale(code);
    _chosen = true;
    notifyListeners();
    try {
      await SharedPreferencesAsync().setString(_preferenceKey, code);
    } catch (_) {
      // Sin almacenamiento el cambio sigue valiendo durante esta sesión.
    }
    return true;
  }

  /// Solo para pruebas: vuelve al estado inicial.
  @visibleForTesting
  void reset() {
    _locale = const Locale('es');
    _chosen = false;
  }
}

extension AppLocalizationsContext on BuildContext {
  AppLocalizations get l10n => AppLocalizations.of(this);
}
