import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'live_api.dart';
import 'live_widgets.dart';

class RewardsScreen extends StatefulWidget {
  const RewardsScreen({super.key, required this.api, this.embedded = false});
  final QuantFutApi api;
  final bool embedded;
  @override
  State<RewardsScreen> createState() => _RewardsScreenState();
}

class _RewardsScreenState extends State<RewardsScreen>
    with WidgetsBindingObserver {
  JsonMap? data;
  String? error;
  bool busy = false;
  final code = TextEditingController();
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    load();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    code.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) load();
  }

  Future<void> load() async {
    if (busy) return;
    setState(() {
      busy = true;
      error = null;
    });
    try {
      final result = jsonMap(await widget.api.request('/mobile/v1/rewards'));
      if (mounted) setState(() => data = result);
    } catch (e) {
      if (mounted) setState(() => error = '$e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> action(String path, {JsonMap? body}) async {
    if (busy) return;
    setState(() => busy = true);
    try {
      await widget.api.request(path, body: body ?? {});
      if (mounted) liveNotice(context, 'Operación confirmada.');
    } catch (e) {
      if (mounted) liveNotice(context, '$e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
    await load();
  }

  Future<void> offer(String provider) async {
    try {
      final result = jsonMap(
        await widget.api.request(
          '/mobile/v1/rewards/offers/$provider',
          body: {},
        ),
      );
      await const MethodChannel('quantfut/offers')
          .invokeMethod<bool>('open', {'url': result['url']});
    } catch (e) {
      if (mounted) liveNotice(context, '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final cfg = jsonMap(data?['settings']),
        wallet = jsonMap(data?['wallet']),
        refs = jsonMap(data?['referrals']);
    final cost = cfg['unlock_cost'] as num?;
    final balance = wallet['spendable'] as num? ?? 0;
    final rewards = cfg['attendance_coins'] is List
        ? cfg['attendance_coins'] as List
        : [];
    return Scaffold(
      backgroundColor: liveBg,
      appBar: AppBar(
        backgroundColor: liveBg,
        foregroundColor: Colors.white,
        automaticallyImplyLeading: !widget.embedded,
        title: const Text('Coins'),
        actions: [
          IconButton(
            tooltip: 'Actualizar saldo',
            onPressed: busy ? null : load,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: data == null
          ? Center(
              child: error == null
                  ? const CircularProgressIndicator()
                  : Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          liveText(error!, color: liveMuted),
                          liveButton('Reintentar', load),
                        ],
                      ),
                    ),
            )
          : RefreshIndicator(
              onRefresh: load,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  if (busy) const LinearProgressIndicator(),
                  Container(
                    padding: const EdgeInsets.all(22),
                    margin: const EdgeInsets.only(bottom: 16),
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [Color(0xff7439c5), Color(0xff3d1c80)],
                      ),
                      borderRadius: BorderRadius.circular(22),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            liveText('Mis monedas', bold: true),
                            const Spacer(),
                            const Icon(Icons.toll, color: liveGold, size: 40),
                          ],
                        ),
                        const SizedBox(height: 12),
                        liveText(
                          data?['signed_in'] == true
                              ? '${wallet['balance'] ?? 0}'
                              : 'Inicia sesión',
                          size: 36,
                          color: liveGold,
                          bold: true,
                        ),
                        const SizedBox(height: 10),
                        liveText(
                          'Desbloquea un pronóstico por ${cfg['unlock_cost']} monedas',
                          size: 12,
                        ),
                        const SizedBox(height: 16),
                        LinearProgressIndicator(
                          value: cost == null
                              ? 0
                              : (balance / cost).clamp(0, 1).toDouble(),
                          color: liveGold,
                          backgroundColor: Colors.white24,
                          minHeight: 6,
                        ),
                        const SizedBox(height: 8),
                        liveText(
                          cost != null && balance >= cost
                              ? 'Tienes monedas para un desbloqueo.'
                              : 'Faltan ${cost == null ? '—' : (cost - balance).clamp(0, cost).toInt()} monedas para tu próximo desbloqueo.',
                          size: 12,
                        ),
                        if (wallet['balance'] is num &&
                            (wallet['balance'] as num) < 0)
                          liveText(
                            'Saldo pendiente por recompensas anuladas.',
                            color: liveGold,
                            size: 12,
                          ),
                      ],
                    ),
                  ),
                  if (cfg['enabled'] != true) training('${cfg['message']}'),
                  if (data?['signed_in'] != true)
                    training(
                      'Inicia sesión en Perfil para guardar tu saldo, marcar asistencia y usar un código de referido.',
                    ),
                  liveHeading(
                    'Racha de asistencia · ${wallet['streak'] ?? 0} días',
                  ),
                  liveCard(
                    child: Column(
                      children: [
                        LayoutBuilder(
                          builder: (context, constraints) => Wrap(
                            spacing: 7,
                            runSpacing: 8,
                            children: List.generate(
                              rewards.length,
                              (i) => Container(
                                width: (constraints.maxWidth - 42) / 7,
                                padding: const EdgeInsets.symmetric(
                                  vertical: 12,
                                ),
                                decoration: BoxDecoration(
                                  color: liveGold.withValues(alpha: .12),
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: Column(
                                  children: [
                                    const Icon(Icons.toll, color: liveGold),
                                    liveText(
                                      '+${rewards[i]}',
                                      bold: true,
                                      color: liveGold,
                                    ),
                                    liveText(
                                      'Día ${i + 1}',
                                      size: 10,
                                      color: liveMuted,
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(height: 16),
                        liveButton(
                          'Marcar asistencia',
                          !busy && wallet['can_check_in'] == true
                              ? () => action('/mobile/v1/rewards/attendance')
                              : null,
                          color: const Color(0xffff426f),
                        ),
                        const SizedBox(height: 8),
                        liveText(
                          'Una vez por día UTC. Si omites un día, la racha se reinicia.',
                          size: 11,
                          color: liveMuted,
                        ),
                      ],
                    ),
                  ),
                  liveHeading('Ofertas para ganar monedas'),
                  ...jsonRows(data?['providers']).map(
                    (p) => liveCard(
                      child: Row(
                        children: [
                          const Icon(
                            Icons.rocket_launch_outlined,
                            color: liveGold,
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                liveText('${p['name']}', bold: true),
                                const SizedBox(height: 5),
                                liveText(
                                  p['available'] == true
                                      ? 'Ofertas según tu país y dispositivo'
                                      : 'Pendiente de activar',
                                  size: 11,
                                  color: liveMuted,
                                ),
                              ],
                            ),
                          ),
                          FilledButton(
                            onPressed:
                                !busy &&
                                    p['available'] == true &&
                                    widget.api.signedIn
                                ? () => offer(p['provider'])
                                : null,
                            child: const Text('Ir'),
                          ),
                        ],
                      ),
                    ),
                  ),
                  liveHeading('Invita a tus amigos'),
                  liveCard(
                    border: liveGold.withValues(alpha: .4),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        liveText(
                          'Tú +${cfg['referrer_coins']} · Tu amigo +${cfg['invitee_coins']} monedas',
                          bold: true,
                          color: liveGold,
                        ),
                        const SizedBox(height: 10),
                        liveText(
                          'Tras verificar el correo y completar ${cfg['referral_min_coins']} monedas en ofertas confirmadas.',
                          color: liveMuted,
                          size: 12,
                        ),
                        if (wallet['referral_code'] != null) ...[
                          const SizedBox(height: 12),
                          liveButton(
                            'Copiar mi código · ${wallet['referral_code']}',
                            () async {
                              await Clipboard.setData(
                                ClipboardData(
                                  text: '${wallet['referral_code']}',
                                ),
                              );
                              if (context.mounted) {
                                liveNotice(context, 'Código copiado.');
                              }
                            },
                            color: liveCyan,
                          ),
                          const SizedBox(height: 10),
                          liveText(
                            '${refs['registered'] ?? 0} registrados · ${refs['qualified'] ?? 0} validados',
                            size: 12,
                            color: liveMuted,
                          ),
                        ],
                        if (data?['signed_in'] == true &&
                            refs['joined'] == null) ...[
                          const SizedBox(height: 16),
                          TextField(
                            controller: code,
                            textCapitalization: TextCapitalization.characters,
                            decoration: const InputDecoration(
                              labelText: 'Código de quien te invitó',
                            ),
                          ),
                          const SizedBox(height: 10),
                          liveButton(
                            'Registrar código',
                            !busy && cfg['referrals_enabled'] == true
                                ? () => action(
                                    '/mobile/v1/rewards/referrals',
                                    body: {'code': code.text},
                                  )
                                : null,
                          ),
                        ] else if (refs['joined'] != null) ...[
                          const SizedBox(height: 12),
                          liveText(
                            'Código de invitación registrado.',
                            color: liveGreen,
                          ),
                        ],
                      ],
                    ),
                  ),
                  liveHeading('Mis movimientos'),
                  if (jsonRows(data?['ledger']).isEmpty)
                    training('Todavía no hay movimientos.')
                  else
                    ...jsonRows(data?['ledger']).map(
                      (r) => liveCard(
                        child: Row(
                          children: [
                            Expanded(
                              child: liveText(
                                '${r['kind']}\n${kickoffText(r['created_at'])}',
                                size: 12,
                                color: liveMuted,
                              ),
                            ),
                            liveText(
                              '${(r['delta'] as num) >= 0 ? '+' : ''}${r['delta']}',
                              bold: true,
                              color: (r['delta'] as num) >= 0
                                  ? liveGreen
                                  : liveGold,
                            ),
                          ],
                        ),
                      ),
                    ),
                  liveText(
                    '${data?['terms'] ?? ''}',
                    color: liveMuted,
                    size: 11,
                  ),
                  const SizedBox(height: 24),
                ],
              ),
            ),
    );
  }
}
