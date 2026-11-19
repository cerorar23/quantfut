import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../l10n/app_locale.dart';
import '../l10n/pick_labels.dart';
import 'alerts_model.dart';
import 'live_alerts.dart';
import '../core/meta_events.dart';
import 'live_api.dart';
import 'live_forecast.dart';
import 'live_match_markets.dart';
import 'live_widgets.dart';
import 'live_statistics.dart';
import 'match_shell.dart';
import 'qf_h2h_view.dart';
import 'qf_theme.dart';
import 'sport_images.dart';

class LiveMatchDetail extends StatefulWidget {
  const LiveMatchDetail({
    super.key,
    required this.api,
    required this.id,
    required this.onVip,
    this.onUnlock,
  });
  final QuantFutApi api;
  final String id;
  final VoidCallback onVip;
  final VoidCallback? onUnlock;
  @override
  State<LiveMatchDetail> createState() => _LiveMatchDetailState();
}

class _LiveMatchDetailState extends State<LiveMatchDetail> {
  late Future<JsonMap> future = widget.api.detail(widget.id);
  int tab = 0;

  @override
  void initState() {
    super.initState();
    MetaEvents.current?.viewMatch(widget.id);
  }

  Widget results(List<JsonMap> rows) => Column(
    children: rows
        .map(
          (p) => liveCard(
            child: Row(
              children: [
                Expanded(
                  child: liveText(
                    '${kickoffText(p['fecha'])}\n${p['rival'] ?? ''}',
                    size: 12,
                    color: liveMuted,
                  ),
                ),
                liveText(
                  '${p['marcador'] ?? ''} · ${resultLetter(p['res'] ?? '')}',
                  bold: true,
                ),
              ],
            ),
          ),
        )
        .toList(),
  );

  Widget stats(JsonMap data, JsonMap ficha) => MatchStatistics(
    data: data,
    api: widget.api,
    onAlerts: () => setState(() => tab = 3),
    onH2h: () => setState(() => tab = 2),
  );

  Widget tactics(JsonMap data, JsonMap ficha) {
    if (!featureEnabled(data, 'h2h')) {
      return training(featureMessage(data, 'h2h'));
    }
    final l10n = context.l10n;
    final caraACara = jsonMap(ficha['cara_a_cara']);
    final h2h = jsonRows(caraACara['partidos']);
    final resumen = jsonMap(caraACara['resumen']);
    final lineups = jsonMap(ficha['alineaciones']);
    final injuries = jsonMap(ficha['bajas']);

    final localName = '${jsonMap(ficha['local'])['nombre'] ?? ''}';
    final awayName = '${jsonMap(ficha['visitante'])['nombre'] ?? ''}';
    final localCrest = serverImageUrl(
      widget.api,
      jsonMap(ficha['local'])['escudo'] as String?,
    );
    final awayCrest = serverImageUrl(
      widget.api,
      jsonMap(ficha['visitante'])['escudo'] as String?,
    );

    final localWins = (resumen['victorias_local'] as num?)?.toInt() ?? 0;
    final draws = (resumen['empates'] as num?)?.toInt() ?? 0;
    final awayWins = (resumen['victorias_visitante'] as num?)?.toInt() ?? 0;

    final hasH2hData = h2h.isNotEmpty || (localWins + draws + awayWins > 0);

    Widget h2hWidget;
    if (!hasH2hData) {
      h2hWidget = training(l10n.detailNoH2h);
    } else {
      final matchItems = <QfH2hMatchItem>[];
      for (final p in h2h) {
        final isHome = p['local'] == true;
        final rival = '${p['rival'] ?? awayName}';
        final rivalCrest =
            serverImageUrl(widget.api, p['rival_escudo'] as String?) ??
            awayCrest;
        final leftName = isHome ? localName : rival;
        final leftCrest = isHome ? localCrest : rivalCrest;
        final rightName = isHome ? rival : localName;
        final rightCrest = isHome ? rivalCrest : localCrest;
        final score = '${p['marcador'] ?? '${p['gf'] ?? 0}-${p['gc'] ?? 0}'}';
        final text = '$leftName $score $rightName';

        final res = '${p['res'] ?? 'E'}'.toUpperCase();
        String winnerBadge;
        String? winnerCrest;
        String? winnerName;
        if (res == 'E') {
          winnerBadge = l10n.h2hDrawBadge;
          winnerCrest = null;
          winnerName = null;
        } else if ((isHome && res == 'G') || (!isHome && res == 'P')) {
          winnerBadge = localName.length > 3
              ? localName.substring(0, 3).toUpperCase()
              : localName.toUpperCase();
          winnerCrest = localCrest;
          winnerName = localName;
        } else {
          winnerBadge = rival.length > 3
              ? rival.substring(0, 3).toUpperCase()
              : rival.toUpperCase();
          winnerCrest = rivalCrest;
          winnerName = rival;
        }

        final rawDate = p['fecha'];
        final d = dateValue(rawDate);
        final dateText = d != null
            ? DateFormat.yMMM(Localizations.localeOf(context).languageCode)
                .format(d)
                .toLowerCase()
            : (rawDate != null ? kickoffText(rawDate) : '—');

        matchItems.add(
          QfH2hMatchItem(
            date: dateText,
            text: text,
            winnerBadge: winnerBadge,
            winnerImageUrl: winnerCrest,
            winnerName: winnerName,
            isCircle: false,
            leftImageUrl: leftCrest,
            leftName: leftName,
            rightImageUrl: rightCrest,
            rightName: rightName,
          ),
        );
      }

      final stackedParts = <(String, double, Color)>[];
      if (localWins + draws + awayWins > 0) {
        stackedParts.add((localName, localWins.toDouble(), QfColors.cyan));
        stackedParts.add((
          l10n.anDrawsCount(draws),
          draws.toDouble(),
          QfColors.slate,
        ));
        stackedParts.add((awayName, awayWins.toDouble(), QfColors.chrome));
      }

      h2hWidget = QfH2hView(
        summary: [
          QfH2hSummaryItem(
            label: localName,
            count: localWins,
            imageUrl: localCrest,
            isCircle: false,
          ),
          QfH2hSummaryItem(
            label: l10n.h2hDraws,
            count: draws,
            isDraw: true,
          ),
          QfH2hSummaryItem(
            label: awayName,
            count: awayWins,
            imageUrl: awayCrest,
            isCircle: false,
          ),
        ],
        stackedBarParts: stackedParts,
        matches: matchItems,
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        h2hWidget,
        if (lineups.isEmpty) training(l10n.detailLineupsPending),
        if (injuries.isEmpty) training(l10n.detailNoInjuriesCheck),
      ],
    );
  }

  @override
  Widget build(BuildContext context) => Material(
    color: liveBg,
    child: FutureBuilder<JsonMap>(
      future: future,
      builder: (context, snapshot) {
        if (!snapshot.hasData) {
          return Column(
            children: [
              Align(
                alignment: Alignment.centerRight,
                child: IconButton(
                  onPressed: () => Navigator.pop(context),
                  icon: const Icon(Icons.close, color: QfColors.text2),
                ),
              ),
              Expanded(
                child: Center(
                  child: snapshot.hasError
                      ? Padding(
                          padding: const EdgeInsets.all(20),
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              liveText('${snapshot.error}', color: QfColors.text2),
                              liveButton(
                                context.l10n.commonRetry,
                                () => setState(
                                  () => future = widget.api.detail(widget.id),
                                ),
                                color: QfColors.primary,
                              ),
                            ],
                          ),
                        )
                      : const CircularProgressIndicator(),
                ),
              ),
            ],
          );
        }
        final data = snapshot.data!,
            ficha = jsonMap(data['ficha']),
            match = jsonMap(ficha['partido']);
        final picks = jsonRows(data['picks']);
        final l10n = context.l10n;
        // El destacado es el del servidor, el mismo de la web (titular, 2026-11-16); `null` = ninguno cumple la regla.
        // Solo si el servidor no lo manda (versión anterior) se calcula aquí con los pronósticos abiertos.
        final serverFeatured = jsonMap(ficha['mercados'])['destacado_app'];
        final featured = jsonMap(ficha['mercados']).containsKey('destacado_app')
            ? (serverFeatured is Map ? jsonMap(serverFeatured) : null)
            : featuredPick(picks);
        // Sin pronóstico sellado, los «Mercados del partido» siguen siendo estimaciones del modelo.
        final marketRows = jsonRows(jsonMap(ficha['mercados'])['filas']);
        final noPicks = marketRows.isEmpty
            ? l10n.detailNoPicks
            : marketRows.any((r) => r['locked'] != true)
            ? l10n.detailNoSealedModel
            : l10n.detailNoSealedModelVip;
        final alertCount = MatchAlerts.fromFicha(ficha)?.total ?? 0;

        final local = jsonMap(ficha['local']);
        final away = jsonMap(ficha['visitante']);
        final homeName = '${local['nombre'] ?? l10n.commonHome}';
        final awayName = '${away['nombre'] ?? l10n.commonAway}';
        final homeForm = jsonMap(local['forma'])['resumen'];
        final awayForm = jsonMap(away['forma'])['resumen'];
        final homeRacha = (homeForm?['racha'] as String?)?.split('').join(' ');
        final awayRacha = (awayForm?['racha'] as String?)?.split('').join(' ');

        // Probabilidades del modelo
        final probsMap = jsonMap(ficha['probabilities']);
        final pHome = statisticNumber(probsMap['home']);
        final pDraw = statisticNumber(probsMap['draw']);
        final pAway = statisticNumber(probsMap['away']);

        String? bigProb;
        String? bigLabel;
        List<MatchProbabilityPart>? probParts;

        if (pHome != null && pAway != null) {
          final homePct = (pHome * 100).round();
          final awayPct = (pAway * 100).round();
          final drawPct = pDraw != null ? (pDraw * 100).round() : (100 - homePct - awayPct);

          if (pHome >= pAway && pHome >= (pDraw ?? 0)) {
            bigProb = '$homePct%';
            bigLabel = l10n.selHomeWins(homeName);
          } else if (pAway >= pHome && pAway >= (pDraw ?? 0)) {
            bigProb = '$awayPct%';
            bigLabel = l10n.selHomeWins(awayName);
          } else {
            bigProb = '$drawPct%';
            bigLabel = l10n.commonDraw.toUpperCase();
          }

          probParts = [
            MatchProbabilityPart(
              label: homeName.toUpperCase(),
              percent: homePct.toDouble(),
              color: pHome >= pAway ? QfColors.cyan : const Color(0xFF747D99),
            ),
            if (pDraw != null)
              MatchProbabilityPart(
                label: l10n.commonDraw.toUpperCase(),
                percent: drawPct.toDouble(),
                color: const Color(0xFF747D99),
              ),
            MatchProbabilityPart(
              label: awayName.toUpperCase(),
              percent: awayPct.toDouble(),
              color: pAway >= pHome ? QfColors.cyan : const Color(0xFFD1D4DE),
            ),
          ];
        } else if (featured != null) {
          final p = statisticNumber(featured['probabilidad'] ?? featured['probability'] ?? featured['prob']);
          if (p != null) {
            bigProb = '${(p * (p <= 1 ? 100 : 1)).round()}%';
            bigLabel = '${featured['seleccion'] ?? featured['texto'] ?? featured['selection'] ?? ''}';
          }
        }

        final score = match['marcador'];
        final inPlayScore = (score is List && score.length == 2)
            ? Text(
                '${score[0]}–${score[1]}',
                style: const TextStyle(
                  fontFamily: qfMono,
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: QfColors.green,
                ),
              )
            : null;

        return MatchShell(
          header: MatchTopBar(
            league: '${jsonMap(match['liga'])['nombre'] ?? ''}',
            when: kickoffText(match['kickoff_utc']),
            onClose: () => Navigator.pop(context),
          ),
          hero: MatchHero(
            sideA: MatchHeroSide(
              name: homeName,
              image: TeamCrest(team: local, api: widget.api, size: 58),
              sub: homeRacha,
            ),
            sideB: MatchHeroSide(
              name: awayName,
              image: TeamCrest(team: away, api: widget.api, size: 58),
              sub: awayRacha,
            ),
            bigProb: bigProb,
            bigLabel: bigLabel,
            centerExtra: inPlayScore,
            probs: probParts,
          ),
          tabs: MatchTabs(
            labels: [
              l10n.detailTabPredictions,
              l10n.detailTabStats,
              l10n.detailTabH2h,
              l10n.detailTabAlerts,
            ],
            index: tab,
            alertIndex: 3,
            alertCount: alertCount,
            onChanged: (i) => setState(() => tab = i),
          ),
          body: switch (tab) {
            0 => Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (data['locked'] == true && picks.isEmpty)
                  liveCard(
                    border: liveGold,
                    child: Column(
                      children: [
                        liveText(l10n.detailVipPickNotice, bold: true),
                        const SizedBox(height: 12),
                        liveButton(l10n.vipAccessButton, widget.onVip),
                      ],
                    ),
                  ),
                if (picks.isEmpty && featured == null && data['locked'] != true)
                  training(noPicks),
                if (picks.isNotEmpty && featured == null)
                  training(l10n.detailNoFeatured),
                const SizedBox(height: 12),
                LiveScoreStrip(ficha: ficha),
                if (featured != null)
                  ForecastPanel(pick: featured, ficha: ficha),
                MatchMarkets(
                  data: jsonMap(ficha['mercados']),
                  onVip: widget.onVip,
                  home: homeName,
                  away: awayName,
                ),
              ],
            ),
            1 => stats(data, ficha),
            3 => AlertsTab(ficha: ficha, api: widget.api),
            _ => tactics(data, ficha),
          },
          bottomBar: MatchBottomBar(
            cost: (jsonMap(data['rewards'])['unlock_cost'] as num?)?.toInt() ?? 40,
            onUnlock: widget.onUnlock,
            onVip: widget.onVip,
          ),
        );
      },
    ),
  );
}
