// Definición de pantallas de `/cliente/v1/config` (Fase 4 · 4.5): orden, visibilidad y avisos de las pantallas
// `deporte` y `partido` de los deportes SIN pantalla propia. Port de `normalizarPantallas`, `pantallaResuelta` y
// `datosAviso` de `frontend/rutas.js`. Sin definición publicada (o con una inservible) cada pantalla conserva el
// orden que tiene en código.
import 'sports.dart';

/// Secciones conocidas de cada pantalla (el id es el contrato con el servidor).
const screenSections = <String, List<String>>{
  'deporte': ['dias', 'resumen', 'destacado', 'partidos'],
  'partido': ['cabecera', 'pronostico', 'mercados', 'contenido', 'sello', 'estadisticas', 'h2h', 'alertas'],
};

/// Orden de hoy de la pantalla `deporte` y de la `partido` cuando no hay definición.
/// Secciones de la pantalla `deporte` que la lista genérica sabe pintar.
const genericSportSections = {'dias', 'resumen', 'destacado', 'partidos'};
const defaultSportSections = ['destacado', 'dias', 'resumen', 'partidos'];
const defaultMatchSections = ['cabecera', 'pronostico', 'mercados', 'contenido', 'sello'];

const _maxBlocks = 20;
final _blockId = RegExp(r'^[a-z0-9_]{1,40}$');
final _sportKey = RegExp(r'^[a-z][a-z0-9_]*$');
const _tones = {'info', 'exito', 'aviso', 'peligro'};

class ScreenBlock {
  const ScreenBlock({required this.id, required this.type, required this.visible, this.section, this.params = const {}});

  final String id;

  /// `seccion`, `aviso` o `vip`.
  final String type;
  final String? section;
  final bool visible;
  final Map<String, Object?> params;

  bool get isSection => type == 'seccion';

  /// Bloque de una sección del orden de hoy.
  factory ScreenBlock.section(String section) =>
      ScreenBlock(id: section, type: 'seccion', section: section, visible: true);
}

/// Datos de un bloque `aviso`: texto en el idioma pedido (cae a `es`), tono y enlace relativo opcional.
class NoticeData {
  const NoticeData({required this.text, required this.tone, this.link});
  final String text;

  /// `info`, `exito`, `aviso` o `peligro` (cualquier otro valor del servidor se trata como `info`).
  final String tone;
  final String? link;
}

String? _clean(Object? v) => v is String && v.trim().isNotEmpty ? v.trim() : null;

/// Texto del aviso en el idioma actual, con caída a español. `null` si el bloque no trae texto.
NoticeData? noticeData(ScreenBlock block, String lang) {
  final texts = block.params['texto'];
  if (texts is! Map) return null;
  final text = _clean(texts[lang]) ?? _clean(texts['es']);
  if (text == null) return null;
  final tone = block.params['tono'];
  final link = block.params['enlace'];
  return NoticeData(
    text: text,
    tone: tone is String && _tones.contains(tone) ? tone : 'info',
    link: link is String && RegExp(r'^/[^/\s]\S*$').hasMatch(link) ? link : null,
  );
}

ScreenBlock? _block(String screen, Object? raw) {
  if (raw is! Map) return null;
  final id = raw['id'];
  if (id is! String || !_blockId.hasMatch(id)) return null;
  final visible = raw['visible'] != false;
  final p = raw['params'];
  final params = p is Map ? {for (final e in p.entries) if (e.key is String) e.key as String: e.value} : <String, Object?>{};
  switch (raw['tipo']) {
    case 'seccion':
      final section = raw['seccion'];
      if (section is! String || !screenSections[screen]!.contains(section)) return null;
      return ScreenBlock(id: id, type: 'seccion', section: section, visible: visible);
    case 'aviso':
      return params['texto'] is Map ? ScreenBlock(id: id, type: 'aviso', visible: visible, params: params) : null;
    case 'vip':
      return ScreenBlock(id: id, type: 'vip', visible: visible, params: params);
  }
  return null; // tipo desconocido: se ignora
}

/// Definiciones vigentes por pantalla y deporte (`'*'` = todos).
class ScreenDefinitions {
  const ScreenDefinitions._(this._byScreen);

  final Map<String, Map<String, List<ScreenBlock>>> _byScreen;

  /// Valida `pantallas` de la respuesta. `null` si no hay ninguna definición utilizable: tipo, sección o parámetro
  /// desconocidos se ignoran, una sección repetida cuenta una vez y una lista sin secciones visibles no vale.
  static ScreenDefinitions? fromJson(Object? json) {
    if (json is! Map) return null;
    final out = <String, Map<String, List<ScreenBlock>>>{};
    for (final screen in screenSections.keys) {
      final bySport = json[screen];
      if (bySport is! Map) continue;
      for (final entry in bySport.entries) {
        final key = entry.key, list = entry.value;
        if (key is! String || (key != '*' && !_sportKey.hasMatch(key)) || list is! List) continue;
        final seen = <String>{};
        final blocks = <ScreenBlock>[
          for (final raw in list.take(_maxBlocks))
            if (_block(screen, raw) case final b?)
              if (!b.isSection || seen.add(b.section!)) b,
        ];
        if (!blocks.any((b) => b.isSection && b.visible)) continue;
        (out[screen] ??= {})[key] = blocks;
      }
    }
    return out.isEmpty ? null : ScreenDefinitions._(out);
  }

  /// Definición del deporte concreto; si no hay, la de `'*'`; si no, `null` (orden en código).
  List<ScreenBlock>? resolve(String screen, SportId sport) {
    final bySport = _byScreen[screen];
    return bySport?[sport] ?? bySport?['*'];
  }
}

/// Bloques que se pintan hoy en una pantalla de un deporte nuevo: la definición publicada (solo los visibles) o el
/// orden de hoy. `known` son las secciones que la pantalla genérica sabe pintar; el resto se ignora.
List<ScreenBlock> effectiveScreen(
  ScreenDefinitions? definitions,
  String screen,
  SportId sport,
  List<String> defaults,
  Set<String> known,
) {
  final defined = definitions?.resolve(screen, sport);
  final blocks = defined ?? [for (final s in defaults) ScreenBlock.section(s)];
  return [
    for (final b in blocks)
      if (b.visible && (!b.isSection || known.contains(b.section))) b,
  ];
}
