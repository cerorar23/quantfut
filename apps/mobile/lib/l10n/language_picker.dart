import 'package:flutter/material.dart';

import '../core/firebase_services.dart';
import '../product/live_api.dart';
import '../product/live_widgets.dart';
import 'app_locale.dart';

/// Cambia el idioma en la app y, si hay Firebase, lo sincroniza como preferencia.
Future<void> selectLanguage(String code) async {
  if (!await AppLocale.instance.select(code)) return;
  final services = FirebaseServices.current;
  if (services != null && services.language != code) {
    await services.setLanguage(code);
  }
  final api = QuantFutApi.firebaseSession;
  if (api != null && api.firebaseConnected) {
    try {
      await api.syncPreferences();
    } catch (_) {
      // La preferencia local ya cambió; se reintenta en la próxima sincronización.
    }
  }
}

/// Hoja con los 6 idiomas, cada uno en su propio idioma.
Future<void> showLanguagePicker(BuildContext context) =>
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: livePanel,
      showDragHandle: true,
      builder: (sheet) => SafeArea(
        child: ListenableBuilder(
          listenable: AppLocale.instance,
          builder: (context, _) => Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(24, 0, 24, 4),
                child: Text(
                  context.l10n.languageTitle,
                  style: const TextStyle(
                    fontSize: 19,
                    fontWeight: FontWeight.w700,
                    color: Colors.white,
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(24, 0, 24, 8),
                child: Text(
                  context.l10n.languageHint,
                  style: const TextStyle(fontSize: 13, color: liveMuted),
                ),
              ),
              for (final entry in appLanguages.entries)
                ListTile(
                  key: ValueKey('language-${entry.key}'),
                  title: Text(
                    entry.value,
                    style: const TextStyle(color: Colors.white),
                  ),
                  trailing: AppLocale.instance.code == entry.key
                      ? const Icon(Icons.check_rounded, color: liveGreen)
                      : null,
                  onTap: () async {
                    await selectLanguage(entry.key);
                    if (sheet.mounted) Navigator.of(sheet).pop();
                  },
                ),
              const SizedBox(height: 8),
            ],
          ),
        ),
      ),
    );

/// Botón de idioma para barras superiores (bienvenida, acceso).
class LanguageButton extends StatelessWidget {
  const LanguageButton({super.key, this.color = const Color(0xffb4bfce)});

  final Color color;

  @override
  Widget build(BuildContext context) => IconButton(
    key: const ValueKey('language-button'),
    tooltip: context.l10n.languageTitle,
    onPressed: () => showLanguagePicker(context),
    icon: Icon(Icons.language_rounded, color: color),
  );
}
