// Ficha de partido de NBA y tenis (hoja inferior): Pronósticos, Análisis, H2H y Alertas.
// Los feeds son públicos: sin candado VIP ni desbloqueo con monedas, y la cuota es solo de referencia (overlay fuera del sello).
import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import 'home_sport.dart';
import 'live_api.dart';
import 'live_widgets.dart';
import 'match_shell.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';
import 'quote_label.dart';
import 'screen_definition.dart';
import 'sport_contract.dart';
import 'sport_detail_tabs.dart';
import 'sport_forecast.dart';
import 'sport_images.dart';
import 'sport_props.dart';
import 'sport_screen_blocks.dart';
import 'sports.dart';
import 'sports_feed.dart';
import 'sport_vip_notice.dart';
import 'sports_quotes.dart';

/// Abre la ficha del partido como hoja inferior (misma forma que la de fútbol).
Future<void> showSportDetail(
  BuildContext context, {
  required QuantFutApi api,
  required SportEvent event,
  required ImageCatalog images,
  QuotesOverlay quotes = QuotesOverlay.empty,
  VoidCallback? onVip,
  VoidCallback? onUnlock,
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
          : SportDetail(
              api: api,
              event: event,
              images: images,
              quotes: quotes,
              onVip: onVip,
              onUnlock: onUnlock,
            ),
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
    this.onVip,
    this.onUnlock,
  });
  final QuantFutApi api;
  final SportEvent event;
  final ImageCatalog images;

  /// Cuotas de referencia del deporte; vacías si no llegaron.
  final QuotesOverlay quotes;
  final VoidCallback? onVip;
  final VoidCallback? onUnlock;
  @override
  State<SportDetail> createState() => _SportDetailState();
}

class _SportDetailState extends State<SportDetail> {
  int tab = 0;
  late final Future<JsonMap?> stats;

  /// Casillas y resumen del destacado (`/web/deportes/{tenis,nba}/analisis/{id}`); null en los deportes sin él.
  late final Future<JsonMap?>? analysis;
  Future<JsonMap?>? _availability;
  Future<JsonMap?> get availability => _availability ??= _loadAvailability();

  @override
  void initState() {
    super.initState();
    stats = _loadStats();
    analysis = e.generic ? null : _loadAnalysis();
  }

  /// Cualquier fallo (404 incluido) es «sin análisis»: se queda la tarjeta compacta de siempre.
  Future<JsonMap?> _loadAnalysis() async {
    try {
      final r = await widget.api.request(
        '/web/deportes/${nba ? 'nba' : 'tenis'}/analisis/${Uri.encodeComponent(e.id)}',
      );
      return r is Map<String, dynamic> ? r : null;
    } catch (_) {
      return null;
    }
  }

  SportEvent get e => widget.event;
  bool get nba => e.sport == kNba;
  Color get accent => sportCatalog.spec(e.sport).accent;

  /// Disponibilidad oficial NBA (lesiones, suspensiones y PDF de la liga).
  Future<JsonMap?> _loadAvailability() async {
    if (!nba) return null;
    try {
      final path =
          '/nba/v1/partido/${Uri.encodeComponent(e.id)}/disponibilidad';
      final r = await widget.api.request(path);
      return r is Map<String, dynamic> ? r : null;
    } catch (_) {
      return null;
    }
  }

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
    final labels = nba
        ? [
            l10n.detailTabPredictions,
            l10n.detailTabProps,
            l10n.detailTabStats,
            l10n.detailTabH2h,
            l10n.detailTabAlerts,
          ]
        : [
            l10n.detailTabPredictions,
            l10n.detailTabStats,
            l10n.detailTabH2h,
            l10n.detailTabAlerts,
          ];

    Widget body() {
      if (nba) {
        return switch (tab) {
          0 => _Predictions(
            api: widget.api,
            event: e,
            images: widget.images,
            accent: accent,
            quotes: widget.quotes,
            analysis: analysis,
            onVip: widget.onVip,
          ),
          1 => SportPropsTab(
            api: widget.api,
            event: e,
            images: widget.images,
            quotes: widget.quotes,
            onVip: widget.onVip,
            onUnlock: widget.onUnlock,
          ),
          2 => SportAnalysis(
            stats: stats,
            event: e,
            api: widget.api,
            images: widget.images,
            onH2h: () => setState(() => tab = 3),
          ),
          3 => SportH2h(
            stats: stats,
            event: e,
            api: widget.api,
            images: widget.images,
          ),
          _ => SportAlerts(
            event: e,
            availability: availability,
            api: widget.api,
            images: widget.images,
          ),
        };
      }
      return switch (tab) {
        0 => _Predictions(
          api: widget.api,
          event: e,
          images: widget.images,
          accent: accent,
          quotes: widget.quotes,
          analysis: analysis,
          onVip: widget.onVip,
        ),
        1 => SportAnalysis(
          stats: stats,
          event: e,
          api: widget.api,
          images: widget.images,
          onH2h: () => setState(() => tab = 2),
        ),
        2 => SportH2h(
          stats: stats,
          event: e,
          api: widget.api,
          images: widget.images,
        ),
        _ => SportAlerts(
          event: e,
          availability: availability,
          api: widget.api,
          images: widget.images,
        ),
      };
    }

    return MatchShell(
      header: MatchTopBar(
        league: e.league,
        when: kickoffText(e.start),
        onClose: () => Navigator.maybePop(context),
      ),
      hero: _Header(api: widget.api, event: e, images: widget.images),
      tabs: MatchTabs(
        labels: labels,
        index: tab,
        onChanged: (i) => setState(() => tab = i),
      ),
      body: body(),
      bottomBar: widget.onVip != null || widget.onUnlock != null
          ? MatchBottomBar(
              cost: 40,
              onUnlock: widget.onUnlock,
              onVip: widget.onVip,
            )
          : null,
    );
  }
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
    final score = event.score;

    String? bigProb;
    String? bigLabel;
    List<MatchProbabilityPart>? probParts;
    if (pHome != null) {
      if (nba) {
        final favHome = pHome >= 0.5;
        final favLabel = favHome ? homeLabel : awayLabel;
        final p = favHome ? pHome : (1 - pHome);
        bigProb = '${(p * 100).round()}%';
        bigLabel = l10n.selHomeWins(favLabel);
        probParts = [
          MatchProbabilityPart(
            label: awayLabel,
            percent: (1 - pHome) * 100,
            color: (1 - pHome) >= pHome ? QfColors.cyan : const Color(0xFF747D99),
          ),
          MatchProbabilityPart(
            label: homeLabel,
            percent: pHome * 100,
            color: pHome >= (1 - pHome) ? QfColors.cyan : const Color(0xFF747D99),
          ),
        ];
      } else {
        final favHome = pHome >= 0.5;
        final favSurname = _surname(favHome ? event.home : event.away);
        final p = favHome ? pHome : (1 - pHome);
        bigProb = '${(p * 100).round()}%';
        bigLabel = l10n.selHomeWins(favSurname);
        probParts = [
          MatchProbabilityPart(
            label: _surname(event.home).toUpperCase(),
            percent: pHome * 100,
            color: pHome >= (1 - pHome) ? QfColors.cyan : const Color(0xFF747D99),
          ),
          MatchProbabilityPart(
            label: _surname(event.away).toUpperCase(),
            percent: (1 - pHome) * 100,
            color: (1 - pHome) >= pHome ? QfColors.cyan : const Color(0xFF747D99),
          ),
        ];
      }
    }

    Widget? centerExtra;
    if (nba) {
      centerExtra = Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            '$awayLabel @ $homeLabel',
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontFamily: qfMono,
              fontSize: 13,
              color: QfColors.text2,
            ),
          ),
          if (score != null) ...[
            const SizedBox(height: 4),
            Text(
              score,
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontFamily: qfMono,
                fontWeight: FontWeight.bold,
                fontSize: 14,
                color: QfColors.text,
              ),
            ),
          ],
        ],
      );
    } else if (score != null) {
      centerExtra = Text(
        score,
        textAlign: TextAlign.center,
        style: const TextStyle(
          fontFamily: qfMono,
          fontWeight: FontWeight.bold,
          fontSize: 14,
          color: QfColors.text,
        ),
      );
    }

    final badges = [
      QfBadge(event.league, color: accent),
      if (!nba && surface != null && _surfaceLabel(l10n, surface) != null)
        QfBadge(_surfaceLabel(l10n, surface)!.toUpperCase(), color: QfColors.text2),
    ];

    final sideAName = nba ? awayLabel : event.home;
    final sideBName = nba ? homeLabel : event.away;

    return MatchHero(
      sideA: MatchHeroSide(
        name: sideAName,
        image: eventAvatar(api, images, event, nba ? event.away : event.home, size: 58),
        sub: nba
            ? (event.availability?['away_record'] as String? ?? 'VISITANTE')
            : (event.surface != null ? _surfaceLabel(l10n, event.surface!) : null),
      ),
      sideB: MatchHeroSide(
        name: sideBName,
        image: eventAvatar(api, images, event, nba ? event.home : event.away, size: 58),
        sub: nba ? (event.availability?['home_record'] as String? ?? 'LOCAL') : null,
      ),
      bigProb: bigProb,
      bigLabel: bigLabel,
      centerExtra: centerExtra,
      probs: probParts,
      badges: badges,
      credits: [
        for (final (name, photo) in credits)
          _Credit(name: name, photo: photo),
      ],
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
    this.analysis,
    this.onVip,
  });
  final VoidCallback? onVip;
  final QuantFutApi api;
  final SportEvent event;
  final ImageCatalog images;
  final Color accent;
  final QuotesOverlay quotes;
  final Future<JsonMap?>? analysis;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    // Solo lo sellado antes del inicio es un pronóstico previo.
    final all = [
      for (final m in event.markets)
        if (m.eligible) m,
    ];
    if (all.isEmpty && event.vipCount == 0) {
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
          _FeaturedSlot(
            api: api,
            event: event,
            market: featured,
            quote: quoteFor(event, featured, quotes),
            l10n: l10n,
            analysis: analysis,
          ),
          const SizedBox(height: 12),
        ],
        SportVipNotice(event: event),
        Text(
          l10n.detailModelMarkets,
          style: const TextStyle(
            fontFamily: qfDisplay,
            fontWeight: FontWeight.w700,
            fontSize: 13,
            letterSpacing: 1.4,
            color: QfColors.text,
          ),
        ),
        const SizedBox(height: 8),
        for (final m in ordered)
          if (!identical(m, featured))
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: QfCard(
                child: _MarketRow(
                  api: api,
                  event: event,
                  images: images,
                  market: m,
                  quote: quoteFor(event, m, quotes),
                  l10n: l10n,
                ),
              ),
            ),
        for (final f in event.vipFamilies.entries)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: SportLockedFamilyRow(family: f.key, count: f.value, onVip: onVip),
          ),
        const SizedBox(height: 4),
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

/// El destacado: la tarjeta de análisis (tenis) si el servidor mandó casillas para ESE mercado; si no, la compacta.
class _FeaturedSlot extends StatelessWidget {
  const _FeaturedSlot({
    required this.api,
    required this.event,
    required this.market,
    required this.quote,
    required this.l10n,
    required this.analysis,
  });

  final QuantFutApi api;
  final SportEvent event;
  final SportMarket market;
  final SportQuote? quote;
  final AppLocalizations l10n;
  final Future<JsonMap?>? analysis;

  @override
  Widget build(BuildContext context) {
    final compact = _FeaturedCard(
      api: api,
      event: event,
      market: market,
      quote: quote,
      l10n: l10n,
    );
    final pending = analysis;
    if (pending == null) return compact;
    return FutureBuilder<JsonMap?>(
      future: pending,
      builder: (context, snap) {
        final data = snap.data;
        if (data == null || '${data['mercado_id']}' != market.id) {
          return compact;
        }
        return SportForecastPanel(
          nba: event.sport == kNba,
          analisis: data,
          pickText: sportPickText(l10n, market),
          probability: market.probability,
          quote: QuoteLabel(quote: quote),
          home: event.home,
          away: event.away,
        );
      },
    );
  }
}

class _FeaturedCard extends StatelessWidget {
  const _FeaturedCard({
    required this.api,
    required this.event,
    required this.market,
    required this.quote,
    required this.l10n,
  });

  final QuantFutApi api;
  final SportEvent event;
  final SportMarket market;
  final SportQuote? quote;
  final AppLocalizations l10n;

  @override
  Widget build(BuildContext context) {
    final m = market;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: const ShapeDecoration(
        color: Color.fromRGBO(5, 255, 161, 0.06),
        shape: CutCornerBorder(
          cut: 10,
          side: BorderSide(
            color: Color.fromRGBO(5, 255, 161, 0.4),
            width: 1,
          ),
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  l10n.detailFeaturedPickFree,
                  style: const TextStyle(
                    fontFamily: qfDisplay,
                    fontWeight: FontWeight.w700,
                    fontSize: 11,
                    letterSpacing: 1.4,
                    color: QfColors.primary,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  sportPickText(l10n, m),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontFamily: qfDisplay,
                    fontWeight: FontWeight.w700,
                    fontSize: 20,
                    color: QfColors.text,
                  ),
                ),
                const SizedBox(height: 4),
                QuoteLabel(quote: quote),
              ],
            ),
          ),
          const SizedBox(width: 10),
          Text(
            realPercent(m.probability),
            style: const TextStyle(
              fontFamily: qfMono,
              fontWeight: FontWeight.w700,
              fontSize: 30,
              color: QfColors.primary,
            ),
          ),
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
    this.event,
    this.images,
    this.big = false,
    this.title,
  });
  final QuantFutApi api;
  final SportEvent? event;
  final ImageCatalog? images;
  final SportMarket market;

  /// Título de la familia ya resuelto (deportes del catálogo sin pantalla propia); null = el de siempre.
  final String? title;
  final SportQuote? quote;
  final AppLocalizations l10n;
  final bool big;

  Widget _teamLogo(String name, double size) {
    final ev = event;
    if (ev != null && ev.sport == kNba) {
      final code = nbaTricode(name);
      final path = code == null ? null : (images?.nbaLogo(code) ?? '/web/imagenes/nba/${code.toUpperCase()}.png');
      return QfAvatar(url: serverImageUrl(api, path), name: name, size: size, shape: AvatarShape.contain);
    }
    return QfAvatar(
      url: serverImageUrl(api, images?.tennisPhoto(name)?.path),
      name: name,
      size: size,
      shape: AvatarShape.circle,
    );
  }

  @override
  Widget build(BuildContext context) {
    final m = market;
    final won = m.outcome == 'win', lost = m.outcome == 'loss';
    final id = m.playerId;
    final ev = event;
    return Row(
      children: [
        if (m.player != null && id != null) ...[
          QfAvatar(
            url: serverImageUrl(api, nbaPlayerPhoto(m.photoId ?? '')),
            name: m.player!,
            size: 36,
            shape: AvatarShape.circle,
          ),
          const SizedBox(width: 10),
        ] else if (ev != null && ev.home.isNotEmpty) ...[
          if (m.market == 'winner' || m.id == 'winner')
            _teamLogo(m.selection, 30)
          else
            SizedBox(
              width: 44,
              height: 30,
              child: Stack(
                children: [
                  _teamLogo(ev.home, 28),
                  Positioned(
                    left: 16,
                    child: _teamLogo(ev.away, 28),
                  ),
                ],
              ),
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
                // El detalle trae TODOS los mercados: pasan por el mismo acceso que el partido tenía en la cartelera.
                final event = detail == null ? e : applyAccess(detail.event, e.access);
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
          if (event.featuredVip || event.vipCount > 0) return [SportVipNotice(event: event)];
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
          SportVipNotice(event: event),
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
