import 'package:flutter/material.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import '../l10n/app_locale.dart';
import 'live_guide.dart';
import 'live_widgets.dart';

// l10n-ignore-start (direcciones de la tienda y de los documentos legales: son datos)
const _storeApp = 'market://details?id=com.saptain.quantfut';
const _storeWeb =
    'https://play.google.com/store/apps/details?id=com.saptain.quantfut';
const _terms = 'https://pronosticosdeportivos.pro/legal/terminos';
const _privacy = 'https://pronosticosdeportivos.pro/legal/privacidad';
// l10n-ignore-end

/// Menú «Más»: guía, evaluar y compartir la app, y los documentos legales.
Future<void> showMoreSheet(BuildContext context) => showModalBottomSheet<void>(
  context: context,
  isScrollControlled: true,
  useSafeArea: true,
  backgroundColor: const Color(0xff0f1a28),
  shape: const RoundedRectangleBorder(
    borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
  ),
  builder: (sheet) => Theme(
    data: liveTheme(),
    child: _MoreSheet(host: context),
  ),
);

class _MoreSheet extends StatelessWidget {
  const _MoreSheet({required this.host});

  /// Contexto de la pantalla que abrió la hoja: sigue vivo cuando la hoja se cierra.
  final BuildContext host;

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
            Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.white24,
                borderRadius: BorderRadius.circular(4),
              ),
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: liveGreen.withValues(alpha: .16),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: const Icon(Icons.insights, color: liveGreen),
                ),
                const SizedBox(width: 12),
                Expanded(child: liveText('QuantFut', size: 20, bold: true)),
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
                color: liveGold,
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
            ]),
            _Section(l10n.moreApp, [
              _Item(
                key: const ValueKey('more-rate'),
                icon: Icons.star_outline,
                color: liveGreen,
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
                color: liveCyan,
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
                color: liveMuted,
                title: l10n.accessTerms,
                onTap: () {
                  close();
                  _open(_terms);
                },
              ),
              _Item(
                key: const ValueKey('more-privacy'),
                icon: Icons.privacy_tip_outlined,
                color: liveMuted,
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
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(4, 18, 4, 8),
        child: Text(
          title.toUpperCase(),
          style: const TextStyle(
            color: liveMuted,
            fontFamily: 'Gilroy Bold',
            fontSize: 11,
          ),
        ),
      ),
      Container(
        decoration: BoxDecoration(
          color: livePanel,
          borderRadius: BorderRadius.circular(18),
        ),
        child: Column(children: items),
      ),
    ],
  );
}

class _Item extends StatelessWidget {
  const _Item({
    super.key,
    required this.icon,
    required this.color,
    required this.title,
    required this.onTap,
    this.subtitle,
  });

  final IconData icon;
  final Color color;
  final String title;
  final String? subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
    borderRadius: BorderRadius.circular(18),
    onTap: onTap,
    child: Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: color.withValues(alpha: .16),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: color, size: 22),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                liveText(title, bold: true),
                if (subtitle != null)
                  liveText(subtitle!, size: 12, color: liveMuted),
              ],
            ),
          ),
          const Icon(Icons.chevron_right, color: liveMuted),
        ],
      ),
    ),
  );
}
