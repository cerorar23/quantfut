import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:provider/provider.dart';

import 'core/firebase_startup.dart';
import 'core/firebase_services.dart';
import 'core/firebase_access.dart';
import 'l10n/app_locale.dart';
import 'l10n/language_selection_screen.dart';
import 'onbonding_screen/splesh_screen.dart';
import 'product/live_widgets.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initializeDateFormatting();
  await AppLocale.instance.load();
  const app = QuantFutApp();
  runApp(firebaseEnabled ? const FirebaseStartup(child: app) : app);
}

class QuantFutApp extends StatelessWidget {
  const QuantFutApp({super.key});

  @override
  Widget build(BuildContext context) => MultiProvider(
    providers: [ChangeNotifierProvider(create: (_) => ColorNotifire())],
    child: ListenableBuilder(
      listenable: AppLocale.instance,
      builder: (context, _) => MaterialApp(
        theme: liveTheme(),
        locale: AppLocale.instance.locale,
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        // Primera vez: elegir idioma antes de la bienvenida y del acceso.
        home: !AppLocale.instance.chosen
            ? const LanguageSelectionScreen()
            : FirebaseServices.current == null
            ? Splesh_Screen()
            : const FirebaseAccountGate(),
        debugShowCheckedModeBanner: false,
      ),
    ),
  );
}
