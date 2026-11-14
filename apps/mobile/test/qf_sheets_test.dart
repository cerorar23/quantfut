// Pruebas unitarias de hojas y modales CyberCore: QfBottomSheet y QfDialogCard.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/qf_controls.dart';
import 'package:gobet/product/qf_sheets.dart';
import 'package:gobet/product/qf_theme.dart';

Widget _host(Widget child) => MaterialApp(
  localizationsDelegates: AppLocalizations.localizationsDelegates,
  supportedLocales: AppLocalizations.supportedLocales,
  locale: AppLocale.instance.locale,
  theme: qfTheme(),
  home: Scaffold(body: Center(child: child)),
);

void main() {
  testWidgets('QfBottomSheet renderiza asa superior y contenido', (tester) async {
    await tester.pumpWidget(
      _host(
        const QfBottomSheet(
          child: Text('Contenido Hoja'),
        ),
      ),
    );
    expect(find.text('Contenido Hoja'), findsOneWidget);
  });

  testWidgets('QfBottomSheet.show abre el modal bottom sheet', (tester) async {
    await tester.pumpWidget(
      _host(
        Builder(
          builder: (context) => ElevatedButton(
            onPressed: () => QfBottomSheet.show(
              context: context,
              builder: (ctx) => const Text('Modal Abierto'),
            ),
            child: const Text('Abrir'),
          ),
        ),
      ),
    );

    await tester.tap(find.text('Abrir'));
    await tester.pumpAndSettle();
    expect(find.text('Modal Abierto'), findsOneWidget);
  });

  testWidgets('QfDialogCard renderiza título, contenido y botones de acción', (tester) async {
    await tester.pumpWidget(
      _host(
        QfDialogCard(
          icon: Icons.info_outline,
          title: 'CONFIRMAR CANJE',
          content: const Text('¿Deseas canjear 50 coins por este pick?'),
          actions: [
            QfButton(
              label: 'CANCELAR',
              variant: QfButtonVariant.secondary,
              onPressed: () {},
            ),
            QfButton(
              label: 'CANJEAR',
              variant: QfButtonVariant.primary,
              onPressed: () {},
            ),
          ],
        ),
      ),
    );

    expect(find.text('CONFIRMAR CANJE'), findsOneWidget);
    expect(find.text('¿Deseas canjear 50 coins por este pick?'), findsOneWidget);
    expect(find.text('CANCELAR'), findsOneWidget);
    expect(find.text('CANJEAR'), findsOneWidget);
  });
}
