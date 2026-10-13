import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../l10n/app_locale.dart';
import 'alerts_model.dart';
import 'live_api.dart';
import 'live_widgets.dart';

const _tile = Color(0xff0e1b2a);
const _red = Color(0xffe85667);

/// Contenido de «Datos del partido»: último resultado de cada equipo, último once conocido (con
/// su fecha, nunca una predicción) y el resumen de bajas. Todo sale de datos guardados; lo que
/// falta se dice.
class MatchFacts extends StatefulWidget {
  const MatchFacts({
    super.key,
    required this.ficha,
    required this.api,
    this.onAlerts,
  });

  final JsonMap ficha;
  final QuantFutApi api;

  /// Abre la pestaña de alertas.
  final VoidCallback? onAlerts;

  @override
  State<MatchFacts> createState() => _MatchFactsState();
}

class _MatchFactsState extends State<MatchFacts> {
  final _open = <String>{};

  /// Partido más reciente del equipo y, si es distinto, el más reciente de esta competición.
  static List<(String, JsonMap)> lastResults(
    AppLocalizations l10n,
    JsonMap team,
    String competition,
  ) {
    final matches = jsonRows(jsonMap(team['forma'])['partidos']);
    if (matches.isEmpty) return const [];
    final out = <(String, JsonMap)>[(l10n.factsLastMatch, matches.first)];
    final same = matches.skip(1).where((m) => m['competicion'] == competition);
    if (competition.isNotEmpty &&
        matches.first['competicion'] != competition &&
        same.isNotEmpty) {
      out.add((l10n.factsInCompetition(competition), same.first));
    }
    return out;
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final competition =
        '${jsonMap(jsonMap(widget.ficha['partido'])['liga'])['nombre'] ?? ''}';
    final alerts = MatchAlerts.fromFicha(widget.ficha);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(Icons.fact_check_outlined, size: 16, color: liveCyan),
            const SizedBox(width: 8),
            liveText(l10n.factsTitle.toUpperCase(), size: 12, bold: true, color: liveCyan),
          ],
        ),
        for (final side in ['local', 'visitante']) ...[
          const SizedBox(height: 14),
          _TeamFacts(
            key: ValueKey('facts-$side'),
            team: jsonMap(widget.ficha[side]),
            api: widget.api,
            results: lastResults(l10n, jsonMap(widget.ficha[side]), competition),
            lineupOpen: _open.contains(side),
            onToggleLineup: () => setState(
              () => _open.contains(side) ? _open.remove(side) : _open.add(side),
            ),
          ),
        ],
        if (alerts != null) ...[
          const SizedBox(height: 14),
          InkWell(
            key: const ValueKey('facts-alerts'),
            borderRadius: BorderRadius.circular(12),
            onTap: widget.onAlerts,
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: _tile,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                children: [
                  const Icon(Icons.healing, size: 18, color: _red),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        liveText(l10n.factsAbsences, size: 12, bold: true),
                        const SizedBox(height: 2),
                        for (final side in ['home', 'away'])
                          liveText(
                            '${jsonMap(widget.ficha[side == 'home' ? 'local' : 'visitante'])['nombre']}: ${l10n.alertsSummary(alerts.confirmedCount(side), alerts.doubtCount(side))}',
                            size: 11,
                            color: liveMuted,
                          ),
                      ],
                    ),
                  ),
                  if (widget.onAlerts != null)
                    liveText('${l10n.factsSeeAlerts} ›', size: 12, bold: true, color: liveCyan),
                ],
              ),
            ),
          ),
        ],
      ],
    );
  }
}

class _TeamFacts extends StatelessWidget {
  const _TeamFacts({
    super.key,
    required this.team,
    required this.api,
    required this.results,
    required this.lineupOpen,
    required this.onToggleLineup,
  });

  final JsonMap team;
  final QuantFutApi api;
  final List<(String, JsonMap)> results;
  final bool lineupOpen;
  final VoidCallback onToggleLineup;

  static String _date(dynamic value) {
    final d = dateValue(value)?.toLocal();
    return d == null ? '' : localDate(DateFormat.MMMd, d);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final once = jsonMap(team['ultimo_once']);
    final starters = jsonRows(once['titulares']);
    const order = {'G': 0, 'D': 1, 'M': 2, 'F': 3};
    final sorted = [...starters]
      ..sort(
        (a, b) => (order[a['pos']] ?? 9).compareTo(order[b['pos']] ?? 9),
      );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            TeamCrest(team: team, api: api, size: 26),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                '${team['nombre'] ?? ''}',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: Colors.white,
                  fontFamily: 'Gilroy Bold',
                  fontSize: 15,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        if (results.isEmpty)
          liveText(l10n.factsNoResult, size: 12, color: liveMuted)
        else
          for (final (label, m) in results) _ResultRow(label: label, match: m, date: _date(m['fecha'])),
        const SizedBox(height: 6),
        if (starters.isEmpty)
          liveText(l10n.factsNoLineup, size: 12, color: liveMuted)
        else
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: _tile,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: liveText(l10n.factsLastLineup, size: 11, color: liveMuted),
                    ),
                    if ('${once['formacion'] ?? ''}'.isNotEmpty)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: liveCyan.withValues(alpha: .15),
                          borderRadius: BorderRadius.circular(99),
                        ),
                        child: Text(
                          '${once['formacion']}',
                          style: const TextStyle(
                            color: liveCyan,
                            fontFamily: 'Gilroy Bold',
                            fontSize: 12,
                          ),
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 2),
                liveText(
                  l10n.factsLineupMeta('${once['rival'] ?? ''}', _date(once['fecha'])),
                  size: 11,
                  color: liveMuted,
                ),
                InkWell(
                  key: ValueKey('facts-lineup-toggle-${team['id']}'),
                  borderRadius: BorderRadius.circular(8),
                  onTap: onToggleLineup,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    child: Row(
                      children: [
                        Expanded(
                          child: liveText(
                            lineupOpen ? l10n.factsHideLineup : l10n.factsShowLineup,
                            size: 12,
                            bold: true,
                            color: liveCyan,
                          ),
                        ),
                        Icon(lineupOpen ? Icons.expand_less : Icons.expand_more, color: liveCyan, size: 20),
                      ],
                    ),
                  ),
                ),
                if (lineupOpen) ...[
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: [
                      for (final p in sorted)
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: .06),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Text(
                            '${p['numero'] != null ? '${p['numero']} ' : ''}${p['nombre']}',
                            style: const TextStyle(color: Colors.white, fontSize: 12),
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  liveText(l10n.factsLineupNote, size: 11, color: liveMuted),
                ],
              ],
            ),
          ),
      ],
    );
  }
}

class _ResultRow extends StatelessWidget {
  const _ResultRow({required this.label, required this.match, required this.date});

  final String label;
  final JsonMap match;
  final String date;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final res = match['res'];
    final (text, color) = switch (res) {
      'G' => (l10n.factsWon, liveGreen),
      'E' => (l10n.factsDrew, liveMuted),
      _ => (l10n.factsLost, _red),
    };
    final score = '${match['gf']}-${match['gc']}';
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            margin: const EdgeInsets.only(top: 2),
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              color: color.withValues(alpha: .16),
              borderRadius: BorderRadius.circular(99),
            ),
            child: Text(
              text,
              style: TextStyle(color: color, fontFamily: 'Gilroy Bold', fontSize: 11),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                liveText(
                  l10n.factsVs(score, '${match['rival'] ?? ''}'),
                  size: 13,
                  bold: true,
                ),
                liveText(
                  [
                    label,
                    // La etiqueta «En X» ya nombra la competición: no se repite.
                    if (!label.contains('${match['competicion'] ?? ''}'))
                      '${match['competicion'] ?? ''}',
                    date,
                  ].where((s) => s.isNotEmpty).join(' · '),
                  size: 11,
                  color: liveMuted,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
