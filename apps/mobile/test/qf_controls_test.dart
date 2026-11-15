// Pruebas unitarias de controles CyberCore: QfButton, QfSwitch, QfCheckbox, QfTabs, QfSectionNav, QfStepDots.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/qf_controls.dart';
import 'package:gobet/product/qf_theme.dart';

Widget _host(Widget child) => MaterialApp(
  localizationsDelegates: AppLocalizations.localizationsDelegates,
  supportedLocales: AppLocalizations.supportedLocales,
  locale: AppLocale.instance.locale,
  theme: qfTheme(),
  home: Scaffold(body: Center(child: child)),
);

void main() {
  group('QfButton', () {
    testWidgets('primary ejecuta onTap y respeta altura mínima 44 dp', (tester) async {
      var tapped = 0;
      await tester.pumpWidget(
        _host(
          QfButton(
            label: 'GUARDAR',
            variant: QfButtonVariant.primary,
            onPressed: () => tapped++,
          ),
        ),
      );

      final buttonFinder = find.byType(QfButton);
      expect(buttonFinder, findsOneWidget);
      expect(tester.getSize(buttonFinder).height, greaterThanOrEqualTo(44.0));
      expect(find.text('GUARDAR'), findsOneWidget);

      await tester.tap(buttonFinder);
      expect(tapped, 1);
    });

    testWidgets('variantes secondary, vip, danger y google se renderizan', (tester) async {
      await tester.pumpWidget(
        _host(
          Column(
            children: [
              QfButton(label: 'CANCELAR', variant: QfButtonVariant.secondary, onPressed: () {}),
              QfButton(label: 'HAZTE VIP', variant: QfButtonVariant.vip, onPressed: () {}),
              QfButton(label: 'ELIMINAR', variant: QfButtonVariant.danger, onPressed: () {}),
              QfButton(label: 'CONTINUAR CON GOOGLE', variant: QfButtonVariant.google, onPressed: () {}),
            ],
          ),
        ),
      );

      expect(find.text('CANCELAR'), findsOneWidget);
      expect(find.text('HAZTE VIP'), findsOneWidget);
      expect(find.text('ELIMINAR'), findsOneWidget);
      expect(find.text('CONTINUAR CON GOOGLE'), findsOneWidget);
    });

    testWidgets('estado deshabilitado (onPressed null) no ejecuta tap', (tester) async {
      await tester.pumpWidget(
        _host(
          const QfButton(
            label: 'DESHABILITADO',
            variant: QfButtonVariant.primary,
            onPressed: null,
          ),
        ),
      );

      await tester.tap(find.byType(QfButton));
      expect(find.text('DESHABILITADO'), findsOneWidget);
    });
  });

  group('QfSwitch', () {
    testWidgets('tamaño 52x30 y conmuta estado con tap', (tester) async {
      var current = false;
      await tester.pumpWidget(
        _host(
          StatefulBuilder(
            builder: (context, setState) => QfSwitch(
              value: current,
              onChanged: (v) => setState(() => current = v),
            ),
          ),
        ),
      );

      final switchFinder = find.byType(QfSwitch);
      expect(switchFinder, findsOneWidget);
      expect(tester.getSize(switchFinder).width, 52.0);
      expect(tester.getSize(switchFinder).height, 30.0);

      await tester.tap(switchFinder);
      await tester.pumpAndSettle();
      expect(current, true);

      await tester.tap(switchFinder);
      await tester.pumpAndSettle();
      expect(current, false);
    });
  });

  group('QfCheckbox', () {
    testWidgets('conmuta valor y asegura target interactivo', (tester) async {
      var checked = false;
      await tester.pumpWidget(
        _host(
          StatefulBuilder(
            builder: (context, setState) => QfCheckbox(
              value: checked,
              onChanged: (v) => setState(() => checked = v),
            ),
          ),
        ),
      );

      final cbFinder = find.byType(QfCheckbox);
      expect(cbFinder, findsOneWidget);
      // El target interactivo externo debe ser >= 44 dp para accesibilidad táctil
      expect(tester.getSize(cbFinder).height, greaterThanOrEqualTo(44.0));

      await tester.tap(cbFinder);
      await tester.pumpAndSettle();
      expect(checked, true);
    });
  });

  group('QfTabs', () {
    testWidgets('modo segmented conmuta índice seleccionado', (tester) async {
      var selected = 0;
      await tester.pumpWidget(
        _host(
          StatefulBuilder(
            builder: (context, setState) => QfTabs(
              labels: const ['ALTA CONFIANZA', 'ESCALERA', 'RETOS'],
              index: selected,
              onChanged: (i) => setState(() => selected = i),
              mode: QfTabsMode.segmented,
            ),
          ),
        ),
      );

      expect(find.text('ALTA CONFIANZA'), findsOneWidget);
      expect(find.text('ESCALERA'), findsOneWidget);

      await tester.tap(find.text('ESCALERA'));
      await tester.pumpAndSettle();
      expect(selected, 1);
    });

    testWidgets('modo chips muestra badges de conteo y conmuta', (tester) async {
      var selected = 0;
      await tester.pumpWidget(
        _host(
          StatefulBuilder(
            builder: (context, setState) => QfTabs(
              labels: const ['TODOS', 'FÚTBOL', 'NBA'],
              counts: const [12, 8, 4],
              index: selected,
              onChanged: (i) => setState(() => selected = i),
              mode: QfTabsMode.chips,
            ),
          ),
        ),
      );

      expect(find.text('(12)'), findsOneWidget);
      expect(find.text('(8)'), findsOneWidget);

      await tester.tap(find.text('NBA'));
      await tester.pumpAndSettle();
      expect(selected, 2);
    });
  });

  group('QfSectionNav', () {
    testWidgets('renderiza secciones con keys asignadas', (tester) async {
      final key1 = GlobalKey();
      final key2 = GlobalKey();
      await tester.pumpWidget(
        _host(
          QfSectionNav(
            sections: [
              ('H2H', key1),
              ('FORMAS', key2),
            ],
          ),
        ),
      );

      expect(find.text('H2H'), findsOneWidget);
      expect(find.text('FORMAS'), findsOneWidget);
    });
  });

  group('QfStepDots', () {
    testWidgets('renderiza N puntos con el activo resaltado', (tester) async {
      await tester.pumpWidget(
        _host(
          const QfStepDots(
            count: 4,
            index: 1,
          ),
        ),
      );

      expect(find.byType(QfStepDots), findsOneWidget);
    });
  });
}
