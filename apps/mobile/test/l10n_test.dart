// Reglas de traducción de la app (ver memoria del proyecto «traducciones siempre al día»):
//  * los 6 idiomas (es, en, pt, fr, it, de) tienen exactamente las mismas claves;
//  * ningún texto vacío y todos los parámetros ({nombre}) de la plantilla presentes;
//  * ninguna cadena fija visible en la interfaz: todo pasa por `context.l10n`.
//
// Para añadir o cambiar un texto:  python tool/l10n_add.py nuevos.json
//
// Excepciones en el código: una línea con `// l10n-ignore`, o un bloque entre
// `// l10n-ignore-start` y `// l10n-ignore-end`, solo para identificadores de datos
// (p. ej. códigos que envía el servidor), nunca para texto que ve la persona.
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

const languages = ['es', 'en', 'pt', 'fr', 'it', 'de'];

Map<String, dynamic> arb(String language) =>
    jsonDecode(File('lib/l10n/app_$language.arb').readAsStringSync())
        as Map<String, dynamic>;

Set<String> keysOf(Map<String, dynamic> data) =>
    data.keys.where((k) => !k.startsWith('@')).toSet();

/// Código de interfaz que NO se traduce: heredado de la plantilla original y no
/// alcanzable desde `main.dart`. Si algún día se conecta, hay que traducirlo.
const deadCode = {
  'lib/product/market_screens.dart',
  'lib/product/match_detail.dart',
  'lib/product/match_visuals.dart',
  'lib/product/profile_settings.dart',
  'lib/product/vip_performance.dart',
};

/// Carpetas con la interfaz activa.
const uiRoots = [
  'lib/product',
  'lib/core',
  'lib/onbonding_screen',
  'lib/widgets',
];

/// Marcas y siglas que se escriben igual en todos los idiomas.
const sameEverywhere = {'QuantFut', 'Q.', 'VIP', 'xG', 'vs', 'NBA', 'H2H'};

final spanishLetters = RegExp('[áéíóúñÁÉÍÓÚÑ¿¡]');
final stringLiteral = RegExp(
  r"""'(?:[^'\\\n]|\\.)*'|"(?:[^"\\\n]|\\.)*" """.trim(),
);

/// Primer argumento literal de los widgets que pintan texto.
final textArgument = RegExp(
  r"""(?:\bText|liveText|liveHeading|liveButton|training|labelText:|hintText:|tooltip:|label:|title:|semanticsLabel:)\(?\s*(?:const\s+)?'([^'$\\\n]+)'""",
);

List<File> uiFiles() => [
  File('lib/main.dart'),
  for (final root in uiRoots)
    ...Directory(root)
        .listSync(recursive: true)
        .whereType<File>()
        .where((f) => f.path.endsWith('.dart')),
];

/// Líneas de [file] fuera de bloques/marcas de excepción: (número, texto).
Iterable<(int, String)> scannedLines(File file) sync* {
  var ignoring = false;
  final lines = file.readAsLinesSync();
  for (var i = 0; i < lines.length; i++) {
    final line = lines[i];
    if (line.contains('l10n-ignore-start')) ignoring = true;
    if (line.contains('l10n-ignore-end')) {
      ignoring = false;
      continue;
    }
    if (ignoring || line.contains('l10n-ignore')) continue;
    final trimmed = line.trim();
    if (trimmed.startsWith('//') || trimmed.startsWith('import ')) continue;
    yield (i + 1, line);
  }
}

void main() {
  group('traducciones', () {
    final data = {for (final l in languages) l: arb(l)};

    test('los 6 idiomas tienen exactamente las mismas claves', () {
      final base = keysOf(data['es']!);
      for (final l in languages.skip(1)) {
        final keys = keysOf(data[l]!);
        expect(base.difference(keys), isEmpty, reason: 'faltan en app_$l.arb');
        expect(
          keys.difference(base),
          isEmpty,
          reason: 'sobran en app_$l.arb (no existen en app_es.arb)',
        );
      }
    });

    test('ningún texto vacío', () {
      for (final l in languages) {
        for (final key in keysOf(data[l]!)) {
          expect(
            (data[l]![key] as String).trim(),
            isNotEmpty,
            reason: '$key vacío en $l',
          );
        }
      }
    });

    test('todos los parámetros de la plantilla aparecen en cada idioma', () {
      final es = data['es']!;
      for (final key in keysOf(es)) {
        final meta = es['@$key'];
        if (meta is! Map || meta['placeholders'] is! Map) continue;
        for (final name in (meta['placeholders'] as Map).keys) {
          for (final l in languages) {
            final text = data[l]![key] as String;
            expect(
              RegExp('\\{$name[,}]').hasMatch(text),
              isTrue,
              reason: '«{$name}» falta en $key ($l)',
            );
          }
        }
      }
    });

    test('las traducciones no son copias del español (salvo siglas)', () {
      // Un texto idéntico al español en un idioma casi siempre es una traducción
      // olvidada. Se permiten siglas, marcas y palabras iguales en varios idiomas.
      final es = data['es']!;
      final suspicious = <String>[];
      // Solo cuenta el texto real: sin {parámetros}, sintaxis ICU ni símbolos.
      String words(String text) {
        var t = text;
        for (var i = 0; i < 4; i++) {
          t = t.replaceAll(RegExp(r'\{[^{}]*\}'), '');
        }
        return t.replaceAll(RegExp(r'[^A-Za-zÀ-ÿ]'), '');
      }

      for (final key in keysOf(es)) {
        final base = es[key] as String;
        // Frases cortas: pueden coincidir.
        if (words(base).length < 24) {
          continue;
        }
        for (final l in languages.skip(1)) {
          if (data[l]![key] == base) {
            suspicious.add('$key ($l)');
          }
        }
      }
      expect(
        suspicious,
        isEmpty,
        reason:
            'Texto igual al español; ¿falta traducirlo?\n${suspicious.join('\n')}',
      );
    });
  });

  test('no hay textos fijos en español en la interfaz', () {
    final offenders = <String>[];
    for (final file in uiFiles()) {
      final path = file.path.replaceAll(r'\', '/');
      if (deadCode.contains(path)) continue;
      for (final (number, line) in scannedLines(file)) {
        for (final m in stringLiteral.allMatches(line)) {
          final text = m.group(0)!;
          if (spanishLetters.hasMatch(text)) {
            offenders.add('$path:$number  $text');
          }
        }
      }
    }
    expect(
      offenders,
      isEmpty,
      reason:
          'Texto fijo en español: muévelo a lib/l10n con tool/l10n_add.py y usa context.l10n\n${offenders.join('\n')}',
    );
  });

  test('ningún widget de texto recibe una cadena literal (con o sin acentos)', () {
    final offenders = <String>[];
    for (final file in uiFiles()) {
      final path = file.path.replaceAll(r'\', '/');
      if (deadCode.contains(path)) continue;
      for (final (number, line) in scannedLines(file)) {
        for (final m in textArgument.allMatches(line)) {
          final text = m.group(1)!;
          final isWord = RegExp('[A-Za-zÀ-ÿ]{3}').hasMatch(text);
          if (isWord &&
              !sameEverywhere.contains(text) &&
              !text.startsWith('Gilroy')) {
            offenders.add('$path:$number  \'$text\'');
          }
        }
      }
    }
    expect(
      offenders,
      isEmpty,
      reason:
          'Cadena literal en un widget de texto: usa context.l10n.\n${offenders.join('\n')}',
    );
  });
}
