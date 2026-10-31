// Ficha de partido de NBA y tenis (hoja inferior): Pronósticos, Análisis, H2H y Alertas.
// Los feeds son públicos: sin candado VIP ni desbloqueo con monedas, y nunca se muestran cuotas.
import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import 'home_sport.dart';
import 'live_api.dart';
import 'live_widgets.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';
import 'sport_detail_tabs.dart';
import 'sport_images.dart';
import 'sports.dart';
import 'sports_feed.dart';
import 'sports_quotes.dart';

/// Abre la ficha del partido como hoja inferior (misma forma que la de fútbol).
Future<void> showSportDetail(
  BuildContext context, {
  required QuantFutApi api,
  required SportEvent event,
  required ImageCatalog images,
  QuotesOverlay quotes = QuotesOverlay.empty,
}) => showModalBottomSheet<void>(
  context: context,
  isScrollControlled: true,
  backgroundColor: QfColors.bg,
  useSafeArea: true,
  builder: (_) => FractionallySizedBox(
    heightFactor: .96,
    child: Theme(
      data: liveTheme(),
      child: SportDetail(api: api, event: event, images: images, quotes: quotes),
    ),
  ),
);

class SportDetail extends StatefulWidget {
  const SportDetail({
    super.key,
    required this.api,
    required this.event,
    required this.images,
    this.quotes = QuotesOverlay.empty,
  });
  final QuantFutApi api;
  final SportEvent event;
  final ImageCatalog images;

  /// Cuotas de referencia del deporte; vacías si no llegaron.
  final QuotesOverlay quotes;
  @override
  State<SportDetail> createState() => _SportDetailState();
}

class _SportDetailState extends State<SportDetail> {
  int tab = 0;
  late final Future<JsonMap?> stats;

  @override
  void initState() {
    super.initState();
    stats = _loadStats();
  }

  SportEvent get e => widget.event;
  bool get nba => e.sport == SportKind.nba;
  Color get accent => sportSpecs[e.sport]!.accent;

  /// Estadísticas públicas del partido; cualquier fallo (404 incluido) es «no hay».
  Future<JsonMap?> _loadStats() async {
    try {
      final path = nba
          ? '/web/deportes/nba/estadisticas/${Uri.encodeComponent(e.id)}'
          : '/web/deportes/tenis/estadisticas/${Uri.encodeComponent(e.id)}';
      final r = await widget.api.request(path);
      return r is Map<String, dynamic> ? r : null;
    } catch (_) {
      return null;
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final labels = [
      l10n.detailTabPredictions,
      l10n.detailTabStats,
      l10n.detailTabH2h,
      l10n.detailTabAlerts,
    ];
    return Material(
      color: QfColors.bg,
      child: Column(
        children: [
          Align(
            alignment: Alignment.centerRight,
            child: IconButton(
              tooltip: l10n.commonClose,
              onPressed: () => Navigator.maybePop(context),
              icon: const Icon(Icons.close, color: QfColors.text2),
            ),
          ),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
              children: [
                _Header(api: widget.api, event: e, images: widget.images),
                const SizedBox(height: 16),
                Row(
                  children: [
                    for (var i = 0; i < labels.length; i++)
                      Expanded(
                        child: _TabButton(
                          label: labels[i],
                          selected: tab == i,
                          color: QfColors.primary,
                          onTap: () => setState(() => tab = i),
                        ),
                      ),
                  ],
                ),
                const Divider(height: 1, color: QfColors.border),
                const SizedBox(height: 16),
                switch (tab) {
                  0 => _Predictions(
                    api: widget.api,
                    event: e,
                    images: widget.images,
                    accent: accent,
                  ),
                  1 => SportAnalysis(stats: stats, event: e),
                  2 => SportH2h(stats: stats, event: e),
                  _ => SportAlerts(event: e),
                },
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _TabButton extends StatelessWidget {
  const _TabButton({
    required this.label,
    required this.selected,
    required this.color,
    required this.onTap,
  });
  final String label;
  final bool selected;
  final Color color;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) => Semantics(
    selected: selected,
    button: true,
    child: InkWell(
      onTap: onTap,
      child: ConstrainedBox(
        constraints: const BoxConstraints(minHeight: 44),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 4),
              child: Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  color: selected ? color : QfColors.text2,
                ),
              ),
            ),
            Container(height: 3, color: selected ? color : Colors.transparent),
          ],
        ),
      ),
    ),
  );
}

// ---- Cabecera --------------------------------------------------------------------------

/// Mercado ganador elegible; su probabilidad es la del lado local.
double? _homeWinProbability(SportEvent e) {
  for (final m in e.markets) {
    final winner =
        m.market == 'winner' || (m.market == null && m.id == 'winner');
    if (winner && m.eligible) {
      return m.selection == e.home ? m.probability : 1 - m.probability;
    }
  }
  return null;
}

/// Apellido para la leyenda de la barra (el nombre completo ya está sobre cada foto).
String _surname(String name) {
  final w = name.trim().split(RegExp(r'\s+'));
  return w.length > 1 ? w.sublist(1).join(' ') : name;
}

String? _surfaceLabel(AppLocalizations l10n, String surface) =>
    switch (surface.trim().toLowerCase()) {
      'clay' => l10n.sportSurfaceClay,
      'hard' => l10n.sportSurfaceHard,
      'grass' => l10n.sportSurfaceGrass,
      _ => null,
    };

class _Header extends StatelessWidget {
  const _Header({required this.api, required this.event, required this.images});
  final QuantFutApi api;
  final SportEvent event;
  final ImageCatalog images;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final nba = event.sport == SportKind.nba;
    final accent = sportSpecs[event.sport]!.accent;
    final pHome = _homeWinProbability(event);
    final homeCode = nba ? nbaTricode(event.home) : null;
    final awayCode = nba ? nbaTricode(event.away) : null;
    final homeLabel = homeCode ?? event.home;
    final awayLabel = awayCode ?? event.away;
    final surface = event.surface;
    final credits = <(String, TennisPhoto)>[];
    if (!nba) {
      for (final name in [event.home, event.away]) {
        final p = images.tennisPhoto(name);
        if (p != null) credits.add((name, p));
      }
    }
    Widget side(String name) => Expanded(
      child: Column(
        children: [
          sportAvatar(api, images, event.sport, name, size: nba ? 48 : 56),
          const SizedBox(height: 6),
          Text(
            name,
            textAlign: TextAlign.center,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              fontFamily: qfDisplay,
              fontWeight: FontWeight.w700,
              fontSize: 15,
              color: QfColors.text,
            ),
          ),
        ],
      ),
    );
    final score = event.score;
    return QfCard(
      accent: accent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 6,
            children: [
              QfBadge(event.league, color: accent),
              if (!nba && surface != null && _surfaceLabel(l10n, surface) != null)
                QfBadge(_surfaceLabel(l10n, surface)!, color: QfColors.text2),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              side(nba ? event.away : event.home),
              Padding(
                padding: const EdgeInsets.only(top: 14, left: 6, right: 6),
                child: Text(
                  nba ? '$awayLabel @ $homeLabel' : (score ?? ''),
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontFamily: qfMono,
                    fontSize: 13,
                    color: QfColors.text2,
                  ),
                ),
              ),
              side(nba ? event.home : event.away),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            kickoffText(event.start),
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 12, color: QfColors.text2),
          ),
          if (nba && score != null) ...[
            const SizedBox(height: 4),
            Text(
              score,
              textAlign: TextAlign.center,
              style: const TextStyle(fontFamily: qfMono, color: QfColors.text),
            ),
          ],
          if (pHome != null) ...[
            const SizedBox(height: 12),
            ProbabilityBar(
              parts: nba
                  ? [(awayLabel, 1 - pHome), (homeLabel, pHome)]
                  : [
                      (_surname(event.home), pHome),
                      (_surname(event.away), 1 - pHome),
                    ],
            ),
          ],
          for (final (name, photo) in credits) ...[
            const SizedBox(height: 8),
            _Credit(name: name, photo: photo),
          ],
        ],
      ),
    );
  }
}

/// Crédito CC BY-SA de una foto mostrada: autor, licencia y página de origen.
class _Credit extends StatelessWidget {
  const _Credit({required this.name, required this.photo});
  final String name;
  final TennisPhoto photo;
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        context.l10n.sportPhotoCredit(name, photo.author, photo.license),
        style: const TextStyle(fontSize: 10, color: QfColors.muted),
      ),
      if (photo.page.isNotEmpty)
        Text(
          photo.page,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontSize: 10, color: QfColors.muted),
        ),
    ],
  );
}

// ---- Pronósticos -----------------------------------------------------------------------

class _Predictions extends StatelessWidget {
  const _Predictions({
    required this.api,
    required this.event,
    required this.images,
    required this.accent,
  });
  final QuantFutApi api;
  final SportEvent event;
  final ImageCatalog images;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    // Solo lo sellado antes del inicio es un pronóstico previo.
    final all = [
      for (final m in event.markets)
        if (m.eligible) m,
    ];
    if (all.isEmpty) return SportNote(l10n.detailNoPicks);
    int rank(SportMarket m) => m.player != null
        ? 2
        : (m.market == 'winner' || (m.market == null && m.id == 'winner'))
        ? 0
        : 1;
    final ordered = [...all]..sort((a, b) => rank(a).compareTo(rank(b)));
    final featured = featuredMarket(event);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (featured != null) ...[
          QfCard(
            accent: accent,
            child: _MarketRow(
              api: api,
              market: featured,
              l10n: l10n,
              big: true,
            ),
          ),
          const SizedBox(height: 12),
        ],
        for (final m in ordered)
          if (!identical(m, featured))
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: QfCard(
                child: _MarketRow(api: api, market: m, l10n: l10n),
              ),
            ),
        const SizedBox(height: 8),
        SealLine(seal: event.seal, publishedAt: event.sealedAt),
      ],
    );
  }
}

class _MarketRow extends StatelessWidget {
  const _MarketRow({
    required this.api,
    required this.market,
    required this.l10n,
    this.big = false,
  });
  final QuantFutApi api;
  final SportMarket market;
  final AppLocalizations l10n;
  final bool big;

  @override
  Widget build(BuildContext context) {
    final m = market;
    final won = m.outcome == 'win', lost = m.outcome == 'loss';
    final id = m.playerId;
    return Row(
      children: [
        if (m.player != null && id != null) ...[
          QfAvatar(
            url: serverImageUrl(api, nbaPlayerPhoto(id)),
            name: m.player!,
            size: 36,
            shape: AvatarShape.circle,
          ),
          const SizedBox(width: 10),
        ],
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                m.label,
                style: const TextStyle(fontSize: 11, color: QfColors.text2),
              ),
              const SizedBox(height: 2),
              Text(
                sportPickText(l10n, m),
                style: TextStyle(
                  fontSize: big ? 16 : 14,
                  fontWeight: FontWeight.bold,
                  color: QfColors.success,
                ),
              ),
            ],
          ),
        ),
        if (won || lost) ...[
          Icon(
            won ? Icons.check_circle : Icons.cancel,
            size: 18,
            color: won ? QfColors.success : QfColors.danger,
          ),
          const SizedBox(width: 8),
        ],
        Text(
          realPercent(m.probability),
          style: TextStyle(
            fontFamily: qfMono,
            fontSize: big ? 20 : 16,
            color: QfColors.primary,
          ),
        ),
      ],
    );
  }
}
