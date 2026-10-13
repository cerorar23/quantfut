import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import 'alerts_model.dart';
import 'live_api.dart';
import 'live_widgets.dart';

const _red = Color(0xffe85667);
const _amber = liveGold;
const _tile = Color(0xff0e1b2a);

/// Pestaña «Alertas» del análisis de un partido: bajas y dudas de cada equipo con datos reales
/// del proveedor. Por equipo, «Desventaja» son sus bajas y «Ventaja» las del rival.
class AlertsTab extends StatefulWidget {
  const AlertsTab({super.key, required this.ficha, required this.api});

  final JsonMap ficha;
  final QuantFutApi api;

  @override
  State<AlertsTab> createState() => _AlertsTabState();
}

class _AlertsTabState extends State<AlertsTab> {
  String _side = 'home';

  JsonMap _team(String side) =>
      jsonMap(widget.ficha[side == 'home' ? 'local' : 'visitante']);

  String _name(String side) => '${_team(side)['nombre'] ?? ''}';

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final alerts = MatchAlerts.fromFicha(widget.ficha);
    if (alerts == null) {
      return Container(
        key: const ValueKey('alerts-no-check'),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: livePanel,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white12),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(Icons.help_outline, color: liveGold),
            const SizedBox(width: 12),
            Expanded(
              child: liveText(l10n.alertsNoCheck, size: 13, color: liveMuted),
            ),
          ],
        ),
      );
    }
    final rival = _side == 'home' ? 'away' : 'home';
    final checked = alerts.checked;
    return GestureDetector(
      behavior: HitTestBehavior.translucent,
      onHorizontalDragEnd: (d) {
        final v = d.primaryVelocity ?? 0;
        if (v.abs() < 300) return;
        setState(() => _side = v < 0 ? 'away' : 'home');
      },
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _TeamSwitcher(
            side: _side,
            home: _team('home'),
            away: _team('away'),
            api: widget.api,
            alerts: alerts,
            onChanged: (s) => setState(() => _side = s),
          ),
          const SizedBox(height: 14),
          AnimatedSwitcher(
            duration: const Duration(milliseconds: 240),
            child: Column(
              key: ValueKey('alerts-$_side'),
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _Section(
                  advantage: true,
                  title: l10n.alertsAdvantage,
                  subtitle: l10n.alertsAbsencesOf(_name(rival)),
                  empty: l10n.alertsAdvantageEmpty,
                  absences: alerts.against(_side),
                ),
                const SizedBox(height: 18),
                _Section(
                  advantage: false,
                  title: l10n.alertsDisadvantage,
                  subtitle: l10n.alertsAbsencesOf(_name(_side)),
                  empty: l10n.alertsDisadvantageEmpty,
                  absences: alerts.of(_side),
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          Wrap(
            spacing: 8,
            runSpacing: 6,
            children: [
              if (checked != null)
                _InfoChip(
                  Icons.schedule,
                  l10n.alertsChecked(kickoffText(checked.toIso8601String())),
                ),
              _InfoChip(Icons.dataset_outlined, l10n.alertsSource),
            ],
          ),
          const SizedBox(height: 8),
          liveText(l10n.alertsNote, size: 11, color: liveMuted),
          const SizedBox(height: 12),
        ],
      ),
    );
  }
}

/// Selector de equipo: escudo, nombre y resumen de bajas, con un indicador que se desliza.
class _TeamSwitcher extends StatelessWidget {
  const _TeamSwitcher({
    required this.side,
    required this.home,
    required this.away,
    required this.api,
    required this.alerts,
    required this.onChanged,
  });

  final String side;
  final JsonMap home, away;
  final QuantFutApi api;
  final MatchAlerts alerts;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    final still = MediaQuery.of(context).disableAnimations;
    final l10n = context.l10n;
    Widget tile(String s, JsonMap team) => Expanded(
      child: Semantics(
        button: true,
        selected: side == s,
        label: '${team['nombre']}',
        child: ExcludeSemantics(
          child: InkWell(
            key: ValueKey('alerts-team-$s'),
            borderRadius: BorderRadius.circular(16),
            onTap: () => onChanged(s),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              child: Row(
                children: [
                  TeamCrest(team: team, api: api, size: 34),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          '${team['nombre'] ?? ''}',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: side == s ? Colors.white : liveMuted,
                            fontFamily: 'Gilroy Bold',
                            fontSize: 13,
                          ),
                        ),
                        FittedBox(
                          fit: BoxFit.scaleDown,
                          alignment: Alignment.centerLeft,
                          child: Text(
                            l10n.alertsSummary(
                              alerts.confirmedCount(s),
                              alerts.doubtCount(s),
                            ),
                            style: const TextStyle(color: liveMuted, fontSize: 10),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
    return Container(
      height: 62,
      decoration: BoxDecoration(
        color: livePanel,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white10),
      ),
      child: Stack(
        children: [
          AnimatedAlign(
            duration: still ? Duration.zero : const Duration(milliseconds: 260),
            curve: Curves.easeOutCubic,
            alignment: side == 'home' ? Alignment.centerLeft : Alignment.centerRight,
            child: FractionallySizedBox(
              widthFactor: .5,
              heightFactor: 1,
              child: Container(
                key: const ValueKey('alerts-indicator'),
                margin: const EdgeInsets.all(3),
                decoration: BoxDecoration(
                  color: liveCyan.withValues(alpha: .16),
                  borderRadius: BorderRadius.circular(13),
                  border: Border.all(color: liveCyan.withValues(alpha: .5)),
                ),
              ),
            ),
          ),
          Row(children: [tile('home', home), tile('away', away)]),
        ],
      ),
    );
  }
}

/// «Ventaja» (bajas del rival) o «Desventaja» (bajas propias) con sus tarjetas.
class _Section extends StatelessWidget {
  const _Section({
    required this.advantage,
    required this.title,
    required this.subtitle,
    required this.empty,
    required this.absences,
  });

  final bool advantage;
  final String title, subtitle, empty;
  final List<Absence> absences;

  @override
  Widget build(BuildContext context) {
    final color = advantage ? liveGreen : _red;
    return Column(
      key: ValueKey(advantage ? 'alerts-advantage' : 'alerts-disadvantage'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(advantage ? Icons.check_box : Icons.cancel, color: color, size: 20),
            const SizedBox(width: 8),
            Text(
              title.toUpperCase(),
              style: TextStyle(
                color: color,
                fontFamily: 'Gilroy ExtraBold',
                fontSize: 14,
                letterSpacing: .8,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                subtitle,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: liveMuted, fontSize: 11),
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        if (absences.isEmpty)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(vertical: 18),
            decoration: BoxDecoration(
              color: _tile,
              borderRadius: BorderRadius.circular(14),
            ),
            child: Center(child: liveText(empty, size: 12, color: liveMuted)),
          )
        else
          for (final (i, a) in absences.indexed)
            _Stagger(
              index: i,
              child: _AbsenceCard(absence: a, advantage: advantage),
            ),
      ],
    );
  }
}

/// Entrada con fundido y ascenso; cada tarjeta tarda un poco más que la anterior.
class _Stagger extends StatelessWidget {
  const _Stagger({required this.index, required this.child});

  final int index;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final still = MediaQuery.of(context).disableAnimations;
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: still ? 1 : 0, end: 1),
      duration: still ? Duration.zero : Duration(milliseconds: 260 + index * 90),
      curve: Curves.easeOutCubic,
      builder: (context, t, child) => Opacity(
        opacity: t,
        child: Transform.translate(offset: Offset(0, (1 - t) * 14), child: child),
      ),
      child: child,
    );
  }
}

class _AbsenceCard extends StatelessWidget {
  const _AbsenceCard({required this.absence, required this.advantage});

  final Absence absence;
  final bool advantage;

  static String _initials(String name) {
    final parts = name.split(RegExp(r'[\s.]+')).where((p) => p.isNotEmpty).toList();
    if (parts.isEmpty) return '?';
    if (parts.length == 1) return parts.first.characters.first.toUpperCase();
    return '${parts.first.characters.first}${parts.last.characters.first}'.toUpperCase();
  }

  static IconData _icon(AbsenceReason r) => switch (r) {
    AbsenceReason.illness => Icons.sick_outlined,
    AbsenceReason.suspension => Icons.block,
    AbsenceReason.other || AbsenceReason.unknown => Icons.info_outline,
    _ => Icons.healing,
  };

  static String _reason(AppLocalizations l10n, Absence a) => switch (a.reason) {
    AbsenceReason.muscle => l10n.alertsReasonMuscle,
    AbsenceReason.knee => l10n.alertsReasonKnee,
    AbsenceReason.foot => l10n.alertsReasonFoot,
    AbsenceReason.knock => l10n.alertsReasonKnock,
    AbsenceReason.illness => l10n.alertsReasonIllness,
    AbsenceReason.injury => l10n.alertsReasonInjury,
    AbsenceReason.suspension => l10n.alertsReasonSuspension,
    AbsenceReason.other => a.rawReason ?? l10n.alertsReasonUnknown,
    AbsenceReason.unknown => l10n.alertsReasonUnknown,
  };

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final doubt = absence.kind == AbsenceKind.doubt;
    final accent = advantage ? liveGreen : _red;
    final status = switch (absence.kind) {
      AbsenceKind.out => l10n.alertsOut,
      AbsenceKind.doubt => l10n.alertsDoubt,
      AbsenceKind.suspended => l10n.alertsSuspended,
    };
    // El estado es un hecho del jugador (no juega / duda) y no cambia de color según la sección;
    // solo el borde de la tarjeta indica si es ventaja o desventaja.
    final statusColor = doubt ? _amber : _red;
    final reason = _reason(l10n, absence);
    return Semantics(
      container: true,
      label: '${absence.player}. $status. $reason',
      child: ExcludeSemantics(
        child: Container(
          margin: const EdgeInsets.only(bottom: 10),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: livePanel,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: accent.withValues(alpha: .45)),
          ),
          child: Row(
            children: [
              Container(
                width: 42,
                height: 42,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: statusColor.withValues(alpha: .15),
                  shape: BoxShape.circle,
                ),
                child: Text(
                  _initials(absence.player),
                  style: TextStyle(
                    color: statusColor,
                    fontFamily: 'Gilroy ExtraBold',
                    fontSize: 14,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      absence.player,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: Colors.white,
                        fontFamily: 'Gilroy Bold',
                        fontSize: 15,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Row(
                      children: [
                        Icon(_icon(absence.reason), size: 14, color: liveMuted),
                        const SizedBox(width: 5),
                        Expanded(
                          child: Text(
                            reason,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(color: liveMuted, fontSize: 12),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                decoration: BoxDecoration(
                  color: statusColor.withValues(alpha: .15),
                  borderRadius: BorderRadius.circular(99),
                ),
                child: Text(
                  status,
                  style: TextStyle(
                    color: statusColor,
                    fontFamily: 'Gilroy Bold',
                    fontSize: 10,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  const _InfoChip(this.icon, this.label);

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
    decoration: BoxDecoration(
      color: _tile,
      borderRadius: BorderRadius.circular(99),
    ),
    child: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 13, color: liveMuted),
        const SizedBox(width: 5),
        Flexible(
          child: Text(
            label,
            style: const TextStyle(color: liveMuted, fontSize: 11),
          ),
        ),
      ],
    ),
  );
}
