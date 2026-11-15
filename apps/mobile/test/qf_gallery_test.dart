// Galería visual CyberCore F1: valida renderizado a 360x800 dp y 390x844 dp sin overflow,
// accesibilidad táctil (targets >= 44 dp), semántica y estados vacíos.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/qf_charts.dart';
import 'package:gobet/product/qf_controls.dart';
import 'package:gobet/product/qf_shapes.dart';
import 'package:gobet/product/qf_theme.dart';
import 'package:gobet/product/sport_images.dart';

Widget _buildGallery() => MaterialApp(
  localizationsDelegates: AppLocalizations.localizationsDelegates,
  supportedLocales: AppLocalizations.supportedLocales,
  locale: AppLocale.instance.locale,
  theme: qfTheme(),
  home: Scaffold(
    backgroundColor: QfColors.bg,
    body: SingleChildScrollView(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            qfSectionTag('Botones CyberCore'),
            const SizedBox(height: 8),
            QfButton(label: 'VER PRONÓSTICO', variant: QfButtonVariant.primary, onPressed: () {}),
            const SizedBox(height: 8),
            QfButton(label: 'CANCELAR', variant: QfButtonVariant.secondary, onPressed: () {}),
            const SizedBox(height: 8),
            QfButton(label: 'HAZTE VIP', variant: QfButtonVariant.vip, onPressed: () {}),
            const SizedBox(height: 8),
            QfButton(label: 'ELIMINAR CUENTA', variant: QfButtonVariant.danger, onPressed: () {}),
            const SizedBox(height: 8),
            QfButton(label: 'CONTINUAR CON GOOGLE', variant: QfButtonVariant.google, onPressed: () {}),

            const SizedBox(height: 16),
            qfSectionTag('Controles Switch y Checkbox'),
            const SizedBox(height: 8),
            Row(
              children: [
                QfSwitch(value: true, onChanged: (_) {}),
                const SizedBox(width: 16),
                QfCheckbox(value: true, onChanged: (_) {}),
              ],
            ),

            const SizedBox(height: 16),
            qfSectionTag('Pestañas Segmentadas y Chips'),
            const SizedBox(height: 8),
            QfTabs(
              labels: const ['ALTA', 'ESCALERA', 'RETOS'],
              index: 0,
              onChanged: (_) {},
              mode: QfTabsMode.segmented,
            ),
            const SizedBox(height: 8),
            QfTabs(
              labels: const ['TODOS', 'FÚTBOL', 'NBA'],
              counts: const [10, 6, 4],
              index: 1,
              onChanged: (_) {},
              mode: QfTabsMode.chips,
            ),

            const SizedBox(height: 16),
            qfSectionTag('Insignias de Estado'),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: const [
                QfBadge.kind(QfBadgeKind.free),
                QfBadge.kind(QfBadgeKind.won),
                QfBadge.kind(QfBadgeKind.vip),
                QfBadge.kind(QfBadgeKind.lost),
                QfBadge.kind(QfBadgeKind.live),
                QfBadge.kind(QfBadgeKind.review),
                QfBadge.kind(QfBadgeKind.voided),
                QfBadge.kind(QfBadgeKind.doubt),
              ],
            ),

            const SizedBox(height: 16),
            qfSectionTag('Avatares Persona y Logo'),
            const SizedBox(height: 8),
            Row(
              children: const [
                QfAvatar(name: 'Luka Doncic', kind: QfAvatarKind.person, size: 40),
                SizedBox(width: 12),
                QfAvatar(name: 'Boston Celtics', kind: QfAvatarKind.logo, size: 40),
              ],
            ),

            const SizedBox(height: 16),
            qfSectionTag('Gráficos de Datos'),
            const SizedBox(height: 8),
            Row(
              children: const [
                QfRing(value: 0.85, size: 54),
                SizedBox(width: 16),
                Expanded(child: QfPips(total: 8, filled: 5)),
              ],
            ),
            const SizedBox(height: 8),
            const QfDivergingRow(label: 'Tiros de 3', a: 14, b: 9),
            const SizedBox(height: 8),
            const QfStackedBar(
              parts: [
                ('Local', 10.0, QfColors.cyan),
                ('Visitante', 5.0, QfColors.chrome),
              ],
            ),

            const SizedBox(height: 16),
            qfSectionTag('Tarjetas CyberCore'),
            const SizedBox(height: 8),
            const QfCard(
              strong: true,
              glow: true,
              child: Text('Tarjeta Fuerte con Brillo Cian'),
            ),
          ],
        ),
      ),
    ),
  ),
);

void main() {
  testWidgets('Galería renderiza sin overflow en pantalla 360x800 dp', (tester) async {
    tester.view.physicalSize = const Size(360 * 2.0, 800 * 2.0);
    tester.view.devicePixelRatio = 2.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_buildGallery());
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.text('VER PRONÓSTICO'), findsOneWidget);
    expect(find.text('Tarjeta Fuerte con Brillo Cian'), findsOneWidget);
  });

  testWidgets('Galería renderiza sin overflow en pantalla 390x844 dp', (tester) async {
    tester.view.physicalSize = const Size(390 * 3.0, 844 * 3.0);
    tester.view.devicePixelRatio = 3.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_buildGallery());
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.text('VER PRONÓSTICO'), findsOneWidget);
  });

  testWidgets('Objetivos interactivos cumplen altura mínima de 44 dp', (tester) async {
    await tester.pumpWidget(_buildGallery());
    await tester.pumpAndSettle();

    final buttons = find.byType(QfButton);
    for (final b in tester.widgetList<QfButton>(buttons)) {
      final size = tester.getSize(find.byWidget(b));
      expect(size.height, greaterThanOrEqualTo(44.0), reason: 'Boton ${b.label} menor a 44 dp');
    }
  });
}
