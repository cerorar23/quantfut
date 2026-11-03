import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import 'live_widgets.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';
import 'sports.dart';

/// Perfil → «Mis deportes»: orden con flechas, interruptor para mostrar u ocultar y el
/// primero visible como deporte por defecto. Guarda con [SportPrefs.save] a cada cambio y
/// avisa con [onChanged] para que el shell relea su lista de deportes.
class MySportsSection extends StatefulWidget {
  const MySportsSection({super.key, required this.prefs, required this.onChanged});

  final SportPrefs prefs;
  final Future<void> Function() onChanged;

  @override
  State<MySportsSection> createState() => _MySportsSectionState();
}

class _MySportsSectionState extends State<MySportsSection> {
  List<SportKind> order = SportKind.values;
  Set<SportKind> hidden = {};
  bool saving = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final (o, h) = await (widget.prefs.order(), widget.prefs.hidden()).wait;
      if (mounted) {
        setState(() {
          order = o;
          hidden = h;
        });
      }
    } catch (_) {
      /* Se queda con el orden de fábrica y todo visible. */
    }
  }

  Future<void> _save(List<SportKind> newOrder, Set<SportKind> newHidden) async {
    if (saving) return;
    final (oldOrder, oldHidden) = (order, hidden);
    setState(() {
      saving = true;
      order = newOrder;
      hidden = newHidden;
    });
    try {
      await widget.prefs.save(order: newOrder, hidden: newHidden);
    } catch (_) {
      // Solo un fallo al guardar revierte: lo que se ve es lo guardado.
      if (mounted) {
        setState(() {
          order = oldOrder;
          hidden = oldHidden;
          saving = false;
        });
        liveNotice(context, context.l10n.profileMySportsSaveError);
      }
      return;
    }
    try {
      await widget.onChanged();
    } catch (_) {
      /* Ya está guardado: el shell lo relee en su próxima carga. */
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  void _move(int from, int to) {
    final next = [...order];
    next.insert(to, next.removeAt(from));
    _save(next, hidden);
  }

  void _toggle(SportKind sport, bool show) {
    if (!show && order.where((k) => !hidden.contains(k)).length <= 1) {
      liveNotice(context, context.l10n.profileMySportsLastVisible);
      return;
    }
    _save(order, show ? ({...hidden}..remove(sport)) : {...hidden, sport});
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final first = order.firstWhere((k) => !hidden.contains(k), orElse: () => order.first);
    return Column(
      key: const ValueKey('my-sports'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        qfTitle(l10n.profileMySports),
        Text(l10n.profileMySportsHint, style: const TextStyle(fontSize: 12, color: QfColors.text2)),
        const SizedBox(height: 4),
        for (final (i, sport) in order.indexed)
          _SportRow(
            key: ValueKey('my-sport-${sport.id}'),
            sport: sport,
            shown: !hidden.contains(sport),
            isDefault: sport == first,
            onUp: i == 0 || saving ? null : () => _move(i, i - 1),
            onDown: i == order.length - 1 || saving ? null : () => _move(i, i + 1),
            onToggle: saving ? null : (v) => _toggle(sport, v),
          ),
      ],
    );
  }
}

class _SportRow extends StatelessWidget {
  const _SportRow({
    super.key,
    required this.sport,
    required this.shown,
    required this.isDefault,
    required this.onUp,
    required this.onDown,
    required this.onToggle,
  });

  final SportKind sport;
  final bool shown, isDefault;
  final VoidCallback? onUp, onDown;
  final ValueChanged<bool>? onToggle;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final spec = sportSpecs[sport]!;
    final name = spec.label(l10n);
    return Container(
      constraints: const BoxConstraints(minHeight: 52),
      decoration: const BoxDecoration(border: Border(top: BorderSide(color: QfColors.border))),
      child: Row(
        children: [
          Icon(spec.icon, size: 20, color: shown ? spec.accent : QfColors.muted),
          const SizedBox(width: 10),
          Expanded(
            child: Wrap(
              crossAxisAlignment: WrapCrossAlignment.center,
              spacing: 6,
              children: [
                Text(name, style: TextStyle(fontSize: 14, color: shown ? QfColors.text : QfColors.text2)),
                if (isDefault)
                  Text(l10n.profileMySportsDefault, style: const TextStyle(fontSize: 11, color: QfColors.text2)),
              ],
            ),
          ),
          IconButton(
            key: ValueKey('my-sport-up-${sport.id}'),
            tooltip: l10n.profileMySportsUp(name),
            constraints: const BoxConstraints(minWidth: 44, minHeight: 44),
            color: QfColors.text2,
            onPressed: onUp,
            icon: const Icon(Icons.arrow_upward),
          ),
          IconButton(
            key: ValueKey('my-sport-down-${sport.id}'),
            tooltip: l10n.profileMySportsDown(name),
            constraints: const BoxConstraints(minWidth: 44, minHeight: 44),
            color: QfColors.text2,
            onPressed: onDown,
            icon: const Icon(Icons.arrow_downward),
          ),
          Semantics(
            label: l10n.profileMySportsShow(name),
            child: Switch(
              key: ValueKey('my-sport-switch-${sport.id}'),
              materialTapTargetSize: MaterialTapTargetSize.padded,
              value: shown,
              activeThumbColor: QfColors.onPrimary,
              activeTrackColor: QfColors.primary,
              inactiveThumbColor: QfColors.text2,
              inactiveTrackColor: QfColors.border,
              onChanged: onToggle,
            ),
          ),
        ],
      ),
    );
  }
}
