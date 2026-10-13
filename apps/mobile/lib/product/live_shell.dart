import 'package:flutter/material.dart';

import 'dart:async';

import 'package:intl/intl.dart';

import '../core/firebase_services.dart';
import '../l10n/app_locale.dart';

import 'live_api.dart';
import 'live_markets.dart';
import 'live_parley.dart';
import 'live_widgets.dart';
import 'live_vip.dart';
import 'live_detail.dart';
import 'live_profile.dart';
import 'live_rewards.dart';

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
  int tab = 0, horizon = 48;
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
    } catch (e) {
      if (mounted) liveNotice(context, '$e');
    }
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
    final rows = [...jsonRows(report['proximos']), ...jsonRows(report['vip'])];
    rows.sort((a, b) {
      int rank(JsonMap p) => p['free'] == true
          ? 0
          : p['locked'] == true
          ? 2
          : 1;
      final access = rank(a).compareTo(rank(b));
      if (access != 0) return access;
      if (a['free'] == true && b['free'] == true) {
        final odds = ((b['ref_price'] as num?) ?? 0).compareTo(
          (a['ref_price'] as num?) ?? 0,
        );
        if (odds != 0) return odds;
      }
      return '${a['kickoff_utc']}'.compareTo('${b['kickoff_utc']}');
    });
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        liveText(
          context.l10n.picksRangeHint(minPercent, maxPercent),
          color: liveMuted,
          size: 12,
        ),
        const SizedBox(height: 12),
        if (report['estado'] != 'activa')
          training(
            context.l10n.picksTrainingReasons(
              '${jsonMap(report)['motivos'] ?? ''}',
            ),
          )
        else if (rows.isEmpty)
          training(context.l10n.picksEmpty),
        ...rows.map((p) => pickCard(p, d)),
      ],
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
    final rows = jsonRows(report['actuales']);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        liveText(context.l10n.ladderFreeHint, color: liveMuted, size: 12),
        const SizedBox(height: 12),
        if (rows.isEmpty) training(context.l10n.ladderEmpty),
        ...rows.map(
          (r) => Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              liveHeading(
                context.l10n.ladderTitle(
                  r['reto_id'] ?? '—',
                  (r['pasos_objetivo'] as num?)?.toInt() ?? 0,
                ),
              ),
              ...jsonRows(r['pasos'])
                  .where((p) => p['outcome'] != null)
                  .map(
                    (p) => liveCard(
                      child: Row(
                        children: [
                          Icon(
                            p['outcome'] == 'win'
                                ? Icons.check_circle
                                : Icons.cancel_outlined,
                            color: p['outcome'] == 'win'
                                ? liveGreen
                                : liveMuted,
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: liveText(
                              '${p['local']} · ${p['visitante']}\n${p['texto']} · ${{'win': context.l10n.outcomeWin, 'loss': context.l10n.outcomeLoss, 'push': context.l10n.outcomePush}[p['outcome']] ?? p['outcome']}\n${p['marcador'] ?? ''}',
                              size: 12,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
              ...[
                ...jsonRows(r['pasos']).where((p) => p['outcome'] == null),
                ...jsonRows(r['vip']),
              ].map((p) => pickCard({...p, '_stream': 'escalera'}, d)),
            ],
          ),
        ),
      ],
    );
  }

  Widget calendar(JsonMap d) {
    if (!featureEnabled(d, 'agenda')) {
      return training(featureMessage(d, 'agenda'));
    }
    final now = DateTime.now();
    final today = dateKey(selected) == dateKey(now);
    final rows = jsonRows(d['agenda']).where((m) {
      final ko = dateValue(m['kickoff_utc'])?.toLocal();
      final name =
          '${jsonMap(m['local'])['nombre']} ${jsonMap(m['visitante'])['nombre']} ${jsonMap(m['liga'])['nombre']}'
              .toLowerCase();
      return ko != null &&
          name.contains(search.toLowerCase()) &&
          (today
              ? !ko.isAfter(now.add(Duration(hours: horizon)))
              : dateKey(ko) == dateKey(selected));
    }).toList();
    final start = DateTime(
      selected.year,
      selected.month,
      selected.day,
    ).subtract(Duration(days: selected.weekday - 1));
    final allPicks = [
      ...jsonRows(jsonMap(d['alta_probabilidad'])['proximos']),
      ...jsonRows(jsonMap(d['alta_probabilidad'])['vip']),
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        liveCard(
          child: Column(
            children: [
              Row(
                children: [
                  liveText(context.l10n.calendarTitle, bold: true),
                  const Spacer(),
                  IconButton(
                    tooltip: context.l10n.calendarPickDate,
                    onPressed: () async {
                      final date = await showDatePicker(
                        context: context,
                        initialDate: selected,
                        firstDate: DateTime(2025),
                        lastDate: DateTime.now().add(const Duration(days: 365)),
                      );
                      if (date != null && mounted) {
                        setState(() => selected = date);
                        reload();
                      }
                    },
                    icon: const Icon(Icons.calendar_month, color: liveCyan),
                  ),
                ],
              ),
              Row(
                children: List.generate(7, (i) {
                  final date = start.add(Duration(days: i));
                  final active = dateKey(date) == dateKey(selected);
                  return Expanded(
                    child: InkWell(
                      onTap: () {
                        setState(() => selected = date);
                        reload();
                      },
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 10),
                        decoration: BoxDecoration(
                          color: active ? liveGreen : Colors.transparent,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Column(
                          children: [
                            liveText(
                              toBeginningOfSentenceCase(
                                    localDate(DateFormat.E, date),
                                  ) ??
                                  '',
                              size: 10,
                              color: active ? liveBg : liveMuted,
                            ),
                            const SizedBox(height: 8),
                            liveText(
                              '${date.day}',
                              bold: active,
                              color: active ? liveBg : Colors.white,
                            ),
                          ],
                        ),
                      ),
                    ),
                  );
                }),
              ),
            ],
          ),
        ),
        TextField(
          onChanged: (s) => setState(() => search = s),
          style: const TextStyle(color: Colors.white),
          decoration: InputDecoration(
            prefixIcon: const Icon(Icons.search, color: liveMuted),
            hintText: context.l10n.calendarSearchHint,
            hintStyle: const TextStyle(color: liveMuted),
            border: const OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 10),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            children: [48, 1, 3, 6, 12]
                .map(
                  (h) => Padding(
                    padding: const EdgeInsets.only(right: 6),
                    child: ChoiceChip(
                      label: Text('+$h h'),
                      selected: horizon == h,
                      onSelected: (_) => setState(() => horizon = h),
                    ),
                  ),
                )
                .toList(),
          ),
        ),
        liveHeading(context.l10n.calendarMatchesCount(rows.length)),
        if (rows.isEmpty) training(context.l10n.calendarEmpty),
        ...rows.map((m) {
          final local = jsonMap(m['local']), away = jsonMap(m['visitante']);
          final available = allPicks
              .where((p) => p['match_id'] == m['match_id'])
              .toList();
          final public = available.where((p) => p['locked'] != true).toList();
          return InkWell(
            onTap: () => detail(m['match_id']),
            child: liveCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  liveText(
                    '${kickoffText(m['kickoff_utc'])} · ${jsonMap(m['liga'])['nombre'] ?? ''}',
                    size: 11,
                    color: liveMuted,
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        flex: 5,
                        child: Column(
                          children: [
                            for (final team in [local, away])
                              Padding(
                                padding: const EdgeInsets.symmetric(
                                  vertical: 4,
                                ),
                                child: Row(
                                  children: [
                                    TeamCrest(team: team, api: api),
                                    const SizedBox(width: 8),
                                    Expanded(
                                      child: liveText(
                                        '${team['nombre']}',
                                        bold: true,
                                        size: 13,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        flex: 3,
                        child: probabilityBars(jsonMap(m['probabilities'])),
                      ),
                      const SizedBox(width: 10),
                      const Icon(Icons.chevron_right, color: liveMuted),
                    ],
                  ),
                  if (m['marcador'] is List)
                    Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: liveText(
                        context.l10n.resultLabel(
                          (m['marcador'] as List).join(' – '),
                        ),
                        color: liveMuted,
                      ),
                    ),
                  if (public.isNotEmpty) ...[
                    const Divider(color: Colors.white12),
                    liveText(
                      '${public.first['texto']} @ ${decimalText(public.first['ref_price'])}',
                      color: liveGreen,
                      size: 12,
                    ),
                  ] else if (available.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    liveText(
                      context.l10n.vipPickLabel,
                      color: liveGold,
                      size: 12,
                    ),
                  ],
                ],
              ),
            ),
          );
        }),
      ],
    );
  }

  Widget home(JsonMap d) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Row(
        children: [
          Expanded(
            child: OutlinedButton.icon(
              onPressed: () => setState(() {
                tab = 1;
                stream = 'high';
              }),
              icon: const Icon(Icons.verified_outlined),
              label: _segmentLabel(context.l10n.streamHighProb),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: OutlinedButton.icon(
              onPressed: () => setState(() {
                tab = 1;
                stream = 'ladder';
              }),
              icon: const Icon(Icons.stairs_outlined),
              label: _segmentLabel(context.l10n.streamLadder),
            ),
          ),
        ],
      ),
      liveHeading(context.l10n.homeByDate),
      calendar(d),
      liveHeading(context.l10n.streamHighProb),
      picks(d),
      liveHeading(context.l10n.streamLadder),
      ladder(d),
    ],
  );
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

  /// Las traducciones largas se reducen para caber en el segmento.
  Widget _segmentLabel(String text) =>
      FittedBox(fit: BoxFit.scaleDown, child: Text(text, maxLines: 1));

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
              title: liveText('QuantFut', bold: true, size: 22),
              actions: [
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
          : RefreshIndicator(
              onRefresh: reload,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  if (busy) const LinearProgressIndicator(),
                  if (services?.banner.isNotEmpty == true)
                    liveCard(child: liveText(services!.banner)),
                  if (services?.maintenance == true)
                    liveCard(
                      child: liveText(
                        context.l10n.maintenanceNotice,
                        color: liveGold,
                      ),
                    ),
                  if (tab == 0)
                    home(data!)
                  else if (tab == 1)
                    Column(
                      children: [
                        SegmentedButton<String>(
                          segments: [
                            ButtonSegment(
                              value: 'high',
                              label: _segmentLabel(context.l10n.streamHighProb),
                            ),
                            ButtonSegment(
                              value: 'ladder',
                              label: _segmentLabel(context.l10n.streamLadder),
                            ),
                            ButtonSegment(
                              value: 'parley',
                              label: _segmentLabel(context.l10n.streamParley),
                            ),
                          ],
                          showSelectedIcon: false,
                          style: const ButtonStyle(
                            textStyle: WidgetStatePropertyAll(
                              TextStyle(fontSize: 12.5),
                            ),
                            padding: WidgetStatePropertyAll(
                              EdgeInsets.symmetric(horizontal: 6),
                            ),
                          ),
                          selected: {stream},
                          onSelectionChanged: (s) =>
                              setState(() => stream = s.first),
                        ),
                        const SizedBox(height: 16),
                        if (stream == 'high')
                          picks(data!)
                        else if (stream == 'ladder')
                          ladder(data!)
                        else
                          ParleyTab(api: api, onVip: vip),
                      ],
                    )
                  else
                    markets(data!),
                ],
              ),
            ),
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
          setState(() => tab = i);
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
