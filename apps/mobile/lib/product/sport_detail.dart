// Ficha de partido de NBA y tenis (hoja inferior): Pronósticos, Análisis, H2H y Alertas.
// Los feeds son públicos: sin candado VIP ni desbloqueo con monedas, y la cuota es solo de referencia (overlay fuera del sello).
import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import 'home_sport.dart';
import 'live_api.dart';
import 'live_widgets.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';
import 'quote_label.dart';
import 'screen_definition.dart';
import 'sport_contract.dart';
import 'sport_detail_tabs.dart';
import 'sport_images.dart';
import 'sport_screen_blocks.dart';
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
  VoidCallback? onVip,
}) => showModalBottomSheet<void>(
  context: context,
  isScrollControlled: true,
  backgroundColor: QfColors.bg,
  useSafeArea: true,
  builder: (_) => FractionallySizedBox(
    heightFactor: .96,
    child: Theme(
      data: liveTheme(),
      // Un deporte del catálogo sin pantalla propia (llegó por el contrato) usa la ficha genérica.
      child: event.generic
          ? GenericSportDetail(api: api, event: event, images: images, onVip: onVip)
          : SportDetail(api: api, event: event, images: images, quotes: quotes),
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
  bool get nba => e.sport == kNba;
  Color get accent => sportCatalog.spec(e.sport).accent;

  /// Estadísticas públicas del partido; cualquier fallo (404 incluido) es «no hay».
  Future<JsonMap?> _loadStats() async {
    try {
      final path = nba
          ? '/nba/v1/partido/${Uri.encodeComponent(e.id)}/estadisticas'
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
                    quotes: widget.quotes,
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
    final nba = event.sport == kNba;
    final accent = sportCatalog.spec(event.sport).accent;
    final pHome = _homeWinProbability(event);
    final homeCode = nba ? nbaTricode(event.home) : null;
    final awayCode = nba ? nbaTricode(event.away) : null;
    final homeLabel = homeCode ?? event.home;
    final awayLabel = awayCode ?? event.away;
    final surface = event.surface;
    final credits = <(String, TennisPhoto)>[];
    if (!nba && !event.generic) {
      for (final name in [event.home, event.away]) {
        final p = images.tennisPhoto(name);
        if (p != null) credits.add((name, p));
      }
    }
    Widget side(String name) => Expanded(
      child: Column(
        children: [
          eventAvatar(api, images, event, name, size: nba ? 48 : 56),
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
    required this.quotes,
  });
  final QuantFutApi api;
  final SportEvent event;
  final ImageCatalog images;
  final Color accent;
  final QuotesOverlay quotes;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    // Solo lo sellado antes del inicio es un pronóstico previo.
    final all = [
      for (final m in event.markets)
        if (m.eligible) m,
    ];
    if (all.isEmpty) {
      return event.sport == kNba && event.markets.isEmpty
          ? _SealCard(event: event, accent: accent)
          : SportNote(l10n.detailNoPicks);
    }
    int rank(SportMarket m) => m.player != null
        ? 2
        : (m.market == 'winner' || (m.market == null && m.id == 'winner'))
        ? 0
        : 1;
    final ordered = [...all]
      ..sort((a, b) {
        final r = rank(a).compareTo(rank(b));
        return r != 0 ? r : b.probability.compareTo(a.probability);
      });
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
              quote: quoteFor(event, featured, quotes),
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
                child: _MarketRow(
                  api: api,
                  market: m,
                  quote: quoteFor(event, m, quotes),
                  l10n: l10n,
                ),
              ),
            ),
        const SizedBox(height: 4),
        const QuoteReferenceCaption(),
        const SizedBox(height: 8),
        SealLine(seal: event.seal, publishedAt: event.sealedAt),
      ],
    );
  }
}

/// Cuándo se agrega el pronóstico de un partido de NBA que aún no tiene (o empezó sin él).
class _SealCard extends StatelessWidget {
  const _SealCard({required this.event, required this.accent});
  final SportEvent event;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final now = DateTime.now();
    final started = !event.start.toLocal().isAfter(now) || event.status == 'finished';
    final planned = event.plannedSeal;
    final (title, body) = started
        ? (l10n.nbaSealMissedTitle, l10n.nbaSealMissedBody)
        : (
            l10n.nbaSealPendingTitle,
            planned == null ? l10n.nbaSealPendingSoon : l10n.nbaSealPendingBody(kickoffText(planned)),
          );
    return QfCard(
      accent: accent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            l10n.nbaSealHeading,
            style: const TextStyle(fontFamily: qfMono, fontSize: 11, letterSpacing: .8, color: QfColors.primary),
          ),
          const SizedBox(height: 6),
          Text(
            title,
            style: const TextStyle(
              fontFamily: qfDisplay,
              fontWeight: FontWeight.w700,
              fontSize: 18,
              color: QfColors.text,
            ),
          ),
          const SizedBox(height: 6),
          Text(body, style: const TextStyle(fontSize: 13, color: QfColors.text2)),
        ],
      ),
    );
  }
}

class _MarketRow extends StatelessWidget {
  const _MarketRow({
    required this.api,
    required this.market,
    required this.quote,
    required this.l10n,
    this.big = false,
    this.title,
  });
  final QuantFutApi api;
  final SportMarket market;

  /// Título de la familia ya resuelto (deportes del catálogo sin pantalla propia); null = el de siempre.
  final String? title;
  final SportQuote? quote;
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
              if (title != '') ...[
                Text(
                  title ??
                      sportFamilyTitle(
                        l10n,
                        m.market ?? m.id.split('-').first,
                        fallback: m.label,
                      ),
                  style: const TextStyle(fontSize: 11, color: QfColors.text2),
                ),
                const SizedBox(height: 2),
              ],
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
        Column(
          crossAxisAlignment: CrossAxisAlignment.end,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              realPercent(m.probability),
              style: TextStyle(
                fontFamily: qfMono,
                fontSize: big ? 20 : 16,
                color: QfColors.primary,
              ),
            ),
            const SizedBox(height: 4),
            QuoteLabel(quote: quote),
          ],
        ),
      ],
    );
  }
}

// ---- Ficha genérica (deportes del catálogo sin pantalla propia) -------------------------------

/// Secciones de la pantalla `partido` que la ficha genérica sabe pintar (`estadisticas`, `h2h` y `alertas` solo
/// existen para NBA y tenis y se ignoran aquí).
const genericMatchSections = {'cabecera', 'pronostico', 'mercados', 'contenido', 'sello'};

typedef ContractDetailLoader = Future<ContractDetail> Function(SportEvent event, String lang);

/// Ficha de un partido de un deporte del catálogo: cabecera, pronóstico, mercados por familia, bloques de contenido y
/// sello, en el orden y con la visibilidad de la pantalla `partido` (sin definición, el orden de hoy). Reutiliza
/// [_Header], [_MarketRow], [SportNote] y [SealLine]; nada de lo atado a NBA o tenis (jugadores, pestañas de
/// estadísticas, H2H, alertas). El evento de la lista se pinta de inmediato y el detalle llega del contrato.
class GenericSportDetail extends StatefulWidget {
  const GenericSportDetail({
    super.key,
    required this.api,
    required this.event,
    required this.images,
    this.onVip,
    this.loader,
  });

  final QuantFutApi api;
  final SportEvent event;
  final ImageCatalog images;

  /// Abre los planes (bloque `vip`).
  final VoidCallback? onVip;

  /// Para pruebas: sustituye la lectura del contrato.
  final ContractDetailLoader? loader;

  @override
  State<GenericSportDetail> createState() => _GenericSportDetailState();
}

class _GenericSportDetailState extends State<GenericSportDetail> {
  Future<ContractDetail>? _detail;
  String? _lang;

  void _load(String lang) {
    _lang = lang;
    final loader = widget.loader;
    _detail = loader != null
        ? loader(widget.event, lang)
        : loadContractDetail(widget.api, widget.event.sport, widget.event.id, lang: lang);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    if (_lang != l10n.localeName) _load(l10n.localeName);
    final e = widget.event;
    final accent = sportCatalog.spec(e.sport).accent;
    final screen = effectiveScreen(sportCatalog.screens, 'partido', e.sport, defaultMatchSections, genericMatchSections);
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
            child: FutureBuilder<ContractDetail>(
              future: _detail,
              builder: (context, snap) {
                final done = snap.connectionState == ConnectionState.done;
                final detail = snap.data;
                final event = detail?.event ?? e;
                return ListView(
                  key: ValueKey('generic-detail-${e.sport}-${e.id}'),
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                  children: [
                    for (final block in screen)
                      ..._block(context, block, event, detail, accent, loading: !done, failed: done && snap.hasError),
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  List<Widget> _block(
    BuildContext context,
    ScreenBlock block,
    SportEvent event,
    ContractDetail? detail,
    Color accent, {
    required bool loading,
    required bool failed,
  }) {
    if (!block.isSection) {
      final extra = screenExtra(block, api: widget.api, onVip: widget.onVip);
      return extra == null ? const [] : [extra];
    }
    final l10n = context.l10n;
    final eligible = [for (final m in event.markets) if (m.eligible) m];
    switch (block.section) {
      case 'cabecera':
        return [_Header(api: widget.api, event: event, images: widget.images), const SizedBox(height: 16)];
      case 'pronostico':
        final featured = featuredMarket(event);
        if (eligible.isEmpty) {
          return loading ? const [] : [SportNote(l10n.detailNoPicks), const SizedBox(height: 12)];
        }
        final principals = [
          for (final m in eligible)
            if (m.principal && !identical(m, featured)) m,
        ];
        return [
          if (featured != null) ...[
            QfCard(
              accent: accent,
              child: _MarketRow(
                api: widget.api,
                market: featured,
                quote: quoteFor(event, featured, QuotesOverlay.empty),
                l10n: l10n,
                big: true,
                title: contractFamilyTitle(l10n, event.sport, featured.family ?? otherFamily),
              ),
            ),
            const SizedBox(height: 12),
          ],
          for (final m in principals)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: QfCard(
                child: _MarketRow(
                  api: widget.api,
                  market: m,
                  quote: quoteFor(event, m, QuotesOverlay.empty),
                  l10n: l10n,
                  title: contractFamilyTitle(l10n, event.sport, m.family ?? otherFamily),
                ),
              ),
            ),
        ];
      case 'mercados':
        if (loading) return const [Center(child: Padding(padding: EdgeInsets.all(24), child: CircularProgressIndicator()))];
        if (failed) return [_DetailError(onRetry: () => setState(() => _load(l10n.localeName)))];
        final families = detail?.families ?? contractFamilies(event.markets, catalogFamilyIds(event.sport));
        return [
          for (final f in families)
            if (f.markets.any((m) => m.eligible)) ...[
              Padding(
                padding: const EdgeInsets.fromLTRB(2, 8, 2, 6),
                child: Text(
                  contractFamilyTitle(l10n, event.sport, f.id).toUpperCase(),
                  key: ValueKey('generic-family-${f.id}'),
                  style: const TextStyle(
                    fontFamily: qfDisplay,
                    fontWeight: FontWeight.w700,
                    fontSize: 13,
                    letterSpacing: .8,
                    color: QfColors.text2,
                  ),
                ),
              ),
              for (final m in f.markets)
                if (m.eligible)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: QfCard(
                      child: _MarketRow(
                        api: widget.api,
                        market: m,
                        quote: quoteFor(event, m, QuotesOverlay.empty),
                        l10n: l10n,
                        title: '', // la familia ya está en el encabezado del grupo
                      ),
                    ),
                  ),
            ],
        ];
      case 'contenido':
        return [for (final b in detail?.blocks ?? const <ContentBlock>[]) SportContentBlock(b, key: ValueKey('content-${b.id}'))];
      case 'sello':
        if (event.seal.isEmpty) return const [];
        return [
          const SizedBox(height: 4),
          // El pie de «cuota de referencia» solo tiene sentido si algún mercado trae cuota.
          if (event.markets.any((m) => m.price != null)) ...[const QuoteReferenceCaption(), const SizedBox(height: 8)],
          SealLine(seal: event.seal, publishedAt: event.sealedAt),
          const SizedBox(height: 12),
        ];
    }
    return const [];
  }
}

/// Error del detalle con «Reintentar» (nunca una ficha en blanco).
class _DetailError extends StatelessWidget {
  const _DetailError({required this.onRetry});
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 16),
    child: Column(
      children: [
        const Icon(Icons.cloud_off, color: QfColors.muted, size: 32),
        const SizedBox(height: 8),
        Text(
          context.l10n.sportDetailError,
          textAlign: TextAlign.center,
          style: const TextStyle(color: QfColors.text2, fontSize: 14),
        ),
        const SizedBox(height: 12),
        FilledButton(
          key: const ValueKey('sport-detail-retry'),
          style: FilledButton.styleFrom(
            backgroundColor: QfColors.primary,
            foregroundColor: QfColors.onPrimary,
            minimumSize: const Size(120, 44),
          ),
          onPressed: onRetry,
          child: Text(context.l10n.commonRetry),
        ),
      ],
    ),
  );
}
