// Preferencias de «Mis deportes» frente a un catálogo que cambia: ids desconocidos, deportes nuevos y beta.
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/product/sports.dart';

Map<String, Object?> sport(String id, int orden, [String estado = 'on']) => {
  'id': id,
  'orden': orden,
  'estado': estado,
  'nombre': {'es': id},
  'color': '#123456',
  'icono': 'generico',
  'secciones': ['high'],
};

SportCatalog catalogOf(List<Map<String, Object?>> sports) => SportCatalog.fromJson({'deportes': sports})!;

SportPrefs prefsOn(Map<String, String> store, SportCatalog catalog) => SportPrefs(
  read: (key) async => store[key],
  write: (key, value) async => store[key] = value,
  catalog: () => catalog,
);

void main() {
  final base = catalogOf([sport('futbol', 1), sport('nba', 2), sport('tenis', 3)]);

  test('un deporte desconocido en las preferencias no se pierde al guardar', () async {
    final store = {'sports_order': 'golf,tenis,futbol', 'sports_hidden': 'golf,nba'};
    final prefs = prefsOn(store, base);
    // La app solo ve los del catálogo...
    expect(await prefs.order(), ['tenis', 'futbol', 'nba']);
    expect(await prefs.hidden(), {'nba'});
    // ...pero guardar conserva el que no conoce.
    await prefs.save(order: ['nba', 'tenis', 'futbol'], hidden: {'tenis'});
    expect(store['sports_order'], 'nba,tenis,futbol,golf');
    expect(store['sports_hidden'], 'tenis,golf');
    // Cuando el catálogo lo vuelve a traer, recupera lo que la persona había elegido.
    final withGolf = catalogOf([sport('futbol', 1), sport('nba', 2), sport('tenis', 3), sport('golf', 4)]);
    final back = prefsOn(store, withGolf);
    expect(await back.order(), ['nba', 'tenis', 'futbol', 'golf']);
    expect(await back.hidden(), {'tenis', 'golf'});
  });

  test('ids repetidos, vacíos o corruptos no rompen la lectura', () async {
    final prefs = prefsOn({'sports_order': ',,nba,nba,???, ', 'sports_hidden': ',,'}, base);
    expect(await prefs.order(), ['nba', 'futbol', 'tenis']);
    expect(await prefs.hidden(), isEmpty);
  });

  test('los deportes nuevos del catálogo van al final del orden guardado y visibles', () async {
    final catalog = catalogOf([sport('futbol', 1), sport('golf', 2), sport('nba', 3), sport('tenis', 4)]);
    final prefs = prefsOn({'sports_order': 'tenis,nba,futbol'}, catalog);
    expect(await prefs.order(), ['tenis', 'nba', 'futbol', 'golf']);
    expect(await prefs.hidden(), isEmpty);
  });

  test('sin preferencias el orden es el del servidor', () async {
    final catalog = catalogOf([sport('nba', 1), sport('futbol', 2)]);
    final prefs = prefsOn({}, catalog);
    expect(await prefs.order(), ['nba', 'futbol']);
    expect(await prefs.initial(), 'nba');
  });

  test('nunca queda la app sin un deporte visible, aunque todos estén guardados como ocultos', () async {
    final prefs = prefsOn({'sports_order': 'tenis,futbol,nba', 'sports_hidden': 'futbol,nba,tenis,golf'}, base);
    final hidden = await prefs.hidden();
    expect(hidden, {'futbol', 'nba'});
    expect(await prefs.initial(), 'tenis');
  });

  test('si el catálogo cambia y el deporte abierto desaparece, abre el primero del nuevo orden', () async {
    final prefs = prefsOn({'sports_order': 'nba,futbol,tenis'}, catalogOf([sport('futbol', 1), sport('tenis', 2)]));
    expect(await prefs.order(), ['futbol', 'tenis']);
    expect(await prefs.initial(), 'futbol');
  });

  test('un deporte en preview nace oculto y la persona puede activarlo', () async {
    final catalog = catalogOf([sport('futbol', 1), sport('golf', 2, 'preview'), sport('nba', 3)]);
    final store = <String, String>{};
    final prefs = prefsOn(store, catalog);
    expect(await prefs.order(), ['futbol', 'golf', 'nba']);
    expect(await prefs.hidden(), {'golf'});
    // Activarlo: guarda el orden completo con golf visible.
    await prefs.save(order: ['futbol', 'golf', 'nba'], hidden: {});
    expect(await prefs.hidden(), isEmpty);
    // Volver a ocultarlo también se respeta.
    await prefs.save(order: ['futbol', 'golf', 'nba'], hidden: {'golf'});
    expect(await prefs.hidden(), {'golf'});
  });

  test('un preview que aparece cuando ya había preferencias guardadas también nace oculto', () async {
    final catalog = catalogOf([sport('futbol', 1), sport('nba', 2), sport('golf', 3, 'preview')]);
    final prefs = prefsOn({'sports_order': 'nba,futbol', 'sports_hidden': ''}, catalog);
    expect(await prefs.order(), ['nba', 'futbol', 'golf']);
    expect(await prefs.hidden(), {'golf'});
  });

  test('si el único deporte es preview, se ve (el primero del orden siempre se ve)', () async {
    final prefs = prefsOn({}, catalogOf([sport('golf', 1, 'preview')]));
    expect(await prefs.hidden(), isEmpty);
    expect(await prefs.initial(), 'golf');
  });

  test('con NBA apagada en el catálogo, sus preferencias guardadas se conservan pero no se ofrece', () async {
    final catalog = catalogOf([sport('futbol', 1), sport('tenis', 2)]);
    final store = {'sports_order': 'nba,futbol,tenis', 'sports_hidden': 'nba'};
    final prefs = prefsOn(store, catalog);
    expect(await prefs.order(), ['futbol', 'tenis']);
    expect(await prefs.hidden(), isEmpty);
    await prefs.save(order: ['tenis', 'futbol'], hidden: {});
    expect(store['sports_order'], 'tenis,futbol,nba');
    expect(store['sports_hidden'], 'nba');
  });
}
