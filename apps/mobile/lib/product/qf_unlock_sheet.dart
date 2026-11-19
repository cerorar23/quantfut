import 'dart:ui';

import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import 'live_api.dart';
import 'qf_charts.dart';
import 'qf_shapes.dart';
import 'qf_sheets.dart';
import 'qf_theme.dart';
import 'sport_images.dart';

/// Hoja inferior CyberCore para desbloquear pronósticos con monedas (§5.11).
///
/// Dos variantes visuales:
/// 1. Con saldo suficiente: botón verde de confirmación con [ValueKey('unlock-confirm')].
/// 2. Sin saldo suficiente: atajos rápidos a Coins (+5, +10, +200) y botón para ganar
///    monedas con [ValueKey('need-coins-go')].
class QfUnlockSheet extends StatefulWidget {
  const QfUnlockSheet({
    super.key,
    required this.pick,
    required this.cost,
    required this.saldo,
    this.initialMissing = false,
    this.monthlyPrice,
    required this.onUnlock,
    required this.onEarnCoins,
    required this.onVip,
    this.images,
  });

  final JsonMap pick;
  final int cost;
  final int saldo;
  final bool initialMissing;
  final String? monthlyPrice;
  final Future<void> Function() onUnlock;
  final VoidCallback onEarnCoins;
  final VoidCallback onVip;
  final ImageCatalog? images;

  /// Abre la hoja inferior CyberCore usando [QfBottomSheet.show].
  static Future<bool?> show({
    required BuildContext context,
    required JsonMap pick,
    required int cost,
    required int saldo,
    bool initialMissing = false,
    String? monthlyPrice,
    required Future<void> Function() onUnlock,
    required VoidCallback onEarnCoins,
    required VoidCallback onVip,
    ImageCatalog? images,
  }) {
    return QfBottomSheet.show<bool>(
      context: context,
      builder: (ctx) => QfUnlockSheet(
        pick: pick,
        cost: cost,
        saldo: saldo,
        initialMissing: initialMissing,
        monthlyPrice: monthlyPrice,
        onUnlock: onUnlock,
        onEarnCoins: onEarnCoins,
        onVip: onVip,
        images: images,
      ),
    );
  }

  @override
  State<QfUnlockSheet> createState() => _QfUnlockSheetState();
}

class _QfUnlockSheetState extends State<QfUnlockSheet> {
  late bool _isMissing;
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    _isMissing = widget.initialMissing || (widget.saldo < widget.cost);
  }

  Future<void> _handleUnlock() async {
    if (_loading) return;
    setState(() => _loading = true);
    try {
      await widget.onUnlock();
      if (mounted) Navigator.of(context).pop(true);
    } on ApiFailure catch (e) {
      if (!mounted) return;
      setState(() => _loading = false);
      if (e.code == 'monedas_insuficientes') {
        setState(() => _isMissing = true);
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.message)),
        );
      }
    } catch (e) {
      if (!mounted) return;
      setState(() => _loading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('$e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final cost = widget.cost > 0 ? widget.cost : 40;
    final saldo = widget.saldo >= 0 ? widget.saldo : 0;
    final missingAmount = (cost - saldo) > 0 ? (cost - saldo) : cost;

    // Colores según estado (con saldo: verde; sin saldo: magenta)
    final headerColor = _isMissing ? QfColors.magenta : QfColors.green;
    final headerBg = headerColor.withValues(alpha: .1);

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Fila de encabezado: icono 44x44, títulos y botón cerrar
        _buildHeader(context, headerColor, headerBg, cost, missingAmount),
        const SizedBox(height: 12),

        // Tarjeta previa del partido (escudos solapados, liga, equipos, pick difuminado y VIP)
        _buildMatchCard(context),
        const SizedBox(height: 12),

        // Tres viñetas de valor con tick verde
        _buildBullets(context),
        const SizedBox(height: 12),

        // Bloque de costo, saldo y barra de 12 pips
        _buildCostBalanceBox(context, cost, saldo, missingAmount),
        const SizedBox(height: 12),

        // Acción principal (desbloquear verde o atajos + botón ganar)
        if (!_isMissing)
          _buildUnlockButton(context, cost)
        else
          _buildMissingActions(context, missingAmount),
        const SizedBox(height: 10),

        // Salida VIP con precio mensual real (o sin precio)
        _buildVipCard(context),
        const SizedBox(height: 10),

        // Pie informativo
        Text(
          l10n.unlockFooterTerms,
          textAlign: TextAlign.center,
          style: const TextStyle(
            fontFamily: qfBody,
            fontSize: 11,
            color: QfColors.slate,
          ),
        ),
      ],
    );
  }

  Widget _buildHeader(
    BuildContext context,
    Color color,
    Color bg,
    int cost,
    int missing,
  ) {
    final l10n = context.l10n;
    final title = _isMissing
        ? l10n.unlockMissingTitle(missing)
        : l10n.unlockSheetTitle;
    final subtitle = _isMissing ? l10n.unlockMissingSub : l10n.unlockSheetSub;

    return Row(
      children: [
        Container(
          width: 44,
          height: 44,
          decoration: ShapeDecoration(
            color: bg,
            shape: CutCornerBorder(
              cut: 8,
              side: BorderSide(color: color, width: 1.2),
            ),
          ),
          child: Icon(
            _isMissing ? Icons.lock_outline_rounded : Icons.lock_open_rounded,
            color: color,
            size: 22,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontFamily: qfDisplay,
                  fontSize: 20,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1.4,
                  color: QfColors.text,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                subtitle,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontFamily: qfBody,
                  fontSize: 12,
                  color: QfColors.text2,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(width: 8),
        IconButton(
          tooltip: l10n.commonClose,
          icon: const Icon(Icons.close_rounded, size: 22, color: QfColors.text2),
          onPressed: () => Navigator.of(context).pop(false),
        ),
      ],
    );
  }

  Widget _buildMatchCard(BuildContext context) {
    final local = widget.pick['local'];
    final homeName = local is Map ? '${local['nombre'] ?? ''}' : '${local ?? ''}';
    final visitante = widget.pick['visitante'];
    final awayName = visitante is Map ? '${visitante['nombre'] ?? ''}' : '${visitante ?? ''}';
    final liga = widget.pick['liga'];
    final leagueName = liga is Map ? '${liga['nombre'] ?? ''}' : '${liga ?? ''}';
    final kickoff = widget.pick['kickoff_utc'] ?? widget.pick['fecha'] ?? '';
    final kickoffStr = kickoff.toString();
    final kickoffLabel = kickoffStr.isNotEmpty ? kickoffText(kickoffStr) : '';

    final subParts = <String>[];
    if (leagueName.isNotEmpty) subParts.add(leagueName.toUpperCase());
    if (kickoffLabel.isNotEmpty) subParts.add(kickoffLabel.toUpperCase());
    final metaText = subParts.isNotEmpty ? subParts.join(' · ') : 'QUANTFUT';

    final matchup = (homeName.isNotEmpty || awayName.isNotEmpty)
        ? '$homeName – $awayName'
        : 'Partido destacado';

    final pickLabel = '${widget.pick['texto'] ?? widget.pick['seleccion'] ?? widget.pick['mercado'] ?? widget.pick['nombre'] ?? 'Pronóstico VIP'}';

    final homeUrl = widget.pick['home_img'] as String? ??
        widget.images?.nbaLogo(homeName) ??
        widget.images?.tennisPhoto(homeName)?.path;
    final awayUrl = widget.pick['away_img'] as String? ??
        widget.images?.nbaLogo(awayName) ??
        widget.images?.tennisPhoto(awayName)?.path;

    return Container(
      decoration: const ShapeDecoration(
        color: QfColors.surface2,
        shape: CutCornerBorder(
          cut: 8,
          side: BorderSide(color: QfColors.border, width: 1),
        ),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      child: Row(
        children: [
          // Dos escudos solapados (38 dp cada uno, el segundo con margen izquierdo -8 dp)
          SizedBox(
            width: 68,
            height: 38,
            child: Stack(
              children: [
                Positioned(
                  left: 0,
                  top: 0,
                  bottom: 0,
                  child: QfAvatar(
                    name: homeName.isNotEmpty ? homeName : 'H',
                    size: 38,
                    url: homeUrl,
                    shape: AvatarShape.contain,
                  ),
                ),
                Positioned(
                  left: 30,
                  top: 0,
                  bottom: 0,
                  child: QfAvatar(
                    name: awayName.isNotEmpty ? awayName : 'A',
                    size: 38,
                    url: awayUrl,
                    shape: AvatarShape.contain,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  metaText,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontFamily: qfMono,
                    fontSize: 10,
                    fontWeight: FontWeight.w500,
                    color: QfColors.slate,
                    letterSpacing: .4,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  matchup,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontFamily: qfBody,
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    color: QfColors.text,
                  ),
                ),
                const SizedBox(height: 2),
                ImageFiltered(
                  imageFilter: ImageFilter.blur(sigmaX: 5, sigmaY: 5),
                  child: Text(
                    pickLabel,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontFamily: qfDisplay,
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                      color: QfColors.cyan,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              border: Border.all(
                color: QfColors.yellow.withValues(alpha: .45),
                width: 1,
              ),
              borderRadius: BorderRadius.circular(2),
            ),
            child: const Text(
              'VIP',
              style: TextStyle(
                fontFamily: qfDisplay,
                fontSize: 11,
                fontWeight: FontWeight.w700,
                letterSpacing: 1.3,
                color: QfColors.yellow,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBullets(BuildContext context) {
    final l10n = context.l10n;
    return Column(
      children: [
        _buildBulletItem(l10n.unlockBullet1),
        const SizedBox(height: 6),
        _buildBulletItem(l10n.unlockBullet2),
        const SizedBox(height: 6),
        _buildBulletItem(l10n.unlockBullet3),
      ],
    );
  }

  Widget _buildBulletItem(String text) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        const Icon(
          Icons.check_rounded,
          size: 16,
          color: QfColors.green,
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            text,
            style: const TextStyle(
              fontFamily: qfBody,
              fontSize: 13,
              color: QfColors.text,
              height: 1.3,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildCostBalanceBox(
    BuildContext context,
    int cost,
    int saldo,
    int missing,
  ) {
    final l10n = context.l10n;

    // Cálculo de pips proporcionales sobre base 12
    final unit = ((cost > 120 || saldo > 120) ? (cost > saldo ? cost : saldo) / 12 : 10)
        .ceil()
        .clamp(1, 1000);

    final int filled;
    final int spend;
    final int missingPips;

    if (!_isMissing) {
      spend = (cost / unit).round().clamp(1, 12);
      filled = (saldo / unit).round().clamp(spend, 12);
      missingPips = 0;
    } else {
      spend = 0;
      filled = (saldo / unit).floor().clamp(0, 11);
      missingPips = (missing / unit).ceil().clamp(1, 12 - filled);
    }

    final captionText = !_isMissing
        ? l10n.unlockRemainingCoins((saldo - cost) > 0 ? (saldo - cost) : 0)
        : l10n.unlockNeedHave(cost, saldo);

    final captionColor = _isMissing ? QfColors.magenta : QfColors.text2;

    return Container(
      decoration: BoxDecoration(
        color: QfColors.yellow.withValues(alpha: .05),
        border: Border.all(
          color: QfColors.yellow.withValues(alpha: .35),
          width: 1,
        ),
        borderRadius: BorderRadius.circular(4),
      ),
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    l10n.unlockCostHeader,
                    style: const TextStyle(
                      fontFamily: qfDisplay,
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1.4,
                      color: QfColors.slate,
                    ),
                  ),
                  RichText(
                    text: TextSpan(
                      text: '$cost ',
                      style: const TextStyle(
                        fontFamily: qfMono,
                        fontSize: 26,
                        fontWeight: FontWeight.w700,
                        height: 1,
                        color: QfColors.yellow,
                      ),
                      children: [
                        TextSpan(
                          text: l10n.unlockCoinsUnit,
                          style: const TextStyle(
                            fontFamily: qfDisplay,
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 1.2,
                            color: QfColors.yellow,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    l10n.unlockBalanceHeader,
                    style: const TextStyle(
                      fontFamily: qfDisplay,
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1.4,
                      color: QfColors.slate,
                    ),
                  ),
                  Text(
                    '$saldo',
                    style: const TextStyle(
                      fontFamily: qfMono,
                      fontSize: 26,
                      fontWeight: FontWeight.w700,
                      height: 1,
                      color: QfColors.text,
                    ),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 10),
          QfPips(
            total: 12,
            filled: filled,
            spend: spend,
            missing: missingPips,
            filledColor: QfColors.yellow,
            height: 10,
            spacing: 3,
          ),
          const SizedBox(height: 8),
          Text(
            captionText,
            style: TextStyle(
              fontFamily: qfMono,
              fontSize: 12,
              fontWeight: FontWeight.w700,
              color: captionColor,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildUnlockButton(BuildContext context, int cost) {
    final l10n = context.l10n;
    return Container(
      decoration: BoxDecoration(
        boxShadow: [
          BoxShadow(
            color: QfColors.green.withValues(alpha: .16),
            blurRadius: 28,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        shape: const CutCornerBorder(cut: 8),
        clipBehavior: Clip.antiAlias,
        child: Ink(
          decoration: const BoxDecoration(
            gradient: qfGreenGradient,
          ),
          child: InkWell(
            key: const ValueKey('unlock-confirm'),
            onTap: _loading ? null : _handleUnlock,
            child: Container(
              constraints: const BoxConstraints(minHeight: 54),
              alignment: Alignment.center,
              child: _loading
                  ? const SizedBox(
                      width: 22,
                      height: 22,
                      child: CircularProgressIndicator(
                        strokeWidth: 2.5,
                        color: QfColors.onGreen,
                      ),
                    )
                  : Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(
                          Icons.lock_open_rounded,
                          size: 18,
                          color: QfColors.onGreen,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          l10n.unlockActionCost(cost),
                          style: const TextStyle(
                            fontFamily: qfDisplay,
                            fontSize: 17,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 1.4,
                            color: QfColors.onGreen,
                          ),
                        ),
                      ],
                    ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildMissingActions(BuildContext context, int missing) {
    final l10n = context.l10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            Expanded(
              child: _buildShortcutCard(
                amount: '+5',
                label: l10n.unlockShortcutVideo,
                onTap: () {
                  Navigator.of(context).pop(false);
                  widget.onEarnCoins();
                },
              ),
            ),
            const SizedBox(width: 6),
            Expanded(
              child: _buildShortcutCard(
                amount: '+10',
                label: l10n.unlockShortcutAttendance,
                onTap: () {
                  Navigator.of(context).pop(false);
                  widget.onEarnCoins();
                },
              ),
            ),
            const SizedBox(width: 6),
            Expanded(
              child: _buildShortcutCard(
                amount: '+200',
                label: l10n.unlockShortcutOffers,
                onTap: () {
                  Navigator.of(context).pop(false);
                  widget.onEarnCoins();
                },
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Container(
          decoration: BoxDecoration(
            boxShadow: [
              BoxShadow(
                color: QfColors.green.withValues(alpha: .16),
                blurRadius: 28,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: Material(
            color: Colors.transparent,
            shape: const CutCornerBorder(cut: 8),
            clipBehavior: Clip.antiAlias,
            child: Ink(
              decoration: const BoxDecoration(
                gradient: qfGreenGradient,
              ),
              child: InkWell(
                key: const ValueKey('need-coins-go'),
                onTap: () {
                  Navigator.of(context).pop(false);
                  widget.onEarnCoins();
                },
                child: Container(
                  constraints: const BoxConstraints(minHeight: 54),
                  alignment: Alignment.center,
                  child: Text(
                    l10n.unlockEarnAction(missing),
                    style: const TextStyle(
                      fontFamily: qfDisplay,
                      fontSize: 17,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1.4,
                      color: QfColors.onGreen,
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildShortcutCard({
    required String amount,
    required String label,
    required VoidCallback onTap,
  }) {
    return Material(
      color: QfColors.surface2,
      shape: const CutCornerBorder(
        cut: 6,
        side: BorderSide(color: QfColors.border, width: 1),
      ),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Container(
          constraints: const BoxConstraints(minHeight: 52),
          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 6),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                amount,
                style: const TextStyle(
                  fontFamily: qfMono,
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  color: QfColors.yellow,
                  height: 1,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                label,
                textAlign: TextAlign.center,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontFamily: qfDisplay,
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  letterSpacing: .6,
                  color: QfColors.text2,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildVipCard(BuildContext context) {
    final l10n = context.l10n;
    final subText = widget.monthlyPrice != null
        ? l10n.unlockVipSubPrice(widget.monthlyPrice!)
        : l10n.unlockVipSubNoPrice;

    return Material(
      color: QfColors.yellow.withValues(alpha: .07),
      shape: CutCornerBorder(
        cut: 8,
        side: BorderSide(
          color: QfColors.yellow.withValues(alpha: .5),
          width: 1,
        ),
      ),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () {
          Navigator.of(context).pop(false);
          widget.onVip();
        },
        child: Container(
          constraints: const BoxConstraints(minHeight: 56),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          child: Row(
            children: [
              const Icon(
                Icons.workspace_premium_rounded,
                color: QfColors.yellow,
                size: 26,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      l10n.unlockVipTitle,
                      style: const TextStyle(
                        fontFamily: qfBody,
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: QfColors.yellow,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      subText,
                      style: const TextStyle(
                        fontFamily: qfBody,
                        fontSize: 12,
                        color: QfColors.text2,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              const Icon(
                Icons.chevron_right_rounded,
                color: QfColors.yellow,
                size: 18,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
