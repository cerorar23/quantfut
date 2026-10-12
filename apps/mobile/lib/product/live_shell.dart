import 'package:flutter/material.dart';

import 'live_api.dart';
import 'live_widgets.dart';
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
  late final QuantFutApi api = widget.api ?? QuantFutApi();
  JsonMap? data;
  String? error;
  bool busy = false;
  int tab = 0, horizon = 48;
  DateTime selected = DateTime.now();
  String search = '';
  String stream = 'Alta probabilidad';
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    reload();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    if (widget.api == null) api.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) reload();
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
      liveNotice(context, 'Inicia sesión en Perfil para usar tus monedas.');
      setState(() => tab = 4);
      return;
    }
    final cost = jsonMap(data?['rewards'])['unlock_cost'];
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Desbloquear pronóstico'),
        content: Text(
          'Se descontarán $cost monedas de tu saldo. El acceso corresponde a este pronóstico.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(c, false),
            child: const Text('Cancelar'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(c, true),
            child: const Text('Confirmar'),
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
          '75–90 % de probabilidad · 10 % gratuito por lote',
          color: liveMuted,
          size: 12,
        ),
        const SizedBox(height: 12),
        if (report['estado'] != 'activa')
          training(
            'Modelo en entrenamiento · ${jsonMap(report)['motivos'] ?? ''}',
          )
        else if (rows.isEmpty)
          training('No hay pronósticos publicados pendientes en este rango.'),
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
        liveText(
          'Un escalón gratuito: el de mayor probabilidad.',
          color: liveMuted,
          size: 12,
        ),
        const SizedBox(height: 12),
        if (rows.isEmpty) training('No hay retos activos publicados.'),
        ...rows.map(
          (r) => Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              liveHeading(
                'Reto #${r['reto_id']} · ${r['pasos_objetivo']} escalones',
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
                              '${p['local']} · ${p['visitante']}\n${p['texto']} · ${{'win': 'Acertado', 'loss': 'Fallado', 'push': 'Reembolso'}[p['outcome']] ?? p['outcome']}\n${p['marcador'] ?? ''}',
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
                  liveText('Calendario · hora local', bold: true),
                  const Spacer(),
                  IconButton(
                    tooltip: 'Elegir fecha',
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
                              [
                                'Lun',
                                'Mar',
                                'Mié',
                                'Jue',
                                'Vie',
                                'Sáb',
                                'Dom',
                              ][i],
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
          decoration: const InputDecoration(
            prefixIcon: Icon(Icons.search, color: liveMuted),
            hintText: 'Busca equipos o ligas',
            hintStyle: TextStyle(color: liveMuted),
            border: OutlineInputBorder(),
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
        liveHeading('${rows.length} enfrentamientos'),
        if (rows.isEmpty)
          training('No hay enfrentamientos para estos filtros.'),
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
                        'Resultado: ${(m['marcador'] as List).join(' – ')}',
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
                    liveText('Pronóstico VIP', color: liveGold, size: 12),
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
                stream = 'Alta probabilidad';
              }),
              icon: const Icon(Icons.verified_outlined),
              label: const Text('Alta probabilidad'),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: OutlinedButton.icon(
              onPressed: () => setState(() {
                tab = 1;
                stream = 'Reto Escalera';
              }),
              icon: const Icon(Icons.stairs_outlined),
              label: const Text('Reto Escalera'),
            ),
          ),
        ],
      ),
      liveHeading('Partidos por fecha y horario'),
      calendar(d),
      liveHeading('Alta probabilidad'),
      picks(d),
      liveHeading('Reto Escalera'),
      ladder(d),
    ],
  );
  Widget markets(JsonMap d) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      liveHeading('Mercados y resultados'),
      historyPerformance(jsonMap(jsonMap(d['alta_probabilidad'])['historial'])),
      liveButton('Ver acceso VIP', vip),
      const SizedBox(height: 16),
      if (!featureEnabled(d, 'nba')) training(featureMessage(d, 'nba')),
    ],
  );

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
                  tooltip: 'VIP',
                  onPressed: data == null ? null : vip,
                  icon: const Icon(Icons.workspace_premium, color: liveGold),
                ),
                IconButton(
                  tooltip: 'Actualizar',
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
                    liveButton('Reintentar', reload),
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
                  if (tab == 0)
                    home(data!)
                  else if (tab == 1)
                    Column(
                      children: [
                        SegmentedButton<String>(
                          segments: const [
                            ButtonSegment(
                              value: 'Alta probabilidad',
                              label: Text('Alta probabilidad'),
                            ),
                            ButtonSegment(
                              value: 'Reto Escalera',
                              label: Text('Reto Escalera'),
                            ),
                          ],
                          selected: {stream},
                          onSelectionChanged: (s) =>
                              setState(() => stream = s.first),
                        ),
                        const SizedBox(height: 16),
                        stream == 'Alta probabilidad'
                            ? picks(data!)
                            : ladder(data!),
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
        onTap: (i) => setState(() => tab = i),
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.grid_view), label: 'Inicio'),
          BottomNavigationBarItem(
            icon: Icon(Icons.track_changes),
            label: 'Predicciones',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.insights),
            label: 'Mercados',
          ),
          BottomNavigationBarItem(icon: Icon(Icons.toll), label: 'Coins'),
          BottomNavigationBarItem(
            icon: Icon(Icons.person_outline),
            label: 'Perfil',
          ),
        ],
      ),
    ),
  );
}

class LiveVipScreen extends StatefulWidget {
  const LiveVipScreen({super.key, required this.api, required this.data});
  final QuantFutApi api;
  final JsonMap data;
  @override
  State<LiveVipScreen> createState() => _LiveVipScreenState();
}

class _LiveVipScreenState extends State<LiveVipScreen> {
  int selected = 0;
  Future<void> checkAccess() async {
    if (!widget.api.signedIn) {
      liveNotice(context, 'Inicia sesión en Perfil para comprobar tu acceso.');
      return;
    }
    try {
      await widget.api.updateAccount();
      if (mounted) {
        liveNotice(
          context,
          widget.api.plus
              ? 'Tu acceso VIP está activo.'
              : 'Tu cuenta tiene acceso gratuito.',
        );
        setState(() {});
      }
    } catch (e) {
      if (mounted) liveNotice(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final plans = jsonRows(widget.data['plans']);
    final history = jsonMap(
      jsonMap(widget.data['alta_probabilidad'])['historial'],
    );
    return Scaffold(
      backgroundColor: liveBg,
      appBar: AppBar(
        backgroundColor: liveBg,
        foregroundColor: Colors.white,
        title: const Text('Acceso VIP'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(18),
        children: [
          liveHeading('Todos los pronósticos publicados'),
          liveText(
            'Alta probabilidad y Reto Escalera con acceso completo mientras tu suscripción esté vigente.',
            color: liveMuted,
          ),
          const SizedBox(height: 16),
          historyPerformance(history, maxMarkets: 0),
          for (var i = 0; i < plans.length; i++)
            liveCard(
              border: selected == i ? liveCyan : null,
              child: ListTile(
                onTap: () => setState(() => selected = i),
                leading: Icon(
                  selected == i
                      ? Icons.radio_button_checked
                      : Icons.radio_button_off,
                  color: liveCyan,
                ),
                title: liveText('${plans[i]['name']}', bold: true),
                subtitle: liveText(
                  '${decimalText((plans[i]['price_cents'] as num) / 100)} ${plans[i]['currency']} · ${plans[i]['duration_days'] ?? 'Sin vencimiento'} días',
                  color: liveMuted,
                ),
              ),
            ),
          liveHeading('Gratis y VIP'),
          Table(
            columnWidths: const {
              0: FlexColumnWidth(2),
              1: FlexColumnWidth(),
              2: FlexColumnWidth(),
            },
            children: [
              for (final row in [
                ['Función', 'Gratis', 'VIP'],
                ['Alta probabilidad', '10 %', 'Todos'],
                ['Reto Escalera', '1 escalón', 'Todos'],
                ['Historial', 'Sí', 'Sí'],
                ['Desbloqueo por monedas', 'Por pick', 'Incluido'],
              ])
                TableRow(
                  children: row
                      .map(
                        (s) => Padding(
                          padding: const EdgeInsets.symmetric(
                            vertical: 12,
                            horizontal: 4,
                          ),
                          child: liveText(
                            s,
                            size: 12,
                            color: s == 'VIP' ? liveGold : Colors.white,
                          ),
                        ),
                      )
                      .toList(),
                ),
            ],
          ),
          const SizedBox(height: 24),
          if (!featureEnabled(widget.data, 'compras'))
            training(featureMessage(widget.data, 'compras'))
          else
            training('La contratación requiere un canal de pago configurado.'),
          const SizedBox(height: 12),
          liveText(
            'Precios y moneda del catálogo del servidor. Las compras y su restauración se habilitarán al conectar el proveedor de pagos.',
            color: liveMuted,
            size: 12,
          ),
        ],
      ),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(18, 8, 18, 12),
          child: liveButton(
            widget.api.plus ? 'Actualizar mi acceso' : 'Consultar mi acceso',
            checkAccess,
          ),
        ),
      ),
    );
  }
}
