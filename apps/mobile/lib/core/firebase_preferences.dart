import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../l10n/app_locale.dart';
import '../l10n/language_picker.dart';
import '../product/live_api.dart';
import '../product/live_detail.dart';
import '../product/live_widgets.dart';
import '../product/qf_shapes.dart';
import '../product/qf_theme.dart';
import '../product/sports.dart';
import 'firebase_services.dart';

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
  Widget build(BuildContext context) => Theme(
    data: qfTheme(),
    child: Scaffold(
    backgroundColor: QfColors.bg,
    appBar: qfAppBar(context.l10n.prefsTitle),
    body: ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (busy) const LinearProgressIndicator(),
        if (error != null) qfError(error!),
        ListTile(
          key: const ValueKey('prefs-language'),
          contentPadding: EdgeInsets.zero,
          minTileHeight: 52,
          leading: const Icon(Icons.language_rounded, color: QfColors.text2),
          title: Text(context.l10n.languageTitle),
          subtitle: Text(appLanguages[AppLocale.instance.code]!),
          trailing: const Icon(Icons.chevron_right, color: QfColors.muted),
          onTap: busy ? null : () => showLanguagePicker(context),
        ),
        liveText(context.l10n.prefsLanguageNote, size: 12, color: QfColors.text2),
        const Divider(color: QfColors.border, height: 24),
        SwitchListTile(
          title: Text(context.l10n.prefsAnalyticsTitle),
          subtitle: Text(context.l10n.prefsAnalyticsBody),
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
        SwitchListTile(
          title: Text(context.l10n.prefsDiagnosticsTitle),
          subtitle: Text(context.l10n.prefsDiagnosticsBody),
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
        SwitchListTile(
          key: const ValueKey('prefs-ads'),
          title: Text(context.l10n.prefsAdsTitle),
          subtitle: Text(context.l10n.prefsAdsBody),
          value: services.adsAllowed,
          onChanged: busy
              ? null
              : (value) => change(() async {
                  await services.setAdsConsent(value);
                  await widget.api.syncPreferences();
                }),
        ),
        SwitchListTile(
          title: Text(context.l10n.prefsNotificationsTitle),
          subtitle: Text(
            widget.api.firebaseConnected
                ? context.l10n.prefsNotificationsOn
                : context.l10n.prefsNotificationsOff,
          ),
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
        if (services.notificationStatus != null)
          liveText(
            switch (services.notificationStatus!) {
              NotificationStatus.permissionDenied =>
                context.l10n.notificationPermissionDenied,
              NotificationStatus.iosPending =>
                context.l10n.notificationIosPending,
            },
            size: 12,
            color: QfColors.text2,
          ),
        if (widget.api.firebaseConnected)
          ListTile(
            key: const ValueKey('prefs-inbox'),
            minTileHeight: 52,
            leading: const Icon(Icons.notifications_outlined, color: QfColors.text2),
            title: Text(context.l10n.prefsInbox),
            trailing: const Icon(Icons.chevron_right, color: QfColors.muted),
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute<void>(
                builder: (_) => FirebaseInbox(api: widget.api),
              ),
            ),
          ),
        const Divider(color: QfColors.border, height: 24),
        ListTile(
          minTileHeight: 52,
          title: Text(context.l10n.prefsPrivacyRights),
          trailing: const Icon(Icons.open_in_new, color: QfColors.primary),
          onTap: () => launchUrl(
            Uri.parse('https://pronosticosdeportivos.pro/legal/privacidad'),
            mode: LaunchMode.externalApplication,
          ),
        ),
        ListTile(
          minTileHeight: 52,
          title: Text(context.l10n.prefsDeleteAccount),
          subtitle: Text(context.l10n.prefsDeleteAccountHint),
          trailing: const Icon(Icons.open_in_new, color: QfColors.primary),
          onTap: () => launchUrl(
            Uri.parse(
              'https://pronosticosdeportivos.pro/legal/eliminar-cuenta',
            ),
            mode: LaunchMode.externalApplication,
          ),
        ),
        liveText(context.l10n.prefsNote, size: 12, color: QfColors.text2),
      ],
    ),
    ),
  );
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
  Widget build(BuildContext context) => Theme(
    data: qfTheme(),
    child: Scaffold(
    backgroundColor: QfColors.bg,
    appBar: qfAppBar(context.l10n.inboxTitle),
    body: error != null
        ? Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  qfError(error!),
                  TextButton(
                    style: qfText(),
                    onPressed: load,
                    child: Text(context.l10n.commonRetry),
                  ),
                ],
              ),
            ),
          )
        : rows == null
        ? const Center(child: CircularProgressIndicator())
        : rows!.isEmpty
        ? Center(child: liveText(context.l10n.inboxEmpty, color: QfColors.text2))
        : RefreshIndicator(
            onRefresh: load,
            child: ListView(
              children: [
                for (final row in rows!) _InboxRow(row: row, onTap: () => open(row)),
              ],
            ),
          ),
    ),
  );
}

/// Aviso: sin leer en negrita y con campana activa (no solo color). La etiqueta de deporte
/// solo sale si el aviso trae `sport`; si no, no se inventa.
class _InboxRow extends StatelessWidget {
  const _InboxRow({required this.row, required this.onTap});

  final JsonMap row;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final unread = row['read_at'] == null;
    final sport = SportKind.fromId(row['sport']?.toString());
    final spec = sport == null ? null : sportSpecs[sport]!;
    return InkWell(
      key: ValueKey('inbox-${row['notification_id']}'),
      onTap: onTap,
      child: Container(
        constraints: const BoxConstraints(minHeight: 56),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        decoration: const BoxDecoration(
          border: Border(bottom: BorderSide(color: QfColors.border)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(
              unread ? Icons.notifications_active_outlined : Icons.notifications_none,
              color: unread ? QfColors.primary : QfColors.muted,
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
                        excludeSemantics: true,
                        child: QfBadge(
                          spec.label(context.l10n),
                          key: ValueKey('inbox-sport-${sport!.id}'),
                          color: spec.accent,
                          icon: spec.icon,
                        ),
                      ),
                    ),
                  Text(
                    '${row['title']}',
                    style: TextStyle(
                      color: QfColors.text,
                      fontWeight: unread ? FontWeight.w700 : FontWeight.w400,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text('${row['body']}', style: const TextStyle(fontSize: 13, color: QfColors.text2)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
