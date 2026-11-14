import 'package:flutter/material.dart';

import 'qf_shapes.dart';
import 'qf_theme.dart';

/// Variantes de botón CyberCore (§4 y §3.1).
enum QfButtonVariant {
  primary, // Gradiente verde, acción principal (una sola por pantalla)
  secondary, // Borde cian, fondo transparente o surface2
  vip, // Borde amarillo, fondo transparente o yellow@9%
  danger, // Texto magentaText sobre fondo transparente / surface2
  google, // Fondo blanco, texto oscuro, botón oficial Google
}

/// Botón CyberCore (mínimo 44 dp de altura, esquinas cortadas 10 dp).
class QfButton extends StatelessWidget {
  const QfButton({
    super.key,
    required this.label,
    this.variant = QfButtonVariant.primary,
    this.onPressed,
    this.icon,
    this.busy = false,
    this.height = 48,
    this.width,
  });

  const QfButton.secondary({
    super.key,
    required this.label,
    this.onPressed,
    this.icon,
    this.busy = false,
    this.height = 44,
    this.width,
  }) : variant = QfButtonVariant.secondary;

  const QfButton.vip({
    super.key,
    required this.label,
    this.onPressed,
    this.icon,
    this.busy = false,
    this.height = 44,
    this.width,
  }) : variant = QfButtonVariant.vip;

  const QfButton.danger({
    super.key,
    required this.label,
    this.onPressed,
    this.icon,
    this.busy = false,
    this.height = 44,
    this.width,
  }) : variant = QfButtonVariant.danger;

  const QfButton.google({
    super.key,
    required this.label,
    this.onPressed,
    this.icon,
    this.busy = false,
    this.height = 48,
    this.width,
  }) : variant = QfButtonVariant.google;

  final String label;
  final QfButtonVariant variant;
  final VoidCallback? onPressed;
  final Widget? icon;
  final bool busy;
  final double height;
  final double? width;

  @override
  Widget build(BuildContext context) {
    const cut = 10.0;

    // Colores y decoraciones según variante
    Decoration decoration;
    Color textColor;
    OutlinedBorder shape;

    switch (variant) {
      case QfButtonVariant.primary:
        decoration = BoxDecoration(
          gradient: onPressed == null ? null : qfGreenGradient,
          color: onPressed == null ? QfColors.track : null,
          boxShadow: onPressed == null
              ? null
              : [
                  BoxShadow(
                    color: QfColors.green.withValues(alpha: .16),
                    blurRadius: 28,
                    offset: const Offset(0, 8),
                  ),
                ],
        );
        textColor = onPressed == null ? QfColors.muted : QfColors.onGreen;
        shape = const CutCornerBorder(cut: cut);

      case QfButtonVariant.secondary:
        decoration = BoxDecoration(
          color: QfColors.cyan.withValues(alpha: .06),
        );
        textColor = QfColors.cyan;
        shape = CutCornerBorder(
          cut: cut,
          side: BorderSide(
            color: onPressed == null ? QfColors.track : QfColors.cyan.withValues(alpha: .5),
          ),
        );

      case QfButtonVariant.vip:
        decoration = BoxDecoration(
          color: QfColors.yellow.withValues(alpha: .08),
        );
        textColor = QfColors.yellow;
        shape = CutCornerBorder(
          cut: cut,
          side: BorderSide(
            color: onPressed == null ? QfColors.track : QfColors.yellow.withValues(alpha: .6),
          ),
        );

      case QfButtonVariant.danger:
        decoration = BoxDecoration(
          color: QfColors.magenta.withValues(alpha: .08),
        );
        textColor = QfColors.magentaText;
        shape = CutCornerBorder(
          cut: cut,
          side: BorderSide(
            color: onPressed == null ? QfColors.track : QfColors.magenta.withValues(alpha: .4),
          ),
        );

      case QfButtonVariant.google:
        decoration = const BoxDecoration(
          color: Colors.white,
        );
        textColor = const Color(0xFF1F1F1F);
        shape = const CutCornerBorder(cut: cut);
    }

    Widget inner = Row(
      mainAxisSize: width == null ? MainAxisSize.min : MainAxisSize.max,
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        if (busy) ...[
          SizedBox(
            width: 16,
            height: 16,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              color: textColor,
            ),
          ),
          const SizedBox(width: 8),
        ] else if (icon != null) ...[
          icon!,
          const SizedBox(width: 8),
        ],
        Flexible(
          child: Text(
            label.toUpperCase(),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontFamily: qfDisplay,
              fontWeight: FontWeight.w700,
              fontSize: 14,
              letterSpacing: 1.12,
              color: textColor,
            ),
          ),
        ),
      ],
    );

    return SizedBox(
      height: height.clamp(44.0, double.infinity),
      width: width,
      child: Material(
        shape: shape,
        clipBehavior: Clip.antiAlias,
        color: Colors.transparent,
        child: Ink(
          decoration: decoration,
          child: InkWell(
            customBorder: shape,
            onTap: (busy || onPressed == null) ? null : onPressed,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              child: Center(child: inner),
            ),
          ),
        ),
      ),
    );
  }
}

/// Interruptor CyberCore de 52×30 dp con borde y perilla cuadrada (CutCornerBorder 4 dp).
class QfSwitch extends StatelessWidget {
  const QfSwitch({
    super.key,
    required this.value,
    required this.onChanged,
    this.semanticLabel,
  });

  final bool value;
  final ValueChanged<bool>? onChanged;
  final String? semanticLabel;

  @override
  Widget build(BuildContext context) {
    const width = 52.0;
    const height = 30.0;
    const thumbSize = 22.0;

    return Semantics(
      label: semanticLabel,
      toggled: value,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onChanged == null ? null : () => onChanged!(!value),
        child: ConstrainedBox(
          constraints: const BoxConstraints(minWidth: 52, minHeight: 44),
          child: Center(
            child: Container(
              width: width,
              height: height,
              padding: const EdgeInsets.all(3),
              decoration: ShapeDecoration(
                color: value ? QfColors.cyan.withValues(alpha: .18) : QfColors.surface2,
                shape: CutCornerBorder(
                  cut: 6,
                  side: BorderSide(
                    color: value ? QfColors.cyan : QfColors.slate.withValues(alpha: .4),
                    width: 1,
                  ),
                ),
              ),
              child: AnimatedAlign(
                duration: const Duration(milliseconds: 150),
                curve: Curves.easeInOut,
                alignment: value ? Alignment.centerRight : Alignment.centerLeft,
                child: Container(
                  width: thumbSize,
                  height: thumbSize,
                  decoration: ShapeDecoration(
                    color: value ? QfColors.cyan : QfColors.slate,
                    shape: const CutCornerBorder(cut: 4),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Casilla de verificación CyberCore de 22×22 dp (✓ negro sobre verde o cian).
class QfCheckbox extends StatelessWidget {
  const QfCheckbox({
    super.key,
    required this.value,
    required this.onChanged,
    this.semanticLabel,
    this.activeColor = QfColors.green,
  });

  final bool value;
  final ValueChanged<bool>? onChanged;
  final String? semanticLabel;
  final Color activeColor;

  @override
  Widget build(BuildContext context) {
    const size = 22.0;

    return Semantics(
      label: semanticLabel,
      checked: value,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onChanged == null ? null : () => onChanged!(!value),
        child: Container(
          width: 44,
          height: 44,
          alignment: Alignment.center,
          child: Container(
            width: size,
            height: size,
            decoration: ShapeDecoration(
              color: value ? activeColor : QfColors.surface2,
              shape: CutCornerBorder(
                cut: 4,
                side: BorderSide(
                  color: value ? activeColor : QfColors.slate.withValues(alpha: .5),
                  width: 1,
                ),
              ),
            ),
            child: value
                ? const Icon(
                    Icons.check_rounded,
                    size: 16,
                    color: QfColors.onGreen,
                  )
                : null,
          ),
        ),
      ),
    );
  }
}

/// Modo de visualización de pestañas CyberCore.
enum QfTabsMode {
  segmented, // Contenedor cerrado de 2-5 pestañas, activa con subrayado cian 2 dp
  chips, // Barra desplazable horizontal con chips independientes
}

/// Pieza unificada de pestañas CyberCore (§4 y §5.1).
class QfTabs extends StatelessWidget {
  const QfTabs({
    super.key,
    required this.labels,
    required this.index,
    required this.onChanged,
    this.mode = QfTabsMode.segmented,
    this.counts,
    this.icons,
    this.fontSize,
  });

  final List<String> labels;
  final int index;
  final ValueChanged<int> onChanged;
  final QfTabsMode mode;
  final List<int?>? counts;
  final List<IconData?>? icons;
  final double? fontSize;

  @override
  Widget build(BuildContext context) {
    if (mode == QfTabsMode.segmented) {
      return _buildSegmented();
    }
    return _buildChips();
  }

  Widget _buildSegmented() {
    return Container(
      height: 44,
      decoration: ShapeDecoration(
        color: QfColors.surface,
        shape: CutCornerBorder(
          cut: 8,
          side: BorderSide(color: QfColors.border),
        ),
      ),
      child: Row(
        children: [
          for (var i = 0; i < labels.length; i++) ...[
            if (i > 0)
              VerticalDivider(
                width: 1,
                thickness: 1,
                color: QfColors.divider,
              ),
            Expanded(
              child: _SegmentTab(
                label: labels[i],
                selected: i == index,
                count: counts != null && i < counts!.length ? counts![i] : null,
                icon: icons != null && i < icons!.length ? icons![i] : null,
                fontSize: fontSize,
                onTap: () => onChanged(i),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildChips() {
    return SizedBox(
      height: 44,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 4),
        itemCount: labels.length,
        separatorBuilder: (_, i) => const SizedBox(width: 8),
        itemBuilder: (context, i) {
          final isSelected = i == index;
          return _ChipTab(
            label: labels[i],
            selected: isSelected,
            count: counts != null && i < counts!.length ? counts![i] : null,
            icon: icons != null && i < icons!.length ? icons![i] : null,
            fontSize: fontSize,
            onTap: () => onChanged(i),
          );
        },
      ),
    );
  }
}

class _SegmentTab extends StatelessWidget {
  const _SegmentTab({
    required this.label,
    required this.selected,
    required this.onTap,
    this.count,
    this.icon,
    this.fontSize,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;
  final int? count;
  final IconData? icon;
  final double? fontSize;

  @override
  Widget build(BuildContext context) {
    final effectiveFont = fontSize ?? (label.length > 8 ? 11.0 : 13.0);

    return InkWell(
      onTap: onTap,
      child: Stack(
        alignment: Alignment.center,
        children: [
          if (selected)
            Positioned(
              bottom: 0,
              left: 8,
              right: 8,
              child: Container(
                height: 2,
                color: QfColors.cyan,
              ),
            ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                if (icon != null) ...[
                  Icon(
                    icon,
                    size: 14,
                    color: selected ? QfColors.cyan : QfColors.text2,
                  ),
                  const SizedBox(width: 4),
                ],
                Flexible(
                  child: Text(
                    label.toUpperCase(),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontFamily: qfDisplay,
                      fontWeight: FontWeight.w700,
                      fontSize: effectiveFont,
                      letterSpacing: .8,
                      color: selected ? QfColors.cyan : QfColors.text2,
                    ),
                  ),
                ),
                if (count != null) ...[
                  const SizedBox(width: 4),
                  Text(
                    '($count)',
                    style: TextStyle(
                      fontFamily: qfMono,
                      fontWeight: FontWeight.w700,
                      fontSize: 11,
                      color: selected ? QfColors.cyan : QfColors.muted,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ChipTab extends StatelessWidget {
  const _ChipTab({
    required this.label,
    required this.selected,
    required this.onTap,
    this.count,
    this.icon,
    this.fontSize,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;
  final int? count;
  final IconData? icon;
  final double? fontSize;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        customBorder: const CutCornerBorder(cut: 8),
        child: Container(
          height: 38,
          padding: const EdgeInsets.symmetric(horizontal: 14),
          alignment: Alignment.center,
          decoration: ShapeDecoration(
            color: selected ? QfColors.cyan.withValues(alpha: .10) : QfColors.surface,
            shape: CutCornerBorder(
              cut: 8,
              side: BorderSide(
                color: selected ? QfColors.cyan : QfColors.border,
                width: selected ? 1.5 : 1.0,
              ),
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (icon != null) ...[
                Icon(
                  icon,
                  size: 14,
                  color: selected ? QfColors.cyan : QfColors.text2,
                ),
                const SizedBox(width: 6),
              ],
              Text(
                label.toUpperCase(),
                style: TextStyle(
                  fontFamily: qfDisplay,
                  fontWeight: FontWeight.w700,
                  fontSize: fontSize ?? 13,
                  letterSpacing: .8,
                  color: selected ? QfColors.cyan : QfColors.text2,
                ),
              ),
              if (count != null) ...[
                const SizedBox(width: 6),
                Text(
                  '($count)',
                  style: TextStyle(
                    fontFamily: qfMono,
                    fontWeight: FontWeight.w700,
                    fontSize: 11,
                    color: selected ? QfColors.cyan : QfColors.muted,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// Barra fija de acceso directo que salta a secciones de una pestaña larga (§4).
class QfSectionNav extends StatelessWidget {
  const QfSectionNav({
    super.key,
    required this.sections,
    this.selectedIndex = 0,
    this.onSelected,
  });

  final List<(String label, GlobalKey key)> sections;
  final int selectedIndex;
  final ValueChanged<int>? onSelected;

  void _jumpTo(int index, BuildContext context) {
    onSelected?.call(index);
    final key = sections[index].$2;
    if (key.currentContext != null) {
      Scrollable.ensureVisible(
        key.currentContext!,
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeInOut,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 46,
      color: QfColors.bg,
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 16),
        itemCount: sections.length,
        separatorBuilder: (_, i) => const SizedBox(width: 8),
        itemBuilder: (context, i) {
          final isSelected = i == selectedIndex;
          return Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: () => _jumpTo(i, context),
              customBorder: const CutCornerBorder(cut: 6),
              child: Container(
                height: 34,
                padding: const EdgeInsets.symmetric(horizontal: 12),
                alignment: Alignment.center,
                decoration: ShapeDecoration(
                  color: isSelected ? QfColors.cyan.withValues(alpha: .12) : QfColors.surface2,
                  shape: CutCornerBorder(
                    cut: 6,
                    side: BorderSide(
                      color: isSelected ? QfColors.cyan : QfColors.border,
                      width: 1,
                    ),
                  ),
                ),
                child: Text(
                  sections[i].$1.toUpperCase(),
                  style: TextStyle(
                    fontFamily: qfDisplay,
                    fontWeight: FontWeight.w700,
                    fontSize: 12,
                    letterSpacing: .7,
                    color: isSelected ? QfColors.cyan : QfColors.text2,
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

/// Puntos de paginación CyberCore (activo 26×6 cian, resto 6×6 `#3A3F55`).
class QfStepDots extends StatelessWidget {
  const QfStepDots({
    super.key,
    required this.count,
    required this.index,
    this.onTap,
  });

  final int count;
  final int index;
  final ValueChanged<int>? onTap;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        for (var i = 0; i < count; i++) ...[
          if (i > 0) const SizedBox(width: 8),
          GestureDetector(
            onTap: onTap != null ? () => onTap!(i) : null,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 180),
              width: i == index ? 26.0 : 6.0,
              height: 6.0,
              decoration: BoxDecoration(
                color: i == index ? QfColors.cyan : const Color(0xFF3A3F55),
                borderRadius: BorderRadius.circular(3),
              ),
            ),
          ),
        ],
      ],
    );
  }
}
