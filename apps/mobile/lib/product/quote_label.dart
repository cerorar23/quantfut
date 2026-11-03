import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../l10n/app_locale.dart';
import 'live_api.dart';
import 'qf_theme.dart';
import 'sports_quotes.dart';

/// Cuota de referencia de un mercado de NBA/tenis: `@1,90` en mono y debajo «casa · hora local».
/// Sin cuota, «—» (muted) con semántica «sin cuota». Nunca ámbar (reservado a compra) y nunca un
/// precio sin su casa y su hora.
class QuoteLabel extends StatelessWidget {
  const QuoteLabel({super.key, required this.quote, this.align = CrossAxisAlignment.end});

  final SportQuote? quote;
  final CrossAxisAlignment align;

  /// Tope de ancho: la casa se recorta con elipsis antes de empujar el pick fuera de la tarjeta.
  static const maxWidth = 88.0;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final q = quote;
    if (q == null) {
      return Semantics(
        label: l10n.quoteNone,
        excludeSemantics: true,
        child: const Text(
          '—',
          key: ValueKey('quote-none'),
          style: TextStyle(fontFamily: qfMono, fontSize: 13, color: QfColors.muted),
        ),
      );
    }
    final time = localDate(DateFormat.Hm, q.asOf.toLocal());
    return ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: maxWidth),
      child: Column(
        key: const ValueKey('quote-value'),
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: align,
        children: [
          Text(
            '@${decimalText(q.price)}',
            maxLines: 1,
            style: const TextStyle(
              fontFamily: qfMono,
              fontSize: 13,
              color: QfColors.text,
            ),
          ),
          Text(
            l10n.quoteBookAt(q.book, time),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 10, color: QfColors.text2),
          ),
        ],
      ),
    );
  }
}

/// Leyenda única de la ficha bajo la lista de pronósticos.
class QuoteReferenceCaption extends StatelessWidget {
  const QuoteReferenceCaption({super.key});

  @override
  Widget build(BuildContext context) => Text(
    context.l10n.quoteReference,
    key: const ValueKey('quote-reference'),
    style: const TextStyle(fontSize: 11, color: QfColors.muted),
  );
}
