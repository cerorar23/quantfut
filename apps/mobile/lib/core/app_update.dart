import 'dart:io';

import 'package:flutter/material.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import '../product/live_api.dart';
import '../product/qf_shapes.dart';
import '../product/qf_theme.dart';
import '../l10n/app_localizations.dart';

class AppUpdate {
  const AppUpdate(this.version, this.store, this.required);
  final String version;
  final Uri store;
  final bool required;

  static AppUpdate? evaluate(
    Map<String, dynamic> config,
    String platform,
    String build,
  ) {
    if (platform != 'android' && platform != 'ios') return null;
    final installed = int.tryParse(build);
    final version = config['app_version_$platform']?.toString() ?? '';
    final match = RegExp(r'^\d+\.\d+\.\d+\+([1-9]\d*)$').firstMatch(version);
    final latest = match == null ? null : int.tryParse(match.group(1)!);
    final minimum = int.tryParse('${config['min_build_$platform'] ?? 0}');
    final store = Uri.tryParse(
      '${config[platform == 'android' ? 'app_link' : 'ios_app_link'] ?? ''}',
    );
    final host = platform == 'android' ? 'play.google.com' : 'apps.apple.com';
    if (installed == null ||
        installed < 0 ||
        latest == null ||
        minimum == null ||
        minimum < 0 ||
        minimum > latest ||
        store == null ||
        store.scheme != 'https' ||
        store.authority != host ||
        store.path.isEmpty ||
        store.path == '/' ||
        latest <= installed) {
      return null;
    }
    final force = config['force_update_app'];
    return AppUpdate(
      version,
      store,
      force == true ||
          force == 1 ||
          force == '1' ||
          force == 'true' ||
          installed < minimum,
    );
  }
}

/// Pide la política de versiones al servidor y la compara con la instalada. La usan el
/// arranque y la fila «Versión de la app» del Perfil.
Future<AppUpdate?> checkAppUpdate() async {
  final api = QuantFutApi();
  try {
    final config = jsonMap(
      await api.request('/mobile/v1/config').timeout(const Duration(seconds: 8)),
    );
    final package = await PackageInfo.fromPlatform().timeout(
      const Duration(seconds: 2),
    );
    return AppUpdate.evaluate(config, Platform.operatingSystem, package.buildNumber);
  } finally {
    api.dispose();
  }
}

/// Remains above navigation, including login and replacement routes.
class AppUpdateGate extends StatefulWidget {
  const AppUpdateGate({
    super.key,
    required this.navigatorKey,
    required this.child,
    this.checkForUpdate,
  });
  final GlobalKey<NavigatorState> navigatorKey;
  final Widget child;
  final Future<AppUpdate?> Function()? checkForUpdate;

  @override
  State<AppUpdateGate> createState() => _AppUpdateGateState();
}

class _AppUpdateGateState extends State<AppUpdateGate>
    with WidgetsBindingObserver {
  bool _checking = false, _ready = false, _optionalShown = false;
  DialogRoute<void>? _route;
  final _update = ValueNotifier<AppUpdate?>(null);

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    WidgetsBinding.instance.addPostFrameCallback((_) => _check());
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) _check();
  }

  Future<void> _check() async {
    if (_checking || !mounted) return;
    _checking = true;
    try {
      final update = await (widget.checkForUpdate ?? checkAppUpdate)();
      if (!mounted) return;
      _update.value = update;
      final nav = widget.navigatorKey.currentState;
      if (nav == null) return;
      if (update == null) {
        final route = _route;
        _route = null;
        if (route != null) nav.removeRoute(route);
      } else if (_route == null && (update.required || !_optionalShown)) {
        _optionalShown = true;
        final route = DialogRoute<void>(
          context: nav.overlay!.context,
          barrierDismissible: false,
          builder: (_) => ValueListenableBuilder<AppUpdate?>(
            valueListenable: _update,
            builder: (context, value, _) => value == null
                ? const SizedBox.shrink()
                : AppUpdateDialog(update: value),
          ),
        );
        _route = route;
        nav.push(route).whenComplete(() {
          if (_route == route) _route = null;
        });
      }
    } catch (_) {
      // Network/config failures allow startup; an already required dialog stays.
    } finally {
      _checking = false;
      if (mounted) setState(() => _ready = true);
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _update.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Stack(
    children: [
      widget.child,
      if (!_ready)
        const Positioned.fill(
          child: ColoredBox(
            color: QfColors.bg,
            child: Center(child: CircularProgressIndicator()),
          ),
        ),
    ],
  );
}

class AppUpdateDialog extends StatefulWidget {
  const AppUpdateDialog({super.key, required this.update, this.openStore});
  final Future<bool> Function(Uri)? openStore;
  final AppUpdate update;
  @override
  State<AppUpdateDialog> createState() => _UpdateDialogState();
}

class _UpdateDialogState extends State<AppUpdateDialog> {
  bool _opening = false, _failed = false;

  Future<void> _open() async {
    if (_opening) return;
    setState(() {
      _opening = true;
      _failed = false;
    });
    try {
      final opened = widget.openStore != null
          ? await widget.openStore!(widget.update.store)
          : await launchUrl(
              widget.update.store,
              mode: LaunchMode.externalApplication,
            );
      if (mounted) setState(() => _failed = !opened);
    } catch (_) {
      if (mounted) setState(() => _failed = true);
    } finally {
      if (mounted) setState(() => _opening = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final title = widget.update.required
        ? l10n.updateRequiredTitle
        : l10n.updateTitle;

    return PopScope(
      canPop: !widget.update.required,
      child: AlertDialog(
        backgroundColor: QfColors.surface,
        elevation: 0,
        insetPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
        shape: const CutCornerBorder(
          cut: 16,
          side: BorderSide(color: QfColors.borderStrong, width: 1.2),
        ),
        titlePadding: const EdgeInsets.fromLTRB(20, 24, 20, 0),
        contentPadding: const EdgeInsets.fromLTRB(20, 14, 20, 0),
        actionsPadding: const EdgeInsets.fromLTRB(20, 16, 20, 20),
        title: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 54,
              height: 54,
              decoration: ShapeDecoration(
                color: QfColors.cyan.withValues(alpha: 0.1),
                shadows: [
                  BoxShadow(
                    color: QfColors.cyan.withValues(alpha: 0.28),
                    blurRadius: 24,
                  ),
                ],
                shape: const CutCornerBorder(
                  cut: 8,
                  side: BorderSide(color: QfColors.borderStrong),
                ),
              ),
              child: const Center(
                child: Icon(Icons.system_update, color: QfColors.cyan, size: 28),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title.toUpperCase(),
                    style: const TextStyle(
                      fontFamily: qfDisplay,
                      fontWeight: FontWeight.w700,
                      fontSize: 20,
                      height: 1.05,
                      letterSpacing: 0.6,
                      color: QfColors.text,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      border: Border.all(color: QfColors.green.withValues(alpha: 0.4)),
                      borderRadius: BorderRadius.circular(2),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          '${l10n.updateVersion.toUpperCase()} ',
                          style: const TextStyle(
                            fontFamily: qfMono,
                            fontWeight: FontWeight.w700,
                            fontSize: 11,
                            color: QfColors.green,
                          ),
                        ),
                        Text(
                          widget.update.version,
                          style: const TextStyle(
                            fontFamily: qfMono,
                            fontWeight: FontWeight.w700,
                            fontSize: 11,
                            color: QfColors.green,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              _failed
                  ? l10n.updateStoreError
                  : widget.update.required
                      ? l10n.updateRequired
                      : l10n.updateOptional,
              style: const TextStyle(
                fontFamily: 'Exo 2',
                color: QfColors.text2,
                fontSize: 14,
                height: 1.4,
              ),
            ),
          ],
        ),
        actions: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              SizedBox(
                height: 50,
                child: FilledButton(
                  key: const ValueKey('update-now'),
                  style: FilledButton.styleFrom(
                    backgroundColor: QfColors.primary,
                    foregroundColor: QfColors.onPrimary,
                    minimumSize: const Size(double.infinity, 48),
                    shape: const CutCornerBorder(cut: 10),
                    elevation: 0,
                  ),
                  onPressed: _opening ? null : _open,
                  child: Text(
                    l10n.updateNow,
                    style: const TextStyle(
                      fontFamily: qfDisplay,
                      fontWeight: FontWeight.w700,
                      fontSize: 16,
                      letterSpacing: 1.2,
                      color: QfColors.onGreen,
                    ),
                  ),
                ),
              ),
              if (!widget.update.required) ...[
                const SizedBox(height: 8),
                TextButton(
                  style: TextButton.styleFrom(
                    foregroundColor: QfColors.muted,
                    minimumSize: const Size(double.infinity, 44),
                  ),
                  onPressed: () => Navigator.of(context).pop(),
                  child: Text(
                    l10n.updateLater,
                    style: const TextStyle(
                      fontFamily: qfDisplay,
                      fontWeight: FontWeight.w700,
                      fontSize: 14,
                      letterSpacing: 1.0,
                      color: QfColors.muted,
                    ),
                  ),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }
}
