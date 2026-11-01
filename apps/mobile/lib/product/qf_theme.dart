import 'dart:math' as math;

import 'package:flutter/material.dart';

/// Familias de la piel v3: titulares/chips y cifras/hashes.
const qfDisplay = 'Rajdhani';
const qfMono = 'JetBrains Mono';

/// Paleta v3 (azul + ámbar). Texto sobre `cta`: `onCta`; sobre `primary`:
/// `onPrimary` (nunca blanco, no llega a 4,5:1).
abstract final class QfColors {
  static const bg = Color(0xff070b14),
      surface = Color(0xff0f1829),
      surface2 = Color(0xff16223a),
      border = Color(0xff26365a),
      text = Color(0xffeef3ff),
      text2 = Color(0xff9daccb),
      muted = Color(0xff7f8dad),
      primary = Color(0xff4c8dff),
      onPrimary = Color(0xff04122e),
      cta = Color(0xffffb020),
      onCta = Color(0xff1a1200),
      success = Color(0xff2bd99f),
      danger = Color(0xffff6b6b),
      football = Color(0xff22d3ee),
      nba = Color(0xffb58cff),
      tennis = Color(0xffd4f53c);
}

ThemeData qfTheme() => ThemeData.dark(useMaterial3: true).copyWith(
  scaffoldBackgroundColor: QfColors.bg,
  colorScheme: const ColorScheme.dark(
    primary: QfColors.primary,
    onPrimary: QfColors.onPrimary,
    secondary: QfColors.cta,
    onSecondary: QfColors.onCta,
    surface: QfColors.surface,
    onSurface: QfColors.text,
    error: QfColors.danger,
    outline: QfColors.border,
  ),
  textTheme: ThemeData.dark().textTheme.apply(fontFamily: 'Gilroy Medium'),
);

double _luminance(Color c) {
  double lin(double v) =>
      v <= 0.03928 ? v / 12.92 : math.pow((v + 0.055) / 1.055, 2.4).toDouble();
  return 0.2126 * lin(c.r) + 0.7152 * lin(c.g) + 0.0722 * lin(c.b);
}

/// Contraste WCAG 2.1 entre dos colores (1 a 21).
double contrastRatio(Color a, Color b) {
  final la = _luminance(a), lb = _luminance(b);
  return (math.max(la, lb) + 0.05) / (math.min(la, lb) + 0.05);
}
