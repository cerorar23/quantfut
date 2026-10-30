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

String _norm(String s) {
  // Códigos de los acentos (la prueba de textos fijos no debe verlos como interfaz).
  final from = String.fromCharCodes([
    225, 224, 228, 226, 227, 233, 232, 235, 234, 237, 236, 239, 238,
    243, 242, 246, 244, 245, 250, 249, 252, 251, 241, 231,
  ]);
  const to = 'aaaaaeeeeiiiiooooouuuunc';
  final b = StringBuffer();
  for (final r in s.toLowerCase().runes) {
    final c = String.fromCharCode(r);
    final i = from.indexOf(c);
    b.write(i >= 0 ? to[i] : c);
  }
  return b.toString().trim().replaceAll(RegExp(r'\s+'), ' ');
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

  static bool _safeFile(String f) => RegExp(r'^[A-Za-z0-9._-]+$').hasMatch(f);

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

// (horizontal, colores)
const _stripes = <String, (bool, List<int>)>{
  'ESP': (true, [0xffaa151b, 0xfff1bf00, 0xfff1bf00, 0xffaa151b]),
  'GER': (true, [0xff000000, 0xffdd0000, 0xffffce00]),
  'ITA': (false, [0xff009246, 0xffffffff, 0xffce2b37]),
  'FRA': (false, [0xff0055a4, 0xffffffff, 0xffef4135]),
  'SRB': (true, [0xffc6363c, 0xff0c4076, 0xffffffff]),
  'USA': (true, [0xffb22234, 0xffffffff, 0xff3c3b6e]),
  'GBR': (true, [0xff012169, 0xffffffff, 0xffc8102e]),
  'POL': (true, [0xffffffff, 0xffdc143c]),
  'KAZ': (false, [0xff00afca, 0xfffec50c, 0xff00afca]),
  'DEN': (false, [0xffc8102e, 0xffffffff, 0xffc8102e]),
  'ARG': (true, [0xff74acdf, 0xffffffff, 0xff74acdf]),
  'CAN': (false, [0xffd52b1e, 0xffffffff, 0xffd52b1e]),
  'NOR': (false, [0xffba0c2f, 0xff00205b, 0xffba0c2f]),
  'GRE': (true, [0xff0d5eaf, 0xffffffff, 0xff0d5eaf]),
  'RUS': (true, [0xffffffff, 0xff0039a6, 0xffd52b1e]),
  'CZE': (true, [0xffffffff, 0xffd7141a]),
  'AUS': (true, [0xff00008b, 0xff00008b, 0xffcc0000]),
  'BRA': (true, [0xff009c3b, 0xffffdf00, 0xff009c3b]),
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
