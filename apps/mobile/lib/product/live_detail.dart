import 'package:flutter/material.dart';

import 'live_api.dart';
import 'live_forecast.dart';
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
  String filter = 'Todos';
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
                  '${p['marcador'] ?? ''} · ${p['res'] ?? ''}',
                  bold: true,
                ),
              ],
            ),
          ),
        )
        .toList(),
  );
  Widget stats(JsonMap data, JsonMap ficha) =>
      MatchStatistics(data: data, api: widget.api);

  Widget tactics(JsonMap data, JsonMap ficha) {
    if (!featureEnabled(data, 'h2h')) {
      return training(featureMessage(data, 'h2h'));
    }
    final h2h = jsonRows(jsonMap(ficha['cara_a_cara'])['partidos']);
    final lineups = jsonMap(ficha['alineaciones']),
        injuries = jsonMap(ficha['bajas']);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        liveHeading('Historial directo (H2H)'),
        if (h2h.isEmpty)
          training('No hay enfrentamientos registrados para este partido.')
        else
          results(h2h),
        liveHeading('Alineaciones'),
        if (lineups.isEmpty)
          training('Alineaciones todavía no confirmadas.')
        else
          ...['home', 'away'].map((side) {
            final l = jsonMap(lineups[side]);
            final players = jsonRows(l['titulares']);
            return liveCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  liveText(
                    '${jsonMap(ficha[side == 'home' ? 'local' : 'visitante'])['nombre']} · ${l['formacion'] ?? 'Formación pendiente'}',
                    bold: true,
                  ),
                  const SizedBox(height: 10),
                  if (players.isEmpty)
                    liveText('Sin titulares confirmados.', color: liveMuted)
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
        liveHeading('Bajas reportadas'),
        if (injuries.isEmpty)
          training('No hay una comprobación de bajas disponible.')
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
                    liveText(
                      'Sin bajas en el reporte disponible.',
                      color: liveMuted,
                      size: 12,
                    )
                  else
                    ...jsonRows(injuries[side]).map(
                      (p) => liveText(
                        '${p['jugador'] ?? p['player']} · ${p['motivo'] ?? p['reason']}',
                        size: 13,
                      ),
                    ),
                  liveText(
                    'Comprobado: ${kickoffText(injuries['comprobada'])}',
                    color: liveMuted,
                    size: 10,
                  ),
                ],
              ),
            ),
          ),
        liveHeading('Árbitro'),
        training('Árbitro pendiente de confirmar.'),
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
                                'Reintentar',
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
        final markets = {'Todos', ...picks.map((p) => '${p['market']}')};
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
                    tooltip: 'Cerrar',
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
                          (0, 'Pronósticos'),
                          (1, 'Estadísticas'),
                          (2, 'H2H'),
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
                        if (data['locked'] == true)
                          liveCard(
                            border: liveGold,
                            child: Column(
                              children: [
                                liveText(
                                  'Este partido tiene un pronóstico VIP',
                                  bold: true,
                                ),
                                const SizedBox(height: 12),
                                liveButton('Ver acceso VIP', widget.onVip),
                              ],
                            ),
                          ),
                        if (picks.isEmpty && data['locked'] != true)
                          training(
                            'No hay pronósticos publicados para este partido.',
                          ),
                        if (markets.length > 2)
                          SingleChildScrollView(
                            scrollDirection: Axis.horizontal,
                            child: Row(
                              children: markets
                                  .map(
                                    (m) => Padding(
                                      padding: const EdgeInsets.only(right: 6),
                                      child: ChoiceChip(
                                        label: Text(
                                          m == 'Todos' ? m : marketName(m),
                                        ),
                                        selected: filter == m,
                                        onSelected: (_) =>
                                            setState(() => filter = m),
                                      ),
                                    ),
                                  )
                                  .toList(),
                            ),
                          ),
                        const SizedBox(height: 12),
                        LiveScoreStrip(ficha: ficha),
                        ...picks
                            .where(
                              (p) => filter == 'Todos' || p['market'] == filter,
                            )
                            .map(
                              (p) => ForecastPanel(
                                pick: p,
                                ficha: ficha,
                                onStats: () => setState(() => tab = 1),
                              ),
                            ),
                      ],
                    )
                  else if (tab == 1)
                    stats(data, ficha)
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
