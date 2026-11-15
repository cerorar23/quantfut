import 'dart:math' as math;

import 'package:flutter/material.dart';

/// Familias tipográficas CyberCore.
const qfDisplay = 'Rajdhani';
const qfTitleFont = 'Rajdhani';
const qfMono = 'JetBrains Mono';
const qfBody = 'Exo 2';

/// Tokens de color CyberCore (§3.1 del plan de rediseño).
abstract final class QfColors {
  // Fondos y superficies
  static const bg = Color(0xFF07080C);
  static const surface = Color(0xFF12141D);
  static const surface2 = Color(0xFF181A25);

  // Tipografía y neutrales
  static const text = Color(0xFFF0F1F5);
  static const text2 = Color(0xFFB2B7C7);
  static const muted = Color(0xFF939AB0);
  static const chrome = Color(0xFFD1D4DE);
  static const slate = Color(0xFF747D99);
  static const track = Color(0xFF2A2D3A);

  // Acentos semánticos
  static const cyan = Color(0xFF00F0FF);
  static const green = Color(0xFF05FFA1);
  static const yellow = Color(0xFFFCEE0A);
  static const magenta = Color(0xFFFF2A6D);
  static const magentaText = Color(0xFFFF7AA3);

  // Textos de alto contraste sobre botones / acentos
  static const onGreen = Color(0xFF03110F);
  static const onYellow = Color(0xFF1A1800);

  // Derivados de diseño (constantes ARGB compilables)
  static const border = Color(0x3300F0FF); // cyan 20% alpha (--b)
  static const borderStrong = Color(0x7A00F0FF); // cyan 48% alpha (--bs)
  static const divider = Color(0x38747D99); // slate 22% alpha (--ln)
  static const chipActiveBg = Color(0x1A00F0FF); // cyan 10% alpha

  // Compatibilidad con código previo durante la migración
  static const primary = cyan;
  static const onPrimary = onGreen;
  static const cta = green;
  static const onCta = onGreen;
  static const success = green;
  static const danger = magenta;

}

/// Espaciados del sistema CyberCore.
abstract final class QfSpace {
  static const double xs = 4.0;
  static const double sm = 8.0;
  static const double md = 12.0;
  static const double lg = 16.0;
  static const double xl = 20.0;
  static const double xxl = 24.0;
  static const double xxxl = 32.0;
}

/// Gradiente verde para la acción principal.
const qfGreenGradient = LinearGradient(
  begin: Alignment.topLeft,
  end: Alignment.bottomRight,
  colors: [QfColors.green, Color(0xFF8AFFDF)],
);

/// Escala tipográfica precalculada CyberCore (§3.2).
abstract final class QfText {
  static const brand = TextStyle(
    fontFamily: qfDisplay,
    fontSize: 21,
    fontWeight: FontWeight.w700,
    letterSpacing: 2.94, // 0.14 em
    color: QfColors.text,
  );

  static const heroTitle = TextStyle(
    fontFamily: qfDisplay,
    fontSize: 32,
    fontWeight: FontWeight.w700,
    letterSpacing: 0.64, // 0.02 em
    height: 1.05,
    color: QfColors.text,
  );

  static const sectionTitle = TextStyle(
    fontFamily: qfDisplay,
    fontSize: 22,
    fontWeight: FontWeight.w700,
    letterSpacing: 0.88, // 0.04 em
    color: QfColors.text,
  );

  static const sectionTag = TextStyle(
    fontFamily: qfDisplay,
    fontSize: 11,
    fontWeight: FontWeight.w700,
    letterSpacing: 1.98, // 0.18 em
    color: QfColors.cyan,
  );

  static const tab = TextStyle(
    fontFamily: qfDisplay,
    fontSize: 13,
    fontWeight: FontWeight.w700,
    letterSpacing: 1.04, // 0.08 em
    color: QfColors.text,
  );

  static const chip = TextStyle(
    fontFamily: qfDisplay,
    fontSize: 13,
    fontWeight: FontWeight.w700,
    letterSpacing: 1.04,
    color: QfColors.text,
  );

  static const button = TextStyle(
    fontFamily: qfDisplay,
    fontSize: 14,
    fontWeight: FontWeight.w700,
    letterSpacing: 1.12, // 0.08 em
    color: QfColors.onGreen,
  );

  static const badge = TextStyle(
    fontFamily: qfDisplay,
    fontSize: 11,
    fontWeight: FontWeight.w700,
    letterSpacing: 1.32, // 0.12 em
    color: QfColors.text,
  );

  static const statLarge = TextStyle(
    fontFamily: qfMono,
    fontSize: 42,
    fontWeight: FontWeight.w700,
    color: QfColors.cyan,
  );

  static const statMedium = TextStyle(
    fontFamily: qfMono,
    fontSize: 18,
    fontWeight: FontWeight.w700,
    color: QfColors.text,
  );

  static const statSmall = TextStyle(
    fontFamily: qfMono,
    fontSize: 13,
    fontWeight: FontWeight.w700,
    color: QfColors.text,
  );

  static const meta = TextStyle(
    fontFamily: qfMono,
    fontSize: 11,
    fontWeight: FontWeight.w500,
    color: QfColors.muted,
  );

  static const body = TextStyle(
    fontFamily: qfBody,
    fontSize: 14,
    fontWeight: FontWeight.w400,
    color: QfColors.text,
  );

  static const bodyMedium = TextStyle(
    fontFamily: qfBody,
    fontSize: 13,
    fontWeight: FontWeight.w400,
    color: QfColors.text2,
  );

  static const bodySmall = TextStyle(
    fontFamily: qfBody,
    fontSize: 11,
    fontWeight: FontWeight.w400,
    color: QfColors.muted,
  );

  static const teamName = TextStyle(
    fontFamily: qfBody,
    fontSize: 15,
    fontWeight: FontWeight.w700,
    color: QfColors.text,
  );
}

/// Tema CyberCore oscuro unificado para la app.
ThemeData qfTheme() => ThemeData.dark(useMaterial3: true).copyWith(
  scaffoldBackgroundColor: QfColors.bg,
  colorScheme: ColorScheme.dark(
    primary: QfColors.cyan,
    onPrimary: QfColors.onGreen,
    secondary: QfColors.yellow,
    onSecondary: QfColors.onYellow,
    surface: QfColors.surface,
    onSurface: QfColors.text,
    error: QfColors.magenta,
    outline: QfColors.border,
  ),
  textTheme: ThemeData.dark().textTheme.apply(
    fontFamily: qfBody,
    bodyColor: QfColors.text,
    displayColor: QfColors.text,
  ),
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
