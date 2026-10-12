import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../l10n/app_locale.dart';
import '../l10n/language_picker.dart';
import '../product/live_api.dart';
import '../product/live_detail.dart';
import '../product/live_widgets.dart';
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
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: Text(context.l10n.prefsTitle)),
    body: ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (busy) const LinearProgressIndicator(),
        if (error != null) liveText(error!, color: liveGold),
        ListTile(
          key: const ValueKey('prefs-language'),
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.language_rounded),
          title: Text(context.l10n.languageTitle),
          subtitle: Text(appLanguages[AppLocale.instance.code]!),
          trailing: const Icon(Icons.chevron_right),
          onTap: busy ? null : () => showLanguagePicker(context),
        ),
        liveText(context.l10n.prefsLanguageNote, size: 12, color: liveMuted),
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
            color: liveMuted,
          ),
        if (widget.api.firebaseConnected)
          ListTile(
            title: Text(context.l10n.prefsInbox),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute<void>(
                builder: (_) => FirebaseInbox(api: widget.api),
              ),
            ),
          ),
        const SizedBox(height: 16),
        ListTile(
          title: Text(context.l10n.prefsPrivacyRights),
          trailing: const Icon(Icons.open_in_new),
          onTap: () => launchUrl(
            Uri.parse('https://pronosticosdeportivos.pro/legal/privacidad'),
            mode: LaunchMode.externalApplication,
          ),
        ),
        ListTile(
          title: Text(context.l10n.prefsDeleteAccount),
          subtitle: Text(context.l10n.prefsDeleteAccountHint),
          trailing: const Icon(Icons.open_in_new),
          onTap: () => launchUrl(
            Uri.parse(
              'https://pronosticosdeportivos.pro/legal/eliminar-cuenta',
            ),
            mode: LaunchMode.externalApplication,
          ),
        ),
        liveText(context.l10n.prefsNote, size: 12, color: liveMuted),
      ],
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
              appBar: AppBar(title: Text(context.l10n.inboxMatch)),
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
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: Text(context.l10n.inboxTitle)),
    body: error != null
        ? Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(error!),
                TextButton(
                  onPressed: load,
                  child: Text(context.l10n.commonRetry),
                ),
              ],
            ),
          )
        : rows == null
        ? const Center(child: CircularProgressIndicator())
        : rows!.isEmpty
        ? Center(child: Text(context.l10n.inboxEmpty))
        : RefreshIndicator(
            onRefresh: load,
            child: ListView(
              children: [
                for (final row in rows!)
                  ListTile(
                    leading: Icon(
                      row['read_at'] == null
                          ? Icons.notifications_active_outlined
                          : Icons.notifications_none,
                    ),
                    title: Text('${row['title']}'),
                    subtitle: Text('${row['body']}'),
                    onTap: () => open(row),
                  ),
              ],
            ),
          ),
  );
}
