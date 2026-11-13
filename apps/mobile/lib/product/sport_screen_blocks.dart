// Bloques de pantalla `aviso` y `vip` de la definición de pantallas (Fase 4 · 4.5). Sin diseño nuevo: el aviso usa
// `liveCard` (la tarjeta de avisos de la app) y la llamada VIP, el botón y las tarjetas de planes que ya existen.
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../l10n/app_locale.dart';
import 'live_api.dart';
import 'live_widgets.dart';
import 'qf_theme.dart';
import 'screen_definition.dart';

/// Color e icono de la tarjeta según el tono del aviso (`info` por omisión).
(Color, IconData) noticeLook(String tone) => switch (tone) {
  'exito' => (QfColors.success, Icons.check_circle_outline),
  'aviso' => (QfColors.cta, Icons.warning_amber_rounded),
  'peligro' => (QfColors.danger, Icons.error_outline),
  _ => (QfColors.primary, Icons.info_outline),
};

/// Bloque `aviso`: texto en el idioma actual (cae a español) y enlace relativo opcional. Sin texto, no se pinta.
class SportNotice extends StatelessWidget {
  const SportNotice({super.key, required this.block, this.api});

  final ScreenBlock block;

  /// Para resolver el enlace relativo contra el servidor; sin él no se muestra el enlace.
  final QuantFutApi? api;

  @override
  Widget build(BuildContext context) {
    final data = noticeData(block, context.l10n.localeName);
    if (data == null) return const SizedBox.shrink();
    final (color, icon) = noticeLook(data.tone);
    final link = data.link;
    return liveCard(
      border: color,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                liveText(data.text, size: 13, color: QfColors.text),
                if (link != null && api != null)
                  TextButton(
                    key: const ValueKey('sport-notice-link'),
                    onPressed: () => launchUrl(api!.base.resolve(link), mode: LaunchMode.externalApplication),
                    child: Text(context.l10n.sportNoticeMore),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Bloque `vip`: la llamada a los planes que ya existe (el mismo botón «Acceso VIP»).
class SportVipCall extends StatelessWidget {
  const SportVipCall({super.key, this.onVip});

  final VoidCallback? onVip;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return liveCard(
      border: QfColors.cta,
      child: Row(
        children: [
          Expanded(child: liveText(l10n.sportVipCall, size: 13, color: QfColors.text)),
          const SizedBox(width: 10),
          FilledButton(
            key: const ValueKey('sport-vip-call'),
            style: FilledButton.styleFrom(
              backgroundColor: QfColors.cta,
              foregroundColor: QfColors.onPrimary,
              minimumSize: const Size(96, 44),
            ),
            onPressed: onVip,
            child: Text(l10n.vipAccessButton),
          ),
        ],
      ),
    );
  }
}

/// Bloque de pantalla que no es una sección (`aviso` o `vip`).
Widget? screenExtra(ScreenBlock block, {QuantFutApi? api, VoidCallback? onVip}) => switch (block.type) {
  'aviso' => SportNotice(key: ValueKey('screen-${block.id}'), block: block, api: api),
  'vip' => SportVipCall(key: ValueKey('screen-${block.id}'), onVip: onVip),
  _ => null,
};
