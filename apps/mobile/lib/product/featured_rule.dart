/// Regla del pronóstico destacado «probabilidad máxima segura» (titular, 2026-11-05), la misma del servidor
/// (`src/qf/api/destacado_valor.py`) y de la web (`bestBySafety` en `frontend/sports-data.js`): el producto
/// quiere que el usuario vea >= 80 % de aciertos, así que NO se maximiza el valor esperado. Cuota de referencia
/// >= 1,20 y probabilidad >= 75 %; gana la MAYOR probabilidad (la cuota no multiplica nada); en empate, la mayor
/// cuota; si aun así empatan, el primero. Sin candidatos devuelve null: mejor no destacar nada que algo que falla.
const featuredMinPrice = 1.20;
const featuredMinProb = .75;

double? _finite(Object? v) => v is num && v.isFinite ? v.toDouble() : null;

T? bestBySafety<T>(
  Iterable<T> items,
  Object? Function(T) probOf,
  Object? Function(T) priceOf,
) {
  T? best;
  var bestProb = double.negativeInfinity, bestPrice = double.negativeInfinity;
  for (final item in items) {
    final prob = _finite(probOf(item)), price = _finite(priceOf(item));
    if (prob == null ||
        price == null ||
        price < featuredMinPrice ||
        prob < featuredMinProb) {
      continue;
    }
    if (best == null ||
        prob > bestProb ||
        (prob == bestProb && price > bestPrice)) {
      best = item;
      bestProb = prob;
      bestPrice = price;
    }
  }
  return best;
}

/// Cuota del modelo (1 ÷ probabilidad) para quien no tiene cuota de casa: con el mínimo de 1,20
/// el destacado sale de la franja 75 %–83,3 %.
double? modelPrice(double prob) => prob > 0 ? 1 / prob : null;
