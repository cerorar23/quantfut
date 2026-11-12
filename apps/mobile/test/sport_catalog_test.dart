// Catálogo de deportes: copia de fábrica, lectura tolerante del contrato 1 y estados.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/qf_theme.dart';
import 'package:gobet/product/sport_catalog_store.dart';
import 'package:gobet/product/sports.dart';

Map<String, Object?> sport(
  String id, {
  int orden = 1,
  String estado = 'on',
  String icono = 'generico',
  String color = '#112233',
  List<Object?> secciones = const ['high'],
  Map<String, Object?>? nombre,
}) => {
  'id': id,
  'orden': orden,
  'estado': estado,
  'nombre': nombre ?? {'es': id.toUpperCase(), 'en': 'EN ${id.toUpperCase()}'},
  'slug': {'es': id, 'en': id, 'pt': id},
  'icono': icono,
  'color': color,
  'secciones': secciones,
  'familias': <Object?>[],
};

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('la copia de fábrica trae los tres deportes de hoy, en orden', () async {
    final factory = await loadFactorySportCatalog();
    expect(factory, isNotNull);
    expect(factory!.ids, [kFootball, kNba, kTennis]);
    expect(factory.sports.every((s) => s.status == SportStatus.on), isTrue);
  });

  test('builtIn coincide con la copia de fábrica (id, acento, icono, secciones)', () async {
    final factory = (await loadFactorySportCatalog())!;
    expect(SportCatalog.builtIn.ids, factory.ids);
    for (final id in factory.ids) {
      final a = SportCatalog.builtIn.spec(id), b = factory.spec(id);
      expect(a.accent, b.accent, reason: id);
      expect(a.icon, b.icon, reason: id);
      expect(a.streams, b.streams, reason: id);
    }
    expect(factory.spec(kFootball).accent, QfColors.football);
    expect(factory.spec(kNba).accent, QfColors.nba);
    expect(factory.spec(kTennis).accent, QfColors.tennis);
  });

  test('los nombres de fábrica son los textos de la app: instalarla no cambia nada en pantalla', () async {
    final factory = (await loadFactorySportCatalog())!;
    for (final code in ['es', 'en', 'pt', 'fr', 'it', 'de']) {
      final l10n = lookupAppLocalizations(Locale(code));
      for (final (id, text) in [
        (kFootball, l10n.sportFootball),
        (kNba, l10n.sportNba),
        (kTennis, l10n.sportTennis),
      ]) {
        expect(factory.spec(id).label(l10n), text, reason: '$code $id');
        expect(SportCatalog.builtIn.spec(id).label(l10n), text, reason: '$code $id (builtIn)');
      }
    }
  });

  test('un estado desconocido se trata como apagado y off no sale', () {
    final catalog = SportCatalog.fromJson({
      'deportes': [
        sport('futbol'),
        sport('raro', orden: 2, estado: 'archivado'),
        sport('apagado', orden: 3, estado: 'off'),
        sport('sinestado', orden: 4, estado: ''),
      ],
    })!;
    expect(catalog.ids, ['futbol']);
  });

  test('icono o sección desconocidos caen al genérico o se ignoran; campos nuevos se ignoran', () {
    final catalog = SportCatalog.fromJson({
      'campo_nuevo': 1,
      'deportes': [
        {
          ...sport('golf', icono: 'palo_de_golf', secciones: ['high', 'torneo', 7, null]),
          'otro_campo': {'x': 1},
        },
        sport('futbol', orden: 2, icono: 'futbol', secciones: ['high', 'ladder', 'parley']),
      ],
    })!;
    final golf = catalog.spec('golf');
    expect(golf.icon, sportIcons['generico']);
    expect(golf.streams, {'high'});
    expect(catalog.spec('futbol').icon, Icons.sports_soccer);
  });

  test('sin secciones válidas se queda con Alta probabilidad', () {
    final catalog = SportCatalog.fromJson({
      'deportes': [sport('golf', secciones: ['nada'])],
    })!;
    expect(catalog.spec('golf').streams, {'high'});
  });

  test('un color ilegible cae al acento neutro del tema', () {
    final catalog = SportCatalog.fromJson({
      'deportes': [
        sport('golf', color: 'azul'),
        sport('hockey', orden: 2, color: '#12'),
        sport('rugby', orden: 3, color: '#ABCDEF'),
      ],
    })!;
    expect(catalog.spec('golf').accent, QfColors.text2);
    expect(catalog.spec('hockey').accent, QfColors.text2);
    expect(catalog.spec('rugby').accent, const Color(0xffabcdef));
  });

  test('orden por `orden`, estable a igualdad; ids repetidos o malformados se descartan', () {
    final catalog = SportCatalog.fromJson({
      'deportes': [
        sport('c', orden: 3),
        sport('a', orden: 1),
        sport('b', orden: 1),
        sport('a', orden: 9, estado: 'preview'),
        sport('Mal,Id', orden: 2),
        'basura',
        null,
      ],
    })!;
    expect(catalog.ids, ['a', 'b', 'c']);
    expect(catalog.spec('a').status, SportStatus.on);
  });

  test('respuesta inválida o vacía: fromJson devuelve null', () {
    expect(SportCatalog.fromJson(null), isNull);
    expect(SportCatalog.fromJson('hola'), isNull);
    expect(SportCatalog.fromJson(<String, Object?>{}), isNull);
    expect(SportCatalog.fromJson({'deportes': 'x'}), isNull);
    expect(SportCatalog.fromJson({'deportes': <Object?>[]}), isNull);
    expect(SportCatalog.fromJson({'deportes': [sport('golf', estado: 'off')]}), isNull);
  });

  test('un deporte nuevo (golf) con icono desconocido se muestra con icono genérico y su nombre', () {
    final catalog = SportCatalog.fromJson({
      'deportes': [
        sport('futbol', icono: 'futbol'),
        sport('golf', orden: 2, icono: 'golf2030', nombre: {'es': 'Golf', 'en': 'Golf!'}),
      ],
    })!;
    final golf = catalog.spec('golf');
    expect(golf.icon, sportIcons['generico']);
    expect(golf.label(lookupAppLocalizations(const Locale('en'))), 'Golf!');
    // Idioma que el catálogo no trae: cae a español.
    expect(golf.label(lookupAppLocalizations(const Locale('de'))), 'Golf');
  });

  test('un id que el catálogo no tiene recibe la especificación genérica', () {
    final spec = SportCatalog.builtIn.spec('curling');
    expect(spec.icon, sportIcons['generico']);
    expect(spec.accent, QfColors.text2);
    expect(spec.label(lookupAppLocalizations(const Locale('es'))), 'curling');
    expect(SportCatalog.builtIn.find('curling'), isNull);
  });

  test('preview: beta, y por defecto oculto salvo que sea el único', () {
    final catalog = SportCatalog.fromJson({
      'deportes': [sport('futbol'), sport('golf', orden: 2, estado: 'preview')],
    })!;
    expect(catalog.spec('golf').isBeta, isTrue);
    expect(catalog.defaultHidden, {'golf'});
    expect(catalog.defaultVisible, ['futbol']);
    final solo = SportCatalog.fromJson({
      'deportes': [sport('golf', estado: 'preview')],
    })!;
    expect(solo.defaultHidden, isEmpty);
    expect(solo.defaultVisible, ['golf']);
  });
}
