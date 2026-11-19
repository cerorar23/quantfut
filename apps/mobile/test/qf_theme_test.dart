import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/product/live_widgets.dart';
import 'package:gobet/product/qf_theme.dart';

void main() {
  test('texto legible en los tres fondos (WCAG >= 4.5)', () {
    const textos = [
      QfColors.text,
      QfColors.text2,
      QfColors.muted,
      QfColors.cyan,
      QfColors.green,
      QfColors.yellow,
      QfColors.magentaText,
      QfColors.chrome,
    ];
    const fondos = [QfColors.bg, QfColors.surface, QfColors.surface2];
    for (final c in textos) {
      for (final f in fondos) {
        expect(contrastRatio(c, f), greaterThanOrEqualTo(4.5),
            reason: '$c sobre $f');
      }
    }
  });

  test('texto sobre botones y acentos (WCAG >= 4.5)', () {
    expect(contrastRatio(QfColors.onGreen, QfColors.green),
        greaterThanOrEqualTo(4.5));
    expect(contrastRatio(QfColors.onGreen, QfColors.cyan),
        greaterThanOrEqualTo(4.5));
    expect(contrastRatio(QfColors.onYellow, QfColors.yellow),
        greaterThanOrEqualTo(4.5));
    // Blanco sobre verde o amarillo no alcanza el contraste exigido
    expect(contrastRatio(Colors.white, QfColors.yellow), lessThan(4.5));
  });

  test('los alias live* apuntan a los tokens CyberCore', () {
    expect(liveBg, QfColors.bg);
    expect(livePanel, QfColors.surface);
    expect(liveCyan, QfColors.cyan);
    expect(liveGold, QfColors.yellow);
    expect(liveGreen, QfColors.green);
    expect(liveMuted, QfColors.muted);
  });
}
