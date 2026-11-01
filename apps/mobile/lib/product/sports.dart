import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import 'qf_theme.dart';

/// Deportes de la app. El `id` es el que se guarda en preferencias y viaja a la API.
enum SportKind {
  football('futbol'),
  nba('nba'),
  tennis('tenis');

  const SportKind(this.id);

  final String id;

  static SportKind? fromId(String? id) {
    for (final kind in values) {
      if (kind.id == id) return kind;
    }
    return null;
  }
}

class SportSpec {
  const SportSpec({
    required this.kind,
    required this.accent,
    required this.icon,
    required this.streams,
  });

  final SportKind kind;
  final Color accent;
  final IconData icon;

  /// Secciones de Predicciones que ofrece el deporte.
  final Set<String> streams;

  String label(AppLocalizations l10n) => switch (kind) {
    SportKind.football => l10n.sportFootball,
    SportKind.nba => l10n.sportNba,
    SportKind.tennis => l10n.sportTennis,
  };
}

const sportSpecs = <SportKind, SportSpec>{
  SportKind.football: SportSpec(
    kind: SportKind.football,
    accent: QfColors.football,
    icon: Icons.sports_soccer,
    streams: {'high', 'ladder', 'parley'},
  ),
  SportKind.nba: SportSpec(
    kind: SportKind.nba,
    accent: QfColors.nba,
    icon: Icons.sports_basketball,
    streams: {'high'},
  ),
  SportKind.tennis: SportSpec(
    kind: SportKind.tennis,
    accent: QfColors.tennis,
    icon: Icons.sports_tennis,
    streams: {'high'},
  ),
};

/// Orden y ocultos. No conoce el almacenamiento: recibe `read`/`write`.
class SportPrefs {
  SportPrefs({required this.read, required this.write});

  final Future<String?> Function(String key) read;
  final Future<void> Function(String key, String value) write;

  static const orderKey = 'sports_order';
  static const hiddenKey = 'sports_hidden';

  List<SportKind> _parse(String? raw) => [
    for (final id in (raw ?? '').split(','))
      ?SportKind.fromId(id.trim()),
  ];

  /// Orden guardado, sin repetidos y con los deportes nuevos al final.
  Future<List<SportKind>> order() async {
    final saved = _parse(await read(orderKey)).toSet().toList();
    return [
      ...saved,
      for (final k in SportKind.values)
        if (!saved.contains(k)) k,
    ];
  }

  /// Ocultos; nunca todos: el primero del orden siempre queda visible.
  Future<Set<SportKind>> hidden() async {
    final hidden = _parse(await read(hiddenKey)).toSet();
    final first = (await order()).first;
    if (hidden.length >= SportKind.values.length) hidden.remove(first);
    return hidden;
  }

  /// Deporte con el que abre la app: el primero visible del orden de «Mis deportes».
  Future<SportKind> initial() async {
    final hiddenNow = await hidden();
    return (await order()).firstWhere((k) => !hiddenNow.contains(k));
  }

  Future<void> save({
    required List<SportKind> order,
    required Set<SportKind> hidden,
  }) async {
    await write(orderKey, order.map((k) => k.id).join(','));
    await write(hiddenKey, hidden.map((k) => k.id).join(','));
  }
}
