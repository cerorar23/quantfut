import 'package:flutter/material.dart';

import 'market_catalog.dart';
import 'match_visuals.dart';

class VipFeatureComparison extends StatelessWidget {
  const VipFeatureComparison({super.key});
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: matchSurface,
      borderRadius: BorderRadius.circular(18),
      border: Border.all(color: matchGold.withValues(alpha: .3)),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text(
          'ELIGE CÓMO SEGUIR LOS PARTIDOS',
          style: TextStyle(fontFamily: 'Gilroy ExtraBold', fontSize: 15),
        ),
        const SizedBox(height: 8),
        const Text(
          'Comparación de acceso propuesta. Las funciones pendientes se activarán por fases.',
          style: TextStyle(color: matchMuted, fontSize: 11, height: 1.5),
        ),
        const SizedBox(height: 16),
        _row('Funciones', 'Básico', 'VIP', header: true),
        for (final row in const [
          ('Pronósticos públicos', 'Sí', 'Sí'),
          ('Análisis premium del partido', 'Vista gratuita', 'Completo'),
          ('Estadísticas disponibles', 'Públicas', 'Ampliadas'),
          ('Historial de resultados', 'Público', 'Público'),
          ('Acceso compartido app y web', 'Por conectar', 'Por conectar'),
          ('Notificaciones de picks', 'Por definir', 'Por definir'),
          ('Asistente de análisis', 'En estudio', 'En estudio'),
          ('Exportar pronósticos', 'En estudio', 'En estudio'),
          ('Soporte', 'Por definir', 'Por definir'),
        ]) ...[
          const Divider(color: Colors.white10, height: 20),
          _row(row.$1, row.$2, row.$3),
        ],
        const SizedBox(height: 16),
        const Text(
          'Los precios, renovaciones, cancelaciones y reembolsos se mostrarán según las condiciones definitivas del proveedor de compra.',
          style: TextStyle(color: matchMuted, fontSize: 11, height: 1.5),
        ),
      ],
    ),
  );

  Widget _row(
    String feature,
    String basic,
    String vip, {
    bool header = false,
  }) => Row(
    crossAxisAlignment: CrossAxisAlignment.center,
    children: [
      Expanded(
        flex: 3,
        child: Text(
          feature,
          style: TextStyle(
            color: header ? matchMuted : Colors.white,
            fontSize: 12,
            fontFamily: header ? 'Gilroy Bold' : 'Gilroy Medium',
          ),
        ),
      ),
      const SizedBox(width: 8),
      Expanded(
        flex: 2,
        child: Text(
          basic,
          textAlign: TextAlign.center,
          style: TextStyle(
            color: header ? Colors.white : matchMuted,
            fontSize: 11,
            fontFamily: header ? 'Gilroy ExtraBold' : 'Gilroy Medium',
          ),
        ),
      ),
      const SizedBox(width: 8),
      Expanded(
        flex: 2,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 9),
          decoration: BoxDecoration(
            color: matchGold.withValues(alpha: .09),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(
            vip,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: matchGold,
              fontSize: 11,
              fontFamily: 'Gilroy Bold',
            ),
          ),
        ),
      ),
    ],
  );
}

class VipPerformancePanel extends StatelessWidget {
  const VipPerformancePanel({super.key, required this.onPlans});
  final VoidCallback onPlans;

  @override
  Widget build(BuildContext context) => FutureBuilder<MarketCatalog>(
    future: MarketCatalog.load(),
    initialData: MarketCatalog.current,
    builder: (context, snapshot) {
      final catalog = snapshot.data;
      final markets =
          catalog
              ?.forSport('Fútbol')
              .where((market) => market.published.cases > 0)
              .toList()
            ?..sort((a, b) => b.published.cases.compareTo(a.published.cases));
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(22),
          border: Border.all(color: matchGold.withValues(alpha: .3)),
          gradient: const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xff19241b), Color(0xff10131b), Color(0xff0c141c)],
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Row(
              children: [
                Icon(Icons.workspace_premium, color: matchGold, size: 34),
                SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'EL MODELO, A LA VISTA',
                        style: TextStyle(
                          fontFamily: 'Gilroy ExtraBold',
                          fontSize: 16,
                        ),
                      ),
                      SizedBox(height: 4),
                      Text(
                        'HISTORIAL PUBLICADO · FÚTBOL',
                        style: TextStyle(color: matchGold, fontSize: 10),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            LayoutBuilder(
              builder: (context, constraints) {
                final tiles = [
                  _metric(
                    Icons.track_changes,
                    percent(catalog?.overall.observed),
                    'Acierto publicado',
                    matchGold,
                    catalog == null
                        ? 'Historial por cargar'
                        : '${catalog.overall.won}/${catalog.overall.cases} resueltos',
                  ),
                  _metric(
                    Icons.local_fire_department,
                    '—',
                    'Racha actual',
                    const Color(0xffff8b3d),
                    'Pendiente de secuencia',
                  ),
                ];
                if (MediaQuery.textScalerOf(context).scale(12) > 17) {
                  return Column(
                    children: [
                      tiles.first,
                      const SizedBox(height: 8),
                      tiles.last,
                    ],
                  );
                }
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(child: tiles.first),
                    const SizedBox(width: 8),
                    Expanded(child: tiles.last),
                  ],
                );
              },
            ),
            const SizedBox(height: 18),
            const Text(
              'RESULTADOS POR MERCADO',
              style: TextStyle(
                color: matchMuted,
                fontFamily: 'Gilroy Bold',
                fontSize: 11,
              ),
            ),
            const SizedBox(height: 10),
            if (snapshot.hasError && catalog == null)
              const Text('No se pudo cargar el historial guardado.')
            else if (markets == null)
              const Text('Cargando historial…')
            else
              for (final market in markets.take(3))
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Wrap(
                        alignment: WrapAlignment.spaceBetween,
                        spacing: 10,
                        runSpacing: 4,
                        children: [
                          Text(
                            market.title,
                            style: const TextStyle(
                              fontFamily: 'Gilroy Bold',
                              fontSize: 12,
                            ),
                          ),
                          Text(
                            percent(market.published.observed),
                            style: const TextStyle(
                              color: matchGreen,
                              fontFamily: 'Gilroy Bold',
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 5),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(6),
                        child: LinearProgressIndicator(
                          value: market.published.observed! / 100,
                          color: matchGreen,
                          backgroundColor: Colors.white10,
                          minHeight: 5,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '${market.published.won}/${market.published.cases} · Muestra limitada',
                        style: const TextStyle(color: matchMuted, fontSize: 10),
                      ),
                    ],
                  ),
                ),
            Text(
              catalog == null
                  ? 'El acierto se mostrará junto con su muestra y fecha.'
                  : 'Corte: ${catalog.cutoff} · ${catalog.cutoffTime}. Historial guardado, sin actualización en directo.',
              style: const TextStyle(
                color: matchMuted,
                fontSize: 10,
                height: 1.5,
              ),
            ),
            const SizedBox(height: 14),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: matchGold.withValues(alpha: .04),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: matchGold.withValues(alpha: .35)),
              ),
              child: Column(
                children: [
                  const Icon(Icons.lock_open_rounded, color: matchGold),
                  const SizedBox(height: 8),
                  const Text(
                    'Amplía tu análisis con VIP',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontFamily: 'Gilroy Bold'),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Pronósticos completos y estadísticas disponibles del partido. Revisa los planes de acceso.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: matchMuted,
                      fontSize: 11,
                      height: 1.4,
                    ),
                  ),
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton(
                      key: const ValueKey('vip-review-plans'),
                      onPressed: onPlans,
                      style: FilledButton.styleFrom(
                        backgroundColor: matchGold,
                        foregroundColor: Colors.black,
                        padding: const EdgeInsets.all(12),
                      ),
                      child: const Text(
                        'Ver planes VIP',
                        textAlign: TextAlign.center,
                        style: TextStyle(fontFamily: 'Gilroy ExtraBold'),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
    },
  );

  Widget _metric(
    IconData icon,
    String value,
    String label,
    Color color,
    String context,
  ) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(
      color: Colors.black.withValues(alpha: .15),
      borderRadius: BorderRadius.circular(14),
      border: Border.all(color: color.withValues(alpha: .2)),
    ),
    child: Column(
      children: [
        Icon(icon, color: color),
        const SizedBox(height: 6),
        Text(
          value,
          style: TextStyle(
            color: color,
            fontFamily: 'Gilroy ExtraBold',
            fontSize: 25,
          ),
        ),
        Text(
          label,
          textAlign: TextAlign.center,
          style: const TextStyle(fontSize: 11),
        ),
        const SizedBox(height: 5),
        Text(
          context,
          textAlign: TextAlign.center,
          style: const TextStyle(color: matchMuted, fontSize: 10),
        ),
      ],
    ),
  );
}
