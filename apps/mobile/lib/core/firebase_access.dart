import 'dart:async';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:url_launcher/url_launcher.dart';

import '../l10n/app_locale.dart';
import '../l10n/language_picker.dart';
import '../onbonding_screen/second_screen.dart';
import '../onbonding_screen/splesh_screen.dart';
import '../product/live_api.dart';
import '../product/live_shell.dart';
import '../product/live_widgets.dart';
import 'firebase_services.dart';

Uri? legalUrl(String value) {
  final uri = Uri.tryParse(value);
  if (uri == null ||
      uri.scheme != 'https' ||
      uri.host != 'pronosticosdeportivos.pro' ||
      uri.userInfo.isNotEmpty ||
      !const ['/legal/terminos', '/legal/privacidad'].contains(uri.path)) {
    return null;
  }
  return uri;
}

class FirebaseAccountGate extends StatefulWidget {
  const FirebaseAccountGate({super.key});
  @override
  State<FirebaseAccountGate> createState() => _FirebaseAccountGateState();
}

class _FirebaseAccountGateState extends State<FirebaseAccountGate> {
  final services = FirebaseServices.current!;
  final api = QuantFutApi();
  final email = TextEditingController(), password = TextEditingController();
  StreamSubscription<User?>? subscription;
  bool busy = false, ready = false, onboardingDone = false;
  bool consent = false, linking = false, wasEnabled = false;
  String? error;
  int generation = 0;
  bool get enabled => services.remoteConfig.getBool('qf_google_auth_enabled');
  Uri? get terms => legalUrl(services.remoteConfig.getString('qf_terms_url'));
  Uri? get privacy =>
      legalUrl(services.remoteConfig.getString('qf_privacy_url'));

  @override
  void initState() {
    super.initState();
    wasEnabled = enabled;
    services.addListener(configurationChanged);
    subscription = services.auth.authStateChanges().listen((user) {
      if (!enabled) return;
      if (user == null) {
        generation++;
        if (mounted) {
          Navigator.of(context).popUntil((route) => route.isFirst);
          setState(() {
            ready = false;
            linking = false;
            busy = false;
            error = null;
            consent = false;
          });
        }
      } else if (!ready && !busy) {
        unawaited(resolve());
      }
    });
  }

  void configurationChanged() {
    if (!mounted) return;
    final newlyEnabled = enabled && !wasEnabled;
    wasEnabled = enabled;
    setState(() {});
    if (newlyEnabled && services.auth.currentUser != null) unawaited(resolve());
  }

  Future<void> resolve() async {
    if (busy || services.auth.currentUser == null) return;
    final attempt = ++generation;
    setState(() {
      busy = true;
      error = null;
    });
    try {
      await api.connectFirebase(acceptedTerms: consent);
      final completed =
          await services.preferences.getBool('onboarding_done') ?? false;
      if (!mounted || attempt != generation) return;
      setState(() {
        ready = true;
        linking = false;
        onboardingDone = completed;
      });
      unawaited(services.event('login'));
    } on ApiFailure catch (failure) {
      if (mounted && attempt == generation) {
        setState(() {
          error = failure.message;
          linking = failure.code == 'vinculacion_requerida';
        });
      }
    } catch (_) {
      if (mounted && attempt == generation) {
        setState(() => error = context.l10n.accessGenericError);
      }
    } finally {
      if (mounted && attempt == generation) setState(() => busy = false);
    }
  }

  Future<void> google() async {
    if (!consent || terms == null || privacy == null || busy) return;
    setState(() {
      busy = true;
      error = null;
    });
    try {
      final user = await GoogleSignIn.instance.authenticate();
      final token = user.authentication.idToken;
      if (token == null) {
        throw const ApiFailure.kind(ApiError.googleNotVerified);
      }
      await services.auth.signInWithCredential(
        GoogleAuthProvider.credential(idToken: token),
      );
    } on GoogleSignInException catch (failure) {
      if (failure.code != GoogleSignInExceptionCode.canceled && mounted) {
        setState(() => error = context.l10n.accessGoogleError);
      }
    } catch (_) {
      if (mounted) {
        setState(() => error = context.l10n.accessGoogleError);
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
    if (mounted && services.auth.currentUser != null) await resolve();
  }

  Future<void> link() async {
    if (busy || !consent || terms == null || privacy == null) return;
    setState(() {
      busy = true;
      error = null;
    });
    try {
      await api.login(email.text, password.text);
      password.clear();
      await api.connectFirebase(acceptedTerms: true);
      onboardingDone =
          await services.preferences.getBool('onboarding_done') ?? false;
      if (mounted) {
        setState(() {
          ready = true;
          linking = false;
        });
      }
    } catch (failure) {
      password.clear();
      if (mounted) setState(() => error = '$failure');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> openLegal(Uri? uri) async {
    if (uri == null) return;
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication) &&
        mounted) {
      liveNotice(context, context.l10n.accessDocumentOpenError);
    }
  }

  @override
  void dispose() {
    generation++;
    subscription?.cancel();
    services.removeListener(configurationChanged);
    if (QuantFutApi.firebaseSession == api) QuantFutApi.firebaseSession = null;
    api.dispose();
    email.dispose();
    password.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // Activation follows publication of real legal documents and the backend.
    if (!enabled) return Splesh_Screen();
    if (ready) {
      if (!onboardingDone) {
        return SecondScreen(
          onFinished: () async {
            await services.preferences.setBool('onboarding_done', true);
            if (mounted) setState(() => onboardingDone = true);
          },
        );
      }
      return ProductShell(api: api);
    }
    final l10n = context.l10n;
    return Scaffold(
      backgroundColor: liveBg,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 480),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Align(
                    alignment: Alignment.centerRight,
                    child: TextButton.icon(
                      key: const ValueKey('language-button'),
                      onPressed: busy
                          ? null
                          : () => showLanguagePicker(context),
                      icon: const Icon(Icons.language_rounded),
                      label: Text(appLanguages[AppLocale.instance.code]!),
                    ),
                  ),
                  const Icon(Icons.insights, size: 64, color: liveCyan),
                  const SizedBox(height: 16),
                  liveText('QuantFut', size: 32, bold: true),
                  const SizedBox(height: 12),
                  liveText(l10n.accessTagline, color: liveMuted),
                  const SizedBox(height: 8),
                  const SizedBox(height: 16),
                  TextButton(
                    onPressed: terms == null ? null : () => openLegal(terms),
                    child: Text(l10n.accessTerms),
                  ),
                  TextButton(
                    onPressed: privacy == null
                        ? null
                        : () => openLegal(privacy),
                    child: Text(l10n.accessPrivacy),
                  ),
                  CheckboxListTile(
                    contentPadding: EdgeInsets.zero,
                    value: consent,
                    onChanged: busy || terms == null || privacy == null
                        ? null
                        : (value) => setState(() => consent = value ?? false),
                    title: Text(l10n.accessConsent),
                  ),
                  if (terms == null || privacy == null)
                    liveText(l10n.accessPreparingDocs, color: liveMuted),
                  if (error != null)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      child: liveText(error!, color: liveGold),
                    ),
                  if (linking) ...[
                    liveText(l10n.accessLinkIntro, color: liveMuted),
                    TextField(
                      controller: email,
                      keyboardType: TextInputType.emailAddress,
                      decoration: InputDecoration(
                        labelText: l10n.accessLinkEmail,
                      ),
                    ),
                    TextField(
                      controller: password,
                      obscureText: true,
                      decoration: InputDecoration(
                        labelText: l10n.accessLinkPassword,
                      ),
                    ),
                    const SizedBox(height: 16),
                    liveButton(
                      busy ? l10n.commonConnecting : l10n.accessLinkButton,
                      busy ? null : link,
                    ),
                    TextButton(
                      onPressed: busy
                          ? null
                          : () async {
                              try {
                                await api.forgotPassword(email.text);
                                if (context.mounted) {
                                  liveNotice(context, l10n.accessForgotSent);
                                }
                              } catch (failure) {
                                if (context.mounted) {
                                  liveNotice(context, '$failure');
                                }
                              }
                            },
                      child: Text(l10n.accessForgotLink),
                    ),
                  ] else
                    liveButton(
                      busy
                          ? l10n.commonConnecting
                          : l10n.accessContinueWithGoogle,
                      busy || !consent || terms == null || privacy == null
                          ? null
                          : google,
                      color: liveCyan,
                    ),
                  if (services.auth.currentUser != null) ...[
                    TextButton(
                      onPressed: busy ? null : resolve,
                      child: Text(l10n.accessRetry),
                    ),
                    TextButton(
                      onPressed: busy
                          ? null
                          : () async {
                              await api.logout();
                            },
                      child: Text(l10n.accessOtherAccount),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
