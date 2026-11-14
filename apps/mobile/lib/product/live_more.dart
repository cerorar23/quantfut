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

/// Menú «Más» CyberCore: VIP, guía, mis deportes, evaluar y compartir la app, y los documentos legales.
/// `onMySports` lleva al Perfil, a la sección «Mis deportes» (solo dentro del shell).
Future<void> showMoreSheet(
  BuildContext context, {
  VoidCallback? onMySports,
  VoidCallback? onVip,
}) =>
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: QfColors.surface,
      shape: const CutCornerBorder(
        cut: 18,
        side: BorderSide(color: QfColors.borderStrong),
      ),
      builder: (sheet) => Theme(
        data: liveTheme(),
        child: _MoreSheet(host: context, onMySports: onMySports, onVip: onVip),
      ),
    );

class _MoreSheet extends StatelessWidget {
  const _MoreSheet({required this.host, this.onMySports, this.onVip});

  /// Contexto de la pantalla que abrió la hoja: sigue vivo cuando la hoja se cierra.
  final BuildContext host;
  final VoidCallback? onMySports;
  final VoidCallback? onVip;

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
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Center(
              child: Container(
                width: 44,
                height: 4,
                decoration: BoxDecoration(
                  color: QfColors.slate.withValues(alpha: .4),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                const Expanded(
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        'QUANT',
                        style: TextStyle(
                          fontFamily: qfDisplay,
                          fontWeight: FontWeight.w700,
                          fontSize: 21,
                          letterSpacing: 1.4,
                          color: QfColors.text,
                        ),
                      ),
                      Text(
                        'FUT',
                        style: TextStyle(
                          fontFamily: qfDisplay,
                          fontWeight: FontWeight.w700,
                          fontSize: 21,
                          letterSpacing: 1.4,
                          color: QfColors.cyan,
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  key: const ValueKey('more-close'),
                  tooltip: MaterialLocalizations.of(context).closeButtonTooltip,
                  constraints: const BoxConstraints(minWidth: 44, minHeight: 44),
                  icon: const Icon(Icons.close, color: QfColors.text2, size: 22),
                  onPressed: close,
                ),
              ],
            ),
            const SizedBox(height: 10),

            // Acceso VIP
            InkWell(
              onTap: () {
                close();
                onVip?.call();
              },
              child: Container(
                constraints: const BoxConstraints(minHeight: 56),
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: ShapeDecoration(
                  color: QfColors.yellow.withValues(alpha: .07),
                  shape: CutCornerBorder(
                    cut: 10,
                    side: BorderSide(color: QfColors.yellow.withValues(alpha: .5)),
                  ),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.workspace_premium, size: 26, color: QfColors.yellow),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            l10n.commonSeeVip,
                            style: const TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w700,
                              color: QfColors.yellow,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            l10n.moreVipSubtitle,
                            style: const TextStyle(fontSize: 12, color: QfColors.text2),
                          ),
                        ],
                      ),
                    ),
                    const Icon(Icons.chevron_right, size: 18, color: QfColors.yellow),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 14),

            // // APRENDE
            Text(
              '// ${l10n.moreLearn.toUpperCase()}',
              style: const TextStyle(
                fontFamily: qfDisplay,
                fontWeight: FontWeight.w700,
                fontSize: 11,
                letterSpacing: 1.8,
                color: QfColors.cyan,
              ),
            ),
            const SizedBox(height: 6),
            InkWell(
              key: const ValueKey('more-guide'),
              onTap: () {
                close();
                Navigator.of(host).push(
                  MaterialPageRoute<void>(
                    builder: (_) =>
                        Theme(data: liveTheme(), child: const GuideScreen()),
                  ),
                );
              },
              child: Container(
                constraints: const BoxConstraints(minHeight: 62),
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: ShapeDecoration(
                  color: QfColors.cyan.withValues(alpha: .06),
                  shape: const CutCornerBorder(
                    cut: 10,
                    side: BorderSide(color: QfColors.borderStrong),
                  ),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 40,
                      height: 40,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: QfColors.cyan.withValues(alpha: .1),
                        border: Border.all(color: QfColors.borderStrong),
                      ),
                      child: const Icon(Icons.menu_book_outlined, color: QfColors.cyan, size: 22),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            l10n.moreGuide,
                            style: const TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.w700,
                              color: QfColors.text,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            l10n.moreGuideSub,
                            style: const TextStyle(fontSize: 12, color: QfColors.text2),
                          ),
                        ],
                      ),
                    ),
                    const Icon(Icons.chevron_right, size: 18, color: QfColors.cyan),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 14),

            // // APP
            Text(
              '// ${l10n.moreApp.toUpperCase()}',
              style: const TextStyle(
                fontFamily: qfDisplay,
                fontWeight: FontWeight.w700,
                fontSize: 11,
                letterSpacing: 1.8,
                color: QfColors.cyan,
              ),
            ),
            const SizedBox(height: 6),
            Container(
              decoration: ShapeDecoration(
                color: QfColors.surface2,
                shape: const CutCornerBorder(
                  cut: 10,
                  side: BorderSide(color: QfColors.border),
                ),
              ),
              child: Column(
                children: [
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
                    isLast: true,
                    onTap: () {
                      close();
                      SharePlus.instance.share(
                        ShareParams(text: l10n.moreShareMessage),
                      );
                    },
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),

            // // LEGAL
            Text(
              '// ${l10n.moreLegal.toUpperCase()}',
              style: const TextStyle(
                fontFamily: qfDisplay,
                fontWeight: FontWeight.w700,
                fontSize: 11,
                letterSpacing: 1.8,
                color: QfColors.cyan,
              ),
            ),
            const SizedBox(height: 6),
            Row(
              children: [
                Expanded(
                  child: InkWell(
                    key: const ValueKey('more-terms'),
                    onTap: () {
                      close();
                      _open(_terms);
                    },
                    child: Container(
                      constraints: const BoxConstraints(minHeight: 48),
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        border: Border.all(color: QfColors.border),
                      ),
                      child: Text(
                        l10n.accessTerms.toUpperCase(),
                        style: const TextStyle(
                          fontFamily: qfDisplay,
                          fontWeight: FontWeight.w700,
                          fontSize: 13,
                          letterSpacing: 0.8,
                          color: QfColors.text2,
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: InkWell(
                    key: const ValueKey('more-privacy'),
                    onTap: () {
                      close();
                      _open(_privacy);
                    },
                    child: Container(
                      constraints: const BoxConstraints(minHeight: 48),
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        border: Border.all(color: QfColors.border),
                      ),
                      child: Text(
                        l10n.accessPrivacy.toUpperCase(),
                        style: const TextStyle(
                          fontFamily: qfDisplay,
                          fontWeight: FontWeight.w700,
                          fontSize: 13,
                          letterSpacing: 0.8,
                          color: QfColors.text2,
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            Center(
              child: Text(
                'QUANTFUT · ${l10n.disclaimerProbability}',
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontFamily: qfMono,
                  fontSize: 10,
                  fontWeight: FontWeight.w500,
                  color: QfColors.muted,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Item extends StatelessWidget {
  const _Item({
    super.key,
    required this.icon,
    required this.title,
    required this.onTap,
    this.subtitle,
    this.isLast = false,
  });

  final IconData icon;
  final String title;
  final String? subtitle;
  final VoidCallback onTap;
  final bool isLast;

  @override
  Widget build(BuildContext context) => InkWell(
    onTap: onTap,
    child: Container(
      constraints: const BoxConstraints(minHeight: 56),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        border: isLast ? null : const Border(bottom: BorderSide(color: QfColors.divider)),
      ),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              border: Border.all(color: QfColors.border),
            ),
            child: Icon(icon, color: QfColors.text2, size: 20),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: QfColors.text,
                  ),
                ),
                if (subtitle != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    subtitle!,
                    style: const TextStyle(fontSize: 12, color: QfColors.text2),
                  ),
                ],
              ],
            ),
          ),
          const Icon(Icons.chevron_right, size: 18, color: QfColors.muted),
        ],
      ),
    ),
  );
}
