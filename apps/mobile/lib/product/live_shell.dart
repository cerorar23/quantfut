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
import 'home_sport.dart';
import 'live_more.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';
import 'qf_unlock_sheet.dart';
import 'sport_detail.dart';
import 'sport_images.dart';
import 'sport_markets.dart';
import 'sport_predictions.dart';
import 'sport_selector.dart';
import 'sports.dart';
import 'sports_feed.dart';
import 'sports_quotes.dart';

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
  SportId sport = sportCatalog.defaultVisible.first;
  List<SportId> visibleSports = sportCatalog.defaultVisible;
  // Feeds de NBA y tenis: se piden la primera vez que se elige el deporte. Cada uno tiene su
  // propio estado; un fallo solo se ve en su hueco.
  final feeds = <SportId, SportFeed>{};
  // La pantalla VIP lo escucha para pintar el acierto cuando llegan los feeds.
  final _feedsNotifier = ValueNotifier<Map<SportId, SportFeed>>(const {});
  // Cuotas de referencia por deporte: overlay aparte del feed; sin ellas todo se ve igual.
  final quotes = <SportId, QuotesOverlay>{};
  final _feedLoading = <SportId>{};
  // Cada recarga de NBA invalida el enriquecimiento anterior.
  int _nbaGeneration = 0;
  ImageCatalog images = ImageCatalog.empty;
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

  /// Orden y ocultos guardados; abre el primer deporte visible.
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
        if (!sportChosen) sport = initial; // una elección del usuario gana a la lectura inicial
        _fitStream();
      });
      _ensureFeed(sport);
    } catch (_) {
      /* Se queda en fútbol con los tres deportes. */
    }
  }

  /// Tras guardar en Perfil → «Mis deportes»: relee orden y ocultos. Si el deporte actual
  /// quedó oculto se pasa al primero visible.
  Future<void> sportsChanged() async {
    final order = await sportPrefs.order();
    final hidden = await sportPrefs.hidden();
    if (!mounted) return;
    setState(() {
      visibleSports = [
        for (final k in order)
          if (!hidden.contains(k)) k,
      ];
      if (!visibleSports.contains(sport)) {
        sport = visibleSports.first;
        _fitStream();
      }
    });
    _ensureFeed(sport);
  }

  /// El catálogo de deportes cambió (llegó el del servidor o el del disco): relee orden y ocultos. Un fallo
  /// aquí no debe romper la pantalla; se queda con lo que ya se ve.
  void _catalogChanged() => unawaited(sportsChanged().catchError((Object _) {}));

  /// Petición pendiente del menú «Mis deportes». El Perfil la consume una vez (la retira con
  /// `onFocusHandled`), así que volver luego a Perfil lo abre arriba.
  bool focusSports = false;

  void openMySports() => setState(() {
    tab = 4;
    focusSports = true;
  });

  /// Si la sección actual no existe en el deporte, vuelve a Alta probabilidad.
  void _fitStream() {
    if (!sportCatalog.spec(sport).streams.contains(stream)) stream = 'high';
  }

  bool sportChosen = false;

  void changeSport(SportId value) {
    sportChosen = true;
    if (value == sport) return;
    setState(() {
      sport = value;
      _fitStream();
    });
    _ensureFeed(value);
  }

  /// El feed tal como lo ven las pantallas: con el cupo de gratis del deporte aplicado para quien no tiene VIP.
  SportFeed _gated(SportId kind, SportFeed feed) => feed.ready
      ? SportFeed(ready: true, events: applyQuota(feed.events, sportCatalog.quotas[kind], plus: api.plus))
      : feed;

  void _ensureFeed(SportId kind) {
    if (!feeds.containsKey(kind)) unawaited(loadFeed(kind));
  }

  /// Pide el feed del deporte y, de paso, el catálogo de imágenes (una vez, con caché).
  Future<void> loadFeed(SportId kind) async {
    if (kind == kFootball || !_feedLoading.add(kind)) return;
    try {
      final (feed, catalog, overlay) = await (
        loadSport(api, kind),
        loadImageCatalog(api),
        loadQuotes(api, kind),
      ).wait;
      if (!mounted) return;
      setState(() {
        // Un refresco fallido no borra un feed bueno: se conserva el anterior.
        if (feed.ready || feeds[kind]?.ready != true) feeds[kind] = _gated(kind, feed);
        // Igual con las cuotas: un overlay vacío (fallo) no pisa uno bueno.
        quotes[kind] = mergeQuotes(quotes[kind], overlay);
        _feedsNotifier.value = Map.of(feeds);
        if (!identical(catalog, ImageCatalog.empty)) images = catalog;
      });
      // NBA: la cartelera solo trae el ganador; el resto de mercados (con su cuota y casa) se pide partido a
      // partido y se va sumando al feed sin bloquear la pantalla.
      if (kind == kNba && feed.ready) {
        final generation = ++_nbaGeneration;
        unawaited(
          enrichNbaFeed(
            api,
            feed,
            current: () => mounted && generation == _nbaGeneration,
            onUpdate: (enriched) {
              if (!mounted) return;
              setState(() {
                feeds[kind] = _gated(kind, enriched);
                _feedsNotifier.value = Map.of(feeds);
              });
            },
          ),
        );
      }
    } finally {
      _feedLoading.remove(kind);
    }
  }

  /// Ficha del partido de NBA o tenis (hoja inferior; fútbol usa `detail`).
  void openSportEvent(SportEvent event) =>
      showSportDetail(
        context,
        api: api,
        event: event,
        images: images,
        quotes: quotes[event.sport] ?? QuotesOverlay.empty,
        onVip: vip,
      );

  List<String> get sportStreams => [
    for (final s in PredictionsSwitcher.order)
      if (sportCatalog.spec(sport).streams.contains(s)) s,
  ];

  @override
  void initState() {
    super.initState();
    unawaited(loadSports());
    sportCatalogNotifier.addListener(_catalogChanged);
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
      barrierColor: Colors.black.withValues(alpha: 0.75),
      builder: (dialogContext) {
        final l10n = dialogContext.l10n;
        return Dialog(
          backgroundColor: Colors.transparent,
          elevation: 0,
          insetPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
          child: Container(
            decoration: BoxDecoration(
              boxShadow: [
                BoxShadow(
                  color: QfColors.cyan.withValues(alpha: 0.2),
                  blurRadius: 60,
                ),
              ],
            ),
            child: Material(
              color: QfColors.surface,
              shape: const CutCornerBorder(
                cut: 16,
                side: BorderSide(color: QfColors.borderStrong, width: 1.2),
              ),
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 24, 20, 20),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.center,
                      children: [
                        Container(
                          width: 54,
                          height: 54,
                          decoration: ShapeDecoration(
                            color: QfColors.cyan.withValues(alpha: 0.1),
                            shape: const CutCornerBorder(
                              cut: 8,
                              side: BorderSide(color: QfColors.borderStrong),
                            ),
                          ),
                          child: const Center(
                            child: Icon(Icons.shield_outlined, color: QfColors.cyan, size: 28),
                          ),
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: Text(
                            l10n.privacyUpdateTitle.toUpperCase(),
                            style: const TextStyle(
                              fontFamily: qfDisplay,
                              fontWeight: FontWeight.w700,
                              fontSize: 20,
                              height: 1.05,
                              letterSpacing: 0.6,
                              color: QfColors.text,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.02),
                        border: Border.all(color: QfColors.divider),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const Icon(Icons.check, size: 16, color: QfColors.green),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Text(
                                  l10n.privacyBullet1,
                                  style: const TextStyle(fontFamily: 'Exo 2', fontSize: 13, color: QfColors.text),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Row(
                            children: [
                              const Icon(Icons.check, size: 16, color: QfColors.yellow),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Text(
                                  l10n.privacyBullet2,
                                  style: const TextStyle(fontFamily: 'Exo 2', fontSize: 13, color: QfColors.text),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      l10n.privacyUpdateBody,
                      style: const TextStyle(
                        fontFamily: 'Exo 2',
                        color: QfColors.text2,
                        fontSize: 13,
                        height: 1.35,
                      ),
                    ),
                    const SizedBox(height: 16),
                    SizedBox(
                      height: 52,
                      child: Container(
                        decoration: ShapeDecoration(
                          gradient: const LinearGradient(
                            colors: [Color(0xFF05FFA1), Color(0xFF8AFFDF)],
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                          ),
                          shadows: [
                            BoxShadow(
                              color: const Color(0xFF05FFA1).withValues(alpha: 0.16),
                              blurRadius: 28,
                              offset: const Offset(0, 8),
                            ),
                          ],
                          shape: const CutCornerBorder(cut: 10),
                        ),
                        child: Material(
                          color: Colors.transparent,
                          child: InkWell(
                            customBorder: const CutCornerBorder(cut: 10),
                            onTap: () => Navigator.pop(dialogContext),
                            child: Center(
                              child: Text(
                                l10n.privacyUpdateOk.toUpperCase(),
                                style: const TextStyle(
                                  fontFamily: qfDisplay,
                                  fontWeight: FontWeight.w700,
                                  fontSize: 16,
                                  letterSpacing: 1.2,
                                  color: Color(0xFF03110F),
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 8),
                    SizedBox(
                      height: 46,
                      child: OutlinedButton(
                        style: OutlinedButton.styleFrom(
                          foregroundColor: QfColors.cyan,
                          side: const BorderSide(color: QfColors.borderStrong),
                          backgroundColor: QfColors.cyan.withValues(alpha: 0.05),
                          shape: const CutCornerBorder(cut: 8),
                        ),
                        onPressed: () {
                          Navigator.pop(dialogContext);
                          launchUrl(
                            Uri.parse('https://pronosticosdeportivos.pro/legal/privacidad'),
                            mode: LaunchMode.externalApplication,
                          );
                        },
                        child: Text(
                          l10n.privacyReadAndAdjust.toUpperCase(),
                          style: const TextStyle(
                            fontFamily: qfDisplay,
                            fontWeight: FontWeight.w700,
                            fontSize: 12,
                            letterSpacing: 1.0,
                            color: QfColors.cyan,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
      },
    );
    await prefs.setString('consent_notice', consentVersion);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    sportCatalogNotifier.removeListener(_catalogChanged);
    services?.openedMatch.removeListener(openNotification);
    services?.foregroundMessage.removeListener(showNotification);
    services?.removeListener(configurationChanged);
    tokenSubscription?.cancel();
    store.dispose();
    _feedsNotifier.dispose();
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
    if (feeds.containsKey(sport)) unawaited(loadFeed(sport));
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

  void vip() {
    _feedsNotifier.value = Map.of(feeds);
    Navigator.of(context)
      .push(
        MaterialPageRoute<void>(
          builder: (_) => Theme(
            data: liveTheme(),
            child: LiveVipScreen(
              api: api,
              data: data ?? {},
              store: store,
              sportFeeds: Map.of(feeds),
              feedsListenable: _feedsNotifier,
              onNeedFeeds: () {
                if (sportCatalog.contains(kNba)) _ensureFeed(kNba);
                if (sportCatalog.contains(kTennis)) _ensureFeed(kTennis);
              },
            ),
          ),
        ),
      )
      .then((_) => reload());
  }

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
  String? _vipMonthlyPrice() {
    final plans = jsonRows(data?['plans']);
    if (plans.isEmpty) return null;
    JsonMap? shortest;
    for (final p in plans) {
      final days = p['duration_days'];
      if (days is num && days > 0) {
        if (shortest == null || days < (shortest['duration_days'] as num)) {
          shortest = p;
        }
      }
    }
    shortest ??= plans.first;
    final planCode = shortest['plan_code'] as String?;
    final product = planCode != null ? store.byPlan[planCode] : null;
    final days = shortest['duration_days'];
    if (product != null && days is num && days > 0) {
      return '${product.currencySymbol}${decimalText(product.rawPrice / (days / 30))}';
    }
    final cents = shortest['price_cents'];
    if (cents is num && days is num && days > 0) {
      final m = cents / 100 / (days / 30);
      return '\$${decimalText(m)}';
    }
    return null;
  }

  Future<void> unlock(JsonMap pick) async {
    if (!api.signedIn) {
      liveNotice(context, context.l10n.shellSignInForCoins);
      setState(() => tab = 4);
      return;
    }
    if (coins == null) {
      await loadCoins();
    }
    if (!mounted) return;
    final userCoins = coins ?? 0;
    final cost = (jsonMap(data?['rewards'])['unlock_cost'] as num?)?.toInt() ?? 40;
    final monthlyPrice = _vipMonthlyPrice();

    final result = await QfUnlockSheet.show(
      context: context,
      pick: pick,
      cost: cost,
      saldo: userCoins,
      initialMissing: userCoins < cost,
      monthlyPrice: monthlyPrice,
      onUnlock: () async {
        await api.request(
          '/mobile/v1/rewards/unlock',
          body: {
            'stream': pick['_stream'] ?? 'alta_probabilidad',
            'pick_key': pick['pick_key'],
          },
        );
      },
      onEarnCoins: () {
        setState(() => tab = 3);
      },
      onVip: vip,
      images: images,
    );

    if (result == true) {
      await reload();
      await loadCoins();
      if (mounted && pick['match_id'] != null) {
        detail(pick['match_id']);
      }
    }
  }

  /// Sin saldo suficiente no se deja al usuario en un error: se le lleva a ganar monedas.
  Future<void> needCoins({JsonMap? pick}) async {
    final effectivePick = pick ?? _firstLockedPick ?? <String, dynamic>{};
    if (coins == null) {
      await loadCoins();
    }
    if (!mounted) return;
    final userCoins = coins ?? 0;
    final cost = (jsonMap(data?['rewards'])['unlock_cost'] as num?)?.toInt() ?? 40;
    await QfUnlockSheet.show(
      context: context,
      pick: effectivePick,
      cost: cost,
      saldo: userCoins,
      initialMissing: true,
      monthlyPrice: _vipMonthlyPrice(),
      onUnlock: () async => unlock(effectivePick),
      onEarnCoins: () {
        setState(() => tab = 3);
      },
      onVip: vip,
      images: images,
    );
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
        agenda: jsonRows(d['agenda']),
        onOpenMatch: detail,
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

  /// El selector va siempre; la carga o el error del fútbol solo afectan a su hueco.
  Widget mainBody() => withSelector(
    sport == kFootball ? footballGate(footballBody) : sportBody(),
  );

  /// Cargando / error con reintento / contenido del fútbol (`data` ya cargado).
  Widget footballGate(Widget Function() content) {
    if (busy && data == null) {
      return const Center(
        child: CircularProgressIndicator(key: ValueKey('football-loading')),
      );
    }
    if (error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              liveText(error!, color: liveMuted),
              const SizedBox(height: 16),
              liveButton(context.l10n.commonRetry, reload, color: QfColors.primary),
            ],
          ),
        ),
      );
    }
    return data == null ? const SizedBox() : content();
  }

  /// Contenido de NBA y tenis: Inicio, Predicciones y Mercados, cada uno con su feed.
  Widget sportBody() {
    if (tab == 0) return sportHome();
    final feed = feeds[sport];
    final loading = const Center(child: CircularProgressIndicator());
    if (tab == 1) {
      return Column(
        children: [
          predictionsSwitcher(),
          Expanded(
            child: stream != 'high' && sportStreams.contains(stream)
                ? footballGate(
                    () => RefreshIndicator(
                      onRefresh: reload,
                      child: ListView(
                        padding: const EdgeInsets.all(16),
                        children: [streamContent()],
                      ),
                    ),
                  )
                : feed == null
                ? loading
                : SportPredictions(
                    key: ValueKey('sport-predictions-$sport'),
                    api: api,
                    sport: sport,
                    feed: feed,
                    quotes: quotes[sport] ?? QuotesOverlay.empty,
                    images: images,
                    onOpen: openSportEvent,
                    onRetry: () => loadFeed(sport),
                  ),
          ),
        ],
      );
    }
    return feed == null
        ? loading
        : SportMarkets(
            key: ValueKey('sport-markets-$sport'),
            api: api,
            sport: sport,
            feed: feed,
            images: images,
            quotes: quotes[sport] ?? QuotesOverlay.empty,
            onOpenEvent: openSportEvent,
            onRetry: () => loadFeed(sport),
          );
  }

  /// Inicio de NBA o tenis en su propio hueco: cargando, error con reintento o contenido.
  Widget sportHome() {
    final feed = feeds[sport];
    return KeyedSubtree(
      key: ValueKey('sport-home-$sport'),
      child: feed == null
          ? const Center(child: CircularProgressIndicator())
          : HomeSport(
              key: ValueKey('home-sport-$sport'),
              api: api,
              sport: sport,
              feed: feed,
              quotes: quotes[sport] ?? QuotesOverlay.empty,
              images: images,
              onOpen: openSportEvent,
              onRetry: () => loadFeed(sport),
              onVip: vip,
            ),
    );
  }

  Widget predictionsSwitcher() => Padding(
    padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
    child: PredictionsSwitcher(
      value: stream,
      onChanged: (value) => setState(() => stream = value),
      streams: sportStreams,
      badges: sport == kFootball
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

  JsonMap? get _firstLockedPick {
    final list = jsonRows(data?['predicciones']);
    for (final p in list) {
      if (p['locked'] == true) return p;
    }
    return null;
  }

  @override
  Widget build(BuildContext context) => Theme(
    data: qfTheme(),
    child: Scaffold(
      appBar: AppBar(
        toolbarHeight: 56,
        elevation: 0,
        scrolledUnderElevation: 0,
        backgroundColor: QfColors.bg,
        shape: const Border(
          bottom: BorderSide(
            color: QfColors.border,
            width: 1,
          ),
        ),
        leading: SizedBox(
          width: 44,
          height: 44,
          child: IconButton(
            key: const ValueKey('home-menu'),
            tooltip: context.l10n.homeMenuTooltip,
            onPressed: () => showMoreSheet(context, onMySports: openMySports, onVip: vip),
            icon: const Icon(Icons.menu, color: QfColors.muted, size: 22),
          ),
        ),
        title: const Text.rich(
          TextSpan(
            children: [
              TextSpan(
                text: 'QUANT',
                style: TextStyle(color: QfColors.text),
              ),
              TextSpan(
                text: 'FUT',
                style: TextStyle(color: QfColors.cyan),
              ),
            ],
          ),
          style: TextStyle(
            fontFamily: qfDisplay,
            fontWeight: FontWeight.w700,
            fontSize: 21,
            letterSpacing: 2.8,
          ),
        ),
        actions: [
          if (tab != 3)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: _CoinsChip(
                coins: coins,
                onTap: () => setState(() => tab = 3),
              ),
            ),
          IconButton(
            tooltip: context.l10n.tooltipVip,
            onPressed: data == null ? null : vip,
            icon: const Icon(Icons.workspace_premium, color: QfColors.yellow, size: 22),
          ),
          IconButton(
            tooltip: context.l10n.commonRefresh,
            onPressed: busy ? null : reload,
            icon: const Icon(Icons.refresh, color: QfColors.primary, size: 22),
          ),
        ],
      ),
      body: tab == 3
          ? RewardsScreen(api: api, embedded: true)
          : tab == 4
          ? footballGate(
              () => LiveProfileScreen(
                api: api,
                data: data!,
                onVip: vip,
                onChanged: reload,
                sportPrefs: sportPrefs,
                onSportsChanged: sportsChanged,
                focusSports: focusSports,
                onFocusHandled: () {
                  if (mounted) setState(() => focusSports = false);
                },
              ),
            )
          : mainBody(),
      bottomNavigationBar: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (tab == 1)
            _PicksBottomBar(
              cost: (jsonMap(data?['rewards'])['unlock_cost'] as num?)?.toInt() ?? 40,
              onUnlock: () {
                final pick = _firstLockedPick;
                if (pick != null) {
                  unlock(pick);
                } else if (!api.signedIn) {
                  liveNotice(context, context.l10n.shellSignInForCoins);
                  setState(() => tab = 4);
                } else {
                  needCoins();
                }
              },
              onVip: vip,
            ),
          QfBottomNav(
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
              QfBottomNavItem(
                icon: const Icon(Icons.grid_view),
                label: context.l10n.navHome,
              ),
              QfBottomNavItem(
                icon: const Icon(Icons.track_changes),
                label: context.l10n.navPicks,
              ),
              QfBottomNavItem(
                icon: const Icon(Icons.insights),
                label: context.l10n.navMarkets,
              ),
              QfBottomNavItem(
                icon: const Icon(Icons.toll),
                label: context.l10n.navCoins,
              ),
              QfBottomNavItem(
                icon: const Icon(Icons.person_outline),
                label: context.l10n.navProfile,
              ),
            ],
          ),
        ],
      ),
    ),
  );
}

class _PicksBottomBar extends StatelessWidget {
  const _PicksBottomBar({
    required this.cost,
    required this.onUnlock,
    required this.onVip,
  });

  final int cost;
  final VoidCallback onUnlock;
  final VoidCallback onVip;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Container(
      decoration: const BoxDecoration(
        color: QfColors.surface,
        border: Border(top: BorderSide(color: QfColors.border)),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      child: SafeArea(
        top: false,
        bottom: false,
        child: Row(
          children: [
            Expanded(
              flex: 2,
              child: SizedBox(
                height: 48,
                child: Material(
                  color: Colors.transparent,
                  shape: const CutCornerBorder(cut: 8),
                  clipBehavior: Clip.antiAlias,
                  child: Ink(
                    decoration: const BoxDecoration(
                      gradient: qfGreenGradient,
                    ),
                    child: InkWell(
                      onTap: onUnlock,
                      child: Center(
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(
                              Icons.lock_open,
                              size: 18,
                              color: Color(0xFF03110F),
                            ),
                            const SizedBox(width: 8),
                            Text(
                              l10n.shellUnlockAction(cost),
                              style: const TextStyle(
                                fontFamily: qfDisplay,
                                fontWeight: FontWeight.w700,
                                fontSize: 15,
                                letterSpacing: 1.2,
                                color: Color(0xFF03110F),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              flex: 1,
              child: SizedBox(
                height: 48,
                child: Material(
                  color: const Color(0x14FCEE0A),
                  shape: const CutCornerBorder(
                    cut: 8,
                    side: BorderSide(color: Color(0x80FCEE0A)),
                  ),
                  clipBehavior: Clip.antiAlias,
                  child: InkWell(
                    onTap: onVip,
                    child: const Center(
                      child: Text(
                        'VIP',
                        style: TextStyle(
                          fontFamily: qfDisplay,
                          fontWeight: FontWeight.w700,
                          fontSize: 15,
                          letterSpacing: 1.2,
                          color: QfColors.yellow,
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class QfBottomNavItem {
  const QfBottomNavItem({
    required this.icon,
    required this.label,
    this.key,
  });

  final Widget icon;
  final String label;
  final Key? key;
}

class QfBottomNav extends StatelessWidget {
  const QfBottomNav({
    super.key,
    required this.currentIndex,
    required this.onTap,
    required this.items,
  });

  final int currentIndex;
  final ValueChanged<int> onTap;
  final List<QfBottomNavItem> items;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: QfColors.surface,
        border: Border(
          top: BorderSide(
            color: QfColors.border,
            width: 1,
          ),
        ),
      ),
      child: SafeArea(
        top: false,
        child: SizedBox(
          height: 64,
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              for (int i = 0; i < items.length; i++)
                Expanded(
                  child: _QfBottomNavItemView(
                    item: items[i],
                    selected: i == currentIndex,
                    onTap: () => onTap(i),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _QfBottomNavItemView extends StatelessWidget {
  const _QfBottomNavItemView({
    required this.item,
    required this.selected,
    required this.onTap,
  });

  final QfBottomNavItem item;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final activeColor = QfColors.cyan;
    final inactiveColor = QfColors.muted;
    final color = selected ? activeColor : inactiveColor;

    return Semantics(
      selected: selected,
      button: true,
      label: item.label,
      child: Material(
        color: selected
            ? QfColors.cyan.withValues(alpha: 0.07)
            : Colors.transparent,
        child: InkWell(
          key: item.key,
          onTap: onTap,
          child: Container(
            decoration: BoxDecoration(
              border: Border(
                top: BorderSide(
                  color: selected ? QfColors.cyan : Colors.transparent,
                  width: 2,
                ),
              ),
            ),
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                IconTheme(
                  data: IconThemeData(
                    color: color,
                    size: 22,
                  ),
                  child: item.icon,
                ),
                const SizedBox(height: 3),
                Text(
                  item.label.toUpperCase(),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontFamily: qfDisplay,
                    fontSize: 11,
                    fontWeight: selected ? FontWeight.w700 : FontWeight.w600,
                    letterSpacing: 0.88,
                    color: color,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
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
      customBorder: const CutCornerBorder(cut: 8),
      child: Container(
        height: 44,
        padding: const EdgeInsets.symmetric(horizontal: 10),
        decoration: ShapeDecoration(
          color: QfColors.yellow.withValues(alpha: 0.08),
          shape: CutCornerBorder(
            cut: 8,
            side: BorderSide(
              color: QfColors.yellow.withValues(alpha: 0.40),
              width: 1,
            ),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.toll, color: QfColors.yellow, size: 16),
            const SizedBox(width: 6),
            Text(
              coins?.toString() ?? '—',
              style: const TextStyle(
                fontFamily: qfMono,
                fontWeight: FontWeight.w700,
                fontSize: 13,
                color: QfColors.yellow,
              ),
            ),
          ],
        ),
      ),
    ),
  );
}
