import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../l10n/app_locale.dart';
import '../l10n/pick_labels.dart';
import 'league_names.dart';
import 'live_api.dart';
import 'live_widgets.dart';

DateTime? _kickoff(JsonMap pick) => dateValue(pick['kickoff_utc'])?.toLocal();

/// Alta probabilidad: acierto histórico, pronósticos abiertos agrupados por día y los de
/// candado resumidos en una sola tarjeta plegable (no una por cada uno).
class HighProbabilityView extends StatelessWidget {
  const HighProbabilityView({
    super.key,
    required this.report,
    required this.minPercent,
    required this.maxPercent,
    this.freeMax = 4,
    required this.onOpen,
    required this.onVip,
    this.onUnlock,
    this.unlockCost,
  });

  final JsonMap report;
  final int minPercent, maxPercent;

  /// Tope de pronósticos gratis abiertos a la vez; lo manda el servidor.
  final int freeMax;
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
            l10n.picksRangeHint(minPercent, maxPercent, freeMax),
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
    return Container(
      key: const ValueKey('high-trust'),
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: livePanel,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: liveGreen.withValues(alpha: .3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          liveText(l10n.picksTrustTitle, size: 12, color: liveMuted),
          const SizedBox(height: 4),
          Row(
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Text(
                percentText(real, 1),
                style: const TextStyle(
                  color: Colors.white,
                  fontFamily: 'Gilroy ExtraBold',
                  fontSize: 28,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: liveText(
                  l10n.picksTrustDetail(hits, total),
                  size: 12,
                  color: liveMuted,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          _Meter(value: real / 100, color: liveGreen),
          if (promised is num) ...[
            const SizedBox(height: 8),
            liveText(
              l10n.picksTrustPromised(percentText(promised, 1)),
              size: 11,
              color: liveMuted,
            ),
          ],
        ],
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
    borderRadius: BorderRadius.circular(3),
    child: Stack(
      children: [
        Container(height: 6, color: const Color(0xff243447)),
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
    return Semantics(
      container: true,
      button: true,
      label:
          '${pick['local']} · ${pick['visitante']}. ${pickText(pick)}. ${l10n.pickProbability(realPercent(prob))}. @$price',
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        decoration: BoxDecoration(
          color: livePanel,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: best
                ? liveGreen.withValues(alpha: .55)
                : Colors.white.withValues(alpha: .08),
          ),
        ),
        child: Material(
          type: MaterialType.transparency,
          child: InkWell(
            borderRadius: BorderRadius.circular(16),
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
                          child: liveText(
                            meta,
                            size: 11,
                            color: liveMuted,
                          ),
                        ),
                        if (best) ...[
                          _Chip(l10n.picksBestProb, liveGreen),
                          const SizedBox(width: 6),
                        ],
                        _Chip(
                          free ? l10n.forecastFree : l10n.forecastUnlocked,
                          free ? liveGreen : liveCyan,
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Text.rich(
                      TextSpan(
                        children: [
                          TextSpan(text: '${pick['local'] ?? ''}'),
                          const TextSpan(
                            text: '  vs  ',
                            style: TextStyle(color: liveMuted, fontSize: 12),
                          ),
                          TextSpan(text: '${pick['visitante'] ?? ''}'),
                        ],
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: Colors.white,
                        fontFamily: 'Gilroy Bold',
                        fontSize: 16,
                        height: 1.2,
                      ),
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Flexible(
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 10,
                              vertical: 6,
                            ),
                            decoration: BoxDecoration(
                              color: liveGreen.withValues(alpha: .14),
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                const Icon(
                                  Icons.check_circle_outline,
                                  size: 16,
                                  color: liveGreen,
                                ),
                                const SizedBox(width: 6),
                                Flexible(
                                  child: Text(
                                    pickText(pick),
                                    maxLines: 2,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(
                                      color: liveGreen,
                                      fontFamily: 'Gilroy Bold',
                                      fontSize: 13,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 10,
                            vertical: 6,
                          ),
                          decoration: BoxDecoration(
                            color: liveGold.withValues(alpha: .15),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Text(
                            '@$price',
                            style: const TextStyle(
                              color: liveGold,
                              fontFamily: 'Gilroy Bold',
                              fontSize: 15,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: _Meter(
                            value: prob is num ? prob.toDouble() : 0,
                            color: liveGreen,
                          ),
                        ),
                        const SizedBox(width: 10),
                        liveText(realPercent(prob), size: 13, bold: true),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Expanded(
                          child: liveText(
                            l10n.pickOddsAtPublish(
                              pick['ref_book'] ??
                                  pick['book'] ??
                                  l10n.pickSourceNA,
                            ),
                            size: 11,
                            color: liveMuted,
                          ),
                        ),
                        liveText(
                          '${l10n.picksSeeAnalysis} ›',
                          size: 12,
                          color: liveCyan,
                          bold: true,
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
      color: color.withValues(alpha: .15),
      borderRadius: BorderRadius.circular(99),
    ),
    child: Text(
      label,
      style: TextStyle(color: color, fontFamily: 'Gilroy Bold', fontSize: 10),
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
    return Container(
      key: const ValueKey('high-locked-group'),
      margin: const EdgeInsets.only(top: 6, bottom: 12),
      decoration: BoxDecoration(
        color: const Color(0xff0f1a28),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: liveGold.withValues(alpha: .4)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.lock_outline, color: liveGold, size: 26),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      liveText(
                        l10n.picksLockedTitle(widget.picks.length),
                        bold: true,
                        size: 15,
                      ),
                      const SizedBox(height: 2),
                      liveText(l10n.picksLockedHint, size: 12, color: liveMuted),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            liveButton(l10n.vipAccessButton, widget.onVip),
            InkWell(
              key: const ValueKey('high-locked-toggle'),
              borderRadius: BorderRadius.circular(10),
              onTap: () => setState(() => _open = !_open),
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Row(
                  children: [
                    Expanded(
                      child: liveText(
                        _open ? l10n.picksLockedHide : l10n.picksLockedShow,
                        size: 13,
                        bold: true,
                        color: liveCyan,
                      ),
                    ),
                    Icon(
                      _open ? Icons.expand_less : Icons.expand_more,
                      color: liveCyan,
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
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.lock_outline, size: 16, color: liveMuted),
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
                                fontFamily: 'Gilroy Bold',
                                fontSize: 13,
                              ),
                            ),
                            liveText(
                              [
                                ?leagueName(p['league_id']),
                                if (_kickoff(p) != null)
                                  time.format(_kickoff(p)!),
                              ].join(' · '),
                              size: 11,
                              color: liveMuted,
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
                            foregroundColor: liveCyan,
                            side: const BorderSide(color: liveCyan),
                            padding: const EdgeInsets.symmetric(
                              horizontal: 10,
                              vertical: 4,
                            ),
                            minimumSize: const Size(0, 36),
                          ),
                          onPressed: () => widget.onUnlock!(p),
                          child: Text(
                            l10n.picksCoinsShort(widget.unlockCost ?? '—'),
                            style: const TextStyle(fontSize: 12),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
          ],
        ),
      ),
    );
  }
}
