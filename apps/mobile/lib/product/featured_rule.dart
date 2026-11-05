/// Regla del pronóstico destacado por valor esperado (titular, 2026-11-05), la misma del servidor
/// (`src/qf/api/destacado_valor.py`) y de la web (`bestByValue` en `frontend/sports-data.js`):
/// cuota de referencia >= 1,20 y probabilidad >= 55 %; gana la mayor probabilidad × cuota y, en
/// empate, la mayor probabilidad; si aun así empatan, el primero. Sin candidatos devuelve null.
const featuredMinPrice = 1.20;
const featuredMinProb = .55;

double? _finite(Object? v) => v is num && v.isFinite ? v.toDouble() : null;

/// Puntuación redondeada a 9 decimales: sin ello el ruido de coma flotante decidiría los empates.
double featuredScore(double prob, double price) =>
    (prob * price * 1e9).round() / 1e9;

T? bestByValue<T>(
  Iterable<T> items,
  Object? Function(T) probOf,
  Object? Function(T) priceOf,
) {
  T? best;
  var bestScore = double.negativeInfinity, bestProb = double.negativeInfinity;
  for (final item in items) {
    final prob = _finite(probOf(item)), price = _finite(priceOf(item));
    if (prob == null ||
        price == null ||
        price < featuredMinPrice ||
        prob < featuredMinProb) {
      continue;
    }
    final score = featuredScore(prob, price);
    if (best == null ||
        score > bestScore ||
        (score == bestScore && prob > bestProb)) {
      best = item;
      bestScore = score;
      bestProb = prob;
    }
  }
  return best;
}

/// Cuota del modelo (1 ÷ probabilidad) para quien no tiene cuota de casa: puntúa 1 en todos
/// los mercados, así que solo manda el desempate (la mayor probabilidad que aún paga 1,20).
double? modelPrice(double prob) => prob > 0 ? 1 / prob : null;
