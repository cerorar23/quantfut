import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../product/live_api.dart';
import '../product/live_detail.dart';
import '../product/live_widgets.dart';
import 'firebase_access.dart';
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
    appBar: AppBar(title: const Text('Privacidad y preferencias')),
    body: ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (busy) const LinearProgressIndicator(),
        if (error != null) liveText(error!, color: liveGold),
        DropdownButtonFormField<String>(
          initialValue: services.language,
          decoration: const InputDecoration(labelText: 'Idioma / Language'),
          items: languageNames.entries
              .map(
                (entry) => DropdownMenuItem(
                  value: entry.key,
                  child: Text(entry.value),
                ),
              )
              .toList(),
          onChanged: busy
              ? null
              : (value) {
                  if (value != null) change(() => services.setLanguage(value));
                },
        ),
        const SizedBox(height: 12),
        liveText(
          'El idioma se aplica al acceso y se guarda como preferencia. La traducción de todas las pantallas sigue en preparación.',
          size: 12,
          color: liveMuted,
        ),
        SwitchListTile(
          title: const Text('Medición de uso'),
          subtitle: const Text(
            'Ayuda a mejorar la app con datos sobre las pantallas utilizadas. Es opcional.',
          ),
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
          title: const Text('Informes de errores y rendimiento'),
          subtitle: const Text(
            'Envía información técnica a Firebase para diagnosticar fallos. Es opcional.',
          ),
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
          title: const Text('Notificaciones de QuantFut'),
          subtitle: Text(
            widget.api.firebaseConnected
                ? 'Puedes retirarlas cuando quieras. Los avisos pueden aparecer en la pantalla bloqueada.'
                : 'Disponible cuando se complete el acceso con Google.',
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
          liveText(services.notificationStatus!, size: 12, color: liveMuted),
        if (widget.api.firebaseConnected)
          ListTile(
            title: const Text('Bandeja de avisos'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute<void>(
                builder: (_) => FirebaseInbox(api: widget.api),
              ),
            ),
          ),
        const SizedBox(height: 16),
        ListTile(
          title: const Text('Privacidad y tus derechos'),
          trailing: const Icon(Icons.open_in_new),
          onTap: () => launchUrl(
            Uri.parse('https://pronosticosdeportivos.pro/legal/privacidad'),
            mode: LaunchMode.externalApplication,
          ),
        ),
        ListTile(
          title: const Text('Solicitar eliminación de mi cuenta'),
          subtitle: const Text(
            'Consulta los pasos y el contacto de Saptain LTD.',
          ),
          trailing: const Icon(Icons.open_in_new),
          onTap: () => launchUrl(
            Uri.parse(
              'https://pronosticosdeportivos.pro/legal/eliminar-cuenta',
            ),
            mode: LaunchMode.externalApplication,
          ),
        ),
        liveText(
          'Puedes usar las funciones básicas sin activar medición o diagnóstico. Cambiar estas opciones no borra automáticamente los datos ya enviados.',
          size: 12,
          color: liveMuted,
        ),
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
              appBar: AppBar(title: const Text('Partido')),
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
    appBar: AppBar(title: const Text('Avisos')),
    body: error != null
        ? Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(error!),
                TextButton(onPressed: load, child: const Text('Reintentar')),
              ],
            ),
          )
        : rows == null
        ? const Center(child: CircularProgressIndicator())
        : rows!.isEmpty
        ? const Center(child: Text('Todavía no tienes avisos.'))
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
