import 'dart:math' as math;
import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';

/// Datos de un participante (equipo o jugador) en el hero del partido.
class MatchHeroSide {
  const MatchHeroSide({
    required this.name,
    required this.image,
    this.sub,
  });

  final String name;
  final Widget image;
  final String? sub;
}

/// Parte de la barra de probabilidad en el hero.
class MatchProbabilityPart {
  const MatchProbabilityPart({
    required this.label,
    required this.percent,
    required this.color,
  });

  final String label;
  final double percent; // 0..100
  final Color color;
}

/// Cabecera superior fija de la ficha de partido (liga, fecha/hora y botón cerrar).
class MatchTopBar extends StatelessWidget {
  const MatchTopBar({
    super.key,
    required this.league,
    required this.when,
    this.onClose,
  });

  final String league;
  final String when;
  final VoidCallback? onClose;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Container(
      height: 56,
      padding: const EdgeInsets.only(left: 14, right: 6),
      decoration: const BoxDecoration(
        color: QfColors.bg,
        border: Border(bottom: BorderSide(color: QfColors.border)),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  league.toUpperCase(),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontFamily: qfDisplay,
                    fontWeight: FontWeight.w700,
                    fontSize: 13,
                    letterSpacing: 1.4,
                    color: QfColors.green,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  when,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontFamily: qfMono,
                    fontWeight: FontWeight.w500,
                    fontSize: 11,
                    color: QfColors.text2,
                  ),
                ),
              ],
            ),
          ),
          IconButton(
            tooltip: l10n.commonClose,
            icon: const Icon(Icons.close, color: QfColors.text2, size: 22),
            onPressed: onClose ?? () => Navigator.maybePop(context),
          ),
        ],
      ),
    );
  }
}

/// Hero del partido con participantes, probabilidad destacada, barra y leyenda.
class MatchHero extends StatelessWidget {
  const MatchHero({
    super.key,
    required this.sideA,
    required this.sideB,
    this.bigProb,
    this.bigLabel,
    this.centerExtra,
    this.probs,
    this.badges,
    this.credits,
  });

  final MatchHeroSide sideA;
  final MatchHeroSide sideB;
  final String? bigProb;
  final String? bigLabel;
  final Widget? centerExtra;
  final List<MatchProbabilityPart>? probs;
  final List<Widget>? badges;
  final List<Widget>? credits;

  Widget _buildSide(MatchHeroSide side) => Expanded(
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        SizedBox(
          width: 58,
          height: 58,
          child: Center(child: side.image),
        ),
        const SizedBox(height: 6),
        Text(
          side.name,
          textAlign: TextAlign.center,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(
            fontFamily: qfDisplay,
            fontWeight: FontWeight.w700,
            fontSize: 15,
            color: QfColors.text,
          ),
        ),
        if (side.sub != null && side.sub!.isNotEmpty) ...[
          const SizedBox(height: 2),
          Text(
            side.sub!,
            textAlign: TextAlign.center,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              fontFamily: qfMono,
              fontWeight: FontWeight.w500,
              fontSize: 10,
              color: QfColors.text2,
            ),
          ),
        ],
      ],
    ),
  );

  @override
  Widget build(BuildContext context) {
    return QfCard(
      strong: true,
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (badges != null && badges!.isNotEmpty) ...[
            Wrap(
              spacing: 8,
              runSpacing: 6,
              children: badges!,
            ),
            const SizedBox(height: 12),
          ],
          Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              _buildSide(sideA),
              Expanded(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (bigProb != null && bigProb!.isNotEmpty) ...[
                      Text(
                        bigProb!,
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          fontFamily: qfMono,
                          fontWeight: FontWeight.w700,
                          fontSize: 38,
                          height: 1.0,
                          color: QfColors.cyan,
                          shadows: [
                            Shadow(
                              color: Color.fromRGBO(0, 240, 255, 0.45),
                              blurRadius: 18,
                            ),
                          ],
                        ),
                      ),
                      if (bigLabel != null && bigLabel!.isNotEmpty) ...[
                        const SizedBox(height: 6),
                        Text(
                          bigLabel!,
                          textAlign: TextAlign.center,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            fontFamily: qfDisplay,
                            fontWeight: FontWeight.w700,
                            fontSize: 12,
                            letterSpacing: 1.2,
                            color: QfColors.text2,
                          ),
                        ),
                      ],
                    ],
                    if (centerExtra != null) ...[
                      const SizedBox(height: 4),
                      centerExtra!,
                    ],
                  ],
                ),
              ),
              _buildSide(sideB),
            ],
          ),
          if (probs != null && probs!.isNotEmpty) ...[
            const SizedBox(height: 12),
            SizedBox(
              height: 6,
              child: Row(
                children: [
                  for (var i = 0; i < probs!.length; i++) ...[
                    if (i > 0) const SizedBox(width: 3),
                    Expanded(
                      flex: math.max(1, (probs![i].percent * 10).round()),
                      child: Container(
                        decoration: BoxDecoration(
                          color: probs![i].color,
                          borderRadius: BorderRadius.circular(1),
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 6),
            Row(
              children: [
                for (var i = 0; i < probs!.length; i++) ...[
                  if (i > 0) const SizedBox(width: 4),
                  Expanded(
                    child: Text(
                      '${probs![i].label} · ${probs![i].percent.round()}%',
                      textAlign: i == 0
                          ? TextAlign.left
                          : (i == probs!.length - 1
                              ? TextAlign.right
                              : TextAlign.center),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontFamily: qfMono,
                        fontWeight: FontWeight.w500,
                        fontSize: 11,
                        color: QfColors.text2,
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ],
          if (credits != null && credits!.isNotEmpty) ...[
            const SizedBox(height: 8),
            for (final c in credits!) c,
          ],
        ],
      ),
    );
  }
}

/// Selector de pestañas del partido (Pronóstico · Análisis · H2H · Alertas · Props).
class MatchTabs extends StatelessWidget {
  const MatchTabs({
    super.key,
    required this.labels,
    required this.index,
    required this.onChanged,
    this.alertIndex,
    this.alertCount,
  });

  final List<String> labels;
  final int index;
  final ValueChanged<int> onChanged;
  final int? alertIndex;
  final int? alertCount;

  @override
  Widget build(BuildContext context) {
    final fontSize = labels.length > 4 ? 11.0 : 12.0;

    return Container(
      height: 44,
      decoration: BoxDecoration(
        color: const Color.fromRGBO(3, 9, 17, 0.72),
        border: Border.all(color: QfColors.border),
      ),
      child: Row(
        children: [
          for (var i = 0; i < labels.length; i++) ...[
            if (i > 0)
              Container(
                width: 1,
                color: QfColors.border,
              ),
            Expanded(
              child: _MatchTabButton(
                label: labels[i],
                selected: i == index,
                fontSize: fontSize,
                badgeCount: i == alertIndex ? alertCount : null,
                isAlertTab: i == alertIndex,
                onTap: () => onChanged(i),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _MatchTabButton extends StatelessWidget {
  const _MatchTabButton({
    required this.label,
    required this.selected,
    required this.fontSize,
    required this.onTap,
    this.badgeCount,
    this.isAlertTab = false,
  });

  final String label;
  final bool selected;
  final double fontSize;
  final VoidCallback onTap;
  final int? badgeCount;
  final bool isAlertTab;

  @override
  Widget build(BuildContext context) {
    final count = badgeCount ?? 0;
    return Semantics(
      selected: selected,
      button: true,
      child: InkWell(
        onTap: onTap,
        child: Container(
          color: selected ? const Color.fromRGBO(0, 240, 255, 0.1) : Colors.transparent,
          child: Stack(
            alignment: Alignment.center,
            children: [
              if (selected)
                Positioned(
                  bottom: 0,
                  left: 0,
                  right: 0,
                  child: Container(
                    height: 2,
                    color: QfColors.cyan,
                  ),
                ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 2),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Flexible(
                      child: Text(
                        label,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontFamily: qfDisplay,
                          fontWeight: FontWeight.w700,
                          fontSize: fontSize,
                          letterSpacing: 0.3,
                          color: selected ? QfColors.cyan : QfColors.text2,
                        ),
                      ),
                    ),
                    if (isAlertTab && count > 0) ...[
                      const SizedBox(width: 4),
                      Container(
                        key: const ValueKey('alerts-tab-badge'),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 5,
                          vertical: 1,
                        ),
                        decoration: BoxDecoration(
                          color: QfColors.danger,
                          borderRadius: BorderRadius.circular(99),
                        ),
                        child: Text(
                          '$count',
                          style: const TextStyle(
                            color: QfColors.bg,
                            fontSize: 9,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Barra inferior fija de conversión en la ficha de partido.
class MatchBottomBar extends StatelessWidget {
  const MatchBottomBar({
    super.key,
    this.cost = 40,
    this.onUnlock,
    this.onVip,
  });

  final int cost;
  final VoidCallback? onUnlock;
  final VoidCallback? onVip;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Container(
      decoration: const BoxDecoration(
        color: QfColors.surface,
        border: Border(top: BorderSide(color: QfColors.border)),
      ),
      padding: const EdgeInsets.fromLTRB(14, 10, 14, 14),
      child: SafeArea(
        top: false,
        child: Row(
          children: [
            Expanded(
              flex: 2,
              child: SizedBox(
                height: 48,
                child: Material(
                  color: Colors.transparent,
                  shape: const CutCornerBorder(cut: 8),
                  clipBehavior: Clip.antiAlias,
                  child: Ink(
                    decoration: const BoxDecoration(
                      gradient: qfGreenGradient,
                    ),
                    child: InkWell(
                      onTap: onUnlock,
                      child: Center(
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(
                              Icons.lock_open,
                              size: 18,
                              color: Color(0xFF03110F),
                            ),
                            const SizedBox(width: 8),
                            Flexible(
                              child: Text(
                                l10n.detailUnlockAll(cost),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  fontFamily: qfDisplay,
                                  fontWeight: FontWeight.w700,
                                  fontSize: 15,
                                  letterSpacing: 1.2,
                                  color: Color(0xFF03110F),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
            if (onVip != null) ...[
              const SizedBox(width: 8),
              Expanded(
                flex: 1,
                child: SizedBox(
                  height: 48,
                  child: Material(
                    color: const Color(0x14FCEE0A),
                    shape: const CutCornerBorder(
                      cut: 8,
                      side: BorderSide(color: Color(0x80FCEE0A)),
                    ),
                    clipBehavior: Clip.antiAlias,
                    child: InkWell(
                      onTap: onVip,
                      child: const Center(
                        child: Text(
                          'VIP',
                          style: TextStyle(
                            fontFamily: qfDisplay,
                            fontWeight: FontWeight.w700,
                            fontSize: 15,
                            letterSpacing: 1.2,
                            color: QfColors.yellow,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Contenedor común de la ficha de partido para los 3 deportes.
class MatchShell extends StatelessWidget {
  const MatchShell({
    super.key,
    required this.header,
    required this.hero,
    required this.tabs,
    required this.body,
    this.bottomBar,
    this.scrollable = true,
  });

  final Widget header;
  final Widget hero;
  final Widget tabs;
  final Widget body;
  final Widget? bottomBar;
  final bool scrollable;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: QfColors.bg,
      child: Column(
        children: [
          header,
          Expanded(
            child: scrollable
                ? ListView(
                    padding: const EdgeInsets.fromLTRB(14, 12, 14, 16),
                    children: [
                      hero,
                      const SizedBox(height: 12),
                      tabs,
                      const SizedBox(height: 12),
                      body,
                    ],
                  )
                : Column(
                    children: [
                      hero,
                      const SizedBox(height: 12),
                      tabs,
                      Expanded(child: body),
                    ],
                  ),
          ),
          ?bottomBar,
        ],
      ),
    );
  }
}
