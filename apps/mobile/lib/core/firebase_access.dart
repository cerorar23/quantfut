import 'dart:async';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:url_launcher/url_launcher.dart';

import '../onbonding_screen/second_screen.dart';
import '../onbonding_screen/splesh_screen.dart';
import '../product/live_api.dart';
import '../product/live_shell.dart';
import '../product/live_widgets.dart';
import 'firebase_services.dart';

const languageNames = {
  'es': 'Español',
  'en': 'English',
  'pt': 'Português',
  'fr': 'Français',
  'it': 'Italiano',
  'de': 'Deutsch',
};

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
        setState(
          () => error = 'No se pudo completar el acceso. Inténtalo de nuevo.',
        );
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
        throw const ApiFailure('Google no pudo verificar el acceso.');
      }
      await services.auth.signInWithCredential(
        GoogleAuthProvider.credential(idToken: token),
      );
    } on GoogleSignInException catch (failure) {
      if (failure.code != GoogleSignInExceptionCode.canceled && mounted) {
        setState(
          () => error = 'No se pudo acceder con Google. Inténtalo de nuevo.',
        );
      }
    } catch (_) {
      if (mounted) {
        setState(
          () => error = 'No se pudo acceder con Google. Inténtalo de nuevo.',
        );
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
      liveNotice(context, 'No se pudo abrir el documento.');
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
    final language = services.language;
    final googleLabel = {
      'es': 'Continuar con Google',
      'en': 'Continue with Google',
      'pt': 'Continuar com Google',
      'fr': 'Continuer avec Google',
      'it': 'Continua con Google',
      'de': 'Mit Google fortfahren',
    }[language]!;
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
                  const Icon(Icons.insights, size: 64, color: liveCyan),
                  const SizedBox(height: 16),
                  liveText('QuantFut', size: 32, bold: true),
                  const SizedBox(height: 12),
                  liveText(
                    'Partidos, análisis e historial. Una probabilidad no es una certeza.',
                    color: liveMuted,
                  ),
                  const SizedBox(height: 24),
                  DropdownButtonFormField<String>(
                    initialValue: language,
                    decoration: const InputDecoration(
                      labelText: 'Idioma / Language',
                    ),
                    items: languageNames.entries
                        .map(
                          (item) => DropdownMenuItem(
                            value: item.key,
                            child: Text(item.value),
                          ),
                        )
                        .toList(),
                    onChanged: busy
                        ? null
                        : (value) async {
                            if (value != null) {
                              await services.setLanguage(value);
                            }
                          },
                  ),
                  const SizedBox(height: 16),
                  TextButton(
                    onPressed: terms == null ? null : () => openLegal(terms),
                    child: const Text('Términos de uso'),
                  ),
                  TextButton(
                    onPressed: privacy == null
                        ? null
                        : () => openLegal(privacy),
                    child: const Text('Política de privacidad'),
                  ),
                  CheckboxListTile(
                    contentPadding: EdgeInsets.zero,
                    value: consent,
                    onChanged: busy || terms == null || privacy == null
                        ? null
                        : (value) => setState(() => consent = value ?? false),
                    title: const Text(
                      'Tengo al menos 18 años y acepto los términos y la política de privacidad.',
                    ),
                  ),
                  if (terms == null || privacy == null)
                    liveText(
                      'Estamos preparando los documentos de acceso.',
                      color: liveMuted,
                    ),
                  if (error != null)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      child: liveText(error!, color: liveGold),
                    ),
                  if (linking) ...[
                    liveText(
                      'Vincula tu cuenta anterior para conservar saldo y acceso.',
                      color: liveMuted,
                    ),
                    TextField(
                      controller: email,
                      keyboardType: TextInputType.emailAddress,
                      decoration: const InputDecoration(
                        labelText: 'Correo de tu cuenta anterior',
                      ),
                    ),
                    TextField(
                      controller: password,
                      obscureText: true,
                      decoration: const InputDecoration(
                        labelText: 'Contraseña anterior',
                      ),
                    ),
                    const SizedBox(height: 16),
                    liveButton(
                      busy ? 'Conectando…' : 'Vincular mi cuenta',
                      busy ? null : link,
                    ),
                    TextButton(
                      onPressed: busy
                          ? null
                          : () async {
                              try {
                                await api.forgotPassword(email.text);
                                if (context.mounted) {
                                  liveNotice(
                                    context,
                                    'Si existe la cuenta, recibirás instrucciones por correo.',
                                  );
                                }
                              } catch (failure) {
                                if (context.mounted) liveNotice(context, '$failure');
                              }
                            },
                      child: const Text('Recuperar contraseña anterior'),
                    ),
                  ] else
                    liveButton(
                      busy ? 'Conectando…' : googleLabel,
                      busy || !consent || terms == null || privacy == null
                          ? null
                          : google,
                      color: liveCyan,
                    ),
                  if (services.auth.currentUser != null) ...[
                    TextButton(
                      onPressed: busy ? null : resolve,
                      child: const Text('Reintentar acceso'),
                    ),
                    TextButton(
                      onPressed: busy
                          ? null
                          : () async {
                              await api.logout();
                            },
                      child: const Text('Usar otra cuenta'),
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
