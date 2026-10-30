import 'package:flutter/material.dart';

import 'dart:async';

import 'package:url_launcher/url_launcher.dart';

import '../core/firebase_services.dart';
import '../core/meta_events.dart';
import '../l10n/app_locale.dart';

import 'ladder_progress.dart';
import 'live_api.dart';
import 'store_purchases.dart';
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
import 'qf_theme.dart';
import 'sport_selector.dart';
import 'sports.dart';

class ProductShell extends StatefulWidget {
  const ProductShell({super.key, this.api, this.sportPrefs});
  final QuantFutApi? api;

  /// Preferencias de deporte; por defecto las de la app (o memoria si no hay servicios).
  final SportPrefs? sportPrefs;
  @override
  State<ProductShell> createState() => _ProductShellState();
}

class _ProductShellState extends State<ProductShell>
    with WidgetsBindingObserver {
  late final QuantFutApi api =
      widget.api ?? QuantFutApi.firebaseSession ?? QuantFutApi();
  final services = FirebaseServices.current;
  late final StoreController store = StoreController(api)..listen();
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
  // Deporte global: lo comparten Inicio, Predicciones y Mercados.
  SportKind sport = SportKind.football;
  List<SportKind> visibleSports = SportKind.values;
  final _memory = <String, String>{};
  late final SportPrefs sportPrefs =
      widget.sportPrefs ??
      SportPrefs(
        read: (key) async => services == null
            ? _memory[key]
            : services!.preferences.getString(key),
        write: (key, value) async => services == null
            ? _memory[key] = value
            : services!.preferences.setString(key, value),
      );

  /// Orden, ocultos y último deporte guardados.
  Future<void> loadSports() async {
    try {
      final order = await sportPrefs.order();
      final hidden = await sportPrefs.hidden();
      final initial = await sportPrefs.initial();
      if (!mounted) return;
      setState(() {
        visibleSports = [
          for (final k in order)
            if (!hidden.contains(k)) k,
        ];
        sport = initial;
        _fitStream();
      });
    } catch (_) {
      /* Se queda en fútbol con los tres deportes. */
    }
  }

  /// Si la sección actual no existe en el deporte, vuelve a Alta probabilidad.
  void _fitStream() {
    if (!sportSpecs[sport]!.streams.contains(stream)) stream = 'high';
  }

  void changeSport(SportKind value) {
    if (value == sport) return;
    setState(() {
      sport = value;
      _fitStream();
    });
    unawaited(sportPrefs.remember(value));
  }

  List<String> get sportStreams => [
    for (final s in PredictionsSwitcher.order)
      if (sportSpecs[sport]!.streams.contains(s)) s,
  ];

  @override
  void initState() {
    super.initState();
    unawaited(loadSports());
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
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      openNotification();
      await MetaEvents.current?.apply(services?.adsAllowed ?? true);
      await api.syncMetaDevice();
      await showPrivacyNotice();
    });
    reload();
  }

  /// Una vez por versión de consentimiento: avisa de que la medición viene activada.
  Future<void> showPrivacyNotice() async {
    final prefs = services?.preferences;
    if (prefs == null || !api.signedIn || !mounted) return;
    if (await prefs.getString('consent_notice') == consentVersion || !mounted) return;
    await showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(dialogContext.l10n.privacyUpdateTitle),
        content: Text(dialogContext.l10n.privacyUpdateBody),
        actions: [
          TextButton(
            onPressed: () => launchUrl(
              Uri.parse('https://pronosticosdeportivos.pro/legal/privacidad'),
              mode: LaunchMode.externalApplication,
            ),
            child: Text(dialogContext.l10n.privacyUpdateRead),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: Text(dialogContext.l10n.privacyUpdateOk),
          ),
        ],
      ),
    );
    await prefs.setString('consent_notice', consentVersion);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    services?.openedMatch.removeListener(openNotification);
    services?.foregroundMessage.removeListener(showNotification);
    services?.removeListener(configurationChanged);
    tokenSubscription?.cancel();
    store.dispose();
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
            child: LiveVipScreen(api: api, data: data ?? {}, store: store),
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
      freePercent:
          (((config['high_probability_free_fraction'] as num?) ?? .10) * 100)
              .round(),
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

  /// Selector de deporte fijo arriba de Inicio, Predicciones y Mercados.
  Widget withSelector(Widget content) => Column(
    children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
        child: SportSelector(
          sports: visibleSports,
          value: sport,
          onChanged: changeSport,
        ),
      ),
      Expanded(child: content),
    ],
  );

  Widget mainBody() => withSelector(
    sport == SportKind.football ? footballBody() : sportBody(),
  );

  /// Contenido de NBA y tenis: vacío hasta que las tareas 7 y 8 lo conecten.
  Widget sportBody() {
    if (tab == 1) {
      return Column(
        children: [
          predictionsSwitcher(),
          const Expanded(child: SportPlaceholder()),
        ],
      );
    }
    return const SportPlaceholder();
  }

  Widget predictionsSwitcher() => Padding(
    padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
    child: PredictionsSwitcher(
      value: stream,
      onChanged: (value) => setState(() => stream = value),
      streams: sportStreams,
      badges: sport == SportKind.football
          ? {
              'high': jsonRows(jsonMap(data!['alta_probabilidad'])['proximos']).length,
              'ladder': jsonRows(jsonMap(data!['escalera'])['actuales']).length,
            }
          : const {},
    ),
  );

  Widget footballBody() {
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
    return Column(
      children: [
        predictionsSwitcher(),
        Expanded(
          child: GestureDetector(
            behavior: HitTestBehavior.translucent,
            onHorizontalDragEnd: (details) {
              final next = PredictionsSwitcher.swipe(
                stream,
                details.primaryVelocity ?? 0,
                sportStreams,
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
      scaffoldBackgroundColor: QfColors.bg,
      colorScheme: const ColorScheme.dark(
        primary: QfColors.primary,
        secondary: liveGold,
        surface: livePanel,
      ),
      textTheme: ThemeData.dark().textTheme.apply(fontFamily: 'Gilroy Medium'),
    ),
    child: Scaffold(
      appBar: tab == 3
          ? null
          : AppBar(
              backgroundColor: QfColors.bg,
              leading: IconButton(
                key: const ValueKey('home-menu'),
                tooltip: context.l10n.homeMenuTooltip,
                onPressed: () => showMoreSheet(context),
                icon: const Icon(Icons.menu),
              ),
              title: Text(
                '// ${_brand.toUpperCase()}',
                style: const TextStyle(
                  color: QfColors.text,
                  fontFamily: qfDisplay,
                  fontWeight: FontWeight.w700,
                  fontSize: 22,
                  letterSpacing: 1.2,
                ),
              ),
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
                  icon: const Icon(Icons.refresh, color: QfColors.primary),
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
        backgroundColor: QfColors.surface,
        selectedItemColor: QfColors.primary,
        unselectedItemColor: QfColors.muted,
        showSelectedLabels: true,
        showUnselectedLabels: true,
        selectedFontSize: 11,
        unselectedFontSize: 10,
        selectedLabelStyle: const TextStyle(fontFamily: qfDisplay, fontWeight: FontWeight.w700),
        unselectedLabelStyle: const TextStyle(fontFamily: qfDisplay, fontWeight: FontWeight.w600),
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

/// Marca de la cabecera; no se traduce.
const _brand = 'QuantFut';

/// Hueco donde las tareas 7 y 8 conectan el contenido de NBA y tenis.
class SportPlaceholder extends StatelessWidget {
  const SportPlaceholder({super.key});

  @override
  Widget build(BuildContext context) {
    // TODO(T7/T8): Inicio, Predicciones y Mercados de NBA y tenis.
    return const SizedBox.expand(key: ValueKey('sport-placeholder'));
  }
}
