import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../l10n/app_locale.dart';
import '../l10n/language_picker.dart';
import '../product/live_api.dart';
import '../product/live_detail.dart';
import '../product/live_widgets.dart';
import '../product/qf_controls.dart';
import '../product/qf_shapes.dart';
import '../product/qf_theme.dart';
import '../product/sports.dart';
import 'firebase_services.dart';

// Servidor hoy solo soporta push global en /app/v1/firebase/preferences.
// Notificaciones por deporte quedan detrás de esta bandera hasta F7a/F7b.
const bool _supportsSportNotifications = false;

class FirebasePreferencesScreen extends StatefulWidget {
  const FirebasePreferencesScreen({super.key, required this.api});
  final QuantFutApi api;
  @override
  State<FirebasePreferencesScreen> createState() =>
      _FirebasePreferencesScreenState();
}

class _FirebasePreferencesScreenState extends State<FirebasePreferencesScreen> {
  final services = FirebaseServices.current!;
  bool busy = false;
  bool showMoreMeta = false;
  String? error;

  Future<void> change(Future<void> Function() action) async {
    if (busy) return;
    setState(() {
      busy = true;
      error = null;
    });
    try {
      await action();
      if (widget.api.firebaseConnected) await widget.api.syncPreferences();
    } catch (failure) {
      if (mounted) setState(() => error = '$failure');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Theme(
      data: qfTheme(),
      child: Scaffold(
        backgroundColor: QfColors.bg,
        appBar: PreferredSize(
          preferredSize: const Size.fromHeight(56),
          child: Container(
            height: 56,
            padding: const EdgeInsets.only(left: 6, right: 14),
            decoration: const BoxDecoration(
              color: QfColors.bg,
              border: Border(bottom: BorderSide(color: QfColors.border)),
            ),
            child: Row(
              children: [
                IconButton(
                  tooltip: MaterialLocalizations.of(context).backButtonTooltip,
                  constraints: const BoxConstraints(minWidth: 44, minHeight: 44),
                  icon: const Icon(Icons.chevron_left, color: QfColors.text2, size: 24),
                  onPressed: () => Navigator.of(context).maybePop(),
                ),
                Expanded(
                  child: Text(
                    l10n.prefsTitle.toUpperCase(),
                    style: const TextStyle(
                      fontFamily: qfDisplay,
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1.0,
                      color: QfColors.text,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
        body: ListView(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          children: [
            if (busy) const LinearProgressIndicator(color: QfColors.cyan),
            if (error != null) ...[
              qfError(error!),
              const SizedBox(height: 12),
            ],

            // // NOTIFICACIONES
            Text(
              '// ${l10n.profileNotifications.toUpperCase()}',
              style: const TextStyle(
                fontFamily: qfDisplay,
                fontWeight: FontWeight.w700,
                fontSize: 11,
                letterSpacing: 1.8,
                color: QfColors.cyan,
              ),
            ),
            const SizedBox(height: 8),
            Container(
              decoration: ShapeDecoration(
                color: QfColors.surface,
                shape: const CutCornerBorder(
                  cut: 10,
                  side: BorderSide(color: QfColors.borderStrong),
                ),
              ),
              child: Column(
                children: [
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                l10n.prefsNotificationsTitle,
                                style: const TextStyle(
                                  fontSize: 15,
                                  fontWeight: FontWeight.w700,
                                  color: QfColors.text,
                                ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                widget.api.firebaseConnected
                                    ? (services.notificationsAllowed
                                        ? l10n.prefsNotificationsOn
                                        : l10n.prefsNotificationsOff)
                                    : l10n.prefsNotificationsOff,
                                style: const TextStyle(fontSize: 12, color: QfColors.text2),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 8),
                        QfSwitch(
                          value: services.notificationsAllowed,
                          onChanged: busy || !widget.api.firebaseConnected
                              ? null
                              : (value) => change(() async {
                                  if (value) {
                                    final token = await services.enableNotifications();
                                    if (token != null) await widget.api.registerDevice(token);
                                  } else {
                                    await widget.api.unregisterDevice();
                                    await services.disableNotifications();
                                  }
                                }),
                        ),
                      ],
                    ),
                  ),
                  if (_supportsSportNotifications) ...[
                    // Notificaciones por deporte (cuando el servidor las soporte)
                    for (final sport in sportCatalog.ids)
                      Container(
                        decoration: const BoxDecoration(
                          border: Border(top: BorderSide(color: QfColors.divider)),
                        ),
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                        child: Row(
                          children: [
                            Icon(
                              sportCatalog.spec(sport).icon,
                              size: 22,
                              color: QfColors.cyan,
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Text(
                                sportCatalog.spec(sport).label(l10n),
                                style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
                              ),
                            ),
                            QfSwitch(
                              value: services.notificationsAllowed,
                              onChanged: services.notificationsAllowed
                                  ? (v) {}
                                  : null,
                            ),
                          ],
                        ),
                      ),
                  ],
                  if (widget.api.firebaseConnected)
                    InkWell(
                      key: const ValueKey('prefs-inbox'),
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute<void>(
                          builder: (_) => FirebaseInbox(api: widget.api),
                        ),
                      ),
                      child: Container(
                        constraints: const BoxConstraints(minHeight: 52),
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                        decoration: const BoxDecoration(
                          border: Border(top: BorderSide(color: QfColors.divider)),
                        ),
                        child: Row(
                          children: [
                            const Icon(Icons.notifications_none, size: 22, color: QfColors.text2),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Text(
                                l10n.prefsInbox,
                                style: const TextStyle(
                                  fontWeight: FontWeight.w600,
                                  fontSize: 14,
                                  color: QfColors.text,
                                ),
                              ),
                            ),
                            const Icon(Icons.chevron_right, size: 18, color: QfColors.muted),
                          ],
                        ),
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 6),
            Text(
              l10n.prefsNotificationsOn,
              style: const TextStyle(fontSize: 11, color: QfColors.muted),
            ),
            const SizedBox(height: 14),

            // // IDIOMA
            Text(
              '// ${l10n.profileLanguage.toUpperCase()}',
              style: const TextStyle(
                fontFamily: qfDisplay,
                fontWeight: FontWeight.w700,
                fontSize: 11,
                letterSpacing: 1.8,
                color: QfColors.cyan,
              ),
            ),
            const SizedBox(height: 8),
            InkWell(
              key: const ValueKey('prefs-language'),
              onTap: busy ? null : () => showLanguagePicker(context),
              child: Container(
                constraints: const BoxConstraints(minHeight: 58),
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                decoration: ShapeDecoration(
                  color: QfColors.surface,
                  shape: const CutCornerBorder(
                    cut: 10,
                    side: BorderSide(color: QfColors.border),
                  ),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 40,
                      height: 36,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: QfColors.cyan.withValues(alpha: .08),
                        border: Border.all(color: QfColors.borderStrong),
                      ),
                      child: Text(
                        AppLocale.instance.code.toUpperCase(),
                        style: const TextStyle(
                          fontFamily: qfMono,
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                          color: QfColors.cyan,
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            appLanguages[AppLocale.instance.code]!,
                            style: const TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.w700,
                              color: QfColors.text,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            l10n.prefsLanguageNote,
                            style: const TextStyle(fontSize: 12, color: QfColors.text2),
                          ),
                        ],
                      ),
                    ),
                    const Icon(Icons.chevron_right, size: 18, color: QfColors.muted),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 14),

            // // MEDICIÓN Y DIAGNÓSTICO
            Text(
              '// ${l10n.profileMeasurement.toUpperCase()}',
              style: const TextStyle(
                fontFamily: qfDisplay,
                fontWeight: FontWeight.w700,
                fontSize: 11,
                letterSpacing: 1.8,
                color: QfColors.cyan,
              ),
            ),
            const SizedBox(height: 8),
            Container(
              decoration: ShapeDecoration(
                color: QfColors.surface,
                shape: const CutCornerBorder(
                  cut: 10,
                  side: BorderSide(color: QfColors.border),
                ),
              ),
              child: Column(
                children: [
                  // 1. Medición de uso
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                l10n.prefsAnalyticsTitle,
                                style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: QfColors.text),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                l10n.prefsAnalyticsBody,
                                style: const TextStyle(fontSize: 12, color: QfColors.text2),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 8),
                        QfSwitch(
                          value: services.analyticsAllowed,
                          onChanged: busy
                              ? null
                              : (value) => change(
                                  () => services.setConsent(
                                    analytics: value,
                                    diagnostics: services.diagnosticsAllowed,
                                  ),
                                ),
                        ),
                      ],
                    ),
                  ),
                  const Divider(color: QfColors.divider, height: 1),

                  // 2. Informes de errores
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                l10n.prefsDiagnosticsTitle,
                                style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: QfColors.text),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                l10n.prefsDiagnosticsBody,
                                style: const TextStyle(fontSize: 12, color: QfColors.text2),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 8),
                        QfSwitch(
                          value: services.diagnosticsAllowed,
                          onChanged: busy
                              ? null
                              : (value) => change(
                                  () => services.setConsent(
                                    analytics: services.analyticsAllowed,
                                    diagnostics: value,
                                  ),
                                ),
                        ),
                      ],
                    ),
                  ),
                  const Divider(color: QfColors.divider, height: 1),

                  // 3. Medición de anuncios (Meta)
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
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
                                    l10n.prefsAdsTitle,
                                    style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: QfColors.text),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    l10n.prefsAdsBody,
                                    style: const TextStyle(fontSize: 12, color: QfColors.text2),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(width: 8),
                            QfSwitch(
                              key: const ValueKey('prefs-ads'),
                              value: services.adsAllowed,
                              onChanged: busy
                                  ? null
                                  : (value) => change(() async {
                                      await services.setAdsConsent(value);
                                      await widget.api.syncPreferences();
                                    }),
                            ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        GestureDetector(
                          onTap: () => setState(() => showMoreMeta = !showMoreMeta),
                          child: Text(
                            showMoreMeta ? l10n.rewardsLedgerLess.toUpperCase() : l10n.rewardsLedgerMore.toUpperCase(),
                            style: const TextStyle(
                              fontFamily: qfDisplay,
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                              letterSpacing: 1.0,
                              color: QfColors.cyan,
                            ),
                          ),
                        ),
                        if (showMoreMeta) ...[
                          const SizedBox(height: 6),
                          Text(
                            l10n.prefsAdsBody,
                            style: const TextStyle(fontSize: 12, color: QfColors.text2),
                          ),
                        ],
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 6),
            Text(
              l10n.prefsNote,
              style: const TextStyle(fontSize: 11, color: QfColors.muted),
            ),
            const SizedBox(height: 14),

            // // TUS DERECHOS
            Text(
              '// ${l10n.prefsPrivacyRights.toUpperCase()}',
              style: const TextStyle(
                fontFamily: qfDisplay,
                fontWeight: FontWeight.w700,
                fontSize: 11,
                letterSpacing: 1.8,
                color: QfColors.cyan,
              ),
            ),
            const SizedBox(height: 8),
            Container(
              decoration: ShapeDecoration(
                color: QfColors.surface,
                shape: const CutCornerBorder(
                  cut: 10,
                  side: BorderSide(color: QfColors.border),
                ),
              ),
              child: Column(
                children: [
                  InkWell(
                    onTap: () => launchUrl(
                      Uri.parse('https://pronosticosdeportivos.pro/legal/privacidad'),
                      mode: LaunchMode.externalApplication,
                    ),
                    child: Container(
                      constraints: const BoxConstraints(minHeight: 52),
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                      child: Row(
                        children: [
                          const Icon(Icons.shield_outlined, size: 22, color: QfColors.text2),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              l10n.prefsPrivacyRights,
                              style: const TextStyle(
                                fontSize: 14,
                                fontWeight: FontWeight.w600,
                                color: QfColors.text,
                              ),
                            ),
                          ),
                          const Icon(Icons.chevron_right, size: 18, color: QfColors.muted),
                        ],
                      ),
                    ),
                  ),
                  const Divider(color: QfColors.divider, height: 1),
                  InkWell(
                    key: const ValueKey('prefs-delete-account'),
                    onTap: () => launchUrl(
                      Uri.parse('https://pronosticosdeportivos.pro/legal/eliminar-cuenta'),
                      mode: LaunchMode.externalApplication,
                    ),
                    child: Container(
                      constraints: const BoxConstraints(minHeight: 60),
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                      child: Row(
                        children: [
                          const Icon(Icons.delete_outline, size: 22, color: QfColors.magenta),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  l10n.prefsDeleteAccount,
                                  style: const TextStyle(
                                    fontSize: 14,
                                    fontWeight: FontWeight.w700,
                                    color: QfColors.magentaText,
                                  ),
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  l10n.prefsDeleteAccountHint,
                                  style: const TextStyle(fontSize: 12, color: QfColors.text2),
                                ),
                              ],
                            ),
                          ),
                          const Icon(Icons.chevron_right, size: 18, color: QfColors.muted),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }
}

class FirebaseInbox extends StatefulWidget {
  const FirebaseInbox({super.key, required this.api});
  final QuantFutApi api;
  @override
  State<FirebaseInbox> createState() => _FirebaseInboxState();
}

class _FirebaseInboxState extends State<FirebaseInbox> {
  List<JsonMap>? rows;
  String? error;
  String selectedFilter = 'todos';

  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    try {
      final data = jsonMap(
        await widget.api.request('/app/v1/firebase/notifications'),
      );
      if (mounted) {
        setState(() {
          rows = jsonRows(data['notifications']);
          error = null;
        });
      }
    } catch (failure) {
      if (mounted) setState(() => error = '$failure');
    }
  }

  Future<void> open(JsonMap row) async {
    try {
      await widget.api.request(
        '/app/v1/firebase/notifications/${row['notification_id']}/read',
        body: {},
      );
      final id = notificationMatchId({
        'route': 'match',
        'match_id': row['match_id'],
      });
      if (!mounted) return;
      if (id != null) {
        await Navigator.of(context).push(
          MaterialPageRoute<void>(
            builder: (_) => Scaffold(
              backgroundColor: QfColors.bg,
              appBar: qfAppBar(context.l10n.inboxMatch),
              body: LiveMatchDetail(
                api: widget.api,
                id: id,
                onVip: () => Navigator.of(context).pop(),
              ),
            ),
          ),
        );
      }
      await load();
    } catch (failure) {
      if (mounted) liveNotice(context, '$failure');
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final allRows = rows ?? [];
    final unreadCount = allRows.where((r) => r['read_at'] == null).length;

    final filtered = selectedFilter == 'todos'
        ? allRows
        : allRows.where((r) => r['sport']?.toString() == selectedFilter).toList();

    return Theme(
      data: qfTheme(),
      child: Scaffold(
        backgroundColor: QfColors.bg,
        appBar: PreferredSize(
          preferredSize: const Size.fromHeight(56),
          child: Container(
            height: 56,
            padding: const EdgeInsets.only(left: 6, right: 14),
            decoration: const BoxDecoration(
              color: QfColors.bg,
              border: Border(bottom: BorderSide(color: QfColors.border)),
            ),
            child: Row(
              children: [
                IconButton(
                  tooltip: MaterialLocalizations.of(context).backButtonTooltip,
                  constraints: const BoxConstraints(minWidth: 44, minHeight: 44),
                  icon: const Icon(Icons.chevron_left, color: QfColors.text2, size: 24),
                  onPressed: () => Navigator.of(context).maybePop(),
                ),
                Expanded(
                  child: Text(
                    l10n.inboxTitle.toUpperCase(),
                    style: const TextStyle(
                      fontFamily: qfDisplay,
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1.0,
                      color: QfColors.text,
                    ),
                  ),
                ),
                if (unreadCount > 0)
                  Text(
                    l10n.inboxUnread(unreadCount).toUpperCase(),
                    style: const TextStyle(
                      fontFamily: qfMono,
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      color: QfColors.cyan,
                    ),
                  ),
              ],
            ),
          ),
        ),
        body: error != null
            ? Center(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      qfError(error!),
                      const SizedBox(height: 12),
                      TextButton(
                        style: qfText(),
                        onPressed: load,
                        child: Text(l10n.commonRetry),
                      ),
                    ],
                  ),
                ),
              )
            : rows == null
            ? const Center(child: CircularProgressIndicator(color: QfColors.cyan))
            : RefreshIndicator(
                onRefresh: load,
                child: ListView(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                  children: [
                    // Sport Filter Chips
                    SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      child: Row(
                        children: [
                          _filterChip(
                            label: '${l10n.commonAll.toUpperCase()} · ${allRows.length}',
                            selected: selectedFilter == 'todos',
                            onTap: () => setState(() => selectedFilter = 'todos'),
                          ),
                          for (final sport in sportCatalog.ids)
                            _filterChip(
                              label:
                                  '${sportCatalog.spec(sport).label(l10n).toUpperCase()} · ${allRows.where((r) => r['sport']?.toString() == sport).length}',
                              selected: selectedFilter == sport,
                              onTap: () => setState(() => selectedFilter = sport),
                            ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 12),

                    // Lista o estado vacío
                    if (filtered.isEmpty)
                      Container(
                        padding: const EdgeInsets.symmetric(vertical: 40, horizontal: 16),
                        decoration: BoxDecoration(
                          border: Border.all(color: QfColors.divider, style: BorderStyle.solid),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Column(
                          children: [
                            const Icon(Icons.notifications_none, size: 40, color: QfColors.muted),
                            const SizedBox(height: 10),
                            Text(
                              l10n.inboxEmpty.toUpperCase(),
                              style: const TextStyle(
                                fontFamily: qfDisplay,
                                fontSize: 16,
                                fontWeight: FontWeight.w700,
                                letterSpacing: 1.0,
                                color: QfColors.text,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              l10n.inboxEmptySubtitle,
                              textAlign: TextAlign.center,
                              style: const TextStyle(fontSize: 12, color: QfColors.text2),
                            ),
                          ],
                        ),
                      )
                    else
                      for (final row in filtered)
                        _InboxRow(row: row, onTap: () => open(row)),
                  ],
                ),
              ),
      ),
    );
  }

  Widget _filterChip({
    required String label,
    required bool selected,
    required VoidCallback onTap,
  }) => Padding(
    padding: const EdgeInsets.only(right: 6),
    child: InkWell(
      onTap: onTap,
      child: Container(
        constraints: const BoxConstraints(minHeight: 40),
        padding: const EdgeInsets.symmetric(horizontal: 14),
        alignment: Alignment.center,
        decoration: ShapeDecoration(
          color: selected ? QfColors.cyan.withValues(alpha: .1) : Colors.transparent,
          shape: CutCornerBorder(
            cut: 8,
            side: BorderSide(color: selected ? QfColors.cyan : QfColors.border),
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontFamily: qfDisplay,
            fontSize: 12,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.8,
            color: selected ? QfColors.cyan : QfColors.text2,
          ),
        ),
      ),
    ),
  );
}

/// Aviso CyberCore: sin leer con borde resaltado y campana activa.
/// La etiqueta de deporte solo sale si el aviso trae `sport`; si no, no se inventa.
class _InboxRow extends StatelessWidget {
  const _InboxRow({required this.row, required this.onTap});

  final JsonMap row;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final unread = row['read_at'] == null;
    final spec = sportCatalog.find(row['sport']?.toString());
    final title = row['title']?.toString() ?? '';
    final body = row['body']?.toString() ?? '';
    final timeStr = row['created_at'] != null ? kickoffText(row['created_at']) : '';

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: InkWell(
        key: ValueKey('inbox-${row['notification_id']}'),
        onTap: onTap,
        child: Container(
          constraints: const BoxConstraints(minHeight: 56),
          padding: const EdgeInsets.all(10),
          decoration: ShapeDecoration(
            color: unread ? QfColors.cyan.withValues(alpha: .05) : QfColors.surface,
            shape: CutCornerBorder(
              cut: 10,
              side: BorderSide(
                color: unread ? QfColors.borderStrong : QfColors.border,
              ),
            ),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Avatar o icono
              Container(
                width: 44,
                height: 44,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: QfColors.surface2,
                  border: Border.all(color: QfColors.border),
                ),
                child: Icon(
                  spec?.icon ?? Icons.notifications_none,
                  size: 22,
                  color: unread ? QfColors.cyan : QfColors.text2,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (spec != null)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 4),
                        child: Semantics(
                          label: context.l10n.inboxSportTag(spec.label(context.l10n)),
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                            decoration: BoxDecoration(
                              border: Border.all(color: QfColors.border),
                            ),
                            child: Text(
                              spec.label(context.l10n).toUpperCase(),
                              key: ValueKey('inbox-sport-${spec.id}'),
                              style: const TextStyle(
                                fontFamily: qfDisplay,
                                fontSize: 9,
                                fontWeight: FontWeight.w700,
                                letterSpacing: 1.2,
                                color: QfColors.cyan,
                              ),
                            ),
                          ),
                        ),
                      ),
                    Text(
                      title,
                      style: TextStyle(
                        color: QfColors.text,
                        fontWeight: unread ? FontWeight.w700 : FontWeight.w500,
                        fontSize: 14,
                      ),
                    ),
                    if (body.isNotEmpty) ...[
                      const SizedBox(height: 2),
                      Text(
                        body,
                        style: const TextStyle(fontSize: 12, color: QfColors.text2),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  if (timeStr.isNotEmpty)
                    Text(
                      timeStr,
                      style: const TextStyle(
                        fontFamily: qfMono,
                        fontSize: 10,
                        fontWeight: FontWeight.w500,
                        color: QfColors.muted,
                      ),
                    ),
                  if (unread) ...[
                    const SizedBox(height: 6),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(
                          Icons.notifications_active_outlined,
                          size: 16,
                          color: QfColors.cyan,
                        ),
                        const SizedBox(width: 4),
                        Container(
                          width: 8,
                          height: 8,
                          decoration: const BoxDecoration(
                            shape: BoxShape.circle,
                            color: QfColors.cyan,
                            boxShadow: [
                              BoxShadow(color: QfColors.cyan, blurRadius: 6),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ],
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
