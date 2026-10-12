import 'package:flutter/material.dart';

import 'match_visuals.dart';

class ProfileSettingsScreen extends StatelessWidget {
  const ProfileSettingsScreen({
    super.key,
    required this.onVip,
    required this.oddsFormat,
    required this.onOddsFormatChanged,
  });
  final VoidCallback onVip;
  final String oddsFormat;
  final ValueChanged<String> onOddsFormatChanged;

  void _notice(BuildContext context, String title, String message) =>
      showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: Text(title),
          content: Text(message),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Entendido'),
            ),
          ],
        ),
      );

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.fromLTRB(12, 4, 12, 24),
    children: [
      Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          gradient: const LinearGradient(
            colors: [Color(0xff126c4c), Color(0xff0b3e35)],
          ),
        ),
        child: const Row(
          children: [
            Icon(Icons.tune_rounded, color: Colors.white, size: 36),
            SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Configuración de QuantFut',
                    style: TextStyle(
                      fontFamily: 'Gilroy ExtraBold',
                      fontSize: 20,
                    ),
                  ),
                  SizedBox(height: 6),
                  Text(
                    'Personaliza tu experiencia',
                    style: TextStyle(color: Color(0xffb3e3d2), fontSize: 12),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
      const SizedBox(height: 14),
      _card(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Row(
              children: [
                Icon(
                  Icons.account_circle_outlined,
                  color: matchGreen,
                  size: 32,
                ),
                SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Tu cuenta',
                        style: TextStyle(
                          fontFamily: 'Gilroy Bold',
                          fontSize: 16,
                        ),
                      ),
                      SizedBox(height: 4),
                      Text(
                        'Inicia sesión para consultar tu plan',
                        style: TextStyle(color: matchMuted, fontSize: 12),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                OutlinedButton(
                  onPressed: () => _notice(
                    context,
                    'Inicio de sesión',
                    'Conectaremos tu cuenta de la web mediante Firebase. El inicio de sesión aún no está activo.',
                  ),
                  child: const Text('Iniciar sesión'),
                ),
                FilledButton(
                  onPressed: onVip,
                  style: FilledButton.styleFrom(
                    backgroundColor: matchGold,
                    foregroundColor: Colors.black,
                  ),
                  child: const Text(
                    'Hazte VIP',
                    style: TextStyle(fontFamily: 'Gilroy ExtraBold'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
      _heading('Preferencias'),
      _setting(
        context,
        icon: Icons.notifications_outlined,
        color: const Color(0xffffb648),
        title: 'Notificaciones',
        subtitle: 'Avisos de picks · Firebase pendiente',
        trailing: Switch(
          key: const ValueKey('profile-notifications'),
          value: false,
          onChanged: (_) => _notice(
            context,
            'Notificaciones por conectar',
            'Activaremos el permiso del dispositivo y tus preferencias cuando Firebase y el envío de avisos estén configurados.',
          ),
        ),
      ),
      _setting(
        context,
        icon: Icons.inbox_outlined,
        color: matchCyan,
        title: 'Bandeja de avisos',
        subtitle: 'Consulta tus notificaciones',
        onTap: () => openNotificationInbox(context),
      ),
      _setting(
        context,
        icon: Icons.account_balance_wallet_outlined,
        color: matchGreen,
        title: 'Balance y seguimiento',
        subtitle: 'Registro de resultados · Por conectar',
        trailing: Switch(
          key: const ValueKey('profile-balance'),
          value: false,
          onChanged: (_) => _notice(
            context,
            'Seguimiento pendiente',
            'Definiremos el registro de tus selecciones y su liquidación antes de activar el balance en Inicio. No se está registrando un saldo.',
          ),
        ),
      ),
      _setting(
        context,
        icon: Icons.privacy_tip_outlined,
        color: const Color(0xffb58aff),
        title: 'Análisis e informes de errores',
        subtitle: 'Preferencias de medición · Por conectar',
        trailing: Switch(
          key: const ValueKey('profile-diagnostics'),
          value: false,
          onChanged: (_) => _notice(
            context,
            'Medición por configurar',
            'Configuraremos Analytics y Crashlytics con preferencias separadas y una explicación de los datos que se recogen. El prototipo no envía telemetría.',
          ),
        ),
      ),
      _setting(
        context,
        key: const ValueKey('profile-language'),
        icon: Icons.language_rounded,
        color: matchCyan,
        title: 'Idioma',
        subtitle: 'Español · Traducciones pendientes',
        onTap: () => _languages(context),
      ),
      _setting(
        context,
        key: const ValueKey('profile-odds'),
        icon: Icons.percent_rounded,
        color: matchGreen,
        title: 'Formato de cuotas',
        subtitle: '$oddsFormat · Vista previa: ${_example(oddsFormat)}',
        onTap: () => _odds(context),
      ),
      _heading('General'),
      _setting(
        context,
        icon: Icons.share_outlined,
        color: matchCyan,
        title: 'Compartir app',
        subtitle: 'Enlace de la tienda por configurar',
        onTap: () => _notice(
          context,
          'Compartir QuantFut',
          'Añadiremos el enlace público de la tienda cuando la app esté publicada.',
        ),
      ),
      _setting(
        context,
        icon: Icons.workspace_premium_outlined,
        color: matchGold,
        title: 'Acceso VIP',
        subtitle: 'Revisa los planes y sus beneficios',
        onTap: onVip,
      ),
      _setting(
        context,
        key: const ValueKey('profile-restore'),
        icon: Icons.restore_rounded,
        color: matchGreen,
        title: 'Restaurar compras',
        subtitle: 'Proveedor de compras pendiente',
        onTap: () => _notice(
          context,
          'Restauración por conectar',
          'La restauración consultará las compras del proveedor y verificará tu acceso con el servidor. Todavía no está configurada.',
        ),
      ),
      _setting(
        context,
        icon: Icons.help_outline_rounded,
        color: matchCyan,
        title: 'Ayuda y soporte',
        subtitle: 'Canal de atención por configurar',
        onTap: () => _notice(
          context,
          'Ayuda y soporte',
          'Definiremos el canal de soporte y los datos de contacto del proyecto.',
        ),
      ),
      _setting(
        context,
        icon: Icons.policy_outlined,
        color: const Color(0xffb58aff),
        title: 'Privacidad',
        subtitle: 'Política de la app por publicar',
        onTap: () => _notice(
          context,
          'Privacidad',
          'La política final incluirá cuenta, compras, notificaciones y preferencias de medición. Se publicará al configurar estos servicios.',
        ),
      ),
      _setting(
        context,
        icon: Icons.code_rounded,
        color: matchMuted,
        title: 'Versión de desarrollo',
        subtitle: '1.0.0+1 · QuantFut',
        onTap: null,
      ),
      const SizedBox(height: 16),
      const Text(
        'QuantFut · Probabilidad y estadística\nLas probabilidades no aseguran el resultado.',
        textAlign: TextAlign.center,
        style: TextStyle(color: matchMuted, height: 1.6, fontSize: 11),
      ),
    ],
  );

  Widget _heading(String title) => Padding(
    padding: const EdgeInsets.fromLTRB(4, 22, 4, 10),
    child: Text(
      title,
      style: const TextStyle(
        color: matchMuted,
        fontFamily: 'Gilroy Bold',
        fontSize: 13,
      ),
    ),
  );

  Widget _card({required Widget child}) => Material(
    color: matchSurface,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(14),
      side: const BorderSide(color: Color(0xff263d42)),
    ),
    clipBehavior: Clip.antiAlias,
    child: Padding(padding: const EdgeInsets.all(14), child: child),
  );

  Widget _setting(
    BuildContext context, {
    Key? key,
    required IconData icon,
    required Color color,
    required String title,
    required String subtitle,
    Widget? trailing,
    VoidCallback? onTap,
  }) => Padding(
    padding: const EdgeInsets.only(bottom: 10),
    child: Material(
      key: key,
      color: matchSurface,
      borderRadius: BorderRadius.circular(14),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(13),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: color.withValues(alpha: .12),
                  shape: BoxShape.circle,
                ),
                child: Icon(icon, color: color, size: 22),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: const TextStyle(
                        fontFamily: 'Gilroy Bold',
                        fontSize: 14,
                      ),
                    ),
                    const SizedBox(height: 5),
                    Text(
                      subtitle,
                      style: const TextStyle(
                        color: matchMuted,
                        fontSize: 11,
                        height: 1.4,
                      ),
                    ),
                  ],
                ),
              ),
              if (trailing != null)
                trailing
              else if (onTap != null)
                const Icon(Icons.chevron_right_rounded, color: matchMuted),
            ],
          ),
        ),
      ),
    ),
  );

  String _example(String format) => switch (format) {
    'Americana' => '-105',
    'Fraccionaria' => '19/20',
    _ => '1,95',
  };

  void _odds(BuildContext context) => showDialog<void>(
    context: context,
    builder: (dialogContext) => SimpleDialog(
      title: const Text('Formato de cuotas'),
      children: [
        const Padding(
          padding: EdgeInsets.symmetric(horizontal: 24, vertical: 8),
          child: Text(
            'Preferencia de vista previa para esta sesión. Se aplicará a las cuotas cuando estén conectadas.',
            style: TextStyle(color: matchMuted, fontSize: 12),
          ),
        ),
        for (final format in ['Decimal', 'Americana', 'Fraccionaria'])
          SimpleDialogOption(
            onPressed: () {
              onOddsFormatChanged(format);
              Navigator.pop(dialogContext);
            },
            child: Row(
              children: [
                Icon(
                  oddsFormat == format
                      ? Icons.radio_button_checked
                      : Icons.radio_button_off,
                  color: matchGreen,
                ),
                const SizedBox(width: 12),
                Expanded(child: Text('$format · ${_example(format)}')),
              ],
            ),
          ),
      ],
    ),
  );

  void _languages(BuildContext context) => showDialog<void>(
    context: context,
    builder: (dialogContext) => AlertDialog(
      title: const Text('Idioma de la app'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'La interfaz actual está en español. El selector inicial y estas traducciones están anotados para la fase de idiomas.',
              style: TextStyle(color: matchMuted, fontSize: 12),
            ),
            const SizedBox(height: 12),
            for (final language in [
              'Español',
              'English',
              'Português',
              'Français',
              'Italiano',
              'Deutsch',
            ])
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 7),
                child: Row(
                  children: [
                    Icon(
                      language == 'Español'
                          ? Icons.check_circle
                          : Icons.schedule_rounded,
                      color: language == 'Español' ? matchGreen : matchMuted,
                      size: 20,
                    ),
                    const SizedBox(width: 10),
                    Expanded(child: Text(language)),
                  ],
                ),
              ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(dialogContext),
          child: const Text('Entendido'),
        ),
      ],
    ),
  );
}

void openNotificationInbox(BuildContext context) => Navigator.of(context).push(
  MaterialPageRoute<void>(builder: (_) => const NotificationInboxScreen()),
);

class NotificationInboxScreen extends StatelessWidget {
  const NotificationInboxScreen({super.key});
  @override
  Widget build(BuildContext context) => Theme(
    data: ThemeData(
      brightness: Brightness.dark,
      fontFamily: 'Gilroy Medium',
      colorScheme: const ColorScheme.dark(
        primary: matchCyan,
        surface: matchSurface,
      ),
    ),
    child: Scaffold(
      backgroundColor: const Color(0xff090f1a),
      appBar: AppBar(
        title: const Text('Bandeja de avisos'),
        backgroundColor: const Color(0xff090f1a),
      ),
      body: const SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: EdgeInsets.all(28),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.inbox_outlined, color: matchCyan, size: 62),
                SizedBox(height: 18),
                Text(
                  'Tu bandeja, en un solo lugar',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontFamily: 'Gilroy ExtraBold',
                    fontSize: 22,
                  ),
                ),
                SizedBox(height: 12),
                Text(
                  'Aquí aparecerán tus avisos guardados. La conexión con Firebase y el backend todavía está pendiente.',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: matchMuted, height: 1.6),
                ),
              ],
            ),
          ),
        ),
      ),
    ),
  );
}
