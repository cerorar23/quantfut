import 'package:flutter/material.dart';

import 'market_catalog.dart';

const _bg = Color(0xff090f1a),
    _panel = Color(0xff132333),
    _cyan = Color(0xff00d5ee),
    _gold = Color(0xffffb600),
    _muted = Color(0xffa0adbd);

IconData marketIcon(String id) => switch (id) {
  'handicap' => Icons.shield_outlined,
  'double_chance' => Icons.alt_route_rounded,
  'corners' || 'corners_team' => Icons.flag_outlined,
  'cards' => Icons.style_outlined,
  'nba_winner' || 'nba_team' || 'nba_total' => Icons.sports_basketball_outlined,
  _ => Icons.sports_soccer,
};

Widget _card(Widget child, {Color? border}) => Material(
  color: _panel,
  shape: RoundedRectangleBorder(
    borderRadius: BorderRadius.circular(15),
    side: BorderSide(color: border ?? const Color(0xff223c51)),
  ),
  clipBehavior: Clip.antiAlias,
  child: Padding(padding: const EdgeInsets.all(16), child: child),
);

class PublishedSummary extends StatelessWidget {
  const PublishedSummary({super.key, this.sport = 'Fútbol'});
  final String sport;
  @override
  Widget build(BuildContext context) => FutureBuilder<MarketCatalog>(
    future: MarketCatalog.load(),
    initialData: MarketCatalog.current,
    builder: (context, snapshot) {
      final catalog = snapshot.data;
      if (snapshot.hasError) {
        return const Text(
          'Historial no disponible.',
          style: TextStyle(color: _muted),
        );
      }
      if (catalog == null) return const LinearProgressIndicator();
      if (sport == 'NBA') {
        return _card(
          const Text(
            'NBA · Evaluación exploratoria\nAún sin un historial prospectivo confirmado.',
            style: TextStyle(color: _muted, height: 1.5),
          ),
        );
      }
      return _card(
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'HISTORIAL PUBLICADO · ALTA PROBABILIDAD',
              style: TextStyle(color: _cyan, fontSize: 10, letterSpacing: .7),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 22,
              runSpacing: 10,
              children: [
                _Number(percent(catalog.overall.observed), 'ACIERTO OBSERVADO'),
                _Number(
                  '${catalog.overall.won}/${catalog.overall.cases}',
                  'ACIERTOS / LIQUIDADOS',
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              'Corte ${catalog.cutoff} · ${catalog.cutoffTime}',
              style: const TextStyle(color: _muted, fontSize: 11),
            ),
            const SizedBox(height: 6),
            const Text(
              'Muestra inicial; no confirma todavía el acierto futuro.',
              style: TextStyle(color: _gold, fontSize: 11),
            ),
          ],
        ),
      );
    },
  );
}

class _Number extends StatelessWidget {
  const _Number(this.value, this.label);
  final String value, label;
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        value,
        style: const TextStyle(
          color: Colors.white,
          fontFamily: 'Gilroy ExtraBold',
          fontSize: 26,
        ),
      ),
      const SizedBox(height: 3),
      Text(label, style: const TextStyle(color: _muted, fontSize: 9)),
    ],
  );
}

class MarketsHub extends StatelessWidget {
  const MarketsHub({super.key, required this.sport, required this.onOpen});
  final String sport;
  final ValueChanged<String> onOpen;
  @override
  Widget build(BuildContext context) => FutureBuilder<MarketCatalog>(
    future: MarketCatalog.load(),
    initialData: MarketCatalog.current,
    builder: (context, snapshot) {
      if (snapshot.hasError) {
        return const Center(
          child: Text('No se pudo cargar la revisión de mercados.'),
        );
      }
      final catalog = snapshot.data;
      if (catalog == null) {
        return const Center(child: CircularProgressIndicator());
      }
      return ListView(
        padding: const EdgeInsets.all(12),
        children: [
          Text(
            sport == 'NBA'
                ? 'NBA · En evaluación'
                : 'Los mercados de tu modelo',
            style: const TextStyle(
              fontSize: 24,
              fontFamily: 'Gilroy ExtraBold',
            ),
          ),
          const SizedBox(height: 8),
          Text(
            sport == 'NBA'
                ? 'Resultados exploratorios. Todavía no los presentamos como mercados confirmados.'
                : 'Destacamos líneas habilitadas que pasaron la revisión histórica y tienen al menos ${caseCount(catalog.minimumCases)} casos.',
            style: const TextStyle(color: _muted, fontSize: 12, height: 1.5),
          ),
          const SizedBox(height: 16),
          PublishedSummary(sport: sport),
          const SizedBox(height: 18),
          for (final market in catalog.forSport(sport))
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: _MarketTile(
                market: market,
                minimum: catalog.minimumCases,
                onTap: () => onOpen(market.id),
              ),
            ),
          const Text(
            'Cada porcentaje pertenece a su línea y filtro de probabilidad. No se mezclan con el historial publicado. El acierto no mide rentabilidad.',
            style: TextStyle(color: _muted, fontSize: 11, height: 1.5),
          ),
        ],
      );
    },
  );
}

class _MarketTile extends StatelessWidget {
  const _MarketTile({
    required this.market,
    required this.minimum,
    required this.onTap,
  });
  final MarketFamily market;
  final int minimum;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    final best = market.bestSupported(minimum);
    final display = best ?? market.lines.first;
    return Semantics(
      button: true,
      child: Material(
        color: _panel,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(15),
          side: const BorderSide(color: Color(0xff223c51)),
        ),
        child: InkWell(
          key: ValueKey('market-${market.id}'),
          onTap: onTap,
          borderRadius: BorderRadius.circular(15),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(
                      marketIcon(market.id),
                      color: market.experimental ? _gold : _cyan,
                      size: 25,
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        market.title,
                        style: const TextStyle(
                          fontFamily: 'Gilroy Bold',
                          fontSize: 16,
                        ),
                      ),
                    ),
                    const Icon(Icons.chevron_right, color: _muted),
                  ],
                ),
                const SizedBox(height: 14),
                Wrap(
                  spacing: 12,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Text(
                      percent(display.observed),
                      style: TextStyle(
                        fontFamily: 'Gilroy ExtraBold',
                        fontSize: 29,
                        color: market.experimental ? _gold : _cyan,
                      ),
                    ),
                    Text(
                      '${caseCount(display.cases)} casos\n${market.experimental ? 'Exploratorio' : 'Prueba histórica'}',
                      style: const TextStyle(
                        color: _muted,
                        fontSize: 11,
                        height: 1.5,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(display.label, style: const TextStyle(fontSize: 12)),
                const SizedBox(height: 4),
                Text(
                  'Filtro de la prueba: ${display.band}',
                  style: const TextStyle(color: _muted, fontSize: 10),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class MarketDetailScreen extends StatefulWidget {
  const MarketDetailScreen({
    super.key,
    required this.catalog,
    required this.market,
    required this.onVip,
  });
  final MarketCatalog catalog;
  final MarketFamily market;
  final VoidCallback onVip;
  @override
  State<MarketDetailScreen> createState() => _MarketDetailScreenState();
}

class _MarketDetailScreenState extends State<MarketDetailScreen> {
  int _tab = 0;
  void _notificationNotice() => showDialog<void>(
    context: context,
    builder: (context) => AlertDialog(
      title: const Text('Avisos por conectar'),
      content: const Text(
        'Activaremos las preferencias y el envío de avisos al integrar Firebase. Este interruptor todavía no registra ni envía notificaciones.',
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Entendido'),
        ),
      ],
    ),
  );

  @override
  Widget build(BuildContext context) {
    final catalog = widget.catalog, market = widget.market;
    final best = market.bestSupported(catalog.minimumCases);
    final record = market.published;
    return Theme(
      data: ThemeData(
        brightness: Brightness.dark,
        fontFamily: 'Gilroy Medium',
        colorScheme: const ColorScheme.dark(
          primary: _cyan,
          secondary: _gold,
          surface: _panel,
        ),
      ),
      child: Scaffold(
        backgroundColor: _bg,
        appBar: AppBar(
          backgroundColor: _bg,
          title: Text(
            market.title,
            style: const TextStyle(fontFamily: 'Gilroy Bold', fontSize: 17),
          ),
        ),
        body: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 650),
              child: ListView(
                padding: const EdgeInsets.all(14),
                children: [
                  _card(
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(marketIcon(market.id), color: _cyan, size: 21),
                            const SizedBox(width: 9),
                            const Expanded(
                              child: Text(
                                'Acierto del mercado',
                                style: TextStyle(fontFamily: 'Gilroy Bold'),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 16),
                        Wrap(
                          spacing: 24,
                          runSpacing: 16,
                          children: [
                            _Number(
                              percent(record.observed),
                              'HISTORIAL PUBLICADO',
                            ),
                            _Number(
                              best == null ? '—' : percent(best.observed),
                              'PRUEBA HISTÓRICA · LÍNEA DESTACADA',
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        Text(
                          record.cases == 0
                              ? 'Sin resultados publicados para esta sección.'
                              : '${record.won}/${record.cases} aciertos liquidados de esta familia · corte ${catalog.cutoff}.',
                          style: const TextStyle(
                            color: _muted,
                            fontSize: 11,
                            height: 1.5,
                          ),
                        ),
                        if (record.cases > 0 && record.cases < 50)
                          const Padding(
                            padding: EdgeInsets.only(top: 8),
                            child: Text(
                              'Muestra publicada pequeña: todavía no confirma el porcentaje.',
                              style: TextStyle(color: _gold, fontSize: 11),
                            ),
                          ),
                        if (best != null)
                          Padding(
                            padding: const EdgeInsets.only(top: 8),
                            child: Text(
                              '${best.label} · ${caseCount(best.cases)} casos · filtro ${best.band}.',
                              style: const TextStyle(
                                color: _muted,
                                fontSize: 11,
                                height: 1.5,
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 14),
                  Wrap(
                    spacing: 10,
                    children: [
                      for (var i = 0; i < 2; i++)
                        ChoiceChip(
                          label: Text(i == 0 ? 'Hoy' : 'Histórico'),
                          selected: _tab == i,
                          selectedColor: _gold,
                          showCheckmark: false,
                          labelStyle: TextStyle(
                            color: _tab == i ? _bg : Colors.white,
                          ),
                          onSelected: (_) => setState(() => _tab = i),
                        ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  if (_tab == 0) ...[
                    _card(
                      Row(
                        children: [
                          const Icon(
                            Icons.notifications_outlined,
                            color: _gold,
                          ),
                          const SizedBox(width: 10),
                          const Expanded(
                            child: Text(
                              'Avisos de este mercado\nPendientes de conexión',
                              style: TextStyle(fontSize: 12, height: 1.5),
                            ),
                          ),
                          Switch(
                            value: false,
                            onChanged: (_) => _notificationNotice(),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 12),
                    _card(
                      const Text(
                        'Los pronósticos de hoy aún están por conectar. Los datos de esta pantalla son un corte guardado del historial y de las pruebas.',
                        style: TextStyle(
                          color: _muted,
                          fontSize: 12,
                          height: 1.6,
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                    _card(
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'El análisis completo, en tu cuenta VIP',
                            style: TextStyle(
                              fontFamily: 'Gilroy Bold',
                              fontSize: 18,
                            ),
                          ),
                          const SizedBox(height: 10),
                          Text(
                            market.subtitle,
                            style: const TextStyle(
                              color: _muted,
                              fontSize: 13,
                              height: 1.5,
                            ),
                          ),
                          const SizedBox(height: 12),
                          const Text(
                            'Podrás revisar contexto, selección y resultados. El historial agregado permanece visible.',
                            style: TextStyle(fontSize: 12, height: 1.5),
                          ),
                          const SizedBox(height: 16),
                          SizedBox(
                            width: double.infinity,
                            child: FilledButton(
                              onPressed: widget.onVip,
                              style: FilledButton.styleFrom(
                                backgroundColor: _gold,
                                foregroundColor: _bg,
                              ),
                              child: const Text(
                                'Hazte VIP',
                                style: TextStyle(
                                  fontFamily: 'Gilroy ExtraBold',
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(height: 8),
                          const Text(
                            'Vista previa de acceso · compras sin activar',
                            style: TextStyle(color: _muted, fontSize: 10),
                          ),
                        ],
                      ),
                      border: _gold.withValues(alpha: .4),
                    ),
                  ] else ...[
                    const Text(
                      'Revisión por línea',
                      style: TextStyle(fontFamily: 'Gilroy Bold', fontSize: 19),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      market.experimental
                          ? 'Exploratoria · las probabilidades no tienen confirmación prospectiva.'
                          : 'Resultados retrospectivos. Una muestra pequeña o una línea pendiente de desplegar no se destaca como fortaleza.',
                      style: const TextStyle(
                        color: _muted,
                        fontSize: 12,
                        height: 1.5,
                      ),
                    ),
                    const SizedBox(height: 12),
                    for (final line in market.lines)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: _LineEvidence(
                          key: ValueKey('evidence-${line.key}'),
                          line: line,
                          minimum: catalog.minimumCases,
                          experimental: market.experimental,
                        ),
                      ),
                    const Text(
                      'El detalle de resultados publicados por partido se conectará con el historial de la web.',
                      style: TextStyle(
                        color: _muted,
                        fontSize: 11,
                        height: 1.5,
                      ),
                    ),
                  ],
                  const SizedBox(height: 18),
                  Text(
                    market.origin,
                    style: const TextStyle(
                      color: _muted,
                      fontSize: 11,
                      height: 1.6,
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Acierto histórico y probabilidad estimada son medidas distintas. El acierto no mide rentabilidad.',
                    style: TextStyle(color: _muted, fontSize: 11, height: 1.5),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _LineEvidence extends StatelessWidget {
  const _LineEvidence({
    super.key,
    required this.line,
    required this.minimum,
    required this.experimental,
  });
  final MarketLine line;
  final int minimum;
  final bool experimental;
  @override
  Widget build(BuildContext context) {
    final supported = !experimental && line.supported(minimum);
    final status = experimental
        ? 'EXPLORATORIO'
        : !line.deployed
        ? 'PENDIENTE DE DESPLEGAR'
        : line.cases < minimum
        ? 'MUESTRA LIMITADA'
        : line.passed
        ? 'RESPALDO HISTÓRICO'
        : 'NO PASÓ LA REVISIÓN';
    return _card(
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            status,
            style: TextStyle(
              color: supported ? _cyan : _gold,
              fontSize: 9,
              letterSpacing: .5,
            ),
          ),
          const SizedBox(height: 9),
          Text(
            line.label,
            style: const TextStyle(fontFamily: 'Gilroy Bold', fontSize: 15),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 20,
            runSpacing: 8,
            children: [
              _Number(percent(line.observed), 'ACIERTO OBSERVADO'),
              _Number(caseCount(line.cases), 'CASOS EVALUADOS'),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            line.expected == null
                ? 'Referencia en los mismos casos: ${percent(line.baseline)}.'
                : 'Probabilidad media estimada: ${percent(line.expected)}.',
            style: const TextStyle(color: _muted, fontSize: 11),
          ),
          const SizedBox(height: 6),
          Text(
            'Filtro de la prueba: ${line.band}',
            style: const TextStyle(color: _muted, fontSize: 11),
          ),
          if (!supported)
            const Padding(
              padding: EdgeInsets.only(top: 9),
              child: Text(
                'No se usa como mercado destacado confirmado.',
                style: TextStyle(color: _gold, fontSize: 11),
              ),
            ),
        ],
      ),
    );
  }
}
