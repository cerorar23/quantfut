import 'package:flutter/material.dart';

import 'live_api.dart';
import 'live_widgets.dart';

const _vipGold = Color(0xffffc61a), _vipAmber = Color(0xffff9500);
const _vipPanel = Color(0xff11151c);

/// Pantalla de acceso VIP. Planes, precios, aciertos y permisos salen del
/// servidor; no hay cifras de miembros, reseñas ni periodos de prueba porque
/// el backend no los entrega.
class LiveVipScreen extends StatefulWidget {
  const LiveVipScreen({super.key, required this.api, required this.data});
  final QuantFutApi api;
  final JsonMap data;
  @override
  State<LiveVipScreen> createState() => _LiveVipScreenState();
}

class _LiveVipScreenState extends State<LiveVipScreen> {
  int? chosen;

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

  static double? _monthly(JsonMap plan) {
    final cents = plan['price_cents'], days = plan['duration_days'];
    return cents is num && days is num && days > 0
        ? cents / 100 / (days / 30)
        : null;
  }

  static String _price(JsonMap plan) =>
      '\$${decimalText((plan['price_cents'] as num?) == null ? null : (plan['price_cents'] as num) / 100)}';

  static String _period(JsonMap plan) {
    final days = plan['duration_days'];
    if (days is! num) return 'Sin vencimiento';
    final months = (days / 30).round();
    return days % 30 == 0 && months >= 1
        ? (months == 1 ? '1 mes' : '$months meses')
        : '$days días';
  }

  Widget _stat(String value, String label, IconData icon) => Expanded(
    child: Column(
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: liveGreen, size: 17),
            const SizedBox(width: 5),
            Flexible(
              child: FittedBox(
                fit: BoxFit.scaleDown,
                child: liveText(value, size: 20, color: liveGreen, bold: true),
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        liveText(label.toUpperCase(), size: 9, color: liveMuted),
      ],
    ),
  );

  Widget _benefit(IconData icon, Color color, String title, String detail) =>
      Padding(
        padding: const EdgeInsets.symmetric(vertical: 9),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(7),
              decoration: BoxDecoration(
                color: color.withValues(alpha: .15),
                borderRadius: BorderRadius.circular(9),
              ),
              child: Icon(icon, color: color, size: 18),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  liveText(title, bold: true, size: 14),
                  const SizedBox(height: 2),
                  liveText(detail, size: 11, color: liveMuted),
                ],
              ),
            ),
            const Icon(Icons.check_circle, color: liveGreen, size: 18),
          ],
        ),
      );

  Widget _plan(
    JsonMap plan,
    bool selected,
    bool best,
    VoidCallback onTap,
    double? monthly,
  ) => Expanded(
    child: GestureDetector(
      onTap: onTap,
      child: Semantics(
        button: true,
        selected: selected,
        child: Container(
          padding: const EdgeInsets.fromLTRB(8, 14, 8, 14),
          decoration: BoxDecoration(
            color: selected ? _vipGold.withValues(alpha: .08) : _vipPanel,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: selected ? _vipGold : Colors.white12,
              width: selected ? 2 : 1,
            ),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                decoration: BoxDecoration(
                  color: best
                      ? _vipGold.withValues(alpha: .16)
                      : Colors.white10,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  best ? '★ MEJOR PRECIO' : _period(plan).toUpperCase(),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 8.5,
                    fontWeight: FontWeight.w800,
                    color: best ? _vipGold : liveMuted,
                  ),
                ),
              ),
              const SizedBox(height: 12),
              FittedBox(
                fit: BoxFit.scaleDown,
                child: liveText(_price(plan), size: 21, bold: true),
              ),
              liveText('${plan['currency'] ?? ''}', size: 10, color: liveMuted),
              const SizedBox(height: 8),
              if (best) liveText(_period(plan), size: 10, color: liveMuted),
              if (monthly != null)
                liveText(
                  '≈ \$${decimalText(monthly)}/mes',
                  size: 10,
                  color: selected ? _vipGold : liveMuted,
                  bold: true,
                ),
            ],
          ),
        ),
      ),
    ),
  );

  @override
  Widget build(BuildContext context) {
    final plans = jsonRows(widget.data['plans']);
    final history = jsonMap(
      jsonMap(widget.data['alta_probabilidad'])['historial'],
    );
    final config = jsonMap(widget.data['config']);
    final shown = plans.take(3).toList();
    final monthlies = shown.map(_monthly).toList();
    final bestIndex = shown.length > 1
        ? monthlies.indexOf(
            monthlies.whereType<double>().fold<double?>(
              null,
              (m, v) => m == null || v < m ? v : m,
            ),
          )
        : -1;
    final selected = chosen ?? (bestIndex >= 0 ? bestIndex : 0);
    final purchases = featureEnabled(widget.data, 'compras');
    final min = ((config['probability_min'] as num?) ?? .75) * 100;
    final max = ((config['probability_max'] as num?) ?? .90) * 100;
    final real = history['acierto_real'];
    return Scaffold(
      backgroundColor: liveBg,
      body: SafeArea(
        child: Stack(
          children: [
            ListView(
              padding: const EdgeInsets.fromLTRB(18, 18, 18, 24),
              children: [
                Center(
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 6,
                    ),
                    decoration: BoxDecoration(
                      color: _vipGold.withValues(alpha: .1),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: _vipGold.withValues(alpha: .5)),
                    ),
                    child: liveText(
                      '✦  ACCESO VIP',
                      size: 10,
                      color: _vipGold,
                      bold: true,
                    ),
                  ),
                ),
                const SizedBox(height: 20),
                Center(
                  child: Container(
                    width: 74,
                    height: 74,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(20),
                      gradient: const LinearGradient(
                        colors: [_vipGold, _vipAmber],
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: _vipGold.withValues(alpha: .35),
                          blurRadius: 24,
                        ),
                      ],
                    ),
                    child: const Icon(
                      Icons.workspace_premium,
                      color: liveBg,
                      size: 42,
                    ),
                  ),
                ),
                const SizedBox(height: 14),
                const Center(
                  child: Text(
                    'QuantFut VIP',
                    style: TextStyle(fontSize: 27, fontWeight: FontWeight.w900),
                  ),
                ),
                const SizedBox(height: 8),
                Center(
                  child: const Text(
                    'Todos los pronósticos de Alta Probabilidad y del Reto Escalera mientras tu suscripción esté vigente.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 13,
                      color: liveMuted,
                      height: 1.4,
                    ),
                  ),
                ),
                const SizedBox(height: 18),
                Container(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  decoration: BoxDecoration(
                    color: liveGreen.withValues(alpha: .08),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: liveGreen.withValues(alpha: .35)),
                  ),
                  child: Row(
                    children: [
                      _stat(
                        real is num ? '${decimalText(real, 1)} %' : '—',
                        'Acierto registrado',
                        Icons.trending_up,
                      ),
                      Container(width: 1, height: 34, color: Colors.white12),
                      _stat(
                        '${history['aciertos'] ?? '—'}/${history['n'] ?? '—'}',
                        'Resueltos',
                        Icons.fact_check_outlined,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 4),
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 6),
                  child: liveText(
                    'Historial público y sellado; las muestras por mercado son pequeñas y un pronóstico puede fallar.',
                    size: 10,
                    color: liveMuted,
                  ),
                ),
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 14,
                    vertical: 6,
                  ),
                  decoration: BoxDecoration(
                    color: _vipPanel,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: Colors.white10),
                  ),
                  child: Column(
                    children: [
                      _benefit(
                        Icons.verified_outlined,
                        liveGreen,
                        'Historial verificable',
                        'Cada pronóstico se sella antes del partido',
                      ),
                      _benefit(
                        Icons.star_outline,
                        _vipGold,
                        'Alta Probabilidad completa',
                        'Todos los picks de ${min.round()} a ${max.round()} %, sin cupo gratuito',
                      ),
                      _benefit(
                        Icons.stairs_outlined,
                        const Color(0xffa78bfa),
                        'Reto Escalera completo',
                        'Todos los escalones pendientes, no solo uno',
                      ),
                      _benefit(
                        Icons.bolt_outlined,
                        const Color(0xffff4d6d),
                        'Cuotas y análisis del partido',
                        'Cuota publicada, probabilidad y xG de cada pick',
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                if (shown.isEmpty)
                  training('Los planes se mostrarán cuando estén disponibles.')
                else
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      for (var i = 0; i < shown.length; i++) ...[
                        if (i > 0) const SizedBox(width: 8),
                        _plan(
                          shown[i],
                          selected == i,
                          i == bestIndex,
                          () => setState(() => chosen = i),
                          monthlies[i],
                        ),
                      ],
                    ],
                  ),
                const SizedBox(height: 18),
                DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [_vipGold, _vipAmber],
                    ),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: SizedBox(
                    width: double.infinity,
                    child: TextButton.icon(
                      style: TextButton.styleFrom(
                        foregroundColor: liveBg,
                        padding: const EdgeInsets.symmetric(vertical: 16),
                      ),
                      onPressed: () => liveNotice(
                        context,
                        purchases
                            ? 'La contratación requiere un canal de pago configurado.'
                            : featureMessage(widget.data, 'compras'),
                      ),
                      icon: const Icon(Icons.workspace_premium),
                      label: const Text(
                        'Activar acceso VIP',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 10),
                Center(
                  child: liveText(
                    purchases ? 'Precios del catálogo del servidor.' : 'Compras en preparación: aún no se cobra nada desde la app.',
                    size: 11,
                    color: liveMuted,
                  ),
                ),
                const SizedBox(height: 14),
                Center(
                  child: OutlinedButton.icon(
                    onPressed: checkAccess,
                    icon: const Icon(Icons.refresh, size: 16),
                    label: Text(
                      widget.api.plus
                          ? 'Actualizar mi acceso'
                          : 'Comprobar mi acceso',
                    ),
                  ),
                ),
                const SizedBox(height: 10),
                Center(
                  child: liveText(
                    '🔒  Tu acceso VIP queda vinculado a tu cuenta',
                    size: 10,
                    color: liveMuted,
                  ),
                ),
              ],
            ),
            Positioned(
              top: 4,
              right: 6,
              child: IconButton(
                tooltip: 'Cerrar',
                onPressed: () => Navigator.maybePop(context),
                icon: const Icon(Icons.close, color: liveMuted),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
