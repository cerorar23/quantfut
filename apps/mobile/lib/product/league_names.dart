// l10n-ignore-start (nombres propios de competiciones: son datos, no textos traducibles)
const _leagueNames = <String, String>{
  'ar.primera': 'Liga Profesional',
  'br.serie_a': 'Brasileirão Série A',
  'br.serie_b': 'Série B',
  'ch.super_league': 'Super League',
  'cl.primera': 'Primera División',
  'de.bundesliga': 'Bundesliga',
  'de.bundesliga2': '2. Bundesliga',
  'dk.superliga': 'Superliga',
  'es.laliga': 'LaLiga',
  'es.laliga2': 'LaLiga 2',
  'eu.ucl': 'Champions League',
  'eu.uel': 'Europa League',
  'fr.ligue_1': 'Ligue 1',
  'fr.ligue_2': 'Ligue 2',
  'gb.championship': 'Championship',
  'gb.premier_league': 'Premier League',
  'it.serie_a': 'Serie A',
  'it.serie_b': 'Serie B',
  'mx.liga_mx': 'Liga MX',
  // Escalones de la NBA en el reto escalera (league_id = deporte).
  'nba': 'NBA',
  'nl.eredivisie': 'Eredivisie',
  'no.eliteserien': 'Eliteserien',
  'pt.primeira': 'Primeira Liga',
  'se.allsvenskan': 'Allsvenskan',
  'tr.super_lig': 'Süper Lig',
  'us.mls': 'MLS',
};
// l10n-ignore-end

/// Nombre corto de una competición a partir de su identificador (`eu.ucl`); `null` si no se conoce.
String? leagueName(dynamic id) => id is String ? _leagueNames[id] : null;
