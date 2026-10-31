import 'package:flutter/material.dart';

import 'package:url_launcher/url_launcher.dart';

import '../core/meta_events.dart';
import '../l10n/app_locale.dart';
import 'live_api.dart';
import 'live_widgets.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';
import 'sport_markets.dart';
import 'sports.dart';
import 'sports_feed.dart';
import 'store_purchases.dart';

/// Pantalla de acceso VIP. Planes, precios, aciertos y permisos salen del
/// servidor; no hay cifras de miembros, reseñas ni periodos de prueba porque
/// el backend no los entrega.
class LiveVipScreen extends StatefulWidget {
  const LiveVipScreen({
    super.key,
    required this.api,
    required this.data,
    this.store,
    this.sportFeeds = const {},
  });
  final QuantFutApi api;
  final JsonMap data;
  final StoreController? store;

  /// Feeds de NBA y tenis ya cargados por el shell: de ahí sale su acierto (sin pedir nada).
  final Map<SportKind, SportFeed> sportFeeds;
  @override
  State<LiveVipScreen> createState() => _LiveVipScreenState();
}

class _LiveVipScreenState extends State<LiveVipScreen> {
  int? chosen;

  @override
  void initState() {
    super.initState();
    MetaEvents.current?.viewVip();
    final store = widget.store;
    if (store != null) {
      store.addListener(_storeChanged);
      // load() notifica enseguida: no puede ejecutarse dentro de initState (usa el contexto).
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) store.load(jsonRows(widget.data['plans']).take(3).toList());
      });
    }
  }

  @override
  void dispose() {
    widget.store?.removeListener(_storeChanged);
    super.dispose();
  }

  void _storeChanged() {
    if (!mounted) return;
    final l10n = context.l10n, s = widget.store!;
    final text = switch (s.state) {
      StoreState.pending => l10n.vipPending,
      StoreState.granted => l10n.vipGranted,
      StoreState.failed => s.error ?? l10n.vipStoreFailed,
      StoreState.manage => l10n.vipManage,
      _ => null,
    };
    if (text != null) liveNotice(context, text);
    if (s.state == StoreState.manage) {
      launchUrl(
        manageSubscriptionsUri(ios: s.ios),
        mode: LaunchMode.externalApplication,
      );
    }
    setState(() {});
  }

  Future<void> checkAccess() async {
    if (!widget.api.signedIn) {
      liveNotice(context, context.l10n.vipCheckSignIn);
      return;
    }
    try {
      await widget.api.updateAccount();
      if (mounted) {
        liveNotice(
          context,
          widget.api.plus ? context.l10n.vipActive : context.l10n.vipFreeAccess,
        );
        setState(() {});
      }
    } catch (e) {
      if (mounted) liveNotice(context, '$e');
    }
  }

  static double? _monthly(JsonMap plan) {
    final cents = plan['price_cents'], days = plan['duration_days'];
    return cents is num && days is num && days > 0
        ? cents / 100 / (days / 30)
        : null;
  }

  static String _price(JsonMap plan) =>
      '\$${decimalText((plan['price_cents'] as num?) == null ? null : (plan['price_cents'] as num) / 100)}';

  static String _period(JsonMap plan) {
    final l10n = AppLocale.instance.l10n;
    final days = plan['duration_days'];
    if (days is! num) return l10n.vipNoExpiry;
    final months = (days / 30).round();
    return days % 30 == 0 && months >= 1
        ? l10n.vipMonths(months)
        : l10n.vipDays(days.toInt());
  }

  /// Aciertos y resueltos de un feed listo; null si no cargó, falló o no hay resueltos.
  static ({int won, int resolved})? _feedRate(SportFeed? feed) {
    if (feed == null || !feed.ready) return null;
    var won = 0, resolved = 0;
    for (final r in hitRateByFamily(feed.events).values) {
      won += r.won;
      resolved += r.resolved;
    }
    return resolved == 0 ? null : (won: won, resolved: resolved);
  }

  /// Tarjeta pequeña con el acento del deporte y la cifra en azul (o «—» sin datos).
  Widget _sportCard(SportKind sport, String value, String? count) {
    final spec = sportSpecs[sport]!;
    return Expanded(
      child: QfCard(
        key: ValueKey('vip-sport-${sport.id}'),
        accent: spec.accent,
        padding: const EdgeInsets.all(10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              spec.label(context.l10n),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 11, color: QfColors.text2),
            ),
            FittedBox(
              fit: BoxFit.scaleDown,
              alignment: Alignment.centerLeft,
              child: Text(
                value,
                style: const TextStyle(fontFamily: qfMono, fontSize: 20, color: QfColors.primary),
              ),
            ),
            if (count != null)
              Text(count, style: const TextStyle(fontFamily: qfMono, fontSize: 11, color: QfColors.muted)),
          ],
        ),
      ),
    );
  }

  Widget _benefit(IconData icon, String title, String detail) => Container(
    padding: const EdgeInsets.symmetric(vertical: 9),
    decoration: const BoxDecoration(border: Border(top: BorderSide(color: QfColors.border))),
    child: Row(
      children: [
        Icon(icon, color: QfColors.primary, size: 20),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              liveText(title, bold: true, size: 14, color: QfColors.text),
              const SizedBox(height: 2),
              liveText(detail, size: 12, color: QfColors.text2),
            ],
          ),
        ),
        const Icon(Icons.check, color: QfColors.primary, size: 18),
      ],
    ),
  );

  Widget _plan(
    int index,
    JsonMap plan,
    bool selected,
    bool best,
    VoidCallback onTap,
    double? monthly,
  ) {
    final l10n = AppLocale.instance.l10n;
    final side = best
        ? BorderSide(color: QfColors.cta, width: selected ? 2 : 1.5)
        : selected
        ? const BorderSide(color: QfColors.primary, width: 2)
        : const BorderSide(color: QfColors.border);
    return Expanded(
      child: Semantics(
        button: true,
        selected: selected,
        child: Material(
          key: ValueKey(best ? 'vip-plan-best' : 'vip-plan-$index'),
          color: selected ? QfColors.surface2 : QfColors.surface,
          shape: CutCornerBorder(side: side),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: onTap,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(8, 12, 8, 12),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    best ? l10n.vipBestPrice : _period(plan).toUpperCase(),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontFamily: qfDisplay,
                      fontWeight: FontWeight.w700,
                      fontSize: 11,
                      color: best ? QfColors.cta : QfColors.text2,
                    ),
                  ),
                  const SizedBox(height: 10),
                  FittedBox(
                    fit: BoxFit.scaleDown,
                    child: Text(
                      widget.store?.byPlan[plan['plan_code']]?.price ?? _price(plan),
                      style: const TextStyle(fontFamily: qfMono, fontSize: 19, color: QfColors.text),
                    ),
                  ),
                  if (widget.store?.byPlan[plan['plan_code']] == null)
                    liveText('${plan['currency'] ?? ''}', size: 10, color: QfColors.text2),
                  const SizedBox(height: 6),
                  if (best) liveText(_period(plan), size: 11, color: QfColors.text2),
                  if (monthly != null)
                    liveText(
                      l10n.vipMonthly('\$${decimalText(monthly)}'),
                      size: 11,
                      color: QfColors.text2,
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final plans = jsonRows(widget.data['plans']);
    final history = jsonMap(
      jsonMap(widget.data['alta_probabilidad'])['historial'],
    );
    final config = jsonMap(widget.data['config']);
    final shown = plans.take(3).toList();
    final monthlies = shown.map(_monthly).toList();
    final bestIndex = shown.length > 1
        ? monthlies.indexOf(
            monthlies.whereType<double>().fold<double?>(
              null,
              (m, v) => m == null || v < m ? v : m,
            ),
          )
        : -1;
    final selected = chosen ?? (bestIndex >= 0 ? bestIndex : 0);
    final purchases = featureEnabled(widget.data, 'compras');
    final store = widget.store;
    final canBuy = purchases && store != null && store.byPlan.isNotEmpty;
    final verifying = store?.state == StoreState.verifying;
    final min = ((config['probability_min'] as num?) ?? .73) * 100;
    final max = ((config['probability_max'] as num?) ?? .95) * 100;
    final real = history['acierto_real'];
    final nba = _feedRate(widget.sportFeeds[SportKind.nba]);
    final tennis = _feedRate(widget.sportFeeds[SportKind.tennis]);
    String? count(({int won, int resolved})? r) => r == null ? null : '${r.won}/${r.resolved}';
    String rate(({int won, int resolved})? r) =>
        r == null ? '—' : percentText(r.won * 100 / r.resolved);
    return Scaffold(
      backgroundColor: QfColors.bg,
      body: SafeArea(
        child: Stack(
          children: [
            ListView(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
              children: [
                Align(
                  alignment: Alignment.centerLeft,
                  child: QfBadge(l10n.vipBadge, color: QfColors.cta),
                ),
                const SizedBox(height: 12),
                const Text(
                  'QuantFut VIP',
                  style: TextStyle(
                    fontFamily: qfDisplay,
                    fontWeight: FontWeight.w700,
                    fontSize: 28,
                    color: QfColors.text,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  l10n.vipIntro,
                  style: const TextStyle(fontSize: 14, color: QfColors.text2, height: 1.45),
                ),
                qfTitle(l10n.vipSportsTitle),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _sportCard(
                      SportKind.football,
                      real is num ? '${decimalText(real, 1)} %' : '—',
                      history['n'] == null ? null : '${history['aciertos'] ?? '—'}/${history['n']}',
                    ),
                    const SizedBox(width: 6),
                    _sportCard(SportKind.nba, rate(nba), count(nba)),
                    const SizedBox(width: 6),
                    _sportCard(SportKind.tennis, rate(tennis), count(tennis)),
                  ],
                ),
                const SizedBox(height: 6),
                liveText(l10n.vipSportsNote, size: 11, color: QfColors.text2),
                const SizedBox(height: 4),
                liveText(l10n.vipHistoryNote, size: 11, color: QfColors.muted),
                const SizedBox(height: 12),
                _benefit(Icons.verified_outlined, l10n.vipBenefit1Title, l10n.vipBenefit1Body),
                _benefit(
                  Icons.star_outline,
                  l10n.vipBenefit2Title,
                  l10n.vipBenefit2Body(min.round(), max.round()),
                ),
                _benefit(
                  Icons.sports_basketball_outlined,
                  l10n.vipBenefitSportsTitle,
                  l10n.vipBenefitSportsBody,
                ),
                _benefit(Icons.stairs_outlined, l10n.vipBenefit3Title, l10n.vipBenefit3Body),
                _benefit(Icons.bolt_outlined, l10n.vipBenefit4Title, l10n.vipBenefit4Body),
                const SizedBox(height: 16),
                if (shown.isEmpty)
                  training(l10n.vipPlansSoon)
                else
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      for (var i = 0; i < shown.length; i++) ...[
                        if (i > 0) const SizedBox(width: 8),
                        _plan(
                          i,
                          shown[i],
                          selected == i,
                          i == bestIndex,
                          () => setState(() => chosen = i),
                          monthlies[i],
                        ),
                      ],
                    ],
                  ),
                const SizedBox(height: 16),
                // La única acción ámbar de la pantalla.
                SizedBox(
                  height: 52,
                  child: FilledButton(
                    key: const ValueKey('vip-subscribe'),
                    style: qfFilled(QfColors.cta),
                    onPressed: verifying
                        ? null
                        : canBuy
                        ? () => store.buy(shown[selected]['plan_code'] as String)
                        : () => liveNotice(
                            context,
                            purchases
                                ? l10n.vipPaymentRequired
                                : featureMessage(widget.data, 'compras'),
                          ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        if (verifying)
                          const SizedBox.square(
                            dimension: 18,
                            child: CircularProgressIndicator(strokeWidth: 2, color: QfColors.onCta),
                          )
                        else
                          const Icon(Icons.workspace_premium, size: 20),
                        const SizedBox(width: 8),
                        Flexible(
                          child: Text(
                            canBuy ? l10n.vipSubscribe : l10n.vipActivate,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 10),
                Center(
                  child: liveText(
                    canBuy
                        ? l10n.vipStoreTerms
                        : purchases && store?.state == StoreState.unavailable
                        ? l10n.vipStoreUnavailable
                        : purchases
                        ? l10n.vipPricesNote
                        : l10n.vipPurchasesPending,
                    size: 11,
                    color: QfColors.text2,
                  ),
                ),
                if (canBuy)
                  Center(
                    child: TextButton(
                      style: qfText(),
                      onPressed: verifying ? null : store.restore,
                      child: Text(l10n.vipRestore),
                    ),
                  ),
                const SizedBox(height: 10),
                Center(
                  child: OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(
                      foregroundColor: QfColors.primary,
                      side: const BorderSide(color: QfColors.primary),
                      minimumSize: const Size(64, 44),
                      shape: const CutCornerBorder(cut: 8),
                    ),
                    onPressed: checkAccess,
                    icon: const Icon(Icons.refresh, size: 16),
                    label: Text(
                      widget.api.plus
                          ? l10n.profileRefreshAccess
                          : l10n.vipCheckAccess,
                    ),
                  ),
                ),
                const SizedBox(height: 10),
                Center(
                  child: liveText(l10n.vipLinked, size: 11, color: QfColors.text2),
                ),
              ],
            ),
            Positioned(
              top: 4,
              right: 6,
              child: IconButton(
                tooltip: l10n.commonClose,
                onPressed: () => Navigator.maybePop(context),
                icon: const Icon(Icons.close, color: QfColors.text2),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
