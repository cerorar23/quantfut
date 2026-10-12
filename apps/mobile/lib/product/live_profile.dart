import 'package:flutter/material.dart';

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
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        liveHeading('Perfil y configuración'),
        liveCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              liveText(
                api.signedIn
                    ? '${account['display_name'] ?? account['email']}'
                    : 'Tu cuenta QuantFut',
                size: 18,
                bold: true,
              ),
              const SizedBox(height: 8),
              liveText(
                api.plus ? 'Acceso VIP activo' : 'Plan gratuito',
                color: api.plus ? liveGold : liveMuted,
              ),
              const SizedBox(height: 12),
              liveButton('Ver planes VIP', widget.onVip),
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
                  decoration: const InputDecoration(
                    labelText: 'Correo electrónico',
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: password,
                  obscureText: true,
                  autofillHints: const [AutofillHints.password],
                  decoration: const InputDecoration(labelText: 'Contraseña'),
                  onSubmitted: (_) => busy ? null : login(),
                ),
                const SizedBox(height: 16),
                if (error != null) liveText(error!, color: liveGold),
                liveButton(
                  busy
                      ? 'Conectando…'
                      : creating
                      ? 'Crear cuenta'
                      : 'Iniciar sesión',
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
                    creating ? 'Ya tengo cuenta' : 'Crear una cuenta',
                  ),
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
                                'Si la cuenta existe, recibirás las instrucciones por correo.',
                              );
                            }
                          } catch (e) {
                            if (context.mounted) liveNotice(context, '$e');
                          }
                        },
                  child: const Text('Olvidé mi contraseña'),
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
                      ? 'Correo verificado'
                      : 'Correo pendiente de verificación',
                  color: liveCyan,
                ),
                if (account['email_verified'] != true)
                  TextButton(
                    onPressed: () async {
                      try {
                        await api.resendVerification();
                        if (context.mounted) {
                          liveNotice(
                            context,
                            'Correo de verificación enviado.',
                          );
                        }
                      } catch (e) {
                        if (context.mounted) liveNotice(context, '$e');
                      }
                    },
                    child: const Text('Enviar correo de verificación'),
                  ),
                if (api.account?['subscription'] != null)
                  liveText(
                    'Vigencia: ${kickoffText(jsonMap(api.account?['subscription'])['ends_at'])}',
                    color: liveMuted,
                    size: 12,
                  ),
              ],
            ),
          ),
          liveButton('Actualizar mi acceso', () async {
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
            child: const Text('Cerrar sesión'),
          ),
        ],
        liveHeading('Preferencias'),
        for (final item in [
          ('notificaciones', 'Notificaciones', Icons.notifications_outlined),
          (
            'balance',
            'Balance y seguimiento',
            Icons.account_balance_wallet_outlined,
          ),
          ('medicion', 'Medición y errores', Icons.shield_outlined),
          ('idiomas', 'Idioma', Icons.language),
        ])
          liveCard(
            child: ListTile(
              contentPadding: EdgeInsets.zero,
              leading: Icon(item.$3, color: liveCyan),
              title: liveText(item.$2, bold: true),
              subtitle: liveText(
                featureMessage(widget.data, item.$1),
                size: 12,
                color: liveMuted,
              ),
              trailing: const Icon(Icons.chevron_right, color: liveMuted),
              onTap: () {
                if (FirebaseServices.current != null && item.$1 != 'balance') {
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
              liveText('Formato de cuotas', bold: true),
              const SizedBox(height: 6),
              liveText(
                'Decimal · Cuotas registradas al publicar',
                color: liveMuted,
                size: 12,
              ),
            ],
          ),
        ),
        liveHeading('General'),
        liveCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              liveText('Versión de la app', bold: true),
              const SizedBox(height: 6),
              liveText(
                'QuantFut · Conectada al servidor',
                color: liveMuted,
                size: 12,
              ),
            ],
          ),
        ),
        liveText(
          'Una probabilidad no es una certeza. Decide con información y juega responsablemente.',
          size: 12,
          color: liveMuted,
        ),
        const SizedBox(height: 24),
      ],
    );
  }
}
