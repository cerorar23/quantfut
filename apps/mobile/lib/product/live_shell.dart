import 'package:flutter/material.dart';

import 'dart:async';

import '../core/firebase_services.dart';
import '../l10n/app_locale.dart';

import 'ladder_progress.dart';
import 'live_api.dart';
import 'predictions_switcher.dart';
import 'live_ladder.dart';
import 'live_picks.dart';
import 'live_markets.dart';
import 'live_parley.dart';
import 'live_widgets.dart';
import 'live_vip.dart';
import 'live_detail.dart';
import 'live_profile.dart';
import 'live_rewards.dart';
import 'live_home.dart';
import 'live_more.dart';

class ProductShell extends StatefulWidget {
  const ProductShell({super.key, this.api});
  final QuantFutApi? api;
  @override
  State<ProductShell> createState() => _ProductShellState();
}

class _ProductShellState extends State<ProductShell>
    with WidgetsBindingObserver {
  late final QuantFutApi api =
      widget.api ?? QuantFutApi.firebaseSession ?? QuantFutApi();
  final services = FirebaseServices.current;
  StreamSubscription<String>? tokenSubscription;
  JsonMap? data;
  String? error;
  bool busy = false;
  // Monedas disponibles para la cabecera; null mientras no hay cuenta o no cargó.
  int? coins;
  int tab = 0;
  DateTime selected = DateTime.now();
  String search = '';
  // Identificadores estables de la pestaña Predicciones (no son texto visible).
  String stream = 'high';
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    services?.openedMatch.addListener(openNotification);
    services?.foregroundMessage.addListener(showNotification);
    services?.addListener(configurationChanged);
    tokenSubscription = services?.messaging.onTokenRefresh.listen((
      token,
    ) async {
      try {
        await api.registerDevice(token);
      } catch (_) {
        /* Retried on resume. */
      }
    });
    unawaited(services?.screen('home'));
    WidgetsBinding.instance.addPostFrameCallback((_) => openNotification());
    reload();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    services?.openedMatch.removeListener(openNotification);
    services?.foregroundMessage.removeListener(showNotification);
    services?.removeListener(configurationChanged);
    tokenSubscription?.cancel();
    if (widget.api == null && QuantFutApi.firebaseSession != api) api.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      reload();
      unawaited(api.registerDevice().catchError((_) {}));
    }
  }

  void configurationChanged() {
    if (mounted) setState(() {});
  }

  void openNotification() {
    final id = services?.openedMatch.value;
    if (!mounted || id == null || !api.firebaseConnected) return;
    services!.openedMatch.value = null;
    detail(id);
  }

  void showNotification() {
    final message = services?.foregroundMessage.value;
    if (!mounted || message == null || !api.firebaseConnected) return;
    services!.foregroundMessage.value = null;
    final id = notificationMatchId(message.data);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          message.notification?.title ?? context.l10n.shellNewAlert,
        ),
        action: id == null
            ? null
            : SnackBarAction(
                label: context.l10n.shellView,
                onPressed: () => detail(id),
              ),
      ),
    );
  }

  Future<void> reload() async {
    if (busy) return;
    setState(() {
      busy = true;
      error = null;
    });
    try {
      final result = await api.home(selected);
      if (mounted) setState(() => data = result);
    } catch (e) {
      if (mounted) {
        setState(() {
          data = null;
          error = e.toString();
        });
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
    unawaited(loadCoins());
  }

  /// Saldo disponible (`spendable`, nunca negativo) para la cabecera. Si falla, se conserva el anterior.
  Future<void> loadCoins() async {
    try {
      final wallet = jsonMap(
        jsonMap(await api.request('/mobile/v1/rewards'))['wallet'],
      );
      if (mounted) setState(() => coins = (wallet['spendable'] as num?)?.toInt());
    } catch (_) {}
  }

  void vip() => Navigator.of(context)
      .push(
        MaterialPageRoute<void>(
          builder: (_) => Theme(
            data: liveTheme(),
            child: LiveVipScreen(api: api, data: data ?? {}),
          ),
        ),
      )
      .then((_) => reload());
  void detail(String id) => showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: liveBg,
    useSafeArea: true,
    builder: (_) => FractionallySizedBox(
      heightFactor: .96,
      child: Theme(
        data: liveTheme(),
        child: LiveMatchDetail(
          api: api,
          id: id,
          onVip: () {
            Navigator.of(context).pop();
            vip();
          },
        ),
      ),
    ),
  ).then((_) => reload());
  Future<void> unlock(JsonMap pick) async {
    if (!api.signedIn) {
      liveNotice(context, context.l10n.shellSignInForCoins);
      setState(() => tab = 4);
      return;
    }
    final cost = jsonMap(data?['rewards'])['unlock_cost'];
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: Text(context.l10n.shellUnlockTitle),
        content: Text(context.l10n.shellUnlockBody(cost ?? '—')),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(c, false),
            child: Text(context.l10n.commonCancel),
          ),
          TextButton(
            onPressed: () => Navigator.pop(c, true),
            child: Text(context.l10n.commonConfirm),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await api.request(
        '/mobile/v1/rewards/unlock',
        body: {
          'stream': pick['_stream'] ?? 'alta_probabilidad',
          'pick_key': pick['pick_key'],
        },
      );
      await reload();
      if (mounted) detail(pick['match_id']);
    } on ApiFailure catch (e) {
      if (!mounted) return;
      if (e.code == 'monedas_insuficientes') {
        await needCoins();
      } else {
        liveNotice(context, e.message);
      }
    } catch (e) {
      if (mounted) liveNotice(context, '$e');
    }
  }

  /// Sin saldo suficiente no se deja al usuario en un error: se le lleva a ganar monedas.
  Future<void> needCoins() async {
    final l10n = context.l10n;
    final go = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: Text(l10n.shellNeedCoinsTitle),
        content: Text(l10n.shellNeedCoinsBody),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(c, false),
            child: Text(l10n.commonCancel),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(c, true),
            child: Text(l10n.shellNeedCoinsCta),
          ),
        ],
      ),
    );
    if (go == true && mounted) setState(() => tab = 3);
  }

  Widget picks(JsonMap d) {
    if (!featureEnabled(d, 'alta_probabilidad')) {
      return training(featureMessage(d, 'alta_probabilidad'));
    }
    final report = jsonMap(d['alta_probabilidad']);
    // El rango lo manda el servidor (mismo origen que la pantalla VIP).
    final config = jsonMap(d['config']);
    final minPercent = (((config['probability_min'] as num?) ?? .73) * 100)
        .round();
    final maxPercent = (((config['probability_max'] as num?) ?? .95) * 100)
        .round();
    final rewards = jsonMap(d['rewards']);
    return HighProbabilityView(
      report: report,
      minPercent: minPercent,
      maxPercent: maxPercent,
      onOpen: (p) => detail(p['match_id']),
      onVip: vip,
      unlockCost: rewards['unlock_cost'],
      onUnlock: rewards['enabled'] == true ? (p) => unlock(p) : null,
    );
  }

  Widget pickCard(JsonMap p, JsonMap d) => RealPickCard(
    pick: p,
    onOpen: () => detail(p['match_id']),
    onVip: vip,
    cost: jsonMap(d['rewards'])['unlock_cost'] as int?,
    onUnlock: jsonMap(d['rewards'])['enabled'] == true ? () => unlock(p) : null,
  );
  Widget ladder(JsonMap d) {
    if (!featureEnabled(d, 'escalera')) {
      return training(featureMessage(d, 'escalera'));
    }
    final report = jsonMap(d['escalera']);
    final rows = sortLadder(jsonRows(report['actuales']));
    final average = LadderProgress.averageProbability(
      jsonMap(report['escalones']),
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        liveText(context.l10n.ladderFreeHint, color: liveMuted, size: 12),
        const SizedBox(height: 12),
        if (rows.isEmpty)
          training(context.l10n.ladderEmpty)
        else
          liveText(
            context.l10n.ladderActiveCount(rows.length),
            bold: true,
            size: 15,
          ),
        if (rows.isNotEmpty) const SizedBox(height: 10),
        for (final r in rows)
          LadderChallengeCard(
            key: ValueKey('ladder-${r['reto_id']}'),
            challenge: r,
            averageProbability: average,
            pending: [
              for (final p in [
                ...jsonRows(r['pasos']).where((p) => p['outcome'] == null),
                ...jsonRows(r['vip']),
              ])
                pickCard({...p, '_stream': 'escalera'}, d),
            ],
          ),
        LadderHistoryCard(report: report),
      ],
    );
  }

  Widget markets(JsonMap d) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      liveHeading(context.l10n.marketsAndResults),
      MarketsDashboard(
        api: api,
        alta: jsonMap(d['alta_probabilidad']),
        onVip: vip,
      ),
      liveButton(context.l10n.commonSeeVip, vip),
      const SizedBox(height: 16),
      if (!featureEnabled(d, 'nba')) training(featureMessage(d, 'nba')),
    ],
  );

  /// Alta probabilidad, Reto Escalera y Parley: el menú queda fijo arriba y se cambia de
  /// sección tocándolo o deslizando el dedo hacia los lados.
  Widget streamContent() => AnimatedSwitcher(
    duration: const Duration(milliseconds: 220),
    child: KeyedSubtree(
      key: ValueKey(stream),
      child: stream == 'high'
          ? picks(data!)
          : stream == 'ladder'
          ? ladder(data!)
          : ParleyTab(api: api, onVip: vip),
    ),
  );

  Widget homeBody() => HomeTab(
    api: api,
    data: data!,
    selected: selected,
    busy: busy,
    banner: services?.banner ?? '',
    maintenance: services?.maintenance == true,
    onRefresh: reload,
    onPickDate: (date) {
      setState(() => selected = date);
      reload();
    },
    onOpenMatch: detail,
    onOpenPredictions: (value) => setState(() {
      tab = 1;
      stream = value;
    }),
    onOpenCoins: () => setState(() => tab = 3),
  );

  Widget mainBody() {
    if (tab == 0) return homeBody();
    final list = RefreshIndicator(
      onRefresh: reload,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (busy) const LinearProgressIndicator(),
          if (services?.banner.isNotEmpty == true)
            liveCard(child: liveText(services!.banner)),
          if (services?.maintenance == true)
            liveCard(
              child: liveText(context.l10n.maintenanceNotice, color: liveGold),
            ),
          if (tab == 1) streamContent() else markets(data!),
        ],
      ),
    );
    if (tab != 1) return list;
    final report = jsonMap(data!['alta_probabilidad']);
    final open = jsonRows(report['proximos']).length;
    final retos = jsonRows(jsonMap(data!['escalera'])['actuales']).length;
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
          child: PredictionsSwitcher(
            value: stream,
            onChanged: (value) => setState(() => stream = value),
            badges: {'high': open, 'ladder': retos},
          ),
        ),
        Expanded(
          child: GestureDetector(
            behavior: HitTestBehavior.translucent,
            onHorizontalDragEnd: (details) {
              final next = PredictionsSwitcher.swipe(
                stream,
                details.primaryVelocity ?? 0,
              );
              if (next != stream) setState(() => stream = next);
            },
            child: list,
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) => Theme(
    data: ThemeData.dark(useMaterial3: true).copyWith(
      scaffoldBackgroundColor: liveBg,
      colorScheme: const ColorScheme.dark(
        primary: liveCyan,
        secondary: liveGold,
        surface: livePanel,
      ),
      textTheme: ThemeData.dark().textTheme.apply(fontFamily: 'Gilroy Medium'),
    ),
    child: Scaffold(
      appBar: tab == 3
          ? null
          : AppBar(
              backgroundColor: liveBg,
              leading: IconButton(
                key: const ValueKey('home-menu'),
                tooltip: context.l10n.homeMenuTooltip,
                onPressed: () => showMoreSheet(context),
                icon: const Icon(Icons.menu),
              ),
              title: liveText('QuantFut', bold: true, size: 22),
              actions: [
                _CoinsChip(
                  coins: coins,
                  onTap: () => setState(() => tab = 3),
                ),
                IconButton(
                  tooltip: context.l10n.tooltipVip,
                  onPressed: data == null ? null : vip,
                  icon: const Icon(Icons.workspace_premium, color: liveGold),
                ),
                IconButton(
                  tooltip: context.l10n.commonRefresh,
                  onPressed: busy ? null : reload,
                  icon: const Icon(Icons.refresh, color: liveCyan),
                ),
              ],
            ),
      body: tab == 3
          ? RewardsScreen(api: api, embedded: true)
          : busy && data == null
          ? const Center(child: CircularProgressIndicator())
          : error != null
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    liveText(error!, color: liveMuted),
                    const SizedBox(height: 16),
                    liveButton(context.l10n.commonRetry, reload),
                  ],
                ),
              ),
            )
          : data == null
          ? const SizedBox()
          : tab == 4
          ? LiveProfileScreen(
              api: api,
              data: data!,
              onVip: vip,
              onChanged: reload,
            )
          : mainBody(),
      bottomNavigationBar: BottomNavigationBar(
        type: BottomNavigationBarType.fixed,
        backgroundColor: livePanel,
        selectedItemColor: liveCyan,
        unselectedItemColor: liveMuted,
        selectedFontSize: 11,
        unselectedFontSize: 10,
        currentIndex: tab,
        onTap: (i) {
          if (i == tab) return;
          final leavingCoins = tab == 3;
          setState(() => tab = i);
          if (leavingCoins) unawaited(loadCoins()); // el saldo pudo cambiar allí
          unawaited(
            services?.screen(
              const ['home', 'predictions', 'markets', 'rewards', 'profile'][i],
            ),
          );
        },
        items: [
          BottomNavigationBarItem(
            icon: const Icon(Icons.grid_view),
            label: context.l10n.navHome,
          ),
          BottomNavigationBarItem(
            icon: const Icon(Icons.track_changes),
            label: context.l10n.navPredictions,
          ),
          BottomNavigationBarItem(
            icon: const Icon(Icons.insights),
            label: context.l10n.navMarkets,
          ),
          BottomNavigationBarItem(
            icon: const Icon(Icons.toll),
            label: context.l10n.navCoins,
          ),
          BottomNavigationBarItem(
            icon: const Icon(Icons.person_outline),
            label: context.l10n.navProfile,
          ),
        ],
      ),
    ),
  );
}

/// Saldo de monedas en miniatura en la cabecera; al tocarlo abre la pestaña Coins.
class _CoinsChip extends StatelessWidget {
  const _CoinsChip({required this.coins, required this.onTap});
  final int? coins;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Tooltip(
    message: context.l10n.navCoins,
    child: InkWell(
      key: const ValueKey('header-coins'),
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.toll, color: liveGold, size: 20),
            const SizedBox(width: 4),
            liveText(coins?.toString() ?? '—', bold: true, size: 14, color: liveGold),
          ],
        ),
      ),
    ),
  );
}
