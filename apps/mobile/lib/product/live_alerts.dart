import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../l10n/app_locale.dart';
import '../l10n/pick_labels.dart';
import 'alerts_model.dart';
import 'lineup_pitch.dart';
import 'live_api.dart';
import 'live_widgets.dart';
import 'qf_theme.dart';
import 'sport_images.dart';

const _red = Color(0xffff2a6d);
const _green = Color(0xff05ffa1);
const _tile = Color(0xff0e1b2a);

/// Pestaña «Alertas» del análisis de un partido: bajas y dudas de cada equipo con datos reales
/// del proveedor y pizarra táctica de alineaciones al final.
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
          color: QfColors.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: QfColors.divider),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(Icons.help_outline, color: QfColors.yellow),
            const SizedBox(width: 12),
            Expanded(
              child: liveText(l10n.alertsNoCheck, size: 13, color: QfColors.muted),
            ),
          ],
        ),
      );
    }

    final rival = _side == 'home' ? 'away' : 'home';
    final checked = alerts.checked;
    final locale = AppLocale.instance.code;

    final homeTeam = _team('home');
    final awayTeam = _team('away');
    final homeLineup = alerts.homeLineup;
    final awayLineup = alerts.awayLineup;

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
            home: homeTeam,
            away: awayTeam,
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
                  api: widget.api,
                ),
                const SizedBox(height: 18),
                _Section(
                  advantage: false,
                  title: l10n.alertsDisadvantage,
                  subtitle: l10n.alertsAbsencesOf(_name(_side)),
                  empty: l10n.alertsDisadvantageEmpty,
                  absences: alerts.of(_side),
                  api: widget.api,
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // Sección de Alineaciones (al final de las bajas)
          _LineupsSection(
            homeTeam: homeTeam,
            awayTeam: awayTeam,
            homeLineup: homeLineup,
            awayLineup: awayLineup,
            api: widget.api,
          ),

          const SizedBox(height: 16),
          // Pie comprobado
          if (checked != null) ...[
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              decoration: BoxDecoration(
                color: const Color(0xff040508),
                border: Border.all(color: QfColors.divider),
              ),
              child: Text(
                '> ${l10n.alertsCheckedFooter(_formatCheckedDate(checked, locale))}',
                style: const TextStyle(
                  fontFamily: 'JetBrains Mono',
                  fontWeight: FontWeight.w500,
                  fontSize: 11,
                  color: QfColors.muted,
                ),
              ),
            ),
            const SizedBox(height: 10),
          ],
          Wrap(
            spacing: 8,
            runSpacing: 6,
            children: [
              _InfoChip(Icons.dataset_outlined, l10n.alertsSource),
            ],
          ),
          const SizedBox(height: 8),
          liveText(l10n.alertsNote, size: 11, color: QfColors.muted),
          const SizedBox(height: 12),
        ],
      ),
    );
  }

  static String _formatCheckedDate(DateTime date, String locale) {
    try {
      final local = date.toLocal();
      var month = DateFormat('MMM', locale).format(local).toLowerCase();
      if (locale == 'es' && !month.endsWith('.') && month != 'may') {
        month = '$month.';
      }
      return '${local.day}-$month ${local.hour.toString().padLeft(2, '0')}:${local.minute.toString().padLeft(2, '0')}';
    } catch (_) {
      return date.toIso8601String();
    }
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
                            color: side == s ? Colors.white : QfColors.muted,
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
                            style: const TextStyle(color: QfColors.muted, fontSize: 10),
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
        color: QfColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: QfColors.divider),
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
                  color: QfColors.cyan.withValues(alpha: .16),
                  borderRadius: BorderRadius.circular(13),
                  border: Border.all(color: QfColors.cyan.withValues(alpha: .5)),
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
    required this.api,
  });

  final bool advantage;
  final String title, subtitle, empty;
  final List<Absence> absences;
  final QuantFutApi api;

  @override
  Widget build(BuildContext context) {
    final color = advantage ? _green : _red;
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
                style: const TextStyle(color: QfColors.muted, fontSize: 11),
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
            child: Center(child: liveText(empty, size: 12, color: QfColors.muted)),
          )
        else
          Container(
            decoration: BoxDecoration(
              color: QfColors.surface,
              border: Border.all(color: QfColors.divider),
            ),
            child: Column(
              children: [
                for (final (i, a) in absences.indexed)
                  _Stagger(
                    index: i,
                    child: _AbsenceCard(absence: a, advantage: advantage, api: api),
                  ),
              ],
            ),
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
  const _AbsenceCard({
    required this.absence,
    required this.advantage,
    required this.api,
  });

  final Absence absence;
  final bool advantage;
  final QuantFutApi api;

  static String _initials(String name) {
    final parts = name.split(RegExp(r'[\s.]+')).where((p) => p.isNotEmpty).toList();
    if (parts.isEmpty) return '?';
    if (parts.length == 1) return parts.first.characters.first.toUpperCase();
    return '${parts.first.characters.first}${parts.last.characters.first}'.toUpperCase();
  }

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
    final badgeLabel = absenceBadgeLabel(absence, l10n);
    final badgeColor = absenceBadgeColor(absence);

    // Subtítulo: «POS · Equipo» o «Equipo»
    final pos = absence.position?.trim();
    final team = absence.team?.trim();
    final subtitle = [
      if (pos != null && pos.isNotEmpty) pos.toUpperCase(),
      if (team != null && team.isNotEmpty) team,
    ].join(' · ');

    // Tercera línea: texto de regreso si existe, o el motivo traducido
    final returnText = absenceReturnText(absence, l10n: l10n);
    final fallbackReason = _reason(l10n, absence);
    final detailLine = returnText ?? fallbackReason;

    final photo = absence.photo;
    final resolvedPhoto = serverImageUrl(api, photo);

    final crest = absence.crest;
    final resolvedCrest = serverImageUrl(api, crest);

    return Semantics(
      container: true,
      label: '${absence.player}. $badgeLabel. $detailLine',
      child: ExcludeSemantics(
        child: Container(
          constraints: const BoxConstraints(minHeight: 68),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: const BoxDecoration(
            border: Border(bottom: BorderSide(color: QfColors.divider)),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              // Avatar redondo 44 dp con escudo 20 dp en la esquina inferior derecha
              SizedBox(
                width: 44,
                height: 44,
                child: Stack(
                  clipBehavior: Clip.none,
                  children: [
                    Container(
                      width: 44,
                      height: 44,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        border: Border.all(
                          color: QfColors.cyan.withValues(alpha: .35),
                        ),
                        gradient: const LinearGradient(
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                          colors: [Color(0xff1f2230), Color(0xff12141d)],
                        ),
                      ),
                      child: ClipOval(
                        child: resolvedPhoto != null && resolvedPhoto.isNotEmpty
                            ? Image.network(
                                resolvedPhoto,
                                fit: BoxFit.cover,
                                errorBuilder: (_, error, stackTrace) => _initialsWidget(),
                              )
                            : _initialsWidget(),
                      ),
                    ),
                    if (resolvedCrest != null && resolvedCrest.isNotEmpty)
                      Positioned(
                        right: -4,
                        bottom: -4,
                        child: Container(
                          width: 20,
                          height: 20,
                          padding: const EdgeInsets.all(2),
                          decoration: const BoxDecoration(
                            color: Color(0xff12141d),
                            shape: BoxShape.circle,
                          ),
                          child: Image.network(
                            resolvedCrest,
                            fit: BoxFit.contain,
                            errorBuilder: (_, error, stackTrace) => const SizedBox.shrink(),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
              const SizedBox(width: 12),

              // Nombre, subtítulo y regreso/motivo
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      absence.player,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: Colors.white,
                        fontFamily: 'Gilroy Bold',
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    if (subtitle.isNotEmpty) ...[
                      const SizedBox(height: 1),
                      Text(
                        subtitle,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: QfColors.muted,
                          fontSize: 12,
                        ),
                      ),
                    ],
                    const SizedBox(height: 2),
                    Text(
                      detailLine,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontFamily: 'JetBrains Mono',
                        fontSize: 11,
                        fontWeight: FontWeight.w500,
                        color: Color(0xff939ab0),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),

              // Insignia CyberCore
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  border: Border.all(color: badgeColor),
                ),
                child: Text(
                  badgeLabel,
                  style: TextStyle(
                    color: badgeColor,
                    fontFamily: 'Rajdhani',
                    fontWeight: FontWeight.bold,
                    fontSize: 11,
                    letterSpacing: 1.2,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _initialsWidget() => Text(
    _initials(absence.player),
    style: const TextStyle(
      color: QfColors.cyan,
      fontFamily: 'JetBrains Mono',
      fontWeight: FontWeight.bold,
      fontSize: 14,
    ),
  );
}

/// Bloque de alineaciones al final de la pestaña de alertas.
class _LineupsSection extends StatelessWidget {
  const _LineupsSection({
    required this.homeTeam,
    required this.awayTeam,
    required this.homeLineup,
    required this.awayLineup,
    required this.api,
  });

  final JsonMap homeTeam, awayTeam;
  final JsonMap? homeLineup, awayLineup;
  final QuantFutApi api;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final locale = AppLocale.instance.code;

    final homeName = '${homeTeam['nombre'] ?? ''}';
    final awayName = '${awayTeam['nombre'] ?? ''}';

    final hasHome = homeLineup != null && jsonRows(homeLineup!['titulares']).isNotEmpty;
    final hasAway = awayLineup != null && jsonRows(awayLineup!['titulares']).isNotEmpty;

    // Si ninguno tiene alineación ni datos, no mostramos el bloque
    if (!hasHome && !hasAway && homeName.isEmpty && awayName.isEmpty) {
      return const SizedBox.shrink();
    }

    return Container(
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        color: QfColors.surface,
        border: Border.all(color: QfColors.cyan.withValues(alpha: .35)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Once local (si existe)
          if (hasHome)
            _TeamPitchBlock(
              team: homeTeam,
              lineup: homeLineup!,
              api: api,
              locale: locale,
            )
          else
            _NoLineupCard(team: homeTeam, api: api, l10n: l10n),

          const SizedBox(height: 12),

          // Once visitante (si existe)
          if (hasAway)
            _TeamPitchBlock(
              team: awayTeam,
              lineup: awayLineup!,
              api: api,
              locale: locale,
            )
          else
            _NoLineupCard(team: awayTeam, api: api, l10n: l10n),
        ],
      ),
    );
  }
}

class _TeamPitchBlock extends StatelessWidget {
  const _TeamPitchBlock({
    required this.team,
    required this.lineup,
    required this.api,
    required this.locale,
  });

  final JsonMap team, lineup;
  final QuantFutApi api;
  final String locale;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final form = '${lineup['formacion'] ?? '4-3-3'}';
    final rival = '${lineup['rival'] ?? ''}';
    final rawDate = '${lineup['fecha'] ?? ''}';
    final parsedDate = DateTime.tryParse(rawDate);
    final dateStr = parsedDate != null
        ? DateFormat('d MMM', locale).format(parsedDate.toLocal())
        : rawDate;
    final cap = rival.isNotEmpty
        ? l10n.alertsLastElevenVs(rival, dateStr)
        : dateStr;

    final titulares = jsonRows(lineup['titulares']);

    return Padding(
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      l10n.alertsLineupsKicker,
                      style: const TextStyle(
                        fontFamily: 'Rajdhani',
                        fontWeight: FontWeight.bold,
                        fontSize: 11,
                        letterSpacing: 1.6,
                        color: QfColors.cyan,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      l10n.alertsLineupsTitle,
                      style: const TextStyle(
                        fontFamily: 'Rajdhani',
                        fontWeight: FontWeight.bold,
                        fontSize: 22,
                        letterSpacing: .4,
                        color: Colors.white,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  border: Border.all(color: QfColors.cyan.withValues(alpha: .5)),
                ),
                child: Text(
                  form,
                  style: const TextStyle(
                    fontFamily: 'JetBrains Mono',
                    fontWeight: FontWeight.bold,
                    fontSize: 12,
                    color: QfColors.cyan,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              TeamCrest(team: team, api: api, size: 22),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  '${team['nombre']} · $cap',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 12,
                    color: QfColors.muted,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          QfPitch(
            formation: form,
            titulares: titulares,
            api: api,
          ),
        ],
      ),
    );
  }
}

class _NoLineupCard extends StatelessWidget {
  const _NoLineupCard({
    required this.team,
    required this.api,
    required this.l10n,
  });

  final JsonMap team;
  final QuantFutApi api;
  final AppLocalizations l10n;

  @override
  Widget build(BuildContext context) {
    final name = '${team['nombre'] ?? ''}';
    return Container(
      margin: const EdgeInsets.all(12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        border: Border.all(color: QfColors.divider, style: BorderStyle.solid), // dashed appearance via border
      ),
      child: Row(
        children: [
          TeamCrest(team: team, api: api, size: 32),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  l10n.alertsNoLineupSaved(name),
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  l10n.alertsNoLineupDesc,
                  style: const TextStyle(
                    fontSize: 12,
                    color: QfColors.muted,
                  ),
                ),
              ],
            ),
          ),
        ],
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
        Icon(icon, size: 13, color: QfColors.muted),
        const SizedBox(width: 5),
        Flexible(
          child: Text(
            label,
            style: const TextStyle(color: QfColors.muted, fontSize: 11),
          ),
        ),
      ],
    ),
  );
}
