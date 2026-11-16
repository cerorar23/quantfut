import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../l10n/app_locale.dart';
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
    if (e.sport == kTennis) {
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

/// Tira de 5 días CyberCore: contador por día del deporte elegido; HOY resaltado.
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
      for (var i = 0; i < 5; i++)
        DateTime(first.year, first.month, first.day + i),
    ];
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 6, 8, 8),
      decoration: const BoxDecoration(
        color: QfColors.bg,
        border: Border(bottom: BorderSide(color: QfColors.divider)),
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
                    color: QfColors.text,
                    fontFamily: qfDisplay,
                    fontWeight: FontWeight.w700,
                    fontSize: 14,
                    letterSpacing: 0.5,
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
                  color: searching ? QfColors.green : QfColors.muted,
                ),
              ),
              IconButton(
                key: const ValueKey('day-picker'),
                tooltip: l10n.calendarPickDate,
                visualDensity: VisualDensity.compact,
                onPressed: onPick,
                icon: const Icon(Icons.calendar_month, color: QfColors.cyan),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Row(
            children: [
              for (var i = 0; i < days.length; i++) ...[
                if (i > 0) const SizedBox(width: 6),
                Expanded(
                  child: _DayTile(
                    key: ValueKey('day-${dateKey(days[i])}'),
                    date: days[i],
                    active: dateKey(days[i]) == active,
                    today: dateKey(days[i]) == dateKey(now),
                    yesterday: dateKey(days[i]) == dateKey(DateTime(now.year, now.month, now.day - 1)),
                    matches: counts[dateKey(days[i])] ?? 0,
                    onTap: () => onDay(days[i]),
                  ),
                ),
              ],
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
    this.yesterday = false,
    required this.matches,
    required this.onTap,
  });

  final DateTime date;
  final bool active, today, yesterday;
  final int matches;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final dayLabel = today
        ? l10n.homeToday.toUpperCase()
        : yesterday
        ? l10n.commonYesterday.toUpperCase()
        : toBeginningOfSentenceCase(localDate(DateFormat.E, date)).toUpperCase();
    final text = '$dayLabel ${date.day}';

    return Semantics(
      button: true,
      selected: active,
      label: '$text, $matches',
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          child: Container(
            height: 44,
            decoration: BoxDecoration(
              color: active
                  ? QfColors.cyan.withValues(alpha: .1)
                  : Colors.transparent,
              border: Border.all(
                color: active
                    ? QfColors.cyan
                    : today
                        ? QfColors.cyan.withValues(alpha: .5)
                        : QfColors.divider,
                width: 1,
              ),
            ),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                FittedBox(
                  fit: BoxFit.scaleDown,
                  child: Text(
                    text,
                    style: TextStyle(
                      fontFamily: qfMono,
                      fontWeight: active ? FontWeight.w700 : FontWeight.w500,
                      fontSize: 11,
                      color: active
                          ? QfColors.cyan
                          : today
                              ? QfColors.cyan.withValues(alpha: .85)
                              : QfColors.muted,
                    ),
                  ),
                ),
                if (matches > 0) ...[
                  const SizedBox(height: 2),
                  Text(
                    '$matches',
                    style: TextStyle(
                      fontFamily: qfMono,
                      fontSize: 9,
                      fontWeight: active ? FontWeight.w700 : FontWeight.w500,
                      color: active ? QfColors.cyan : QfColors.text2,
                    ),
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
            width: 3,
            height: 16,
            color: QfColors.cyan,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              dayLabel(l10n, day.day, DateTime.now()),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: QfColors.text,
                fontFamily: qfDisplay,
                fontWeight: FontWeight.w700,
                fontSize: 14,
                letterSpacing: 1.0,
              ),
            ),
          ),
          Text(
            l10n.calendarMatchesCount(day.matches.length),
            style: const TextStyle(
              fontFamily: qfMono,
              fontSize: 11,
              color: QfColors.text2,
            ),
          ),
        ],
      ),
    );
  }
}

/// Fila de un partido: hora, equipos con escudos solapados de 30 dp, liga,
/// y a la derecha % verde / candado VIP / «desde HH:MM».
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
    final finished = match['marcador'] is List;

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Material(
        color: QfColors.surface,
        shape: const CutCornerBorder(cut: 8, side: BorderSide(color: QfColors.border)),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onOpen,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  children: [
                    // Columna 1: Hora en Mono 12
                    SizedBox(
                      width: 48,
                      child: Text(
                        ko == null ? '—' : localDate(DateFormat.Hm, ko),
                        style: const TextStyle(
                          color: QfColors.muted,
                          fontFamily: qfMono,
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),

                    // Columna 2: Escudos solapados 30 dp + Nombres + Liga
                    Expanded(
                      child: Row(
                        children: [
                          SizedBox(
                            width: 30,
                            height: 30,
                            child: TeamCrest(team: local, api: api, size: 30),
                          ),
                          Transform.translate(
                            offset: const Offset(-6, 0),
                            child: SizedBox(
                              width: 30,
                              height: 30,
                              child: TeamCrest(team: away, api: api, size: 30),
                            ),
                          ),
                          const SizedBox(width: 4),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Text(
                                  '${local['nombre'] ?? ''} – ${away['nombre'] ?? ''}',
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(
                                    color: QfColors.text,
                                    fontFamily: 'Exo 2', fontWeight: FontWeight.w700,
                                    fontSize: 13,
                                  ),
                                ),
                                if (league.isNotEmpty)
                                  Text(
                                    league,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(
                                      color: QfColors.text2,
                                      fontSize: 11,
                                    ),
                                  ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),

                    const SizedBox(width: 8),

                    // Columna 3: Insignia a la derecha
                    if (finished)
                      Text(
                        (match['marcador'] as List).join(' – '),
                        style: const TextStyle(
                          fontFamily: qfMono,
                          fontSize: 13,
                          color: QfColors.text2,
                        ),
                      )
                    else if (pending)
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.lock_clock,
                            size: 14,
                            color: QfColors.yellow,
                            semanticLabel: l10n.homeForecastPending,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            'desde ${localDate(DateFormat.Hm, unlock)}',
                            style: const TextStyle(
                              fontFamily: qfMono,
                              fontSize: 11,
                              color: QfColors.text2,
                            ),
                          ),
                        ],
                      )
                    else if (public.isNotEmpty)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          border: Border.all(color: QfColors.green.withValues(alpha: .4)),
                          color: QfColors.green.withValues(alpha: .09),
                        ),
                        child: Text(
                          realPercent(public.first['prob']),
                          style: const TextStyle(
                            fontFamily: qfMono,
                            fontWeight: FontWeight.w700,
                            fontSize: 12,
                            color: QfColors.green,
                          ),
                        ),
                      )
                    else if (picks.isNotEmpty)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          border: Border.all(color: QfColors.yellow.withValues(alpha: .4)),
                          color: QfColors.yellow.withValues(alpha: .08),
                        ),
                        child: const Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.lock, size: 12, color: QfColors.yellow),
                            SizedBox(width: 4),
                            Text(
                              'VIP',
                              style: TextStyle(
                                fontFamily: qfMono,
                                fontWeight: FontWeight.w700,
                                fontSize: 12,
                                color: QfColors.yellow,
                              ),
                            ),
                          ],
                        ),
                      )
                    else if (top != null)
                      _Likely(
                        label: switch (top.$1) {
                          'home' => l10n.probBarHome,
                          'draw' => l10n.probBarDraw,
                          _ => l10n.probBarAway,
                        },
                        value: top.$2,
                        probabilities: probabilities,
                      )
                    else
                      const SizedBox.shrink(),
                  ],
                ),
                if (pending) ...[
                  const SizedBox(height: 6),
                  _PickTag(
                    text: l10n.homeForecastAt(
                      '${localDate(DateFormat.MMMEd, unlock)}, ${localDate(DateFormat.Hm, unlock)}',
                      localDate(
                        DateFormat.Hm,
                        unlock.toUtc().subtract(const Duration(hours: 6)),
                      ),
                    ),
                    color: QfColors.yellow,
                    icon: Icons.lock_clock,
                  ),
                ] else if (match['marcador'] is List) ...[
                  Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: liveText(
                      l10n.resultLabel((match['marcador'] as List).join(' – ')),
                      color: QfColors.muted,
                      size: 12,
                    ),
                  ),
                ] else if (match['estado'] != 'finished' &&
                    awaitingResult(match['kickoff_utc'])) ...[
                  Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: liveText(
                      l10n.matchAwaitingResult,
                      color: QfColors.muted,
                      size: 12,
                    ),
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
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
    decoration: BoxDecoration(
      border: Border.all(color: QfColors.green.withValues(alpha: .4)),
      color: QfColors.green.withValues(alpha: .09),
    ),
    child: Text(
      '$label ${realPercent(value)}',
      maxLines: 1,
      style: const TextStyle(
        color: QfColors.green,
        fontFamily: qfMono,
        fontWeight: FontWeight.w700,
        fontSize: 12,
      ),
    ),
  );
}

class _PickTag extends StatelessWidget {
  const _PickTag({required this.text, required this.color, required this.icon});

  final String text;
  final Color color;
  final IconData icon;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
    decoration: ShapeDecoration(
      color: color.withValues(alpha: .1),
      shape: CutCornerBorder(
        cut: 6,
        side: BorderSide(color: color.withValues(alpha: .3)),
      ),
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
