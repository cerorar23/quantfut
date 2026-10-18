import 'package:flutter/material.dart';

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

class LiveMatchDetail extends StatefulWidget {
  const LiveMatchDetail({
    super.key,
    required this.api,
    required this.id,
    required this.onVip,
  });
  final QuantFutApi api;
  final String id;
  final VoidCallback onVip;
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
  );

  Widget tactics(JsonMap data, JsonMap ficha) {
    if (!featureEnabled(data, 'h2h')) {
      return training(featureMessage(data, 'h2h'));
    }
    final l10n = context.l10n;
    final h2h = jsonRows(jsonMap(ficha['cara_a_cara'])['partidos']);
    final lineups = jsonMap(ficha['alineaciones']),
        injuries = jsonMap(ficha['bajas']);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        liveHeading(l10n.detailH2hTitle),
        if (h2h.isEmpty) training(l10n.detailNoH2h) else results(h2h),
        liveHeading(l10n.detailLineups),
        if (lineups.isEmpty)
          training(l10n.detailLineupsPending)
        else
          ...['home', 'away'].map((side) {
            final l = jsonMap(lineups[side]);
            final players = jsonRows(l['titulares']);
            return liveCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  liveText(
                    '${jsonMap(ficha[side == 'home' ? 'local' : 'visitante'])['nombre']} · ${l['formacion'] ?? l10n.detailFormationPending}',
                    bold: true,
                  ),
                  const SizedBox(height: 10),
                  if (players.isEmpty)
                    liveText(l10n.detailNoStarters, color: liveMuted)
                  else
                    ...players.map(
                      (p) => liveText(
                        '${p['numero'] ?? p['number'] ?? ''} ${p['nombre'] ?? p['name'] ?? p['player'] ?? ''}',
                        size: 13,
                      ),
                    ),
                ],
              ),
            );
          }),
        liveHeading(l10n.detailInjuries),
        if (injuries.isEmpty)
          training(l10n.detailNoInjuriesCheck)
        else
          ...['home', 'away'].map(
            (side) => liveCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  liveText(
                    '${jsonMap(ficha[side == 'home' ? 'local' : 'visitante'])['nombre']}',
                    bold: true,
                  ),
                  const SizedBox(height: 8),
                  if (jsonRows(injuries[side]).isEmpty)
                    liveText(l10n.detailNoInjuries, color: liveMuted, size: 12)
                  else
                    ...jsonRows(injuries[side]).map(
                      (p) => liveText(
                        '${p['jugador'] ?? p['player']} · ${p['motivo'] ?? p['reason']}',
                        size: 13,
                      ),
                    ),
                  liveText(
                    l10n.detailChecked(kickoffText(injuries['comprobada'])),
                    color: liveMuted,
                    size: 10,
                  ),
                ],
              ),
            ),
          ),
        liveHeading(l10n.detailReferee),
        training(l10n.detailRefereePending),
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
                  icon: const Icon(Icons.close, color: liveMuted),
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
                              liveText('${snapshot.error}', color: liveMuted),
                              liveButton(
                                context.l10n.commonRetry,
                                () => setState(
                                  () => future = widget.api.detail(widget.id),
                                ),
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
        final featured = featuredPick(picks);
        final alertCount = MatchAlerts.fromFicha(ficha)?.total ?? 0;
        return Column(
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(
                children: [
                  Expanded(
                    child: liveText(
                      '${jsonMap(match['liga'])['nombre'] ?? ''} · ${kickoffText(match['kickoff_utc'])}',
                      size: 11,
                      color: liveMuted,
                    ),
                  ),
                  IconButton(
                    tooltip: l10n.commonClose,
                    onPressed: () => Navigator.pop(context),
                    icon: const Icon(Icons.close, color: liveMuted),
                  ),
                ],
              ),
            ),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  MatchFixtureHeader(ficha: ficha, api: widget.api),
                  const SizedBox(height: 24),
                  Container(
                    decoration: const BoxDecoration(
                      border: Border(bottom: BorderSide(color: Colors.white12)),
                    ),
                    child: Row(
                      children: [
                        for (final item in [
                          (0, l10n.detailTabPredictions),
                          (1, l10n.detailTabStats),
                          (2, l10n.detailTabH2h),
                          (3, l10n.detailTabAlerts),
                        ])
                          Expanded(
                            child: Semantics(
                              selected: tab == item.$1,
                              button: true,
                              child: InkWell(
                                onTap: () => setState(() => tab = item.$1),
                                child: Column(
                                  children: [
                                    Padding(
                                      padding: const EdgeInsets.symmetric(
                                        vertical: 14,
                                        horizontal: 4,
                                      ),
                                      child: Row(
                                        mainAxisAlignment:
                                            MainAxisAlignment.center,
                                        children: [
                                          Flexible(
                                            child: Text(
                                              item.$2,
                                              maxLines: 1,
                                              overflow: TextOverflow.ellipsis,
                                              style: TextStyle(
                                                fontSize: 12,
                                                fontWeight: FontWeight.bold,
                                                color: tab == item.$1
                                                    ? statsLime
                                                    : liveMuted,
                                              ),
                                            ),
                                          ),
                                          if (item.$1 == 3 && alertCount > 0) ...[
                                            const SizedBox(width: 4),
                                            Container(
                                              key: const ValueKey(
                                                'alerts-tab-badge',
                                              ),
                                              padding: const EdgeInsets.symmetric(
                                                horizontal: 5,
                                                vertical: 1,
                                              ),
                                              decoration: BoxDecoration(
                                                color: const Color(0xffe85667),
                                                borderRadius:
                                                    BorderRadius.circular(99),
                                              ),
                                              child: Text(
                                                '$alertCount',
                                                style: const TextStyle(
                                                  color: Colors.white,
                                                  fontSize: 9,
                                                  fontWeight: FontWeight.bold,
                                                ),
                                              ),
                                            ),
                                          ],
                                        ],
                                      ),
                                    ),
                                    Container(
                                      height: 3,
                                      color: tab == item.$1
                                          ? statsLime
                                          : Colors.transparent,
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 18),
                  if (tab == 0)
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Con un pronóstico ya abierto (gratis o desbloqueado) no se ofrece VIP
                        // arriba: los demás van con su candado en «Mercados del partido».
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
                        if (picks.isEmpty && data['locked'] != true)
                          training(l10n.detailNoPicks),
                        const SizedBox(height: 12),
                        LiveScoreStrip(ficha: ficha),
                        if (featured != null)
                          ForecastPanel(pick: featured, ficha: ficha),
                        MatchMarkets(
                          data: jsonMap(ficha['mercados']),
                          onVip: widget.onVip,
                          home:
                              '${jsonMap(ficha['local'])['nombre'] ?? l10n.commonHome}',
                          away:
                              '${jsonMap(ficha['visitante'])['nombre'] ?? l10n.commonAway}',
                        ),
                      ],
                    )
                  else if (tab == 1)
                    stats(data, ficha)
                  else if (tab == 3)
                    AlertsTab(ficha: ficha, api: widget.api)
                  else
                    tactics(data, ficha),
                ],
              ),
            ),
          ],
        );
      },
    ),
  );
}
