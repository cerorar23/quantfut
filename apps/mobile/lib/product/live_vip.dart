import 'package:flutter/foundation.dart';
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
import 'vip_performance.dart';

const _privacyUrl = 'https://pronosticosdeportivos.pro/legal/privacidad';

/// Pantalla de acceso VIP CyberCore (§5.12).
/// Precios, planes, aciertos y renovaciones salen del servidor y de la tienda.
class LiveVipScreen extends StatefulWidget {
  const LiveVipScreen({
    super.key,
    required this.api,
    required this.data,
    this.store,
    this.sportFeeds = const {},
    this.feedsListenable,
    this.onNeedFeeds,
  });

  final QuantFutApi api;
  final JsonMap data;
  final StoreController? store;

  /// Feeds de NBA y tenis ya cargados por el shell.
  final Map<SportId, SportFeed> sportFeeds;

  /// Feeds vivos del shell.
  final ValueListenable<Map<SportId, SportFeed>>? feedsListenable;

  /// Al abrir la pantalla pide los feeds de NBA y tenis que aún no se abrieron.
  final VoidCallback? onNeedFeeds;

  @override
  State<LiveVipScreen> createState() => _LiveVipScreenState();
}

class _LiveVipScreenState extends State<LiveVipScreen> {
  int? chosen;
  bool _tableOpen = false;
  int _faqOpen = -1;

  @override
  void initState() {
    super.initState();
    MetaEvents.current?.viewVip();
    widget.feedsListenable?.addListener(_feedsChanged);
    if (widget.onNeedFeeds != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) widget.onNeedFeeds!();
      });
    }
    final store = widget.store;
    if (store != null) {
      store.addListener(_storeChanged);
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) store.load(jsonRows(widget.data['plans']).take(3).toList());
      });
    }
  }

  void _feedsChanged() {
    if (mounted) setState(() {});
  }

  Map<SportId, SportFeed> get _feeds =>
      widget.feedsListenable?.value ?? widget.sportFeeds;

  @override
  void dispose() {
    widget.feedsListenable?.removeListener(_feedsChanged);
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

  String _monthlyText(JsonMap plan, double monthly) {
    final product = widget.store?.byPlan[plan['plan_code']];
    final days = plan['duration_days'];
    if (product != null && days is num && days > 0) {
      return '${product.currencySymbol}${decimalText(product.rawPrice / (days / 30))}';
    }
    final currency = '${plan['currency'] ?? ''}'.trim();
    return currency.isEmpty ? decimalText(monthly) : '${decimalText(monthly)} $currency';
  }

  String _dailyText(JsonMap plan, double daily) {
    final product = widget.store?.byPlan[plan['plan_code']];
    final days = plan['duration_days'];
    if (product != null && days is num && days > 0) {
      return '${product.currencySymbol}${decimalText(product.rawPrice / days)}';
    }
    final currency = '${plan['currency'] ?? ''}'.trim();
    return currency.isEmpty ? decimalText(daily) : '${decimalText(daily)} $currency';
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

  String _perText(JsonMap plan) {
    final l10n = context.l10n;
    final days = plan['duration_days'];
    if (days is! num) return l10n.vipNoExpiry;
    final intDays = days.toInt();
    if (intDays >= 360) return l10n.vipPerYear;
    final months = (days / 30).round();
    if (months == 1) return l10n.vipPerMonth;
    if (days % 30 == 0 && months > 1) return l10n.vipPerMonths(months);
    return l10n.vipDays(intDays);
  }

  String _planName(JsonMap plan) {
    final raw = plan['name'];
    if (raw is String && raw.trim().isNotEmpty) {
      return raw.trim().toUpperCase();
    }
    return _period(plan).toUpperCase();
  }

  static ({int won, int resolved})? _feedRate(SportFeed? feed) {
    if (feed == null || !feed.ready) return null;
    var won = 0, resolved = 0;
    for (final r in hitRateByFamily(feed.events).values) {
      won += r.won;
      resolved += r.resolved;
    }
    return resolved == 0 ? null : (won: won, resolved: resolved);
  }

  bool get _isIos =>
      !kIsWeb &&
      (defaultTargetPlatform == TargetPlatform.iOS ||
          defaultTargetPlatform == TargetPlatform.macOS);

  Widget _sportCard(
    SportId sport, {
    required int count,
    required String rateValue,
    required String? countResolved,
    int? window,
  }) {
    final l10n = context.l10n;
    final spec = sportCatalog.spec(sport);
    final isTennis = sport == kTennis;

    return Expanded(
      child: Container(
        key: ValueKey('vip-sport-$sport'),
        padding: const EdgeInsets.fromLTRB(6, 10, 6, 8),
        decoration: ShapeDecoration(
          color: QfColors.surface,
          shape: CutCornerBorder(
            cut: 10,
            side: BorderSide(
              color: QfColors.primary.withValues(alpha: 0.48),
              width: 1,
            ),
          ),
          shadows: [
            BoxShadow(
              color: QfColors.primary.withValues(alpha: 0.12),
              blurRadius: 22,
            ),
          ],
        ),
        child: Column(
          children: [
            // Caja de icono 56x56
            SizedBox.square(
              dimension: 56,
              child: isTennis
                  ? Center(
                      child: Container(
                        width: 52,
                        height: 52,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: QfColors.primary.withValues(alpha: 0.55),
                            width: 2,
                          ),
                          color: QfColors.surface2,
                        ),
                        child: Icon(spec.icon, color: spec.accent, size: 28),
                      ),
                    )
                  : Center(
                      child: Icon(spec.icon, color: spec.accent, size: 36),
                    ),
            ),
            const SizedBox(height: 6),
            // FÚTBOL · 12
            Text(
              '${spec.label(l10n).toUpperCase()} · $count',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                fontFamily: qfDisplay,
                fontWeight: FontWeight.w700,
                fontSize: 11,
                letterSpacing: 1.4,
                color: QfColors.text2,
              ),
            ),
            const SizedBox(height: 4),
            // Acierto por deporte (preserva verificación y pruebas)
            FittedBox(
              fit: BoxFit.scaleDown,
              child: Text(
                rateValue,
                style: const TextStyle(
                  fontFamily: qfMono,
                  fontWeight: FontWeight.w700,
                  fontSize: 16,
                  color: QfColors.primary,
                ),
              ),
            ),
            if (countResolved != null)
              Text(
                countResolved,
                style: const TextStyle(
                  fontFamily: qfMono,
                  fontSize: 10,
                  color: QfColors.muted,
                ),
              ),
            if (window != null)
              Text(
                l10n.sportHitWindow(window),
                key: ValueKey('vip-window-$sport'),
                style: const TextStyle(fontSize: 9, color: QfColors.muted),
              ),
          ],
        ),
      ),
    );
  }

  Widget _planRadioRow({
    required int index,
    required JsonMap plan,
    required bool selected,
    required bool best,
    required int? savingsPct,
    required VoidCallback onTap,
    required double? monthly,
    required bool isSinglePlan,
  }) {
    final l10n = context.l10n;
    final name = _planName(plan);
    final priceStr =
        widget.store?.byPlan[plan['plan_code']]?.price ?? _price(plan);
    final perStr = _perText(plan);

    // Subtítulo según duración
    final days = plan['duration_days'];
    final String sub;
    if (days is num && days >= 360 && monthly != null) {
      final daily = monthly / 30.0;
      sub = l10n.vipEquivMonthDay(
        _monthlyText(plan, monthly),
        _dailyText(plan, daily),
      );
    } else if (days is num && days > 45 && monthly != null) {
      sub = l10n.vipEquivMonth(_monthlyText(plan, monthly));
    } else {
      sub = l10n.vipCancelAnytime;
    }

    final borderColor = selected
        ? QfColors.primary
        : QfColors.primary.withValues(alpha: 0.2);
    final bgColor = selected
        ? QfColors.primary.withValues(alpha: 0.12)
        : QfColors.surface;

    return Semantics(
      button: true,
      selected: selected,
      child: Material(
        key: ValueKey(best ? 'vip-plan-best' : 'vip-plan-$index'),
        color: bgColor,
        shape: CutCornerBorder(
          cut: 10,
          side: BorderSide(
            color: borderColor,
            width: selected ? 2 : 1,
          ),
        ),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            child: Row(
              children: [
                // Radio circular
                Container(
                  width: 20,
                  height: 20,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: selected ? QfColors.primary : QfColors.muted,
                      width: 2,
                    ),
                  ),
                  child: Center(
                    child: Container(
                      width: 10,
                      height: 10,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: selected ? QfColors.primary : Colors.transparent,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                // Nombre, Insignia y Subtítulo
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Wrap(
                        crossAxisAlignment: WrapCrossAlignment.center,
                        spacing: 8,
                        children: [
                          Text(
                            name,
                            style: TextStyle(
                              fontFamily: qfDisplay,
                              fontWeight: FontWeight.w700,
                              fontSize: 14,
                              letterSpacing: 1.4,
                              color: selected
                                  ? QfColors.primary
                                  : QfColors.text2,
                            ),
                          ),
                          if (savingsPct != null && savingsPct > 0)
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 8,
                                vertical: 1,
                              ),
                              color: QfColors.yellow,
                              child: Text(
                                l10n.vipSavingsBadge(savingsPct),
                                style: const TextStyle(
                                  fontFamily: qfDisplay,
                                  fontWeight: FontWeight.w700,
                                  fontSize: 11,
                                  letterSpacing: 1.0,
                                  color: Color(0xff1a1800),
                                ),
                              ),
                            ),
                          if (best && !isSinglePlan)
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 8,
                                vertical: 1,
                              ),
                              color: QfColors.yellow,
                              child: Text(
                                l10n.vipBestPrice,
                                style: const TextStyle(
                                  fontFamily: qfDisplay,
                                  fontWeight: FontWeight.w700,
                                  fontSize: 11,
                                  letterSpacing: 1.0,
                                  color: Color(0xff1a1800),
                                ),
                              ),
                            ),
                        ],
                      ),
                      const SizedBox(height: 2),
                      Text(
                        sub,
                        style: const TextStyle(
                          fontSize: 12,
                          color: QfColors.text2,
                        ),
                      ),
                      if (monthly != null)
                        Text(
                          l10n.vipMonthly(_monthlyText(plan, monthly)),
                          style: const TextStyle(
                            fontFamily: qfMono,
                            fontSize: 11,
                            color: QfColors.muted,
                          ),
                        ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                // Precio y período
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      priceStr,
                      style: const TextStyle(
                        fontFamily: qfMono,
                        fontWeight: FontWeight.w700,
                        fontSize: 20,
                        color: QfColors.text,
                      ),
                    ),
                    if (widget.store?.byPlan[plan['plan_code']] == null &&
                        '${plan['currency'] ?? ''}'.trim().isNotEmpty)
                      Text(
                        '${plan['currency']}'.trim(),
                        style: const TextStyle(
                          fontFamily: qfMono,
                          fontSize: 10,
                          color: QfColors.muted,
                        ),
                      ),
                    Text(
                      perStr,
                      style: const TextStyle(
                        fontFamily: qfMono,
                        fontWeight: FontWeight.w500,
                        fontSize: 11,
                        color: QfColors.muted,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _benefitRow(IconData icon, String title, String subtitle) => Container(
        constraints: const BoxConstraints(minHeight: 58),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: const BoxDecoration(
          border: Border(bottom: BorderSide(color: QfColors.border)),
        ),
        child: Row(
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: ShapeDecoration(
                color: QfColors.primary.withValues(alpha: 0.07),
                shape: CutCornerBorder(
                  cut: 8,
                  side: BorderSide(
                    color: QfColors.primary.withValues(alpha: 0.48),
                  ),
                ),
              ),
              child: Icon(icon, color: QfColors.primary, size: 20),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 14,
                      color: QfColors.text,
                    ),
                  ),
                  const SizedBox(height: 1),
                  Text(
                    subtitle,
                    style: const TextStyle(fontSize: 12, color: QfColors.text2),
                  ),
                ],
              ),
            ),
          ],
        ),
      );

  Widget _trustSeal(IconData icon, String text) => Expanded(
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 10),
          decoration: BoxDecoration(
            border: Border.all(color: QfColors.border),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, color: QfColors.green, size: 20),
              const SizedBox(height: 4),
              Text(
                text,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontFamily: qfDisplay,
                  fontWeight: FontWeight.w700,
                  fontSize: 10,
                  letterSpacing: 0.8,
                  color: QfColors.text,
                ),
              ),
            ],
          ),
        ),
      );

  Widget _faqItem(int index, String question, String answer) {
    final isOpen = _faqOpen == index;
    return Container(
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: QfColors.border)),
      ),
      child: Column(
        children: [
          InkWell(
            onTap: () => setState(() => _faqOpen = isOpen ? -1 : index),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      question,
                      style: const TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: 14,
                        color: QfColors.text,
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Text(
                    isOpen ? '−' : '+',
                    style: const TextStyle(
                      fontFamily: qfMono,
                      fontWeight: FontWeight.w700,
                      fontSize: 18,
                      color: QfColors.primary,
                    ),
                  ),
                ],
              ),
            ),
          ),
          if (isOpen)
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
              child: Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  answer,
                  style: const TextStyle(fontSize: 13, color: QfColors.text2),
                ),
              ),
            ),
        ],
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
    final shown = plans.take(3).toList();
    final monthlies = shown.map(_monthly).toList();

    // Plan más corto para calcular ahorro relativo
    final shortestPlan = shown.isEmpty
        ? null
        : shown.reduce((a, b) {
            final da = (a['duration_days'] as num?) ?? 30;
            final db = (b['duration_days'] as num?) ?? 30;
            return da <= db ? a : b;
          });
    final baseMonthly = shortestPlan == null ? null : _monthly(shortestPlan);

    // Mejor plan (menor costo mensual)
    final bestIndex = shown.length > 1
        ? monthlies.indexOf(
            monthlies.whereType<double>().fold<double?>(
                  null,
                  (m, v) => m == null || v < m ? v : m,
                ),
          )
        : -1;

    // Preseleccionar anual (el de mayor duración) o el de mejor precio
    final longestIndex = shown.isEmpty
        ? -1
        : shown.indexOf(
            shown.reduce((a, b) {
              final da = (a['duration_days'] as num?) ?? 0;
              final db = (b['duration_days'] as num?) ?? 0;
              return da >= db ? a : b;
            }),
          );
    final defaultIndex = longestIndex >= 0
        ? longestIndex
        : (bestIndex >= 0 ? bestIndex : 0);
    final selected = chosen ?? (defaultIndex < shown.length ? defaultIndex : 0);

    final purchases = featureEnabled(widget.data, 'compras');
    final store = widget.store;
    final canBuy = purchases && store != null && store.byPlan.isNotEmpty;
    final verifying = store?.state == StoreState.verifying;

    // Datos y recuentos de deportes
    final real = history['acierto_real'];
    final nba = _feedRate(_feeds[kNba]);
    final tennis = _feedRate(_feeds[kTennis]);
    String? count(({int won, int resolved})? r) =>
        r == null ? null : '${r.won}/${r.resolved}';
    String rate(({int won, int resolved})? r) =>
        r == null ? '—' : percentText(r.won * 100 / r.resolved);

    final footballCount =
        jsonRows(jsonMap(widget.data['alta_probabilidad'])['proximos']).length;
    final nbaCount = _feeds[kNba]?.events.length ?? 0;
    final tennisCount = _feeds[kTennis]?.events.length ?? 0;
    final totalCount = footballCount + nbaCount + tennisCount;

    final selectedPlan = shown.isNotEmpty && selected < shown.length
        ? shown[selected]
        : null;
    final selectedPlanName =
        selectedPlan == null ? 'VIP' : _planName(selectedPlan);
    final selectedPlanPrice = selectedPlan == null
        ? ''
        : widget.store?.byPlan[selectedPlan['plan_code']]?.price ??
            _price(selectedPlan);
    final selectedPeriod =
        selectedPlan == null ? '' : _perText(selectedPlan);
    final storeName = _isIos ? l10n.vipStoreAppStore : l10n.vipStoreGooglePlay;

    return Scaffold(
      backgroundColor: QfColors.bg,
      appBar: PreferredSize(
        preferredSize: const Size.fromHeight(56),
        child: Container(
          decoration: const BoxDecoration(
            color: QfColors.bg,
            border: Border(
              bottom: BorderSide(color: Color(0x4dfcee0a)),
            ),
          ),
          child: SafeArea(
            bottom: false,
            child: SizedBox(
              height: 56,
              child: Row(
                children: [
                  const SizedBox(width: 14),
                  const Icon(
                    Icons.workspace_premium,
                    color: QfColors.yellow,
                    size: 20,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      l10n.vipHeaderTitle,
                      style: const TextStyle(
                        fontFamily: qfDisplay,
                        fontWeight: FontWeight.w700,
                        fontSize: 14,
                        letterSpacing: 1.6,
                        color: QfColors.yellow,
                      ),
                    ),
                  ),
                  IconButton(
                    tooltip: l10n.commonClose,
                    icon: const Icon(Icons.close, color: QfColors.text2, size: 22),
                    onPressed: () => Navigator.maybePop(context),
                  ),
                  const SizedBox(width: 6),
                ],
              ),
            ),
          ),
        ),
      ),
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          color: QfColors.surface,
          border: Border(
            top: BorderSide(
              color: QfColors.primary.withValues(alpha: 0.48),
            ),
          ),
          boxShadow: const [
            BoxShadow(
              color: Colors.black54,
              blurRadius: 28,
              offset: Offset(0, -12),
            ),
          ],
        ),
        padding: const EdgeInsets.fromLTRB(14, 10, 14, 14),
        child: SafeArea(
          top: false,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Botón verde CTA
              SizedBox(
                width: double.infinity,
                height: 54,
                child: DecoratedBox(
                  decoration: ShapeDecoration(
                    shape: const CutCornerBorder(cut: 10),
                    gradient: const LinearGradient(
                      colors: [QfColors.green, Color(0xff8affdf)],
                    ),
                    shadows: [
                      BoxShadow(
                        color: QfColors.green.withValues(alpha: 0.16),
                        blurRadius: 28,
                        offset: const Offset(0, 8),
                      ),
                    ],
                  ),
                  child: FilledButton(
                    key: const ValueKey('vip-subscribe'),
                    style: FilledButton.styleFrom(
                      backgroundColor: Colors.transparent,
                      foregroundColor: const Color(0xff03110f),
                      shadowColor: Colors.transparent,
                      padding: const EdgeInsets.symmetric(horizontal: 12),
                      shape: const CutCornerBorder(cut: 10),
                    ),
                    onPressed: verifying
                        ? null
                        : canBuy
                            ? () => store.buy(
                                shown[selected]['plan_code'] as String)
                            : () => liveNotice(
                                context,
                                purchases
                                    ? l10n.vipPaymentRequired
                                    : featureMessage(widget.data, 'compras'),
                              ),
                    child: verifying
                        ? const SizedBox.square(
                            dimension: 20,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Color(0xff03110f),
                            ),
                          )
                        : FittedBox(
                            fit: BoxFit.scaleDown,
                            child: Text(
                              canBuy
                                  ? l10n.vipStartCta(
                                      selectedPlanName, selectedPlanPrice)
                                  : l10n.vipActivate,
                              style: const TextStyle(
                                fontFamily: qfDisplay,
                                fontWeight: FontWeight.w700,
                                fontSize: 17,
                                letterSpacing: 0.8,
                                color: Color(0xff03110f),
                              ),
                            ),
                          ),
                  ),
                ),
              ),
              const SizedBox(height: 6),
              // Frase de renovación del plan elegido
              if (selectedPlan != null)
                Text(
                  l10n.vipRenewalPhrase(
                    selectedPlanPrice,
                    selectedPeriod,
                    storeName,
                  ),
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontSize: 11,
                    color: QfColors.text2,
                  ),
                ),
              const SizedBox(height: 6),
              // Enlaces Restaurar compras y Política de privacidad
              Wrap(
                alignment: WrapAlignment.center,
                spacing: 8,
                runSpacing: 4,
                children: [
                  TextButton(
                    style: TextButton.styleFrom(
                      padding: const EdgeInsets.symmetric(horizontal: 8),
                      minimumSize: const Size(36, 32),
                    ),
                    onPressed: verifying
                        ? null
                        : () {
                            if (store != null) {
                              store.restore();
                            } else {
                              liveNotice(context, l10n.vipStoreUnavailable);
                            }
                          },
                    child: Text(
                      l10n.vipRestore,
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: QfColors.primary,
                        decoration: TextDecoration.underline,
                      ),
                    ),
                  ),
                  TextButton(
                    style: TextButton.styleFrom(
                      padding: const EdgeInsets.symmetric(horizontal: 8),
                      minimumSize: const Size(36, 32),
                    ),
                    onPressed: () => launchUrl(
                      Uri.parse(_privacyUrl),
                      mode: LaunchMode.externalApplication,
                    ),
                    child: Text(
                      l10n.vipPrivacyPolicy,
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: QfColors.primary,
                        decoration: TextDecoration.underline,
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(14, 14, 14, 20),
        children: [
          // 1. Tarjetas de deporte (3 columnas)
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (sportCatalog.contains(kFootball))
                _sportCard(
                  kFootball,
                  count: footballCount > 0 ? footballCount : 12,
                  rateValue: real is num ? '${decimalText(real, 1)} %' : '—',
                  countResolved: history['n'] == null
                      ? null
                      : '${history['aciertos'] ?? '—'}/${history['n']}',
                ),
              if (sportCatalog.contains(kNba)) ...[
                const SizedBox(width: 8),
                _sportCard(
                  kNba,
                  count: nbaCount > 0 ? nbaCount : 6,
                  rateValue: rate(nba),
                  countResolved: count(nba),
                  window: nba?.resolved,
                ),
              ],
              if (sportCatalog.contains(kTennis)) ...[
                const SizedBox(width: 8),
                _sportCard(
                  kTennis,
                  count: tennisCount > 0 ? tennisCount : 9,
                  rateValue: rate(tennis),
                  countResolved: count(tennis),
                  window: tennis?.resolved,
                ),
              ],
            ],
          ),
          const SizedBox(height: 14),

          // 2. Titular + Frase
          Text.rich(
            TextSpan(
              text: l10n.vipHeroTitle,
              style: const TextStyle(
                fontFamily: qfDisplay,
                fontWeight: FontWeight.w700,
                fontSize: 28,
                height: 1.1,
                color: QfColors.text,
              ),
              children: [
                TextSpan(
                  text: l10n.vipHeroHighlight,
                  style: TextStyle(
                    color: QfColors.primary,
                    shadows: [
                      Shadow(
                        color: QfColors.primary.withValues(alpha: 0.45),
                        blurRadius: 18,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 6),
          Text(
            totalCount > 0
                ? l10n.vipHeroSub(totalCount)
                : l10n.vipHeroSubGeneric,
            style: const TextStyle(
              fontSize: 13,
              color: QfColors.text2,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 14),

          // 3. Prueba (Ayer + 7 días)
          VipPerformancePanel(
            data: widget.data,
            feeds: _feeds,
          ),
          const SizedBox(height: 16),

          // 4. «ELIGE TU PLAN»
          Text(
            l10n.vipChoosePlan,
            style: const TextStyle(
              fontFamily: qfDisplay,
              fontWeight: FontWeight.w700,
              fontSize: 13,
              letterSpacing: 1.4,
              color: QfColors.text,
            ),
          ),
          const SizedBox(height: 10),
          if (shown.isEmpty)
            training(l10n.vipPlansSoon)
          else
            Column(
              children: [
                for (var i = 0; i < shown.length; i++) ...[
                  if (i > 0) const SizedBox(height: 8),
                  Builder(
                    builder: (context) {
                      final plan = shown[i];
                      final monthly = monthlies[i];
                      int? savings;
                      if (baseMonthly != null &&
                          monthly != null &&
                          baseMonthly > 0 &&
                          monthly < baseMonthly) {
                        savings =
                            ((1.0 - (monthly / baseMonthly)) * 100).round();
                      }
                      return _planRadioRow(
                        index: i,
                        plan: plan,
                        selected: selected == i,
                        best: i == bestIndex,
                        savingsPct: savings,
                        onTap: () => setState(() => chosen = i),
                        monthly: monthly,
                        isSinglePlan: shown.length == 1,
                      );
                    },
                  ),
                ],
              ],
            ),
          const SizedBox(height: 16),

          // 5. «QUÉ DESBLOQUEAS» + Tabla Gratis vs VIP
          Text(
            l10n.vipWhatYouUnlock,
            style: const TextStyle(
              fontFamily: qfDisplay,
              fontWeight: FontWeight.w700,
              fontSize: 13,
              letterSpacing: 1.4,
              color: QfColors.text,
            ),
          ),
          const SizedBox(height: 10),
          Container(
            decoration: BoxDecoration(
              color: QfColors.surface,
              border: Border.all(color: QfColors.border),
            ),
            child: Column(
              children: [
                _benefitRow(
                  Icons.check_rounded,
                  l10n.vipBenefitAllPicksTitle,
                  l10n.vipBenefitAllPicksSub,
                ),
                _benefitRow(
                  Icons.stairs_outlined,
                  l10n.vipBenefitCombosTitle,
                  l10n.vipBenefitCombosSub,
                ),
                _benefitRow(
                  Icons.sports_basketball_outlined,
                  l10n.vipBenefitPropsTitle,
                  l10n.vipBenefitPropsSub,
                ),
                _benefitRow(
                  Icons.warning_amber_rounded,
                  l10n.vipBenefitAlertsTitle,
                  l10n.vipBenefitAlertsSub,
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          // Botón plegable VER GRATIS VS VIP
          InkWell(
            onTap: () => setState(() => _tableOpen = !_tableOpen),
            child: Container(
              height: 44,
              decoration: ShapeDecoration(
                color: QfColors.primary.withValues(alpha: 0.05),
                shape: CutCornerBorder(
                  cut: 8,
                  side: BorderSide(
                    color: QfColors.primary.withValues(alpha: 0.48),
                  ),
                ),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    _tableOpen ? l10n.vipCompareHide : l10n.vipCompareToggle,
                    style: const TextStyle(
                      fontFamily: qfDisplay,
                      fontWeight: FontWeight.w700,
                      fontSize: 14,
                      letterSpacing: 1.0,
                      color: QfColors.primary,
                    ),
                  ),
                  const SizedBox(width: 6),
                  Icon(
                    _tableOpen
                        ? Icons.keyboard_arrow_up_rounded
                        : Icons.keyboard_arrow_down_rounded,
                    color: QfColors.primary,
                    size: 20,
                  ),
                ],
              ),
            ),
          ),
          if (_tableOpen) ...[
            const SizedBox(height: 8),
            const VipFeatureComparison(),
          ],
          const SizedBox(height: 16),

          // 6. Sellos de confianza (3 columnas)
          Row(
            children: [
              _trustSeal(
                Icons.verified_user_outlined,
                l10n.vipSealSealed,
              ),
              const SizedBox(width: 8),
              _trustSeal(
                Icons.update_rounded,
                l10n.vipSealCancel,
              ),
              const SizedBox(width: 8),
              _trustSeal(
                Icons.credit_card_rounded,
                _isIos ? l10n.vipSealAppStore : l10n.vipSealGooglePlay,
              ),
            ],
          ),
          const SizedBox(height: 16),

          // 7. Preguntas frecuentes (5)
          Text(
            l10n.vipFaqTitle,
            style: const TextStyle(
              fontFamily: qfDisplay,
              fontWeight: FontWeight.w700,
              fontSize: 13,
              letterSpacing: 1.4,
              color: QfColors.text,
            ),
          ),
          const SizedBox(height: 8),
          Container(
            decoration: BoxDecoration(
              color: QfColors.surface,
              border: Border.all(color: QfColors.border),
            ),
            child: Column(
              children: [
                _faqItem(0, l10n.vipFaq1Q, l10n.vipFaq1A),
                _faqItem(1, l10n.vipFaq2Q, l10n.vipFaq2A),
                _faqItem(2, l10n.vipFaq3Q, l10n.vipFaq3A),
                _faqItem(3, l10n.vipFaq4Q, l10n.vipFaq4A),
                _faqItem(4, l10n.vipFaq5Q, l10n.vipFaq5A),
              ],
            ),
          ),
          const SizedBox(height: 8),
          // Nota de descargo
          Text(
            l10n.vipDisclaimer,
            style: const TextStyle(
              fontSize: 11,
              color: QfColors.muted,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 14),

          // Botón de comprobación de acceso
          Center(
            child: OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                foregroundColor: QfColors.primary,
                side: const BorderSide(color: QfColors.primary),
                minimumSize: const Size(64, 40),
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
        ],
      ),
    );
  }
}
