import 'dart:ui';

import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import '../l10n/pick_labels.dart' show lineText;
import 'live_api.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';
import 'quote_label.dart';
import 'sport_images.dart';
import 'sport_markets.dart' show orderSettledMarkets;
import 'sports_feed.dart';
import 'sports_quotes.dart';

/// Pestaña de Props de jugadores NBA: filtro por estadística (TODOS · PUNTOS · REBOTES · ASIST. · TRIPLES)
/// y lista de tarjetas de jugadores con foto, equipo, selección, barra de los últimos 5 y cuota/VIP.
class SportPropsTab extends StatefulWidget {
  const SportPropsTab({
    super.key,
    required this.api,
    required this.event,
    required this.quotes,
    this.images = ImageCatalog.empty,
    this.onVip,
    this.onUnlock,
  });

  final QuantFutApi api;
  final SportEvent event;
  final QuotesOverlay quotes;
  final ImageCatalog images;
  final VoidCallback? onVip;
  final VoidCallback? onUnlock;

  @override
  State<SportPropsTab> createState() => _SportPropsTabState();
}

class _SportPropsTabState extends State<SportPropsTab> {
  String _filter = 'all';

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final allProps = widget.event.markets.where((m) {
      if (!m.eligible) return false;
      return m.player != null ||
          m.market == 'player_points' ||
          m.market == 'player_rebounds' ||
          m.market == 'player_assists' ||
          m.market == 'player_threes';
    }).toList();

    final filtered = allProps.where((m) {
      return switch (_filter) {
        'points' => m.market == 'player_points',
        'rebounds' => m.market == 'player_rebounds',
        'assists' => m.market == 'player_assists',
        'threes' => m.market == 'player_threes',
        _ => true,
      };
    }).toList();

    // Antes del partido: mayor probabilidad primero. Al terminar: acertados primero (cuota alta → baja), luego el resto.
    final finished = widget.event.status == 'finished';
    double price(SportMarket m) =>
        quoteFor(widget.event, m, widget.quotes)?.price ?? m.price ?? 0;
    if (finished) {
      final ordered = orderSettledMarkets(List.of(filtered), price: price);
      filtered
        ..clear()
        ..addAll(ordered);
    } else {
      filtered.sort((a, b) => b.probability.compareTo(a.probability));
    }

    final filters = [
      ('all', l10n.commonAll.toUpperCase()),
      ('points', l10n.propsFilterPoints),
      ('rebounds', l10n.propsFilterRebounds),
      ('assists', l10n.propsFilterAssists),
      ('threes', l10n.propsFilterThrees),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Selector de estadística en chips
        SizedBox(
          height: 44,
          child: Row(
            children: [
              for (var i = 0; i < filters.length; i++) ...[
                if (i > 0) const SizedBox(width: 6),
                Expanded(
                  child: _FilterButton(
                    key: ValueKey('props-filter-${filters[i].$1}'),
                    label: filters[i].$2,
                    active: _filter == filters[i].$1,
                    onTap: () => setState(() => _filter = filters[i].$1),
                  ),
                ),
              ],
            ],
          ),
        ),
        const SizedBox(height: 12),
        if (filtered.isEmpty)
          QfCard(
            padding: const EdgeInsets.all(20),
            child: Center(
              child: Text(
                l10n.propsEmptyFilter,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontFamily: qfMono,
                  fontSize: 12,
                  color: QfColors.text2,
                ),
              ),
            ),
          )
        else
          for (final m in filtered)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: SportPropCard(
                key: ValueKey('sport-prop-${m.id}'),
                api: widget.api,
                event: widget.event,
                market: m,
                images: widget.images,
                quote: quoteFor(widget.event, m, widget.quotes),
                onVip: widget.onVip,
              ),
            ),
      ],
    );
  }
}

class _FilterButton extends StatelessWidget {
  const _FilterButton({
    super.key,
    required this.label,
    required this.active,
    required this.onTap,
  });

  final String label;
  final bool active;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(6),
      child: Container(
        height: 44,
        alignment: Alignment.center,
        padding: const EdgeInsets.symmetric(horizontal: 2),
        decoration: BoxDecoration(
          color: active ? QfColors.cyan.withValues(alpha: 0.1) : Colors.transparent,
          border: Border.all(
            color: active ? QfColors.cyan : QfColors.border,
            width: 1,
          ),
          borderRadius: BorderRadius.circular(6),
        ),
        child: FittedBox(
          fit: BoxFit.scaleDown,
          child: Text(
            label,
            maxLines: 1,
            style: TextStyle(
              fontFamily: qfMono,
              fontWeight: active ? FontWeight.w700 : FontWeight.w500,
              fontSize: 10,
              color: active ? QfColors.cyan : QfColors.text2,
            ),
          ),
        ),
      ),
    );
  }
}

class SportPropCard extends StatelessWidget {
  const SportPropCard({
    super.key,
    required this.api,
    required this.event,
    required this.market,
    required this.quote,
    this.images = ImageCatalog.empty,
    this.onVip,
  });

  final QuantFutApi api;
  final SportEvent event;
  final SportMarket market;
  final ImageCatalog images;
  final SportQuote? quote;
  final VoidCallback? onVip;

  Widget _teamBadge(String team) {
    final code = nbaTricode(team);
    final path = code == null
        ? null
        : (images.nbaLogo(code) ?? '/web/imagenes/nba/${code.toUpperCase()}.png');
    return Container(
      width: 20,
      height: 20,
      padding: const EdgeInsets.all(1.5),
      decoration: const BoxDecoration(
        color: QfColors.bg,
        shape: BoxShape.circle,
      ),
      child: QfAvatar(
        url: serverImageUrl(api, path),
        name: team,
        size: 18,
        shape: AvatarShape.contain,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final m = market;
    final playerName = m.player ?? m.selection;
    final team = m.team ??
        (event.home.toLowerCase().contains(playerName.toLowerCase())
            ? event.home
            : (event.away.toLowerCase().contains(playerName.toLowerCase())
                ? event.away
                : null));

    final statName = switch (m.market) {
      'player_points' => l10n.propStatPoints,
      'player_rebounds' => l10n.propStatRebounds,
      'player_assists' => l10n.propStatAssists,
      'player_threes' => l10n.propStatThrees,
      _ => '',
    };
    final statCap = statName.isNotEmpty
        ? '${statName[0].toUpperCase()}${statName.substring(1)}'
        : '';
    final lineStr = m.line != null
        ? (m.side == 'under'
            ? l10n.marketUnderLine(lineText(m.line!))
            : l10n.marketOverLine(lineText(m.line!)))
        : m.selection;
    final selText = statCap.isNotEmpty ? '$statCap · $lineStr' : lineStr;

    final isLocked = m.locked;

    return InkWell(
      onTap: isLocked ? onVip : null,
      borderRadius: BorderRadius.circular(8),
      child: QfCard(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            // Foto redonda 52 dp con logo del equipo (20 dp) en la esquina
            SizedBox(
              width: 52,
              height: 52,
              child: Stack(
                clipBehavior: Clip.none,
                children: [
                  QfAvatar(
                    url: serverImageUrl(api, nbaPlayerPhoto(m.photoId ?? '')),
                    name: playerName,
                    size: 52,
                    shape: AvatarShape.circle,
                    ring: QfColors.border,
                  ),
                  if (team != null && team.isNotEmpty)
                    Positioned(
                      right: -3,
                      bottom: -3,
                      child: _teamBadge(team),
                    ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            // Centro: Nombre + Selección + Barra últimos 5 (si existe)
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    playerName,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontFamily: qfDisplay,
                      fontWeight: FontWeight.w700,
                      fontSize: 15,
                      height: 1.2,
                      color: QfColors.text,
                    ),
                  ),
                  const SizedBox(height: 2),
                  if (isLocked)
                    ImageFiltered(
                      imageFilter: ImageFilter.blur(sigmaX: 5, sigmaY: 5),
                      child: Text(
                        selText,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontFamily: qfDisplay,
                          fontWeight: FontWeight.w700,
                          fontSize: 16,
                          color: QfColors.primary,
                        ),
                      ),
                    )
                  else
                    Text(
                      selText,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontFamily: qfDisplay,
                        fontWeight: FontWeight.w700,
                        fontSize: 16,
                        color: QfColors.primary,
                      ),
                    ),
                  if (m.last5 != null) ...[
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        for (var i = 0; i < 5; i++) ...[
                          if (i > 0) const SizedBox(width: 2.5),
                          Container(
                            width: 8,
                            height: 6,
                            decoration: BoxDecoration(
                              color: i < m.last5!
                                  ? QfColors.primary
                                  : const Color(0xFF2A2D3A),
                              borderRadius: BorderRadius.circular(1),
                            ),
                          ),
                        ],
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            l10n.propsLastFive(m.last5!),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontFamily: qfMono,
                              fontSize: 10,
                              color: QfColors.text2,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(width: 10),
            // Derecha: Probabilidad / VIP + cuota / "con monedas o VIP"
            if (isLocked)
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text(
                    'VIP',
                    style: TextStyle(
                      fontFamily: qfMono,
                      fontWeight: FontWeight.w700,
                      fontSize: 20,
                      height: 1.2,
                      color: QfColors.yellow,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    l10n.detailLockedWithCoinsOrVip,
                    style: const TextStyle(
                      fontFamily: qfMono,
                      fontSize: 10,
                      color: QfColors.text2,
                    ),
                  ),
                ],
              )
            else
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    realPercent(m.probability),
                    style: const TextStyle(
                      fontFamily: qfMono,
                      fontWeight: FontWeight.w700,
                      fontSize: 20,
                      height: 1.2,
                      color: QfColors.cyan,
                    ),
                  ),
                  const SizedBox(height: 4),
                  QuoteLabel(quote: quote),
                  if (m.outcome != null) ...[
                    const SizedBox(height: 4),
                    Text(
                      switch (m.outcome) {
                        'win' => l10n.outcomeWin,
                        'loss' => l10n.outcomeLoss,
                        _ => l10n.outcomePush,
                      },
                      key: const ValueKey('prop-outcome'),
                      style: TextStyle(
                        fontFamily: qfMono,
                        fontWeight: FontWeight.w700,
                        fontSize: 11,
                        color: switch (m.outcome) {
                          'win' => QfColors.primary,
                          'loss' => QfColors.danger,
                          _ => QfColors.text2,
                        },
                      ),
                    ),
                  ],
                ],
              ),
          ],
        ),
      ),
    );
  }
}
