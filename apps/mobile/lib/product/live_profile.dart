import 'package:flutter/material.dart';
import 'package:package_info_plus/package_info_plus.dart';

import '../core/app_update.dart';
import '../l10n/app_locale.dart';
import '../l10n/language_picker.dart';
import 'live_api.dart';
import 'live_widgets.dart';
import 'my_sports.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';
import 'sports.dart';
import '../core/firebase_services.dart';
import '../core/firebase_preferences.dart';

class LiveProfileScreen extends StatefulWidget {
  const LiveProfileScreen({
    super.key,
    required this.api,
    required this.data,
    required this.onVip,
    required this.onChanged,
    this.sportPrefs,
    this.onSportsChanged,
    this.focusSports = 0,
    this.checkUpdate,
  });
  final QuantFutApi api;
  final JsonMap data;
  final VoidCallback onVip;
  final Future<void> Function() onChanged;

  /// Preferencias de deporte del shell; sin ellas no se pinta «Mis deportes».
  final SportPrefs? sportPrefs;
  final Future<void> Function()? onSportsChanged;

  /// Cada vez que cambia (menú «Más» → «Mis deportes») la sección se desplaza a la vista.
  final int focusSports;

  /// Comprobación de versión; por defecto la del arranque ([checkAppUpdate]).
  final Future<AppUpdate?> Function()? checkUpdate;
  @override
  State<LiveProfileScreen> createState() => _LiveProfileScreenState();
}

class _LiveProfileScreenState extends State<LiveProfileScreen> {
  final email = TextEditingController(), password = TextEditingController();
  final _sportsKey = GlobalKey();
  bool busy = false, creating = false, checking = false;
  String? error, version;

  @override
  void initState() {
    super.initState();
    if (widget.focusSports > 0) _focusSports();
    PackageInfo.fromPlatform()
        .then((p) {
          if (mounted) setState(() => version = '${p.version} (${p.buildNumber})');
        })
        .catchError((_) {});
  }

  @override
  void didUpdateWidget(LiveProfileScreen old) {
    super.didUpdateWidget(old);
    if (widget.focusSports != old.focusSports) _focusSports();
  }

  void _focusSports() => WidgetsBinding.instance.addPostFrameCallback((_) {
    final target = _sportsKey.currentContext;
    if (target == null || !mounted) return;
    Scrollable.ensureVisible(
      target,
      duration: MediaQuery.of(context).disableAnimations
          ? Duration.zero
          : const Duration(milliseconds: 300),
    );
  });

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

  /// «Versión de la app»: mismo flujo que el arranque; sin novedad, un aviso.
  Future<void> checkVersion() async {
    if (checking) return;
    setState(() => checking = true);
    final l10n = context.l10n;
    AppUpdate? update;
    try {
      update = await (widget.checkUpdate ?? checkAppUpdate)();
    } catch (_) {
      if (mounted) liveNotice(context, l10n.profileUpdateCheckFailed);
      return;
    } finally {
      if (mounted) setState(() => checking = false);
    }
    if (!mounted) return;
    if (update == null) {
      liveNotice(context, l10n.profileUpToDate);
      return;
    }
    final found = update;
    await showDialog<void>(
      context: context,
      barrierDismissible: !found.required,
      builder: (_) => AppUpdateDialog(update: found),
    );
  }

  Widget _row({
    required Key key,
    required IconData icon,
    required String title,
    String? value,
    Color valueColor = QfColors.text2,
    Widget? trailing,
    VoidCallback? onTap,
  }) => InkWell(
    key: key,
    onTap: onTap,
    child: Container(
      constraints: const BoxConstraints(minHeight: 52),
      decoration: const BoxDecoration(border: Border(top: BorderSide(color: QfColors.border))),
      child: Row(
        children: [
          Icon(icon, size: 20, color: QfColors.text2),
          const SizedBox(width: 10),
          Expanded(child: liveText(title, color: QfColors.text)),
          if (value != null)
            Flexible(
              child: Text(
                value,
                textAlign: TextAlign.end,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: 12, color: valueColor),
              ),
            ),
          trailing ?? (onTap == null ? const SizedBox() : const Icon(Icons.chevron_right, color: QfColors.muted)),
        ],
      ),
    ),
  );

  @override
  Widget build(BuildContext context) {
    final api = widget.api, account = jsonMap(api.account?['account']);
    final l10n = context.l10n;
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          liveHeading(l10n.profileTitle),
          QfCard(
            accent: QfColors.primary,
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
                QfBadge(
                  api.plus ? l10n.profileVipActive : l10n.profileFreePlan,
                  color: api.plus ? QfColors.cta : QfColors.text2,
                  icon: api.plus ? Icons.workspace_premium : null,
                ),
                const SizedBox(height: 12),
                // La única acción ámbar del Perfil.
                liveButton(l10n.profileSeePlans, widget.onVip),
              ],
            ),
          ),
          const SizedBox(height: 12),
          if (!api.signedIn)
            QfCard(
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
                  if (error != null)
                    Row(
                      children: [
                        const Icon(Icons.error_outline, size: 16, color: QfColors.danger),
                        const SizedBox(width: 6),
                        Expanded(child: liveText(error!, color: QfColors.danger, size: 13)),
                      ],
                    ),
                  liveButton(
                    busy
                        ? l10n.commonConnecting
                        : creating
                        ? l10n.profileCreateAccount
                        : l10n.profileSignIn,
                    busy ? null : login,
                    color: QfColors.primary,
                  ),
                  TextButton(
                    style: TextButton.styleFrom(minimumSize: const Size(44, 44)),
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
                    style: TextButton.styleFrom(minimumSize: const Size(44, 44)),
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
            QfCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  liveText('${account['email']}', color: QfColors.text2),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Icon(
                        account['email_verified'] == true ? Icons.check : Icons.schedule,
                        size: 16,
                        color: account['email_verified'] == true ? QfColors.success : QfColors.text2,
                      ),
                      const SizedBox(width: 6),
                      Expanded(
                        child: liveText(
                          account['email_verified'] == true
                              ? l10n.profileEmailVerified
                              : l10n.profileEmailPending,
                          color: account['email_verified'] == true ? QfColors.success : QfColors.text2,
                        ),
                      ),
                    ],
                  ),
                  if (account['email_verified'] != true)
                    TextButton(
                      style: TextButton.styleFrom(minimumSize: const Size(44, 44)),
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
                      color: QfColors.text2,
                      size: 12,
                    ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            liveButton(l10n.profileRefreshAccess, () async {
              try {
                await api.updateAccount();
                await widget.onChanged();
                if (mounted) setState(() {});
              } catch (e) {
                if (context.mounted) liveNotice(context, '$e');
              }
            }, color: QfColors.primary),
          ],
          if (widget.sportPrefs != null)
            MySportsSection(
              key: _sportsKey,
              prefs: widget.sportPrefs!,
              onChanged: widget.onSportsChanged ?? () async {},
            ),
          qfTitle(l10n.profilePreferences),
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
            _row(
              key: ValueKey('profile-${item.$1}'),
              icon: item.$3,
              title: item.$2,
              value: item.$1 == 'idiomas'
                  ? appLanguages[AppLocale.instance.code]!
                  : featureMessage(widget.data, item.$1),
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
          _row(
            key: const ValueKey('profile-odds'),
            icon: Icons.show_chart,
            title: l10n.profileOddsFormat,
            value: l10n.profileOddsFormatValue,
          ),
          qfTitle(l10n.profileGeneral),
          _row(
            key: const ValueKey('profile-version'),
            icon: Icons.system_update_outlined,
            title: l10n.profileAppVersion,
            value: version,
            valueColor: QfColors.muted,
            trailing: Padding(
              padding: const EdgeInsets.only(left: 8),
              child: checking
                  ? const SizedBox.square(
                      dimension: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : Text(
                      l10n.profileCheckUpdate,
                      style: const TextStyle(fontSize: 12, color: QfColors.primary),
                    ),
            ),
            onTap: checkVersion,
          ),
          _row(
            key: const ValueKey('profile-connection'),
            icon: Icons.check_circle_outline,
            title: l10n.profileConnected,
          ),
          if (api.signedIn)
            _row(
              key: const ValueKey('profile-sign-out'),
              icon: Icons.logout,
              title: l10n.profileSignOut,
              trailing: const SizedBox(),
              onTap: () async {
                try {
                  await api.logout();
                } catch (e) {
                  if (context.mounted) liveNotice(context, '$e');
                }
                await widget.onChanged();
                if (mounted) setState(() {});
              },
            ),
          const SizedBox(height: 12),
          liveText(l10n.disclaimerProbability, size: 12, color: QfColors.muted),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}
