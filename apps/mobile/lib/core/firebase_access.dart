import 'dart:async';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:url_launcher/url_launcher.dart';

import '../l10n/app_locale.dart';
import '../onbonding_screen/splesh_screen.dart';
import '../product/live_api.dart';
import '../product/live_shell.dart';
import '../product/live_widgets.dart';
import 'access_screen.dart';
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
  bool busy = false, ready = false;
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
      if (!mounted || attempt != generation) return;
      setState(() {
        ready = true;
        linking = false;
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
    if (ready) return ProductShell(api: api);
    final l10n = context.l10n;
    return AccessScreen(
      busy: busy,
      consent: consent,
      docsReady: terms != null && privacy != null,
      onConsent: (value) => setState(() => consent = value),
      onGoogle: google,
      onTerms: () => openLegal(terms),
      onPrivacy: () => openLegal(privacy),
      error: error,
      linkingForm: linking ? _linkingForm(l10n) : null,
      actions: [
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
    );
  }

  Widget _linkingForm(AppLocalizations l10n) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    mainAxisSize: MainAxisSize.min,
    children: [
      liveText(l10n.accessLinkIntro, color: liveMuted),
      TextField(
        controller: email,
        keyboardType: TextInputType.emailAddress,
        decoration: InputDecoration(labelText: l10n.accessLinkEmail),
      ),
      TextField(
        controller: password,
        obscureText: true,
        decoration: InputDecoration(labelText: l10n.accessLinkPassword),
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
                  if (mounted) liveNotice(context, l10n.accessForgotSent);
                } catch (failure) {
                  if (mounted) liveNotice(context, '$failure');
                }
              },
        child: Text(l10n.accessForgotLink),
      ),
    ],
  );
}
