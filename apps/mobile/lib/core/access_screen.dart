import 'dart:math' as math;

import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import '../l10n/language_picker.dart';
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
  late final AnimationController _shake = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 420),
  );
  final _termsTap = TapGestureRecognizer();
  final _privacyTap = TapGestureRecognizer();
  int _page = 0;
  bool _hint = false;

  @override
  void initState() {
    super.initState();
    _termsTap.onTap = () => widget.onTerms();
    _privacyTap.onTap = () => widget.onPrivacy();
  }

  @override
  void dispose() {
    _pages.dispose();
    _shake.dispose();
    _termsTap.dispose();
    _privacyTap.dispose();
    super.dispose();
  }

  /// Sin la casilla no se inicia sesión: el botón sigue activo y el error aparece junto a
  /// la casilla (nunca un botón apagado sin explicación).
  void _google() {
    if (!widget.consent) {
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
                    height: math.max(box.maxHeight, linking ? 0 : 760),
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

  Widget _topBar(BuildContext context) => Container(
    height: 56,
    padding: const EdgeInsets.only(left: 16, right: 10),
    child: Row(
      children: [
        const Text.rich(
          TextSpan(
            text: 'QUANT',
            style: TextStyle(
              fontFamily: qfDisplay,
              fontWeight: FontWeight.w700,
              fontSize: 21,
              letterSpacing: 1.4,
              color: QfColors.text,
            ),
            children: [
              TextSpan(
                text: 'FUT',
                style: TextStyle(color: QfColors.cyan),
              ),
            ],
          ),
        ),
        const Spacer(),
        OutlinedButton(
          key: const ValueKey('language-button'),
          style: OutlinedButton.styleFrom(
            foregroundColor: QfColors.text2,
            side: const BorderSide(color: QfColors.border),
            shape: const CutCornerBorder(cut: 6),
            minimumSize: const Size(48, 44),
            padding: const EdgeInsets.symmetric(horizontal: 12),
          ),
          onPressed: widget.busy ? null : () => showLanguagePicker(context),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.language_rounded, size: 16, color: QfColors.text2),
              const SizedBox(width: 6),
              Text(
                AppLocale.instance.code.toUpperCase(),
                style: const TextStyle(
                  fontFamily: qfMono,
                  fontWeight: FontWeight.w700,
                  fontSize: 12,
                  color: QfColors.text2,
                ),
              ),
            ],
          ),
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
          child: Stack(
            alignment: Alignment.center,
            children: [
              // Resplandor radial de fondo
              Positioned.fill(
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: RadialGradient(
                      center: const Alignment(0, -0.3),
                      radius: 0.65,
                      colors: [
                        QfColors.cyan.withValues(alpha: 0.14),
                        Colors.transparent,
                      ],
                    ),
                  ),
                ),
              ),
              PageView.builder(
                key: const ValueKey('access-carousel'),
                controller: _pages,
                itemCount: _slides,
                onPageChanged: (i) => setState(() => _page = i),
                itemBuilder: (context, i) => Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 24),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      // Tres tarjetas decorativas deportivas CyberCore en FittedBox adaptable
                      const Expanded(
                        child: Center(
                          child: FittedBox(
                            fit: BoxFit.contain,
                            child: _AccessSportsCards(),
                          ),
                        ),
                      ),
                      const SizedBox(height: 8),
                      // Textos de la presentación
                      Text(
                        kickers[i].toUpperCase(),
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          fontFamily: qfDisplay,
                          fontWeight: FontWeight.w700,
                          fontSize: 11,
                          letterSpacing: 1.5,
                          color: QfColors.cyan,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        titles[i],
                        key: ValueKey('access-title-$i'),
                        textAlign: TextAlign.center,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: QfColors.text,
                          fontFamily: qfDisplay,
                          fontWeight: FontWeight.w700,
                          fontSize: 22,
                          height: 1.08,
                          letterSpacing: 0.2,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        bodies[i],
                        textAlign: TextAlign.center,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontFamily: 'Exo 2',
                          fontSize: 12.5,
                          color: QfColors.text2,
                          height: 1.25,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
        // Puntos indicadores pulsables
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 4),
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
                      width: 30,
                      height: 44,
                      child: Center(
                        child: AnimatedContainer(
                          duration: MediaQuery.of(context).disableAnimations
                              ? Duration.zero
                              : const Duration(milliseconds: 250),
                          width: i == _page ? 24 : 6,
                          height: 6,
                          decoration: BoxDecoration(
                            color: i == _page ? QfColors.cyan : const Color(0xFF3A3F55),
                            borderRadius: BorderRadius.circular(1),
                          ),
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
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 16),
      decoration: const ShapeDecoration(
        color: QfColors.surface,
        shadows: [
          BoxShadow(
            color: Color(0x1A00F0FF),
            blurRadius: 40,
            offset: Offset(0, -10),
          ),
        ],
        shape: CutCornerBorder(
          cut: 16,
          side: BorderSide(color: QfColors.borderStrong),
        ),
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
                fontSize: 21,
                letterSpacing: 0.6,
                color: QfColors.text,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              l10n.accessCardBody,
              style: const TextStyle(
                fontFamily: 'Exo 2',
                fontSize: 13,
                color: QfColors.text2,
              ),
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 4,
              children: [
                QfBadge(l10n.accessFreeToStart.toUpperCase(), color: QfColors.green),
                QfBadge(l10n.accessNoCard.toUpperCase(), color: QfColors.muted),
              ],
            ),
            const SizedBox(height: 12),
            _googleButton(context),
          ] else
            widget.linkingForm!,
          const SizedBox(height: 10),
          _consent(context),
          if (!widget.docsReady)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Text(
                l10n.accessPreparingDocs,
                style: const TextStyle(fontSize: 12, color: QfColors.text2),
              ),
            ),
          if (widget.error != null)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.error_outline, size: 16, color: QfColors.danger),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      widget.error!,
                      style: const TextStyle(fontSize: 13, color: QfColors.danger),
                    ),
                  ),
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
      height: 54,
      child: OutlinedButton(
        key: const ValueKey('google-button'),
        style: OutlinedButton.styleFrom(
          backgroundColor: Colors.white,
          foregroundColor: const Color(0xFF111111),
          disabledBackgroundColor: QfColors.text2,
          side: BorderSide.none,
          shape: const CutCornerBorder(cut: 10),
          padding: const EdgeInsets.symmetric(horizontal: 16),
          elevation: 0,
        ),
        onPressed: widget.busy || !widget.docsReady ? null : _google,
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (widget.busy)
              const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(strokeWidth: 2.4, color: QfColors.bg),
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
                  fontFamily: 'Exo 2',
                  fontWeight: FontWeight.w700,
                  fontSize: 16,
                  color: Color(0xFF111111),
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
      color: QfColors.cyan,
      decoration: TextDecoration.underline,
      decorationColor: QfColors.cyan,
      fontFamily: 'Exo 2',
      fontWeight: FontWeight.w600,
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
                    activeColor: QfColors.green,
                    checkColor: QfColors.onGreen,
                    side: BorderSide(color: _hint ? QfColors.danger : QfColors.muted, width: 1.6),
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
    padding: const EdgeInsets.fromLTRB(28, 8, 28, 12),
    child: Text(
      context.l10n.accessDisclaimer,
      textAlign: TextAlign.center,
      style: const TextStyle(
        fontFamily: 'Exo 2',
        color: Color(0xFF939AB0),
        fontSize: 11,
        height: 1.3,
      ),
    ),
  );
}

class _AccessSportsCards extends StatelessWidget {
  const _AccessSportsCards();

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 280,
      height: 120,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          // Tarjeta Fútbol (inclinada -5 grados)
          Transform.rotate(
            angle: -5 * math.pi / 180,
            child: Container(
              width: 78,
              height: 96,
              margin: const EdgeInsets.only(top: 10),
              decoration: const ShapeDecoration(
                color: QfColors.surface,
                shape: CutCornerBorder(
                  cut: 8,
                  side: BorderSide(color: QfColors.border),
                ),
              ),
              child: const Center(
                child: Icon(Icons.sports_soccer, size: 44, color: QfColors.text),
              ),
            ),
          ),
          const SizedBox(width: 8),
          // Tarjeta NBA (elevada, con brillo cian)
          Container(
            width: 92,
            height: 116,
            decoration: ShapeDecoration(
              color: QfColors.surface2,
              shadows: [
                BoxShadow(
                  color: QfColors.cyan.withValues(alpha: 0.28),
                  blurRadius: 30,
                  spreadRadius: 1,
                ),
              ],
              shape: const CutCornerBorder(
                cut: 10,
                side: BorderSide(color: QfColors.cyan, width: 1.2),
              ),
            ),
            child: const Center(
              child: Icon(Icons.sports_basketball, size: 54, color: QfColors.cyan),
            ),
          ),
          const SizedBox(width: 8),
          // Tarjeta Tenis (inclinada 5 grados)
          Transform.rotate(
            angle: 5 * math.pi / 180,
            child: Container(
              width: 78,
              height: 96,
              margin: const EdgeInsets.only(top: 10),
              decoration: const ShapeDecoration(
                color: QfColors.surface,
                shape: CutCornerBorder(
                  cut: 8,
                  side: BorderSide(color: QfColors.border),
                ),
              ),
              child: const Center(
                child: Icon(Icons.sports_tennis, size: 44, color: QfColors.text),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
