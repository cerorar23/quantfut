import 'package:flutter/material.dart';

import 'qf_shapes.dart';
import 'qf_theme.dart';

/// Hoja inferior CyberCore con esquinas superiores cortadas 18 dp, asa 44×4 y borde cian (§4 y §3.3).
class QfBottomSheet extends StatelessWidget {
  const QfBottomSheet({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.fromLTRB(16, 8, 16, 24),
  });

  final Widget child;
  final EdgeInsets padding;

  /// Abre un modal bottom sheet con el estilo CyberCore.
  static Future<T?> show<T>({
    required BuildContext context,
    required WidgetBuilder builder,
    bool isScrollControlled = true,
    bool isDismissible = true,
  }) {
    return showModalBottomSheet<T>(
      context: context,
      isScrollControlled: isScrollControlled,
      isDismissible: isDismissible,
      backgroundColor: Colors.transparent,
      elevation: 0,
      builder: (ctx) => QfBottomSheet(child: builder(ctx)),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        boxShadow: [
          BoxShadow(
            color: QfColors.cyan.withValues(alpha: .12),
            blurRadius: 28,
            offset: const Offset(0, -6),
          ),
        ],
      ),
      child: Material(
        color: QfColors.surface,
        shape: BottomSheetCutShape(
          cut: 18,
          side: BorderSide(color: QfColors.borderStrong, width: 1.5),
        ),
        clipBehavior: Clip.antiAlias,
        child: SafeArea(
          top: false,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Asa superior CyberCore 44×4 dp
              Padding(
                padding: const EdgeInsets.only(top: 10, bottom: 8),
                child: Container(
                  width: 44,
                  height: 4,
                  decoration: BoxDecoration(
                    color: QfColors.slate.withValues(alpha: .5),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              Padding(
                padding: padding,
                child: child,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Diálogo centrado CyberCore con esquinas cortadas 16 dp (§4 y §5.14).
class QfDialogCard extends StatelessWidget {
  const QfDialogCard({
    super.key,
    this.icon,
    this.iconColor = QfColors.cyan,
    required this.title,
    required this.content,
    required this.actions,
  });

  final IconData? icon;
  final Color iconColor;
  final String title;
  final Widget content;
  final List<Widget> actions;

  /// Muestra un diálogo modal centrado con el estilo CyberCore.
  static Future<T?> show<T>({
    required BuildContext context,
    IconData? icon,
    Color iconColor = QfColors.cyan,
    required String title,
    required Widget content,
    required List<Widget> actions,
    bool barrierDismissible = true,
  }) {
    return showDialog<T>(
      context: context,
      barrierDismissible: barrierDismissible,
      barrierColor: Colors.black.withValues(alpha: .75),
      builder: (ctx) => QfDialogCard(
        icon: icon,
        iconColor: iconColor,
        title: title,
        content: content,
        actions: actions,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: Colors.transparent,
      elevation: 0,
      insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
      child: Container(
        decoration: BoxDecoration(
          boxShadow: [
            BoxShadow(
              color: QfColors.cyan.withValues(alpha: .15),
              blurRadius: 32,
              spreadRadius: 2,
            ),
          ],
        ),
        child: Material(
          color: QfColors.surface,
          shape: CutCornerBorder(
            cut: 16,
            side: BorderSide(color: QfColors.borderStrong, width: 1.5),
          ),
          clipBehavior: Clip.antiAlias,
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (icon != null) ...[
                  Center(
                    child: Container(
                      width: 48,
                      height: 48,
                      decoration: ShapeDecoration(
                        color: iconColor.withValues(alpha: .12),
                        shape: CutCornerBorder(
                          cut: 8,
                          side: BorderSide(color: iconColor.withValues(alpha: .4)),
                        ),
                      ),
                      child: Icon(icon, color: iconColor, size: 24),
                    ),
                  ),
                  const SizedBox(height: 14),
                ],
                Text(
                  title.toUpperCase(),
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontFamily: qfDisplay,
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                    letterSpacing: .8,
                    color: QfColors.text,
                  ),
                ),
                const SizedBox(height: 14),
                DefaultTextStyle(
                  style: const TextStyle(
                    fontFamily: qfBody,
                    fontSize: 14,
                    color: QfColors.text2,
                    height: 1.45,
                  ),
                  textAlign: TextAlign.center,
                  child: content,
                ),
                const SizedBox(height: 22),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    for (var i = 0; i < actions.length; i++) ...[
                      if (i > 0) const SizedBox(height: 8),
                      actions[i],
                    ],
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
