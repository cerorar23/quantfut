import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:share_plus/share_plus.dart';

import '../l10n/app_locale.dart';
import 'coin_burst.dart';
import 'live_ads.dart';
import '../core/meta_events.dart';
import 'live_api.dart';
import 'live_widgets.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';
import 'rewards_progress.dart';

final _inviteLink = RegExp(r'/i/([A-Za-z0-9]{6,24})');
final _inviteCode = RegExp(r'^[A-Za-z0-9]{6,24}$');

/// El código de invitación dentro de lo pegado o escrito: el propio código, o el que va en el
/// enlace `/i/CODIGO` (también si viene dentro del mensaje compartido). Nada más: una palabra
/// cualquiera del texto no se toma por código.
String? inviteCodeFrom(String raw) {
  final link = _inviteLink.firstMatch(raw);
  if (link != null) return link.group(1)!.toUpperCase();
  final text = raw.trim();
  return _inviteCode.hasMatch(text) ? text.toUpperCase() : null;
}

/// Enlace a la página de invitación del servidor.
String inviteLink(Uri base, String code) =>
    base.resolve('/i/${Uri.encodeComponent(code)}').toString();

/// Mensaje que se comparte con el código y el enlace.
String inviteShareText(AppLocalizations l10n, Uri base, String code) =>
    l10n.rewardsShareMessage(code, inviteLink(base, code));

/// Etiqueta legible de un movimiento del historial (el servidor envía un código).
String ledgerKindLabel(AppLocalizations l10n, Object? kind) => switch (kind) {
  'attendance' => l10n.ledgerAttendance,
  'offer' => l10n.ledgerOffer,
  'unlock' => l10n.ledgerUnlock,
  'referrer' => l10n.ledgerReferrer,
  'invitee' => l10n.ledgerInvitee,
  'reversal' => l10n.ledgerReversal,
  'referral_reversal' => l10n.ledgerReferralReversal,
  'ad' => l10n.ledgerAd,
  _ => '$kind',
};

class RewardsScreen extends StatefulWidget {
  const RewardsScreen({
    super.key,
    required this.api,
    this.embedded = false,
    this.adGateway,
  });
  final QuantFutApi api;
  final bool embedded;

  /// Pasarela del SDK de anuncios; las pruebas inyectan una falsa.
  final RewardedAdGateway? adGateway;
  @override
  State<RewardsScreen> createState() => _RewardsScreenState();
}

class _RewardsScreenState extends State<RewardsScreen>
    with WidgetsBindingObserver {
  JsonMap? data;
  String? error;
  bool busy = false;
  bool openingOffer = false;
  bool watchingAd = false;
  String? adStatus;
  late final RewardedAdGateway _adGateway = widget.adGateway ?? AdMobGateway();
  bool _ledgerOpen = false;
  bool _termsOpen = false;
  int _burst = 0;
  String _burstLabel = '';
  Timer? _clock;
  final code = TextEditingController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    // Refresca la cuenta atrás de la asistencia; solo repinta cuando ya se marcó hoy.
    _clock = Timer.periodic(const Duration(seconds: 1), (_) {
      final wallet = jsonMap(data?['wallet']);
      if (!mounted || wallet.isEmpty) return;
      final coins = _attendanceCoins(jsonMap(data?['settings']));
      final nextAd = DateTime.tryParse('${jsonMap(data?['ads'])['next_at'] ?? ''}');
      if (AttendanceState.of(wallet, coins, DateTime.now()).claimedToday ||
          (nextAd != null && nextAd.isAfter(DateTime.now().toUtc()))) {
        setState(() {});
      }
    });
    load();
  }

  @override
  void dispose() {
    _clock?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    code.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) load();
  }

  static List<num> _attendanceCoins(JsonMap cfg) => [
    for (final c in (cfg['attendance_coins'] as List? ?? const []))
      if (c is num) c,
  ];

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
      if (mounted) liveNotice(context, context.l10n.rewardsOperationDone);
    } catch (e) {
      if (mounted) liveNotice(context, '$e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
    await load();
  }

  /// Marca la asistencia y celebra con monedas si se acreditó.
  Future<void> claim() async {
    if (busy) return;
    setState(() => busy = true);
    try {
      final result = jsonMap(
        await widget.api.request('/mobile/v1/rewards/attendance', body: {}),
      );
      if (!mounted) return;
      if (result['credited'] == true) {
        HapticFeedback.mediumImpact();
        setState(() {
          _burst++;
          _burstLabel = context.l10n.rewardsClaimed(result['coins'] ?? '');
        });
      } else {
        liveNotice(context, context.l10n.rewardsOperationDone);
      }
    } catch (e) {
      if (mounted) liveNotice(context, '$e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
    await load();
  }

  Future<void> offer(String provider) async {
    if (openingOffer || busy) return;
    setState(() => openingOffer = true);
    try {
      final result = jsonMap(
        await widget.api.request(
          '/mobile/v1/rewards/offers/$provider',
          body: {},
        ),
      );
      const channel = MethodChannel('quantfut/offers');
      if (result['sdk'] == 'tapjoy') {
        await channel.invokeMethod<bool>('tapjoy', {
          'sdk_key': result['sdk_key'],
          'user_id': result['user_id'],
          'placement': 'coins_offerwall',
        });
      } else {
        await channel.invokeMethod<bool>('open', {'url': result['url']});
      }
    } on PlatformException catch (e) {
      if (mounted) {
        final l10n = context.l10n;
        liveNotice(context, switch (e.code) {
          'tapjoy_unavailable' => l10n.rewardsOffersUnavailable,
          'tapjoy_timeout' => l10n.rewardsOffersTimeout,
          'tapjoy_config' || 'invalid_url' => l10n.rewardsOffersConfig,
          _ => l10n.rewardsOffersLoadFailed,
        });
      }
    } on ApiFailure catch (e) {
      if (mounted) liveNotice(context, e.message);
    } catch (_) {
      if (mounted) liveNotice(context, context.l10n.rewardsOffersLoadFailed);
    } finally {
      if (mounted) setState(() => openingOffer = false);
    }
  }

  /// Ver un video con recompensa. La celebración sale de la diferencia de saldo que
  /// confirma el servidor; la app nunca acredita monedas por su cuenta.
  Future<void> watchAd() async {
    if (watchingAd || busy) return;
    final l10n = context.l10n;
    setState(() {
      watchingAd = true;
      adStatus = l10n.adsLoading;
    });
    String? message;
    try {
      final out = await RewardedAdFlow(
        api: widget.api,
        gateway: _adGateway,
        onVerifying: () {
          if (mounted) setState(() => adStatus = l10n.adsVerifying);
        },
      ).run();
      if (!mounted) return;
      switch (out.result) {
        case AdResult.credited:
          HapticFeedback.mediumImpact();
          setState(() {
            _burst++;
            _burstLabel = l10n.rewardsClaimed(out.coins);
          });
        case AdResult.pending:
          message = l10n.adsPending;
        case AdResult.unavailable:
          message = l10n.adsUnavailable;
        case AdResult.dismissed || AdResult.limit || AdResult.waiting:
          break;
      }
    } on ApiFailure catch (e) {
      message = e.message;
    } catch (_) {
      message = l10n.adsUnavailable;
    } finally {
      if (mounted) {
        setState(() {
          watchingAd = false;
          adStatus = message;
        });
      }
    }
    await load();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final cfg = jsonMap(data?['settings']),
        wallet = jsonMap(data?['wallet']),
        refs = jsonMap(data?['referrals']);
    final signedIn = data?['signed_in'] == true;
    return Scaffold(
      backgroundColor: QfColors.bg,
      appBar: AppBar(
        backgroundColor: QfColors.bg,
        foregroundColor: QfColors.text,
        automaticallyImplyLeading: !widget.embedded,
        title: Text(
          l10n.navCoins,
          style: const TextStyle(fontFamily: qfDisplay, fontWeight: FontWeight.w700, fontSize: 22),
        ),
        actions: [
          IconButton(
            tooltip: l10n.rewardsRefreshBalance,
            onPressed: busy ? null : load,
            icon: const Icon(Icons.refresh, color: QfColors.primary),
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
                          liveText(error!, color: QfColors.text2),
                          liveButton(l10n.commonRetry, load, color: QfColors.primary),
                        ],
                      ),
                    ),
            )
          : Stack(
              children: [
                RefreshIndicator(
                  onRefresh: load,
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      if (busy) const LinearProgressIndicator(),
                      _Hero(cfg: cfg, wallet: wallet, signedIn: signedIn),
                      if (cfg['enabled'] != true) training('${cfg['message']}'),
                      if (!signedIn) training(l10n.rewardsSignInHint),
                      qfTitle(l10n.rewardsEarnTitle, size: 17),
                      const SizedBox(height: 6),
                      _AttendanceCard(
                        cfg: cfg,
                        wallet: wallet,
                        busy: busy,
                        onClaim: claim,
                      ),
                      AdsCard(
                        ads: jsonMap(data?['ads']),
                        enabled: !busy && !watchingAd && widget.api.signedIn,
                        status: adStatus,
                        onWatch: watchAd,
                      ),
                      _OffersCard(
                        providers: jsonRows(data?['providers']),
                        unlockCost: cfg['unlock_cost'],
                        enabled: !busy && !openingOffer && widget.api.signedIn,
                        onOffer: offer,
                      ),
                      _InviteCard(
                        base: widget.api.base,
                        cfg: cfg,
                        wallet: wallet,
                        refs: refs,
                        signedIn: signedIn,
                        codeController: code,
                        canRegister: !busy && cfg['referrals_enabled'] == true,
                        onRegister: () => action(
                          '/mobile/v1/rewards/referrals',
                          body: {'code': inviteCodeFrom(code.text) ?? code.text.trim()},
                        ),
                      ),
                      _Ledger(
                        rows: jsonRows(data?['ledger']),
                        open: _ledgerOpen,
                        onToggle: () =>
                            setState(() => _ledgerOpen = !_ledgerOpen),
                      ),
                      _Terms(
                        text: '${data?['terms'] ?? ''}',
                        open: _termsOpen,
                        onToggle: () => setState(() => _termsOpen = !_termsOpen),
                      ),
                      const SizedBox(height: 24),
                    ],
                  ),
                ),
                if (_burst > 0)
                  Positioned.fill(
                    child: CoinBurst(
                      key: ValueKey(_burst),
                      label: _burstLabel,
                    ),
                  ),
              ],
            ),
    );
  }
}

/// Saldo en mono, avance hacia el siguiente desbloqueo y los dos datos que más importan.
class _Hero extends StatelessWidget {
  const _Hero({required this.cfg, required this.wallet, required this.signedIn});

  final JsonMap cfg, wallet;
  final bool signedIn;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final cost = cfg['unlock_cost'] as num?;
    final balance = (wallet['spendable'] as num?) ?? 0;
    final progress = unlockProgress(balance, cost);
    final unlocks = cost == null || cost <= 0 ? 0 : balance ~/ cost;
    final attendance = AttendanceState.of(
      wallet,
      _RewardsScreenState._attendanceCoins(cfg),
      DateTime.now(),
    );
    return Padding(
      key: const ValueKey('coins-hero'),
      padding: const EdgeInsets.only(bottom: 16),
      child: QfCard(
        accent: QfColors.cta,
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            liveText(l10n.rewardsMyCoins, color: QfColors.text2, size: 13),
            const SizedBox(height: 4),
            Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Expanded(
                  child: FittedBox(
                    fit: BoxFit.scaleDown,
                    alignment: Alignment.centerLeft,
                    child: Text(
                      signedIn ? '${wallet['balance'] ?? 0}' : l10n.rewardsSignIn,
                      style: TextStyle(
                        color: QfColors.text,
                        fontFamily: signedIn ? qfMono : qfDisplay,
                        fontWeight: signedIn ? FontWeight.w500 : FontWeight.w700,
                        fontSize: 38,
                        height: 1.1,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Text(
                  realPercent(progress.fraction),
                  style: const TextStyle(fontFamily: qfMono, fontSize: 13, color: QfColors.text2),
                ),
              ],
            ),
            const SizedBox(height: 8),
            SegmentedBar(
              total: 10,
              filled: (progress.fraction * 10).floor(),
              color: QfColors.cta,
            ),
            const SizedBox(height: 8),
            liveText(
              cost == null
                  ? l10n.rewardsMissingUnknown
                  : progress.missing == 0
                  ? l10n.rewardsUnlocksAvailable(unlocks)
                  : l10n.rewardsMissing(progress.missing),
              size: 12,
              color: QfColors.text2,
            ),
            if ((wallet['balance'] as num?) != null &&
                (wallet['balance'] as num) < 0)
              Row(
                children: [
                  const Icon(Icons.error_outline, size: 14, color: QfColors.danger),
                  const SizedBox(width: 4),
                  Expanded(child: liveText(l10n.rewardsDebt, color: QfColors.danger, size: 12)),
                ],
              ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 6,
              children: [
                if (signedIn && attendance.streak > 0)
                  _HeroChip(
                    Icons.local_fire_department,
                    l10n.rewardsChipStreak(attendance.streak),
                    QfColors.success,
                  ),
                _HeroChip(Icons.lock_open, l10n.rewardsChipRate(cost ?? '—'), QfColors.text2),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

/// Insignia con borde de 1 dp y esquina cortada (sin mayúsculas: lleva cifras y frases).
class _HeroChip extends StatelessWidget {
  const _HeroChip(this.icon, this.label, this.color);

  final IconData icon;
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: ShapeDecoration(
      shape: CutCornerBorder(cut: 8, side: BorderSide(color: color)),
    ),
    child: Padding(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: color),
          const SizedBox(width: 5),
          Flexible(
            child: Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(color: color, fontFamily: 'Gilroy Bold', fontSize: 11),
            ),
          ),
        ],
      ),
    ),
  );
}

/// Asistencia diaria: la semana en 7 casillas (hechas con ✓, hoy con borde ámbar) y la
/// única acción ámbar de la pestaña, o la cuenta atrás si ya se marcó.
class _AttendanceCard extends StatelessWidget {
  const _AttendanceCard({
    required this.cfg,
    required this.wallet,
    required this.busy,
    required this.onClaim,
  });

  final JsonMap cfg, wallet;
  final bool busy;
  final VoidCallback onClaim;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final coins = _RewardsScreenState._attendanceCoins(cfg);
    final state = AttendanceState.of(wallet, coins, DateTime.now());
    final canClaim = !busy && wallet['can_check_in'] == true;
    return Padding(
      key: const ValueKey('coins-attendance'),
      padding: const EdgeInsets.only(bottom: 12),
      child: QfCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        l10n.rewardsAttendanceTitle.toUpperCase(),
                        style: const TextStyle(
                          fontFamily: qfDisplay,
                          fontWeight: FontWeight.w700,
                          fontSize: 15,
                          color: QfColors.text,
                        ),
                      ),
                      const SizedBox(height: 2),
                      liveText(l10n.rewardsAttendanceSub, size: 12, color: QfColors.text2),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                _StatusChip(
                  label: state.claimedToday ? l10n.rewardsClaimedToday : l10n.rewardsAvailable,
                  color: state.claimedToday ? QfColors.text2 : QfColors.success,
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                for (var i = 0; i < coins.length; i++) ...[
                  if (i > 0) const SizedBox(width: 4),
                  Expanded(
                    child: _dayCell(
                      i,
                      coins: coins[i],
                      label: i == state.todayIndex && !state.claimedToday
                          ? l10n.commonToday
                          : l10n.rewardsDay(i + 1),
                      done: i < state.claimedDays,
                      today: i == state.todayIndex && !state.claimedToday,
                    ),
                  ),
                ],
              ],
            ),
            const SizedBox(height: 12),
            if (state.claimedToday)
              Container(
                key: const ValueKey('coins-countdown'),
                width: double.infinity,
                constraints: const BoxConstraints(minHeight: 48),
                decoration: ShapeDecoration(
                  shape: const CutCornerBorder(cut: 8, side: BorderSide(color: QfColors.success)),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.check, size: 18, color: QfColors.success),
                    const SizedBox(width: 8),
                    Flexible(
                      child: Text(
                        l10n.rewardsNextIn(AttendanceState.clock(state.untilReset)),
                        style: const TextStyle(fontFamily: qfMono, fontSize: 13, color: QfColors.success),
                      ),
                    ),
                  ],
                ),
              )
            else
              SizedBox(
                width: double.infinity,
                height: 48,
                child: FilledButton(
                  key: const ValueKey('coins-claim'),
                  style: qfFilled(QfColors.cta),
                  onPressed: canClaim ? onClaim : null,
                  child: Text(
                    state.nextCoins == null
                        ? l10n.rewardsCheckIn
                        : l10n.rewardsClaimCta(state.nextCoins!),
                  ),
                ),
              ),
            const SizedBox(height: 8),
            liveText(l10n.rewardsCheckInNote, size: 11, color: QfColors.text2),
          ],
        ),
      ),
    );
  }

  /// Casilla de un día: hecha (verde con ✓), hoy (borde ámbar) o pendiente.
  static Widget _dayCell(
    int i, {
    required num coins,
    required String label,
    required bool done,
    required bool today,
  }) {
    final fg = done ? QfColors.success : (today ? QfColors.cta : QfColors.text2);
    return Container(
      key: ValueKey('coins-day-$i'),
      padding: const EdgeInsets.symmetric(vertical: 8),
      decoration: BoxDecoration(
        color: done ? QfColors.success.withValues(alpha: .16) : QfColors.surface2,
        border: today ? Border.all(color: QfColors.cta, width: 1.5) : null,
      ),
      child: Column(
        children: [
          if (done)
            const Icon(Icons.check, size: 16, color: QfColors.success)
          else
            Icon(Icons.toll, size: 16, color: fg),
          const SizedBox(height: 2),
          FittedBox(
            fit: BoxFit.scaleDown,
            child: Text(
              '+${coins.toInt()}',
              style: TextStyle(color: fg, fontFamily: qfMono, fontSize: 12),
            ),
          ),
          FittedBox(
            fit: BoxFit.scaleDown,
            child: Text(label, style: TextStyle(color: fg, fontSize: 9)),
          ),
        ],
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: ShapeDecoration(
      color: color.withValues(alpha: .13),
      shape: CutCornerBorder(cut: 8, side: BorderSide(color: color)),
    ),
    child: Padding(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      child: Text(
        label,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: TextStyle(color: color, fontFamily: 'Gilroy Bold', fontSize: 11),
      ),
    ),
  );
}

/// Ofertas: el proveedor disponible como tarjeta con un botón grande, y los demás en una línea.
class _OffersCard extends StatelessWidget {
  const _OffersCard({
    required this.providers,
    required this.unlockCost,
    required this.enabled,
    required this.onOffer,
  });

  final List<JsonMap> providers;
  final Object? unlockCost;
  final bool enabled;
  final void Function(String provider) onOffer;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final ready = providers.where((p) => p['available'] == true).toList();
    final soon = [
      for (final p in providers)
        if (p['available'] != true) '${p['name']}',
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final p in ready)
          Padding(
            key: ValueKey('coins-offer-${p['provider']}'),
            padding: const EdgeInsets.only(bottom: 12),
            child: QfCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      width: 40,
                      height: 40,
                      color: QfColors.surface2,
                      child: const Icon(Icons.rocket_launch_outlined, color: QfColors.primary, size: 22),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          liveText(l10n.rewardsOffersTitle, size: 15, bold: true),
                          const SizedBox(height: 2),
                          liveText(
                            '${l10n.rewardsOffersLead} ${l10n.rewardsChipRate(unlockCost ?? '—')}',
                            size: 12,
                            color: QfColors.text2,
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    style: qfFilled(QfColors.primary),
                    onPressed: enabled ? () => onOffer('${p['provider']}') : null,
                    child: Text(l10n.rewardsOffersCta),
                  ),
                ),
                const SizedBox(height: 8),
                liveText(l10n.rewardsOfferAvailable, size: 11, color: QfColors.text2),
              ],
            ),
          ),
          ),
        if (ready.isEmpty)
          training(l10n.rewardsOffersUnavailable),
        if (soon.isNotEmpty)
          Padding(
            key: const ValueKey('coins-coming-soon'),
            padding: const EdgeInsets.fromLTRB(4, 0, 4, 14),
            child: liveText(
              l10n.rewardsComingSoon(soon.join(', ')),
              size: 11,
              color: QfColors.text2,
            ),
          ),
      ],
    );
  }
}

/// Invitar amigos: premios, código para copiar y, si procede, dónde escribir el de quien invitó.
class _InviteCard extends StatelessWidget {
  const _InviteCard({
    required this.base,
    required this.cfg,
    required this.wallet,
    required this.refs,
    required this.signedIn,
    required this.codeController,
    required this.canRegister,
    required this.onRegister,
  });

  final Uri base;
  final JsonMap cfg, wallet, refs;
  final bool signedIn;
  final TextEditingController codeController;
  final bool canRegister;
  final VoidCallback onRegister;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final myCode = wallet['referral_code'];
    return Padding(
      key: const ValueKey('coins-invite'),
      padding: const EdgeInsets.only(bottom: 12),
      child: QfCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: liveText(l10n.rewardsInviteTitle, size: 15, bold: true),
              ),
              _StatusChip(
                label: l10n.rewardsInviteChip(cfg['referrer_coins'] ?? '—'),
                color: QfColors.primary,
              ),
            ],
          ),
          const SizedBox(height: 4),
          liveText(
            l10n.rewardsInviteFriend(cfg['invitee_coins'] ?? '—'),
            size: 12,
            color: QfColors.text2,
          ),
          if (myCode != null) ...[
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: Container(
                    constraints: const BoxConstraints(minHeight: 44),
                    alignment: Alignment.center,
                    color: QfColors.surface2,
                    child: Text(
                      '$myCode',
                      style: const TextStyle(
                        color: QfColors.text,
                        fontFamily: qfMono,
                        fontSize: 17,
                        letterSpacing: 2,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                FilledButton.icon(
                  style: qfFilled(QfColors.primary),
                  onPressed: () async {
                    await Clipboard.setData(ClipboardData(text: '$myCode'));
                    if (context.mounted) {
                      liveNotice(context, l10n.rewardsCodeCopied);
                    }
                  },
                  icon: const Icon(Icons.copy, size: 16),
                  label: Text(l10n.rewardsCopy),
                ),
              ],
            ),
            const SizedBox(height: 10),
            OutlinedButton.icon(
              key: const ValueKey('coins-share'),
              style: OutlinedButton.styleFrom(
                foregroundColor: QfColors.primary,
                side: const BorderSide(color: QfColors.primary),
                minimumSize: const Size.fromHeight(44),
                shape: const CutCornerBorder(cut: 8),
              ),
              onPressed: () {
                MetaEvents.current?.invite();
                SharePlus.instance.share(
                  ShareParams(text: inviteShareText(l10n, base, '$myCode')),
                );
              },
              icon: const Icon(Icons.share_outlined, size: 18),
              label: Text(l10n.rewardsShare),
            ),
            const SizedBox(height: 10),
            liveText(
              l10n.rewardsReferralStats(
                refs['registered'] ?? 0,
                refs['qualified'] ?? 0,
              ),
              size: 12,
              color: QfColors.text2,
            ),
          ],
          const SizedBox(height: 6),
          liveText(
            l10n.rewardsInviteCondition(cfg['referral_min_coins'] ?? '—'),
            color: QfColors.text2,
            size: 11,
          ),
          if (signedIn && refs['joined'] == null) ...[
            const SizedBox(height: 14),
            TextField(
              controller: codeController,
              textCapitalization: TextCapitalization.characters,
              decoration: InputDecoration(
                labelText: l10n.rewardsInviterCode,
                suffixIcon: IconButton(
                  key: const ValueKey('coins-paste'),
                  tooltip: l10n.rewardsPaste,
                  icon: const Icon(Icons.content_paste, size: 20),
                  onPressed: () async {
                    final pasted = await Clipboard.getData(Clipboard.kTextPlain);
                    final found = inviteCodeFrom(pasted?.text ?? '');
                    if (found == null) {
                      if (context.mounted) {
                        liveNotice(context, l10n.rewardsPasteEmpty);
                      }
                      return;
                    }
                    codeController.text = found;
                  },
                ),
              ),
            ),
            const SizedBox(height: 10),
            liveButton(
              l10n.rewardsRegisterCode,
              canRegister ? onRegister : null,
              color: QfColors.primary,
            ),
          ] else if (refs['joined'] != null) ...[
            const SizedBox(height: 12),
            Row(
              children: [
                const Icon(Icons.check, size: 16, color: QfColors.success),
                const SizedBox(width: 6),
                Expanded(child: liveText(l10n.rewardsCodeRegistered, color: QfColors.success)),
              ],
            ),
          ],
        ],
      ),
      ),
    );
  }
}

/// Últimos movimientos; el resto se despliega.
class _Ledger extends StatelessWidget {
  const _Ledger({required this.rows, required this.open, required this.onToggle});

  final List<JsonMap> rows;
  final bool open;
  final VoidCallback onToggle;

  static const _preview = 5;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final shown = open ? rows : rows.take(_preview).toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        qfTitle(l10n.rewardsLedgerTitle, size: 17),
        const SizedBox(height: 6),
        if (rows.isEmpty)
          training(l10n.rewardsLedgerEmpty)
        else ...[
          for (final r in shown)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 10),
              decoration: const BoxDecoration(
                border: Border(top: BorderSide(color: QfColors.border)),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: liveText(
                      '${ledgerKindLabel(l10n, r['kind'])}\n${kickoffText(r['created_at'])}',
                      size: 12,
                      color: QfColors.text2,
                    ),
                  ),
                  Text(
                    '${(r['delta'] as num) >= 0 ? '+' : ''}${r['delta']}',
                    style: TextStyle(
                      fontFamily: qfMono,
                      fontSize: 13,
                      color: (r['delta'] as num) >= 0 ? QfColors.success : QfColors.text,
                    ),
                  ),
                ],
              ),
            ),
          if (rows.length > _preview)
            InkWell(
              key: const ValueKey('coins-ledger-toggle'),
              onTap: onToggle,
              child: Container(
                constraints: const BoxConstraints(minHeight: 48),
                padding: const EdgeInsets.symmetric(horizontal: 4),
                decoration: const BoxDecoration(
                  border: Border(top: BorderSide(color: QfColors.border)),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: liveText(
                        open ? l10n.rewardsLedgerLess : l10n.rewardsLedgerMore,
                        size: 13,
                        bold: true,
                        color: QfColors.primary,
                      ),
                    ),
                    Icon(open ? Icons.expand_less : Icons.expand_more, color: QfColors.primary),
                  ],
                ),
              ),
            ),
        ],
      ],
    );
  }
}

/// Términos de las monedas, plegados para que no ocupen la pantalla.
class _Terms extends StatelessWidget {
  const _Terms({required this.text, required this.open, required this.onToggle});

  final String text;
  final bool open;
  final VoidCallback onToggle;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      InkWell(
        key: const ValueKey('coins-terms-toggle'),
        onTap: onToggle,
        child: ConstrainedBox(
          constraints: const BoxConstraints(minHeight: 48),
          child: Row(
            children: [
              const Icon(Icons.info_outline, size: 18, color: QfColors.text2),
              const SizedBox(width: 8),
              Expanded(
                child: liveText(
                  context.l10n.rewardsTermsTitle,
                  size: 13,
                  color: QfColors.text2,
                  bold: true,
                ),
              ),
              Icon(open ? Icons.expand_less : Icons.expand_more, color: QfColors.text2),
            ],
          ),
        ),
      ),
      if (open) liveText(text, color: QfColors.text2, size: 11),
    ],
  );
}
