import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/product/live_widgets.dart';
import 'package:gobet/product/qf_theme.dart';

void main() {
  test('texto legible en los tres fondos', () {
    const textos = [
      QfColors.text, QfColors.text2, QfColors.muted, QfColors.primary,
      QfColors.cta, QfColors.success, QfColors.danger, QfColors.football,
      QfColors.nba, QfColors.tennis,
    ];
    const fondos = [QfColors.bg, QfColors.surface, QfColors.surface2];
    for (final c in textos) {
      for (final f in fondos) {
        expect(contrastRatio(c, f), greaterThanOrEqualTo(4.5),
            reason: '$c sobre $f');
      }
    }
  });

  test('texto sobre botones', () {
    expect(contrastRatio(QfColors.onCta, QfColors.cta),
        greaterThanOrEqualTo(4.5));
    expect(contrastRatio(QfColors.onPrimary, QfColors.primary),
        greaterThanOrEqualTo(4.5));
    // Por eso no se usa blanco sobre el azul primario.
    expect(contrastRatio(Colors.white, QfColors.primary), lessThan(4.5));
  });

  test('los alias live* apuntan a la paleta v3', () {
    expect(liveBg, QfColors.bg);
    expect(livePanel, QfColors.surface);
    expect(liveCyan, QfColors.primary);
    expect(liveGold, QfColors.cta);
    expect(liveGreen, QfColors.success);
    expect(liveMuted, QfColors.text2);
  });
}
