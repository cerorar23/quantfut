// Pestañas Análisis, H2H y Alertas de la ficha de NBA y tenis. Los datos vienen de las
// estadísticas públicas del servidor (pueden faltar: el mensaje neutro vive solo en su pestaña).
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../l10n/app_locale.dart';
import 'live_api.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';
import 'sports.dart';
import 'sports_feed.dart';

// ---- Análisis, H2H y Alertas -----------------------------------------------------------

class SportNote extends StatelessWidget {
  const SportNote(this.text, {super.key});
  final String text;
  @override
  Widget build(BuildContext context) => QfCard(
    child: Row(
      children: [
        const Icon(Icons.info_outline, color: QfColors.text2, size: 18),
        const SizedBox(width: 10),
        Expanded(
          child: Text(text, style: const TextStyle(color: QfColors.text2)),
        ),
      ],
    ),
  );
}

/// Espera las estadísticas; sin ellas, el mensaje neutro vive solo en esta pestaña.
class _StatsGate extends StatelessWidget {
  const _StatsGate({
    required this.stats,
    required this.empty,
    required this.builder,
  });
  final Future<JsonMap?> stats;
  final String Function(AppLocalizations) empty;
  final Widget Function(JsonMap data) builder;
  @override
  Widget build(BuildContext context) => FutureBuilder<JsonMap?>(
    future: stats,
    builder: (context, snap) {
      if (snap.connectionState != ConnectionState.done) {
        return const Center(
          child: Padding(
            padding: EdgeInsets.all(24),
            child: CircularProgressIndicator(),
          ),
        );
      }
      final data = snap.data;
      return data == null ? SportNote(empty(context.l10n)) : builder(data);
    },
  );
}

class _StatLine extends StatelessWidget {
  const _StatLine(this.label, this.value);
  final String label, value;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 3),
    child: Row(
      children: [
        Expanded(
          child: Text(
            label,
            style: const TextStyle(fontSize: 13, color: QfColors.text2),
          ),
        ),
        Text(
          value,
          style: const TextStyle(
            fontFamily: qfMono,
            fontSize: 13,
            color: QfColors.text,
          ),
        ),
      ],
    ),
  );
}

String? _record(dynamic r) => r is Map && r['won'] is num && r['lost'] is num
    ? '${(r['won'] as num).toInt()}-${(r['lost'] as num).toInt()}'
    : null;

String? _number(dynamic v, [int digits = 1]) =>
    v is num && v.isFinite ? decimalText(v, digits) : null;

String? _signed(dynamic v) =>
    v is num && v != 0 ? '${v > 0 ? '+' : ''}${v.toInt()}' : null;

class SportAnalysis extends StatelessWidget {
  const SportAnalysis({super.key, required this.stats, required this.event});
  final Future<JsonMap?> stats;
  final SportEvent event;

  List<Widget> nbaTeam(AppLocalizations l10n, JsonMap t) {
    final scoring = jsonMap(t['scoring']);
    final standing = jsonMap(t['standing']);
    final rows = <(String, String?)>[
      (l10n.sportStatSeason, _record(t['season'])),
      (l10n.sportStatHome, _record(t['home'])),
      (l10n.sportStatAway, _record(t['away'])),
      (l10n.sportStatLast6, _record(t['last6'])),
      (l10n.sportStatPointsFor, _number(scoring['points_for'])),
      (l10n.sportStatPointsAgainst, _number(scoring['points_against'])),
      (l10n.sportStatStreak, _signed(t['streak'])),
      (
        l10n.sportStatRest,
        t['rest_days'] is num ? '${(t['rest_days'] as num).toInt()}' : null,
      ),
      (
        l10n.sportStatStanding,
        standing['rank'] is num && standing['of'] is num
            ? '${standing['rank']} / ${standing['of']}'
            : null,
      ),
    ];
    return [
      for (final (label, value) in rows)
        if (value != null) _StatLine(label, value),
      if (t['back_to_back'] == true) ...[
        const SizedBox(height: 6),
        Align(
          alignment: Alignment.centerLeft,
          child: QfBadge(
            l10n.sportStatBackToBack,
            color: QfColors.text2,
            icon: Icons.event_repeat,
          ),
        ),
      ],
    ];
  }

  List<Widget> tennisPlayer(AppLocalizations l10n, JsonMap p) {
    final surfaces = jsonMap(p['surfaces']);
    final key = (event.surface ?? '').trim().toLowerCase();
    final form = p['form'] is Map ? jsonMap(p['form']) : <String, dynamic>{};
    final rows = <(String, String?)>[
      (l10n.sportStatRank, p['rank'] != null ? '${p['rank']}' : null),
      (
        l10n.sportStatAge,
        p['age'] is num ? '${(p['age'] as num).toInt()}' : null,
      ),
      (l10n.sportStatSeason, _record(p['season'])),
      (l10n.sportStatCareer, _record(p['career'])),
      (l10n.sportStatSurface, _record(jsonMap(surfaces[key])['career'])),
      (
        l10n.sportStatFormIndex,
        form['index'] is num ? '${(form['index'] as num).toInt()}' : null,
      ),
      (l10n.sportStatStreak, _signed(form['streak'])),
    ];
    return [
      for (final (label, value) in rows)
        if (value != null) _StatLine(label, value),
    ];
  }

  @override
  Widget build(BuildContext context) => _StatsGate(
    stats: stats,
    empty: (l) => l.sportStatsUnavailable,
    builder: (data) {
      final l10n = context.l10n;
      final nba = event.sport == SportKind.nba;
      final items = jsonRows(data[nba ? 'teams' : 'players']);
      if (items.isEmpty) return SportNote(l10n.sportStatsUnavailable);
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          for (final t in items)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: QfCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      '${t['name'] ?? ''}',
                      style: const TextStyle(
                        fontFamily: qfDisplay,
                        fontWeight: FontWeight.w700,
                        fontSize: 16,
                        color: QfColors.text,
                      ),
                    ),
                    const SizedBox(height: 6),
                    ...(nba ? nbaTeam(l10n, t) : tennisPlayer(l10n, t)),
                  ],
                ),
              ),
            ),
        ],
      );
    },
  );
}

class SportH2h extends StatelessWidget {
  const SportH2h({super.key, required this.stats, required this.event});
  final Future<JsonMap?> stats;
  final SportEvent event;

  String _date(dynamic v) {
    final d = dateValue(v);
    return d == null ? '' : localDate(DateFormat.yMd, d);
  }

  Widget row(String date, String text) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 4),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 84,
          child: Text(
            date,
            style: const TextStyle(
              fontFamily: qfMono,
              fontSize: 11,
              color: QfColors.muted,
            ),
          ),
        ),
        Expanded(
          child: Text(
            text,
            style: const TextStyle(fontSize: 13, color: QfColors.text),
          ),
        ),
      ],
    ),
  );

  Widget nba(AppLocalizations l10n, JsonMap h2h) {
    final matches = jsonRows(h2h['matches']);
    var homeWins = 0, awayWins = 0;
    for (final m in matches) {
      final hp = m['home_points'], ap = m['away_points'];
      if (hp is! num || ap is! num || hp == ap) continue;
      final winner = hp > ap ? m['home'] : m['away'];
      if (winner == event.home) homeWins++;
      if (winner == event.away) awayWins++;
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (homeWins + awayWins > 0)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Text(
              l10n.sportH2hRecord(event.home, event.away, homeWins, awayWins),
              style: const TextStyle(
                fontFamily: qfDisplay,
                fontWeight: FontWeight.w700,
                fontSize: 16,
                color: QfColors.text,
              ),
            ),
          ),
        for (final m in matches)
          row(
            _date(m['date']),
            '${m['home']} ${m['home_points']} · ${m['away']} ${m['away_points']}',
          ),
      ],
    );
  }

  Widget tennis(AppLocalizations l10n, JsonMap data, JsonMap h2h) {
    final players = jsonRows(data['players']);
    final first = players.isNotEmpty ? '${players[0]['name']}' : event.home;
    final second = players.length > 1 ? '${players[1]['name']}' : event.away;
    final fw = h2h['first_wins'], sw = h2h['second_wins'];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (fw is num && sw is num)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Text(
              l10n.sportH2hRecord(first, second, fw.toInt(), sw.toInt()),
              style: const TextStyle(
                fontFamily: qfDisplay,
                fontWeight: FontWeight.w700,
                fontSize: 16,
                color: QfColors.text,
              ),
            ),
          ),
        for (final m in jsonRows(h2h['matches']))
          row(
            _date(m['date']),
            '${m['tournament'] ?? ''} · ${m['won'] == true ? first : second}'
            '${m['score'] != null ? ' ${m['score']}' : ''}',
          ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) => _StatsGate(
    stats: stats,
    empty: (l) => l.detailNoH2h,
    builder: (data) {
      final l10n = context.l10n;
      final h2h = jsonMap(data['h2h']);
      if (jsonRows(h2h['matches']).isEmpty) return SportNote(l10n.detailNoH2h);
      return QfCard(
        child: event.sport == SportKind.nba
            ? nba(l10n, h2h)
            : tennis(l10n, data, h2h),
      );
    },
  );
}

class SportAlerts extends StatelessWidget {
  const SportAlerts({super.key, required this.event});
  final SportEvent event;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final a = event.availability;
    // Tenis: las estadísticas no traen avisos; NBA sin reporte tampoco.
    if (event.sport != SportKind.nba || a == null) {
      return SportNote(l10n.sportAlertsNone);
    }
    final applied = a['state'] == 'reporte_aplicado';
    final missingHome = _number(a['missing_minutes_home'], 0);
    final missingAway = _number(a['missing_minutes_away'], 0);
    final notSent = [
      for (final t
          in (a['teams_not_submitted'] is List
              ? a['teams_not_submitted'] as List
              : const []))
        '$t',
    ];
    final listed = a['listed'];
    return QfCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Align(
            alignment: Alignment.centerLeft,
            child: applied
                ? QfBadge(
                    l10n.sportAvailApplied,
                    color: QfColors.success,
                    icon: Icons.check_circle_outline,
                  )
                : QfBadge(
                    l10n.sportAvailPending,
                    color: QfColors.text2,
                    icon: Icons.schedule,
                  ),
          ),
          const SizedBox(height: 10),
          if (listed is num)
            Text(
              l10n.sportAvailListed(listed.toInt()),
              style: const TextStyle(color: QfColors.text),
            ),
          if (missingHome != null)
            Text(
              l10n.sportAvailMissingMinutes(event.home, missingHome),
              style: const TextStyle(fontSize: 13, color: QfColors.text2),
            ),
          if (missingAway != null)
            Text(
              l10n.sportAvailMissingMinutes(event.away, missingAway),
              style: const TextStyle(fontSize: 13, color: QfColors.text2),
            ),
          for (final team in notSent) ...[
            const SizedBox(height: 6),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(
                  Icons.warning_amber_rounded,
                  size: 16,
                  color: QfColors.danger,
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    l10n.sportAvailNotSubmitted(team),
                    style: const TextStyle(fontSize: 13, color: QfColors.text),
                  ),
                ),
              ],
            ),
          ],
          if (a['report_timestamp_utc'] != null) ...[
            const SizedBox(height: 8),
            Text(
              l10n.detailChecked(kickoffText(a['report_timestamp_utc'])),
              style: const TextStyle(fontSize: 11, color: QfColors.muted),
            ),
          ],
        ],
      ),
    );
  }
}
