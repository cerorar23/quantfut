import 'dart:math' as math;

import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../l10n/app_locale.dart';
import '../l10n/language_picker.dart';
import '../product/live_widgets.dart';
import '../product/qf_shapes.dart';
import '../product/qf_theme.dart';
import 'access_illustrations.dart';

const _slides = 5;

/// Pantalla de acceso: presentación en carrusel (arriba) y tarjeta con el botón de Google, el
/// consentimiento y los avisos (abajo, a la altura del pulgar). No conoce Firebase: la puerta de
/// acceso le pasa el estado y las acciones.
class AccessScreen extends StatefulWidget {
  const AccessScreen({
    super.key,
    required this.busy,
    required this.consent,
    required this.docsReady,
    required this.onConsent,
    required this.onGoogle,
    required this.onTerms,
    required this.onPrivacy,
    this.error,
    this.linkingForm,
    this.actions = const [],
  });

  final bool busy, consent, docsReady;
  final ValueChanged<bool> onConsent;
  final VoidCallback onGoogle, onTerms, onPrivacy;
  final String? error;

  /// Formulario para vincular una cuenta anterior; sustituye al carrusel y al botón de Google.
  final Widget? linkingForm;

  /// Acciones secundarias bajo el botón (reintentar, usar otra cuenta).
  final List<Widget> actions;

  @override
  State<AccessScreen> createState() => _AccessScreenState();
}

class _AccessScreenState extends State<AccessScreen>
    with TickerProviderStateMixin {
  final _pages = PageController();
  late final AnimationController _loop = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 6),
  );
  late final AnimationController _shake = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 420),
  );
  final _termsTap = TapGestureRecognizer();
  final _privacyTap = TapGestureRecognizer();
  int _page = 0;
  bool _hint = false;
  bool _started = false;

  @override
  void initState() {
    super.initState();
    _termsTap.onTap = () => widget.onTerms();
    _privacyTap.onTap = () => widget.onPrivacy();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_started) return;
    _started = true;
    if (MediaQuery.of(context).disableAnimations) {
      _loop.value = .8;
    } else {
      _loop.repeat();
    }
  }

  @override
  void dispose() {
    _pages.dispose();
    _loop.dispose();
    _shake.dispose();
    _termsTap.dispose();
    _privacyTap.dispose();
    super.dispose();
  }

  /// Sin la casilla no se inicia sesión: el botón sigue activo y el error aparece junto a
  /// la casilla (nunca un botón apagado sin explicación).
  void _google() {
    if (!widget.consent) {
      HapticFeedback.lightImpact();
      setState(() => _hint = true);
      if (!MediaQuery.of(context).disableAnimations) _shake.forward(from: 0);
      return;
    }
    widget.onGoogle();
  }

  void _toggle(bool value) {
    widget.onConsent(value);
    if (value && _hint) setState(() => _hint = false);
  }

  @override
  Widget build(BuildContext context) {
    final linking = widget.linkingForm != null;
    return Scaffold(
      backgroundColor: QfColors.bg,
      resizeToAvoidBottomInset: true,
      body: ColoredBox(
        color: QfColors.bg,
        child: SafeArea(
          child: LayoutBuilder(
            builder: (context, box) => SingleChildScrollView(
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 480),
                  child: SizedBox(
                    // Por debajo de este alto el carrusel no cabe: la pantalla se desplaza.
                    height: math.max(box.maxHeight, linking ? 0 : 700),
                    child: Column(
                      children: [
                        _topBar(context),
                        if (!linking) Expanded(child: _carousel(context)),
                        if (linking) const SizedBox(height: 12),
                        _card(context, linking),
                        _disclaimer(context),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _topBar(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(20, 8, 12, 0),
    child: Row(
      children: [
        const Expanded(
          child: Text.rich(
            TextSpan(
              children: [
                TextSpan(text: '// ', style: TextStyle(color: QfColors.primary)), // l10n-ignore (marca)
                TextSpan(text: 'QUANTFUT'), // l10n-ignore (marca)
              ],
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontFamily: qfDisplay,
              fontWeight: FontWeight.w700,
              fontSize: 20,
              letterSpacing: 1.2,
              color: QfColors.text,
            ),
          ),
        ),
        const SizedBox(width: 8),
        OutlinedButton.icon(
          key: const ValueKey('language-button'),
          style: OutlinedButton.styleFrom(
            foregroundColor: QfColors.text,
            side: const BorderSide(color: QfColors.border),
            shape: const CutCornerBorder(cut: 8),
            minimumSize: const Size(48, 44),
          ),
          onPressed: widget.busy ? null : () => showLanguagePicker(context),
          icon: const Icon(Icons.language_rounded, size: 18),
          label: Text(appLanguages[AppLocale.instance.code]!),
        ),
      ],
    ),
  );

  Widget _carousel(BuildContext context) {
    final l10n = context.l10n;
    final kickers = [
      l10n.accessKicker1,
      l10n.accessKicker2,
      l10n.accessKicker3,
      l10n.accessKicker4,
      l10n.accessKicker5,
    ];
    final titles = [
      l10n.accessTitle1,
      l10n.accessTitle2,
      l10n.accessTitle3,
      l10n.accessTitle4,
      l10n.accessTitle5,
    ];
    final bodies = [
      l10n.accessBody1,
      l10n.accessBody2,
      l10n.accessBody3,
      l10n.accessBody4,
      l10n.accessBody5,
    ];
    return Column(
      children: [
        Expanded(
          child: PageView.builder(
            key: const ValueKey('access-carousel'),
            controller: _pages,
            itemCount: _slides,
            onPageChanged: (i) => setState(() => _page = i),
            itemBuilder: (context, i) => Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: ExcludeSemantics(
                      child: AccessIllustration(
                        index: i,
                        t: i == _page
                            ? _loop
                            : const AlwaysStoppedAnimation(.8),
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    kickers[i],
                    style: const TextStyle(
                      fontFamily: qfDisplay,
                      fontWeight: FontWeight.w700,
                      fontSize: 13,
                      letterSpacing: .9,
                      color: QfColors.primary,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    titles[i],
                    key: ValueKey('access-title-$i'),
                    style: const TextStyle(
                      color: QfColors.text,
                      fontFamily: qfDisplay,
                      fontWeight: FontWeight.w700,
                      fontSize: 26,
                      height: 1.1,
                    ),
                  ),
                  const SizedBox(height: 6),
                  liveText(bodies[i], size: 14, color: QfColors.text2),
                ],
              ),
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 2),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              for (var i = 0; i < _slides; i++)
                Semantics(
                  button: true,
                  selected: i == _page,
                  label: context.l10n.welcomeGoTo(i + 1),
                  child: GestureDetector(
                    key: ValueKey('access-dot-$i'),
                    behavior: HitTestBehavior.opaque,
                    onTap: () => MediaQuery.of(context).disableAnimations
                        ? _pages.jumpToPage(i)
                        : _pages.animateToPage(
                            i,
                            duration: const Duration(milliseconds: 300),
                            curve: Curves.easeOut,
                          ),
                    child: SizedBox(
                      width: 44,
                      height: 44,
                      child: Center(
                        child: AnimatedContainer(
                          duration: MediaQuery.of(context).disableAnimations
                              ? Duration.zero
                              : const Duration(milliseconds: 250),
                          width: i == _page ? 24 : 6,
                          height: 6,
                          color: i == _page ? QfColors.primary : QfColors.border,
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _card(BuildContext context, bool linking) {
    final l10n = context.l10n;
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 12),
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 14),
      decoration: const ShapeDecoration(
        color: QfColors.surface,
        shape: CutCornerBorder(side: BorderSide(color: QfColors.border)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (!linking) ...[
            Text(
              l10n.accessCardTitle,
              style: const TextStyle(
                fontFamily: qfDisplay,
                fontWeight: FontWeight.w700,
                fontSize: 20,
                color: QfColors.text,
              ),
            ),
            const SizedBox(height: 4),
            liveText(l10n.accessCardBody, size: 13, color: QfColors.text2),
            const SizedBox(height: 14),
            _googleButton(context),
          ] else
            widget.linkingForm!,
          const SizedBox(height: 10),
          _consent(context),
          if (!widget.docsReady)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: liveText(l10n.accessPreparingDocs, size: 12, color: QfColors.text2),
            ),
          if (widget.error != null)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.error_outline, size: 16, color: QfColors.danger),
                  const SizedBox(width: 6),
                  Expanded(child: liveText(widget.error!, size: 13, color: QfColors.danger)),
                ],
              ),
            ),
          ...widget.actions,
        ],
      ),
    );
  }

  Widget _googleButton(BuildContext context) {
    final l10n = context.l10n;
    return SizedBox(
      height: 52,
      child: OutlinedButton(
        key: const ValueKey('google-button'),
        style: OutlinedButton.styleFrom(
          backgroundColor: QfColors.text,
          foregroundColor: QfColors.bg,
          disabledBackgroundColor: QfColors.text2,
          side: BorderSide.none,
          shape: const CutCornerBorder(cut: 8),
          padding: const EdgeInsets.symmetric(horizontal: 16),
        ),
        onPressed: widget.busy || !widget.docsReady ? null : _google,
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (widget.busy)
              const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(strokeWidth: 2.4, color: QfColors.primary),
              )
            else
              const GoogleLogo(size: 22),
            const SizedBox(width: 12),
            Flexible(
              child: Text(
                widget.busy ? l10n.commonConnecting : l10n.accessContinueWithGoogle,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontFamily: 'Gilroy Bold',
                  fontSize: 15,
                  color: QfColors.bg,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _consent(BuildContext context) {
    final l10n = context.l10n;
    const termsMark = '\u0001', privacyMark = '\u0002';
    final template = l10n.accessConsentRich(termsMark, privacyMark);
    final spans = <InlineSpan>[];
    const link = TextStyle(
      color: QfColors.primary,
      decoration: TextDecoration.underline,
      decorationColor: QfColors.primary,
      fontFamily: 'Gilroy Bold',
    );
    for (final part in template.split(RegExp('(?=[$termsMark$privacyMark])|(?<=[$termsMark$privacyMark])'))) {
      if (part == termsMark) {
        spans.add(TextSpan(text: l10n.accessTerms, style: link, recognizer: widget.docsReady ? _termsTap : null));
      } else if (part == privacyMark) {
        spans.add(TextSpan(text: l10n.accessPrivacy, style: link, recognizer: widget.docsReady ? _privacyTap : null));
      } else {
        spans.add(TextSpan(text: part));
      }
    }
    return AnimatedBuilder(
      animation: _shake,
      builder: (context, child) => Transform.translate(
        offset: Offset(math.sin(_shake.value * math.pi * 6) * 8 * (1 - _shake.value), 0),
        child: child,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          InkWell(
            onTap: widget.busy || !widget.docsReady ? null : () => _toggle(!widget.consent),
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 4),
              decoration: _hint
                  ? const ShapeDecoration(
                      shape: CutCornerBorder(cut: 8, side: BorderSide(color: QfColors.danger)),
                    )
                  : null,
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Checkbox(
                    key: const ValueKey('consent'),
                    value: widget.consent,
                    activeColor: QfColors.primary,
                    checkColor: QfColors.onPrimary,
                    side: BorderSide(color: _hint ? QfColors.danger : QfColors.text2, width: 1.6),
                    onChanged: widget.busy || !widget.docsReady ? null : (v) => _toggle(v ?? false),
                  ),
                  Expanded(
                    child: Text.rich(
                      TextSpan(
                        style: const TextStyle(color: QfColors.text2, fontSize: 12, height: 1.3),
                        children: spans,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          if (_hint)
            Semantics(
              liveRegion: true,
              child: Padding(
                key: const ValueKey('consent-error'),
                padding: const EdgeInsets.only(left: 12, top: 4),
                child: Row(
                  children: [
                    const Icon(Icons.error_outline, size: 16, color: QfColors.danger),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        l10n.accessConsentRequired,
                        style: const TextStyle(fontSize: 12, color: QfColors.danger),
                      ),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _disclaimer(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(28, 10, 28, 12),
    child: Text(
      context.l10n.accessDisclaimer,
      textAlign: TextAlign.center,
      style: const TextStyle(color: QfColors.muted, fontSize: 11, height: 1.3),
    ),
  );
}
