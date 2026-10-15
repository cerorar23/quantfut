// Pestaña Coins: saldo con avance, asistencia de 7 días con cuenta atrás, ofertas, invitación,
// historial plegable y términos, con la forma real de los datos del servidor.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/coin_burst.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/live_rewards.dart';
import 'package:gobet/product/live_widgets.dart';

const languages = ['es', 'en', 'pt', 'fr', 'it', 'de'];

String day(DateTime d) =>
    '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

Map<String, dynamic> rewards({
  required bool signedIn,
  bool claimedToday = false,
  int streak = 3,
  int balance = 60,
}) {
  final today = DateTime.now().toUtc();
  final last = claimedToday ? today : today.subtract(const Duration(days: 1));
  return {
    'signed_in': signedIn,
    'settings': {
      'enabled': true,
      'unlock_cost': 100,
      'attendance_enabled': true,
      'attendance_coins': [30, 35, 35, 40, 40, 45, 50],
      'referrals_enabled': true,
      'referrer_coins': 200,
      'invitee_coins': 100,
      'referral_min_coins': 100,
      'message': '',
    },
    'providers': [
      {'provider': 'adjoe', 'name': 'adjoe Playtime', 'available': false},
      {'provider': 'ayet', 'name': 'ayeT-Studios', 'available': false},
      {'provider': 'bitlabs', 'name': 'BitLabs', 'available': false},
      {'provider': 'revu', 'name': 'RevU', 'available': false},
      {'provider': 'tapjoy', 'name': 'Tapjoy / Unity Offerwall', 'available': true},
      {'provider': 'torox', 'name': 'Torox', 'available': false},
    ],
    'wallet': signedIn
        ? {
            'balance': balance,
            'spendable': balance,
            'streak': streak,
            'last_attendance': day(last),
            'referral_code': 'QF7K2P',
            'can_check_in': !claimedToday,
          }
        : null,
    'referrals': signedIn ? {'registered': 2, 'qualified': 1} : null,
    'ledger': [
      for (var i = 0; i < 7; i++)
        {'delta': i == 6 ? -100 : 30 + i, 'kind': i == 6 ? 'unlock' : 'attendance', 'created_at': '2026-10-1${i}T12:00:00+00:00'},
    ],
    'terms': 'Monedas sin valor monetario: canjeables solo por pronósticos.',
  };
}

class _Api extends QuantFutApi {
  _Api(this.payload);

  final Map<String, dynamic> payload;
  final calls = <String>[];

  @override
  bool get signedIn => payload['signed_in'] == true;

  @override
  Future<dynamic> request(
    String path, {
    JsonMap? query,
    JsonMap? body,
    bool retry = true,
  }) async {
    calls.add(path);
    if (path == '/mobile/v1/rewards/attendance') {
      return {'credited': true, 'coins': 40, 'streak': 4};
    }
    return payload;
  }
}

Future<_Api> open(
  WidgetTester tester,
  Map<String, dynamic> payload, {
  Size size = const Size(390, 2600),
  String code = 'es',
}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await AppLocale.instance.select(code);
  final api = _Api(payload);
  await tester.pumpWidget(
    MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      locale: AppLocale.instance.locale,
      theme: liveTheme(),
      home: RewardsScreen(api: api),
    ),
  );
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 900));
  return api;
}

void main() {
  setUpAll(() async {
    for (final f in {
      'Gilroy Medium': 'fonts/Gilroy-Medium.ttf',
      'Gilroy Bold': 'fonts/Gilroy-Bold.otf',
      'Gilroy ExtraBold': 'fonts/Gilroy-ExtraBold.otf',
      'MaterialIcons': 'fonts/MaterialIcons-Regular.otf',
    }.entries) {
      await (FontLoader(f.key)..addFont(rootBundle.load(f.value))).load();
    }
  });
  tearDown(() => AppLocale.instance.reset());

  testWidgets('el saldo muestra su avance hacia el desbloqueo y los datos clave', (tester) async {
    await open(tester, rewards(signedIn: true));
    expect(find.text('60'), findsWidgets);
    expect(find.text('60 %'), findsOneWidget);
    expect(find.text('Faltan 40 monedas para tu próximo desbloqueo.'), findsOneWidget);
    expect(find.text('Racha de 3 días'), findsOneWidget);
    expect(find.text('100 monedas = 1 pronóstico'), findsWidgets);
  });

  testWidgets('la asistencia marca los días cobrados, resalta hoy y celebra al reclamar', (tester) async {
    final api = await open(tester, rewards(signedIn: true));
    expect(find.byKey(const ValueKey('coins-attendance')), findsOneWidget);
    for (var i = 0; i < 7; i++) {
      expect(find.byKey(ValueKey('coins-day-$i')), findsOneWidget);
    }
    expect(find.text('Hoy'), findsOneWidget); // el día 4
    expect(find.text('Disponible'), findsOneWidget);
    final claim = find.byKey(const ValueKey('coins-claim'));
    expect(find.text('Marcar asistencia · +40'), findsOneWidget);
    await tester.tap(claim);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    expect(api.calls, contains('/mobile/v1/rewards/attendance'));
    expect(find.byType(CoinBurst), findsOneWidget);
    expect(find.text('+40 monedas'), findsOneWidget);
    await tester.pump(const Duration(seconds: 2));
  });

  testWidgets('ya marcada hoy: cuenta atrás en vez de botón', (tester) async {
    await open(tester, rewards(signedIn: true, claimedToday: true));
    expect(find.byKey(const ValueKey('coins-claim')), findsNothing);
    expect(find.byKey(const ValueKey('coins-countdown')), findsOneWidget);
    expect(find.textContaining('Próxima asistencia en'), findsOneWidget);
    expect(find.text('Reclamada hoy'), findsOneWidget);
  });

  testWidgets('una racha rota no se cuenta aunque el servidor guarde el número', (tester) async {
    final payload = rewards(signedIn: true, streak: 5);
    (payload['wallet'] as Map)['last_attendance'] = day(DateTime.now().toUtc().subtract(const Duration(days: 3)));
    await open(tester, payload);
    expect(find.textContaining('Racha de'), findsNothing);
    expect(find.text('Marcar asistencia · +30'), findsOneWidget);
  });

  testWidgets('ofertas: una tarjeta del proveedor listo y los demás en una línea', (tester) async {
    await open(tester, rewards(signedIn: true));
    expect(find.byKey(const ValueKey('coins-offer-tapjoy')), findsOneWidget);
    expect(find.text('Ver ofertas'), findsOneWidget);
    expect(find.byKey(const ValueKey('coins-offer-adjoe')), findsNothing);
    expect(find.text('Pendiente de activar'), findsNothing);
    expect(
      find.text('Próximamente: adjoe Playtime, ayeT-Studios, BitLabs, RevU, Torox'),
      findsOneWidget,
    );
  });

  testWidgets('invitación: premios, código y estadísticas', (tester) async {
    await open(tester, rewards(signedIn: true));
    expect(find.text('+200 para ti'), findsOneWidget);
    expect(find.text('Tu amigo recibe +100 al registrar tu código'), findsOneWidget);
    expect(find.text('QF7K2P'), findsOneWidget);
    expect(find.text('Copiar'), findsOneWidget);
    expect(find.text('2 registrados · 1 validados'), findsOneWidget);
  });

  test('el código de invitación sale del propio código, del enlace o del mensaje compartido', () {
    expect(inviteCodeFrom(r' f9b9cbe3633f '), 'F9B9CBE3633F');
    expect(inviteCodeFrom('https://pronosticosdeportivos.pro/i/f9b9cbe3633f'), 'F9B9CBE3633F');
    expect(
      inviteCodeFrom('Usa mi código de invitación QF7K2P en QuantFut. Todo aquí: https://x.pro/i/qf7k2p'),
      'QF7K2P',
    );
    // una palabra suelta de un texto cualquiera no se toma por código
    expect(inviteCodeFrom('Hola, usa QuantFut conmigo'), isNull);
    expect(inviteCodeFrom('abc'), isNull);
    expect(inviteCodeFrom(''), isNull);
    expect(inviteCodeFrom('QF7K2P; DROP TABLE'), isNull);
  });

  test('el enlace y el mensaje compartidos llevan el código y la página de invitación', () async {
    await AppLocale.instance.select('es');
    final base = Uri.parse('https://pronosticosdeportivos.pro');
    expect(inviteLink(base, 'QF7K2P'), 'https://pronosticosdeportivos.pro/i/QF7K2P');
    final text = inviteShareText(AppLocale.instance.l10n, base, 'QF7K2P');
    expect(text, contains('QF7K2P'));
    expect(text, contains('https://pronosticosdeportivos.pro/i/QF7K2P'));
    expect(text, contains('Código de quien te invitó'));
    for (final code in languages) {
      await AppLocale.instance.select(code);
      final t = inviteShareText(AppLocale.instance.l10n, base, 'QF7K2P');
      expect(t, allOf(contains('QF7K2P'), contains('/i/QF7K2P')), reason: code);
    }
  });

  testWidgets('compartir y pegar: el botón de compartir está y pegar rellena el campo', (tester) async {
    var clipboard = 'Mira esto: https://pronosticosdeportivos.pro/i/ab12cd34ef56';
    tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(SystemChannels.platform, (call) async {
      if (call.method == 'Clipboard.getData') return <String, dynamic>{'text': clipboard};
      return null;
    });
    addTearDown(() => tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(SystemChannels.platform, null));
    await open(tester, rewards(signedIn: true));
    expect(find.byKey(const ValueKey('coins-share')), findsOneWidget);
    expect(find.text('Compartir mi código'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('coins-paste')));
    await tester.pump();
    expect(find.text('AB12CD34EF56'), findsOneWidget);
    // sin código en el portapapeles se avisa y el campo no cambia
    clipboard = 'nada que ver';
    await tester.tap(find.byKey(const ValueKey('coins-paste')));
    await tester.pump();
    expect(find.text('No hay un código de invitación en el portapapeles.'), findsOneWidget);
    expect(find.text('AB12CD34EF56'), findsOneWidget);
  });

  testWidgets('el historial enseña 5 y el resto se despliega; los términos están plegados', (tester) async {
    await open(tester, rewards(signedIn: true));
    Finder row(String label) => find.byWidgetPredicate(
      (w) => w is Text && (w.data ?? '').startsWith('$label\n'),
    );
    expect(row('Asistencia'), findsNWidgets(5)); // se enseñan 5 de 7 movimientos
    final more = find.byKey(const ValueKey('coins-ledger-toggle'));
    expect(find.text('Ver más'), findsOneWidget);
    await tester.ensureVisible(more);
    await tester.tap(more);
    await tester.pump();
    expect(find.text('Ver menos'), findsOneWidget);
    expect(row('Asistencia'), findsNWidgets(6));
    expect(row('Pronóstico desbloqueado'), findsOneWidget);
    expect(find.textContaining('Monedas sin valor monetario'), findsNothing);
    final terms = find.byKey(const ValueKey('coins-terms-toggle'));
    await tester.ensureVisible(terms);
    await tester.tap(terms);
    await tester.pump();
    expect(find.textContaining('Monedas sin valor monetario'), findsOneWidget);
  });

  testWidgets('sin sesión: pide entrar y no deja marcar asistencia ni abrir ofertas', (tester) async {
    await open(tester, rewards(signedIn: false));
    expect(find.text('Inicia sesión'), findsOneWidget);
    expect(find.textContaining('Inicia sesión en Perfil'), findsOneWidget);
    final claim = tester.widget<FilledButton>(find.byKey(const ValueKey('coins-claim')));
    expect(claim.onPressed, isNull);
    expect(tester.takeException(), isNull);
  });

  for (final code in languages) {
    testWidgets('se pinta en $code sin desbordes, también en 320 px', (tester) async {
      for (final size in const [Size(390, 2600), Size(320, 2600)]) {
        await open(tester, rewards(signedIn: true), size: size, code: code);
        expect(tester.takeException(), isNull, reason: '$code $size');
      }
    });
  }
}
