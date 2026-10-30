import 'package:flutter/material.dart';

import 'live_api.dart';
import 'qf_theme.dart';

/// Foto de tenis del servidor (CC BY-SA): autor, licencia y página para el crédito visible.
class TennisPhoto {
  const TennisPhoto({
    required this.path,
    this.author = '',
    this.license = '',
    this.page = '',
  });
  final String path, author, license, page;
}

// Mismo criterio que `norm()` del servidor (scripts/imagenes/descargar_imagenes.py): NFD,
// sin marcas combinadas, minúsculas y espacios colapsados. Sin transliteración: la barra
// de d/l (por ejemplo la d cruzada) no se descompone y queda igual, como en el servidor.
// Tabla en códigos de caracteres (la prueba de textos fijos no admite acentos en lib).
const _accentCodes = <int>[
    192, 193, 194, 195, 196, 197, 199, 200, 201, 202, 203, 204,
    205, 206, 207, 209, 210, 211, 212, 213, 214, 217, 218, 219,
    220, 221, 224, 225, 226, 227, 228, 229, 231, 232, 233, 234,
    235, 236, 237, 238, 239, 241, 242, 243, 244, 245, 246, 249,
    250, 251, 252, 253, 255, 256, 257, 258, 259, 260, 261, 262,
    263, 264, 265, 266, 267, 268, 269, 270, 271, 274, 275, 276,
    277, 278, 279, 280, 281, 282, 283, 284, 285, 286, 287, 288,
    289, 290, 291, 292, 293, 296, 297, 298, 299, 300, 301, 302,
    303, 304, 308, 309, 310, 311, 313, 314, 315, 316, 317, 318,
    323, 324, 325, 326, 327, 328, 332, 333, 334, 335, 336, 337,
    340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351,
    352, 353, 354, 355, 356, 357, 360, 361, 362, 363, 364, 365,
    366, 367, 368, 369, 370, 371, 372, 373, 374, 375, 376, 377,
    378, 379, 380, 381, 382, 416, 417, 431, 432, 461, 462, 463,
    464, 465, 466, 467, 468, 469, 470, 471, 472, 473, 474, 475,
    476, 478, 479, 480, 481, 486, 487, 488, 489, 490, 491, 492,
    493, 496, 500, 501, 504, 505, 506, 507, 512, 513, 514, 515,
    516, 517, 518, 519, 520, 521, 522, 523, 524, 525, 526, 527,
    528, 529, 530, 531, 532, 533, 534, 535, 536, 537, 538, 539,
    542, 543, 550, 551, 552, 553, 554, 555, 556, 557, 558, 559,
    560, 561, 562, 563, 7680, 7681, 7682, 7683, 7684, 7685, 7686, 7687,
    7688, 7689, 7690, 7691, 7692, 7693, 7694, 7695, 7696, 7697, 7698, 7699,
    7700, 7701, 7702, 7703, 7704, 7705, 7706, 7707, 7708, 7709, 7710, 7711,
    7712, 7713, 7714, 7715, 7716, 7717, 7718, 7719, 7720, 7721, 7722, 7723,
    7724, 7725, 7726, 7727, 7728, 7729, 7730, 7731, 7732, 7733, 7734, 7735,
    7736, 7737, 7738, 7739, 7740, 7741, 7742, 7743, 7744, 7745, 7746, 7747,
    7748, 7749, 7750, 7751, 7752, 7753, 7754, 7755, 7756, 7757, 7758, 7759,
    7760, 7761, 7762, 7763, 7764, 7765, 7766, 7767, 7768, 7769, 7770, 7771,
    7772, 7773, 7774, 7775, 7776, 7777, 7778, 7779, 7780, 7781, 7782, 7783,
    7784, 7785, 7786, 7787, 7788, 7789, 7790, 7791, 7792, 7793, 7794, 7795,
    7796, 7797, 7798, 7799, 7800, 7801, 7802, 7803, 7804, 7805, 7806, 7807,
    7808, 7809, 7810, 7811, 7812, 7813, 7814, 7815, 7816, 7817, 7818, 7819,
    7820, 7821, 7822, 7823, 7824, 7825, 7826, 7827, 7828, 7829, 7830, 7831,
    7832, 7833, 7840, 7841, 7842, 7843, 7844, 7845, 7846, 7847, 7848, 7849,
    7850, 7851, 7852, 7853, 7854, 7855, 7856, 7857, 7858, 7859, 7860, 7861,
    7862, 7863, 7864, 7865, 7866, 7867, 7868, 7869, 7870, 7871, 7872, 7873,
    7874, 7875, 7876, 7877, 7878, 7879, 7880, 7881, 7882, 7883, 7884, 7885,
    7886, 7887, 7888, 7889, 7890, 7891, 7892, 7893, 7894, 7895, 7896, 7897,
    7898, 7899, 7900, 7901, 7902, 7903, 7904, 7905, 7906, 7907, 7908, 7909,
    7910, 7911, 7912, 7913, 7914, 7915, 7916, 7917, 7918, 7919, 7920, 7921,
    7922, 7923, 7924, 7925, 7926, 7927, 7928, 7929,
];
const _accentBases = 'AAAAAACEEEEIIIINOOOOOUUUUYaaaaaaceeeeiiiinooooouuuuyyAaAaAaCcCcCcCcDdEeEeEeEeEeGgGgGgGgHhIiIiIiIiIJjKkLlLlLlNnNnNnOoOoOoRrRrRrSsSsSsSsTtTtUuUuUuUuUuUuWwYyYZzZzZzOoUuAaIiOoUuUuUuUuUuAaAaGgKkOoOojGgNnAaAaAaEeEeIiIiOoOoRrRrUuUuSsTtHhAaEeOoOoOoOoYyAaBbBbBbCcDdDdDdDdDdEeEeEeEeEeFfGgHhHhHhHhHhIiIiKkKkKkLlLlLlLlMmMmMmNnNnNnNnOoOoOoOoPpPpRrRrRrRrSsSsSsSsSsTtTtTtTtUuUuUuUuUuVvVvWwWwWwWwWwXxXxYyZzZzZzhtwyAaAaAaAaAaAaAaAaAaAaAaAaEeEeEeEeEeEeEeEeIiIiOoOoOoOoOoOoOoOoOoOoOoOoUuUuUuUuUuUuUuYyYyYyYy';
final _accentMap = () {
  final m = <int, String>{};
  var j = 0;
  // Las bases de longitud 1 son lo habitual; se guardan en el orden de la tabla.
  for (var i = 0; i < _accentCodes.length; i++) {
    final len = _accentLens.codeUnitAt(i) - 48;
    m[_accentCodes[i]] = _accentBases.substring(j, j + len);
    j += len;
  }
  return m;
}();
const _accentLens = '11111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111';

String _norm(String s) {
  final b = StringBuffer();
  for (final r in s.runes) {
    if (r >= 0x300 && r <= 0x36f) continue;
    b.write(_accentMap[r] ?? String.fromCharCode(r));
  }
  return b.toString().toLowerCase().replaceAll(RegExp(r'\s+'), ' ').trim();
}

/// Catálogo de imágenes del servidor (`/web/imagenes/manifiesto.json`).
class ImageCatalog {
  const ImageCatalog._(this._nba, this._tennis);
  static const empty = ImageCatalog._({}, {});
  final Map<String, String> _nba;
  final Map<String, TennisPhoto> _tennis;

  factory ImageCatalog.fromManifest(JsonMap? m) {
    if (m == null) return empty;
    final nba = m['nba'], tenis = m['tenis'];
    final nbaOut = <String, String>{};
    final tennisOut = <String, TennisPhoto>{};
    if (nba is Map) {
      for (final e in nba.entries) {
        final v = e.value;
        if (v is Map && v['f'] is String && _safeFile(v['f'] as String)) {
          nbaOut[e.key.toString().toUpperCase()] = v['f'] as String;
        }
      }
    }
    if (tenis is Map) {
      for (final e in tenis.entries) {
        final v = e.value;
        if (v is Map && v['f'] is String && _safeFile(v['f'] as String)) {
          tennisOut[_norm(e.key.toString())] = TennisPhoto(
            path: '/web/imagenes/tenis/${v['f']}',
            author: '${v['a'] ?? ''}',
            license: '${v['l'] ?? ''}',
            page: '${v['p'] ?? ''}',
          );
        }
      }
    }
    if (nbaOut.isEmpty && tennisOut.isEmpty) return empty;
    return ImageCatalog._(nbaOut, tennisOut);
  }

  static bool _safeFile(String f) =>
      RegExp(r'^[A-Za-z0-9._-]+$').hasMatch(f) &&
      RegExp(r'[A-Za-z0-9]').hasMatch(f);

  String? nbaLogo(String abbr) {
    final k = abbr.toUpperCase();
    return _nba.containsKey(k) ? '/web/imagenes/nba/$k.png' : null;
  }

  TennisPhoto? tennisPhoto(String fullName) => _tennis[_norm(fullName)];
}

/// Retrato NBA por id numérico; un id inválido da `''` (el avatar cae a iniciales).
String nbaPlayerPhoto(String playerId) =>
    RegExp(r'^[1-9][0-9]{0,7}$').hasMatch(playerId)
    ? '/web/imagenes/jugadores/nba/$playerId.png'
    : '';

// Las 30 siglas NBA con su nombre completo (el feed da nombres, el logo va por sigla).
const _nbaTeams = <String, String>{
  'ATL': 'atlanta hawks', 'BOS': 'boston celtics', 'BKN': 'brooklyn nets',
  'CHA': 'charlotte hornets', 'CHI': 'chicago bulls', 'CLE': 'cleveland cavaliers',
  'DAL': 'dallas mavericks', 'DEN': 'denver nuggets', 'DET': 'detroit pistons',
  'GSW': 'golden state warriors', 'HOU': 'houston rockets', 'IND': 'indiana pacers',
  'LAC': 'los angeles clippers', 'LAL': 'los angeles lakers', 'MEM': 'memphis grizzlies',
  'MIA': 'miami heat', 'MIL': 'milwaukee bucks', 'MIN': 'minnesota timberwolves',
  'NOP': 'new orleans pelicans', 'NYK': 'new york knicks', 'OKC': 'oklahoma city thunder',
  'ORL': 'orlando magic', 'PHI': 'philadelphia 76ers', 'PHX': 'phoenix suns',
  'POR': 'portland trail blazers', 'SAC': 'sacramento kings', 'SAS': 'san antonio spurs',
  'TOR': 'toronto raptors', 'UTA': 'utah jazz', 'WAS': 'washington wizards',
};

final _nbaByName = () {
  final m = <String, String>{};
  for (final e in _nbaTeams.entries) {
    m[e.value] = e.key;
    // Nombre corto: lo que sigue a la ciudad («knicks», «trail blazers», «76ers»).
    final words = e.value.split(' ');
    m[words.last] = e.key;
    if (words.length > 2) m[words.sublist(words.length - 2).join(' ')] = e.key;
  }
  m['la clippers'] = 'LAC';
  m['la lakers'] = 'LAL';
  m['blazers'] = 'POR';
  m['sixers'] = 'PHI';
  return m;
}();

/// Sigla NBA de un nombre de equipo (completo o corto); desconocido: null (avatar con iniciales).
String? nbaTricode(String name) => _nbaByName[_norm(name)];

/// URL absoluta de una ruta del servidor; nula o vacía da null. Toda pantalla debe usarla
/// para cada ruta de imagen (así un '' de `nbaPlayerPhoto` nunca pide la raíz de la API).
String? serverImageUrl(QuantFutApi api, String? path) =>
    path == null || path.isEmpty ? null : api.base.resolve(path).toString();

Future<ImageCatalog>? _catalog;

/// Carga el manifiesto una vez; si falló, el siguiente refresco lo reintenta.
Future<ImageCatalog> loadImageCatalog(QuantFutApi api, {bool refresh = false}) {
  if (refresh) _catalog = null;
  return _catalog ??= () async {
    try {
      final r = await api.request('/web/imagenes/manifiesto.json');
      final c = ImageCatalog.fromManifest(r is Map<String, dynamic> ? r : null);
      if (identical(c, ImageCatalog.empty)) _catalog = null;
      return c;
    } catch (_) {
      _catalog = null;
      return ImageCatalog.empty;
    }
  }();
}

enum AvatarShape { contain, circle }

// (horizontal, colores). Solo banderas que son franjas lisas; el resto, sin bandera
// (una bandera mal dibujada es peor que ninguna).
const _stripes = <String, (bool, List<int>)>{
  'ESP': (true, [0xffaa151b, 0xfff1bf00, 0xfff1bf00, 0xffaa151b]),
  'GER': (true, [0xff000000, 0xffdd0000, 0xffffce00]),
  'ITA': (false, [0xff009246, 0xffffffff, 0xffce2b37]),
  'FRA': (false, [0xff0055a4, 0xffffffff, 0xffef4135]),
  'POL': (true, [0xffffffff, 0xffdc143c]),
  'ARG': (true, [0xff74acdf, 0xffffffff, 0xff74acdf]),
  'SRB': (true, [0xffc6363c, 0xff0c4076, 0xffffffff]),
};

/// Bandera de 14×10 con franjas simples; código desconocido: nada.
class _Flag extends StatelessWidget {
  const _Flag(this.code);
  final String code;
  @override
  Widget build(BuildContext context) {
    final f = _stripes[code.toUpperCase()];
    if (f == null) return const SizedBox.shrink();
    final bars = [
      for (final c in f.$2) Expanded(child: ColoredBox(color: Color(c))),
    ];
    return Container(
      key: ValueKey('qf-flag-${code.toUpperCase()}'),
      width: 14,
      height: 10,
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(1.5),
        border: Border.all(color: QfColors.border, width: 0.5),
      ),
      child: f.$1 ? Column(children: bars) : Row(children: bars),
    );
  }
}

String _initials(String name) {
  final w = name
      .trim()
      .split(RegExp(r'\s+'))
      .where((s) => s.isNotEmpty)
      .toList();
  if (w.isEmpty) return '?';
  final s = w.length == 1
      ? (w.first.length > 1 ? w.first.substring(0, 2) : w.first)
      : '${w.first[0]}${w.last[0]}';
  return s.toUpperCase();
}

/// Escudo, logo o retrato. `url` ya resuelta (absoluta); vacía o con error: iniciales
/// (nunca la foto de otra persona). Decorativo salvo que se pase `semanticLabel`.
class QfAvatar extends StatelessWidget {
  const QfAvatar({
    super.key,
    this.url,
    required this.name,
    this.size = 32,
    this.shape = AvatarShape.contain,
    this.countryCode,
    this.ring,
    this.semanticLabel,
  });
  final String? url;
  final String name;
  final double size;
  final AvatarShape shape;
  final String? countryCode;
  final Color? ring;
  final String? semanticLabel;

  @override
  Widget build(BuildContext context) {
    final circle = shape == AvatarShape.circle;
    final u = url;
    final usable = u != null && Uri.tryParse(u)?.hasScheme == true;
    final fallback = _Fallback(
      initials: _initials(name),
      size: size,
      circle: circle,
      countryCode: countryCode,
    );
    Widget child = usable
        ? Image.network(
            u,
            width: size,
            height: size,
            headers: const {'User-Agent': 'QuantFut/1.0 (Android; Flutter)'},
            fit: circle ? BoxFit.cover : BoxFit.contain,
            alignment: circle ? const Alignment(0, -0.7) : Alignment.center,
            excludeFromSemantics: true,
            errorBuilder: (_, error, stack) => fallback,
          )
        : fallback;
    if (circle) {
      child = ClipOval(child: child);
      child = Container(
        width: size,
        height: size,
        decoration: ring == null
            ? null
            : BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(color: ring!, width: 2),
              ),
        child: child,
      );
    }
    final box = SizedBox(width: size, height: size, child: child);
    return semanticLabel == null
        ? ExcludeSemantics(child: box)
        : Semantics(label: semanticLabel, image: true, child: box);
  }
}

class _Fallback extends StatelessWidget {
  const _Fallback({
    required this.initials,
    required this.size,
    required this.circle,
    required this.countryCode,
  });
  final String initials;
  final double size;
  final bool circle;
  final String? countryCode;
  @override
  Widget build(BuildContext context) {
    final cc = countryCode;
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: QfColors.surface2,
        shape: circle ? BoxShape.circle : BoxShape.rectangle,
        borderRadius: circle ? null : BorderRadius.circular(size * 0.2),
      ),
      child: Stack(
        alignment: Alignment.center,
        children: [
          Text(
            initials,
            style: TextStyle(
              fontFamily: qfMono,
              fontSize: size * 0.36,
              fontWeight: FontWeight.w700,
              color: QfColors.text2,
            ),
          ),
          if (cc != null && cc.isNotEmpty)
            Positioned(right: 0, bottom: 0, child: _Flag(cc)),
        ],
      ),
    );
  }
}
