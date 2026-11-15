import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../l10n/app_locale.dart';
import '../l10n/pick_labels.dart';
import 'league_names.dart';
import 'live_api.dart';
import 'live_widgets.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';
import 'sport_images.dart';

DateTime? _kickoff(JsonMap pick) => dateValue(pick['kickoff_utc'])?.toLocal();

/// Alta probabilidad: acierto histórico, pronósticos abiertos agrupados por día y los de
/// candado resumidos en una sola tarjeta plegable (no una por cada uno).
class HighProbabilityView extends StatelessWidget {
  const HighProbabilityView({
    super.key,
    required this.report,
    required this.minPercent,
    required this.maxPercent,
    this.freePercent = 10,
    required this.onOpen,
    required this.onVip,
    this.onUnlock,
    this.unlockCost,
  });

  final JsonMap report;
  final int minPercent, maxPercent;

  /// Porcentaje de los pronósticos del día que son gratis; lo manda el servidor.
  final int freePercent;
  final void Function(JsonMap pick) onOpen;
  final VoidCallback onVip;
  final void Function(JsonMap pick)? onUnlock;
  final Object? unlockCost;

  /// El de mayor probabilidad entre los abiertos; a igualdad, el de cuota más alta.
  static JsonMap? best(List<JsonMap> open) {
    double number(dynamic v) => v is num && v.isFinite ? v.toDouble() : -1;
    JsonMap? top;
    for (final p in open) {
      if (number(p['prob']) < 0) continue;
      if (top == null) {
        top = p;
        continue;
      }
      final byProb = number(p['prob']).compareTo(number(top['prob']));
      final byPrice = number(p['ref_price'] ?? p['price']).compareTo(
        number(top['ref_price'] ?? top['price']),
      );
      if (byProb > 0 || (byProb == 0 && byPrice > 0)) top = p;
    }
    return top;
  }

  /// Etiqueta de día para la cabecera de un grupo (hoy, mañana o fecha corta).
  static String dayLabel(DateTime day, DateTime now, AppLocalizations l10n) {
    DateTime only(DateTime d) => DateTime(d.year, d.month, d.day);
    final diff = only(day).difference(only(now)).inDays;
    if (diff == 0) return l10n.commonToday;
    if (diff == 1) return l10n.picksTomorrow;
    return toBeginningOfSentenceCase(
          DateFormat.MMMEd(AppLocale.instance.code).format(day),
        ) ??
        '';
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final all = [...jsonRows(report['proximos']), ...jsonRows(report['vip'])];
    final open = all.where((p) => p['locked'] != true).toList()
      ..sort((a, b) => '${a['kickoff_utc']}'.compareTo('${b['kickoff_utc']}'));
    final locked = all.where((p) => p['locked'] == true).toList()
      ..sort((a, b) => '${a['kickoff_utc']}'.compareTo('${b['kickoff_utc']}'));
    final top = best(open);
    final allFree = open.every((p) => p['free'] == true);
    final groups = <DateTime, List<JsonMap>>{};
    for (final p in open) {
      final ko = _kickoff(p);
      final key = ko == null ? DateTime(1970) : DateTime(ko.year, ko.month, ko.day);
      groups.putIfAbsent(key, () => []).add(p);
    }
    final now = DateTime.now();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (report['estado'] != 'activa')
          training(
            l10n.picksTrainingReasons('${jsonMap(report)['motivos'] ?? ''}'),
          )
        else ...[
          _TrustCard(history: jsonMap(report['historial'])),
          liveText(
            l10n.picksRangeHint(minPercent, maxPercent, freePercent),
            color: liveMuted,
            size: 12,
          ),
          const SizedBox(height: 14),
          if (all.isEmpty) training(l10n.picksEmpty),
          if (open.isNotEmpty) ...[
            liveText(
              allFree
                  ? l10n.picksFreeHeading(open.length)
                  : l10n.picksAllHeading(open.length),
              bold: true,
              size: 15,
            ),
            for (final entry in groups.entries) ...[
              Padding(
                padding: const EdgeInsets.fromLTRB(2, 12, 0, 8),
                child: liveText(
                  entry.key.year == 1970
                      ? '—'
                      : dayLabel(entry.key, now, l10n),
                  size: 12,
                  color: liveMuted,
                  bold: true,
                ),
              ),
              for (final p in entry.value)
                PickTile(
                  pick: p,
                  best: identical(p, top),
                  onOpen: () => onOpen(p),
                ),
            ],
          ],
          if (locked.isNotEmpty)
            LockedPicksGroup(
              picks: locked,
              onVip: onVip,
              onUnlock: onUnlock,
              unlockCost: unlockCost,
            ),
        ],
      ],
    );
  }
}

/// Acierto real frente al prometido, con barra. Solo si ya hay pronósticos liquidados.
class _TrustCard extends StatelessWidget {
  const _TrustCard({required this.history});

  final JsonMap history;

  @override
  Widget build(BuildContext context) {
    final real = history['acierto_real'];
    final total = (history['n'] as num?)?.toInt() ?? 0;
    if (real is! num || total <= 0) return const SizedBox.shrink();
    final l10n = context.l10n;
    final hits = (history['aciertos'] as num?)?.toInt() ?? 0;
    final promised = history['acierto_prometido'];
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Material(
        key: const ValueKey('high-trust'),
        color: QfColors.surface,
        shape: CutCornerBorder(
          cut: 10,
          side: BorderSide(color: QfColors.green.withValues(alpha: .3)),
        ),
        clipBehavior: Clip.antiAlias,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                l10n.picksTrustTitle.toUpperCase(),
                style: const TextStyle(
                  color: QfColors.muted,
                  fontFamily: qfDisplay,
                  fontWeight: FontWeight.w700,
                  fontSize: 12,
                  letterSpacing: 0.8,
                ),
              ),
              const SizedBox(height: 6),
              Row(
                crossAxisAlignment: CrossAxisAlignment.baseline,
                textBaseline: TextBaseline.alphabetic,
                children: [
                  Text(
                    percentText(real, 1),
                    style: const TextStyle(
                      color: QfColors.green,
                      fontFamily: qfMono,
                      fontWeight: FontWeight.w700,
                      fontSize: 28,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      l10n.picksTrustDetail(hits, total),
                      style: const TextStyle(
                        color: QfColors.muted,
                        fontSize: 12,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              _Meter(value: real / 100, color: QfColors.green),
              if (promised is num) ...[
                const SizedBox(height: 8),
                Text(
                  l10n.picksTrustPromised(percentText(promised, 1)),
                  style: const TextStyle(
                    color: QfColors.muted,
                    fontSize: 11,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// Barra fina de 0 a 1.
class _Meter extends StatelessWidget {
  const _Meter({required this.value, required this.color});

  final double value;
  final Color color;

  @override
  Widget build(BuildContext context) => ClipRRect(
    borderRadius: BorderRadius.circular(2),
    child: Stack(
      children: [
        Container(height: 6, color: const Color(0xff2A2D3A)),
        FractionallySizedBox(
          widthFactor: value.clamp(0, 1).toDouble(),
          child: Container(height: 6, color: color),
        ),
      ],
    ),
  );
}

/// Pronóstico abierto (gratuito o desbloqueado): toda la tarjeta abre el análisis.
class PickTile extends StatelessWidget {
  const PickTile({
    super.key,
    required this.pick,
    required this.onOpen,
    this.best = false,
  });

  final JsonMap pick;
  final VoidCallback onOpen;
  final bool best;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final ko = _kickoff(pick);
    final league = leagueName(pick['league_id']);
    final meta = [
      ?league,
      if (ko != null) DateFormat.Hm(AppLocale.instance.code).format(ko),
    ].join(' · ');
    final prob = pick['prob'];
    final price = decimalText(pick['ref_price'] ?? pick['price']);
    final free = pick['free'] == true;
    final localName = '${pick['local'] ?? ''}';
    final awayName = '${pick['visitante'] ?? ''}';

    return Semantics(
      container: true,
      button: true,
      label:
          '$localName · $awayName. ${pickText(pick)}. ${l10n.pickProbability(realPercent(prob))}. @$price',
      child: Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Material(
          color: QfColors.surface,
          shape: CutCornerBorder(
            cut: 10,
            side: BorderSide(
              color: best ? QfColors.borderStrong : QfColors.border,
            ),
          ),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            customBorder: const CutCornerBorder(cut: 10),
            onTap: onOpen,
            child: ExcludeSemantics(
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            meta,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontFamily: qfMono,
                              fontSize: 11,
                              fontWeight: FontWeight.w500,
                              color: QfColors.muted,
                            ),
                          ),
                        ),
                        if (best) ...[
                          _Chip(l10n.picksBestProb, QfColors.green),
                          const SizedBox(width: 6),
                        ],
                        _Chip(
                          free ? l10n.forecastFree : l10n.forecastUnlocked,
                          free ? QfColors.green : QfColors.cyan,
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        SizedBox(
                          width: 36,
                          height: 36,
                          child: QfAvatar(
                            name: localName,
                            size: 36,
                            kind: QfAvatarKind.logo,
                          ),
                        ),
                        Transform.translate(
                          offset: const Offset(-8, 0),
                          child: SizedBox(
                            width: 36,
                            height: 36,
                            child: QfAvatar(
                              name: awayName,
                              size: 36,
                              kind: QfAvatarKind.logo,
                            ),
                          ),
                        ),
                        const SizedBox(width: 4),
                        Expanded(
                          child: Text.rich(
                            TextSpan(
                              children: [
                                TextSpan(text: localName),
                                const TextSpan(
                                  text: '  vs  ',
                                  style: TextStyle(
                                    color: QfColors.muted,
                                    fontSize: 12,
                                  ),
                                ),
                                TextSpan(text: awayName),
                              ],
                            ),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: QfColors.text,
                              fontFamily: 'Exo 2', fontWeight: FontWeight.w700,
                              fontSize: 15,
                              height: 1.2,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                pickText(pick),
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  color: QfColors.cyan,
                                  fontFamily: qfDisplay,
                                  fontWeight: FontWeight.w700,
                                  fontSize: 17,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Row(
                                children: [
                                  Text(
                                    '@$price',
                                    style: const TextStyle(
                                      color: QfColors.yellow,
                                      fontFamily: qfMono,
                                      fontWeight: FontWeight.w700,
                                      fontSize: 14,
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  Flexible(
                                    child: Text(
                                      l10n.pickOddsAtPublish(
                                        pick['ref_book'] ??
                                            pick['book'] ??
                                            l10n.pickSourceNA,
                                      ),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(
                                        color: QfColors.muted,
                                        fontSize: 11,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 12),
                        Text(
                          realPercent(prob),
                          style: const TextStyle(
                            color: QfColors.cyan,
                            fontFamily: qfMono,
                            fontWeight: FontWeight.w700,
                            fontSize: 26,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Expanded(
                          child: _Meter(
                            value: prob is num ? prob.toDouble() : 0,
                            color: QfColors.green,
                          ),
                        ),
                        const SizedBox(width: 10),
                        Text(
                          '${l10n.picksSeeAnalysis} ›',
                          style: const TextStyle(
                            color: QfColors.cyan,
                            fontWeight: FontWeight.w700,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip(this.label, this.color);

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
    decoration: BoxDecoration(
      color: color.withValues(alpha: .12),
      border: Border.all(color: color.withValues(alpha: .4)),
      borderRadius: BorderRadius.circular(2),
    ),
    child: Text(
      label,
      style: TextStyle(
        color: color,
        fontFamily: qfDisplay,
        fontWeight: FontWeight.w700,
        fontSize: 11,
        letterSpacing: 0.6,
      ),
    ),
  );
}

/// Todos los pronósticos de candado en una sola tarjeta: cuántos son, qué se gana con VIP y la lista, con
/// el pronóstico difuminado (`LockedBlur`), su cuota a la vista y el desbloqueo por monedas. Va desplegada
/// por defecto (decisión del titular, 18-oct-2026); se puede plegar.
class LockedPicksGroup extends StatefulWidget {
  const LockedPicksGroup({
    super.key,
    required this.picks,
    required this.onVip,
    this.onUnlock,
    this.unlockCost,
  });

  final List<JsonMap> picks;
  final VoidCallback onVip;
  final void Function(JsonMap pick)? onUnlock;
  final Object? unlockCost;

  @override
  State<LockedPicksGroup> createState() => _LockedPicksGroupState();
}

class _LockedPicksGroupState extends State<LockedPicksGroup> {
  bool _open = true;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final time = DateFormat.Hm(AppLocale.instance.code);
    return Padding(
      padding: const EdgeInsets.only(top: 6, bottom: 12),
      child: Material(
        key: const ValueKey('high-locked-group'),
        color: QfColors.surface,
        shape: CutCornerBorder(
          cut: 10,
          side: BorderSide(color: QfColors.yellow.withValues(alpha: .4)),
        ),
        clipBehavior: Clip.antiAlias,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.lock_outline, color: QfColors.yellow, size: 26),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          l10n.picksLockedTitle(widget.picks.length),
                          style: const TextStyle(
                            color: QfColors.text,
                            fontFamily: qfDisplay,
                            fontWeight: FontWeight.w700,
                            fontSize: 15,
                            letterSpacing: 0.5,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          l10n.picksLockedHint,
                          style: const TextStyle(
                            color: QfColors.muted,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              liveButton(
                l10n.vipAccessButton,
                widget.onVip,
                color: QfColors.yellow,
              ),
              InkWell(
                key: const ValueKey('high-locked-toggle'),
                onTap: () => setState(() => _open = !_open),
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          _open ? l10n.picksLockedHide : l10n.picksLockedShow,
                          style: const TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                            color: QfColors.cyan,
                          ),
                        ),
                      ),
                      Icon(
                        _open ? Icons.expand_less : Icons.expand_more,
                        color: QfColors.cyan,
                      ),
                    ],
                  ),
                ),
              ),
              if (_open)
                for (final p in widget.picks)
                  Container(
                    margin: const EdgeInsets.only(top: 6),
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 8,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: .04),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.lock_outline, size: 16, color: QfColors.muted),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                '${p['local'] ?? ''} · ${p['visitante'] ?? ''}',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  fontFamily: 'Exo 2', fontWeight: FontWeight.w700,
                                  fontSize: 13,
                                  color: QfColors.text,
                                ),
                              ),
                              Text(
                                [
                                  ?leagueName(p['league_id']),
                                  if (_kickoff(p) != null)
                                    time.format(_kickoff(p)!),
                                ].join(' · '),
                                style: const TextStyle(
                                  fontFamily: qfMono,
                                  fontSize: 11,
                                  color: QfColors.muted,
                                ),
                              ),
                              const SizedBox(height: 4),
                              const LockedBlur(),
                            ],
                          ),
                        ),
                        // La cuota también va difuminada: bloques, no el número, para que quitar el filtro no revele nada.
                        if (p['cuota'] is num) ...[
                          const SizedBox(width: 8),
                          const LockedBlur(
                            text: '@█.██',
                            size: 17,
                            blurKey: ValueKey('locked-quote'),
                          ),
                        ],
                        if (widget.onUnlock != null) ...[
                          const SizedBox(width: 8),
                          OutlinedButton(
                            style: OutlinedButton.styleFrom(
                              foregroundColor: QfColors.cyan,
                              side: const BorderSide(color: QfColors.cyan),
                              padding: const EdgeInsets.symmetric(
                                horizontal: 10,
                                vertical: 4,
                              ),
                              minimumSize: const Size(0, 36),
                              shape: const CutCornerBorder(cut: 6),
                            ),
                            onPressed: () => widget.onUnlock!(p),
                            child: Text(
                              l10n.picksCoinsShort(widget.unlockCost ?? '—'),
                              style: const TextStyle(
                                fontFamily: qfMono,
                                fontSize: 12,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
            ],
          ),
        ),
      ),
    );
  }
}
