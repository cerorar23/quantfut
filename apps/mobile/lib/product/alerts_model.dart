import 'live_api.dart';

/// Qué le pasa al jugador respecto al partido.
enum AbsenceKind { out, doubt, suspended }

/// Motivo, agrupado a partir del texto del proveedor (en inglés). Lo que no encaja en un grupo
/// se enseña tal cual (`rawReason`): nunca se inventa un motivo.
enum AbsenceReason {
  muscle,
  knee,
  foot,
  knock,
  illness,
  injury,
  suspension,
  other,
  unknown,
}

class Absence {
  const Absence({
    required this.player,
    required this.kind,
    required this.reason,
    this.rawReason,
  });

  final String player;
  final AbsenceKind kind;
  final AbsenceReason reason;
  final String? rawReason;

  /// Entrada del servidor: `{jugador, tipo, motivo}` con los textos crudos de API-Football
  /// (`Missing Fixture`, `Questionable`, `Muscle Injury`, `Red Card`…).
  factory Absence.of(JsonMap row) {
    final type = '${row['tipo'] ?? ''}'.toLowerCase();
    final reason = row['motivo'] == null ? '' : '${row['motivo']}'.trim();
    final text = reason.toLowerCase();
    final suspended =
        type.contains('suspen') ||
        text.contains('suspen') ||
        text.contains('card') ||
        text.contains('ban');
    final kind = type.contains('question')
        ? AbsenceKind.doubt
        : suspended
        ? AbsenceKind.suspended
        : AbsenceKind.out;
    bool has(List<String> words) => words.any(text.contains);
    final category = reason.isEmpty
        ? AbsenceReason.unknown
        : suspended
        ? AbsenceReason.suspension
        : has(['muscle', 'hamstring', 'calf', 'thigh', 'groin', 'adductor'])
        ? AbsenceReason.muscle
        : has(['knee'])
        ? AbsenceReason.knee
        : has(['ankle', 'foot', 'toe', 'achilles'])
        ? AbsenceReason.foot
        : has(['knock'])
        ? AbsenceReason.knock
        : has(['illness', 'virus', 'flu', 'covid', 'sick'])
        ? AbsenceReason.illness
        : text == 'injury' || text == 'injured'
        ? AbsenceReason.injury
        : AbsenceReason.other;
    return Absence(
      player: '${row['jugador'] ?? ''}',
      kind: kind,
      reason: category,
      rawReason: category == AbsenceReason.other ? reason : null,
    );
  }

  /// Bajas confirmadas (no juega) frente a dudas.
  bool get confirmed => kind != AbsenceKind.doubt;
}

/// Bajas y dudas de un partido tal como las entrega el servidor (`ficha.bajas`).
class MatchAlerts {
  const MatchAlerts({required this.checked, required this.home, required this.away});

  /// Última vez que se comprobaron (hora del servidor).
  final DateTime? checked;
  final List<Absence> home, away;

  /// `null` si el partido aún no se ha comprobado nunca: eso NO equivale a «sin lesionados».
  static MatchAlerts? fromFicha(JsonMap ficha) {
    final raw = ficha['bajas'];
    if (raw is! Map) return null;
    final data = jsonMap(raw);
    List<Absence> side(String key) {
      final seen = <String>{};
      final rows = [
        for (final r in jsonRows(data[key]))
          if (seen.add('${r['jugador']}')) Absence.of(r),
      ];
      rows.sort((a, b) {
        final byKind = (a.confirmed ? 0 : 1).compareTo(b.confirmed ? 0 : 1);
        return byKind != 0 ? byKind : a.player.compareTo(b.player);
      });
      return rows;
    }

    return MatchAlerts(
      checked: dateValue(data['comprobada']),
      home: side('home'),
      away: side('away'),
    );
  }

  List<Absence> of(String side) => side == 'home' ? home : away;
  List<Absence> against(String side) => side == 'home' ? away : home;

  int confirmedCount(String side) => of(side).where((a) => a.confirmed).length;
  int doubtCount(String side) => of(side).where((a) => !a.confirmed).length;

  /// Bajas totales de ambos equipos (para el contador de la pestaña).
  int get total => home.length + away.length;
}
