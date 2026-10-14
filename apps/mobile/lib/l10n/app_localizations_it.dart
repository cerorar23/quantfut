// ignore: unused_import
import 'package:intl/intl.dart' as intl;

import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Italian (`it`).
class AppLocalizationsIt extends AppLocalizations {
  AppLocalizationsIt([String locale = 'it']) : super(locale);

  @override
  String get accessBody1 =>
      'Un modello statistico calcola le probabilità. Una probabilità non è una certezza.';

  @override
  String get accessBody2 =>
      'Ogni giorno, i più probabili, con il loro tasso di successo storico reale.';

  @override
  String get accessBody3 =>
      'Segui l\'avanzamento di ogni sfida e quanto manca per completarla.';

  @override
  String get accessBody4 =>
      'Con la sua quota e la probabilità congiunta, per sapere cosa rischi.';

  @override
  String get accessBody5 =>
      'Segna la presenza, completa le offerte e invita gli amici per sbloccare i pronostici.';

  @override
  String get accessCardBody =>
      'Conserva i tuoi progressi e le tue monete su tutti i dispositivi.';

  @override
  String get accessCardTitle => 'Accedi per continuare';

  @override
  String get accessConsent =>
      'Ho almeno 18 anni e accetto i termini e l\'informativa sulla privacy.';

  @override
  String get accessConsentNeeded => 'Seleziona la casella per continuare.';

  @override
  String accessConsentRich(String terms, String privacy) {
    return 'Ho almeno 18 anni e accetto: $terms e $privacy.';
  }

  @override
  String get accessContinueWithGoogle => 'Continua con Google';

  @override
  String get accessDisclaimer =>
      'Solo a scopo informativo e di intrattenimento. I pronostici non garantiscono risultati.';

  @override
  String get accessDocumentOpenError => 'Impossibile aprire il documento.';

  @override
  String get accessForgotLink => 'Recupera la password precedente';

  @override
  String get accessForgotSent =>
      'Se l\'account esiste, riceverai le istruzioni via e-mail.';

  @override
  String get accessGenericError =>
      'Impossibile completare l\'accesso. Riprova.';

  @override
  String get accessGoogleError => 'Impossibile accedere con Google. Riprova.';

  @override
  String get accessKicker1 => 'PROBABILITÀ REALI';

  @override
  String get accessKicker2 => 'ALTA PROBABILITÀ';

  @override
  String get accessKicker3 => 'SFIDA SCALA';

  @override
  String get accessKicker4 => 'MULTIPLA';

  @override
  String get accessKicker5 => 'MONETE';

  @override
  String get accessLinkButton => 'Collega il mio account';

  @override
  String get accessLinkEmail => 'E-mail del tuo account precedente';

  @override
  String get accessLinkIntro =>
      'Collega il tuo account precedente per conservare saldo e accesso.';

  @override
  String get accessLinkPassword => 'Password precedente';

  @override
  String get accessOtherAccount => 'Usa un altro account';

  @override
  String get accessPreparingDocs => 'Stiamo preparando i documenti di accesso.';

  @override
  String get accessPrivacy => 'Informativa sulla privacy';

  @override
  String get accessRetry => 'Riprova l\'accesso';

  @override
  String get accessTagline =>
      'Partite, analisi e storico. Una probabilità non è una certezza.';

  @override
  String get accessTerms => 'Termini di utilizzo';

  @override
  String get accessTitle1 => 'Capisci ogni partita con i dati.';

  @override
  String get accessTitle2 => 'Pronostici con il tasso di successo in vista.';

  @override
  String get accessTitle3 => 'Sali gradino dopo gradino.';

  @override
  String get accessTitle4 => 'Un biglietto sigillato prima delle partite.';

  @override
  String get accessTitle5 => 'Guadagna monete e sblocca.';

  @override
  String alertsAbsencesOf(String team) {
    return 'Assenze di $team';
  }

  @override
  String get alertsAdvantage => 'Vantaggio';

  @override
  String get alertsAdvantageEmpty => 'Nessun vantaggio segnalato.';

  @override
  String alertsChecked(String when) {
    return 'Verificato $when';
  }

  @override
  String get alertsDisadvantage => 'Svantaggio';

  @override
  String get alertsDisadvantageEmpty => 'Nessuno svantaggio segnalato.';

  @override
  String get alertsDoubt => 'Dubbio';

  @override
  String get alertsNoCheck =>
      'Non c\'è ancora un controllo delle assenze per questa partita. Se il suo campionato non ha questo dato, non significa che non ci siano infortunati.';

  @override
  String get alertsNote =>
      'Le assenze possono cambiare fino al calcio d\'inizio. La formazione ufficiale esce poco prima della partita.';

  @override
  String get alertsOut => 'Indisponibile';

  @override
  String get alertsReasonFoot => 'Infortunio a caviglia o piede';

  @override
  String get alertsReasonIllness => 'Malattia';

  @override
  String get alertsReasonInjury => 'Infortunio';

  @override
  String get alertsReasonKnee => 'Infortunio al ginocchio';

  @override
  String get alertsReasonKnock => 'Colpo';

  @override
  String get alertsReasonMuscle => 'Infortunio muscolare';

  @override
  String get alertsReasonSuspension => 'Squalifica';

  @override
  String get alertsReasonUnknown => 'Motivo non indicato';

  @override
  String get alertsSource => 'Fonte: API-Football';

  @override
  String alertsSummary(int out, int doubt) {
    String _temp0 = intl.Intl.pluralLogic(
      out,
      locale: localeName,
      other: '$out assenze',
      one: '1 assenza',
    );
    String _temp1 = intl.Intl.pluralLogic(
      doubt,
      locale: localeName,
      other: '$doubt dubbi',
      one: '1 dubbio',
    );
    return '$_temp0 · $_temp1';
  }

  @override
  String get alertsSuspended => 'Squalificato';

  @override
  String get apiGoogleNotVerified =>
      'Google non è riuscito a verificare l\'accesso.';

  @override
  String get apiInvalidResponse => 'Risposta non valida dal server.';

  @override
  String get apiInvalidSession => 'Sessione non valida.';

  @override
  String apiLoadFailed(int status) {
    return 'Impossibile caricare le informazioni (HTTP $status).';
  }

  @override
  String get apiOffline =>
      'Impossibile connettersi. Controlla la connessione e riprova.';

  @override
  String get apiSessionExpired => 'Accedi di nuovo.';

  @override
  String get apiSignInWithGoogle => 'Accedi con Google.';

  @override
  String get artAnalyzeEach => 'ANALIZZA OGNI SELEZIONE';

  @override
  String get artCorners => 'CORNER';

  @override
  String get artFootball => 'CALCIO';

  @override
  String get artForm => 'FORMA';

  @override
  String get artGoals => 'GOL';

  @override
  String get artHeadToHead => 'TESTA A TESTA';

  @override
  String get artHeading0 => 'CALCIO + NBA';

  @override
  String get artHeading1 => 'IL CONTESTO CONTA';

  @override
  String get artHeading2 => 'ESPLORA I MERCATI';

  @override
  String get artHeading3 => 'STORICO A PORTATA';

  @override
  String get artHeading4 => 'DATI + IL TUO GIUDIZIO';

  @override
  String get artNba => 'NBA';

  @override
  String get artStats => 'STATISTICHE';

  @override
  String get artTagline => 'ANALIZZA. CONFRONTA. ESPLORA.';

  @override
  String get artTransparency => 'TRASPARENZA';

  @override
  String get bannerLive =>
      'PARTITA IN CORSO · pronostico sigillato prima dell\'inizio';

  @override
  String bannerLost(String score) {
    return 'PERSO$score · pronostico sigillato prima dell\'inizio';
  }

  @override
  String bannerWon(String score) {
    return 'VINTO$score · pronostico sigillato prima dell\'inizio';
  }

  @override
  String get calendarEmpty => 'Nessun incontro per questi filtri.';

  @override
  String calendarMatchesCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count incontri',
      one: '$count incontro',
    );
    return '$_temp0';
  }

  @override
  String get calendarPickDate => 'Scegli la data';

  @override
  String get calendarSearchHint => 'Cerca squadre o campionati';

  @override
  String get calendarTitle => 'Calendario · ora locale';

  @override
  String casesCount(int count, String formatted) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$formatted casi',
      one: '$formatted caso',
    );
    return '$_temp0';
  }

  @override
  String get commonAll => 'Tutti';

  @override
  String get commonAway => 'Ospite';

  @override
  String get commonCancel => 'Annulla';

  @override
  String get commonClose => 'Chiudi';

  @override
  String get commonConfirm => 'Conferma';

  @override
  String get commonConnecting => 'Connessione…';

  @override
  String get commonDraw => 'Pareggio';

  @override
  String get commonHome => 'Casa';

  @override
  String get commonRefresh => 'Aggiorna';

  @override
  String get commonRetry => 'Riprova';

  @override
  String get commonSeeVip => 'Vedi accesso VIP';

  @override
  String get commonToday => 'Oggi';

  @override
  String get commonYesterday => 'Ieri';

  @override
  String countdownDays(int days, String time) {
    return '${days}g $time';
  }

  @override
  String detailChecked(String date) {
    return 'Verificato: $date';
  }

  @override
  String get detailFormationPending => 'Modulo in attesa';

  @override
  String get detailH2hTitle => 'Scontri diretti (H2H)';

  @override
  String get detailInjuries => 'Assenze segnalate';

  @override
  String get detailLineups => 'Formazioni';

  @override
  String get detailLineupsPending => 'Formazioni non ancora confermate.';

  @override
  String get detailNoH2h =>
      'Non ci sono scontri registrati per questa partita.';

  @override
  String get detailNoInjuries => 'Nessuna assenza nel rapporto disponibile.';

  @override
  String get detailNoInjuriesCheck =>
      'Non è disponibile alcun controllo delle assenze.';

  @override
  String get detailNoPicks =>
      'Non ci sono pronostici pubblicati per questa partita.';

  @override
  String get detailNoStarters => 'Nessun titolare confermato.';

  @override
  String get detailReferee => 'Arbitro';

  @override
  String get detailRefereePending => 'Arbitro da confermare.';

  @override
  String get detailTabAlerts => 'Avvisi';

  @override
  String get detailTabH2h => 'H2H';

  @override
  String get detailTabPredictions => 'Pronostici';

  @override
  String get detailTabStats => 'Analisi';

  @override
  String get detailVipPickNotice => 'Questa partita ha un pronostico VIP';

  @override
  String get dictAwayDefault => 'la squadra ospite';

  @override
  String get dictHomeDefault => 'la squadra di casa';

  @override
  String dictOddsAbove(String fair) {
    return 'La quota pubblicata supera la quota giusta ($fair).';
  }

  @override
  String dictOddsBelow(String fair) {
    return 'La quota pubblicata è inferiore alla quota giusta ($fair); il pregio sta nella probabilità, non nel prezzo.';
  }

  @override
  String dictPick(String pick, String percent) {
    return '$pick con probabilità calcolata del $percent.';
  }

  @override
  String get dictPickDefault => 'Il pronostico';

  @override
  String dictXg(
    String total,
    String home,
    String homeXg,
    String away,
    String awayXg,
  ) {
    return 'Le quote di mercato senza margine implicano $total gol attesi ($home $homeXg · $away $awayXg).';
  }

  @override
  String get disclaimerProbability =>
      'Una probabilità non è una certezza. Decidi con consapevolezza e gioca responsabilmente.';

  @override
  String get factsAbsences => 'Assenze';

  @override
  String get factsDrew => 'Pareggiò';

  @override
  String get factsHideLineup => 'Nascondi gli undici';

  @override
  String factsInCompetition(String competition) {
    return 'In $competition';
  }

  @override
  String get factsLastLineup => 'Ultima formazione nota';

  @override
  String get factsLastMatch => 'Ultima partita';

  @override
  String factsLineupMeta(String rival, String date) {
    return 'contro $rival · $date';
  }

  @override
  String get factsLineupNote =>
      'È la formazione di quella partita, non una previsione per quella di oggi.';

  @override
  String get factsLost => 'Perse';

  @override
  String get factsNoLineup => 'Nessuna formazione salvata per ora.';

  @override
  String get factsNoResult => 'Nessuna partita precedente registrata.';

  @override
  String get factsSeeAlerts => 'Vedi gli avvisi';

  @override
  String get factsShowLineup => 'Mostra gli undici';

  @override
  String get factsTitle => 'Dati della partita';

  @override
  String factsVs(String score, String rival) {
    return '$score contro $rival';
  }

  @override
  String get factsWon => 'Vinse';

  @override
  String get famCardsSubtitle =>
      'Linee di meno cartellini con supporto storico';

  @override
  String get famCardsTitle => 'Cartellini';

  @override
  String get famCornersSubtitle => 'Più e meno corner dell\'intera partita';

  @override
  String get famCornersTeamSubtitle =>
      'Casa e ospite, ciascuno con la propria linea';

  @override
  String get famCornersTeamTitle => 'Corner per squadra';

  @override
  String get famCornersTitle => 'Corner totali';

  @override
  String get famDoubleChanceSubtitle =>
      'Due risultati possibili in una selezione';

  @override
  String get famDoubleChanceTitle => 'Doppia chance';

  @override
  String get famGoalsSubtitle => 'Totali con linee valutate storicamente';

  @override
  String get famGoalsTitle => 'Gol della partita';

  @override
  String get famHandicapSubtitle =>
      'Linee di protezione e pareggio con rimborso';

  @override
  String get famHandicapTitle => 'Handicap asiatico';

  @override
  String get famNbaSubtitle =>
      'Valutazione esplorativa · in attesa di conferma';

  @override
  String get famNbaTeamTitle => 'NBA · Punti di squadra';

  @override
  String get famNbaTotalTitle => 'NBA · Totale della partita';

  @override
  String get famNbaWinnerTitle => 'NBA · Vincitore';

  @override
  String get famTeamGoalsSubtitle =>
      'Almeno un gol della squadra di casa o ospite';

  @override
  String get famTeamGoalsTitle => 'Segna una squadra';

  @override
  String get famWinnerSubtitle => 'Risultato 1X2 ad alta probabilità';

  @override
  String get famWinnerTitle => 'Vincitore della partita';

  @override
  String get featAgenda => 'Calendario temporaneamente non disponibile';

  @override
  String get featBalance => 'Monitoraggio in preparazione';

  @override
  String get featCommunity => 'Community in preparazione';

  @override
  String get featLanguages => 'Traduzioni in preparazione';

  @override
  String get featMatchData =>
      'Dati della partita temporaneamente non disponibili';

  @override
  String get featMeasurement => 'Misurazione in preparazione';

  @override
  String get featNba => 'Modello NBA in addestramento';

  @override
  String get featNotifications => 'Notifiche in preparazione';

  @override
  String get featPurchases => 'Acquisti in preparazione';

  @override
  String get featStats => 'Statistiche temporaneamente non disponibili';

  @override
  String get featVip => 'Accesso VIP temporaneamente non disponibile';

  @override
  String get featureTraining => 'Modello in addestramento';

  @override
  String get fixtureFinished => 'TERMINATA';

  @override
  String get fixtureLive => 'IN DIRETTA';

  @override
  String get fixtureLocalTime => 'ORA LOCALE';

  @override
  String get fixtureStartsIn => 'INIZIA TRA';

  @override
  String get fixtureTbd => 'DA CONFERMARE';

  @override
  String get forecastCanFail =>
      'Un pronostico può sbagliare; la probabilità non garantisce il risultato.';

  @override
  String get forecastFeatured => 'IN EVIDENZA';

  @override
  String get forecastFree => 'GRATUITO';

  @override
  String get forecastHalfTime => 'INTERVALLO';

  @override
  String get forecastInPlay => 'IN CORSO';

  @override
  String get forecastLiveScore => 'Risultato in diretta';

  @override
  String forecastLiveScoreAgo(int minutes) {
    return 'Risultato in diretta · aggiornato $minutes min fa';
  }

  @override
  String get forecastMarketNote =>
      'Probabilità calcolate con le quote di mercato senza margine: questo campionato non ha un modello proprio.';

  @override
  String get forecastOddsAtPublish => 'Quota alla pubblicazione';

  @override
  String forecastProbCalc(String percent) {
    return '$percent prob. calcolata';
  }

  @override
  String get forecastSeeStats => 'Vedi le statistiche della partita';

  @override
  String get forecastSourceMarket => 'QUOTE DI MERCATO';

  @override
  String get forecastSourceModel => 'MODELLO PROPRIO';

  @override
  String get forecastTitle => 'ANALISI STATISTICA';

  @override
  String get forecastUnlocked => 'SBLOCCATO';

  @override
  String get forecastVerdictTitle => '💡  VERDETTO DEL MODELLO';

  @override
  String get formatScheduleUnavailable => 'Orario non disponibile';

  @override
  String get groupBtts => 'ENTRAMBE SEGNANO';

  @override
  String get groupCards => 'CARTELLINI';

  @override
  String get groupCorners => 'CORNER';

  @override
  String get groupDoubleChance => 'DOPPIA CHANCE';

  @override
  String get groupDrawNoBet => 'PAREGGIO RIMBORSATO';

  @override
  String get groupFirstHalf => '1º TEMPO';

  @override
  String get groupGoals => 'GOL';

  @override
  String get groupHandicap => 'HANDICAP';

  @override
  String get groupResult => 'RISULTATO';

  @override
  String get groupSpecials => 'SPECIALI';

  @override
  String get groupTeamGoals => 'GOL DI SQUADRA';

  @override
  String get guideBody1 =>
      'Se un pronostico ha il 75% di probabilità, il modello si aspetta che si avveri circa 3 volte su 4 quando una situazione simile si ripete. Significa che 1 volta su 4 non si avvererà. Nessun dato garantisce un risultato preciso.';

  @override
  String get guideBody2 =>
      'La quota è fissata da un bookmaker e include il suo margine. Confrontare la probabilità del modello con quella implicita nella quota aiuta a capire se il prezzo è ragionevole; non assicura il risultato.';

  @override
  String get guideBody3 =>
      'Vengono pubblicati con la loro probabilità e la quota di riferimento prima del calcio d\'inizio e non possono essere modificati. Per questo puoi confrontare il tasso di successo storico reale con quello promesso.';

  @override
  String get guideBody4 =>
      'In una multipla la probabilità congiunta è il prodotto di quella di ogni selezione, quindi scende in fretta aggiungendo partite. Una quota alta di solito riflette proprio questo.';

  @override
  String get guideBody5 =>
      'Ogni sfida procede per passi e il successivo conta solo se il precedente è stato rispettato. Guarda l\'avanzamento e lo storico, comprese le sfide fallite, prima di seguirne una.';

  @override
  String get guideBody6 =>
      'QuantFut non è un bookmaker e non assicura guadagni. Se decidi di scommettere, usa solo denaro che puoi permetterti di perdere e solo se sei maggiorenne. Se il gioco smette di essere un passatempo, chiedi aiuto.';

  @override
  String get guideHead1 => 'Una probabilità non è una certezza';

  @override
  String get guideHead2 => 'La quota è un prezzo, non l\'opinione del modello';

  @override
  String get guideHead3 => 'Ogni pronostico è sigillato prima della partita';

  @override
  String get guideHead4 => 'Più selezioni, meno probabilità';

  @override
  String get guideHead5 => 'Si sale un gradino alla volta';

  @override
  String get guideHead6 => 'È informazione e intrattenimento';

  @override
  String get guideSubtitle => 'Impara a leggere i dati prima di decidere.';

  @override
  String get guideTitle => 'Guida ai pronostici';

  @override
  String get guideTopic1 => 'PROBABILITÀ';

  @override
  String get guideTopic2 => 'QUOTA';

  @override
  String get guideTopic3 => 'ALTA PROBABILITÀ';

  @override
  String get guideTopic4 => 'MULTIPLA';

  @override
  String get guideTopic5 => 'SFIDA SCALA';

  @override
  String get guideTopic6 => 'RESPONSABILITÀ';

  @override
  String get homeBannerClose => 'Chiudi l\'avviso';

  @override
  String get homeByDate => 'Partite per data e orario';

  @override
  String homeForecastAt(String when, String mexico) {
    return 'Pronostico il $when ($mexico ora del Messico)';
  }

  @override
  String get homeForecastPending => 'Pronostico in attesa';

  @override
  String get homeMenuTooltip => 'Menu';

  @override
  String get homeNoMatchesDay => 'Nessuna partita in questo giorno.';

  @override
  String get homeSeeAll => 'Vedi tutto';

  @override
  String homeTicketJoint(String percent) {
    return 'Prob. congiunta $percent';
  }

  @override
  String homeTicketLegs(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count selezioni',
      one: '$count selezione',
    );
    return '$_temp0';
  }

  @override
  String homeTicketOdds(String value) {
    return 'Quota $value';
  }

  @override
  String get homeTicketsEmpty => 'Ancora nessun biglietto oggi';

  @override
  String get homeTicketsTitle => 'Biglietti del giorno';

  @override
  String get homeToday => 'Oggi';

  @override
  String get homeTomorrow => 'Domani';

  @override
  String get inboxEmpty => 'Non hai ancora avvisi.';

  @override
  String get inboxMatch => 'Partita';

  @override
  String get inboxTitle => 'Avvisi';

  @override
  String ladderActiveCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count sfide in corso',
      one: '1 sfida in corso',
    );
    return '$_temp0';
  }

  @override
  String get ladderBalance => 'saldo attuale';

  @override
  String get ladderChance => 'di completarlo';

  @override
  String get ladderEmpty => 'Non ci sono sfide attive pubblicate.';

  @override
  String ladderEstimateNote(String avg) {
    return 'Stima: usa la probabilità del gradino in gioco e la media degli altri ($avg). Non è una garanzia.';
  }

  @override
  String get ladderFreeHint =>
      'Un gradino gratuito: quello a maggiore probabilità.';

  @override
  String get ladderHideSteps => 'Nascondi i gradini';

  @override
  String get ladderHistoryDone => 'Completata';

  @override
  String get ladderHistoryEmpty =>
      'Non ci sono ancora sfide chiuse. Quando una finisce, comparirà qui con il suo risultato.';

  @override
  String ladderHistoryFailedAt(int step) {
    return 'Fallita al gradino $step';
  }

  @override
  String ladderHistoryRate(String rate) {
    return 'Tasso di completamento: $rate';
  }

  @override
  String ladderHistoryResult(String roi) {
    return 'Risultato cumulato: $roi';
  }

  @override
  String ladderHistorySummary(int done, int closed) {
    return '$done completate su $closed chiuse';
  }

  @override
  String get ladderHistoryTitle => 'Storico delle sfide';

  @override
  String get ladderNoteInPlay =>
      'Un gradino attende il risultato. La sfida è ancora viva.';

  @override
  String get ladderNoteToPick =>
      'Manca da scegliere il prossimo gradino; può richiedere giorni. La sfida è ancora viva.';

  @override
  String ladderRemaining(int remaining) {
    String _temp0 = intl.Intl.pluralLogic(
      remaining,
      locale: localeName,
      other: 'ne mancano $remaining',
      one: 'ne manca 1',
    );
    return '$_temp0';
  }

  @override
  String get ladderShowSteps => 'Mostra i gradini';

  @override
  String get ladderStatusInPlay => 'In gioco';

  @override
  String get ladderStatusToPick => 'Da scegliere';

  @override
  String ladderTitle(Object id, int steps) {
    String _temp0 = intl.Intl.pluralLogic(
      steps,
      locale: localeName,
      other: '$steps gradini',
      one: '$steps gradino',
    );
    return 'Sfida #$id · $_temp0';
  }

  @override
  String ladderWonOf(int won, int goal) {
    return '$won su $goal vinti';
  }

  @override
  String get languageFirstBadge => 'Configurazione della lingua';

  @override
  String get languageFirstHint =>
      'Imposta la lingua dell\'analisi per un\'esperienza migliore';

  @override
  String get languageFirstTitle => 'Seleziona la tua lingua';

  @override
  String get languageHint =>
      'Scegli la lingua. Viene salvata su questo dispositivo e nel tuo account.';

  @override
  String get languageTitle => 'Lingua dell\'app';

  @override
  String get ledgerAttendance => 'Presenza';

  @override
  String get ledgerInvitee => 'Premio di benvenuto';

  @override
  String get ledgerOffer => 'Offerta completata';

  @override
  String get ledgerReferralReversal => 'Premio invito annullato';

  @override
  String get ledgerReferrer => 'Premio per l\'invito';

  @override
  String get ledgerReversal => 'Offerta annullata';

  @override
  String get ledgerUnlock => 'Pronostico sbloccato';

  @override
  String get levelHigh => 'ALTA PROB.';

  @override
  String get levelModerate => 'MODERATA';

  @override
  String get levelSolid => 'SOLIDA';

  @override
  String get lineAwayScores => 'Segna la squadra ospite · più di 0,5 gol';

  @override
  String get lineDoubleChance => 'Doppia chance · 1X / X2 / 12';

  @override
  String lineHandicap(String line) {
    return 'Handicap $line';
  }

  @override
  String get lineHomeScores => 'Segna la squadra di casa · più di 0,5 gol';

  @override
  String lineTeamCorners(String team, String side, String line) {
    String _temp0 = intl.Intl.selectLogic(side, {
      'over': 'più di $line corner',
      'other': 'meno di $line corner',
    });
    return '$team: $_temp0';
  }

  @override
  String get lineWinner => 'Vincitore · selezione ad alta probabilità';

  @override
  String get maintenanceNotice =>
      'Stiamo eseguendo la manutenzione. Alcune funzioni potrebbero richiedere più tempo.';

  @override
  String get marketAwayScores => 'Segna la squadra ospite';

  @override
  String get marketBtts => 'Entrambe segnano';

  @override
  String get marketCards => 'Cartellini';

  @override
  String get marketCorners => 'Corner';

  @override
  String get marketCornersAway => 'Corner della squadra ospite';

  @override
  String get marketCornersHome => 'Corner della squadra di casa';

  @override
  String get marketDoubleChance => 'Doppia chance';

  @override
  String get marketGoals => 'Gol';

  @override
  String get marketGoalsAway => 'Gol della squadra ospite';

  @override
  String get marketGoalsHome => 'Gol della squadra di casa';

  @override
  String get marketHandicap => 'Handicap';

  @override
  String get marketHomeScores => 'Segna la squadra di casa';

  @override
  String get marketHtBtts => 'Entrambe segnano nel 1º tempo';

  @override
  String get marketHtGoal => 'Gol nel 1º tempo';

  @override
  String get marketResult1x2 => 'Risultato 1X2';

  @override
  String get marketUnknown => 'Mercato';

  @override
  String get marketWinToNil => 'Vince senza subire gol';

  @override
  String get marketsAndResults => 'Mercati e risultati';

  @override
  String marketsEvidenceAt(String date) {
    return 'Evidenza al $date';
  }

  @override
  String get marketsFamiliesRadar => 'famiglie di mercato nel radar';

  @override
  String marketsHistoricHit(String percent) {
    return 'successo storico $percent';
  }

  @override
  String get marketsInReview => 'In revisione: nessuna linea confermata';

  @override
  String get marketsModelActive => 'MODELLO ATTIVO';

  @override
  String get marketsNoLineLabel => 'nessuna linea confermata';

  @override
  String get marketsNoPublications => 'Ancora nessuna pubblicazione';

  @override
  String get marketsNoResolved => 'Nessun pronostico risolto';

  @override
  String marketsPublished(int won, int cases) {
    return 'Pubblicati $won/$cases';
  }

  @override
  String marketsPublishedWon(int won, int cases, String percent) {
    return '$won/$cases pubblicati vinti · $percent';
  }

  @override
  String get marketsRadarNote =>
      'L\'anello è la percentuale storica di successo della migliore linea convalidata di ogni mercato; «Pubblicati» sono i pronostici già risolti. Sono pronostici pre-partita, non avvisi in diretta, e nessuna probabilità garantisce un risultato.';

  @override
  String mdCornersTotal(Object total) {
    return 'corner · totale $total';
  }

  @override
  String get mdEmptyHistory =>
      'Non ci sono ancora pronostici risolti in questo mercato.';

  @override
  String get mdEmptyToday =>
      'Non ci sono pronostici disponibili ora per questo mercato. Compaiono quando il modello li pubblica, prima della partita.';

  @override
  String get mdHitRate => 'Percentuale di successo';

  @override
  String get mdLineConfirmed => 'Confermata';

  @override
  String get mdLineNotDeployed => 'Non distribuita';

  @override
  String get mdLineReview => 'In revisione';

  @override
  String get mdLineShort => 'Campione ridotto';

  @override
  String get mdLoadError => 'Impossibile caricare lo storico.';

  @override
  String get mdModel => 'MODELLO';

  @override
  String get mdNoDate => 'Senza data';

  @override
  String get mdOverall => 'Generale';

  @override
  String get mdTabPrevious => 'Precedenti';

  @override
  String mdTabToday(int count) {
    return 'Oggi ($count)';
  }

  @override
  String get mdValidatedLines => 'Linee convalidate';

  @override
  String get mmChance => 'OPPORTUNITÀ';

  @override
  String get mmDisclaimer =>
      'È un\'analisi del modello, non un consiglio di scommessa. La «quota giusta» è 1/probabilità: non è una quota da bookmaker. Un pronostico può sbagliare.';

  @override
  String get mmFairOdds => 'quota giusta';

  @override
  String mmGroupCount(String group, int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count mercati',
      one: '$count mercato',
    );
    return '$group · $_temp0';
  }

  @override
  String mmLocked(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count bloccati',
      one: '$count bloccato',
    );
    return '$_temp0';
  }

  @override
  String mmOpen(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count aperti',
      one: '$count aperto',
    );
    return '$_temp0';
  }

  @override
  String mmProb(int value) {
    return '$value% prob.';
  }

  @override
  String get mmPublishedOdds => 'quota pubblicata';

  @override
  String get mmScoresTitle => 'Risultati più probabili';

  @override
  String get mmScoresVip => 'I risultati più probabili sono per i VIP.';

  @override
  String get mmTitle => 'Mercati della partita';

  @override
  String get moreApp => 'App';

  @override
  String get moreGuide => 'Guida ai pronostici';

  @override
  String get moreGuideSub => 'Come leggere probabilità, quote e sfide';

  @override
  String get moreLearn => 'Impara';

  @override
  String get moreLegal => 'Note legali';

  @override
  String get moreRate => 'Valuta l\'app';

  @override
  String get moreRateSub => 'Condividi la tua opinione';

  @override
  String get moreShare => 'Condividi l\'app';

  @override
  String get moreShareMessage =>
      'Scopri QuantFut: probabilità di calcio basate sui dati, senza promesse. https://pronosticosdeportivos.pro';

  @override
  String get moreShareSub => 'Invita i tuoi amici';

  @override
  String get moreStoreError => 'Impossibile aprire lo store delle app.';

  @override
  String get navCoins => 'Coins';

  @override
  String get navHome => 'Home';

  @override
  String get navMarkets => 'Mercati';

  @override
  String get navPredictions => 'Pronostici';

  @override
  String get navProfile => 'Profilo';

  @override
  String noteExpectedAverage(String value) {
    return 'Media attesa: $value';
  }

  @override
  String noteExpectedGoals(String value) {
    return 'Gol attesi: $value';
  }

  @override
  String noteXg(String home, String homeValue, String away, String awayValue) {
    return 'xG: $home $homeValue · $away $awayValue';
  }

  @override
  String get notificationIosPending =>
      'Le notifiche iOS attendono la configurazione di Apple.';

  @override
  String get notificationPermissionDenied =>
      'Attiva l\'autorizzazione dalle impostazioni del dispositivo.';

  @override
  String get outcomeLoss => 'Perso';

  @override
  String get outcomePush => 'Rimborso';

  @override
  String get outcomeWin => 'Vinto';

  @override
  String parleyChipLine(int count, String min, String max) {
    return 'Fino a $count multiple · quota $min–$max';
  }

  @override
  String parleyDayCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count multiple',
      one: '$count multipla',
    );
    return '$_temp0';
  }

  @override
  String parleyDaySettled(int won, int settled) {
    return '$won/$settled vinte';
  }

  @override
  String get parleyDisclaimer =>
      'Viene scelta per probabilità, non per valore, e ogni selezione riduce il margine. Una multipla può sbagliare: moltiplicare le quote moltiplica anche il rischio.';

  @override
  String get parleyFewNote =>
      'Con poche multiple il tasso reale non dimostra ancora nulla.';

  @override
  String get parleyFreeChip => '1 gratis al giorno';

  @override
  String get parleyFreeNote =>
      'Una gratis al giorno (quella a quota più bassa); le altre, VIP.';

  @override
  String get parleyHistoryTitle => 'Storico della Multipla';

  @override
  String get parleyInactiveBody =>
      'Quando sarà attivata vedrai qui le multiple del giorno, sigillate prima dell\'inizio delle partite.';

  @override
  String get parleyInactiveTitle => 'La Multipla non è ancora attiva';

  @override
  String get parleyInfoTitle => 'Come viene scelta una multipla';

  @override
  String parleyJointProb(String percent, int legs) {
    String _temp0 = intl.Intl.pluralLogic(
      legs,
      locale: localeName,
      other: '$legs selezioni',
      one: '$legs selezione',
    );
    return '$percent di probabilità congiunta · $_temp0';
  }

  @override
  String get parleyLoadError => 'Impossibile caricare la Multipla.';

  @override
  String get parleyNoHistory =>
      'Non c\'è ancora uno storico delle multiple. Comparirà qui quando la prima sarà liquidata.';

  @override
  String get parleyNoneBody =>
      'Il modello non pubblica una multipla se non ne trova una entro le regole.';

  @override
  String get parleyNoneTitle => 'Oggi non ci sono multiple';

  @override
  String parleyOddsBetween(String min, String max) {
    return 'Quota tra $min e $max';
  }

  @override
  String get parleyOutcomeLoss => 'Perso';

  @override
  String get parleyOutcomePending => 'In sospeso';

  @override
  String get parleyOutcomeVoid => 'Annullato';

  @override
  String get parleyOutcomeWin => 'Vinto';

  @override
  String get parleyPastDays => 'Giorni precedenti';

  @override
  String parleyRange(int count, String min, String max) {
    return 'Da 1 a $count multiple · quota tra $min e $max · la più probabile di ogni gradino';
  }

  @override
  String parleyResultScore(Object score) {
    return 'Risultato $score';
  }

  @override
  String get parleySealed => 'Multiple sigillate prima delle partite';

  @override
  String parleyStep(Object step) {
    return 'GRADINO $step';
  }

  @override
  String parleySummary(Object hits, Object total) {
    return '$hits/$total multiple vinte';
  }

  @override
  String parleySummaryPromised(String value) {
    return ' contro $value% promesso';
  }

  @override
  String parleySummaryReal(String value) {
    return ' · $value% reale';
  }

  @override
  String pickOddsAtPublish(Object book) {
    return 'Quota alla pubblicazione · $book';
  }

  @override
  String pickProbability(String percent) {
    return 'Probabilità $percent';
  }

  @override
  String get pickSeeAnalysis => 'Vedi l\'analisi della partita';

  @override
  String get pickSourceNA => 'Fonte non disponibile';

  @override
  String pickUnlockCoins(Object cost) {
    return 'Sblocca per $cost monete';
  }

  @override
  String get pickUnlockPrompt => 'Sblocca il pronostico e la sua quota.';

  @override
  String get pickUnlockVip => 'Sblocca il pronostico VIP';

  @override
  String picksAllHeading(int count) {
    return 'Pronostici · $count';
  }

  @override
  String get picksBestProb => 'Probabilità più alta';

  @override
  String picksCoinsShort(Object cost) {
    return '$cost monete';
  }

  @override
  String get picksEmpty =>
      'Non ci sono pronostici pubblicati in attesa in questo intervallo.';

  @override
  String picksFreeHeading(int count) {
    return 'Gratis · $count';
  }

  @override
  String get picksLockedHide => 'Nascondi l\'elenco';

  @override
  String get picksLockedHint =>
      'Con VIP vedi il pronostico, la probabilità e l\'analisi';

  @override
  String get picksLockedShow => 'Mostra l\'elenco';

  @override
  String picksLockedTitle(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count pronostici in più con VIP',
      one: '1 pronostico in più con VIP',
    );
    return '$_temp0';
  }

  @override
  String picksRangeHint(int min, int max) {
    return '$min–$max% di probabilità · uno gratis per mercato';
  }

  @override
  String get picksSeeAnalysis => 'Vedi l\'analisi';

  @override
  String get picksTomorrow => 'Domani';

  @override
  String picksTrainingReasons(String reasons) {
    return 'Modello in addestramento · $reasons';
  }

  @override
  String picksTrustDetail(int hits, int total) {
    return '$hits su $total pronostici';
  }

  @override
  String picksTrustPromised(String percent) {
    return 'Promesso: $percent';
  }

  @override
  String get picksTrustTitle => 'Tasso di successo storico';

  @override
  String get prefsAnalyticsBody =>
      'Aiuta a migliorare l\'app con dati sulle schermate utilizzate. È facoltativo.';

  @override
  String get prefsAnalyticsTitle => 'Misurazione dell\'uso';

  @override
  String get prefsDeleteAccount => 'Richiedi l\'eliminazione del mio account';

  @override
  String get prefsDeleteAccountHint =>
      'Consulta i passaggi e il contatto di Saptain LTD.';

  @override
  String get prefsDiagnosticsBody =>
      'Invia informazioni tecniche a Firebase e a Sentry per diagnosticare i guasti. È facoltativo.';

  @override
  String get prefsDiagnosticsTitle => 'Segnalazioni di errori e prestazioni';

  @override
  String get prefsInbox => 'Casella degli avvisi';

  @override
  String get prefsLanguageNote =>
      'La lingua si applica a tutta l\'app e viene salvata come preferenza.';

  @override
  String get prefsNote =>
      'Puoi usare le funzioni di base senza attivare misurazione o diagnostica. Modificare queste opzioni non elimina automaticamente i dati già inviati.';

  @override
  String get prefsNotificationsOff =>
      'Disponibile quando l\'accesso con Google sarà completato.';

  @override
  String get prefsNotificationsOn =>
      'Puoi disattivarle quando vuoi. Gli avvisi possono comparire sulla schermata di blocco.';

  @override
  String get prefsNotificationsTitle => 'Notifiche di QuantFut';

  @override
  String get prefsPrivacyRights => 'Privacy e i tuoi diritti';

  @override
  String get prefsTitle => 'Privacy e preferenze';

  @override
  String get probBarAway => 'Osp.';

  @override
  String get probBarDraw => 'Pari';

  @override
  String get probBarHome => 'Casa';

  @override
  String get profileAppVersion => 'Versione dell\'app';

  @override
  String get profileBalance => 'Saldo e monitoraggio';

  @override
  String get profileConnected => 'QuantFut · Connesso al server';

  @override
  String get profileCreateAccount => 'Crea account';

  @override
  String get profileCreateOne => 'Crea un account';

  @override
  String get profileEmail => 'E-mail';

  @override
  String get profileEmailPending => 'E-mail in attesa di verifica';

  @override
  String get profileEmailVerified => 'E-mail verificata';

  @override
  String get profileForgot => 'Ho dimenticato la password';

  @override
  String get profileForgotSent =>
      'Se l\'account esiste, riceverai le istruzioni via e-mail.';

  @override
  String get profileFreePlan => 'Piano gratuito';

  @override
  String get profileGeneral => 'Generale';

  @override
  String get profileHaveAccount => 'Ho già un account';

  @override
  String get profileLanguage => 'Lingua';

  @override
  String get profileMeasurement => 'Misurazione ed errori';

  @override
  String get profileNotifications => 'Notifiche';

  @override
  String get profileOddsFormat => 'Formato delle quote';

  @override
  String get profileOddsFormatValue =>
      'Decimale · Quote registrate alla pubblicazione';

  @override
  String get profilePassword => 'Password';

  @override
  String get profilePreferences => 'Preferenze';

  @override
  String get profileRefreshAccess => 'Aggiorna il mio accesso';

  @override
  String get profileSeePlans => 'Vedi i piani VIP';

  @override
  String get profileSendVerification => 'Invia e-mail di verifica';

  @override
  String get profileSignIn => 'Accedi';

  @override
  String get profileSignOut => 'Esci';

  @override
  String get profileTitle => 'Profilo e impostazioni';

  @override
  String profileValidUntil(String date) {
    return 'Validità: $date';
  }

  @override
  String get profileVerificationSent => 'E-mail di verifica inviata.';

  @override
  String get profileVipActive => 'Accesso VIP attivo';

  @override
  String get profileYourAccount => 'Il tuo account QuantFut';

  @override
  String resultLabel(String score) {
    return 'Risultato: $score';
  }

  @override
  String get rewardsAttendanceSub =>
      'Una volta al giorno · si azzera alle 00:00 UTC';

  @override
  String get rewardsAttendanceTitle => 'Presenza giornaliera';

  @override
  String get rewardsAvailable => 'Disponibile';

  @override
  String get rewardsCheckIn => 'Segna la presenza';

  @override
  String get rewardsCheckInNote =>
      'Una volta al giorno UTC. Se salti un giorno, la serie ricomincia.';

  @override
  String rewardsChipRate(Object cost) {
    return '$cost monete = 1 pronostico';
  }

  @override
  String rewardsChipStreak(int days) {
    String _temp0 = intl.Intl.pluralLogic(
      days,
      locale: localeName,
      other: 'Serie di $days giorni',
      one: 'Serie di 1 giorno',
    );
    return '$_temp0';
  }

  @override
  String rewardsClaimCta(Object coins) {
    return 'Segna la presenza · +$coins';
  }

  @override
  String rewardsClaimed(Object coins) {
    return '+$coins monete';
  }

  @override
  String get rewardsClaimedToday => 'Riscattata oggi';

  @override
  String get rewardsCodeCopied => 'Codice copiato.';

  @override
  String get rewardsCodeRegistered => 'Codice invito registrato.';

  @override
  String rewardsComingSoon(String names) {
    return 'Prossimamente: $names';
  }

  @override
  String get rewardsCopy => 'Copia';

  @override
  String rewardsCopyCode(Object code) {
    return 'Copia il mio codice · $code';
  }

  @override
  String rewardsDay(int number) {
    return 'Giorno $number';
  }

  @override
  String get rewardsDebt => 'Saldo in sospeso per ricompense annullate.';

  @override
  String get rewardsEarnTitle => 'Guadagna monete oggi';

  @override
  String get rewardsEnough => 'Hai monete per uno sblocco.';

  @override
  String get rewardsGo => 'Vai';

  @override
  String rewardsInviteChip(Object coins) {
    return '+$coins per te';
  }

  @override
  String rewardsInviteCondition(Object min) {
    return 'Dopo aver verificato l\'e-mail e completato $min monete in offerte confermate.';
  }

  @override
  String rewardsInviteFriend(Object coins) {
    return 'Il tuo amico riceve +$coins registrando il tuo codice';
  }

  @override
  String rewardsInviteReward(Object referrer, Object invitee) {
    return 'Tu +$referrer · Il tuo amico +$invitee monete';
  }

  @override
  String get rewardsInviteTitle => 'Invita i tuoi amici';

  @override
  String get rewardsInviterCode => 'Codice di chi ti ha invitato';

  @override
  String get rewardsLedgerEmpty => 'Non ci sono ancora movimenti.';

  @override
  String get rewardsLedgerLess => 'Mostra meno';

  @override
  String get rewardsLedgerMore => 'Mostra altro';

  @override
  String get rewardsLedgerTitle => 'I miei movimenti';

  @override
  String rewardsMissing(int missing) {
    String _temp0 = intl.Intl.pluralLogic(
      missing,
      locale: localeName,
      other: 'Mancano $missing monete per il prossimo sblocco.',
      one: 'Manca $missing moneta per il prossimo sblocco.',
    );
    return '$_temp0';
  }

  @override
  String get rewardsMissingUnknown =>
      'Mancano — monete per il prossimo sblocco.';

  @override
  String get rewardsMyCoins => 'Le mie monete';

  @override
  String rewardsNextIn(String time) {
    return 'Prossima presenza tra $time';
  }

  @override
  String get rewardsOfferAvailable =>
      'Offerte in base al tuo paese e dispositivo';

  @override
  String get rewardsOfferPending => 'In attesa di attivazione';

  @override
  String get rewardsOffersConfig =>
      'Questo fornitore non è ancora pronto. Riprova più tardi.';

  @override
  String get rewardsOffersCta => 'Vedi le offerte';

  @override
  String get rewardsOffersLead => 'Completa le offerte e ricevi monete.';

  @override
  String get rewardsOffersLoadFailed =>
      'Impossibile aprire le offerte. Controlla la connessione e riprova.';

  @override
  String get rewardsOffersTimeout =>
      'Il caricamento delle offerte ha richiesto troppo tempo. Riprova.';

  @override
  String get rewardsOffersTitle => 'Offerte per guadagnare monete';

  @override
  String get rewardsOffersUnavailable =>
      'Nessuna offerta disponibile al momento. Riprova più tardi.';

  @override
  String get rewardsOperationDone => 'Operazione confermata.';

  @override
  String rewardsReferralStats(Object registered, Object qualified) {
    return '$registered registrati · $qualified convalidati';
  }

  @override
  String get rewardsRefreshBalance => 'Aggiorna il saldo';

  @override
  String get rewardsRegisterCode => 'Registra il codice';

  @override
  String get rewardsSignIn => 'Accedi';

  @override
  String get rewardsSignInHint =>
      'Accedi da Profilo per salvare il saldo, segnare la presenza e usare un codice invito.';

  @override
  String rewardsStreak(int days) {
    String _temp0 = intl.Intl.pluralLogic(
      days,
      locale: localeName,
      other: '$days giorni',
      one: '$days giorno',
    );
    return 'Serie di presenze · $_temp0';
  }

  @override
  String get rewardsTermsTitle => 'Regole e condizioni';

  @override
  String rewardsUnlockFor(Object cost) {
    return 'Sblocca un pronostico per $cost monete';
  }

  @override
  String get selBttsNo => 'Non segnano entrambe';

  @override
  String get selBttsYes => 'Segnano entrambe';

  @override
  String selCards(String side, String line) {
    String _temp0 = intl.Intl.selectLogic(side, {
      'over': 'Più di $line cartellini',
      'other': 'Meno di $line cartellini',
    });
    return '$_temp0';
  }

  @override
  String selCorners(String side, String line) {
    String _temp0 = intl.Intl.selectLogic(side, {
      'over': 'Più di $line corner',
      'other': 'Meno di $line corner',
    });
    return '$_temp0';
  }

  @override
  String selCornersTeam(String side, String line, String team) {
    String _temp0 = intl.Intl.selectLogic(side, {
      'over': 'Più di $line corner di $team',
      'other': 'Meno di $line corner di $team',
    });
    return '$_temp0';
  }

  @override
  String selDrawNoBet(String team) {
    return '$team vince (il pareggio rimborsa)';
  }

  @override
  String selEitherNoDraw(String home, String away) {
    return '$home o $away (senza pareggio)';
  }

  @override
  String selGoals(String side, String line) {
    String _temp0 = intl.Intl.selectLogic(side, {
      'over': 'Più di $line gol',
      'other': 'Meno di $line gol',
    });
    return '$_temp0';
  }

  @override
  String selHandicapLong(String team, String line) {
    return '$team $line (handicap asiatico)';
  }

  @override
  String selHandicapShort(String team, String line) {
    return '$team $line';
  }

  @override
  String selHomeWins(String team) {
    return 'Vince $team';
  }

  @override
  String get selHtBttsNo => 'Non segnano entrambe nel 1T';

  @override
  String get selHtGoalYes => 'Ci sarà un gol nel 1T';

  @override
  String selTeamOrDraw(String team) {
    return '$team o pareggio';
  }

  @override
  String selTeamScores(String team) {
    return 'Segna $team';
  }

  @override
  String selWinToNil(String team) {
    return '$team vince senza subire gol';
  }

  @override
  String get shellNeedCoinsBody =>
      'Guadagna monete con la presenza giornaliera e le offerte per sbloccare questo pronostico.';

  @override
  String get shellNeedCoinsCta => 'Guadagna monete';

  @override
  String get shellNeedCoinsTitle => 'Ti mancano delle monete';

  @override
  String get shellNewAlert => 'Nuovo avviso di QuantFut';

  @override
  String get shellSignInForCoins =>
      'Accedi da Profilo per usare le tue monete.';

  @override
  String shellUnlockBody(Object cost) {
    return 'Verranno scalate $cost monete dal tuo saldo. L\'accesso riguarda questo pronostico.';
  }

  @override
  String get shellUnlockTitle => 'Sblocca il pronostico';

  @override
  String get shellView => 'Vedi';

  @override
  String get splashTagline => 'CALCIO · NBA · STATISTICA';

  @override
  String get startupFailed => 'Impossibile avviare QuantFut. Riprova.';

  @override
  String get startupLoading => 'Avvio di QuantFut';

  @override
  String statAveragesNote(Object homeN, Object awayN) {
    return 'Medie di $homeN partite della squadra di casa e $awayN di quella ospite. La copertura di tiri, corner e xG può essere parziale.';
  }

  @override
  String get statBestAway => 'Miglior vittoria in trasferta';

  @override
  String get statBestHome => 'Miglior vittoria in casa';

  @override
  String get statCleanSheet => 'Porta inviolata';

  @override
  String get statCompareNote =>
      'Le barre confrontano i valori registrati; non rappresentano probabilità di vittoria. Meno gol subiti è meglio.';

  @override
  String get statCompareTitle => 'Confronto tra squadre';

  @override
  String get statDrawStreak => 'Serie di pareggi';

  @override
  String get statFormLegend =>
      'V: vittoria · P: pareggio · S: sconfitta. Più recente a sinistra.';

  @override
  String get statFormNA => 'Forma non disponibile.';

  @override
  String get statFormTitle => 'Forma delle squadre';

  @override
  String get statGoalsAgainst => 'Gol subiti';

  @override
  String get statGoalsAvgNote =>
      'Gol fatti per partita; non è la proiezione dei gol del modello.';

  @override
  String get statGoalsAvgTitle => 'MEDIA STORICA DEI GOL';

  @override
  String get statGoalsFor => 'Gol fatti';

  @override
  String statH2hSummary(
    Object n,
    Object home,
    Object homeWins,
    Object away,
    Object awayWins,
    Object draws,
  ) {
    return 'In $n scontri registrati: $home ha vinto $homeWins, $away ha vinto $awayWins e ci sono stati $draws pareggi.';
  }

  @override
  String get statH2hTitle => 'Testa a testa';

  @override
  String statLastMatches(int count) {
    return 'Ultime $count partite registrate';
  }

  @override
  String get statMinutesNA =>
      'La distribuzione per minuti non è disponibile per questa partita.';

  @override
  String get statMinutesTitle => 'Gol per minuto';

  @override
  String get statNeedsAccess =>
      'Il pronostico di questa partita richiede l\'accesso VIP o uno sblocco con monete.';

  @override
  String get statOnTargetShort => 'In porta';

  @override
  String get statOver25 => 'Più di 2,5 gol';

  @override
  String statPickProbOdds(String percent, String odds) {
    return 'Probabilità $percent · Quota @ $odds';
  }

  @override
  String statPlayed(Object played) {
    return '$played partite';
  }

  @override
  String statPoints(Object points) {
    return '$points punti';
  }

  @override
  String get statPoissonNA =>
      'La distribuzione di Poisson e i risultati probabili non sono ancora disponibili nei dati di questa partita.';

  @override
  String get statPoissonTitle => 'Distribuzione dei gol di Poisson';

  @override
  String statPosition(Object position) {
    return 'Posizione $position';
  }

  @override
  String get statProbNA => 'Probabilità del modello non ancora disponibili.';

  @override
  String get statProbTitle => 'PROBABILITÀ DI VITTORIA · 1X2';

  @override
  String get statPublishedPick => 'PRONOSTICO PUBBLICATO';

  @override
  String get statRadarNeeds =>
      'Il confronto grafico richiede almeno tre metriche disponibili per entrambe le squadre.';

  @override
  String get statRadarNote =>
      'Scala relativa per asse. Un\'area maggiore non implica una maggiore probabilità di vincere.';

  @override
  String get statResDraw => 'P';

  @override
  String get statResLoss => 'S';

  @override
  String get statResWin => 'V';

  @override
  String statResultsAvailable(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count risultati disponibili',
      one: '$count risultato disponibile',
    );
    return '$_temp0';
  }

  @override
  String get statSeasonTitle => 'Stagione e risultati recenti';

  @override
  String get statShots => 'Tiri';

  @override
  String get statShotsOnTarget => 'Tiri in porta';

  @override
  String get statStandingNA => 'Classifica non disponibile.';

  @override
  String get statSummaryTitle => 'Riepilogo del pronostico';

  @override
  String get statTeamStatsTitle => 'Statistiche della squadra';

  @override
  String get statWinStreak => 'Serie di vittorie';

  @override
  String get statXgHistoric => 'xG storico';

  @override
  String get streamHighProb => 'Alta probabilità';

  @override
  String get streamLadder => 'Sfida Scala';

  @override
  String get streamParley => 'Multipla';

  @override
  String tileFairOdds(String value) {
    return 'Quota giusta $value';
  }

  @override
  String get tileFavorite => 'Favorito 1X2';

  @override
  String tileFavoriteLead(String team, int pts) {
    return '$team · +$pts pt';
  }

  @override
  String get tileFavoriteNA => 'Probabilità non disponibili';

  @override
  String get tileGoalsNA => 'Storico insufficiente';

  @override
  String get tileGoalsTrend => 'Tendenza gol';

  @override
  String get tileOver25Model => 'Più di 2,5 secondo il modello';

  @override
  String get tileOver25Recent => 'Più di 2,5 nelle ultime partite';

  @override
  String get tileProbability => 'Probabilità';

  @override
  String get tileXg => 'xG previsto';

  @override
  String tileXgCaption(String home, String away) {
    return '$home casa · $away ospite';
  }

  @override
  String get tileXgNA => 'Disponibile nei mercati dei gol';

  @override
  String get titleAsianHandicap => 'Handicap asiatico';

  @override
  String get titleDrawNoBet => 'Pareggio rimborsato';

  @override
  String titleTeamGoals(String team) {
    return 'Gol di $team';
  }

  @override
  String get titleTotalCards => 'Cartellini totali';

  @override
  String get titleTotalCorners => 'Corner totali';

  @override
  String get titleTotalGoals => 'Gol totali';

  @override
  String get titleWinner => 'Vincitore della partita';

  @override
  String get tooltipVip => 'VIP';

  @override
  String get vipActivate => 'Attiva l\'accesso VIP';

  @override
  String get vipActive => 'Il tuo accesso VIP è attivo.';

  @override
  String get vipBadge => '✦  ACCESSO VIP';

  @override
  String get vipBenefit1Body =>
      'Ogni pronostico viene sigillato prima della partita';

  @override
  String get vipBenefit1Title => 'Storico verificabile';

  @override
  String vipBenefit2Body(int min, int max) {
    return 'Tutti i pronostici da $min a $max%, senza quota gratuita';
  }

  @override
  String get vipBenefit2Title => 'Alta probabilità completa';

  @override
  String get vipBenefit3Body => 'Tutti i gradini in sospeso, non solo uno';

  @override
  String get vipBenefit3Title => 'Sfida Scala completa';

  @override
  String get vipBenefit4Body =>
      'Quota pubblicata, probabilità e xG di ogni pronostico';

  @override
  String get vipBenefit4Title => 'Quote e analisi della partita';

  @override
  String get vipBestPrice => '★ MIGLIOR PREZZO';

  @override
  String get vipCheckAccess => 'Verifica il mio accesso';

  @override
  String get vipCheckSignIn =>
      'Accedi da Profilo per verificare il tuo accesso.';

  @override
  String vipDays(int days) {
    String _temp0 = intl.Intl.pluralLogic(
      days,
      locale: localeName,
      other: '$days giorni',
      one: '$days giorno',
    );
    return '$_temp0';
  }

  @override
  String get vipFreeAccess => 'Il tuo account ha accesso gratuito.';

  @override
  String get vipHistoryNote =>
      'Storico pubblico e sigillato; i campioni per mercato sono piccoli e un pronostico può sbagliare.';

  @override
  String get vipIntro =>
      'Tutti i pronostici Alta probabilità e della Sfida Scala finché il tuo abbonamento è attivo.';

  @override
  String get vipLinked => '🔒  Il tuo accesso VIP è collegato al tuo account';

  @override
  String vipMonthly(String amount) {
    return '≈ $amount/mese';
  }

  @override
  String vipMonths(int months) {
    String _temp0 = intl.Intl.pluralLogic(
      months,
      locale: localeName,
      other: '$months mesi',
      one: '$months mese',
    );
    return '$_temp0';
  }

  @override
  String get vipNoExpiry => 'Senza scadenza';

  @override
  String get vipPaymentRequired =>
      'La sottoscrizione richiede un canale di pagamento configurato.';

  @override
  String get vipPickLabel => 'Pronostico VIP';

  @override
  String get vipPlansSoon =>
      'I piani verranno mostrati quando saranno disponibili.';

  @override
  String get vipPricesNote => 'Prezzi dal catalogo del server.';

  @override
  String get vipPurchasesPending =>
      'Acquisti in preparazione: dall\'app non viene ancora addebitato nulla.';

  @override
  String get vipStatRecorded => 'Percentuale di successo registrata';

  @override
  String get vipStatResolved => 'Risolti';

  @override
  String get welcome1Body =>
      'Scopri il lato statistico dello sport: partite, analisi e pronostici del progetto che già conosci sul web.';

  @override
  String get welcome1Title => 'Calcio e NBA,\ncon un\'altra prospettiva';

  @override
  String get welcome2Body =>
      'La forma recente, gli scontri diretti e le statistiche aiutano a capire cosa può succedere. Parti dai dati.';

  @override
  String get welcome2Title => 'Ogni partita,\ncon più contesto';

  @override
  String get welcome3Body =>
      'Gol, corner, handicap e statistiche dell\'NBA. Scopri cosa misura ogni analisi prima di interpretare una selezione.';

  @override
  String get welcome3Title => 'Più mercati.\nPiù informazioni.';

  @override
  String get welcome4Body =>
      'Un pronostico si capisce anche dopo la partita. Lo storico permette di confrontare le stime con i risultati.';

  @override
  String get welcome4Title => 'I risultati,\nsott\'occhio';

  @override
  String get welcome5Body =>
      'Una probabilità non è una certezza. Esplora i contenuti, rivedi il contesto e forma il tuo giudizio.';

  @override
  String get welcome5Title => 'Tutto inizia\ndall\'informarsi';

  @override
  String welcomeGoTo(int number) {
    return 'Vai alla schermata di benvenuto $number';
  }

  @override
  String get welcomeNext => 'Avanti';

  @override
  String welcomeScreenOf(int page, int total) {
    return 'Schermata $page di $total';
  }

  @override
  String get welcomeSkip => 'Salta';

  @override
  String get welcomeStart => 'Inizia';
}
