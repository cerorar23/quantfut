import 'dart:math' as math;

import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../l10n/app_locale.dart';
import '../l10n/language_picker.dart';
import '../product/live_widgets.dart';
import 'access_illustrations.dart';

const _slides = 5;
const _googleDark = Color(0xff131314);
const _googleBorder = Color(0xff8e918f);
const _alertRed = Color(0xffe85667);

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

  void _google() {
    if (!widget.consent) {
      HapticFeedback.lightImpact();
      setState(() => _hint = true);
      _shake.forward(from: 0);
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
      backgroundColor: liveBg,
      resizeToAvoidBottomInset: true,
      body: DecoratedBox(
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment(0, -.85),
            radius: 1.1,
            colors: [Color(0x3300d58b), Color(0x00090f1a)],
          ),
        ),
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
        Container(
          width: 32,
          height: 32,
          decoration: BoxDecoration(
            color: liveGreen.withValues(alpha: .16),
            borderRadius: BorderRadius.circular(10),
          ),
          child: const Icon(Icons.insights, size: 20, color: liveGreen),
        ),
        const SizedBox(width: 10),
        liveText('QuantFut', size: 20, bold: true),
        const Spacer(),
        OutlinedButton.icon(
          key: const ValueKey('language-button'),
          style: OutlinedButton.styleFrom(
            foregroundColor: Colors.white,
            side: const BorderSide(color: Color(0xff243447)),
            shape: const StadiumBorder(),
            minimumSize: const Size(48, 40),
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
                  liveText(kickers[i], size: 12, bold: true, color: liveGreen),
                  const SizedBox(height: 6),
                  Text(
                    titles[i],
                    key: ValueKey('access-title-$i'),
                    style: const TextStyle(
                      color: Colors.white,
                      fontFamily: 'Gilroy ExtraBold',
                      fontSize: 22,
                      height: 1.15,
                    ),
                  ),
                  const SizedBox(height: 6),
                  liveText(bodies[i], size: 14, color: liveMuted),
                ],
              ),
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 6),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              for (var i = 0; i < _slides; i++)
                GestureDetector(
                  key: ValueKey('access-dot-$i'),
                  behavior: HitTestBehavior.opaque,
                  onTap: () => _pages.animateToPage(
                    i,
                    duration: const Duration(milliseconds: 300),
                    curve: Curves.easeOut,
                  ),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 4,
                      vertical: 10,
                    ),
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 250),
                      width: i == _page ? 22 : 7,
                      height: 7,
                      decoration: BoxDecoration(
                        color: i == _page ? liveGreen : const Color(0xff33465c),
                        borderRadius: BorderRadius.circular(99),
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
      decoration: BoxDecoration(
        color: livePanel,
        borderRadius: BorderRadius.circular(28),
        border: Border.all(color: const Color(0xff1f3347)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (!linking) ...[
            liveText(l10n.accessCardTitle, size: 18, bold: true),
            const SizedBox(height: 4),
            liveText(l10n.accessCardBody, size: 13, color: liveMuted),
            const SizedBox(height: 14),
            _googleButton(context),
          ] else
            widget.linkingForm!,
          const SizedBox(height: 10),
          _consent(context),
          if (!widget.docsReady)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: liveText(l10n.accessPreparingDocs, size: 12, color: liveMuted),
            ),
          if (widget.error != null)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: liveText(widget.error!, size: 13, color: liveGold),
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
          backgroundColor: _googleDark,
          foregroundColor: Colors.white,
          disabledBackgroundColor: _googleDark,
          side: const BorderSide(color: _googleBorder),
          shape: const StadiumBorder(),
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
                child: CircularProgressIndicator(strokeWidth: 2.4, color: liveGreen),
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
                  color: Colors.white,
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
    final link = TextStyle(
      color: liveGreen,
      decoration: TextDecoration.underline,
      decorationColor: liveGreen,
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
            borderRadius: BorderRadius.circular(12),
            onTap: widget.busy || !widget.docsReady ? null : () => _toggle(!widget.consent),
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 4),
              decoration: _hint
                  ? BoxDecoration(
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: _alertRed.withValues(alpha: .7)),
                    )
                  : null,
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Checkbox(
                    key: const ValueKey('consent'),
                    value: widget.consent,
                    activeColor: liveGreen,
                    checkColor: liveBg,
                    side: const BorderSide(color: liveMuted, width: 1.6),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                    onChanged: widget.busy || !widget.docsReady ? null : (v) => _toggle(v ?? false),
                  ),
                  Expanded(
                    child: Text.rich(
                      TextSpan(
                        style: const TextStyle(color: liveMuted, fontSize: 12, height: 1.3),
                        children: spans,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          if (_hint)
            Padding(
              padding: const EdgeInsets.only(left: 12, top: 4),
              child: liveText(l10n.accessConsentNeeded, size: 12, color: _alertRed),
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
      style: const TextStyle(color: liveMuted, fontSize: 11, height: 1.3),
    ),
  );
}
