import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import 'live_api.dart';
import 'live_rewards.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';

/// Pantalla «Mis movimientos» con tarjeta de saldo/ganadas/gastadas,
/// lista agrupada por día, iconos por tipo y botón de ver más/menos.
class MovimientosScreen extends StatefulWidget {
  const MovimientosScreen({
    super.key,
    required this.api,
    required this.wallet,
    this.ledger,
  });

  final QuantFutApi api;
  final JsonMap wallet;
  final List<JsonMap>? ledger;

  @override
  State<MovimientosScreen> createState() => _MovimientosScreenState();
}

class _MovimientosScreenState extends State<MovimientosScreen> {
  List<JsonMap>? _rows;
  bool _open = false;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _rows = widget.ledger;
    if (_rows == null) {
      _load();
    }
  }

  Future<void> _load() async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final res = jsonMap(await widget.api.request('/mobile/v1/rewards'));
      if (mounted) {
        setState(() {
          _rows = jsonRows(res['ledger']);
        });
      }
    } catch (_) {
      // Si falla la red se conserva lo que haya
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  static String _groupLabel(AppLocalizations l10n, dynamic createdAt) {
    if (createdAt == null) return l10n.rewardsLedgerEarlier.toUpperCase();
    final parsed = DateTime.tryParse('$createdAt');
    if (parsed == null) return l10n.rewardsLedgerEarlier.toUpperCase();
    final d = parsed.toUtc();
    final now = DateTime.now().toUtc();
    final today = DateTime.utc(now.year, now.month, now.day);
    final target = DateTime.utc(d.year, d.month, d.day);
    if (target == today) return l10n.commonToday.toUpperCase();
    if (target == today.subtract(const Duration(days: 1))) {
      return l10n.commonYesterday.toUpperCase();
    }
    return l10n.rewardsLedgerEarlier.toUpperCase();
  }

  static IconData _iconForKind(Object? kind) => switch (kind) {
    'attendance' => Icons.check,
    'offer' => Icons.card_giftcard,
    'unlock' => Icons.lock_open,
    'referrer' || 'invitee' => Icons.group,
    'reversal' || 'referral_reversal' => Icons.undo,
    'ad' => Icons.play_arrow,
    _ => Icons.toll,
  };

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final allRows = _rows ?? jsonRows(widget.ledger);
    final rows = _open ? allRows : allRows.take(5).toList();
    final isEmpty = allRows.isEmpty;

    // Calcular ganadas y gastadas del ledger
    var earned = 0;
    var spent = 0;
    for (final r in allRows) {
      final delta = (r['delta'] as num?)?.toInt() ?? 0;
      if (delta > 0) {
        earned += delta;
      } else if (delta < 0) {
        spent += delta.abs();
      }
    }
    final balance = widget.wallet['balance'] ?? 0;

    return Scaffold(
      backgroundColor: QfColors.bg,
      appBar: AppBar(
        backgroundColor: QfColors.bg,
        foregroundColor: QfColors.text,
        elevation: 0,
        title: Text(
          l10n.rewardsLedgerTitle.toUpperCase(),
          style: const TextStyle(
            fontFamily: qfDisplay,
            fontWeight: FontWeight.w700,
            fontSize: 18,
            letterSpacing: 1.4,
          ),
        ),
        bottom: const PreferredSize(
          preferredSize: Size.fromHeight(1),
          child: Divider(height: 1, color: QfColors.border),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          children: [
            // Tarjeta de resumen (SALDO / GANADAS / GASTADAS)
            Container(
              decoration: ShapeDecoration(
                color: QfColors.surface,
                shape: const CutCornerBorder(
                  cut: 16,
                  side: BorderSide(color: Color(0x73FCEE0A)),
                ),
              ),
              padding: const EdgeInsets.all(14),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          l10n.rewardsLedgerBalance.toUpperCase(),
                          style: const TextStyle(
                            fontFamily: qfDisplay,
                            fontWeight: FontWeight.w700,
                            fontSize: 10,
                            letterSpacing: 1.4,
                            color: QfColors.text2,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '$balance',
                          style: const TextStyle(
                            fontFamily: qfMono,
                            fontWeight: FontWeight.w700,
                            fontSize: 30,
                            height: 1,
                            color: QfColors.yellow,
                            shadows: [
                              Shadow(
                                color: Color(0x59FCEE0A),
                                blurRadius: 18,
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          l10n.rewardsLedgerEarned.toUpperCase(),
                          style: const TextStyle(
                            fontFamily: qfDisplay,
                            fontWeight: FontWeight.w700,
                            fontSize: 10,
                            letterSpacing: 1.4,
                            color: QfColors.text2,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          earned > 0 ? '+$earned' : '$earned',
                          style: const TextStyle(
                            fontFamily: qfMono,
                            fontWeight: FontWeight.w700,
                            fontSize: 18,
                            color: QfColors.green,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          l10n.rewardsLedgerSpent.toUpperCase(),
                          style: const TextStyle(
                            fontFamily: qfDisplay,
                            fontWeight: FontWeight.w700,
                            fontSize: 10,
                            letterSpacing: 1.4,
                            color: QfColors.text2,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          spent > 0 ? '−$spent' : '$spent',
                          style: const TextStyle(
                            fontFamily: qfMono,
                            fontWeight: FontWeight.w700,
                            fontSize: 18,
                            color: QfColors.text2,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),

            if (isEmpty)
              // Estado vacío CyberCore
              Container(
                margin: const EdgeInsets.only(top: 16),
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 40),
                decoration: BoxDecoration(
                  color: QfColors.surface,
                  border: Border.all(
                    color: QfColors.divider,
                    width: 1,
                  ),
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(
                      Icons.toll_outlined,
                      size: 40,
                      color: QfColors.text2,
                    ),
                    const SizedBox(height: 12),
                    Text(
                      l10n.rewardsLedgerEmpty.toUpperCase(),
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        fontFamily: qfDisplay,
                        fontWeight: FontWeight.w700,
                        fontSize: 16,
                        letterSpacing: 1.0,
                        color: QfColors.text,
                      ),
                    ),
                    const SizedBox(height: 14),
                    TextButton(
                      onPressed: () => Navigator.of(context).pop(),
                      child: Text(
                        l10n.shellNeedCoinsCta.toUpperCase(),
                        style: const TextStyle(
                          fontFamily: qfDisplay,
                          fontWeight: FontWeight.w700,
                          fontSize: 13,
                          letterSpacing: 1.0,
                          color: QfColors.primary,
                        ),
                      ),
                    ),
                  ],
                ),
              )
            else ...[
              // Lista de movimientos agrupada por día
              Container(
                decoration: BoxDecoration(
                  color: QfColors.surface,
                  border: Border.all(color: QfColors.border),
                ),
                child: Column(
                  children: [
                    for (var i = 0; i < rows.length; i++) ...[
                      // Cabecera del día si es el primer elemento o si cambió de día
                      if (i == 0 ||
                          _groupLabel(l10n, rows[i]['created_at']) !=
                              _groupLabel(l10n, rows[i - 1]['created_at']))
                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.symmetric(
                            horizontal: 12,
                            vertical: 6,
                          ),
                          decoration: const BoxDecoration(
                            color: Color(0x0D00F0FF),
                            border: Border(
                              bottom: BorderSide(color: QfColors.divider),
                            ),
                          ),
                          child: Text(
                            _groupLabel(l10n, rows[i]['created_at']),
                            style: const TextStyle(
                              fontFamily: qfDisplay,
                              fontWeight: FontWeight.w700,
                              fontSize: 10,
                              letterSpacing: 1.6,
                              color: QfColors.primary,
                            ),
                          ),
                        ),

                      // Fila del movimiento
                      Container(
                        constraints: const BoxConstraints(minHeight: 58),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 8,
                        ),
                        decoration: BoxDecoration(
                          border: Border(
                            bottom: i < rows.length - 1
                                ? const BorderSide(color: QfColors.divider)
                                : BorderSide.none,
                          ),
                        ),
                        child: Row(
                          children: [
                            // Icono con caja cortada
                            _MovementIcon(
                              icon: _iconForKind(rows[i]['kind']),
                              positive: (rows[i]['delta'] as num? ?? 0) >= 0,
                            ),
                            const SizedBox(width: 12),

                            // Título y fecha/detalle
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Text(
                                    ledgerKindLabel(l10n, rows[i]['kind']),
                                    style: const TextStyle(
                                      fontFamily: qfBody,
                                      fontWeight: FontWeight.w600,
                                      fontSize: 14,
                                      color: QfColors.text,
                                    ),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    kickoffText(rows[i]['created_at']),
                                    style: const TextStyle(
                                      fontFamily: qfBody,
                                      fontSize: 12,
                                      color: QfColors.text2,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(width: 8),

                            // Importe
                            Text(
                              '${(rows[i]['delta'] as num? ?? 0) >= 0 ? '+' : '−'}${((rows[i]['delta'] as num? ?? 0)).abs()}',
                              style: TextStyle(
                                fontFamily: qfMono,
                                fontWeight: FontWeight.w700,
                                fontSize: 18,
                                color: (rows[i]['delta'] as num? ?? 0) >= 0
                                    ? QfColors.green
                                    : QfColors.text2,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ],
                ),
              ),

              // Botón "VER MÁS" / "VER MENOS"
              if (allRows.length > 5) ...[
                const SizedBox(height: 8),
                InkWell(
                  key: const ValueKey('coins-ledger-toggle'),
                  onTap: () => setState(() => _open = !_open),
                  child: Container(
                    height: 44,
                    alignment: Alignment.center,
                    decoration: ShapeDecoration(
                      color: const Color(0x0D00F0FF),
                      shape: const CutCornerBorder(
                        cut: 10,
                        side: BorderSide(color: Color(0x7A00F0FF)),
                      ),
                    ),
                    child: Text(
                      _open
                          ? l10n.rewardsLedgerLess.toUpperCase()
                          : l10n.rewardsLedgerMore.toUpperCase(),
                      style: const TextStyle(
                        fontFamily: qfDisplay,
                        fontWeight: FontWeight.w700,
                        fontSize: 14,
                        letterSpacing: 1.0,
                        color: QfColors.primary,
                      ),
                    ),
                  ),
                ),
              ],
            ],
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }
}

class _MovementIcon extends StatelessWidget {
  const _MovementIcon({required this.icon, required this.positive});

  final IconData icon;
  final bool positive;

  @override
  Widget build(BuildContext context) {
    final fg = positive ? QfColors.green : QfColors.text2;
    final bg = positive ? const Color(0x1405FFA1) : const Color(0x10B2B7C7);
    final border = positive ? const Color(0x6605FFA1) : QfColors.divider;

    return Container(
      width: 36,
      height: 36,
      decoration: ShapeDecoration(
        color: bg,
        shape: CutCornerBorder(
          cut: 6,
          side: BorderSide(color: border),
        ),
      ),
      alignment: Alignment.center,
      child: Icon(icon, size: 18, color: fg),
    );
  }
}
