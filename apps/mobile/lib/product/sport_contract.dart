// Contrato común `/deportes/v1/{deporte}` (Fase 3–4) para los deportes del catálogo SIN pantalla propia en la app.
// Convierte `Evento`/`Mercado` del contrato en el `SportEvent`/`SportMarket` que ya pintan NBA y tenis, agrupa los
// mercados por familia del catálogo y lee los bloques de contenido del partido. Port de `eventoDesdeContrato`,
// `mercadoDesdeContrato`, `bloquesDesdeContrato`, `familiasDeEvento` y `loadPartidoContrato` de `frontend/sports-data.js`.
//
// Todo lo que sale de aquí ya está validado: un evento o mercado mal formado se descarta (nunca se completa ni se
// inventa un dato) y un bloque de tipo desconocido se ignora sin error. Los textos se pintan como texto plano.
import 'package:flutter/foundation.dart';
import 'package:intl/intl.dart';

import '../l10n/app_locale.dart';
import 'live_api.dart';
import 'sports.dart';
import 'sports_feed.dart';

/// Deportes con pantalla propia en la app: el fútbol, NBA y tenis. Todo lo demás del catálogo se pinta con la
/// pantalla genérica alimentada por el contrato.
const ownScreenSports = {kFootball, kNba, kTennis};

bool isGenericSport(SportId sport) => !ownScreenSports.contains(sport);

/// Familia de los mercados que el catálogo del deporte no nombra (siempre al final).
const otherFamily = 'otros';

const _statuses = {'scheduled', 'live', 'awaiting_result', 'finished', 'cancelled'};
const _outcomes = {'win', 'loss', 'push', 'void'};

DateTime? _time(Object? v) => v is String ? DateTime.tryParse(v)?.toUtc() : null;
String? _str(Object? v) => v is String && v.isNotEmpty ? v : null;
double? _finite(Object? v) => v is num && v.isFinite ? v.toDouble() : null;

/// Un mercado del contrato como `SportMarket`; `null` si no es utilizable. `eventSealedAt` rellena el sello de un
/// mercado que no trae el suyo. La cuota solo se acepta con su origen (`reference`): el contrato no trae casa.
SportMarket? contractMarket(Object? raw, {required DateTime eventSealedAt}) {
  if (raw is! Map) return null;
  final id = _str(raw['id']), label = _str(raw['label']);
  final p = _finite(raw['probability']);
  final eligible = raw['eligible'];
  if (id == null || label == null || raw['selection'] is! String || p == null || p <= 0 || p >= 1 || eligible is! bool) {
    return null;
  }
  final sealed = _time(raw['sealed_at']) ?? eventSealedAt;
  final price = _finite(raw['price']);
  final reference = raw['reference'] is String ? (raw['reference'] as String).trim() : '';
  final quoted = price != null && price > 1 && reference.isNotEmpty;
  final outcome = raw['outcome'];
  return SportMarket(
    id: id,
    label: label,
    selection: raw['selection'] as String,
    probability: p,
    sealedAt: sealed,
    eligible: eligible,
    outcome: outcome is String && _outcomes.contains(outcome) ? outcome : null,
    market: _str(raw['market']),
    player: _str(raw['player']),
    playerId: _str(raw['player_id']),
    line: _finite(raw['line']),
    price: quoted ? price : null,
    book: quoted ? reference : null,
    quotedAt: quoted ? sealed : null,
    // El contrato solo expone lo que el adaptador publica: no hay regla local de banda para un deporte nuevo.
    publishable: eligible,
    family: _str(raw['family']) ?? otherFamily,
    principal: raw['principal'] == true,
  );
}

/// Un evento del contrato como `SportEvent`; `null` si no es utilizable (sin id, equipos u hora de inicio).
SportEvent? contractEvent(Object? raw, SportId sport) {
  if (raw is! Map) return null;
  final id = _str(raw['id']), home = _str(raw['home']), away = _str(raw['away']);
  final start = _time(raw['start']);
  if (id == null || home == null || away == null || start == null || raw['markets'] is! List) return null;
  final sealedAt = _time(raw['sealed_at']) ?? start;
  final images = raw['imagenes'] is Map ? raw['imagenes'] as Map : const {};
  final destacado = raw['destacado'];
  return SportEvent(
    id: id,
    sport: sport,
    home: home,
    away: away,
    league: raw['league'] is String ? raw['league'] as String : '',
    start: start,
    status: raw['status'] is String && _statuses.contains(raw['status']) ? raw['status'] as String : 'scheduled',
    seal: raw['seal'] is String ? raw['seal'] as String : '',
    sealedAt: sealedAt,
    markets: [
      for (final m in raw['markets'] as List)
        ?contractMarket(m, eventSealedAt: sealedAt),
    ],
    surface: _str(raw['surface']),
    score: _str(raw['score']),
    plannedSeal: _time(raw['planned_seal']),
    serverFeatured: true,
    featuredId: destacado is String ? destacado : null,
    imageHome: _ownImage(images['home']),
    imageAway: _ownImage(images['away']),
    generic: true,
  );
}

/// Solo rutas de imagen del propio servidor (`/web/…`); cualquier otra cosa se descarta.
String? _ownImage(Object? v) =>
    v is String && RegExp(r'^/web/[\w./-]+\.(png|jpe?g|webp|svg)$', caseSensitive: false).hasMatch(v) ? v : null;

/// Respuesta de la cartelera (`{contrato, deporte, eventos}`) → eventos ordenados por inicio. Lanza
/// [FormatException] si no es la cartelera de ese deporte.
List<SportEvent> contractEvents(Object? data, SportId sport) {
  if (data is! Map || data['contrato'] != 1 || data['deporte'] != sport || data['eventos'] is! List) {
    throw const FormatException('Invalid sport contract');
  }
  final events = <String, SportEvent>{};
  for (final raw in data['eventos'] as List) {
    if (contractEvent(raw, sport) case final e?) events[e.id] = e;
  }
  return events.values.toList()..sort((a, b) => a.start.compareTo(b.start));
}

String _day(DateTime d) => DateTime(d.year, d.month, d.day).toIso8601String().substring(0, 10);

/// Ventana de la lista: tres días atrás a tres adelante (hora local), en UNA petición de 7 días.
Future<SportFeed> loadContractSport(QuantFutApi api, SportId sport, {DateTime? now}) async {
  final today = now ?? DateTime.now();
  final from = DateTime(today.year, today.month, today.day - 3);
  final data = await api.request(
    '/deportes/v1/${Uri.encodeComponent(sport)}/cartelera',
    query: {'cliente': 'app', 'contrato': 1, 'desde': _day(from), 'dias': 7, 'tz': today.timeZoneOffset.inMinutes},
  );
  return SportFeed(ready: true, events: contractEvents(data, sport));
}

// ---- Familias de mercados ----------------------------------------------------------------------

/// Mercados de una familia del catálogo.
class ContractFamily {
  const ContractFamily(this.id, this.markets);
  final String id;
  final List<SportMarket> markets;
}

/// Ids de las familias del catálogo del deporte, en su orden.
List<String> catalogFamilyIds(SportId sport) => [for (final f in sportCatalog.spec(sport).families) f.id];

/// Familias de un evento en el orden del catálogo, con `otros` siempre al final. Una familia sin mercados no sale.
/// Con `served` (las del endpoint de mercados) se respeta su agrupación y lo que no cuelgue de ellas va a `otros`.
List<ContractFamily> contractFamilies(
  List<SportMarket> markets,
  List<String> order, {
  List<(String, List<String>)>? served,
}) {
  final groups = <ContractFamily>[];
  if (served != null) {
    final byId = {for (final m in markets) m.id: m};
    final placed = <String>{};
    for (final (id, ids) in served) {
      groups.add(ContractFamily(id, [for (final mid in ids) if (byId[mid] case final m? when placed.add(mid)) m]));
    }
    final loose = [for (final m in markets) if (!placed.contains(m.id)) m];
    if (loose.isNotEmpty) groups.add(ContractFamily(otherFamily, loose));
  } else {
    final map = <String, List<SportMarket>>{};
    for (final m in markets) {
      (map[m.family ?? otherFamily] ??= []).add(m);
    }
    groups.addAll([for (final e in map.entries) ContractFamily(e.key, e.value)]);
  }
  int rank(String id) {
    final i = order.indexOf(id);
    return i < 0 ? order.length : i;
  }

  final normal = [
    for (final (i, g) in groups.where((g) => g.id != otherFamily).indexed) (i, g),
  ]..sort((a, b) => rank(a.$2.id) != rank(b.$2.id) ? rank(a.$2.id).compareTo(rank(b.$2.id)) : a.$1.compareTo(b.$1));
  return [
    for (final e in normal) e.$2,
    ...groups.where((g) => g.id == otherFamily),
  ].where((g) => g.markets.isNotEmpty).toList();
}

/// Nombre de la familia: el del catálogo en el idioma actual (cae a `es`) y, sin él, el id legible. `otros` se traduce.
String contractFamilyTitle(AppLocalizations l10n, SportId sport, String familyId) {
  if (familyId == otherFamily) return l10n.sportFamilyOthers;
  final name = sportCatalog.find(sport)?.family(familyId)?.name(l10n.localeName);
  if (name != null) return name;
  final spaced = familyId.replaceAll('_', ' ');
  return spaced.isEmpty ? familyId : '${spaced[0].toUpperCase()}${spaced.substring(1)}';
}

/// Subtítulo de la familia en el catálogo, si lo tiene.
String? contractFamilySubtitle(AppLocalizations l10n, SportId sport, String familyId) =>
    sportCatalog.find(sport)?.family(familyId)?.subtitle(l10n.localeName);

// ---- Bloques de contenido ----------------------------------------------------------------------

/// Bloque de contenido del partido (`partido.bloques`). El cliente los pinta sin conocer el deporte.
sealed class ContentBlock {
  const ContentBlock(this.id, this.title);
  final String id, title;
}

class TableBlock extends ContentBlock {
  const TableBlock(super.id, super.title, this.columns, this.rows);
  final List<String> columns;

  /// Celdas ya como texto (`—` si falta el dato).
  final List<List<String>> rows;
}

class BarsBlock extends ContentBlock {
  const BarsBlock(super.id, super.title, this.items);
  final List<({String label, double value, String? note})> items;
}

class PairsBlock extends ContentBlock {
  const PairsBlock(super.id, super.title, this.items);
  final List<({String label, String value})> items;
}

class TextBlock extends ContentBlock {
  const TextBlock(super.id, super.title, this.body);
  final String body;
}

final _contentId = RegExp(r'^[a-z0-9_]{1,40}$');

bool _isCell(Object? v) => v == null || v is String || (v is num && v.isFinite);

String _cell(Object? v) {
  if (v == null) return '—';
  if (v is num) return NumberFormat('#,##0.###', AppLocale.instance.code).format(v);
  return v as String;
}

ContentBlock? _content(Map raw, String id, String title) {
  switch (raw['tipo']) {
    case 'tabla':
      final cols = raw['columnas'], rows = raw['filas'];
      if (cols is! List || cols.isEmpty || cols.length > 12 || !cols.every((c) => c is String)) return null;
      if (rows is! List || rows.length > 100) return null;
      for (final r in rows) {
        if (r is! List || r.length != cols.length || !r.every(_isCell)) return null;
      }
      return TableBlock(id, title, cols.cast<String>(), [
        for (final r in rows) [for (final c in r as List) _cell(c)],
      ]);
    case 'barras':
      final items = raw['items'];
      if (items is! List || items.length > 20) return null;
      final out = <({String label, double value, String? note})>[];
      for (final i in items) {
        final v = i is Map ? _finite(i['valor']) : null;
        if (i is! Map || i['etiqueta'] is! String || v == null || v < 0 || v > 1 || (i['nota'] != null && i['nota'] is! String)) {
          return null;
        }
        out.add((label: i['etiqueta'] as String, value: v, note: _str(i['nota'])));
      }
      return BarsBlock(id, title, out);
    case 'pares':
      final items = raw['items'];
      if (items is! List || items.length > 30) return null;
      final out = <({String label, String value})>[];
      for (final i in items) {
        if (i is! Map || i['etiqueta'] is! String || !_isCell(i['valor'])) return null;
        out.add((label: i['etiqueta'] as String, value: _cell(i['valor'])));
      }
      return PairsBlock(id, title, out);
    case 'texto':
      final body = raw['cuerpo'];
      return body is String && body.isNotEmpty && body.length <= 600 ? TextBlock(id, title, body) : null;
  }
  return null;
}

/// Bloques de contenido válidos de `partido.bloques`. Un tipo desconocido se ignora sin ruido (una app más vieja que el
/// servidor no debe romperse) y un bloque mal formado o con id repetido se ignora también. Sin tope de cantidad propio:
/// el servidor ya acota el tamaño de cada bloque.
List<ContentBlock> contentBlocks(Object? raw) {
  if (raw is! List) return const [];
  final seen = <String>{};
  final out = <ContentBlock>[];
  for (final b in raw) {
    if (b is! Map) continue;
    final id = b['id'], title = b['titulo'];
    final valid = id is String && _contentId.hasMatch(id) && !seen.contains(id) && title is String && title.isNotEmpty && title.length <= 120;
    if (!valid) {
      if (kDebugMode && b['tipo'] is String) debugPrint('Bloque de contenido ignorado (mal formado): $id');
      continue;
    }
    final block = _content(b, id, title);
    if (block == null) continue;
    seen.add(id);
    out.add(block);
  }
  return out;
}

// ---- Detalle del partido ------------------------------------------------------------------------

/// Detalle de un partido: el evento completo, sus familias del catálogo y sus bloques de contenido.
class ContractDetail {
  const ContractDetail({required this.event, required this.families, required this.blocks});
  final SportEvent event;
  final List<ContractFamily> families;
  final List<ContentBlock> blocks;
}

/// `/partido/{id}?cliente=app&lang=…` (evento completo + bloques en el idioma de la app) y `/partido/{id}/mercados`
/// (familias del catálogo). Si solo falla `/mercados`, el detalle sigue con las familias que traen los propios
/// mercados; si falla `/partido/{id}`, lanza (la pantalla ofrece «Reintentar»).
Future<ContractDetail> loadContractDetail(QuantFutApi api, SportId sport, String eventId, {required String lang}) async {
  final base = '/deportes/v1/${Uri.encodeComponent(sport)}/partido/${Uri.encodeComponent(eventId)}';
  final results = await Future.wait<Object?>([
    api.request(base, query: {'cliente': 'app', 'lang': lang}),
    api.request('$base/mercados', query: {'cliente': 'app'}).then<Object?>((v) => v, onError: (Object _) => null),
  ]);
  final data = results[0], markets = results[1];
  if (data is! Map || data['contrato'] != 1 || data['deporte'] != sport) throw const FormatException('Invalid sport contract');
  final event = contractEvent(data['evento'], sport);
  if (event == null) throw const FormatException('Invalid sport event');
  List<(String, List<String>)>? served;
  if (markets is Map && markets['contrato'] == 1 && '${markets['evento_id']}' == event.id && markets['familias'] is List) {
    served = [
      for (final g in markets['familias'] as List)
        if (g is Map && g['id'] is String && g['mercados'] is List)
          (g['id'] as String, [for (final m in g['mercados'] as List) if (m is Map && m['id'] is String) m['id'] as String]),
    ];
  }
  return ContractDetail(
    event: event,
    families: contractFamilies(event.markets, catalogFamilyIds(sport), served: served),
    blocks: contentBlocks(data['bloques']),
  );
}
