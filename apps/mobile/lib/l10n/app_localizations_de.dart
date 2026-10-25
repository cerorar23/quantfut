// ignore: unused_import
import 'package:intl/intl.dart' as intl;

import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for German (`de`).
class AppLocalizationsDe extends AppLocalizations {
  AppLocalizationsDe([String locale = 'de']) : super(locale);

  @override
  String get accessBody1 =>
      'Ein statistisches Modell berechnet die Wahrscheinlichkeiten. Eine Wahrscheinlichkeit ist keine Gewissheit.';

  @override
  String get accessBody2 =>
      'Jeden Tag die wahrscheinlichsten, mit ihrer echten historischen Trefferquote.';

  @override
  String get accessBody3 =>
      'Verfolge den Fortschritt jeder Challenge und wie viel bis zum Abschluss fehlt.';

  @override
  String get accessBody4 =>
      'Mit Quote und gemeinsamer Wahrscheinlichkeit, damit du weißt, was du riskierst.';

  @override
  String get accessBody5 =>
      'Checke ein, schließe Angebote ab und lade Freunde ein, um Prognosen freizuschalten.';

  @override
  String get accessCardBody =>
      'Behalte deinen Fortschritt und deine Münzen auf allen Geräten.';

  @override
  String get accessCardTitle => 'Melde dich an, um fortzufahren';

  @override
  String get accessConsent =>
      'Ich bin mindestens 18 Jahre alt und akzeptiere die Nutzungsbedingungen und die Datenschutzerklärung.';

  @override
  String get accessConsentNeeded => 'Setze den Haken, um fortzufahren.';

  @override
  String accessConsentRich(String terms, String privacy) {
    return 'Ich bin mindestens 18 Jahre alt und akzeptiere $terms und $privacy.';
  }

  @override
  String get accessContinueWithGoogle => 'Mit Google fortfahren';

  @override
  String get accessDisclaimer =>
      'Nur zu Informations- und Unterhaltungszwecken. Prognosen garantieren keine Ergebnisse.';

  @override
  String get accessDocumentOpenError =>
      'Das Dokument konnte nicht geöffnet werden.';

  @override
  String get accessForgotLink => 'Bisheriges Passwort wiederherstellen';

  @override
  String get accessForgotSent =>
      'Falls das Konto existiert, erhältst du Anweisungen per E-Mail.';

  @override
  String get accessGenericError =>
      'Die Anmeldung konnte nicht abgeschlossen werden. Bitte versuche es erneut.';

  @override
  String get accessGoogleError =>
      'Anmeldung mit Google nicht möglich. Bitte versuche es erneut.';

  @override
  String get accessKicker1 => 'ECHTE WAHRSCHEINLICHKEITEN';

  @override
  String get accessKicker2 => 'HOHE WAHRSCHEINLICHKEIT';

  @override
  String get accessKicker3 => 'TREPPEN-CHALLENGE';

  @override
  String get accessKicker4 => 'KOMBIWETTE';

  @override
  String get accessKicker5 => 'MÜNZEN';

  @override
  String get accessLinkButton => 'Mein Konto verknüpfen';

  @override
  String get accessLinkEmail => 'E-Mail deines bisherigen Kontos';

  @override
  String get accessLinkIntro =>
      'Verknüpfe dein bisheriges Konto, um Guthaben und Zugang zu behalten.';

  @override
  String get accessLinkPassword => 'Bisheriges Passwort';

  @override
  String get accessOtherAccount => 'Anderes Konto verwenden';

  @override
  String get accessPreparingDocs => 'Wir bereiten die Zugangsdokumente vor.';

  @override
  String get accessPrivacy => 'Datenschutzerklärung';

  @override
  String get accessRetry => 'Anmeldung erneut versuchen';

  @override
  String get accessTagline =>
      'Spiele, Analysen und Verlauf. Eine Wahrscheinlichkeit ist keine Gewissheit.';

  @override
  String get accessTerms => 'Nutzungsbedingungen';

  @override
  String get accessTitle1 => 'Verstehe jedes Spiel mit Daten.';

  @override
  String get accessTitle2 => 'Prognosen mit sichtbarer Trefferquote.';

  @override
  String get accessTitle3 => 'Stufe für Stufe nach oben.';

  @override
  String get accessTitle4 => 'Ein Schein, vor den Spielen versiegelt.';

  @override
  String get accessTitle5 => 'Verdiene Münzen und schalte frei.';

  @override
  String get adsCardTitle => 'Videos mit Belohnung';

  @override
  String get adsFootnote =>
      'Die Münzen werden am Ende des Videos gutgeschrieben. Wenn du es vorher schließt, bekommst du keine.';

  @override
  String get adsLimitReached =>
      'Heutiges Limit erreicht. Komm nach 00:00 UTC wieder.';

  @override
  String get adsLoading => 'Video wird geladen…';

  @override
  String get adsPending => 'Deine Münzen kommen gleich an.';

  @override
  String adsProgress(int used, int cap) {
    return 'Heute: $used von $cap';
  }

  @override
  String get adsUnavailable =>
      'Derzeit sind keine Videos verfügbar. Versuche es später erneut.';

  @override
  String get adsVerifying => 'Deine Belohnung wird geprüft…';

  @override
  String adsWaitFor(String time) {
    return 'Nächstes Video in $time';
  }

  @override
  String adsWatchCta(int coins) {
    return 'Video ansehen · +$coins Münzen';
  }

  @override
  String alertsAbsencesOf(String team) {
    return 'Ausfälle von $team';
  }

  @override
  String get alertsAdvantage => 'Vorteil';

  @override
  String get alertsAdvantageEmpty => 'Keine Vorteile gemeldet.';

  @override
  String alertsChecked(String when) {
    return 'Geprüft $when';
  }

  @override
  String get alertsDisadvantage => 'Nachteil';

  @override
  String get alertsDisadvantageEmpty => 'Keine Nachteile gemeldet.';

  @override
  String get alertsDoubt => 'Fraglich';

  @override
  String get alertsNoCheck =>
      'Für dieses Spiel gibt es noch keine Ausfall-Prüfung. Hat die Liga diese Daten nicht, heißt das nicht, dass niemand verletzt ist.';

  @override
  String get alertsNote =>
      'Ausfälle können sich bis zum Anpfiff ändern. Die offizielle Aufstellung erscheint kurz vor dem Spiel.';

  @override
  String get alertsOut => 'Nicht verfügbar';

  @override
  String get alertsReasonFoot => 'Knöchel- oder Fußverletzung';

  @override
  String get alertsReasonIllness => 'Krankheit';

  @override
  String get alertsReasonInjury => 'Verletzung';

  @override
  String get alertsReasonKnee => 'Knieverletzung';

  @override
  String get alertsReasonKnock => 'Prellung';

  @override
  String get alertsReasonMuscle => 'Muskelverletzung';

  @override
  String get alertsReasonSuspension => 'Sperre';

  @override
  String get alertsReasonUnknown => 'Grund nicht angegeben';

  @override
  String get alertsSource => 'Quelle: API-Football';

  @override
  String alertsSummary(int out, int doubt) {
    String _temp0 = intl.Intl.pluralLogic(
      out,
      locale: localeName,
      other: '$out Ausfälle',
      one: '1 Ausfall',
    );
    String _temp1 = intl.Intl.pluralLogic(
      doubt,
      locale: localeName,
      other: '$doubt Fragliche',
      one: '1 Fraglicher',
    );
    return '$_temp0 · $_temp1';
  }

  @override
  String get alertsSuspended => 'Gesperrt';

  @override
  String get apiGoogleNotVerified =>
      'Google konnte die Anmeldung nicht verifizieren.';

  @override
  String get apiInvalidResponse => 'Ungültige Antwort des Servers.';

  @override
  String get apiInvalidSession => 'Ungültige Sitzung.';

  @override
  String apiLoadFailed(int status) {
    return 'Die Informationen konnten nicht geladen werden (HTTP $status).';
  }

  @override
  String get apiOffline =>
      'Verbindung nicht möglich. Prüfe deine Verbindung und versuche es erneut.';

  @override
  String get apiSessionExpired => 'Bitte melde dich erneut an.';

  @override
  String get apiSignInWithGoogle => 'Melde dich mit Google an.';

  @override
  String get artAnalyzeEach => 'ANALYSIERE JEDE AUSWAHL';

  @override
  String get artCorners => 'ECKEN';

  @override
  String get artFootball => 'FUSSBALL';

  @override
  String get artForm => 'FORM';

  @override
  String get artGoals => 'TORE';

  @override
  String get artHeadToHead => 'DIREKTVERGLEICH';

  @override
  String get artHeading0 => 'FUSSBALL + NBA';

  @override
  String get artHeading1 => 'KONTEXT ZÄHLT';

  @override
  String get artHeading2 => 'ENTDECKE DIE MÄRKTE';

  @override
  String get artHeading3 => 'VERLAUF IM BLICK';

  @override
  String get artHeading4 => 'DATEN + DEIN URTEIL';

  @override
  String get artNba => 'NBA';

  @override
  String get artStats => 'STATISTIKEN';

  @override
  String get artTagline => 'ANALYSIEREN. VERGLEICHEN. ENTDECKEN.';

  @override
  String get artTransparency => 'TRANSPARENZ';

  @override
  String get bannerLive => 'SPIEL LÄUFT · Prognose vor Anpfiff versiegelt';

  @override
  String bannerLost(String score) {
    return 'VERLOREN$score · Prognose vor Anpfiff versiegelt';
  }

  @override
  String bannerWon(String score) {
    return 'GEWONNEN$score · Prognose vor Anpfiff versiegelt';
  }

  @override
  String get calendarEmpty => 'Keine Begegnungen für diese Filter.';

  @override
  String calendarMatchesCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count Begegnungen',
      one: '$count Begegnung',
    );
    return '$_temp0';
  }

  @override
  String get calendarPickDate => 'Datum wählen';

  @override
  String get calendarSearchHint => 'Teams oder Ligen suchen';

  @override
  String get calendarTitle => 'Kalender · Ortszeit';

  @override
  String casesCount(int count, String formatted) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$formatted Fälle',
      one: '$formatted Fall',
    );
    return '$_temp0';
  }

  @override
  String get commonAll => 'Alle';

  @override
  String get commonAway => 'Gast';

  @override
  String get commonCancel => 'Abbrechen';

  @override
  String get commonClose => 'Schließen';

  @override
  String get commonConfirm => 'Bestätigen';

  @override
  String get commonConnecting => 'Verbindung wird hergestellt…';

  @override
  String get commonDraw => 'Unentschieden';

  @override
  String get commonHome => 'Heim';

  @override
  String get commonRefresh => 'Aktualisieren';

  @override
  String get commonRetry => 'Erneut versuchen';

  @override
  String get commonSeeVip => 'VIP-Zugang ansehen';

  @override
  String get commonToday => 'Heute';

  @override
  String get commonYesterday => 'Gestern';

  @override
  String countdownDays(int days, String time) {
    return '$days T $time';
  }

  @override
  String detailChecked(String date) {
    return 'Geprüft: $date';
  }

  @override
  String get detailFormationPending => 'Formation ausstehend';

  @override
  String get detailH2hTitle => 'Direkter Vergleich (H2H)';

  @override
  String get detailInjuries => 'Gemeldete Ausfälle';

  @override
  String get detailLineups => 'Aufstellungen';

  @override
  String get detailLineupsPending => 'Aufstellungen noch nicht bestätigt.';

  @override
  String get detailNoFeatured =>
      'Kein hervorgehobener Tipp mit einer Quote von 1.40 oder höher.';

  @override
  String get detailNoH2h => 'Für dieses Spiel sind keine Begegnungen erfasst.';

  @override
  String get detailNoInjuries => 'Keine Ausfälle im vorliegenden Bericht.';

  @override
  String get detailNoInjuriesCheck => 'Es liegt keine Ausfallprüfung vor.';

  @override
  String get detailNoPicks =>
      'Für dieses Spiel gibt es keine veröffentlichten Prognosen.';

  @override
  String get detailNoStarters => 'Keine bestätigten Starter.';

  @override
  String get detailReferee => 'Schiedsrichter';

  @override
  String get detailRefereePending => 'Schiedsrichter noch nicht bestätigt.';

  @override
  String get detailTabAlerts => 'Hinweise';

  @override
  String get detailTabH2h => 'H2H';

  @override
  String get detailTabPredictions => 'Prognosen';

  @override
  String get detailTabStats => 'Analyse';

  @override
  String get detailVipPickNotice => 'Dieses Spiel hat eine VIP-Prognose';

  @override
  String get dictAwayDefault => 'das Gastteam';

  @override
  String get dictHomeDefault => 'das Heimteam';

  @override
  String dictOddsAbove(String fair) {
    return 'Die veröffentlichte Quote liegt über der fairen Quote ($fair).';
  }

  @override
  String dictOddsBelow(String fair) {
    return 'Die veröffentlichte Quote liegt unter der fairen Quote ($fair); der Reiz liegt in der Wahrscheinlichkeit, nicht im Preis.';
  }

  @override
  String dictPick(String pick, String percent) {
    return '$pick mit einer berechneten Wahrscheinlichkeit von $percent.';
  }

  @override
  String get dictPickDefault => 'Die Prognose';

  @override
  String dictXg(
    String total,
    String home,
    String homeXg,
    String away,
    String awayXg,
  ) {
    return 'Die margenfreien Marktquoten implizieren $total erwartete Tore ($home $homeXg · $away $awayXg).';
  }

  @override
  String get disclaimerProbability =>
      'Eine Wahrscheinlichkeit ist keine Gewissheit. Entscheide informiert und spiele verantwortungsvoll.';

  @override
  String get factsAbsences => 'Ausfälle';

  @override
  String get factsDrew => 'Unentschieden';

  @override
  String get factsHideLineup => 'Elf ausblenden';

  @override
  String factsInCompetition(String competition) {
    return 'In $competition';
  }

  @override
  String get factsLastLineup => 'Letzte bekannte Aufstellung';

  @override
  String get factsLastMatch => 'Letztes Spiel';

  @override
  String factsLineupMeta(String rival, String date) {
    return 'gegen $rival · $date';
  }

  @override
  String get factsLineupNote =>
      'Das ist die Aufstellung dieses Spiels, keine Vorhersage für das heutige.';

  @override
  String get factsLost => 'Verloren';

  @override
  String get factsNoLineup => 'Noch keine Aufstellung gespeichert.';

  @override
  String get factsNoResult => 'Keine früheren Spiele erfasst.';

  @override
  String get factsSeeAlerts => 'Hinweise ansehen';

  @override
  String get factsShowLineup => 'Elf anzeigen';

  @override
  String get factsTitle => 'Spieldaten';

  @override
  String factsVs(String score, String rival) {
    return '$score gegen $rival';
  }

  @override
  String get factsWon => 'Gewonnen';

  @override
  String get famCardsSubtitle =>
      'Unter-Karten-Linien mit historischer Grundlage';

  @override
  String get famCardsTitle => 'Karten';

  @override
  String get famCornersSubtitle => 'Mehr und weniger Ecken im gesamten Spiel';

  @override
  String get famCornersTeamSubtitle =>
      'Heim und Gast, jeweils mit eigener Linie';

  @override
  String get famCornersTeamTitle => 'Ecken pro Team';

  @override
  String get famCornersTitle => 'Ecken insgesamt';

  @override
  String get famDoubleChanceSubtitle =>
      'Zwei mögliche Ergebnisse in einer Auswahl';

  @override
  String get famDoubleChanceTitle => 'Doppelte Chance';

  @override
  String get famGoalsSubtitle => 'Summen mit historisch geprüften Linien';

  @override
  String get famGoalsTitle => 'Tore im Spiel';

  @override
  String get famHandicapSubtitle =>
      'Schutzlinien und Unentschieden mit Rückerstattung';

  @override
  String get famHandicapTitle => 'Asiatisches Handicap';

  @override
  String get famNbaSubtitle =>
      'Explorative Auswertung · Bestätigung ausstehend';

  @override
  String get famNbaTeamTitle => 'NBA · Teampunkte';

  @override
  String get famNbaTotalTitle => 'NBA · Spielsumme';

  @override
  String get famNbaWinnerTitle => 'NBA · Sieger';

  @override
  String get famTeamGoalsSubtitle =>
      'Mindestens ein Tor von Heim- oder Gastteam';

  @override
  String get famTeamGoalsTitle => 'Ein Team trifft';

  @override
  String get famWinnerSubtitle => '1X2-Ergebnis mit hoher Wahrscheinlichkeit';

  @override
  String get famWinnerTitle => 'Spielsieger';

  @override
  String get featAgenda => 'Spielplan vorübergehend nicht verfügbar';

  @override
  String get featBalance => 'Verlauf in Vorbereitung';

  @override
  String get featCommunity => 'Community in Vorbereitung';

  @override
  String get featLanguages => 'Übersetzungen in Vorbereitung';

  @override
  String get featMatchData => 'Spieldaten vorübergehend nicht verfügbar';

  @override
  String get featMeasurement => 'Messung in Vorbereitung';

  @override
  String get featNba => 'NBA-Modell im Training';

  @override
  String get featNotifications => 'Benachrichtigungen in Vorbereitung';

  @override
  String get featPurchases => 'Käufe in Vorbereitung';

  @override
  String get featStats => 'Statistiken vorübergehend nicht verfügbar';

  @override
  String get featVip => 'VIP-Zugang vorübergehend nicht verfügbar';

  @override
  String get featureTraining => 'Modell im Training';

  @override
  String get fixtureFinished => 'BEENDET';

  @override
  String get fixtureLive => 'LIVE';

  @override
  String get fixtureLocalTime => 'ORTSZEIT';

  @override
  String get fixtureStartsIn => 'BEGINNT IN';

  @override
  String get fixtureTbd => 'NOCH OFFEN';

  @override
  String get forecastCanFail =>
      'Eine Prognose kann scheitern; Wahrscheinlichkeit garantiert kein Ergebnis.';

  @override
  String get forecastFeatured => 'HERVORGEHOBEN';

  @override
  String get forecastFree => 'KOSTENLOS';

  @override
  String get forecastHalfTime => 'HALBZEIT';

  @override
  String get forecastInPlay => 'LÄUFT';

  @override
  String get forecastLiveScore => 'Live-Ergebnis';

  @override
  String forecastLiveScoreAgo(int minutes) {
    return 'Live-Ergebnis · vor $minutes Min. aktualisiert';
  }

  @override
  String get forecastMarketNote =>
      'Wahrscheinlichkeiten aus margenfreien Marktquoten berechnet: Diese Liga hat kein eigenes Modell.';

  @override
  String get forecastOddsAtPublish => 'Quote bei Veröffentlichung';

  @override
  String forecastProbCalc(String percent) {
    return '$percent berechnete Wahrsch.';
  }

  @override
  String get forecastSeeStats => 'Spielstatistiken ansehen';

  @override
  String get forecastSourceMarket => 'MARKTQUOTEN';

  @override
  String get forecastSourceModel => 'EIGENES MODELL';

  @override
  String get forecastTitle => 'STATISTISCHE ANALYSE';

  @override
  String get forecastUnlocked => 'FREIGESCHALTET';

  @override
  String get forecastVerdictTitle => '💡  MODELLURTEIL';

  @override
  String get formatScheduleUnavailable => 'Uhrzeit nicht verfügbar';

  @override
  String get groupBtts => 'BEIDE TEAMS TREFFEN';

  @override
  String get groupCards => 'KARTEN';

  @override
  String get groupCorners => 'ECKEN';

  @override
  String get groupDoubleChance => 'DOPPELTE CHANCE';

  @override
  String get groupDrawNoBet => 'WETTE OHNE UNENTSCHIEDEN';

  @override
  String get groupFirstHalf => '1. HALBZEIT';

  @override
  String get groupGoals => 'TORE';

  @override
  String get groupHandicap => 'HANDICAP';

  @override
  String get groupResult => 'ERGEBNIS';

  @override
  String get groupSpecials => 'SPEZIAL';

  @override
  String get groupTeamGoals => 'TEAMTORE';

  @override
  String get guideBody1 =>
      'Hat eine Prognose 75 % Wahrscheinlichkeit, erwartet das Modell, dass sie bei einer ähnlichen Situation etwa 3 von 4 Mal eintritt. Das heißt, 1 von 4 Mal tritt sie nicht ein. Keine Daten garantieren ein bestimmtes Ergebnis.';

  @override
  String get guideBody2 =>
      'Die Quote setzt ein Wettanbieter und sie enthält dessen Marge. Die Wahrscheinlichkeit des Modells mit der in der Quote enthaltenen zu vergleichen, hilft einzuschätzen, ob der Preis vernünftig ist; das Ergebnis sichert es nicht.';

  @override
  String get guideBody3 =>
      'Sie werden vor dem Anpfiff mit Wahrscheinlichkeit und Referenzquote veröffentlicht und können nicht geändert werden. So kannst du die echte historische Trefferquote mit der versprochenen vergleichen.';

  @override
  String get guideBody4 =>
      'Bei einer Kombiwette ist die gemeinsame Wahrscheinlichkeit das Produkt der einzelnen und sinkt daher schnell, wenn du Spiele hinzufügst. Eine hohe Quote spiegelt meist genau das wider.';

  @override
  String get guideBody5 =>
      'Jede Challenge läuft in Schritten, und der nächste zählt nur, wenn der vorherige erfüllt ist. Sieh dir Fortschritt und Verlauf an, auch gescheiterte Challenges, bevor du einer folgst.';

  @override
  String get guideBody6 =>
      'QuantFut ist kein Wettanbieter und sichert keine Gewinne zu. Wenn du wettest, setze nur Geld, dessen Verlust du verkraften kannst, und nur als Volljähriger. Wenn das Spielen kein Zeitvertreib mehr ist, hol dir Hilfe.';

  @override
  String get guideHead1 => 'Eine Wahrscheinlichkeit ist keine Gewissheit';

  @override
  String get guideHead2 =>
      'Die Quote ist ein Preis, nicht die Meinung des Modells';

  @override
  String get guideHead3 => 'Jede Prognose wird vor dem Spiel versiegelt';

  @override
  String get guideHead4 => 'Mehr Auswahlen, geringere Wahrscheinlichkeit';

  @override
  String get guideHead5 => 'Es geht jeweils eine Stufe nach oben';

  @override
  String get guideHead6 => 'Es dient der Information und Unterhaltung';

  @override
  String get guideSubtitle =>
      'Lerne die Daten zu lesen, bevor du entscheidest.';

  @override
  String get guideTitle => 'Prognose-Leitfaden';

  @override
  String get guideTopic1 => 'WAHRSCHEINLICHKEIT';

  @override
  String get guideTopic2 => 'QUOTE';

  @override
  String get guideTopic3 => 'HOHE WAHRSCHEINLICHKEIT';

  @override
  String get guideTopic4 => 'KOMBIWETTE';

  @override
  String get guideTopic5 => 'TREPPEN-CHALLENGE';

  @override
  String get guideTopic6 => 'VERANTWORTUNG';

  @override
  String get homeBannerClose => 'Hinweis schließen';

  @override
  String get homeByDate => 'Spiele nach Datum und Uhrzeit';

  @override
  String homeForecastAt(String when, String mexico) {
    return 'Prognose am $when ($mexico Uhr mexikanischer Zeit)';
  }

  @override
  String get homeForecastPending => 'Prognose ausstehend';

  @override
  String get homeMenuTooltip => 'Menü';

  @override
  String get homeNoMatchesDay => 'An diesem Tag gibt es keine Spiele.';

  @override
  String get homeSeeAll => 'Alle ansehen';

  @override
  String homeTicketJoint(String percent) {
    return 'Gem. Wahrsch. $percent';
  }

  @override
  String homeTicketLegs(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count Auswahlen',
      one: '$count Auswahl',
    );
    return '$_temp0';
  }

  @override
  String homeTicketOdds(String value) {
    return 'Quote $value';
  }

  @override
  String get homeTicketsEmpty => 'Heute noch keine Scheine';

  @override
  String get homeTicketsTitle => 'Scheine des Tages';

  @override
  String get homeToday => 'Heute';

  @override
  String get homeTomorrow => 'Morgen';

  @override
  String get inboxEmpty => 'Du hast noch keine Hinweise.';

  @override
  String get inboxMatch => 'Spiel';

  @override
  String get inboxTitle => 'Hinweise';

  @override
  String ladderActiveCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count Challenges laufen',
      one: '1 Challenge läuft',
    );
    return '$_temp0';
  }

  @override
  String get ladderBalance => 'aktuelles Guthaben';

  @override
  String get ladderChance => 'bis zum Abschluss';

  @override
  String get ladderEmpty => 'Es sind keine aktiven Challenges veröffentlicht.';

  @override
  String ladderEstimateNote(String avg) {
    return 'Schätzung: nutzt die Wahrscheinlichkeit der laufenden Stufe und den Durchschnitt der übrigen ($avg). Keine Garantie.';
  }

  @override
  String get ladderFreeHint =>
      'Eine kostenlose Stufe: die mit der höchsten Wahrscheinlichkeit.';

  @override
  String get ladderHideSteps => 'Stufen ausblenden';

  @override
  String get ladderHistoryDone => 'Geschafft';

  @override
  String get ladderHistoryEmpty =>
      'Noch keine beendeten Challenges. Sobald eine endet, erscheint sie hier mit ihrem Ergebnis.';

  @override
  String ladderHistoryFailedAt(int step) {
    return 'Gescheitert an Stufe $step';
  }

  @override
  String get ladderHistoryShown =>
      'Angezeigt werden die zuletzt geschafften Challenges und die letzte gescheiterte.';

  @override
  String get ladderHistoryTitle => 'Challenge-Verlauf';

  @override
  String get ladderNoteInPlay =>
      'Eine Stufe wartet auf ihr Ergebnis. Die Challenge läuft weiter.';

  @override
  String get ladderNoteToPick =>
      'Die nächste Stufe steht noch aus; das kann Tage dauern. Die Challenge läuft weiter.';

  @override
  String ladderRemaining(int remaining) {
    String _temp0 = intl.Intl.pluralLogic(
      remaining,
      locale: localeName,
      other: 'noch $remaining',
      one: 'noch 1',
    );
    return '$_temp0';
  }

  @override
  String get ladderShowSteps => 'Stufen anzeigen';

  @override
  String get ladderStatusInPlay => 'Läuft';

  @override
  String get ladderStatusToPick => 'Auswahl offen';

  @override
  String ladderTitle(Object id, int steps) {
    String _temp0 = intl.Intl.pluralLogic(
      steps,
      locale: localeName,
      other: '$steps Stufen',
      one: '$steps Stufe',
    );
    return 'Challenge #$id · $_temp0';
  }

  @override
  String ladderWonOf(int won, int goal) {
    return '$won von $goal gewonnen';
  }

  @override
  String get languageFirstBadge => 'Spracheinstellung';

  @override
  String get languageFirstHint =>
      'Lege die Sprache der Analyse für ein besseres Erlebnis fest';

  @override
  String get languageFirstTitle => 'Wähle deine Sprache';

  @override
  String get languageHint =>
      'Wähle die Sprache. Sie wird auf diesem Gerät und in deinem Konto gespeichert.';

  @override
  String get languageTitle => 'App-Sprache';

  @override
  String get ledgerAd => 'Video mit Belohnung';

  @override
  String get ledgerAttendance => 'Check-in';

  @override
  String get ledgerInvitee => 'Willkommensprämie';

  @override
  String get ledgerOffer => 'Angebot abgeschlossen';

  @override
  String get ledgerReferralReversal => 'Empfehlungsprämie zurückgebucht';

  @override
  String get ledgerReferrer => 'Empfehlungsprämie';

  @override
  String get ledgerReversal => 'Angebot storniert';

  @override
  String get ledgerUnlock => 'Prognose freigeschaltet';

  @override
  String get levelHigh => 'HOHE WAHRSCH.';

  @override
  String get levelModerate => 'MODERAT';

  @override
  String get levelSolid => 'SOLIDE';

  @override
  String get lineAwayScores => 'Gastteam trifft · über 0,5 Tore';

  @override
  String get lineDoubleChance => 'Doppelte Chance · 1X / X2 / 12';

  @override
  String lineHandicap(String line) {
    return 'Handicap $line';
  }

  @override
  String get lineHomeScores => 'Heimteam trifft · über 0,5 Tore';

  @override
  String lineTeamCorners(String team, String side, String line) {
    String _temp0 = intl.Intl.selectLogic(side, {
      'over': 'über $line Ecken',
      'other': 'unter $line Ecken',
    });
    return '$team: $_temp0';
  }

  @override
  String get lineWinner => 'Sieger · Auswahl mit hoher Wahrscheinlichkeit';

  @override
  String get maintenanceNotice =>
      'Wir führen Wartungsarbeiten durch. Einige Funktionen können länger dauern.';

  @override
  String get marketAwayScores => 'Gastteam trifft';

  @override
  String get marketBtts => 'Beide Teams treffen';

  @override
  String get marketCards => 'Karten';

  @override
  String get marketCorners => 'Ecken';

  @override
  String get marketCornersAway => 'Ecken des Gastteams';

  @override
  String get marketCornersHome => 'Ecken des Heimteams';

  @override
  String get marketDoubleChance => 'Doppelte Chance';

  @override
  String get marketGoals => 'Tore';

  @override
  String get marketGoalsAway => 'Tore des Gastteams';

  @override
  String get marketGoalsHome => 'Tore des Heimteams';

  @override
  String get marketHandicap => 'Handicap';

  @override
  String get marketHomeScores => 'Heimteam trifft';

  @override
  String get marketHtBtts => 'Beide Teams treffen in der 1. Halbzeit';

  @override
  String get marketHtGoal => 'Tor in der 1. Halbzeit';

  @override
  String get marketResult1x2 => 'Ergebnis 1X2';

  @override
  String get marketUnknown => 'Markt';

  @override
  String get marketWinToNil => 'Sieg ohne Gegentor';

  @override
  String get marketsAndResults => 'Märkte und Ergebnisse';

  @override
  String marketsEvidenceAt(String date) {
    return 'Stand der Belege: $date';
  }

  @override
  String get marketsFamiliesRadar => 'Marktfamilien im Radar';

  @override
  String marketsHistoricHit(String percent) {
    return 'historische Trefferquote $percent';
  }

  @override
  String get marketsInReview => 'In Prüfung: keine bestätigte Linie';

  @override
  String get marketsModelActive => 'MODELL AKTIV';

  @override
  String get marketsNoLineLabel => 'keine bestätigte Linie';

  @override
  String get marketsNoPublications => 'Noch keine Veröffentlichungen';

  @override
  String get marketsNoResolved => 'Keine ausgewerteten Prognosen';

  @override
  String marketsPublished(int won, int cases) {
    return 'Veröffentlicht $won/$cases';
  }

  @override
  String marketsPublishedWon(int won, int cases, String percent) {
    return '$won/$cases veröffentlichte gewonnen · $percent';
  }

  @override
  String get marketsRadarNote =>
      'Der Ring ist die historische Trefferquote der besten validierten Linie jedes Marktes; „Veröffentlicht“ sind die bereits ausgewerteten Prognosen. Es sind Prognosen vor dem Spiel, keine Live-Hinweise, und keine Wahrscheinlichkeit garantiert ein Ergebnis.';

  @override
  String mdCornersTotal(Object total) {
    return 'Ecken · gesamt $total';
  }

  @override
  String get mdEmptyHistory =>
      'In diesem Markt gibt es noch keine ausgewerteten Prognosen.';

  @override
  String get mdEmptyToday =>
      'Für diesen Markt sind derzeit keine Prognosen verfügbar. Sie erscheinen, wenn das Modell sie vor dem Spiel veröffentlicht.';

  @override
  String get mdHitRate => 'Trefferquote';

  @override
  String get mdLineConfirmed => 'Bestätigt';

  @override
  String get mdLineNotDeployed => 'Nicht eingesetzt';

  @override
  String get mdLineReview => 'In Prüfung';

  @override
  String get mdLineShort => 'Kleine Stichprobe';

  @override
  String get mdLoadError => 'Der Verlauf konnte nicht geladen werden.';

  @override
  String get mdModel => 'MODELL';

  @override
  String get mdNoDate => 'Ohne Datum';

  @override
  String get mdOverall => 'Gesamt';

  @override
  String get mdTabPrevious => 'Frühere';

  @override
  String mdTabToday(int count) {
    return 'Heute ($count)';
  }

  @override
  String get mdValidatedLines => 'Validierte Linien';

  @override
  String get mmChance => 'GELEGENHEIT';

  @override
  String get mmDisclaimer =>
      'Das ist eine Modellanalyse, keine Wettempfehlung. Die „faire Quote“ ist 1/Wahrscheinlichkeit: Sie ist keine Buchmacherquote. Eine Prognose kann scheitern.';

  @override
  String get mmFairOdds => 'faire Quote';

  @override
  String mmGroupCount(String group, int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count Märkte',
      one: '$count Markt',
    );
    return '$group · $_temp0';
  }

  @override
  String mmLocked(int count) {
    return '$count gesperrt';
  }

  @override
  String mmOpen(int count) {
    return '$count offen';
  }

  @override
  String mmProb(int value) {
    return '$value % Wahrsch.';
  }

  @override
  String get mmPublishedOdds => 'veröffentlichte Quote';

  @override
  String get mmScoresTitle => 'Wahrscheinlichste Ergebnisse';

  @override
  String get mmScoresVip => 'Die wahrscheinlichsten Ergebnisse sind für VIP.';

  @override
  String get mmTitle => 'Spielmärkte';

  @override
  String get moreApp => 'App';

  @override
  String get moreGuide => 'Prognose-Leitfaden';

  @override
  String get moreGuideSub =>
      'Wahrscheinlichkeiten, Quoten und Challenges lesen';

  @override
  String get moreLearn => 'Lernen';

  @override
  String get moreLegal => 'Rechtliches';

  @override
  String get moreRate => 'App bewerten';

  @override
  String get moreRateSub => 'Teile deine Meinung';

  @override
  String get moreShare => 'App teilen';

  @override
  String get moreShareMessage =>
      'Schau dir QuantFut an: Fußball-Wahrscheinlichkeiten auf Datenbasis, ohne Versprechen. https://pronosticosdeportivos.pro';

  @override
  String get moreShareSub => 'Lade deine Freunde ein';

  @override
  String get moreStoreError => 'Der App-Store konnte nicht geöffnet werden.';

  @override
  String get navCoins => 'Coins';

  @override
  String get navHome => 'Start';

  @override
  String get navMarkets => 'Märkte';

  @override
  String get navPredictions => 'Prognosen';

  @override
  String get navProfile => 'Profil';

  @override
  String noteExpectedAverage(String value) {
    return 'Erwarteter Durchschnitt: $value';
  }

  @override
  String noteExpectedGoals(String value) {
    return 'Erwartete Tore: $value';
  }

  @override
  String noteXg(String home, String homeValue, String away, String awayValue) {
    return 'xG: $home $homeValue · $away $awayValue';
  }

  @override
  String get notificationIosPending =>
      'iOS-Benachrichtigungen warten auf die Apple-Konfiguration.';

  @override
  String get notificationPermissionDenied =>
      'Aktiviere die Berechtigung in den Geräteeinstellungen.';

  @override
  String get outcomeLoss => 'Verloren';

  @override
  String get outcomePush => 'Erstattet';

  @override
  String get outcomeWin => 'Gewonnen';

  @override
  String parleyChipLine(int count, String min, String max) {
    return 'Bis zu $count Kombiwetten · Quote $min–$max';
  }

  @override
  String parleyDayCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count Kombiwetten',
      one: '$count Kombiwette',
    );
    return '$_temp0';
  }

  @override
  String parleyDaySettled(int won, int settled) {
    return '$won/$settled gewonnen';
  }

  @override
  String get parleyDisclaimer =>
      'Sie wird nach Wahrscheinlichkeit gewählt, nicht nach Wert, und jeder Tipp verringert die Marge. Eine Kombiwette kann scheitern: Quoten zu multiplizieren vervielfacht auch das Risiko.';

  @override
  String get parleyFewNote =>
      'Mit wenigen Kombiwetten beweist die tatsächliche Quote noch nichts.';

  @override
  String get parleyFreeChip => '1 kostenlos pro Tag';

  @override
  String get parleyFreeNote =>
      'Eine pro Tag kostenlos (die mit der niedrigsten Quote); der Rest ist VIP.';

  @override
  String get parleyHistoryTitle => 'Verlauf der Kombiwette';

  @override
  String get parleyInactiveBody =>
      'Sobald sie aktiviert ist, siehst du hier die Kombiwetten des Tages, versiegelt vor Spielbeginn.';

  @override
  String get parleyInactiveTitle => 'Die Kombiwette ist noch nicht aktiv';

  @override
  String get parleyInfoTitle => 'So wird eine Kombiwette gewählt';

  @override
  String parleyJointProb(String percent, int legs) {
    String _temp0 = intl.Intl.pluralLogic(
      legs,
      locale: localeName,
      other: '$legs Tipps',
      one: '$legs Tipp',
    );
    return '$percent gemeinsame Wahrscheinlichkeit · $_temp0';
  }

  @override
  String get parleyLoadError => 'Die Kombiwette konnte nicht geladen werden.';

  @override
  String get parleyNoHistory =>
      'Noch kein Verlauf. Er erscheint hier, sobald die erste Kombiwette abgerechnet ist.';

  @override
  String get parleyNoneBody =>
      'Das Modell veröffentlicht keine Kombiwette, wenn es keine innerhalb der Regeln findet.';

  @override
  String get parleyNoneTitle => 'Heute gibt es keine Kombiwetten';

  @override
  String parleyOddsBetween(String min, String max) {
    return 'Quote zwischen $min und $max';
  }

  @override
  String get parleyOutcomeLoss => 'Verloren';

  @override
  String get parleyOutcomePending => 'Ausstehend';

  @override
  String get parleyOutcomeVoid => 'Annulliert';

  @override
  String get parleyOutcomeWin => 'Gewonnen';

  @override
  String get parleyPastDays => 'Frühere Tage';

  @override
  String parleyRange(int count, String min, String max) {
    return '1 bis $count Kombiwetten · Quote zwischen $min und $max · die wahrscheinlichste jeder Stufe';
  }

  @override
  String parleyResultScore(Object score) {
    return 'Ergebnis $score';
  }

  @override
  String get parleySealed => 'Vor den Spielen versiegelte Kombiwetten';

  @override
  String parleyStep(Object step) {
    return 'STUFE $step';
  }

  @override
  String parleySummary(Object hits, Object total) {
    return '$hits/$total Kombiwetten gewonnen';
  }

  @override
  String parleySummaryPromised(String value) {
    return ' gegenüber $value % versprochen';
  }

  @override
  String parleySummaryReal(String value) {
    return ' · $value % tatsächlich';
  }

  @override
  String pickOddsAtPublish(Object book) {
    return 'Quote bei Veröffentlichung · $book';
  }

  @override
  String pickProbability(String percent) {
    return 'Wahrscheinlichkeit $percent';
  }

  @override
  String get pickSeeAnalysis => 'Spielanalyse ansehen';

  @override
  String get pickSourceNA => 'Quelle nicht verfügbar';

  @override
  String pickUnlockCoins(Object cost) {
    return 'Für $cost Münzen freischalten';
  }

  @override
  String get pickUnlockPrompt => 'Schalte die Prognose und ihre Quote frei.';

  @override
  String get pickUnlockVip => 'VIP-Prognose freischalten';

  @override
  String picksAllHeading(int count) {
    return 'Prognosen · $count';
  }

  @override
  String get picksBestProb => 'Höchste Wahrscheinlichkeit';

  @override
  String picksCoinsShort(Object cost) {
    return '$cost Münzen';
  }

  @override
  String get picksEmpty =>
      'In diesem Bereich sind keine veröffentlichten Prognosen offen.';

  @override
  String picksFreeHeading(int count) {
    return 'Kostenlos · $count';
  }

  @override
  String get picksLockedHide => 'Liste ausblenden';

  @override
  String get picksLockedHint =>
      'Mit VIP siehst du die Prognose, die Wahrscheinlichkeit und die Analyse';

  @override
  String get picksLockedShow => 'Liste anzeigen';

  @override
  String picksLockedTitle(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count weitere Prognosen mit VIP',
      one: '1 weitere Prognose mit VIP',
    );
    return '$_temp0';
  }

  @override
  String picksRangeHint(int min, int max, int free) {
    return '$min–$max % Wahrscheinlichkeit · bis zu $free kostenlos';
  }

  @override
  String get picksSeeAnalysis => 'Analyse ansehen';

  @override
  String get picksTomorrow => 'Morgen';

  @override
  String picksTrainingReasons(String reasons) {
    return 'Modell im Training · $reasons';
  }

  @override
  String picksTrustDetail(int hits, int total) {
    return '$hits von $total Prognosen';
  }

  @override
  String picksTrustPromised(String percent) {
    return 'Versprochen: $percent';
  }

  @override
  String get picksTrustTitle => 'Bisherige Trefferquote';

  @override
  String get prefsAdsBody =>
      'Teilt verschlüsselte Konto-, Geräte- und Kaufdaten mit Meta, um zu messen, welche Anzeigen wirken. In Kalifornien bedeutet das Deaktivieren „Meine Daten nicht teilen“.';

  @override
  String get prefsAdsTitle => 'Anzeigenmessung (Meta)';

  @override
  String get prefsAnalyticsBody =>
      'Hilft, die App mit Daten zu den genutzten Bildschirmen zu verbessern. Optional.';

  @override
  String get prefsAnalyticsTitle => 'Nutzungsmessung';

  @override
  String get prefsDeleteAccount => 'Löschung meines Kontos beantragen';

  @override
  String get prefsDeleteAccountHint =>
      'Sieh dir die Schritte und den Kontakt von Saptain LTD an.';

  @override
  String get prefsDiagnosticsBody =>
      'Sendet technische Informationen an Firebase und Sentry, um Fehler zu diagnostizieren. Optional.';

  @override
  String get prefsDiagnosticsTitle => 'Fehler- und Leistungsberichte';

  @override
  String get prefsInbox => 'Hinweis-Postfach';

  @override
  String get prefsLanguageNote =>
      'Die Sprache gilt für die gesamte App und wird als Einstellung gespeichert.';

  @override
  String get prefsNote =>
      'Du kannst die Grundfunktionen nutzen, ohne Messung oder Diagnose zu aktivieren. Das Ändern dieser Optionen löscht bereits gesendete Daten nicht automatisch.';

  @override
  String get prefsNotificationsOff =>
      'Verfügbar, sobald die Google-Anmeldung abgeschlossen ist.';

  @override
  String get prefsNotificationsOn =>
      'Du kannst sie jederzeit ausschalten. Hinweise können auf dem Sperrbildschirm erscheinen.';

  @override
  String get prefsNotificationsTitle => 'QuantFut-Benachrichtigungen';

  @override
  String get prefsPrivacyRights => 'Datenschutz und deine Rechte';

  @override
  String get prefsTitle => 'Datenschutz und Einstellungen';

  @override
  String get privacyUpdateBody =>
      'Du kannst jetzt über Google Play oder den App Store abonnieren, und Nutzungsmessung, Diagnose und Meta-Anzeigenmessung sind aktiviert. Du kannst sie in den Einstellungen deaktivieren.';

  @override
  String get privacyUpdateOk => 'Verstanden';

  @override
  String get privacyUpdateRead => 'Richtlinie lesen';

  @override
  String get privacyUpdateTitle => 'Wir haben den Datenschutz aktualisiert';

  @override
  String get probBarAway => 'Gast';

  @override
  String get probBarDraw => 'Unent.';

  @override
  String get probBarHome => 'Heim';

  @override
  String get profileAppVersion => 'App-Version';

  @override
  String get profileBalance => 'Bilanz und Verlauf';

  @override
  String get profileConnected => 'QuantFut · Mit dem Server verbunden';

  @override
  String get profileCreateAccount => 'Konto erstellen';

  @override
  String get profileCreateOne => 'Ein Konto erstellen';

  @override
  String get profileEmail => 'E-Mail';

  @override
  String get profileEmailPending => 'E-Mail noch nicht bestätigt';

  @override
  String get profileEmailVerified => 'E-Mail bestätigt';

  @override
  String get profileForgot => 'Passwort vergessen';

  @override
  String get profileForgotSent =>
      'Falls das Konto existiert, erhältst du die Anweisungen per E-Mail.';

  @override
  String get profileFreePlan => 'Kostenloser Plan';

  @override
  String get profileGeneral => 'Allgemein';

  @override
  String get profileHaveAccount => 'Ich habe bereits ein Konto';

  @override
  String get profileLanguage => 'Sprache';

  @override
  String get profileMeasurement => 'Messung und Fehler';

  @override
  String get profileNotifications => 'Benachrichtigungen';

  @override
  String get profileOddsFormat => 'Quotenformat';

  @override
  String get profileOddsFormatValue =>
      'Dezimal · Zum Veröffentlichungszeitpunkt erfasste Quoten';

  @override
  String get profilePassword => 'Passwort';

  @override
  String get profilePreferences => 'Einstellungen';

  @override
  String get profileRefreshAccess => 'Meinen Zugang aktualisieren';

  @override
  String get profileSeePlans => 'VIP-Pläne ansehen';

  @override
  String get profileSendVerification => 'Bestätigungs-E-Mail senden';

  @override
  String get profileSignIn => 'Anmelden';

  @override
  String get profileSignOut => 'Abmelden';

  @override
  String get profileTitle => 'Profil und Einstellungen';

  @override
  String profileValidUntil(String date) {
    return 'Gültig bis: $date';
  }

  @override
  String get profileVerificationSent => 'Bestätigungs-E-Mail gesendet.';

  @override
  String get profileVipActive => 'VIP-Zugang aktiv';

  @override
  String get profileYourAccount => 'Dein QuantFut-Konto';

  @override
  String resultLabel(String score) {
    return 'Ergebnis: $score';
  }

  @override
  String get rewardsAttendanceSub => 'Einmal täglich · Neustart um 00:00 UTC';

  @override
  String get rewardsAttendanceTitle => 'Tägliches Einchecken';

  @override
  String get rewardsAvailable => 'Verfügbar';

  @override
  String get rewardsCheckIn => 'Einchecken';

  @override
  String get rewardsCheckInNote =>
      'Einmal pro UTC-Tag. Wenn du einen Tag auslässt, beginnt die Serie von vorn.';

  @override
  String rewardsChipRate(Object cost) {
    return '$cost Münzen = 1 Prognose';
  }

  @override
  String rewardsChipStreak(int days) {
    String _temp0 = intl.Intl.pluralLogic(
      days,
      locale: localeName,
      other: 'Serie: $days Tage',
      one: 'Serie: 1 Tag',
    );
    return '$_temp0';
  }

  @override
  String rewardsClaimCta(Object coins) {
    return 'Einchecken · +$coins';
  }

  @override
  String rewardsClaimed(Object coins) {
    return '+$coins Münzen';
  }

  @override
  String get rewardsClaimedToday => 'Heute eingelöst';

  @override
  String get rewardsCodeCopied => 'Code kopiert.';

  @override
  String get rewardsCodeRegistered => 'Einladungscode registriert.';

  @override
  String rewardsComingSoon(String names) {
    return 'Demnächst: $names';
  }

  @override
  String get rewardsCopy => 'Kopieren';

  @override
  String rewardsCopyCode(Object code) {
    return 'Meinen Code kopieren · $code';
  }

  @override
  String rewardsDay(int number) {
    return 'Tag $number';
  }

  @override
  String get rewardsDebt => 'Offenes Guthaben wegen stornierter Belohnungen.';

  @override
  String get rewardsEarnTitle => 'Verdiene heute Münzen';

  @override
  String get rewardsEnough => 'Du hast genug Münzen für eine Freischaltung.';

  @override
  String get rewardsGo => 'Los';

  @override
  String rewardsInviteChip(Object coins) {
    return '+$coins für dich';
  }

  @override
  String rewardsInviteCondition(Object min) {
    return 'Nach der E-Mail-Bestätigung und $min Münzen aus bestätigten Angeboten.';
  }

  @override
  String rewardsInviteFriend(Object coins) {
    return 'Dein Freund erhält +$coins, wenn er deinen Code eingibt';
  }

  @override
  String rewardsInviteReward(Object referrer, Object invitee) {
    return 'Du +$referrer · Dein Freund +$invitee Münzen';
  }

  @override
  String get rewardsInviteTitle => 'Lade deine Freunde ein';

  @override
  String get rewardsInviterCode => 'Code der Person, die dich eingeladen hat';

  @override
  String get rewardsLedgerEmpty => 'Noch keine Buchungen.';

  @override
  String get rewardsLedgerLess => 'Weniger anzeigen';

  @override
  String get rewardsLedgerMore => 'Mehr anzeigen';

  @override
  String get rewardsLedgerTitle => 'Meine Buchungen';

  @override
  String rewardsMissing(int missing) {
    String _temp0 = intl.Intl.pluralLogic(
      missing,
      locale: localeName,
      other: 'Noch $missing Münzen bis zur nächsten Freischaltung.',
      one: 'Noch $missing Münze bis zur nächsten Freischaltung.',
    );
    return '$_temp0';
  }

  @override
  String get rewardsMissingUnknown =>
      'Noch — Münzen bis zur nächsten Freischaltung.';

  @override
  String get rewardsMyCoins => 'Meine Münzen';

  @override
  String rewardsNextIn(String time) {
    return 'Nächstes Einchecken in $time';
  }

  @override
  String get rewardsOfferAvailable => 'Angebote je nach Land und Gerät';

  @override
  String get rewardsOfferPending => 'Aktivierung ausstehend';

  @override
  String get rewardsOffersConfig =>
      'Dieser Anbieter ist noch nicht bereit. Versuche es später erneut.';

  @override
  String get rewardsOffersCta => 'Angebote ansehen';

  @override
  String get rewardsOffersLead => 'Schließe Angebote ab und erhalte Münzen.';

  @override
  String get rewardsOffersLoadFailed =>
      'Die Angebote konnten nicht geöffnet werden. Prüfe deine Verbindung und versuche es erneut.';

  @override
  String get rewardsOffersTimeout =>
      'Das Laden der Angebote hat zu lange gedauert. Versuche es erneut.';

  @override
  String get rewardsOffersTitle => 'Angebote, um Münzen zu verdienen';

  @override
  String get rewardsOffersUnavailable =>
      'Zurzeit sind keine Angebote verfügbar. Versuche es später erneut.';

  @override
  String get rewardsOperationDone => 'Vorgang bestätigt.';

  @override
  String get rewardsPaste => 'Code einfügen';

  @override
  String get rewardsPasteEmpty =>
      'In der Zwischenablage befindet sich kein Einladungscode.';

  @override
  String rewardsReferralStats(Object registered, Object qualified) {
    return '$registered registriert · $qualified bestätigt';
  }

  @override
  String get rewardsRefreshBalance => 'Guthaben aktualisieren';

  @override
  String get rewardsRegisterCode => 'Code registrieren';

  @override
  String get rewardsShare => 'Meinen Code teilen';

  @override
  String rewardsShareMessage(String code, String link) {
    return 'Nutze meinen Einladungscode $code in QuantFut: Gib ihn in Coins bei „Code der Person, die dich eingeladen hat“ ein. Alles erklärt hier: $link';
  }

  @override
  String get rewardsSignIn => 'Anmelden';

  @override
  String get rewardsSignInHint =>
      'Melde dich im Profil an, um dein Guthaben zu speichern, dich einzuchecken und einen Empfehlungscode zu nutzen.';

  @override
  String rewardsStreak(int days) {
    String _temp0 = intl.Intl.pluralLogic(
      days,
      locale: localeName,
      other: '$days Tage',
      one: '$days Tag',
    );
    return 'Anwesenheitsserie · $_temp0';
  }

  @override
  String get rewardsTermsTitle => 'Regeln und Bedingungen';

  @override
  String rewardsUnlockFor(Object cost) {
    return 'Schalte eine Prognose für $cost Münzen frei';
  }

  @override
  String get selBttsNo => 'Nicht beide Teams treffen';

  @override
  String get selBttsYes => 'Beide Teams treffen';

  @override
  String selCards(String side, String line) {
    String _temp0 = intl.Intl.selectLogic(side, {
      'over': 'Über $line Karten',
      'other': 'Unter $line Karten',
    });
    return '$_temp0';
  }

  @override
  String selCorners(String side, String line) {
    String _temp0 = intl.Intl.selectLogic(side, {
      'over': 'Über $line Ecken',
      'other': 'Unter $line Ecken',
    });
    return '$_temp0';
  }

  @override
  String selCornersTeam(String side, String line, String team) {
    String _temp0 = intl.Intl.selectLogic(side, {
      'over': 'Über $line Ecken von $team',
      'other': 'Unter $line Ecken von $team',
    });
    return '$_temp0';
  }

  @override
  String selDrawNoBet(String team) {
    return '$team gewinnt (bei Unentschieden Einsatz zurück)';
  }

  @override
  String selEitherNoDraw(String home, String away) {
    return '$home oder $away (kein Unentschieden)';
  }

  @override
  String selGoals(String side, String line) {
    String _temp0 = intl.Intl.selectLogic(side, {
      'over': 'Über $line Tore',
      'other': 'Unter $line Tore',
    });
    return '$_temp0';
  }

  @override
  String selHandicapLong(String team, String line) {
    return '$team $line (Asiatisches Handicap)';
  }

  @override
  String selHandicapShort(String team, String line) {
    return '$team $line';
  }

  @override
  String selHomeWins(String team) {
    return '$team gewinnt';
  }

  @override
  String get selHtBttsNo => 'Nicht beide Teams treffen in der 1. Halbzeit';

  @override
  String get selHtGoalYes => 'In der 1. Halbzeit fällt ein Tor';

  @override
  String selTeamOrDraw(String team) {
    return '$team oder Unentschieden';
  }

  @override
  String selTeamScores(String team) {
    return '$team trifft';
  }

  @override
  String selWinToNil(String team) {
    return '$team gewinnt ohne Gegentor';
  }

  @override
  String get shellNeedCoinsBody =>
      'Verdiene Münzen mit dem täglichen Einchecken und Angeboten, um diese Prognose freizuschalten.';

  @override
  String get shellNeedCoinsCta => 'Münzen verdienen';

  @override
  String get shellNeedCoinsTitle => 'Dir fehlen Münzen';

  @override
  String get shellNewAlert => 'Neuer QuantFut-Hinweis';

  @override
  String get shellSignInForCoins =>
      'Melde dich im Profil an, um deine Münzen zu nutzen.';

  @override
  String shellUnlockBody(Object cost) {
    return '$cost Münzen werden von deinem Guthaben abgezogen. Der Zugang gilt für diese Prognose.';
  }

  @override
  String get shellUnlockTitle => 'Prognose freischalten';

  @override
  String get shellView => 'Ansehen';

  @override
  String get splashTagline => 'FUSSBALL · NBA · STATISTIK';

  @override
  String get startupFailed =>
      'QuantFut konnte nicht gestartet werden. Bitte versuche es erneut.';

  @override
  String get startupLoading => 'QuantFut wird gestartet';

  @override
  String statAveragesNote(Object homeN, Object awayN) {
    return 'Durchschnitte aus $homeN Spielen des Heimteams und $awayN des Gastteams. Die Abdeckung von Schüssen, Ecken und xG kann unvollständig sein.';
  }

  @override
  String get statBestAway => 'Bester Auswärtssieg';

  @override
  String get statBestHome => 'Bester Heimsieg';

  @override
  String get statCleanSheet => 'Zu null';

  @override
  String get statCompareNote =>
      'Die Balken vergleichen die erfassten Werte; sie stellen keine Siegwahrscheinlichkeiten dar. Weniger Gegentore ist besser.';

  @override
  String get statCompareTitle => 'Teamvergleich';

  @override
  String get statDrawStreak => 'Unentschieden-Serie';

  @override
  String get statFormLegend =>
      'S: Sieg · U: Unentschieden · N: Niederlage. Neuestes links.';

  @override
  String get statFormNA => 'Form nicht verfügbar.';

  @override
  String get statFormTitle => 'Form der Teams';

  @override
  String get statGoalsAgainst => 'Gegentore';

  @override
  String get statGoalsAvgNote =>
      'Erzielte Tore pro Spiel; das ist nicht die Torprognose des Modells.';

  @override
  String get statGoalsAvgTitle => 'HISTORISCHER TORDURCHSCHNITT';

  @override
  String get statGoalsFor => 'Erzielte Tore';

  @override
  String statH2hSummary(
    Object n,
    Object home,
    Object homeWins,
    Object away,
    Object awayWins,
    Object draws,
  ) {
    return 'In $n erfassten Duellen: $home gewann $homeWins, $away gewann $awayWins und es gab $draws Unentschieden.';
  }

  @override
  String get statH2hTitle => 'Direktvergleich';

  @override
  String statLastMatches(int count) {
    return 'Letzte $count erfasste Spiele';
  }

  @override
  String get statMinutesNA =>
      'Die Verteilung nach Minuten ist für dieses Spiel nicht verfügbar.';

  @override
  String get statMinutesTitle => 'Tore pro Minute';

  @override
  String get statNeedsAccess =>
      'Die Prognose für dieses Spiel erfordert VIP-Zugang oder eine Freischaltung mit Münzen.';

  @override
  String get statOnTargetShort => 'Aufs Tor';

  @override
  String get statOver25 => 'Über 2,5 Tore';

  @override
  String statPickProbOdds(String percent, String odds) {
    return 'Wahrscheinlichkeit $percent · Quote @ $odds';
  }

  @override
  String statPlayed(Object played) {
    return '$played Spiele';
  }

  @override
  String statPoints(Object points) {
    return '$points Punkte';
  }

  @override
  String get statPoissonNA =>
      'Die Poisson-Verteilung und wahrscheinliche Ergebnisse sind in den Daten dieses Spiels noch nicht verfügbar.';

  @override
  String get statPoissonTitle => 'Poisson-Torverteilung';

  @override
  String statPosition(Object position) {
    return 'Platz $position';
  }

  @override
  String get statProbNA => 'Modellwahrscheinlichkeiten noch nicht verfügbar.';

  @override
  String get statProbTitle => 'SIEGWAHRSCHEINLICHKEIT · 1X2';

  @override
  String get statPublishedPick => 'VERÖFFENTLICHTE PROGNOSE';

  @override
  String get statRadarNeeds =>
      'Der grafische Vergleich benötigt mindestens drei verfügbare Kennzahlen beider Teams.';

  @override
  String get statRadarNote =>
      'Relative Skala pro Achse. Eine größere Fläche bedeutet keine höhere Siegwahrscheinlichkeit.';

  @override
  String get statResDraw => 'U';

  @override
  String get statResLoss => 'N';

  @override
  String get statResWin => 'S';

  @override
  String statResultsAvailable(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count Ergebnisse verfügbar',
      one: '$count Ergebnis verfügbar',
    );
    return '$_temp0';
  }

  @override
  String get statSeasonTitle => 'Saison und aktuelle Ergebnisse';

  @override
  String get statShots => 'Schüsse';

  @override
  String get statShotsOnTarget => 'Schüsse aufs Tor';

  @override
  String get statStandingNA => 'Tabelle nicht verfügbar.';

  @override
  String get statSummaryTitle => 'Prognose-Zusammenfassung';

  @override
  String get statTeamStatsTitle => 'Teamstatistiken';

  @override
  String get statWinStreak => 'Siegesserie';

  @override
  String get statXgHistoric => 'Historisches xG';

  @override
  String get streamHighProb => 'Hohe Wahrscheinlichkeit';

  @override
  String get streamLadder => 'Treppen-Challenge';

  @override
  String get streamParley => 'Kombiwette';

  @override
  String tileFairOdds(String value) {
    return 'Faire Quote $value';
  }

  @override
  String get tileFavorite => '1X2-Favorit';

  @override
  String tileFavoriteLead(String team, int pts) {
    return '$team · +$pts Pkt.';
  }

  @override
  String get tileFavoriteNA => 'Wahrscheinlichkeiten nicht verfügbar';

  @override
  String get tileGoalsNA => 'Unzureichender Verlauf';

  @override
  String get tileGoalsTrend => 'Tor-Trend';

  @override
  String get tileOver25Model => 'Über 2,5 laut Modell';

  @override
  String get tileOver25Recent => 'Über 2,5 in ihren letzten Spielen';

  @override
  String get tileProbability => 'Wahrscheinlichkeit';

  @override
  String get tileXg => 'Prognostiziertes xG';

  @override
  String tileXgCaption(String home, String away) {
    return '$home Heim · $away Gast';
  }

  @override
  String get tileXgNA => 'Verfügbar bei Tormärkten';

  @override
  String get titleAsianHandicap => 'Asiatisches Handicap';

  @override
  String get titleDrawNoBet => 'Wette ohne Unentschieden';

  @override
  String titleTeamGoals(String team) {
    return 'Tore von $team';
  }

  @override
  String get titleTotalCards => 'Karten insgesamt';

  @override
  String get titleTotalCorners => 'Ecken insgesamt';

  @override
  String get titleTotalGoals => 'Tore insgesamt';

  @override
  String get titleWinner => 'Spielsieger';

  @override
  String get tooltipVip => 'VIP';

  @override
  String get updateLater => 'Später';

  @override
  String get updateNow => 'Jetzt aktualisieren';

  @override
  String get updateOptional => 'Eine neue Version von QuantFut ist verfügbar.';

  @override
  String get updateRequired => 'Aktualisiere QuantFut, um fortzufahren.';

  @override
  String get updateStoreError =>
      'Der Store konnte nicht geöffnet werden. Versuche es erneut.';

  @override
  String get updateTitle => 'Update verfügbar';

  @override
  String get vipAccessButton => 'VIP-Zugang';

  @override
  String get vipActivate => 'VIP-Zugang aktivieren';

  @override
  String get vipActive => 'Dein VIP-Zugang ist aktiv.';

  @override
  String get vipBadge => '✦  VIP-ZUGANG';

  @override
  String get vipBenefit1Body => 'Jede Prognose wird vor dem Spiel versiegelt';

  @override
  String get vipBenefit1Title => 'Überprüfbarer Verlauf';

  @override
  String vipBenefit2Body(int min, int max) {
    return 'Alle Prognosen von $min bis $max %, ohne Gratiskontingent';
  }

  @override
  String get vipBenefit2Title => 'Hohe Wahrscheinlichkeit komplett';

  @override
  String get vipBenefit3Body => 'Alle offenen Stufen, nicht nur eine';

  @override
  String get vipBenefit3Title => 'Treppen-Challenge komplett';

  @override
  String get vipBenefit4Body =>
      'Veröffentlichte Quote, Wahrscheinlichkeit und xG jeder Prognose';

  @override
  String get vipBenefit4Title => 'Quoten und Spielanalyse';

  @override
  String get vipBestPrice => '★ BESTER PREIS';

  @override
  String get vipCheckAccess => 'Meinen Zugang prüfen';

  @override
  String get vipCheckSignIn =>
      'Melde dich im Profil an, um deinen Zugang zu prüfen.';

  @override
  String vipDays(int days) {
    String _temp0 = intl.Intl.pluralLogic(
      days,
      locale: localeName,
      other: '$days Tage',
      one: '$days Tag',
    );
    return '$_temp0';
  }

  @override
  String get vipFreeAccess => 'Dein Konto hat kostenlosen Zugang.';

  @override
  String get vipGranted => 'Fertig! Dein VIP-Zugang ist aktiv.';

  @override
  String get vipHistoryNote =>
      'Öffentlicher, versiegelter Verlauf; die Stichproben pro Markt sind klein und eine Prognose kann scheitern.';

  @override
  String get vipIntro =>
      'Alle Prognosen für Hohe Wahrscheinlichkeit und die Treppen-Challenge, solange dein Abonnement gültig ist.';

  @override
  String get vipLinked => '🔒  Dein VIP-Zugang ist mit deinem Konto verknüpft';

  @override
  String get vipManage =>
      'Du hast bereits Plus. Ändere oder kündige deinen Plan im Store.';

  @override
  String vipMonthly(String amount) {
    return '≈ $amount/Monat';
  }

  @override
  String vipMonths(int months) {
    String _temp0 = intl.Intl.pluralLogic(
      months,
      locale: localeName,
      other: '$months Monate',
      one: '$months Monat',
    );
    return '$_temp0';
  }

  @override
  String get vipNoExpiry => 'Ohne Ablaufdatum';

  @override
  String get vipPaymentRequired =>
      'Für den Abschluss ist ein eingerichteter Zahlungskanal erforderlich.';

  @override
  String get vipPending =>
      'Zahlung ausstehend. Du erhältst Zugang, sobald der Store sie bestätigt.';

  @override
  String get vipPickLabel => 'VIP-Prognose';

  @override
  String get vipPlansSoon =>
      'Die Pläne werden angezeigt, sobald sie verfügbar sind.';

  @override
  String get vipPricesNote => 'Preise aus dem Serverkatalog.';

  @override
  String get vipPurchasesPending =>
      'Käufe in Vorbereitung: Über die App wird noch nichts abgerechnet.';

  @override
  String get vipRestore => 'Käufe wiederherstellen';

  @override
  String get vipStatRecorded => 'Erfasste Trefferquote';

  @override
  String get vipStatResolved => 'Ausgewertet';

  @override
  String get vipStoreFailed =>
      'Der Kauf konnte nicht bestätigt werden. Wir versuchen es beim nächsten Öffnen der App erneut.';

  @override
  String get vipStoreTerms =>
      'Verlängert sich automatisch zum gleichen Preis, bis du im Store kündigst.';

  @override
  String get vipStoreUnavailable =>
      'Der Store ist auf diesem Gerät nicht verfügbar.';

  @override
  String get vipSubscribe => 'Abonnieren';

  @override
  String get vipVerifying => 'Kauf wird beim Store überprüft…';

  @override
  String get welcome1Body =>
      'Entdecke die statistische Seite des Sports: Spiele, Analysen und Prognosen des Projekts, das du schon aus dem Web kennst.';

  @override
  String get welcome1Title => 'Fußball und NBA,\nmit anderem Blick';

  @override
  String get welcome2Body =>
      'Aktuelle Form, direkte Duelle und Statistiken helfen zu verstehen, was passieren kann. Beginne mit den Daten.';

  @override
  String get welcome2Title => 'Jedes Spiel,\nmit mehr Kontext';

  @override
  String get welcome3Body =>
      'Tore, Ecken, Handicap und NBA-Statistiken. Erfahre, was jede Analyse misst, bevor du eine Auswahl interpretierst.';

  @override
  String get welcome3Title => 'Mehr Märkte.\nMehr Informationen.';

  @override
  String get welcome4Body =>
      'Eine Prognose versteht man auch nach dem Spiel. Der Verlauf erlaubt es, Schätzungen mit Ergebnissen zu vergleichen.';

  @override
  String get welcome4Title => 'Die Ergebnisse,\nauf einen Blick';

  @override
  String get welcome5Body =>
      'Eine Wahrscheinlichkeit ist keine Gewissheit. Erkunde die Inhalte, prüfe den Kontext und bilde dir dein eigenes Urteil.';

  @override
  String get welcome5Title => 'Alles beginnt\nmit Information';

  @override
  String welcomeGoTo(int number) {
    return 'Zum Willkommensbildschirm $number';
  }

  @override
  String get welcomeNext => 'Weiter';

  @override
  String welcomeScreenOf(int page, int total) {
    return 'Bildschirm $page von $total';
  }

  @override
  String get welcomeSkip => 'Überspringen';

  @override
  String get welcomeStart => 'Los geht\'s';
}
