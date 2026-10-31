import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../l10n/app_locale.dart';
import '../l10n/pick_labels.dart';
import 'live_api.dart';
import 'live_widgets.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';
import 'sports.dart';
import 'sports_feed.dart';

/// Partidos de un mismo día local, en orden cronológico.
class AgendaDay {
  const AgendaDay(this.day, this.matches);

  final DateTime day;
  final List<JsonMap> matches;

  String get key => dateKey(day);
}

/// Agrupa por día local y ordena por hora de inicio. Los partidos sin hora válida no se muestran.
List<AgendaDay> groupAgenda(Iterable<JsonMap> rows) {
  final dated = <(DateTime, JsonMap)>[
    for (final m in rows)
      if (dateValue(m['kickoff_utc'])?.toLocal() case final ko?) (ko, m),
  ]..sort((a, b) => a.$1.compareTo(b.$1));
  final days = <AgendaDay>[];
  for (final (ko, match) in dated) {
    final day = DateTime(ko.year, ko.month, ko.day);
    if (days.isNotEmpty && days.last.key == dateKey(day)) {
      days.last.matches.add(match);
    } else {
      days.add(AgendaDay(day, [match]));
    }
  }
  return days;
}

/// Grupo de la agenda de NBA (`hour`, hora local en punto) o de tenis (`tournament`).
class SportAgendaGroup {
  SportAgendaGroup({this.hour, this.tournament});

  final DateTime? hour;
  final String? tournament;
  final events = <SportEvent>[];
}

/// Eventos de NBA o tenis de un mismo día local.
class SportAgendaDay {
  SportAgendaDay(this.day);

  final DateTime day;
  final groups = <SportAgendaGroup>[];

  String get key => dateKey(day);
  int get count => groups.fold(0, (n, g) => n + g.events.length);
}

/// Agrupa por día LOCAL (como `groupAgenda`): NBA por hora y tenis por torneo, en orden
/// cronológico. El feed de tenis no trae ronda, así que no se agrupa por ella. `toLocal`
/// solo se cambia en pruebas, para fijar una zona horaria distinta de la de la máquina.
List<SportAgendaDay> groupSportAgenda(
  Iterable<SportEvent> events, {
  DateTime Function(DateTime utc) toLocal = _deviceLocal,
}) {
  final sorted = [...events]..sort((a, b) => a.start.compareTo(b.start));
  final days = <SportAgendaDay>[];
  for (final e in sorted) {
    final t = toLocal(e.start);
    final day = DateTime(t.year, t.month, t.day);
    if (days.isEmpty || days.last.key != dateKey(day)) {
      days.add(SportAgendaDay(day));
    }
    final groups = days.last.groups;
    SportAgendaGroup? group;
    if (e.sport == SportKind.tennis) {
      for (final g in groups) {
        if (g.tournament == e.league) group = g;
      }
      if (group == null) groups.add(group = SportAgendaGroup(tournament: e.league));
    } else {
      final hour = DateTime(t.year, t.month, t.day, t.hour);
      group = groups.isNotEmpty && groups.last.hour == hour ? groups.last : null;
      if (group == null) groups.add(group = SportAgendaGroup(hour: hour));
    }
    group.events.add(e);
  }
  return days;
}

DateTime _deviceLocal(DateTime d) => d.toLocal();

/// «Hoy · jue, 15 oct», «Mañana · vie, 16 oct» o solo la fecha.
String dayLabel(AppLocalizations l10n, DateTime day, DateTime now) {
  final date = toBeginningOfSentenceCase(localDate(DateFormat.MMMEd, day));
  final today = DateTime(now.year, now.month, now.day);
  final diff = DateTime(day.year, day.month, day.day).difference(today).inDays;
  return switch (diff) {
    0 => '${l10n.homeToday} · $date',
    1 => '${l10n.homeTomorrow} · $date',
    _ => date,
  };
}

/// Tira de siete días con el mes y el botón de calendario completo. Los días con partidos
/// llevan un punto; el activo va relleno.
class DayStrip extends StatelessWidget {
  const DayStrip({
    super.key,
    required this.start,
    required this.active,
    required this.counts,
    required this.onDay,
    required this.onPick,
    required this.onSearch,
    this.searching = false,
  });

  final DateTime start;
  final String active;
  final Map<String, int> counts;
  final ValueChanged<DateTime> onDay;
  final VoidCallback onPick, onSearch;
  final bool searching;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final now = DateTime.now();
    final first = DateTime(start.year, start.month, start.day);
    final days = [
      for (var i = 0; i < 7; i++)
        DateTime(first.year, first.month, first.day + i),
    ];
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 6, 8, 8),
      decoration: const BoxDecoration(
        color: liveBg,
        border: Border(bottom: BorderSide(color: Color(0xff1a2a3b))),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              const SizedBox(width: 4),
              Expanded(
                child: Text(
                  toBeginningOfSentenceCase(
                        localDate(DateFormat.yMMMM, days[days.length ~/ 2]),
                      ) ??
                      '',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Colors.white,
                    fontFamily: 'Gilroy Bold',
                    fontSize: 15,
                  ),
                ),
              ),
              IconButton(
                key: const ValueKey('day-search'),
                tooltip: l10n.calendarSearchHint,
                visualDensity: VisualDensity.compact,
                onPressed: onSearch,
                icon: Icon(
                  searching ? Icons.search_off : Icons.search,
                  color: searching ? liveGreen : liveMuted,
                ),
              ),
              IconButton(
                key: const ValueKey('day-picker'),
                tooltip: l10n.calendarPickDate,
                visualDensity: VisualDensity.compact,
                onPressed: onPick,
                icon: const Icon(Icons.calendar_month, color: liveCyan),
              ),
            ],
          ),
          Row(
            children: [
              for (final date in days)
                Expanded(
                  child: _DayTile(
                    key: ValueKey('day-${dateKey(date)}'),
                    date: date,
                    active: dateKey(date) == active,
                    today: dateKey(date) == dateKey(now),
                    matches: counts[dateKey(date)] ?? 0,
                    onTap: () => onDay(date),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _DayTile extends StatelessWidget {
  const _DayTile({
    super.key,
    required this.date,
    required this.active,
    required this.today,
    required this.matches,
    required this.onTap,
  });

  final DateTime date;
  final bool active, today;
  final int matches;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final label = toBeginningOfSentenceCase(localDate(DateFormat.E, date));
    return Semantics(
      button: true,
      selected: active,
      label: '$label ${date.day}',
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          margin: const EdgeInsets.symmetric(horizontal: 2),
          padding: const EdgeInsets.symmetric(vertical: 8),
          decoration: BoxDecoration(
            color: active ? liveGreen : Colors.transparent,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: active
                  ? liveGreen
                  : today
                  ? liveCyan.withValues(alpha: .6)
                  : Colors.transparent,
            ),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.clip,
                style: TextStyle(
                  fontSize: 11,
                  color: active ? liveBg : liveMuted,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                '${date.day}',
                style: TextStyle(
                  fontFamily: 'Gilroy ExtraBold',
                  fontSize: 18,
                  color: active ? liveBg : Colors.white,
                ),
              ),
              const SizedBox(height: 4),
              Container(
                width: 5,
                height: 5,
                decoration: BoxDecoration(
                  color: matches == 0
                      ? Colors.transparent
                      : active
                      ? liveBg
                      : liveGreen,
                  shape: BoxShape.circle,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Encabezado de un día con su número de partidos.
class DayHeader extends StatelessWidget {
  const DayHeader({super.key, required this.day});

  final AgendaDay day;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 18, 16, 10),
      child: Row(
        children: [
          Container(
            width: 4,
            height: 18,
            decoration: BoxDecoration(
              color: liveGreen,
              borderRadius: BorderRadius.circular(4),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              dayLabel(l10n, day.day, DateTime.now()),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: Colors.white,
                fontFamily: 'Gilroy ExtraBold',
                fontSize: 16,
              ),
            ),
          ),
          liveText(
            l10n.calendarMatchesCount(day.matches.length),
            size: 12,
            color: liveMuted,
          ),
        ],
      ),
    );
  }
}

/// Fila de un partido: hora, equipos, resultado más probable y, si lo hay, el pronóstico.
class MatchRow extends StatelessWidget {
  const MatchRow({
    super.key,
    required this.match,
    required this.api,
    required this.picks,
    required this.onOpen,
  });

  final JsonMap match;
  final QuantFutApi api;
  final List<JsonMap> picks;
  final VoidCallback onOpen;

  /// Resultado 1X2 más probable, o `null` si no hay probabilidades.
  static (String, double)? best(JsonMap probabilities) {
    String? key;
    var top = -1.0;
    for (final k in const ['home', 'draw', 'away']) {
      final v = probabilities[k];
      if (v is num && v.isFinite && v > top) {
        top = v.toDouble();
        key = k;
      }
    }
    return key == null ? null : (key, top);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final local = jsonMap(match['local']), away = jsonMap(match['visitante']);
    final ko = dateValue(match['kickoff_utc'])?.toLocal();
    final probabilities = jsonMap(match['probabilities']);
    final top = best(probabilities);
    final unlock = dateValue(match['pronostico_desde'])?.toLocal();
    // Aún sin calcular: el servidor lo calcula el mismo día, a las 03:00 de México.
    final pending =
        top == null && unlock != null && unlock.isAfter(DateTime.now());
    final public = picks.where((p) => p['locked'] != true).toList();
    final league = '${jsonMap(match['liga'])['nombre'] ?? ''}';
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Material(
        color: livePanel,
        shape: const CutCornerBorder(side: BorderSide(color: QfColors.border)),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onOpen,
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        league,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: liveMuted, fontSize: 11),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    SizedBox(
                      width: 54,
                      child: Text(
                        ko == null ? '—' : localDate(DateFormat.Hm, ko),
                        style: const TextStyle(
                          color: Colors.white,
                          fontFamily: 'Gilroy ExtraBold',
                          fontSize: 16,
                        ),
                      ),
                    ),
                    Expanded(
                      child: Column(
                        children: [
                          for (final team in [local, away])
                            Padding(
                              padding: const EdgeInsets.symmetric(vertical: 4),
                              child: Row(
                                children: [
                                  TeamCrest(team: team, api: api, size: 32),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Text(
                                      '${team['nombre'] ?? ''}',
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(
                                        color: Colors.white,
                                        fontFamily: 'Gilroy Bold',
                                        fontSize: 13,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 10),
                    SizedBox(
                      width: 84,
                      child: pending
                          ? Align(
                              alignment: Alignment.centerRight,
                              child: Icon(
                                Icons.lock_clock,
                                semanticLabel: l10n.homeForecastPending,
                                color: liveGold,
                              ),
                            )
                          : top == null
                          ? const SizedBox.shrink()
                          : _Likely(
                              label: switch (top.$1) {
                                'home' => l10n.probBarHome,
                                'draw' => l10n.probBarDraw,
                                _ => l10n.probBarAway,
                              },
                              value: top.$2,
                              probabilities: probabilities,
                            ),
                    ),
                    const Icon(Icons.chevron_right, color: liveMuted, size: 20),
                  ],
                ),
                if (match['marcador'] is List)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: liveText(
                      l10n.resultLabel((match['marcador'] as List).join(' – ')),
                      color: liveMuted,
                      size: 12,
                    ),
                  )
                else if (match['estado'] != 'finished' &&
                    awaitingResult(match['kickoff_utc']))
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: liveText(
                      l10n.matchAwaitingResult,
                      color: liveMuted,
                      size: 12,
                    ),
                  ),
                if (pending) ...[
                  const SizedBox(height: 8),
                  _PickTag(
                    text: l10n.homeForecastAt(
                      '${localDate(DateFormat.MMMEd, unlock)}, ${localDate(DateFormat.Hm, unlock)}',
                      // México es UTC-6 todo el año; la hora sale del propio dato del servidor.
                      localDate(
                        DateFormat.Hm,
                        unlock.toUtc().subtract(const Duration(hours: 6)),
                      ),
                    ),
                    color: liveGold,
                    icon: Icons.lock_clock,
                  ),
                ] else if (public.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  _PickTag(
                    text:
                        '${pickText(public.first, home: local['nombre'], away: away['nombre'])} @ ${decimalText(public.first['ref_price'] ?? public.first['price'])}',
                    color: liveGreen,
                    icon: Icons.verified_outlined,
                  ),
                ] else if (picks.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  _PickTag(
                    text: l10n.vipPickLabel,
                    color: liveGold,
                    icon: Icons.lock_outline,
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Likely extends StatelessWidget {
  const _Likely({
    required this.label,
    required this.value,
    required this.probabilities,
  });

  final String label;
  final double value;
  final JsonMap probabilities;

  @override
  Widget build(BuildContext context) {
    int flex(String k) {
      final v = probabilities[k];
      return v is num && v.isFinite ? (v * 100).round().clamp(1, 100) : 1;
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
          decoration: BoxDecoration(
            color: liveGreen.withValues(alpha: .15),
            borderRadius: BorderRadius.circular(8),
          ),
          child: FittedBox(
            fit: BoxFit.scaleDown,
            child: Text(
              '$label ${realPercent(value)}',
              maxLines: 1,
              style: const TextStyle(
                color: liveGreen,
                fontFamily: 'Gilroy Bold',
                fontSize: 12,
              ),
            ),
          ),
        ),
        const SizedBox(height: 6),
        ClipRRect(
          borderRadius: BorderRadius.circular(3),
          child: Row(
            children: [
              Expanded(
                flex: flex('home'),
                child: Container(height: 4, color: liveGreen),
              ),
              Expanded(
                flex: flex('draw'),
                child: Container(height: 4, color: liveMuted),
              ),
              Expanded(
                flex: flex('away'),
                child: Container(height: 4, color: liveCyan),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _PickTag extends StatelessWidget {
  const _PickTag({required this.text, required this.color, required this.icon});

  final String text;
  final Color color;
  final IconData icon;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
    decoration: BoxDecoration(
      color: color.withValues(alpha: .1),
      borderRadius: BorderRadius.circular(10),
    ),
    child: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 14, color: color),
        const SizedBox(width: 6),
        Flexible(
          child: Text(
            text,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(color: color, fontSize: 12),
          ),
        ),
      ],
    ),
  );
}
