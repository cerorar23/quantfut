import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:share_plus/share_plus.dart';

import '../l10n/app_locale.dart';
import 'coin_burst.dart';
import 'live_ads.dart';
import '../core/meta_events.dart';
import 'live_api.dart';
import 'live_widgets.dart';
import 'rewards_progress.dart';

const _purple = Color(0xff7439c5), _purpleDark = Color(0xff3d1c80);
const _pink = Color(0xffff426f);
const _tile = Color(0xff0e1b2a);

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
      backgroundColor: liveBg,
      appBar: AppBar(
        backgroundColor: liveBg,
        foregroundColor: Colors.white,
        automaticallyImplyLeading: !widget.embedded,
        title: Text(l10n.navCoins),
        actions: [
          IconButton(
            tooltip: l10n.rewardsRefreshBalance,
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
                          liveButton(l10n.commonRetry, load),
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
                      Padding(
                        padding: const EdgeInsets.fromLTRB(2, 6, 0, 10),
                        child: liveText(
                          l10n.rewardsEarnTitle,
                          size: 19,
                          bold: true,
                        ),
                      ),
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

/// Saldo, avance hacia el siguiente desbloqueo y los dos datos que más importan.
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
    final attendance = AttendanceState.of(
      wallet,
      _RewardsScreenState._attendanceCoins(cfg),
      DateTime.now(),
    );
    return Container(
      key: const ValueKey('coins-hero'),
      padding: const EdgeInsets.all(18),
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [_purple, _purpleDark],
        ),
        borderRadius: BorderRadius.circular(22),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    liveText(l10n.rewardsMyCoins, color: const Color(0xffe3d4ff)),
                    const SizedBox(height: 4),
                    FittedBox(
                      fit: BoxFit.scaleDown,
                      alignment: Alignment.centerLeft,
                      child: Text(
                        signedIn ? '${wallet['balance'] ?? 0}' : l10n.rewardsSignIn,
                        style: const TextStyle(
                          color: liveGold,
                          fontFamily: 'Gilroy ExtraBold',
                          fontSize: 40,
                          height: 1.1,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              _Ring(fraction: progress.fraction),
            ],
          ),
          const SizedBox(height: 10),
          liveText(
            cost == null
                ? l10n.rewardsMissingUnknown
                : progress.missing == 0
                ? l10n.rewardsEnough
                : l10n.rewardsMissing(progress.missing),
            size: 12,
            color: const Color(0xffe3d4ff),
          ),
          if ((wallet['balance'] as num?) != null &&
              (wallet['balance'] as num) < 0)
            liveText(l10n.rewardsDebt, color: liveGold, size: 12),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 6,
            children: [
              if (signedIn && attendance.streak > 0)
                _HeroChip(
                  Icons.local_fire_department,
                  l10n.rewardsChipStreak(attendance.streak),
                ),
              _HeroChip(Icons.lock_open, l10n.rewardsChipRate(cost ?? '—')),
            ],
          ),
        ],
      ),
    );
  }
}

class _HeroChip extends StatelessWidget {
  const _HeroChip(this.icon, this.label);

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
    decoration: BoxDecoration(
      color: Colors.white.withValues(alpha: .16),
      borderRadius: BorderRadius.circular(99),
    ),
    child: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 14, color: liveGold),
        const SizedBox(width: 5),
        Flexible(
          child: Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: Colors.white,
              fontFamily: 'Gilroy Bold',
              fontSize: 11,
            ),
          ),
        ),
      ],
    ),
  );
}

/// Anillo de avance con el porcentaje en el centro.
class _Ring extends StatelessWidget {
  const _Ring({required this.fraction});

  final double fraction;

  @override
  Widget build(BuildContext context) {
    final still = MediaQuery.of(context).disableAnimations;
    return TweenAnimationBuilder<double>(
      tween: Tween(end: fraction),
      duration: still ? Duration.zero : const Duration(milliseconds: 800),
      curve: Curves.easeOutCubic,
      builder: (context, value, _) => SizedBox.square(
        dimension: 76,
        child: CustomPaint(
          painter: _RingPainter(value),
          child: Center(
            child: Text(
              realPercent(fraction),
              style: const TextStyle(
                color: Colors.white,
                fontFamily: 'Gilroy Bold',
                fontSize: 15,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _RingPainter extends CustomPainter {
  const _RingPainter(this.value);

  final double value;

  @override
  void paint(Canvas canvas, Size size) {
    final rect = (Offset.zero & size).deflate(5);
    final base = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 7
      ..color = Colors.white24;
    canvas.drawArc(rect, 0, 2 * math.pi, false, base);
    if (value <= 0) return;
    canvas.drawArc(
      rect,
      -math.pi / 2,
      2 * math.pi * value.clamp(0, 1),
      false,
      base
        ..strokeCap = StrokeCap.round
        ..color = liveGold,
    );
  }

  @override
  bool shouldRepaint(_RingPainter oldDelegate) => oldDelegate.value != value;
}

/// Asistencia diaria: 7 días, el de hoy resaltado, y un botón o la cuenta atrás.
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
    return Container(
      key: const ValueKey('coins-attendance'),
      margin: const EdgeInsets.only(bottom: 14),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: livePanel,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: liveGold.withValues(alpha: .4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    liveText(l10n.rewardsAttendanceTitle, size: 15, bold: true),
                    const SizedBox(height: 2),
                    liveText(
                      l10n.rewardsAttendanceSub,
                      size: 12,
                      color: liveMuted,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              _StatusChip(
                label: state.claimedToday
                    ? l10n.rewardsClaimedToday
                    : l10n.rewardsAvailable,
                color: state.claimedToday ? liveMuted : liveGreen,
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              for (var i = 0; i < coins.length; i++) ...[
                if (i > 0) const SizedBox(width: 5),
                Expanded(
                  child: _DayCell(
                    key: ValueKey('coins-day-$i'),
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
          const SizedBox(height: 14),
          if (state.claimedToday)
            Container(
              key: const ValueKey('coins-countdown'),
              width: double.infinity,
              padding: const EdgeInsets.symmetric(vertical: 14),
              decoration: BoxDecoration(
                color: _tile,
                borderRadius: BorderRadius.circular(99),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.schedule, size: 18, color: liveMuted),
                  const SizedBox(width: 8),
                  liveText(
                    l10n.rewardsNextIn(AttendanceState.clock(state.untilReset)),
                    size: 13,
                    color: liveMuted,
                    bold: true,
                  ),
                ],
              ),
            )
          else
            SizedBox(
              width: double.infinity,
              child: FilledButton(
                key: const ValueKey('coins-claim'),
                style: FilledButton.styleFrom(
                  backgroundColor: _pink,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.all(15),
                  shape: const StadiumBorder(),
                ),
                onPressed: canClaim ? onClaim : null,
                child: Text(
                  state.nextCoins == null
                      ? l10n.rewardsCheckIn
                      : l10n.rewardsClaimCta(state.nextCoins!),
                  style: const TextStyle(fontFamily: 'Gilroy Bold', fontSize: 15),
                ),
              ),
            ),
          const SizedBox(height: 8),
          liveText(l10n.rewardsCheckInNote, size: 11, color: liveMuted),
        ],
      ),
    );
  }
}

class _DayCell extends StatelessWidget {
  const _DayCell({
    super.key,
    required this.coins,
    required this.label,
    required this.done,
    required this.today,
  });

  final num coins;
  final String label;
  final bool done;
  final bool today;

  @override
  Widget build(BuildContext context) {
    final fg = today ? liveBg : (done ? liveGreen : liveMuted);
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 9),
      decoration: BoxDecoration(
        color: today
            ? liveGold
            : (done ? liveGreen.withValues(alpha: .16) : _tile),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        children: [
          Icon(done ? Icons.check_circle : Icons.toll, size: 18, color: today ? liveBg : (done ? liveGreen : liveGold)),
          const SizedBox(height: 2),
          FittedBox(
            fit: BoxFit.scaleDown,
            child: Text(
              '+${coins.toInt()}',
              style: TextStyle(color: fg, fontFamily: 'Gilroy Bold', fontSize: 12),
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
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
    decoration: BoxDecoration(
      color: color.withValues(alpha: .16),
      borderRadius: BorderRadius.circular(99),
    ),
    child: Text(
      label,
      maxLines: 1,
      overflow: TextOverflow.ellipsis,
      style: TextStyle(color: color, fontFamily: 'Gilroy Bold', fontSize: 11),
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
          Container(
            key: ValueKey('coins-offer-${p['provider']}'),
            margin: const EdgeInsets.only(bottom: 14),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: livePanel,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: liveCyan.withValues(alpha: .35)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.rocket_launch_outlined, color: liveGold, size: 28),
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
                            color: liveMuted,
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
                    style: FilledButton.styleFrom(
                      backgroundColor: liveCyan,
                      foregroundColor: liveBg,
                      padding: const EdgeInsets.all(15),
                      shape: const StadiumBorder(),
                    ),
                    onPressed: enabled ? () => onOffer('${p['provider']}') : null,
                    child: Text(
                      l10n.rewardsOffersCta,
                      style: const TextStyle(fontFamily: 'Gilroy Bold', fontSize: 15),
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                liveText(l10n.rewardsOfferAvailable, size: 11, color: liveMuted),
              ],
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
              color: liveMuted,
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
    return Container(
      key: const ValueKey('coins-invite'),
      margin: const EdgeInsets.only(bottom: 14),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: livePanel,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: liveGold.withValues(alpha: .3)),
      ),
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
                color: liveGold,
              ),
            ],
          ),
          const SizedBox(height: 4),
          liveText(
            l10n.rewardsInviteFriend(cfg['invitee_coins'] ?? '—'),
            size: 12,
            color: liveMuted,
          ),
          if (myCode != null) ...[
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: _tile,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: const Color(0xff4a5d73)),
                    ),
                    child: Text(
                      '$myCode',
                      style: const TextStyle(
                        color: Colors.white,
                        fontFamily: 'Gilroy ExtraBold',
                        fontSize: 18,
                        letterSpacing: 2,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                FilledButton.icon(
                  style: FilledButton.styleFrom(
                    backgroundColor: liveCyan,
                    foregroundColor: liveBg,
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                  ),
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
                foregroundColor: liveCyan,
                side: const BorderSide(color: liveCyan),
                minimumSize: const Size.fromHeight(44),
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
              color: liveMuted,
            ),
          ],
          const SizedBox(height: 6),
          liveText(
            l10n.rewardsInviteCondition(cfg['referral_min_coins'] ?? '—'),
            color: liveMuted,
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
            ),
          ] else if (refs['joined'] != null) ...[
            const SizedBox(height: 12),
            liveText(l10n.rewardsCodeRegistered, color: liveGreen),
          ],
        ],
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
        Padding(
          padding: const EdgeInsets.fromLTRB(2, 6, 0, 10),
          child: liveText(l10n.rewardsLedgerTitle, size: 19, bold: true),
        ),
        if (rows.isEmpty)
          training(l10n.rewardsLedgerEmpty)
        else ...[
          for (final r in shown)
            Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: livePanel,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: liveText(
                      '${ledgerKindLabel(l10n, r['kind'])}\n${kickoffText(r['created_at'])}',
                      size: 12,
                      color: liveMuted,
                    ),
                  ),
                  liveText(
                    '${(r['delta'] as num) >= 0 ? '+' : ''}${r['delta']}',
                    bold: true,
                    color: (r['delta'] as num) >= 0 ? liveGreen : liveGold,
                  ),
                ],
              ),
            ),
          if (rows.length > _preview)
            InkWell(
              key: const ValueKey('coins-ledger-toggle'),
              borderRadius: BorderRadius.circular(10),
              onTap: onToggle,
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 10),
                child: Row(
                  children: [
                    Expanded(
                      child: liveText(
                        open ? l10n.rewardsLedgerLess : l10n.rewardsLedgerMore,
                        size: 13,
                        bold: true,
                        color: liveCyan,
                      ),
                    ),
                    Icon(open ? Icons.expand_less : Icons.expand_more, color: liveCyan),
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
        borderRadius: BorderRadius.circular(10),
        onTap: onToggle,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 12),
          child: Row(
            children: [
              const Icon(Icons.info_outline, size: 18, color: liveMuted),
              const SizedBox(width: 8),
              Expanded(
                child: liveText(
                  context.l10n.rewardsTermsTitle,
                  size: 13,
                  color: liveMuted,
                  bold: true,
                ),
              ),
              Icon(open ? Icons.expand_less : Icons.expand_more, color: liveMuted),
            ],
          ),
        ),
      ),
      if (open) liveText(text, color: liveMuted, size: 11),
    ],
  );
}
