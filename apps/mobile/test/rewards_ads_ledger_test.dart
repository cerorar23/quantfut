// El historial de monedas etiqueta los videos con recompensa en cada idioma.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/live_rewards.dart';

void main() {
  for (final language in ['es', 'en', 'pt', 'fr', 'it', 'de']) {
    test('movimiento «ad» tiene etiqueta propia en $language', () {
      final l10n = lookupAppLocalizations(Locale(language));
      expect(ledgerKindLabel(l10n, 'ad'), l10n.ledgerAd);
      expect(l10n.ledgerAd, isNotEmpty);
    });
  }
}
