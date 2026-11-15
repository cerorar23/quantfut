// Pestañas Análisis, H2H y Alertas de la ficha de NBA y tenis. Los datos vienen de las
// estadísticas públicas del servidor (pueden faltar: el mensaje neutro vive solo en su pestaña).
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../l10n/app_locale.dart';
import 'analysis_nba.dart';
import 'analysis_tennis.dart';
import 'live_api.dart';
import 'live_widgets.dart' show valueBars;
import 'qf_h2h_view.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';
import 'sport_contract.dart';
import 'sport_images.dart';
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

/// Bloque de contenido de un partido de un deporte del catálogo sin pantalla propia (`partido.bloques`). Cada tipo usa
/// una pieza que ya existe: `tabla` → filas en columnas con el estilo de [_StatLine]; `barras` → [valueBars] (la fila
/// de `probabilityBars`); `pares` → [_StatLine]; `texto` → [SportNote]. Todo es texto plano.
class SportContentBlock extends StatelessWidget {
  const SportContentBlock(this.block, {super.key});
  final ContentBlock block;

  @override
  Widget build(BuildContext context) {
    final b = block;
    if (b is TextBlock) {
      return Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: QfCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [_title(b.title), Text(b.body, style: const TextStyle(color: QfColors.text2))],
          ),
        ),
      );
    }
    final Widget body = switch (b) {
      TableBlock() => _table(b),
      BarsBlock() => valueBars(b.items),
      PairsBlock() => Column(children: [for (final i in b.items) _StatLine(i.label, i.value)]),
      TextBlock() => const SizedBox.shrink(),
    };
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: QfCard(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [_title(b.title), body]),
      ),
    );
  }

  static Widget _title(String text) => Padding(
    padding: const EdgeInsets.only(bottom: 8),
    child: Text(
      text,
      style: const TextStyle(
        fontFamily: qfDisplay,
        fontWeight: FontWeight.w700,
        fontSize: 13,
        letterSpacing: .8,
        color: QfColors.text,
      ),
    ),
  );

  static Widget _table(TableBlock t) {
    final columns = t.columns.length;
    Widget cell(String text, {bool head = false, bool first = false}) => Padding(
      padding: const EdgeInsets.symmetric(vertical: 4, horizontal: 2),
      child: Text(
        text,
        textAlign: first ? TextAlign.start : TextAlign.end,
        style: TextStyle(
          fontFamily: head || first ? null : qfMono,
          fontSize: 12,
          fontWeight: head ? FontWeight.bold : FontWeight.normal,
          color: head ? QfColors.text2 : QfColors.text,
        ),
      ),
    );
    return Table(
      defaultColumnWidth: const FlexColumnWidth(),
      columnWidths: columns > 1 ? {0: const FlexColumnWidth(2)} : null,
      children: [
        TableRow(children: [for (final (i, c) in t.columns.indexed) cell(c, head: true, first: i == 0)]),
        for (final r in t.rows) TableRow(children: [for (final (i, c) in r.indexed) cell(c, first: i == 0)]),
      ],
    );
  }
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

String? _number(dynamic v, [int digits = 1]) =>
    v is num && v.isFinite ? decimalText(v, digits) : null;

class SportAnalysis extends StatelessWidget {
  const SportAnalysis({
    super.key,
    required this.stats,
    required this.event,
    this.api,
    this.images,
    this.onH2h,
  });

  final Future<JsonMap?> stats;
  final SportEvent event;
  final QuantFutApi? api;
  final ImageCatalog? images;
  final VoidCallback? onH2h;

  @override
  Widget build(BuildContext context) => _StatsGate(
    stats: stats,
    empty: (l) => l.sportStatsUnavailable,
    builder: (data) {
      final l10n = context.l10n;
      final nba = event.sport == kNba;
      if (nba) {
        return NbaAnalysis(
          event: event,
          data: data,
          api: api,
          images: images,
          onH2h: onH2h,
        );
      }
      final tennis = event.sport == kTennis;
      if (tennis) {
        return TennisAnalysis(
          event: event,
          data: data,
          api: api,
          images: images,
          onH2h: onH2h,
        );
      }
      final items = jsonRows(data['players']);
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
  const SportH2h({
    super.key,
    required this.stats,
    required this.event,
    this.api,
    this.images,
  });

  final Future<JsonMap?> stats;
  final SportEvent event;
  final QuantFutApi? api;
  final ImageCatalog? images;

  String _date(dynamic v, BuildContext context) {
    if (v == null || v == '' || v == '—') return '—';
    final d = dateValue(v);
    if (d == null) return '$v';
    final locale = Localizations.localeOf(context).languageCode;
    return DateFormat.yMMM(locale).format(d).toLowerCase();
  }

  Widget nba(BuildContext context, AppLocalizations l10n, JsonMap h2h) {
    final matches = jsonRows(h2h['matches']);
    var homeWins = (h2h['home_wins'] as num?)?.toInt() ?? 0;
    var awayWins = (h2h['away_wins'] as num?)?.toInt() ?? 0;
    if (homeWins == 0 && awayWins == 0) {
      for (final m in matches) {
        final hp = m['home_points'], ap = m['away_points'];
        if (hp is! num || ap is! num || hp == ap) continue;
        final winner = hp > ap ? m['home'] : m['away'];
        if (winner == event.home) homeWins++;
        if (winner == event.away) awayWins++;
      }
    }

    if (matches.isEmpty && homeWins + awayWins == 0) {
      return SportNote(l10n.detailNoH2h);
    }

    final homeCode = nbaTricode(event.home);
    final awayCode = nbaTricode(event.away);
    final homePath = homeCode == null
        ? null
        : (images?.nbaLogo(homeCode) ??
            '/web/imagenes/nba/${homeCode.toUpperCase()}.png');
    final awayPath = awayCode == null
        ? null
        : (images?.nbaLogo(awayCode) ??
            '/web/imagenes/nba/${awayCode.toUpperCase()}.png');
    final homeUrl = api != null && homePath != null
        ? serverImageUrl(api!, homePath)
        : null;
    final awayUrl = api != null && awayPath != null
        ? serverImageUrl(api!, awayPath)
        : null;

    final matchItems = <QfH2hMatchItem>[];
    for (final m in matches) {
      final mHome = '${m['home'] ?? ''}';
      final mAway = '${m['away'] ?? ''}';
      final hp = m['home_points'];
      final ap = m['away_points'];
      final text = '$mHome $hp · $mAway $ap';
      final isHomeWinner = (hp is num && ap is num) ? hp > ap : false;
      final winnerTeam = isHomeWinner ? mHome : mAway;
      final winnerCode = nbaTricode(winnerTeam);
      final winnerPath = winnerCode == null
          ? null
          : (images?.nbaLogo(winnerCode) ??
              '/web/imagenes/nba/${winnerCode.toUpperCase()}.png');
      final winnerUrl = api != null && winnerPath != null
          ? serverImageUrl(api!, winnerPath)
          : null;
      final badge = winnerCode ??
          (winnerTeam.length > 3
              ? winnerTeam.substring(0, 3).toUpperCase()
              : winnerTeam.toUpperCase());

      final mHomeCode = nbaTricode(mHome);
      final mAwayCode = nbaTricode(mAway);
      final mHomeUrl = api != null && mHomeCode != null
          ? serverImageUrl(
              api!,
              images?.nbaLogo(mHomeCode) ??
                  '/web/imagenes/nba/${mHomeCode.toUpperCase()}.png',
            )
          : null;
      final mAwayUrl = api != null && mAwayCode != null
          ? serverImageUrl(
              api!,
              images?.nbaLogo(mAwayCode) ??
                  '/web/imagenes/nba/${mAwayCode.toUpperCase()}.png',
            )
          : null;

      matchItems.add(
        QfH2hMatchItem(
          date: _date(m['date'], context),
          text: text,
          winnerBadge: badge,
          winnerImageUrl: winnerUrl,
          winnerName: winnerTeam,
          isCircle: false,
          leftImageUrl: mHomeUrl,
          leftName: mHome,
          rightImageUrl: mAwayUrl,
          rightName: mAway,
        ),
      );
    }

    final stackedParts = <(String, double, Color)>[];
    if (homeWins + awayWins > 0) {
      stackedParts.add((homeCode ?? event.home, homeWins.toDouble(), QfColors.cyan));
      stackedParts.add((awayCode ?? event.away, awayWins.toDouble(), QfColors.chrome));
    }

    return QfH2hView(
      summary: [
        QfH2hSummaryItem(
          label: homeCode ?? event.home,
          count: homeWins,
          imageUrl: homeUrl,
          isCircle: false,
        ),
        QfH2hSummaryItem(
          label: awayCode ?? event.away,
          count: awayWins,
          imageUrl: awayUrl,
          isCircle: false,
        ),
      ],
      stackedBarParts: stackedParts,
      matches: matchItems,
    );
  }

  Widget tennis(
    BuildContext context,
    AppLocalizations l10n,
    JsonMap data,
    JsonMap h2h,
  ) {
    final players = jsonRows(data['players']);
    final first = event.home.trim().isNotEmpty
        ? event.home.trim()
        : (players.isNotEmpty ? '${players[0]['name']}' : '');
    final second = event.away.trim().isNotEmpty
        ? event.away.trim()
        : (players.length > 1 ? '${players[1]['name']}' : '');
    final fw = h2h['first_wins'];
    final sw = h2h['second_wins'];
    final firstWins = (fw as num?)?.toInt() ?? 0;
    final secondWins = (sw as num?)?.toInt() ?? 0;
    final matches = jsonRows(h2h['matches']);

    String surname(String fullName) {
      final parts = fullName.trim().split(RegExp(r'\s+'));
      return parts.isNotEmpty ? parts.last : fullName;
    }

    final firstShort = surname(first);
    final secondShort = surname(second);

    final photo1 = images?.tennisPhoto(first);
    final photo2 = images?.tennisPhoto(second);
    final photo1Url = photo1 != null && api != null
        ? serverImageUrl(api!, photo1.path)
        : null;
    final photo2Url = photo2 != null && api != null
        ? serverImageUrl(api!, photo2.path)
        : null;

    // Estado «primer duelo» (tenis 0–0 y sin partidos)
    if (firstWins == 0 && secondWins == 0 && matches.isEmpty) {
      return QfH2hView(
        summary: [
          QfH2hSummaryItem(
            label: firstShort,
            count: 0,
            imageUrl: photo1Url,
            isCircle: true,
          ),
          QfH2hSummaryItem(
            label: secondShort,
            count: 0,
            imageUrl: photo2Url,
            isCircle: true,
          ),
        ],
        matches: [
          QfH2hMatchItem(
            date: '—',
            text: l10n.h2hFirstDuelRow,
            winnerBadge: '0–0',
            winnerImageUrl: photo1Url,
            winnerName: first,
            isCircle: true,
          ),
        ],
      );
    }

    // Partidos registrados
    final matchItems = <QfH2hMatchItem>[];
    for (final m in matches) {
      final won = m['won'] == true;
      final winnerName = won ? first : second;
      final winnerShort = won ? firstShort : secondShort;
      final winnerUrl = won ? photo1Url : photo2Url;
      final score = m['score'] != null ? ' ${m['score']}' : '';
      final tourn = m['tournament'] != null && '${m['tournament']}'.isNotEmpty
          ? '${m['tournament']} · '
          : '';
      final text = '$tourn$winnerName$score'.trim();
      final badge = winnerShort.length > 3
          ? winnerShort.substring(0, 3).toUpperCase()
          : winnerShort.toUpperCase();
      matchItems.add(
        QfH2hMatchItem(
          date: _date(m['date'], context),
          text: text,
          winnerBadge: badge,
          winnerImageUrl: winnerUrl,
          winnerName: winnerName,
          isCircle: true,
        ),
      );
    }

    final stackedParts = <(String, double, Color)>[];
    if (firstWins + secondWins > 0) {
      stackedParts.add((firstShort, firstWins.toDouble(), QfColors.cyan));
      stackedParts.add((secondShort, secondWins.toDouble(), QfColors.chrome));
    }

    return QfH2hView(
      summary: [
        QfH2hSummaryItem(
          label: firstShort,
          count: firstWins,
          imageUrl: photo1Url,
          isCircle: true,
        ),
        QfH2hSummaryItem(
          label: secondShort,
          count: secondWins,
          imageUrl: photo2Url,
          isCircle: true,
        ),
      ],
      stackedBarParts: stackedParts,
      matches: matchItems,
    );
  }

  @override
  Widget build(BuildContext context) => _StatsGate(
    stats: stats,
    empty: (l) => l.detailNoH2h,
    builder: (data) {
      final l10n = context.l10n;
      final h2h = jsonMap(data['h2h']);
      if (event.sport == kNba) {
        return nba(context, l10n, h2h);
      } else {
        if (h2h.isEmpty && jsonRows(data['players']).isEmpty) {
          return SportNote(l10n.detailNoH2h);
        }
        return tennis(context, l10n, data, h2h);
      }
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
    if (event.sport != kNba || a == null) {
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
