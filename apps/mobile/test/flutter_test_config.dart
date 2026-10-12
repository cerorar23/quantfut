import 'dart:async';

import 'package:gobet/l10n/app_locale.dart';
import 'package:intl/date_symbol_data_local.dart';

/// Se ejecuta antes de cada archivo de prueba: datos de fecha de todos los idiomas y
/// español como idioma inicial (las pruebas comprueban textos en español salvo las
/// que cambian el idioma a propósito).
Future<void> testExecutable(FutureOr<void> Function() testMain) async {
  await initializeDateFormatting();
  AppLocale.instance.reset();
  await testMain();
}
