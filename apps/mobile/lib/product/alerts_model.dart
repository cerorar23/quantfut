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
    this.type,
    this.position,
    this.returnDate,
    this.team,
    this.crest,
    this.photo,
  });

  final String player;
  final AbsenceKind kind;
  final AbsenceReason reason;
  final String? rawReason;
  final String? type;
  final String? position;
  final String? returnDate;
  final String? team;
  final String? crest;
  final String? photo;

  /// Entrada del servidor: `{jugador, tipo, motivo}` con los textos crudos de API-Football
  /// (`Missing Fixture`, `Questionable`, `Muscle Injury`, `Red Card`…).
  factory Absence.of(JsonMap row, {String? team, String? crest}) {
    final rawType = row['tipo'] == null ? null : '${row['tipo']}'.trim();
    final type = (rawType ?? '').toLowerCase();
    final rawReason = row['motivo'] == null ? '' : '${row['motivo']}'.trim();
    final text = rawReason.toLowerCase();
    final suspended =
        type.contains('suspen') ||
        text.contains('suspen') ||
        text.contains('card') ||
        text.contains('ban');
    final kind = type.contains('question') || text == 'doubtful'
        ? AbsenceKind.doubt
        : suspended
        ? AbsenceKind.suspended
        : AbsenceKind.out;
    bool has(List<String> words) => words.any(text.contains);
    final category = rawReason.isEmpty
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
      rawReason: category == AbsenceReason.other ||
              text == 'doubtful' ||
              text == 'back in training' ||
              RegExp(r'^(Early|Mid|Late)\s+', caseSensitive: false).hasMatch(rawReason)
          ? rawReason
          : null,
      type: rawType,
      position: row['posicion'] != null
          ? '${row['posicion']}'
          : (row['pos'] != null ? '${row['pos']}' : null),
      returnDate: row['regreso_fecha'] != null ? '${row['regreso_fecha']}' : null,
      team: team,
      crest: crest,
      photo: row['foto'] != null ? '${row['foto']}' : null,
    );
  }

  /// Bajas confirmadas (no juega) frente a dudas.
  bool get confirmed => kind != AbsenceKind.doubt;
}

/// Bajas y dudas de un partido tal como las entrega el servidor (`ficha.bajas`).
class MatchAlerts {
  const MatchAlerts({
    required this.checked,
    required this.home,
    required this.away,
    this.homeLineup,
    this.awayLineup,
  });

  /// Última vez que se comprobaron (hora del servidor).
  final DateTime? checked;
  final List<Absence> home, away;

  /// Alineaciones o último once conocido de los equipos
  final JsonMap? homeLineup;
  final JsonMap? awayLineup;

  /// `null` si el partido aún no se ha comprobado nunca: eso NO equivale a «sin lesionados».
  static MatchAlerts? fromFicha(JsonMap ficha) {
    final raw = ficha['bajas'];
    if (raw is! Map) return null;
    final data = jsonMap(raw);

    final homeTeam = jsonMap(ficha['local']);
    final awayTeam = jsonMap(ficha['visitante']);
    final homeName = '${homeTeam['nombre'] ?? ''}';
    final awayName = '${awayTeam['nombre'] ?? ''}';
    final homeCrest = '${homeTeam['escudo'] ?? ''}';
    final awayCrest = '${awayTeam['escudo'] ?? ''}';

    List<Absence> side(String key) {
      final tName = key == 'home' ? homeName : awayName;
      final tCrest = key == 'home' ? homeCrest : awayCrest;
      final seen = <String>{};
      final rows = [
        for (final r in jsonRows(data[key]))
          if (seen.add('${r['jugador']}'))
            Absence.of(r, team: tName.isNotEmpty ? tName : null, crest: tCrest.isNotEmpty ? tCrest : null),
      ];
      rows.sort((a, b) {
        final byKind = (a.confirmed ? 0 : 1).compareTo(b.confirmed ? 0 : 1);
        return byKind != 0 ? byKind : a.player.compareTo(b.player);
      });
      return rows;
    }

    final rawAlineaciones = ficha['alineaciones'];
    final alineacionesMap = rawAlineaciones is Map ? jsonMap(rawAlineaciones) : const <String, dynamic>{};
    final homeLineup = alineacionesMap['home'] is Map
        ? jsonMap(alineacionesMap['home'])
        : (homeTeam['ultimo_once'] is Map ? jsonMap(homeTeam['ultimo_once']) : null);
    final awayLineup = alineacionesMap['away'] is Map
        ? jsonMap(alineacionesMap['away'])
        : (awayTeam['ultimo_once'] is Map ? jsonMap(awayTeam['ultimo_once']) : null);

    return MatchAlerts(
      checked: dateValue(data['comprobada']),
      home: side('home'),
      away: side('away'),
      homeLineup: homeLineup,
      awayLineup: awayLineup,
    );
  }

  List<Absence> of(String side) => side == 'home' ? home : away;
  List<Absence> against(String side) => side == 'home' ? away : home;

  int confirmedCount(String side) => of(side).where((a) => a.confirmed).length;
  int doubtCount(String side) => of(side).where((a) => !a.confirmed).length;

  /// Bajas totales de ambos equipos (para el contador de la pestaña).
  int get total => home.length + away.length;
}
