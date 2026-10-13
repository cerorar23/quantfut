// ignore: unused_import
import 'package:intl/intl.dart' as intl;

import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Spanish Castilian (`es`).
class AppLocalizationsEs extends AppLocalizations {
  AppLocalizationsEs([String locale = 'es']) : super(locale);

  @override
  String get accessConsent =>
      'Tengo al menos 18 años y acepto los términos y la política de privacidad.';

  @override
  String get accessContinueWithGoogle => 'Continuar con Google';

  @override
  String get accessDocumentOpenError => 'No se pudo abrir el documento.';

  @override
  String get accessForgotLink => 'Recuperar contraseña anterior';

  @override
  String get accessForgotSent =>
      'Si existe la cuenta, recibirás instrucciones por correo.';

  @override
  String get accessGenericError =>
      'No se pudo completar el acceso. Inténtalo de nuevo.';

  @override
  String get accessGoogleError =>
      'No se pudo acceder con Google. Inténtalo de nuevo.';

  @override
  String get accessLinkButton => 'Vincular mi cuenta';

  @override
  String get accessLinkEmail => 'Correo de tu cuenta anterior';

  @override
  String get accessLinkIntro =>
      'Vincula tu cuenta anterior para conservar saldo y acceso.';

  @override
  String get accessLinkPassword => 'Contraseña anterior';

  @override
  String get accessOtherAccount => 'Usar otra cuenta';

  @override
  String get accessPreparingDocs =>
      'Estamos preparando los documentos de acceso.';

  @override
  String get accessPrivacy => 'Política de privacidad';

  @override
  String get accessRetry => 'Reintentar acceso';

  @override
  String get accessTagline =>
      'Partidos, análisis e historial. Una probabilidad no es una certeza.';

  @override
  String get accessTerms => 'Términos de uso';

  @override
  String get apiGoogleNotVerified => 'Google no pudo verificar el acceso.';

  @override
  String get apiInvalidResponse => 'Respuesta no válida del servidor.';

  @override
  String get apiInvalidSession => 'Sesión no válida.';

  @override
  String apiLoadFailed(int status) {
    return 'No se pudo cargar la información (HTTP $status).';
  }

  @override
  String get apiOffline =>
      'No se pudo conectar. Comprueba tu conexión e inténtalo de nuevo.';

  @override
  String get apiSessionExpired => 'Inicia sesión de nuevo.';

  @override
  String get apiSignInWithGoogle => 'Inicia sesión con Google.';

  @override
  String get artAnalyzeEach => 'ANALIZA CADA SELECCIÓN';

  @override
  String get artCorners => 'CÓRNERS';

  @override
  String get artFootball => 'FÚTBOL';

  @override
  String get artForm => 'FORMA';

  @override
  String get artGoals => 'GOLES';

  @override
  String get artHeadToHead => 'CARA A CARA';

  @override
  String get artHeading0 => 'FÚTBOL + NBA';

  @override
  String get artHeading1 => 'EL CONTEXTO IMPORTA';

  @override
  String get artHeading2 => 'EXPLORA LOS MERCADOS';

  @override
  String get artHeading3 => 'HISTORIAL A LA VISTA';

  @override
  String get artHeading4 => 'DATOS + TU CRITERIO';

  @override
  String get artNba => 'NBA';

  @override
  String get artStats => 'ESTADÍSTICAS';

  @override
  String get artTagline => 'ANALIZA. COMPARA. EXPLORA.';

  @override
  String get artTransparency => 'TRANSPARENCIA';

  @override
  String get bannerLive =>
      'PARTIDO EN JUEGO · pronóstico sellado antes del inicio';

  @override
  String bannerLost(String score) {
    return 'FALLADO$score · pronóstico sellado antes del inicio';
  }

  @override
  String bannerWon(String score) {
    return 'ACERTADO$score · pronóstico sellado antes del inicio';
  }

  @override
  String get calendarEmpty => 'No hay enfrentamientos para estos filtros.';

  @override
  String calendarMatchesCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count enfrentamientos',
      one: '$count enfrentamiento',
    );
    return '$_temp0';
  }

  @override
  String get calendarPickDate => 'Elegir fecha';

  @override
  String get calendarSearchHint => 'Busca equipos o ligas';

  @override
  String get calendarTitle => 'Calendario · hora local';

  @override
  String casesCount(int count, String formatted) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$formatted casos',
      one: '$formatted caso',
    );
    return '$_temp0';
  }

  @override
  String get commonAll => 'Todos';

  @override
  String get commonAway => 'Visitante';

  @override
  String get commonCancel => 'Cancelar';

  @override
  String get commonClose => 'Cerrar';

  @override
  String get commonConfirm => 'Confirmar';

  @override
  String get commonConnecting => 'Conectando…';

  @override
  String get commonDraw => 'Empate';

  @override
  String get commonHome => 'Local';

  @override
  String get commonRefresh => 'Actualizar';

  @override
  String get commonRetry => 'Reintentar';

  @override
  String get commonSeeVip => 'Ver acceso VIP';

  @override
  String get commonToday => 'Hoy';

  @override
  String get commonYesterday => 'Ayer';

  @override
  String countdownDays(int days, String time) {
    return '${days}d $time';
  }

  @override
  String detailChecked(String date) {
    return 'Comprobado: $date';
  }

  @override
  String get detailFormationPending => 'Formación pendiente';

  @override
  String get detailH2hTitle => 'Historial directo (H2H)';

  @override
  String get detailInjuries => 'Bajas reportadas';

  @override
  String get detailLineups => 'Alineaciones';

  @override
  String get detailLineupsPending => 'Alineaciones todavía no confirmadas.';

  @override
  String get detailNoH2h =>
      'No hay enfrentamientos registrados para este partido.';

  @override
  String get detailNoInjuries => 'Sin bajas en el reporte disponible.';

  @override
  String get detailNoInjuriesCheck =>
      'No hay una comprobación de bajas disponible.';

  @override
  String get detailNoPicks =>
      'No hay pronósticos publicados para este partido.';

  @override
  String get detailNoStarters => 'Sin titulares confirmados.';

  @override
  String get detailReferee => 'Árbitro';

  @override
  String get detailRefereePending => 'Árbitro pendiente de confirmar.';

  @override
  String get detailTabH2h => 'H2H';

  @override
  String get detailTabPredictions => 'Pronósticos';

  @override
  String get detailTabStats => 'Estadísticas';

  @override
  String get detailVipPickNotice => 'Este partido tiene un pronóstico VIP';

  @override
  String get dictAwayDefault => 'el visitante';

  @override
  String get dictHomeDefault => 'el local';

  @override
  String dictOddsAbove(String fair) {
    return 'La cuota publicada supera la cuota justa ($fair).';
  }

  @override
  String dictOddsBelow(String fair) {
    return 'La cuota publicada queda por debajo de la cuota justa ($fair); el atractivo está en la probabilidad, no en el precio.';
  }

  @override
  String dictPick(String pick, String percent) {
    return '$pick con probabilidad calculada de $percent.';
  }

  @override
  String get dictPickDefault => 'El pronóstico';

  @override
  String dictXg(
    String total,
    String home,
    String homeXg,
    String away,
    String awayXg,
  ) {
    return 'Las cuotas del mercado sin margen implican $total goles esperados ($home $homeXg · $away $awayXg).';
  }

  @override
  String get disclaimerProbability =>
      'Una probabilidad no es una certeza. Decide con información y juega responsablemente.';

  @override
  String get famCardsSubtitle =>
      'Líneas de menos tarjetas con respaldo histórico';

  @override
  String get famCardsTitle => 'Tarjetas';

  @override
  String get famCornersSubtitle => 'Más y menos córners del partido completo';

  @override
  String get famCornersTeamSubtitle => 'Local y visitante, con su propia línea';

  @override
  String get famCornersTeamTitle => 'Córners por equipo';

  @override
  String get famCornersTitle => 'Córners totales';

  @override
  String get famDoubleChanceSubtitle =>
      'Dos resultados posibles en una selección';

  @override
  String get famDoubleChanceTitle => 'Doble oportunidad';

  @override
  String get famGoalsSubtitle => 'Totales con líneas históricamente evaluadas';

  @override
  String get famGoalsTitle => 'Goles del partido';

  @override
  String get famHandicapSubtitle =>
      'Líneas de protección y empate con devolución';

  @override
  String get famHandicapTitle => 'Hándicap asiático';

  @override
  String get famNbaSubtitle =>
      'Evaluación exploratoria · pendiente de confirmación';

  @override
  String get famNbaTeamTitle => 'NBA · Puntos de equipo';

  @override
  String get famNbaTotalTitle => 'NBA · Total del partido';

  @override
  String get famNbaWinnerTitle => 'NBA · Ganador';

  @override
  String get famTeamGoalsSubtitle =>
      'Al menos un gol del local o del visitante';

  @override
  String get famTeamGoalsTitle => 'Marca un equipo';

  @override
  String get famWinnerSubtitle => 'Resultado 1X2 de alta probabilidad';

  @override
  String get famWinnerTitle => 'Ganador del partido';

  @override
  String get featAgenda => 'Agenda temporalmente no disponible';

  @override
  String get featBalance => 'Seguimiento en preparación';

  @override
  String get featCommunity => 'Comunidad en preparación';

  @override
  String get featLanguages => 'Traducciones en preparación';

  @override
  String get featMatchData => 'Datos del partido temporalmente no disponibles';

  @override
  String get featMeasurement => 'Medición en preparación';

  @override
  String get featNba => 'Modelo NBA en entrenamiento';

  @override
  String get featNotifications => 'Notificaciones en preparación';

  @override
  String get featPurchases => 'Compras en preparación';

  @override
  String get featStats => 'Estadísticas temporalmente no disponibles';

  @override
  String get featVip => 'Acceso VIP temporalmente no disponible';

  @override
  String get featureTraining => 'Modelo en entrenamiento';

  @override
  String get fixtureFinished => 'FINALIZADO';

  @override
  String get fixtureLive => 'EN VIVO';

  @override
  String get fixtureLocalTime => 'HORA LOCAL';

  @override
  String get fixtureStartsIn => 'EMPIEZA EN';

  @override
  String get fixtureTbd => 'POR CONFIRMAR';

  @override
  String get forecastCanFail =>
      'Un pronóstico puede fallar; la probabilidad no garantiza el resultado.';

  @override
  String get forecastFeatured => 'DESTACADO';

  @override
  String get forecastFree => 'GRATUITO';

  @override
  String get forecastHalfTime => 'DESCANSO';

  @override
  String get forecastInPlay => 'EN JUEGO';

  @override
  String get forecastLiveScore => 'Marcador en vivo';

  @override
  String forecastLiveScoreAgo(int minutes) {
    return 'Marcador en vivo · actualizado hace $minutes min';
  }

  @override
  String get forecastMarketNote =>
      'Probabilidades calculadas con las cuotas del mercado sin margen: esta liga no tiene modelo propio.';

  @override
  String get forecastOddsAtPublish => 'Cuota al publicar';

  @override
  String forecastProbCalc(String percent) {
    return '$percent prob. calculada';
  }

  @override
  String get forecastSeeStats => 'Ver estadísticas del partido';

  @override
  String get forecastSourceMarket => 'CUOTAS DEL MERCADO';

  @override
  String get forecastSourceModel => 'MODELO PROPIO';

  @override
  String get forecastTitle => 'ANÁLISIS ESTADÍSTICO';

  @override
  String get forecastUnlocked => 'DESBLOQUEADO';

  @override
  String get forecastVerdictTitle => '💡  DICTAMEN DEL MODELO';

  @override
  String get formatScheduleUnavailable => 'Horario no disponible';

  @override
  String get groupBtts => 'AMBOS MARCAN';

  @override
  String get groupCards => 'TARJETAS';

  @override
  String get groupCorners => 'CÓRNERS';

  @override
  String get groupDoubleChance => 'DOBLE OPORTUNIDAD';

  @override
  String get groupDrawNoBet => 'EMPATE NO ACCIÓN';

  @override
  String get groupFirstHalf => '1ª MITAD';

  @override
  String get groupGoals => 'GOLES';

  @override
  String get groupHandicap => 'HÁNDICAP';

  @override
  String get groupResult => 'RESULTADO';

  @override
  String get groupSpecials => 'ESPECIALES';

  @override
  String get groupTeamGoals => 'GOLES DE EQUIPO';

  @override
  String get homeByDate => 'Partidos por fecha y horario';

  @override
  String get inboxEmpty => 'Todavía no tienes avisos.';

  @override
  String get inboxMatch => 'Partido';

  @override
  String get inboxTitle => 'Avisos';

  @override
  String ladderActiveCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count retos en marcha',
      one: '1 reto en marcha',
    );
    return '$_temp0';
  }

  @override
  String get ladderBalance => 'saldo actual';

  @override
  String get ladderChance => 'de completarlo';

  @override
  String get ladderEmpty => 'No hay retos activos publicados.';

  @override
  String ladderEstimateNote(String avg) {
    return 'Estimación: usa la probabilidad del escalón en juego y la media de los demás ($avg). No es una garantía.';
  }

  @override
  String get ladderFreeHint => 'Un escalón gratuito: el de mayor probabilidad.';

  @override
  String get ladderHideSteps => 'Ocultar escalones';

  @override
  String get ladderHistoryDone => 'Cumplido';

  @override
  String get ladderHistoryEmpty =>
      'Aún no hay retos cerrados. Cuando uno termine, aparecerá aquí con su resultado.';

  @override
  String ladderHistoryFailedAt(int step) {
    return 'Falló en el escalón $step';
  }

  @override
  String ladderHistoryRate(String rate) {
    return 'Tasa de cumplidos: $rate';
  }

  @override
  String ladderHistoryResult(String roi) {
    return 'Resultado acumulado: $roi';
  }

  @override
  String ladderHistorySummary(int done, int closed) {
    return '$done cumplidos de $closed cerrados';
  }

  @override
  String get ladderHistoryTitle => 'Historial de retos';

  @override
  String get ladderNoteInPlay =>
      'Hay un escalón esperando resultado. El reto sigue vivo.';

  @override
  String get ladderNoteToPick =>
      'Falta elegir el siguiente escalón; puede tardar días. El reto sigue vivo.';

  @override
  String ladderRemaining(int remaining) {
    String _temp0 = intl.Intl.pluralLogic(
      remaining,
      locale: localeName,
      other: 'faltan $remaining',
      one: 'falta 1',
    );
    return '$_temp0';
  }

  @override
  String get ladderShowSteps => 'Ver escalones';

  @override
  String get ladderStatusInPlay => 'En juego';

  @override
  String get ladderStatusToPick => 'Por elegir';

  @override
  String ladderTitle(Object id, int steps) {
    String _temp0 = intl.Intl.pluralLogic(
      steps,
      locale: localeName,
      other: '$steps escalones',
      one: '$steps escalón',
    );
    return 'Reto #$id · $_temp0';
  }

  @override
  String ladderWonOf(int won, int goal) {
    return '$won de $goal ganados';
  }

  @override
  String get languageFirstBadge => 'Configuración de idioma';

  @override
  String get languageFirstHint =>
      'Configura el idioma de análisis para una mejor experiencia';

  @override
  String get languageFirstTitle => 'Selecciona tu idioma';

  @override
  String get languageHint =>
      'Elige el idioma. Se guarda en este dispositivo y en tu cuenta.';

  @override
  String get languageTitle => 'Idioma de la app';

  @override
  String get ledgerAttendance => 'Asistencia';

  @override
  String get ledgerInvitee => 'Premio de bienvenida';

  @override
  String get ledgerOffer => 'Oferta completada';

  @override
  String get ledgerReferralReversal => 'Premio de invitación revertido';

  @override
  String get ledgerReferrer => 'Premio por invitar';

  @override
  String get ledgerReversal => 'Oferta anulada';

  @override
  String get ledgerUnlock => 'Pronóstico desbloqueado';

  @override
  String get levelHigh => 'ALTA PROB.';

  @override
  String get levelModerate => 'MODERADA';

  @override
  String get levelSolid => 'SÓLIDA';

  @override
  String get lineAwayScores => 'Marca el visitante · más de 0,5 goles';

  @override
  String get lineDoubleChance => 'Doble oportunidad · 1X / X2 / 12';

  @override
  String lineHandicap(String line) {
    return 'Hándicap $line';
  }

  @override
  String get lineHomeScores => 'Marca el local · más de 0,5 goles';

  @override
  String lineTeamCorners(String team, String side, String line) {
    String _temp0 = intl.Intl.selectLogic(side, {
      'over': 'más de $line córners',
      'other': 'menos de $line córners',
    });
    return '$team: $_temp0';
  }

  @override
  String get lineWinner => 'Ganador · selección de alta probabilidad';

  @override
  String get maintenanceNotice =>
      'Estamos realizando mantenimiento. Algunas funciones pueden tardar más.';

  @override
  String get marketAwayScores => 'Marca el visitante';

  @override
  String get marketBtts => 'Ambos marcan';

  @override
  String get marketCards => 'Tarjetas';

  @override
  String get marketCorners => 'Córners';

  @override
  String get marketCornersAway => 'Córners del visitante';

  @override
  String get marketCornersHome => 'Córners del local';

  @override
  String get marketDoubleChance => 'Doble oportunidad';

  @override
  String get marketGoals => 'Goles';

  @override
  String get marketGoalsAway => 'Goles del visitante';

  @override
  String get marketGoalsHome => 'Goles del local';

  @override
  String get marketHandicap => 'Hándicap';

  @override
  String get marketHomeScores => 'Marca el local';

  @override
  String get marketHtBtts => 'Ambos anotan en el 1er tiempo';

  @override
  String get marketHtGoal => 'Gol en el 1er tiempo';

  @override
  String get marketResult1x2 => 'Resultado 1X2';

  @override
  String get marketUnknown => 'Mercado';

  @override
  String get marketWinToNil => 'Gana a cero';

  @override
  String get marketsAndResults => 'Mercados y resultados';

  @override
  String marketsEvidenceAt(String date) {
    return 'Evidencia al $date';
  }

  @override
  String get marketsFamiliesRadar => 'familias de mercado en el radar';

  @override
  String marketsHistoricHit(String percent) {
    return 'acierto histórico $percent';
  }

  @override
  String get marketsInReview => 'En revisión: sin línea confirmada';

  @override
  String get marketsModelActive => 'MODELO ACTIVO';

  @override
  String get marketsNoLineLabel => 'sin línea confirmada';

  @override
  String get marketsNoPublications => 'Sin publicaciones aún';

  @override
  String get marketsNoResolved => 'Sin pronósticos resueltos';

  @override
  String marketsPublished(int won, int cases) {
    return 'Publicado $won/$cases';
  }

  @override
  String marketsPublishedWon(int won, int cases, String percent) {
    return '$won/$cases publicados acertados · $percent';
  }

  @override
  String get marketsRadarNote =>
      'El anillo es el acierto histórico de la mejor línea validada de cada mercado; «Publicado» son los pronósticos ya resueltos. Son pronósticos previos al partido, no alertas en vivo, y ninguna probabilidad garantiza un resultado.';

  @override
  String mdCornersTotal(Object total) {
    return 'córners · total $total';
  }

  @override
  String get mdEmptyHistory =>
      'Todavía no hay pronósticos resueltos en este mercado.';

  @override
  String get mdEmptyToday =>
      'No hay pronósticos disponibles ahora para este mercado. Aparecen cuando el modelo los publica, antes del partido.';

  @override
  String get mdHitRate => 'Tasa de acierto';

  @override
  String get mdLineConfirmed => 'Confirmada';

  @override
  String get mdLineNotDeployed => 'Sin desplegar';

  @override
  String get mdLineReview => 'En revisión';

  @override
  String get mdLineShort => 'Muestra corta';

  @override
  String get mdLoadError => 'No se pudo cargar el historial.';

  @override
  String get mdModel => 'MODELO';

  @override
  String get mdNoDate => 'Sin fecha';

  @override
  String get mdOverall => 'General';

  @override
  String get mdTabPrevious => 'Anteriores';

  @override
  String mdTabToday(int count) {
    return 'Hoy ($count)';
  }

  @override
  String get mdValidatedLines => 'Líneas validadas';

  @override
  String get mmChance => 'OPORTUNIDAD';

  @override
  String get mmDisclaimer =>
      'Es análisis del modelo, no una recomendación de apuesta. «Cuota justa» es 1/probabilidad: no es una cuota de casa. Un pronóstico puede fallar.';

  @override
  String get mmFairOdds => 'cuota justa';

  @override
  String mmGroupCount(String group, int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count mercados',
      one: '$count mercado',
    );
    return '$group · $_temp0';
  }

  @override
  String mmLocked(int count) {
    return '$count con candado';
  }

  @override
  String mmOpen(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count abiertos',
      one: '$count abierto',
    );
    return '$_temp0';
  }

  @override
  String mmProb(int value) {
    return '$value% Prob.';
  }

  @override
  String get mmPublishedOdds => 'cuota publicada';

  @override
  String get mmScoresTitle => 'Marcadores más probables';

  @override
  String get mmScoresVip => 'Los marcadores más probables son para VIP.';

  @override
  String get mmTitle => 'Mercados del partido';

  @override
  String get navCoins => 'Coins';

  @override
  String get navHome => 'Inicio';

  @override
  String get navMarkets => 'Mercados';

  @override
  String get navPredictions => 'Predicciones';

  @override
  String get navProfile => 'Perfil';

  @override
  String noteExpectedAverage(String value) {
    return 'Media esperada: $value';
  }

  @override
  String noteExpectedGoals(String value) {
    return 'Goles esperados: $value';
  }

  @override
  String noteXg(String home, String homeValue, String away, String awayValue) {
    return 'xG: $home $homeValue · $away $awayValue';
  }

  @override
  String get notificationIosPending =>
      'Las notificaciones de iOS esperan la configuración de Apple.';

  @override
  String get notificationPermissionDenied =>
      'Activa el permiso desde los ajustes del dispositivo.';

  @override
  String get outcomeLoss => 'Fallado';

  @override
  String get outcomePush => 'Reembolso';

  @override
  String get outcomeWin => 'Acertado';

  @override
  String parleyDayCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count parlays',
      one: '$count parlay',
    );
    return '$_temp0';
  }

  @override
  String parleyDaySettled(int won, int settled) {
    return '$won/$settled acertados';
  }

  @override
  String get parleyDisclaimer =>
      'Se elige por probabilidad, no por valor, y cada pata resta margen. Un parley puede fallar: multiplicar cuotas también multiplica el riesgo.';

  @override
  String get parleyFewNote =>
      'Con pocos parlays la tasa real no demuestra nada todavía.';

  @override
  String get parleyFreeNote =>
      'Uno gratis al día (el de menor cuota); el resto, VIP.';

  @override
  String get parleyHistoryTitle => 'Historial del Parley';

  @override
  String get parleyInactiveBody =>
      'Cuando se active verás aquí los parlays del día, sellados antes de que empiecen los partidos.';

  @override
  String get parleyInactiveTitle => 'El Parley todavía no está activo';

  @override
  String parleyJointProb(String percent, int legs) {
    String _temp0 = intl.Intl.pluralLogic(
      legs,
      locale: localeName,
      other: '$legs patas',
      one: '$legs pata',
    );
    return '$percent de probabilidad conjunta · $_temp0';
  }

  @override
  String get parleyLoadError => 'No se pudo cargar el Parley.';

  @override
  String get parleyNoneBody =>
      'El modelo no publica un parley si no encuentra uno dentro de las reglas.';

  @override
  String get parleyNoneTitle => 'Hoy no hay parlays';

  @override
  String parleyOddsBetween(String min, String max) {
    return 'Cuota entre $min y $max';
  }

  @override
  String get parleyOutcomeLoss => 'Falló';

  @override
  String get parleyOutcomePending => 'Pendiente';

  @override
  String get parleyOutcomeVoid => 'Anulado';

  @override
  String get parleyOutcomeWin => 'Acertó';

  @override
  String get parleyPastDays => 'Días anteriores';

  @override
  String parleyRange(int count, String min, String max) {
    return 'De 1 a $count parlays · cuota entre $min y $max · el más probable de cada escalón';
  }

  @override
  String parleyResultScore(Object score) {
    return 'Resultado $score';
  }

  @override
  String get parleySealed => 'Parlays sellados antes de los partidos';

  @override
  String parleyStep(Object step) {
    return 'ESCALÓN $step';
  }

  @override
  String parleySummary(Object hits, Object total) {
    return '$hits/$total parlays acertados';
  }

  @override
  String parleySummaryPromised(String value) {
    return ' frente a $value % prometido';
  }

  @override
  String parleySummaryReal(String value) {
    return ' · $value % real';
  }

  @override
  String pickOddsAtPublish(Object book) {
    return 'Cuota al publicar · $book';
  }

  @override
  String pickProbability(String percent) {
    return 'Probabilidad $percent';
  }

  @override
  String get pickSeeAnalysis => 'Ver análisis del partido';

  @override
  String get pickSourceNA => 'Fuente no disponible';

  @override
  String pickUnlockCoins(Object cost) {
    return 'Desbloquear por $cost monedas';
  }

  @override
  String get pickUnlockPrompt => 'Desbloquea el pronóstico y su cuota.';

  @override
  String get pickUnlockVip => 'Desbloquear pronóstico VIP';

  @override
  String get picksEmpty =>
      'No hay pronósticos publicados pendientes en este rango.';

  @override
  String picksRangeHint(int min, int max) {
    return '$min–$max % de probabilidad · uno gratis por mercado';
  }

  @override
  String picksTrainingReasons(String reasons) {
    return 'Modelo en entrenamiento · $reasons';
  }

  @override
  String get prefsAnalyticsBody =>
      'Ayuda a mejorar la app con datos sobre las pantallas utilizadas. Es opcional.';

  @override
  String get prefsAnalyticsTitle => 'Medición de uso';

  @override
  String get prefsDeleteAccount => 'Solicitar eliminación de mi cuenta';

  @override
  String get prefsDeleteAccountHint =>
      'Consulta los pasos y el contacto de Saptain LTD.';

  @override
  String get prefsDiagnosticsBody =>
      'Envía información técnica a Firebase y a Sentry para diagnosticar fallos. Es opcional.';

  @override
  String get prefsDiagnosticsTitle => 'Informes de errores y rendimiento';

  @override
  String get prefsInbox => 'Bandeja de avisos';

  @override
  String get prefsLanguageNote =>
      'El idioma se aplica a toda la app y se guarda como preferencia.';

  @override
  String get prefsNote =>
      'Puedes usar las funciones básicas sin activar medición o diagnóstico. Cambiar estas opciones no borra automáticamente los datos ya enviados.';

  @override
  String get prefsNotificationsOff =>
      'Disponible cuando se complete el acceso con Google.';

  @override
  String get prefsNotificationsOn =>
      'Puedes retirarlas cuando quieras. Los avisos pueden aparecer en la pantalla bloqueada.';

  @override
  String get prefsNotificationsTitle => 'Notificaciones de QuantFut';

  @override
  String get prefsPrivacyRights => 'Privacidad y tus derechos';

  @override
  String get prefsTitle => 'Privacidad y preferencias';

  @override
  String get probBarAway => 'Visita';

  @override
  String get probBarDraw => 'Empate';

  @override
  String get probBarHome => 'Local';

  @override
  String get profileAppVersion => 'Versión de la app';

  @override
  String get profileBalance => 'Balance y seguimiento';

  @override
  String get profileConnected => 'QuantFut · Conectada al servidor';

  @override
  String get profileCreateAccount => 'Crear cuenta';

  @override
  String get profileCreateOne => 'Crear una cuenta';

  @override
  String get profileEmail => 'Correo electrónico';

  @override
  String get profileEmailPending => 'Correo pendiente de verificación';

  @override
  String get profileEmailVerified => 'Correo verificado';

  @override
  String get profileForgot => 'Olvidé mi contraseña';

  @override
  String get profileForgotSent =>
      'Si la cuenta existe, recibirás las instrucciones por correo.';

  @override
  String get profileFreePlan => 'Plan gratuito';

  @override
  String get profileGeneral => 'General';

  @override
  String get profileHaveAccount => 'Ya tengo cuenta';

  @override
  String get profileLanguage => 'Idioma';

  @override
  String get profileMeasurement => 'Medición y errores';

  @override
  String get profileNotifications => 'Notificaciones';

  @override
  String get profileOddsFormat => 'Formato de cuotas';

  @override
  String get profileOddsFormatValue =>
      'Decimal · Cuotas registradas al publicar';

  @override
  String get profilePassword => 'Contraseña';

  @override
  String get profilePreferences => 'Preferencias';

  @override
  String get profileRefreshAccess => 'Actualizar mi acceso';

  @override
  String get profileSeePlans => 'Ver planes VIP';

  @override
  String get profileSendVerification => 'Enviar correo de verificación';

  @override
  String get profileSignIn => 'Iniciar sesión';

  @override
  String get profileSignOut => 'Cerrar sesión';

  @override
  String get profileTitle => 'Perfil y configuración';

  @override
  String profileValidUntil(String date) {
    return 'Vigencia: $date';
  }

  @override
  String get profileVerificationSent => 'Correo de verificación enviado.';

  @override
  String get profileVipActive => 'Acceso VIP activo';

  @override
  String get profileYourAccount => 'Tu cuenta QuantFut';

  @override
  String resultLabel(String score) {
    return 'Resultado: $score';
  }

  @override
  String get rewardsCheckIn => 'Marcar asistencia';

  @override
  String get rewardsCheckInNote =>
      'Una vez por día UTC. Si omites un día, la racha se reinicia.';

  @override
  String get rewardsCodeCopied => 'Código copiado.';

  @override
  String get rewardsCodeRegistered => 'Código de invitación registrado.';

  @override
  String rewardsCopyCode(Object code) {
    return 'Copiar mi código · $code';
  }

  @override
  String rewardsDay(int number) {
    return 'Día $number';
  }

  @override
  String get rewardsDebt => 'Saldo pendiente por recompensas anuladas.';

  @override
  String get rewardsEnough => 'Tienes monedas para un desbloqueo.';

  @override
  String get rewardsGo => 'Ir';

  @override
  String rewardsInviteCondition(Object min) {
    return 'Tras verificar el correo y completar $min monedas en ofertas confirmadas.';
  }

  @override
  String rewardsInviteReward(Object referrer, Object invitee) {
    return 'Tú +$referrer · Tu amigo +$invitee monedas';
  }

  @override
  String get rewardsInviteTitle => 'Invita a tus amigos';

  @override
  String get rewardsInviterCode => 'Código de quien te invitó';

  @override
  String get rewardsLedgerEmpty => 'Todavía no hay movimientos.';

  @override
  String get rewardsLedgerTitle => 'Mis movimientos';

  @override
  String rewardsMissing(int missing) {
    String _temp0 = intl.Intl.pluralLogic(
      missing,
      locale: localeName,
      other: 'Faltan $missing monedas para tu próximo desbloqueo.',
      one: 'Falta $missing moneda para tu próximo desbloqueo.',
    );
    return '$_temp0';
  }

  @override
  String get rewardsMissingUnknown =>
      'Faltan — monedas para tu próximo desbloqueo.';

  @override
  String get rewardsMyCoins => 'Mis monedas';

  @override
  String get rewardsOfferAvailable => 'Ofertas según tu país y dispositivo';

  @override
  String get rewardsOfferPending => 'Pendiente de activar';

  @override
  String get rewardsOffersTitle => 'Ofertas para ganar monedas';

  @override
  String get rewardsOperationDone => 'Operación confirmada.';

  @override
  String rewardsReferralStats(Object registered, Object qualified) {
    return '$registered registrados · $qualified validados';
  }

  @override
  String get rewardsRefreshBalance => 'Actualizar saldo';

  @override
  String get rewardsRegisterCode => 'Registrar código';

  @override
  String get rewardsSignIn => 'Inicia sesión';

  @override
  String get rewardsSignInHint =>
      'Inicia sesión en Perfil para guardar tu saldo, marcar asistencia y usar un código de referido.';

  @override
  String rewardsStreak(int days) {
    String _temp0 = intl.Intl.pluralLogic(
      days,
      locale: localeName,
      other: '$days días',
      one: '$days día',
    );
    return 'Racha de asistencia · $_temp0';
  }

  @override
  String rewardsUnlockFor(Object cost) {
    return 'Desbloquea un pronóstico por $cost monedas';
  }

  @override
  String get selBttsNo => 'No marcan los dos';

  @override
  String get selBttsYes => 'Marcan los dos';

  @override
  String selCards(String side, String line) {
    String _temp0 = intl.Intl.selectLogic(side, {
      'over': 'Más de $line tarjetas',
      'other': 'Menos de $line tarjetas',
    });
    return '$_temp0';
  }

  @override
  String selCorners(String side, String line) {
    String _temp0 = intl.Intl.selectLogic(side, {
      'over': 'Más de $line córners',
      'other': 'Menos de $line córners',
    });
    return '$_temp0';
  }

  @override
  String selCornersTeam(String side, String line, String team) {
    String _temp0 = intl.Intl.selectLogic(side, {
      'over': 'Más de $line córners de $team',
      'other': 'Menos de $line córners de $team',
    });
    return '$_temp0';
  }

  @override
  String selDrawNoBet(String team) {
    return '$team gana (empate devuelve)';
  }

  @override
  String selEitherNoDraw(String home, String away) {
    return '$home o $away (sin empate)';
  }

  @override
  String selGoals(String side, String line) {
    String _temp0 = intl.Intl.selectLogic(side, {
      'over': 'Más de $line goles',
      'other': 'Menos de $line goles',
    });
    return '$_temp0';
  }

  @override
  String selHandicapLong(String team, String line) {
    return '$team $line (hándicap asiático)';
  }

  @override
  String selHandicapShort(String team, String line) {
    return '$team $line';
  }

  @override
  String selHomeWins(String team) {
    return 'Gana $team';
  }

  @override
  String get selHtBttsNo => 'No marcan los dos en el 1T';

  @override
  String get selHtGoalYes => 'Habrá gol en el 1T';

  @override
  String selTeamOrDraw(String team) {
    return '$team o empate';
  }

  @override
  String selTeamScores(String team) {
    return 'Marca $team';
  }

  @override
  String selWinToNil(String team) {
    return '$team gana sin recibir gol';
  }

  @override
  String get shellNewAlert => 'Nuevo aviso de QuantFut';

  @override
  String get shellSignInForCoins =>
      'Inicia sesión en Perfil para usar tus monedas.';

  @override
  String shellUnlockBody(Object cost) {
    return 'Se descontarán $cost monedas de tu saldo. El acceso corresponde a este pronóstico.';
  }

  @override
  String get shellUnlockTitle => 'Desbloquear pronóstico';

  @override
  String get shellView => 'Ver';

  @override
  String get splashTagline => 'FÚTBOL · NBA · ESTADÍSTICA';

  @override
  String get startupFailed =>
      'No pudimos iniciar QuantFut. Inténtalo de nuevo.';

  @override
  String get startupLoading => 'Iniciando QuantFut';

  @override
  String statAveragesNote(Object homeN, Object awayN) {
    return 'Promedios de $homeN partidos del local y $awayN del visitante. La cobertura de remates, córners y xG puede ser parcial.';
  }

  @override
  String get statBestAway => 'Mejor triunfo fuera';

  @override
  String get statBestHome => 'Mejor triunfo en casa';

  @override
  String get statCleanSheet => 'Portería a cero';

  @override
  String get statCompareNote =>
      'Las barras comparan los valores registrados; no representan probabilidades de victoria. Menos goles recibidos es mejor.';

  @override
  String get statCompareTitle => 'Comparación de equipos';

  @override
  String get statDrawStreak => 'Racha de empates';

  @override
  String get statFormLegend =>
      'G: ganado · E: empate · P: perdido. Más reciente a la izquierda.';

  @override
  String get statFormNA => 'Forma no disponible.';

  @override
  String get statFormTitle => 'Forma de los equipos';

  @override
  String get statGoalsAgainst => 'Goles recibidos';

  @override
  String get statGoalsAvgNote =>
      'Goles a favor por partido; no es la proyección de goles del modelo.';

  @override
  String get statGoalsAvgTitle => 'PROMEDIO HISTÓRICO DE GOLES';

  @override
  String get statGoalsFor => 'Goles a favor';

  @override
  String statH2hSummary(
    Object n,
    Object home,
    Object homeWins,
    Object away,
    Object awayWins,
    Object draws,
  ) {
    return 'En $n cruces registrados: $home ganó $homeWins, $away ganó $awayWins y hubo $draws empates.';
  }

  @override
  String get statH2hTitle => 'Cara a cara';

  @override
  String statLastMatches(int count) {
    return 'Últimos $count partidos registrados';
  }

  @override
  String get statMinutesNA =>
      'La distribución por minutos no está disponible para este partido.';

  @override
  String get statMinutesTitle => 'Goles por minuto';

  @override
  String get statNeedsAccess =>
      'El pronóstico de este partido requiere acceso VIP o un desbloqueo con monedas.';

  @override
  String get statOnTargetShort => 'A puerta';

  @override
  String get statOver25 => 'Más de 2,5 goles';

  @override
  String statPickProbOdds(String percent, String odds) {
    return 'Probabilidad $percent · Cuota @ $odds';
  }

  @override
  String statPlayed(Object played) {
    return '$played partidos';
  }

  @override
  String statPoints(Object points) {
    return '$points puntos';
  }

  @override
  String get statPoissonNA =>
      'La distribución Poisson y los marcadores probables aún no están disponibles en la entrega de este partido.';

  @override
  String get statPoissonTitle => 'Distribución de goles Poisson';

  @override
  String statPosition(Object position) {
    return 'Posición $position';
  }

  @override
  String get statProbNA => 'Probabilidades del modelo todavía no disponibles.';

  @override
  String get statProbTitle => 'PROBABILIDAD DE VICTORIA · 1X2';

  @override
  String get statPublishedPick => 'PRONÓSTICO PUBLICADO';

  @override
  String get statRadarNeeds =>
      'La comparación gráfica necesita al menos tres métricas disponibles de ambos equipos.';

  @override
  String get statRadarNote =>
      'Escala relativa por eje. Un área mayor no implica mayor probabilidad de ganar.';

  @override
  String get statResDraw => 'E';

  @override
  String get statResLoss => 'P';

  @override
  String get statResWin => 'G';

  @override
  String statResultsAvailable(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count resultados disponibles',
      one: '$count resultado disponible',
    );
    return '$_temp0';
  }

  @override
  String get statSeasonTitle => 'Temporada y resultados recientes';

  @override
  String get statShots => 'Remates';

  @override
  String get statShotsOnTarget => 'Remates a puerta';

  @override
  String get statStandingNA => 'Clasificación no disponible.';

  @override
  String get statSummaryTitle => 'Resumen de predicción';

  @override
  String get statTeamStatsTitle => 'Estadísticas del equipo';

  @override
  String get statWinStreak => 'Racha de victorias';

  @override
  String get statXgHistoric => 'xG histórico';

  @override
  String get streamHighProb => 'Alta probabilidad';

  @override
  String get streamLadder => 'Reto Escalera';

  @override
  String get streamParley => 'Parley';

  @override
  String tileFairOdds(String value) {
    return 'Cuota justa $value';
  }

  @override
  String get tileFavorite => 'Favorito 1X2';

  @override
  String tileFavoriteLead(String team, int pts) {
    return '$team · +$pts pts';
  }

  @override
  String get tileFavoriteNA => 'Probabilidades no disponibles';

  @override
  String get tileGoalsNA => 'Historial insuficiente';

  @override
  String get tileGoalsTrend => 'Tendencia goles';

  @override
  String get tileOver25Model => 'Más de 2,5 según el modelo';

  @override
  String get tileOver25Recent => 'Más de 2,5 en sus últimos partidos';

  @override
  String get tileProbability => 'Probabilidad';

  @override
  String get tileXg => 'xG proyectado';

  @override
  String tileXgCaption(String home, String away) {
    return '$home local · $away visita';
  }

  @override
  String get tileXgNA => 'Disponible en mercados de goles';

  @override
  String get titleAsianHandicap => 'Hándicap asiático';

  @override
  String get titleDrawNoBet => 'Empate no acción';

  @override
  String titleTeamGoals(String team) {
    return 'Goles de $team';
  }

  @override
  String get titleTotalCards => 'Tarjetas totales';

  @override
  String get titleTotalCorners => 'Córners totales';

  @override
  String get titleTotalGoals => 'Goles totales';

  @override
  String get titleWinner => 'Ganador del partido';

  @override
  String get tooltipVip => 'VIP';

  @override
  String get vipActivate => 'Activar acceso VIP';

  @override
  String get vipActive => 'Tu acceso VIP está activo.';

  @override
  String get vipBadge => '✦  ACCESO VIP';

  @override
  String get vipBenefit1Body => 'Cada pronóstico se sella antes del partido';

  @override
  String get vipBenefit1Title => 'Historial verificable';

  @override
  String vipBenefit2Body(int min, int max) {
    return 'Todos los picks de $min a $max %, sin cupo gratuito';
  }

  @override
  String get vipBenefit2Title => 'Alta Probabilidad completa';

  @override
  String get vipBenefit3Body => 'Todos los escalones pendientes, no solo uno';

  @override
  String get vipBenefit3Title => 'Reto Escalera completo';

  @override
  String get vipBenefit4Body =>
      'Cuota publicada, probabilidad y xG de cada pick';

  @override
  String get vipBenefit4Title => 'Cuotas y análisis del partido';

  @override
  String get vipBestPrice => '★ MEJOR PRECIO';

  @override
  String get vipCheckAccess => 'Comprobar mi acceso';

  @override
  String get vipCheckSignIn =>
      'Inicia sesión en Perfil para comprobar tu acceso.';

  @override
  String vipDays(int days) {
    String _temp0 = intl.Intl.pluralLogic(
      days,
      locale: localeName,
      other: '$days días',
      one: '$days día',
    );
    return '$_temp0';
  }

  @override
  String get vipFreeAccess => 'Tu cuenta tiene acceso gratuito.';

  @override
  String get vipHistoryNote =>
      'Historial público y sellado; las muestras por mercado son pequeñas y un pronóstico puede fallar.';

  @override
  String get vipIntro =>
      'Todos los pronósticos de Alta Probabilidad y del Reto Escalera mientras tu suscripción esté vigente.';

  @override
  String get vipLinked => '🔒  Tu acceso VIP queda vinculado a tu cuenta';

  @override
  String vipMonthly(String amount) {
    return '≈ $amount/mes';
  }

  @override
  String vipMonths(int months) {
    String _temp0 = intl.Intl.pluralLogic(
      months,
      locale: localeName,
      other: '$months meses',
      one: '$months mes',
    );
    return '$_temp0';
  }

  @override
  String get vipNoExpiry => 'Sin vencimiento';

  @override
  String get vipPaymentRequired =>
      'La contratación requiere un canal de pago configurado.';

  @override
  String get vipPickLabel => 'Pronóstico VIP';

  @override
  String get vipPlansSoon =>
      'Los planes se mostrarán cuando estén disponibles.';

  @override
  String get vipPricesNote => 'Precios del catálogo del servidor.';

  @override
  String get vipPurchasesPending =>
      'Compras en preparación: aún no se cobra nada desde la app.';

  @override
  String get vipStatRecorded => 'Acierto registrado';

  @override
  String get vipStatResolved => 'Resueltos';

  @override
  String get welcome1Body =>
      'Descubre el lado estadístico del deporte: partidos, análisis y pronósticos del proyecto que ya conoces en la web.';

  @override
  String get welcome1Title => 'Fútbol y NBA,\ncon otra perspectiva';

  @override
  String get welcome2Body =>
      'La forma reciente, el cara a cara y las estadísticas ayudan a entender lo que puede pasar. Empieza por los datos.';

  @override
  String get welcome2Title => 'Cada partido,\ncon más contexto';

  @override
  String get welcome3Body =>
      'Goles, córners, hándicap y estadísticas de la NBA. Conoce qué mide cada análisis antes de interpretar una selección.';

  @override
  String get welcome3Title => 'Más mercados.\nMás información.';

  @override
  String get welcome4Body =>
      'Un pronóstico también se entiende después del partido. El historial permite comparar estimaciones con resultados.';

  @override
  String get welcome4Title => 'Los resultados,\na la vista';

  @override
  String get welcome5Body =>
      'Una probabilidad no es una certeza. Explora el contenido, revisa el contexto y forma tu propio criterio.';

  @override
  String get welcome5Title => 'Todo empieza\npor informarte';

  @override
  String welcomeGoTo(int number) {
    return 'Ir a bienvenida $number';
  }

  @override
  String get welcomeNext => 'Siguiente';

  @override
  String welcomeScreenOf(int page, int total) {
    return 'Pantalla $page de $total';
  }

  @override
  String get welcomeSkip => 'Saltar';

  @override
  String get welcomeStart => 'Empezar';
}
