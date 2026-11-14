import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:package_info_plus/package_info_plus.dart';

import '../core/app_update.dart';
import '../core/firebase_preferences.dart';
import '../core/firebase_services.dart';
import '../l10n/app_locale.dart';
import '../l10n/language_picker.dart';
import 'live_api.dart';
import 'live_widgets.dart';
import 'my_sports.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';
import 'sports.dart';

class LiveProfileScreen extends StatefulWidget {
  const LiveProfileScreen({
    super.key,
    required this.api,
    required this.data,
    required this.onVip,
    required this.onChanged,
    this.sportPrefs,
    this.onSportsChanged,
    this.focusSports = false,
    this.onFocusHandled,
    this.checkUpdate,
  });
  final QuantFutApi api;
  final JsonMap data;
  final VoidCallback onVip;
  final Future<void> Function() onChanged;

  /// Preferencias de deporte del shell; sin ellas no se pinta «Mis deportes».
  final SportPrefs? sportPrefs;
  final Future<void> Function()? onSportsChanged;

  /// Petición de foco del menú «Más» → «Mis deportes»: la sección se desplaza a la vista
  /// una vez y se avisa con [onFocusHandled] para que el shell la retire.
  final bool focusSports;
  final VoidCallback? onFocusHandled;

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
    if (widget.focusSports) _focusSports();
    PackageInfo.fromPlatform()
        .then((p) {
          if (mounted) setState(() => version = '${p.version} (${p.buildNumber})');
        })
        .catchError((_) {});
  }

  @override
  void didUpdateWidget(LiveProfileScreen old) {
    super.didUpdateWidget(old);
    if (widget.focusSports && !old.focusSports) _focusSports();
  }

  void _focusSports() => WidgetsBinding.instance.addPostFrameCallback((_) {
    if (!mounted) return;
    widget.onFocusHandled?.call();
    final target = _sportsKey.currentContext;
    if (target == null) return;
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

  String _initials(QuantFutApi api, JsonMap account) {
    if (!api.signedIn) return 'QF';
    final name = (account['display_name'] ?? account['email'] ?? '').toString().trim();
    if (name.isEmpty) return 'QF';
    final parts = name.split(RegExp(r'[\s@._-]+')).where((p) => p.isNotEmpty).toList();
    if (parts.length >= 2) {
      return '${parts[0][0]}${parts[1][0]}'.toUpperCase();
    }
    return name.substring(0, math.min(2, name.length)).toUpperCase();
  }

  String _maskEmail(String email) {
    final at = email.indexOf('@');
    if (at <= 2) return email;
    final prefix = email.substring(0, 2);
    final domain = email.substring(at);
    return '$prefix•••$domain';
  }

  Widget _row({
    required Key key,
    required String title,
    String? value,
    Color valueColor = QfColors.cyan,
    Widget? trailing,
    bool isLast = false,
    VoidCallback? onTap,
  }) => InkWell(
    key: key,
    onTap: onTap,
    child: Container(
      constraints: const BoxConstraints(minHeight: 46),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        border: isLast ? null : const Border(bottom: BorderSide(color: QfColors.divider)),
      ),
      child: Row(
        children: [
          Expanded(
            child: Text(
              title,
              style: const TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: QfColors.text,
              ),
            ),
          ),
          if (value != null)
            Flexible(
              child: Text(
                value,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontFamily: qfMono,
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                  color: valueColor,
                ),
              ),
            ),
          ?trailing,
        ],
      ),
    ),
  );

  @override
  Widget build(BuildContext context) {
    final api = widget.api, account = jsonMap(api.account?['account']);
    final l10n = context.l10n;
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Tarjeta de cuenta CyberCore (§5.6)
          Container(
            key: const ValueKey('profile-account-card'),
            decoration: ShapeDecoration(
              color: QfColors.surface,
              shape: const CutCornerBorder(
                cut: 16,
                side: BorderSide(color: QfColors.borderStrong),
              ),
            ),
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    Container(
                      width: 46,
                      height: 46,
                      alignment: Alignment.center,
                      decoration: ShapeDecoration(
                        color: QfColors.cyan.withValues(alpha: .08),
                        shape: const CutCornerBorder(
                          cut: 10,
                          side: BorderSide(color: QfColors.borderStrong),
                        ),
                      ),
                      child: Text(
                        _initials(api, account),
                        style: const TextStyle(
                          fontFamily: qfMono,
                          fontSize: 16,
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
                            api.signedIn
                                ? _maskEmail('${account['email'] ?? account['display_name'] ?? ''}')
                                : l10n.profileYourAccount,
                            style: const TextStyle(
                              fontFamily: qfMono,
                              fontSize: 13,
                              fontWeight: FontWeight.w500,
                              color: QfColors.text,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          const SizedBox(height: 4),
                          Wrap(
                            spacing: 6,
                            runSpacing: 4,
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                decoration: BoxDecoration(
                                  border: Border.all(
                                    color: api.plus ? QfColors.yellow : QfColors.divider,
                                  ),
                                ),
                                child: Text(
                                  (api.plus ? l10n.profileVipActive : l10n.profileFreePlan).toUpperCase(),
                                  style: TextStyle(
                                    fontFamily: qfDisplay,
                                    fontSize: 11,
                                    fontWeight: FontWeight.w700,
                                    letterSpacing: 1.2,
                                    color: api.plus ? QfColors.yellow : QfColors.text2,
                                  ),
                                ),
                              ),
                              if (api.signedIn)
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                  decoration: BoxDecoration(
                                    border: Border.all(
                                      color: account['email_verified'] == true
                                          ? QfColors.green.withValues(alpha: .4)
                                          : QfColors.divider,
                                    ),
                                  ),
                                  child: Text(
                                    (account['email_verified'] == true
                                            ? l10n.profileEmailVerified
                                            : l10n.profileEmailPending)
                                        .toUpperCase(),
                                    style: TextStyle(
                                      fontFamily: qfDisplay,
                                      fontSize: 11,
                                      fontWeight: FontWeight.w700,
                                      letterSpacing: 1.2,
                                      color: account['email_verified'] == true
                                          ? QfColors.green
                                          : QfColors.text2,
                                    ),
                                  ),
                                ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                InkWell(
                  onTap: widget.onVip,
                  child: Container(
                    constraints: const BoxConstraints(minHeight: 48),
                    alignment: Alignment.center,
                    decoration: ShapeDecoration(
                      color: QfColors.yellow.withValues(alpha: .08),
                      shape: CutCornerBorder(
                        cut: 10,
                        side: BorderSide(color: QfColors.yellow.withValues(alpha: .5)),
                      ),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.workspace_premium, size: 18, color: QfColors.yellow),
                        const SizedBox(width: 8),
                        Text(
                          l10n.profileSeePlans.toUpperCase(),
                          style: const TextStyle(
                            fontFamily: qfDisplay,
                            fontSize: 15,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 1.0,
                            color: QfColors.yellow,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 10),

          // En caso de no haber iniciado sesión, formulario
          if (!api.signedIn) ...[
            Container(
              decoration: ShapeDecoration(
                color: QfColors.surface,
                shape: const CutCornerBorder(
                  cut: 10,
                  side: BorderSide(color: QfColors.border),
                ),
              ),
              padding: const EdgeInsets.all(14),
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
            ),
            const SizedBox(height: 10),
          ] else ...[
            // Si está autenticado, botón de actualizar acceso
            liveButton(l10n.profileRefreshAccess, () async {
              try {
                await api.updateAccount();
                await widget.onChanged();
                if (mounted) setState(() {});
              } catch (e) {
                if (context.mounted) liveNotice(context, '$e');
              }
            }, color: QfColors.primary),
            const SizedBox(height: 10),
          ],

          // Mis deportes
          if (widget.sportPrefs != null)
            MySportsSection(
              key: _sportsKey,
              prefs: widget.sportPrefs!,
              onChanged: widget.onSportsChanged ?? () async {},
            ),

          // Preferencias
          const SizedBox(height: 14),
          Text(
            l10n.profilePreferences.toUpperCase(),
            style: const TextStyle(
              fontFamily: qfDisplay,
              fontWeight: FontWeight.w700,
              fontSize: 13,
              letterSpacing: 1.4,
              color: QfColors.text,
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
                _row(
                  key: const ValueKey('profile-notificaciones'),
                  title: l10n.profileNotifications,
                  value: 'Por deporte ›',
                  onTap: () {
                    if (FirebaseServices.current != null) {
                      Navigator.of(context).push(
                        MaterialPageRoute<void>(
                          builder: (_) => FirebasePreferencesScreen(api: api),
                        ),
                      );
                    } else {
                      liveNotice(context, featureMessage(widget.data, 'notificaciones'));
                    }
                  },
                ),
                _row(
                  key: const ValueKey('profile-idiomas'),
                  title: l10n.profileLanguage,
                  value: '${appLanguages[AppLocale.instance.code]!} ›',
                  onTap: () => showLanguagePicker(context),
                ),
                _row(
                  key: const ValueKey('profile-odds'),
                  title: l10n.profileOddsFormat,
                  value: 'Decimal ›',
                ),
                _row(
                  key: const ValueKey('profile-medicion'),
                  title: l10n.prefsPrivacyRights,
                  value: '›',
                  isLast: true,
                  onTap: () {
                    if (FirebaseServices.current != null) {
                      Navigator.of(context).push(
                        MaterialPageRoute<void>(
                          builder: (_) => FirebasePreferencesScreen(api: api),
                        ),
                      );
                    } else {
                      liveNotice(context, featureMessage(widget.data, 'medicion'));
                    }
                  },
                ),
              ],
            ),
          ),

          // Versión y Cerrar sesión
          const SizedBox(height: 12),
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
                _row(
                  key: const ValueKey('profile-version'),
                  title: l10n.profileAppVersion,
                  value: version,
                  valueColor: QfColors.text2,
                  trailing: checking
                      ? const Padding(
                          padding: EdgeInsets.only(left: 8),
                          child: SizedBox.square(
                            dimension: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          ),
                        )
                      : (version == null
                          ? Text(
                              l10n.profileCheckUpdate,
                              style: const TextStyle(
                                fontFamily: qfMono,
                                fontSize: 12,
                                color: QfColors.cyan,
                              ),
                            )
                          : null),
                  isLast: !api.signedIn,
                  onTap: checkVersion,
                ),
                if (api.signedIn)
                  InkWell(
                    key: const ValueKey('profile-sign-out'),
                    onTap: () async {
                      try {
                        await api.logout();
                      } catch (e) {
                        if (context.mounted) liveNotice(context, '$e');
                      }
                      await widget.onChanged();
                      if (mounted) setState(() {});
                    },
                    child: Container(
                      constraints: const BoxConstraints(minHeight: 46),
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      alignment: Alignment.centerLeft,
                      child: Text(
                        l10n.profileSignOut,
                        style: const TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                          color: QfColors.magenta,
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          Text(
            l10n.disclaimerProbability,
            style: const TextStyle(fontSize: 11, color: QfColors.muted),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}
