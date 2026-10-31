import 'package:flutter/material.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import '../l10n/app_locale.dart';
import 'live_guide.dart';
import 'live_widgets.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';

// l10n-ignore-start (direcciones de la tienda y de los documentos legales: son datos)
const _storeApp = 'market://details?id=com.saptain.quantfut';
const _storeWeb =
    'https://play.google.com/store/apps/details?id=com.saptain.quantfut';
const _terms = 'https://pronosticosdeportivos.pro/legal/terminos';
const _privacy = 'https://pronosticosdeportivos.pro/legal/privacidad';
// l10n-ignore-end

/// Menú «Más»: guía, mis deportes, evaluar y compartir la app, y los documentos legales.
/// `onMySports` lleva al Perfil, a la sección «Mis deportes» (solo dentro del shell).
Future<void> showMoreSheet(BuildContext context, {VoidCallback? onMySports}) =>
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: QfColors.surface,
      shape: const CutCornerBorder(side: BorderSide(color: QfColors.border)),
      builder: (sheet) => Theme(
        data: liveTheme(),
        child: _MoreSheet(host: context, onMySports: onMySports),
      ),
    );

class _MoreSheet extends StatelessWidget {
  const _MoreSheet({required this.host, this.onMySports});

  /// Contexto de la pantalla que abrió la hoja: sigue vivo cuando la hoja se cierra.
  final BuildContext host;
  final VoidCallback? onMySports;

  Future<void> _open(String url) async {
    if (!await launchUrl(
          Uri.parse(url),
          mode: LaunchMode.externalApplication,
        ) &&
        host.mounted) {
      liveNotice(host, host.l10n.accessDocumentOpenError);
    }
  }

  Future<void> _rate() async {
    final l10n = host.l10n;
    final messenger = ScaffoldMessenger.of(host);
    var opened = false;
    try {
      opened = await launchUrl(
        Uri.parse(_storeApp),
        mode: LaunchMode.externalApplication,
      );
    } catch (_) {}
    if (!opened) {
      try {
        opened = await launchUrl(
          Uri.parse(_storeWeb),
          mode: LaunchMode.externalApplication,
        );
      } catch (_) {}
    }
    if (!opened) {
      messenger.showSnackBar(SnackBar(content: Text(l10n.moreStoreError)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    void close() => Navigator.of(context).pop();
    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(16, 10, 16, 20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(width: 40, height: 4, color: QfColors.border),
            const SizedBox(height: 14),
            Row(
              children: [
                const Text(
                  '//', // l10n-ignore (marca)
                  style: TextStyle(
                    fontFamily: qfDisplay,
                    fontWeight: FontWeight.w700,
                    fontSize: 22,
                    color: QfColors.primary,
                  ),
                ),
                const SizedBox(width: 8),
                const Expanded(
                  child: Text(
                    'QUANTFUT', // l10n-ignore (marca)
                    style: TextStyle(
                      fontFamily: qfDisplay,
                      fontWeight: FontWeight.w700,
                      fontSize: 22,
                      letterSpacing: 1.2,
                      color: QfColors.text,
                    ),
                  ),
                ),
                IconButton(
                  key: const ValueKey('more-close'),
                  tooltip: MaterialLocalizations.of(context).closeButtonTooltip,
                  onPressed: close,
                  icon: const Icon(Icons.close),
                ),
              ],
            ),
            _Section(l10n.moreLearn, [
              _Item(
                key: const ValueKey('more-guide'),
                icon: Icons.menu_book_outlined,
                title: l10n.moreGuide,
                subtitle: l10n.moreGuideSub,
                onTap: () {
                  close();
                  Navigator.of(host).push(
                    MaterialPageRoute<void>(
                      builder: (_) =>
                          Theme(data: liveTheme(), child: const GuideScreen()),
                    ),
                  );
                },
              ),
              if (onMySports != null)
                _Item(
                  key: const ValueKey('more-sports'),
                  icon: Icons.tune,
                  title: l10n.profileMySports,
                  subtitle: l10n.moreMySportsSub,
                  onTap: () {
                    close();
                    onMySports!();
                  },
                ),
            ]),
            _Section(l10n.moreApp, [
              _Item(
                key: const ValueKey('more-rate'),
                icon: Icons.star_outline,
                title: l10n.moreRate,
                subtitle: l10n.moreRateSub,
                onTap: () {
                  close();
                  _rate();
                },
              ),
              _Item(
                key: const ValueKey('more-share'),
                icon: Icons.share_outlined,
                title: l10n.moreShare,
                subtitle: l10n.moreShareSub,
                onTap: () {
                  close();
                  SharePlus.instance.share(
                    ShareParams(text: l10n.moreShareMessage),
                  );
                },
              ),
            ]),
            _Section(l10n.moreLegal, [
              _Item(
                key: const ValueKey('more-terms'),
                icon: Icons.description_outlined,
                title: l10n.accessTerms,
                onTap: () {
                  close();
                  _open(_terms);
                },
              ),
              _Item(
                key: const ValueKey('more-privacy'),
                icon: Icons.privacy_tip_outlined,
                title: l10n.accessPrivacy,
                onTap: () {
                  close();
                  _open(_privacy);
                },
              ),
            ]),
          ],
        ),
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section(this.title, this.items);

  final String title;
  final List<Widget> items;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(4, 18, 4, 6),
        child: Text(
          title.toUpperCase(),
          style: const TextStyle(
            color: QfColors.text2,
            fontFamily: qfDisplay,
            fontWeight: FontWeight.w700,
            fontSize: 13,
            letterSpacing: .9,
          ),
        ),
      ),
      ...items,
    ],
  );
}

/// Fila del menú: icono azul, título y subtítulo, 56 dp, separador superior.
class _Item extends StatelessWidget {
  const _Item({
    super.key,
    required this.icon,
    required this.title,
    required this.onTap,
    this.subtitle,
  });

  final IconData icon;
  final String title;
  final String? subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
    onTap: onTap,
    child: Container(
      constraints: const BoxConstraints(minHeight: 56),
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 8),
      decoration: const BoxDecoration(
        border: Border(top: BorderSide(color: QfColors.border)),
      ),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            color: QfColors.surface2,
            child: Icon(icon, color: QfColors.primary, size: 22),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                liveText(title, bold: true, color: QfColors.text),
                if (subtitle != null)
                  liveText(subtitle!, size: 12, color: QfColors.text2),
              ],
            ),
          ),
          const Icon(Icons.chevron_right, color: QfColors.muted),
        ],
      ),
    ),
  );
}
