import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import 'qf_theme.dart';
import 'screen_definition.dart';

/// Identificador estable de un deporte (el `deporte_id` del catálogo del servidor). Es el que se guarda en
/// preferencias y viaja a la API. Texto y no `enum`: un deporte nuevo del catálogo no necesita versión de app.
typedef SportId = String;

/// Los tres deportes que la app sabe pintar con pantallas propias. Úsalos SOLO donde el código de verdad
/// distingue deporte (parley y Escalera, ficha de partido, endpoints); el resto consulta el [SportCatalog].
const SportId kFootball = 'futbol', kNba = 'nba', kTennis = 'tenis';

/// Estado de un deporte para esta app. `off` no existe aquí: un deporte apagado simplemente no está en el catálogo.
enum SportStatus { on, preview }

/// Conjunto cerrado de claves de icono. Una app anterior a una clave nueva cae en `generico`.
const sportIcons = <String, IconData>{
  'futbol': Icons.sports_soccer,
  'baloncesto': Icons.sports_basketball,
  'tenis': Icons.sports_tennis,
  'beisbol': Icons.sports_baseball,
  'hockey': Icons.sports_hockey,
  'rugby': Icons.sports_rugby,
  'futbol_americano': Icons.sports_football,
  'voleibol': Icons.sports_volleyball,
  'golf': Icons.sports_golf,
  'mma': Icons.sports_mma,
  'motor': Icons.sports_motorsports,
  'generico': Icons.sports_score,
};

/// Secciones de Predicciones que la app sabe mostrar.
const knownSportStreams = {'high', 'ladder', 'parley'};

const _fallbackLang = 'es';

String? _text(Object? value) {
  if (value is! String) return null;
  final trimmed = value.trim();
  return trimmed.isEmpty ? null : trimmed;
}

/// Texto en el idioma pedido y, si no lo hay, en español.
String? _localized(Map<String, String> texts, String lang) => texts[lang] ?? texts[_fallbackLang];

Map<String, String> _texts(Object? json) => json is Map
    ? {
        for (final e in json.entries)
          if (e.key is String && _text(e.value) != null) e.key as String: _text(e.value)!,
      }
    : const {};

/// Color `#rrggbb` del catálogo; si no se puede leer, el acento neutro del tema.
Color parseSportColor(Object? value) {
  final hex = RegExp(r'^#([0-9a-fA-F]{6})$').firstMatch(value is String ? value.trim() : '');
  if (hex == null) return QfColors.text2;
  return Color(0xff000000 | int.parse(hex.group(1)!, radix: 16));
}

/// Familia de mercados de un deporte según el catálogo (solo presentación: nombre, subtítulo y orden).
class SportFamilySpec {
  const SportFamilySpec({required this.id, required this.order, this.names = const {}, this.subtitles = const {}});

  final String id;
  final int order;
  final Map<String, String> names, subtitles;

  String? name(String lang) => _localized(names, lang);
  String? subtitle(String lang) => _localized(subtitles, lang);
}

class SportSpec {
  const SportSpec({
    required this.id,
    required this.accent,
    required this.icon,
    required this.streams,
    this.order = 0,
    this.status = SportStatus.on,
    this.names = const {},
    this.families = const [],
  });

  /// Deporte que el catálogo no conoce (p. ej. el de un aviso antiguo): icono genérico y acento neutro.
  factory SportSpec.unknown(SportId id) =>
      SportSpec(id: id, accent: QfColors.text2, icon: sportIcons['generico']!, streams: const {'high'});

  final SportId id;
  final Color accent;
  final IconData icon;
  final int order;
  final SportStatus status;

  /// Secciones de Predicciones que ofrece el deporte.
  final Set<String> streams;

  /// Nombre por idioma (los 6 de la app en el catálogo del servidor).
  final Map<String, String> names;
  final List<SportFamilySpec> families;

  bool get isBeta => status == SportStatus.preview;

  /// Nombre en el idioma actual: catálogo → español → texto de la app para los tres deportes de siempre → id.
  String label(AppLocalizations l10n) =>
      _localized(names, l10n.localeName) ??
      switch (id) {
        kFootball => l10n.sportFootball,
        kNba => l10n.sportNba,
        kTennis => l10n.sportTennis,
        _ => id,
      };

  SportFamilySpec? family(String familyId) {
    for (final f in families) {
      if (f.id == familyId) return f;
    }
    return null;
  }

  /// Lee un deporte de la respuesta del servidor. `null` si no se puede usar: sin id válido o con estado `off`
  /// o desconocido (un estado nuevo que la app no entiende se trata como apagado). Los campos que no conoce se
  /// ignoran; un icono o una sección desconocidos caen al genérico o se descartan.
  static SportSpec? fromJson(Object? json) {
    if (json is! Map) return null;
    final id = _text(json['id']);
    if (id == null || !RegExp(r'^[a-z][a-z0-9_]*$').hasMatch(id)) return null;
    final status = switch (json['estado']) {
      'on' => SportStatus.on,
      'preview' => SportStatus.preview,
      _ => null,
    };
    if (status == null) return null;
    final streams = <String>{
      if (json['secciones'] is List)
        for (final s in json['secciones'] as List)
          if (s is String && knownSportStreams.contains(s)) s,
    };
    final families = <SportFamilySpec>[
      if (json['familias'] is List)
        for (final f in json['familias'] as List)
          if (f is Map && _text(f['id']) != null)
            SportFamilySpec(
              id: _text(f['id'])!,
              order: f['orden'] is num ? (f['orden'] as num).toInt() : 0,
              names: _texts(f['nombre']),
              subtitles: _texts(f['subtitulo']),
            ),
    ]..sort((a, b) => a.order.compareTo(b.order));
    return SportSpec(
      id: id,
      order: json['orden'] is num ? (json['orden'] as num).toInt() : 0,
      status: status,
      accent: parseSportColor(json['color']),
      icon: sportIcons[json['icono']] ?? sportIcons['generico']!,
      streams: streams.isEmpty ? const {'high'} : streams,
      names: _texts(json['nombre']),
      families: families,
    );
  }
}

/// Deportes que ofrece la app, en el orden del servidor. Nunca está vacío: sin catálogo del servidor ni del
/// disco vale la copia de fábrica (`assets/model/cliente_config_defecto.json`) y, si ni el asset carga, [builtIn].
class SportCatalog {
  SportCatalog._(this.sports, [this.screens]) : assert(sports.isNotEmpty);

  /// Los tres deportes de fábrica, para el primer fotograma y las pruebas. Debe coincidir con el asset
  /// (`test/sport_catalog_test.dart` lo comprueba).
  static final builtIn = SportCatalog._(const [
    SportSpec(
      id: kFootball,
      order: 1,
      accent: QfColors.football,
      icon: Icons.sports_soccer,
      streams: {'high', 'ladder', 'parley'},
    ),
    SportSpec(id: kNba, order: 2, accent: QfColors.nba, icon: Icons.sports_basketball, streams: {'high'}),
    SportSpec(id: kTennis, order: 3, accent: QfColors.tennis, icon: Icons.sports_tennis, streams: {'high'}),
  ]);

  /// Lee la respuesta de `/cliente/v1/config`. `null` si no es utilizable (no es un mapa, sin `deportes` o sin
  /// ningún deporte encendido): quien llama conserva el catálogo anterior.
  static SportCatalog? fromJson(Object? json) {
    if (json is! Map || json['deportes'] is! List) return null;
    final seen = <String>{};
    final sports = <SportSpec>[];
    for (final raw in json['deportes'] as List) {
      final spec = SportSpec.fromJson(raw);
      if (spec != null && seen.add(spec.id)) sports.add(spec);
    }
    if (sports.isEmpty) return null;
    // Orden estable: por `orden` y, a igualdad, el de llegada.
    final indexed = [for (final (i, s) in sports.indexed) (i, s)]
      ..sort((a, b) {
        final byOrder = a.$2.order.compareTo(b.$2.order);
        return byOrder != 0 ? byOrder : a.$1.compareTo(b.$1);
      });
    return SportCatalog._([for (final e in indexed) e.$2], ScreenDefinitions.fromJson(json['pantallas']));
  }

  final List<SportSpec> sports;

  /// Definición de pantallas del servidor (`pantallas`); `null` mientras no haya ninguna publicada: cada pantalla
  /// conserva entonces su orden en código.
  final ScreenDefinitions? screens;

  List<SportId> get ids => [for (final s in sports) s.id];

  SportSpec? find(SportId? id) {
    for (final s in sports) {
      if (s.id == id) return s;
    }
    return null;
  }

  /// Especificación del deporte; un id que el catálogo no tiene recibe la genérica en vez de fallar.
  SportSpec spec(SportId id) => find(id) ?? SportSpec.unknown(id);

  bool contains(SportId id) => find(id) != null;

  /// Ocultos sin preferencias guardadas: los beta (`preview`), salvo que sean todos.
  Set<SportId> get defaultHidden {
    final beta = {
      for (final s in sports)
        if (s.isBeta) s.id,
    };
    return beta.length >= sports.length ? {} : beta;
  }

  /// Visibles sin preferencias guardadas, en el orden del catálogo.
  List<SportId> get defaultVisible => [
    for (final s in sports)
      if (!defaultHidden.contains(s.id)) s.id,
  ];
}

/// Catálogo vigente. Arranca con [SportCatalog.builtIn]; el almacén (`sport_catalog_store.dart`) lo sustituye
/// por la copia de fábrica, la del disco o la de red. Las pantallas que deben reaccionar lo escuchan.
final ValueNotifier<SportCatalog> sportCatalogNotifier = ValueNotifier(SportCatalog.builtIn);

SportCatalog get sportCatalog => sportCatalogNotifier.value;

/// Orden y ocultos. No conoce el almacenamiento: recibe `read`/`write`.
///
/// Tolerante con el catálogo: los ids que ya no están (deporte apagado o futuro) se CONSERVAN al guardar,
/// los deportes nuevos van al final del orden y siempre queda uno visible (el primero del orden).
class SportPrefs {
  SportPrefs({required this.read, required this.write, SportCatalog Function()? catalog})
    : _catalog = catalog ?? (() => sportCatalog);

  final Future<String?> Function(String key) read;
  final Future<void> Function(String key, String value) write;
  final SportCatalog Function() _catalog;

  static const orderKey = 'sports_order';
  static const hiddenKey = 'sports_hidden';

  List<SportId> _parse(String? raw) => [
    for (final id in (raw ?? '').split(','))
      if (id.trim().isNotEmpty) id.trim(),
  ];

  /// Orden guardado (solo deportes del catálogo, sin repetidos) y, al final, los que no estaban guardados.
  Future<List<SportId>> order() async {
    final catalog = _catalog();
    final saved = [
      for (final id in _parse(await read(orderKey)).toSet())
        if (catalog.contains(id)) id,
    ];
    return [
      ...saved,
      for (final id in catalog.ids)
        if (!saved.contains(id)) id,
    ];
  }

  /// Ocultos; nunca todos: el primero del orden siempre queda visible. Un deporte en `preview` que la persona
  /// aún no ha tocado (no está en el orden guardado) nace oculto.
  Future<Set<SportId>> hidden() async {
    final catalog = _catalog();
    final savedOrder = _parse(await read(orderKey)).toSet();
    final hidden = {
      for (final id in _parse(await read(hiddenKey)))
        if (catalog.contains(id)) id,
      for (final s in catalog.sports)
        if (s.isBeta && !savedOrder.contains(s.id)) s.id,
    };
    if (hidden.length >= catalog.sports.length) hidden.remove((await order()).first);
    return hidden;
  }

  /// Deporte con el que abre la app: el primero visible del orden de «Mis deportes».
  Future<SportId> initial() async {
    final hiddenNow = await hidden();
    return (await order()).firstWhere((k) => !hiddenNow.contains(k));
  }

  Future<void> save({required List<SportId> order, required Set<SportId> hidden}) async {
    final catalog = _catalog();
    // Lo que ya estaba guardado y el catálogo de hoy no conoce se conserva detrás de lo visible.
    final keptOrder = [
      for (final id in _parse(await read(orderKey)).toSet())
        if (!catalog.contains(id) && !order.contains(id)) id,
    ];
    final keptHidden = [
      for (final id in _parse(await read(hiddenKey)).toSet())
        if (!catalog.contains(id) && !hidden.contains(id)) id,
    ];
    await write(orderKey, [...order, ...keptOrder].join(','));
    await write(hiddenKey, [...hidden, ...keptHidden].join(','));
  }
}

/// Nombre de la familia en el idioma actual. Una familia desconocida usa la etiqueta del servidor.
String sportFamilyTitle(
  AppLocalizations l10n,
  String family, {
  String? fallback,
}) => switch (family) {
  'winner' => l10n.famWinnerTitle,
  'handicap' => l10n.sfNbaHandicap,
  'game_total' => l10n.sfNbaGameTotal,
  'team_points' => l10n.sfNbaTeamPoints,
  'player_points' => l10n.sfNbaPlayerPoints,
  'player_rebounds' => l10n.sfNbaPlayerRebounds,
  'player_assists' => l10n.sfNbaPlayerAssists,
  'player_threes' => l10n.sfNbaPlayerThrees,
  'games_total' => l10n.sfTennisGamesTotal,
  'games_handicap' => l10n.sfTennisGamesHandicap,
  'set_winner' => l10n.sfTennisSetWinner,
  'sets_handicap' => l10n.sfTennisSetsHandicap,
  'sets_total' => l10n.sfTennisSetsTotal,
  'tiebreak' => l10n.sfTennisTiebreak,
  _ => fallback ?? family,
};
