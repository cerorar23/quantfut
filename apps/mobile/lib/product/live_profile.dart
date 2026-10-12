import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import '../l10n/language_picker.dart';
import 'live_api.dart';
import 'live_widgets.dart';
import '../core/firebase_services.dart';
import '../core/firebase_preferences.dart';

class LiveProfileScreen extends StatefulWidget {
  const LiveProfileScreen({
    super.key,
    required this.api,
    required this.data,
    required this.onVip,
    required this.onChanged,
  });
  final QuantFutApi api;
  final JsonMap data;
  final VoidCallback onVip;
  final Future<void> Function() onChanged;
  @override
  State<LiveProfileScreen> createState() => _LiveProfileScreenState();
}

class _LiveProfileScreenState extends State<LiveProfileScreen> {
  final email = TextEditingController(), password = TextEditingController();
  bool busy = false, creating = false;
  String? error;
  @override
  void dispose() {
    email.dispose();
    password.dispose();
    super.dispose();
  }

  Future<void> login() async {
    setState(() {
      busy = true;
      error = null;
    });
    try {
      if (creating) {
        await widget.api.register(email.text, password.text);
      } else {
        await widget.api.login(email.text, password.text);
      }
      password.clear();
      await widget.onChanged();
    } catch (e) {
      if (mounted) setState(() => error = '$e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final api = widget.api, account = jsonMap(api.account?['account']);
    final l10n = context.l10n;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        liveHeading(l10n.profileTitle),
        liveCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              liveText(
                api.signedIn
                    ? '${account['display_name'] ?? account['email']}'
                    : l10n.profileYourAccount,
                size: 18,
                bold: true,
              ),
              const SizedBox(height: 8),
              liveText(
                api.plus ? l10n.profileVipActive : l10n.profileFreePlan,
                color: api.plus ? liveGold : liveMuted,
              ),
              const SizedBox(height: 12),
              liveButton(l10n.profileSeePlans, widget.onVip),
            ],
          ),
        ),
        if (!api.signedIn)
          liveCard(
            child: Column(
              children: [
                TextField(
                  controller: email,
                  keyboardType: TextInputType.emailAddress,
                  autofillHints: const [AutofillHints.email],
                  decoration: InputDecoration(labelText: l10n.profileEmail),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: password,
                  obscureText: true,
                  autofillHints: const [AutofillHints.password],
                  decoration: InputDecoration(labelText: l10n.profilePassword),
                  onSubmitted: (_) => busy ? null : login(),
                ),
                const SizedBox(height: 16),
                if (error != null) liveText(error!, color: liveGold),
                liveButton(
                  busy
                      ? l10n.commonConnecting
                      : creating
                      ? l10n.profileCreateAccount
                      : l10n.profileSignIn,
                  busy ? null : login,
                  color: liveCyan,
                ),
                TextButton(
                  onPressed: busy
                      ? null
                      : () => setState(() {
                          creating = !creating;
                          error = null;
                        }),
                  child: Text(
                    creating ? l10n.profileHaveAccount : l10n.profileCreateOne,
                  ),
                ),
                TextButton(
                  onPressed: busy
                      ? null
                      : () async {
                          try {
                            await api.forgotPassword(email.text);
                            if (context.mounted) {
                              liveNotice(context, l10n.profileForgotSent);
                            }
                          } catch (e) {
                            if (context.mounted) liveNotice(context, '$e');
                          }
                        },
                  child: Text(l10n.profileForgot),
                ),
              ],
            ),
          )
        else ...[
          liveCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                liveText('${account['email']}', color: liveMuted),
                const SizedBox(height: 8),
                liveText(
                  account['email_verified'] == true
                      ? l10n.profileEmailVerified
                      : l10n.profileEmailPending,
                  color: liveCyan,
                ),
                if (account['email_verified'] != true)
                  TextButton(
                    onPressed: () async {
                      try {
                        await api.resendVerification();
                        if (context.mounted) {
                          liveNotice(context, l10n.profileVerificationSent);
                        }
                      } catch (e) {
                        if (context.mounted) liveNotice(context, '$e');
                      }
                    },
                    child: Text(l10n.profileSendVerification),
                  ),
                if (api.account?['subscription'] != null)
                  liveText(
                    l10n.profileValidUntil(
                      kickoffText(
                        jsonMap(api.account?['subscription'])['ends_at'],
                      ),
                    ),
                    color: liveMuted,
                    size: 12,
                  ),
              ],
            ),
          ),
          liveButton(l10n.profileRefreshAccess, () async {
            try {
              await api.updateAccount();
              await widget.onChanged();
              if (mounted) setState(() {});
            } catch (e) {
              if (context.mounted) liveNotice(context, '$e');
            }
          }, color: liveCyan),
          TextButton(
            onPressed: () async {
              try {
                await api.logout();
              } catch (e) {
                if (context.mounted) liveNotice(context, '$e');
              }
              await widget.onChanged();
              if (mounted) setState(() {});
            },
            child: Text(l10n.profileSignOut),
          ),
        ],
        liveHeading(l10n.profilePreferences),
        for (final item in [
          (
            'notificaciones',
            l10n.profileNotifications,
            Icons.notifications_outlined,
          ),
          (
            'balance',
            l10n.profileBalance,
            Icons.account_balance_wallet_outlined,
          ),
          ('medicion', l10n.profileMeasurement, Icons.shield_outlined),
          ('idiomas', l10n.profileLanguage, Icons.language),
        ])
          liveCard(
            child: ListTile(
              key: ValueKey('profile-${item.$1}'),
              contentPadding: EdgeInsets.zero,
              leading: Icon(item.$3, color: liveCyan),
              title: liveText(item.$2, bold: true),
              subtitle: liveText(
                item.$1 == 'idiomas'
                    ? appLanguages[AppLocale.instance.code]!
                    : featureMessage(widget.data, item.$1),
                size: 12,
                color: liveMuted,
              ),
              trailing: const Icon(Icons.chevron_right, color: liveMuted),
              onTap: () {
                if (item.$1 == 'idiomas') {
                  showLanguagePicker(context);
                } else if (FirebaseServices.current != null &&
                    item.$1 != 'balance') {
                  Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => FirebasePreferencesScreen(api: api),
                    ),
                  );
                } else {
                  liveNotice(context, featureMessage(widget.data, item.$1));
                }
              },
            ),
          ),
        liveCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              liveText(l10n.profileOddsFormat, bold: true),
              const SizedBox(height: 6),
              liveText(l10n.profileOddsFormatValue, color: liveMuted, size: 12),
            ],
          ),
        ),
        liveHeading(l10n.profileGeneral),
        liveCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              liveText(l10n.profileAppVersion, bold: true),
              const SizedBox(height: 6),
              liveText(l10n.profileConnected, color: liveMuted, size: 12),
            ],
          ),
        ),
        liveText(l10n.disclaimerProbability, size: 12, color: liveMuted),
        const SizedBox(height: 24),
      ],
    );
  }
}
