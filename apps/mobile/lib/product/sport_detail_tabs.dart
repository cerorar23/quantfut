// Pestañas Análisis, H2H y Alertas de la ficha de NBA y tenis. Los datos vienen de las
// estadísticas públicas del servidor (pueden faltar: el mensaje neutro vive solo en su pestaña).
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';

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
  const SportAlerts({
    super.key,
    required this.event,
    this.availability,
    this.api,
    this.images,
  });

  final SportEvent event;
  final Future<JsonMap?>? availability;
  final QuantFutApi? api;
  final ImageCatalog? images;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    if (event.sport != kNba) {
      return SportNote(l10n.sportAlertsNone);
    }

    if (availability != null) {
      return FutureBuilder<JsonMap?>(
        future: availability,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting &&
              event.availability == null) {
            return const Padding(
              padding: EdgeInsets.symmetric(vertical: 40),
              child: Center(
                child: SizedBox(
                  width: 24,
                  height: 24,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
              ),
            );
          }
          final data = snapshot.data ?? event.availability;
          return _buildAlertsContent(context, l10n, data);
        },
      );
    }

    return _buildAlertsContent(context, l10n, event.availability);
  }

  Widget _buildAlertsContent(
    BuildContext context,
    AppLocalizations l10n,
    JsonMap? data,
  ) {
    if (data == null) {
      return SportNote(l10n.sportAlertsNone);
    }

    final hasOfficialReport = data.containsKey('local') ||
        data.containsKey('visitante') ||
        data.containsKey('teams') ||
        data.containsKey('players') ||
        data.containsKey('jugadores');

    if (hasOfficialReport) {
      return _NbaInjuriesReport(
        event: event,
        data: data,
        api: api,
        images: images,
      );
    }

    return _LegacyAlerts(event: event, a: data);
  }
}

class _NbaInjuriesReport extends StatelessWidget {
  const _NbaInjuriesReport({
    required this.event,
    required this.data,
    required this.api,
    required this.images,
  });

  final SportEvent event;
  final JsonMap data;
  final QuantFutApi? api;
  final ImageCatalog? images;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final reportUrl = (data['reporte_url'] ?? data['report_url']) as String?;
    final reportTime =
        (data['reporte_timestamp_utc'] ?? data['report_timestamp_utc'])
            as String?;
    final hasPdf = reportUrl != null && reportUrl.startsWith('https://');

    Map<String, dynamic> homeTeam;
    Map<String, dynamic> awayTeam;

    if (data['local'] is Map<String, dynamic> &&
        data['visitante'] is Map<String, dynamic>) {
      final localMap = data['local'] as Map<String, dynamic>;
      final visitMap = data['visitante'] as Map<String, dynamic>;
      final localName = localMap['nombre']?.toString() ?? '';
      final isSwapped = nbaTricode(localName) != null &&
          nbaTricode(localName) == nbaTricode(event.away);
      homeTeam = isSwapped ? visitMap : localMap;
      awayTeam = isSwapped ? localMap : visitMap;
    } else if (data['teams'] is List && (data['teams'] as List).length >= 2) {
      final list = data['teams'] as List;
      final t0 = list[0] is Map<String, dynamic>
          ? list[0] as Map<String, dynamic>
          : <String, dynamic>{};
      final t1 = list[1] is Map<String, dynamic>
          ? list[1] as Map<String, dynamic>
          : <String, dynamic>{};
      final name0 = (t0['nombre'] ?? t0['name'])?.toString() ?? '';
      final isSwapped = nbaTricode(name0) != null &&
          nbaTricode(name0) == nbaTricode(event.away);
      homeTeam = isSwapped ? t0 : t1;
      awayTeam = isSwapped ? t1 : t0;
    } else {
      homeTeam = {'nombre': event.home, 'jugadores': const []};
      awayTeam = {'nombre': event.away, 'jugadores': const []};
    }

    final awayName = awayTeam['nombre']?.toString() ?? event.away;
    final homeName = homeTeam['nombre']?.toString() ?? event.home;

    final mb = data['metricas_bajas'] is Map<String, dynamic>
        ? data['metricas_bajas'] as Map<String, dynamic>
        : (data['missing_points_home'] != null ? data : null);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        QfCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              qfTitle(l10n.nbaInjuriesTitle, size: 14),
              const SizedBox(height: 4),
              Text(
                l10n.nbaInjuriesSub,
                style: const TextStyle(fontSize: 12, color: QfColors.text2),
              ),
              if (reportTime != null || hasPdf) const SizedBox(height: 10),
              if (reportTime != null)
                Text(
                  l10n.detailChecked(kickoffText(reportTime)),
                  style: const TextStyle(fontSize: 11, color: QfColors.muted),
                ),
              if (hasPdf) ...[
                const SizedBox(height: 8),
                Align(
                  alignment: Alignment.centerLeft,
                  child: InkWell(
                    onTap: () {
                      final uri = Uri.tryParse(reportUrl);
                      if (uri != null) {
                        launchUrl(uri, mode: LaunchMode.externalApplication);
                      }
                    },
                    borderRadius: BorderRadius.circular(6),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 6,
                      ),
                      decoration: BoxDecoration(
                        color: QfColors.surface2,
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: QfColors.border),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(
                            Icons.picture_as_pdf_outlined,
                            size: 14,
                            color: QfColors.cyan,
                          ),
                          const SizedBox(width: 6),
                          Flexible(
                            child: Text(
                              l10n.nbaInjuriesPdfLink,
                              style: const TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                                color: QfColors.cyan,
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          const SizedBox(width: 4),
                          const Icon(
                            Icons.open_in_new,
                            size: 12,
                            color: QfColors.cyan,
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
        const SizedBox(height: 10),
        _TeamInjuryCard(
          teamName: awayName,
          roleLabel: l10n.commonAway,
          teamData: awayTeam,
          api: api,
          images: images,
        ),
        const SizedBox(height: 10),
        _TeamInjuryCard(
          teamName: homeName,
          roleLabel: l10n.commonHome,
          teamData: homeTeam,
          api: api,
          images: images,
        ),
        if (mb != null) ...[
          const SizedBox(height: 10),
          QfCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                qfTitle(l10n.nbaInjuriesImpactTitle, size: 13),
                const SizedBox(height: 8),
                if (mb['missing_points_home'] != null)
                  _StatLine(
                    l10n.nbaInjuriesImpactPoints(event.home),
                    _formatStatNum(mb['missing_points_home']),
                  ),
                if (mb['missing_points_away'] != null)
                  _StatLine(
                    l10n.nbaInjuriesImpactPoints(event.away),
                    _formatStatNum(mb['missing_points_away']),
                  ),
                if (mb['missing_minutes_home'] != null)
                  _StatLine(
                    l10n.nbaInjuriesImpactMinutes(event.home),
                    _formatStatNum(mb['missing_minutes_home']),
                  ),
                if (mb['missing_minutes_away'] != null)
                  _StatLine(
                    l10n.nbaInjuriesImpactMinutes(event.away),
                    _formatStatNum(mb['missing_minutes_away']),
                  ),
              ],
            ),
          ),
        ],
      ],
    );
  }
}

String _formatStatNum(dynamic v) {
  if (v is num) {
    return decimalText(v, v is int || v == v.roundToDouble() ? 0 : 1);
  }
  return '$v';
}

class _TeamInjuryCard extends StatelessWidget {
  const _TeamInjuryCard({
    required this.teamName,
    required this.roleLabel,
    required this.teamData,
    required this.api,
    required this.images,
  });

  final String teamName;
  final String roleLabel;
  final Map<String, dynamic> teamData;
  final QuantFutApi? api;
  final ImageCatalog? images;

  Widget _teamAvatar(String name, {double size = 28}) {
    final code = nbaTricode(name);
    final path = code == null
        ? null
        : (images?.nbaLogo(code) ??
            '/web/imagenes/nba/${code.toUpperCase()}.png');
    final resolved = api != null ? serverImageUrl(api!, path) : null;
    return QfAvatar(
      url: resolved,
      name: name,
      size: size,
      shape: AvatarShape.contain,
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final reporteNoEnviado = teamData['reporte_no_enviado'] == true;
    final rawPlayers = teamData['jugadores'] ?? teamData['players'];
    final players = [
      if (rawPlayers is List)
        for (final p in rawPlayers)
          if (p is Map<String, dynamic>) p,
    ];

    final bajasCount = players.where(_isBaja).length;
    final dudasCount = players.length - bajasCount;

    Widget badgeWidget;
    if (reporteNoEnviado) {
      badgeWidget = QfBadge(
        l10n.sportAvailPending,
        color: QfColors.yellow,
        icon: Icons.schedule,
      );
    } else if (players.isEmpty) {
      badgeWidget = QfBadge(
        l10n.nbaInjuriesFullRoster,
        color: QfColors.success,
        icon: Icons.check_circle_outline,
      );
    } else {
      final String label;
      if (bajasCount > 0 && dudasCount > 0) {
        label = l10n.nbaInjuriesBadgeBajasDudas(bajasCount, dudasCount);
      } else if (bajasCount > 0) {
        label = l10n.nbaInjuriesBadgeBajasOnly(bajasCount);
      } else {
        label = l10n.nbaInjuriesBadgeDudasOnly(dudasCount);
      }
      badgeWidget = QfBadge(
        label,
        color: bajasCount > 0 ? QfColors.danger : QfColors.yellow,
        icon: bajasCount > 0 ? Icons.error_outline : Icons.warning_amber_rounded,
      );
    }

    return QfCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              _teamAvatar(teamName, size: 28),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      teamName,
                      style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 14,
                        color: QfColors.text,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    Text(
                      roleLabel,
                      style: const TextStyle(
                        fontSize: 11,
                        color: QfColors.text2,
                      ),
                    ),
                  ],
                ),
              ),
              badgeWidget,
            ],
          ),
          if (reporteNoEnviado) ...[
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Row(
                children: [
                  const Icon(
                    Icons.warning_amber_rounded,
                    size: 16,
                    color: QfColors.danger,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      l10n.nbaInjuriesNotYetSubmitted,
                      style:
                          const TextStyle(fontSize: 13, color: QfColors.text2),
                    ),
                  ),
                ],
              ),
            ),
          ] else if (players.isEmpty) ...[
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Row(
                children: [
                  const Icon(
                    Icons.check_circle_outline,
                    size: 16,
                    color: QfColors.success,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      l10n.nbaInjuriesClean,
                      style:
                          const TextStyle(fontSize: 13, color: QfColors.text2),
                    ),
                  ),
                ],
              ),
            ),
          ] else ...[
            Padding(
              padding: const EdgeInsets.only(top: 10),
              child: Column(
                children: [
                  for (var i = 0; i < players.length; i++) ...[
                    if (i > 0)
                      const Divider(
                        height: 12,
                        thickness: 0.5,
                        color: QfColors.border,
                      ),
                    _InjuryPlayerRow(
                      player: players[i],
                      api: api,
                    ),
                  ],
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _InjuryPlayerRow extends StatelessWidget {
  const _InjuryPlayerRow({
    required this.player,
    required this.api,
  });

  final Map<String, dynamic> player;
  final QuantFutApi? api;

  String? _playerPhoto() {
    final nbaId = player['nba_id'] ?? player['nbaId'];
    if (nbaId != null && '$nbaId'.isNotEmpty && '$nbaId' != '0') {
      return 'https://cdn.nba.com/headshots/nba/latest/260x190/$nbaId.png';
    }
    final pid = player['id'] ?? player['playerId'];
    if (pid != null && '$pid'.isNotEmpty && api != null) {
      return serverImageUrl(api!, nbaPlayerPhoto('$pid'));
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final name =
        player['nombre']?.toString() ?? player['name']?.toString() ?? '?';
    final estado =
        player['estado']?.toString() ?? player['status']?.toString();
    final motivo =
        player['motivo']?.toString() ?? player['reason']?.toString();
    final statusInfo = _statusInfo(l10n, estado, motivo);
    final shortName = _formatPlayerShort(name);
    final reason = _traducirMotivo(motivo);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          QfAvatar(
            url: _playerPhoto(),
            name: name,
            size: 36,
            shape: AvatarShape.circle,
            ring: statusInfo.color,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        shortName,
                        style: const TextStyle(
                          fontWeight: FontWeight.w700,
                          fontSize: 13,
                          color: QfColors.text,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 6,
                        vertical: 2,
                      ),
                      decoration: BoxDecoration(
                        color: statusInfo.color.withValues(alpha: .12),
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(
                          color: statusInfo.color.withValues(alpha: .35),
                          width: 0.5,
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            '+ ',
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w900,
                              color: statusInfo.color,
                            ),
                          ),
                          Text(
                            statusInfo.label,
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                              color: statusInfo.color,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 2),
                Text(
                  reason.isNotEmpty
                      ? reason
                      : (motivo ?? l10n.nbaInjuriesNoReason),
                  style: const TextStyle(
                    fontSize: 11,
                    color: QfColors.text2,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _StatusLook {
  const _StatusLook(this.label, this.color);
  final String label;
  final Color color;
}

_StatusLook _statusInfo(
  AppLocalizations l10n,
  String? estado,
  String? motivo,
) {
  final e = (estado ?? '').trim().toLowerCase();
  final m = (motivo ?? '').toLowerCase();
  if (m.contains('suspension')) {
    return _StatusLook(l10n.nbaInjuryStatusSuspended, QfColors.magenta);
  }
  return switch (e) {
    'out' => _StatusLook(l10n.nbaInjuryStatusOut, QfColors.danger),
    'doubtful' =>
      _StatusLook(l10n.nbaInjuryStatusDoubtful, const Color(0xfff59e0b)),
    'questionable' =>
      _StatusLook(l10n.nbaInjuryStatusQuestionable, QfColors.yellow),
    'probable' => _StatusLook(l10n.nbaInjuryStatusProbable, QfColors.success),
    'available' => _StatusLook(l10n.nbaInjuryStatusAvailable, QfColors.cyan),
    _ => _StatusLook(
        estado != null && estado.isNotEmpty
            ? estado
            : l10n.nbaInjuryStatusOut,
        QfColors.danger,
      ),
  };
}

bool _isBaja(Map<String, dynamic> player) {
  final motivo = (player['motivo'] ?? player['reason'] ?? '')
      .toString()
      .toLowerCase();
  if (motivo.contains('suspension')) return true;
  final estado = (player['estado'] ?? player['status'] ?? '')
      .toString()
      .toLowerCase();
  return estado == 'out' || estado == 'suspended' || estado == 'baja';
}

String _formatPlayerShort(String name) {
  final n = name.trim();
  if (n.isEmpty) return n;
  if (n.contains(',')) {
    final parts = n.split(',').map((s) => s.trim()).toList();
    if (parts.length >= 2 && parts[1].isNotEmpty) {
      return '${parts[1][0]}. ${parts[0]}';
    }
  }
  final parts = n.split(RegExp(r'\s+'));
  if (parts.length > 1) {
    return '${parts[0][0]}. ${parts.sublist(1).join(' ')}';
  }
  return n;
}

// l10n-ignore-start
String _traducirParte(String txt) {
  var res = txt
      .replaceAll(RegExp(r'left\s+ankle', caseSensitive: false), 'tobillo izq.')
      .replaceAll(RegExp(r'right\s+ankle', caseSensitive: false), 'tobillo der.')
      .replaceAll(RegExp(r'bilateral\s+ankle', caseSensitive: false), 'tobillo bilateral')
      .replaceAll(RegExp(r'left\s+knee', caseSensitive: false), 'rodilla izq.')
      .replaceAll(RegExp(r'right\s+knee', caseSensitive: false), 'rodilla der.')
      .replaceAll(RegExp(r'bilateral\s+knee', caseSensitive: false), 'rodilla bilateral')
      .replaceAll(RegExp(r'left\s+foot', caseSensitive: false), 'pie izq.')
      .replaceAll(RegExp(r'right\s+foot', caseSensitive: false), 'pie der.')
      .replaceAll(RegExp(r'left\s+heel', caseSensitive: false), 'talón izq.')
      .replaceAll(RegExp(r'right\s+heel', caseSensitive: false), 'talón der.')
      .replaceAll(RegExp(r'left\s+hamstring', caseSensitive: false), 'isquiotibiales izq.')
      .replaceAll(RegExp(r'right\s+hamstring', caseSensitive: false), 'isquiotibiales der.')
      .replaceAll(RegExp(r'left\s+quad(?:riceps)?', caseSensitive: false), 'cuádriceps izq.')
      .replaceAll(RegExp(r'right\s+quad(?:riceps)?', caseSensitive: false), 'cuádriceps der.')
      .replaceAll(RegExp(r'left\s+calf', caseSensitive: false), 'pantorrilla izq.')
      .replaceAll(RegExp(r'right\s+calf', caseSensitive: false), 'pantorrilla der.')
      .replaceAll(RegExp(r'left\s+groin', caseSensitive: false), 'ingle izq.')
      .replaceAll(RegExp(r'right\s+groin', caseSensitive: false), 'ingle der.')
      .replaceAll(RegExp(r'left\s+hip', caseSensitive: false), 'cadera izq.')
      .replaceAll(RegExp(r'right\s+hip', caseSensitive: false), 'cadera der.')
      .replaceAll(RegExp(r'left\s+shoulder', caseSensitive: false), 'hombro izq.')
      .replaceAll(RegExp(r'right\s+shoulder', caseSensitive: false), 'hombro der.')
      .replaceAll(RegExp(r'left\s+wrist', caseSensitive: false), 'muñeca izq.')
      .replaceAll(RegExp(r'right\s+wrist', caseSensitive: false), 'muñeca der.')
      .replaceAll(RegExp(r'left\s+thumb', caseSensitive: false), 'pulgar izq.')
      .replaceAll(RegExp(r'right\s+thumb', caseSensitive: false), 'pulgar der.')
      .replaceAll(RegExp(r'left\s+hand', caseSensitive: false), 'mano izq.')
      .replaceAll(RegExp(r'right\s+hand', caseSensitive: false), 'mano der.')
      .replaceAll(RegExp(r'left\s+elbow', caseSensitive: false), 'codo izq.')
      .replaceAll(RegExp(r'right\s+elbow', caseSensitive: false), 'codo der.')
      .replaceAll(RegExp(r'left\s+eye', caseSensitive: false), 'ojo izq.')
      .replaceAll(RegExp(r'right\s+eye', caseSensitive: false), 'ojo der.')
      .replaceAll(RegExp(r'lower\s+back', caseSensitive: false), 'espalda baja')
      .replaceAll(RegExp(r'mid\s+back', caseSensitive: false), 'espalda media')
      .replaceAll(RegExp(r'upper\s+back', caseSensitive: false), 'espalda alta');

  const dic = [
    [r'left', 'izq.'], [r'right', 'der.'], [r'bilateral', 'bilateral'],
    [r'ankle', 'tobillo'], [r'knee', 'rodilla'], [r'foot', 'pie'],
    [r'heel', 'talón'], [r'hamstring', 'isquiotibiales'], [r'quad', 'cuádriceps'],
    [r'calf', 'pantorrilla'], [r'groin', 'ingle'], [r'hip', 'cadera'],
    [r'back', 'espalda'], [r'shoulder', 'hombro'], [r'wrist', 'muñeca'],
    [r'thumb', 'pulgar'], [r'finger', 'dedo'], [r'hand', 'mano'],
    [r'elbow', 'codo'], [r'neck', 'cuello'], [r'eye', 'ojo'],
    [r'sprain', 'esguince'], [r'strain', 'distensión'], [r'soreness', 'molestias'],
    [r'contusion', 'contusión'], [r'fracture', 'fractura'], [r'surgery', 'cirugía'],
    [r'tear', 'desgarro'], [r'inflammation', 'inflamación'], [r'tightness', 'sobrecarga'],
    [r'illness', 'enfermedad'], [r'recovery', 'recuperación'],
    [r'injury\s+management', 'gestión de carga'], [r'rest', 'descanso'],
  ];

  for (final pair in dic) {
    res = res.replaceAll(RegExp(pair[0], caseSensitive: false), pair[1]);
  }
  res = res.replaceAll(RegExp(r';\s*'), ' · ').trim();
  return res.isNotEmpty ? '${res[0].toUpperCase()}${res.substring(1)}' : '';
}

String _traducirMotivo(String? raw) {
  if (raw == null || raw.trim().isEmpty) return '';
  final txt = raw.trim();
  if (RegExp(r'suspension', caseSensitive: false).hasMatch(txt)) {
    if (RegExp(r'league\s+suspension', caseSensitive: false).hasMatch(txt)) {
      return 'Suspensión de la liga';
    }
    if (RegExp(r'team\s+suspension', caseSensitive: false).hasMatch(txt)) {
      return 'Suspensión del equipo';
    }
    return 'Suspensión disciplinaria';
  }
  if (RegExp(r'g\s*league', caseSensitive: false).hasMatch(txt)) {
    if (RegExp(r'two-way', caseSensitive: false).hasMatch(txt)) {
      return 'Contrato Two-Way (G League)';
    }
    if (RegExp(r'assignment', caseSensitive: false).hasMatch(txt)) {
      return 'Asignado a G League';
    }
    return 'G League';
  }
  if (RegExp(r'health\s+and\s+safety', caseSensitive: false).hasMatch(txt)) {
    return 'Protocolos de salud y seguridad';
  }
  if (RegExp(r'personal\s+reasons', caseSensitive: false).hasMatch(txt)) {
    return 'Motivos personales';
  }
  if (RegExp(r'not\s+with\s+team', caseSensitive: false).hasMatch(txt)) {
    return 'No está con el equipo';
  }
  if (RegExp(r'^Injury/Illness\s*-\s*Rest$', caseSensitive: false)
          .hasMatch(txt) ||
      RegExp(r'^Rest$', caseSensitive: false).hasMatch(txt)) {
    return 'Descanso programado';
  }
  final clean = txt.replaceFirst(
    RegExp(r'^Injury/Illness\s*-\s*', caseSensitive: false),
    '',
  );
  return _traducirParte(clean);
}
// l10n-ignore-end

class _LegacyAlerts extends StatelessWidget {
  const _LegacyAlerts({required this.event, required this.a});
  final SportEvent event;
  final JsonMap a;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
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
