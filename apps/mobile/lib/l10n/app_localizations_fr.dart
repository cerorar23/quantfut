// ignore: unused_import
import 'package:intl/intl.dart' as intl;

import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for French (`fr`).
class AppLocalizationsFr extends AppLocalizations {
  AppLocalizationsFr([String locale = 'fr']) : super(locale);

  @override
  String get accessBody1 =>
      'Un modèle statistique calcule les probabilités. Une probabilité n\'est pas une certitude.';

  @override
  String get accessBody2 =>
      'Chaque jour, les plus probables, avec leur taux de réussite historique réel.';

  @override
  String get accessBody3 =>
      'Suivez l\'avancement de chaque défi et ce qu\'il reste pour le terminer.';

  @override
  String get accessBody4 =>
      'Avec sa cote et sa probabilité conjointe, pour savoir ce que vous risquez.';

  @override
  String get accessBody5 =>
      'Pointez votre présence, terminez des offres et invitez des amis pour débloquer des pronostics.';

  @override
  String get accessCardBody =>
      'Gardez votre progression et vos pièces sur tous vos appareils.';

  @override
  String get accessCardTitle => 'Connectez-vous pour continuer';

  @override
  String get accessConsent =>
      'J\'ai au moins 18 ans et j\'accepte les conditions et la politique de confidentialité.';

  @override
  String get accessConsentNeeded => 'Cochez la case pour continuer.';

  @override
  String accessConsentRich(String terms, String privacy) {
    return 'J\'ai 18 ans ou plus et j\'accepte les $terms et la $privacy.';
  }

  @override
  String get accessContinueWithGoogle => 'Continuer avec Google';

  @override
  String get accessDisclaimer =>
      'À titre informatif et de divertissement uniquement. Les pronostics ne garantissent pas les résultats.';

  @override
  String get accessDocumentOpenError => 'Impossible d\'ouvrir le document.';

  @override
  String get accessForgotLink => 'Récupérer l\'ancien mot de passe';

  @override
  String get accessForgotSent =>
      'Si le compte existe, vous recevrez des instructions par e-mail.';

  @override
  String get accessGenericError =>
      'Impossible de terminer la connexion. Veuillez réessayer.';

  @override
  String get accessGoogleError =>
      'Impossible de se connecter avec Google. Veuillez réessayer.';

  @override
  String get accessKicker1 => 'PROBABILITÉS RÉELLES';

  @override
  String get accessKicker2 => 'HAUTE PROBABILITÉ';

  @override
  String get accessKicker3 => 'DÉFI ESCALIER';

  @override
  String get accessKicker4 => 'COMBINÉ';

  @override
  String get accessKicker5 => 'PIÈCES';

  @override
  String get accessLinkButton => 'Associer mon compte';

  @override
  String get accessLinkEmail => 'E-mail de votre ancien compte';

  @override
  String get accessLinkIntro =>
      'Associez votre ancien compte pour conserver votre solde et votre accès.';

  @override
  String get accessLinkPassword => 'Ancien mot de passe';

  @override
  String get accessOtherAccount => 'Utiliser un autre compte';

  @override
  String get accessPreparingDocs => 'Nous préparons les documents d\'accès.';

  @override
  String get accessPrivacy => 'Politique de confidentialité';

  @override
  String get accessRetry => 'Réessayer la connexion';

  @override
  String get accessTagline =>
      'Matchs, analyses et historique. Une probabilité n\'est pas une certitude.';

  @override
  String get accessTerms => 'Conditions d\'utilisation';

  @override
  String get accessTitle1 => 'Comprenez chaque match avec des données.';

  @override
  String get accessTitle2 =>
      'Des pronostics avec leur taux de réussite visible.';

  @override
  String get accessTitle3 => 'Montez palier par palier.';

  @override
  String get accessTitle4 => 'Un ticket scellé avant les matchs.';

  @override
  String get accessTitle5 => 'Gagnez des pièces et débloquez.';

  @override
  String get adsCardTitle => 'Vidéos avec récompense';

  @override
  String get adsFootnote =>
      'Les pièces sont créditées à la fin de la vidéo. Si vous la fermez avant, vous n\'en recevez pas.';

  @override
  String get adsLimitReached =>
      'Limite du jour atteinte. Revenez après 00:00 UTC.';

  @override
  String get adsLoading => 'Chargement de la vidéo…';

  @override
  String get adsPending => 'Vos pièces arriveront dans un instant.';

  @override
  String adsProgress(int used, int cap) {
    return 'Aujourd\'hui : $used sur $cap';
  }

  @override
  String get adsUnavailable =>
      'Aucune vidéo disponible pour le moment. Réessayez plus tard.';

  @override
  String get adsVerifying => 'Vérification de votre récompense…';

  @override
  String adsWaitFor(String time) {
    return 'Prochaine vidéo dans $time';
  }

  @override
  String adsWatchCta(int coins) {
    return 'Voir la vidéo · +$coins pièces';
  }

  @override
  String alertsAbsencesOf(String team) {
    return 'Absences de $team';
  }

  @override
  String get alertsAdvantage => 'Avantage';

  @override
  String get alertsAdvantageEmpty => 'Aucun avantage signalé.';

  @override
  String alertsChecked(String when) {
    return 'Vérifié $when';
  }

  @override
  String get alertsDisadvantage => 'Désavantage';

  @override
  String get alertsDisadvantageEmpty => 'Aucun désavantage signalé.';

  @override
  String get alertsDoubt => 'Incertain';

  @override
  String get alertsNoCheck =>
      'Il n\'y a pas encore de vérification des absences pour ce match. Si sa ligue n\'a pas cette donnée, cela ne veut pas dire qu\'il n\'y a aucun blessé.';

  @override
  String get alertsNote =>
      'Les absences peuvent changer jusqu\'au coup d\'envoi. La composition officielle est publiée peu avant le match.';

  @override
  String get alertsOut => 'Indisponible';

  @override
  String get alertsReasonFoot => 'Blessure à la cheville ou au pied';

  @override
  String get alertsReasonIllness => 'Maladie';

  @override
  String get alertsReasonInjury => 'Blessure';

  @override
  String get alertsReasonKnee => 'Blessure au genou';

  @override
  String get alertsReasonKnock => 'Choc';

  @override
  String get alertsReasonMuscle => 'Blessure musculaire';

  @override
  String get alertsReasonSuspension => 'Suspension';

  @override
  String get alertsReasonUnknown => 'Motif non précisé';

  @override
  String get alertsSource => 'Source : API-Football';

  @override
  String alertsSummary(int out, int doubt) {
    String _temp0 = intl.Intl.pluralLogic(
      out,
      locale: localeName,
      other: '$out absents',
      one: '1 absent',
    );
    String _temp1 = intl.Intl.pluralLogic(
      doubt,
      locale: localeName,
      other: '$doubt incertains',
      one: '1 incertain',
    );
    return '$_temp0 · $_temp1';
  }

  @override
  String get alertsSuspended => 'Suspendu';

  @override
  String get apiGoogleNotVerified =>
      'Google n\'a pas pu vérifier la connexion.';

  @override
  String get apiInvalidResponse => 'Réponse invalide du serveur.';

  @override
  String get apiInvalidSession => 'Session invalide.';

  @override
  String apiLoadFailed(int status) {
    return 'Impossible de charger les informations (HTTP $status).';
  }

  @override
  String get apiOffline =>
      'Connexion impossible. Vérifiez votre connexion et réessayez.';

  @override
  String get apiSessionExpired => 'Reconnectez-vous.';

  @override
  String get apiSignInWithGoogle => 'Connectez-vous avec Google.';

  @override
  String get artAnalyzeEach => 'ANALYSEZ CHAQUE CHOIX';

  @override
  String get artCorners => 'CORNERS';

  @override
  String get artFootball => 'FOOTBALL';

  @override
  String get artForm => 'FORME';

  @override
  String get artGoals => 'BUTS';

  @override
  String get artHeadToHead => 'FACE À FACE';

  @override
  String get artHeading0 => 'FOOTBALL + NBA';

  @override
  String get artHeading1 => 'LE CONTEXTE COMPTE';

  @override
  String get artHeading2 => 'EXPLOREZ LES MARCHÉS';

  @override
  String get artHeading3 => 'HISTORIQUE VISIBLE';

  @override
  String get artHeading4 => 'DONNÉES + VOTRE AVIS';

  @override
  String get artNba => 'NBA';

  @override
  String get artStats => 'STATISTIQUES';

  @override
  String get artTagline => 'ANALYSEZ. COMPAREZ. EXPLOREZ.';

  @override
  String get artTransparency => 'TRANSPARENCE';

  @override
  String get bannerLive =>
      'MATCH EN COURS · pronostic scellé avant le coup d\'envoi';

  @override
  String bannerLost(String score) {
    return 'PERDU$score · pronostic scellé avant le coup d\'envoi';
  }

  @override
  String bannerWon(String score) {
    return 'GAGNÉ$score · pronostic scellé avant le coup d\'envoi';
  }

  @override
  String get calendarEmpty => 'Aucune affiche pour ces filtres.';

  @override
  String calendarMatchesCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count affiches',
      one: '$count affiche',
    );
    return '$_temp0';
  }

  @override
  String get calendarPickDate => 'Choisir la date';

  @override
  String get calendarSearchHint => 'Recherchez des équipes ou des ligues';

  @override
  String get calendarTitle => 'Calendrier · heure locale';

  @override
  String casesCount(int count, String formatted) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$formatted cas',
      one: '$formatted cas',
    );
    return '$_temp0';
  }

  @override
  String get commonAll => 'Tous';

  @override
  String get commonAway => 'Extérieur';

  @override
  String get commonCancel => 'Annuler';

  @override
  String get commonClose => 'Fermer';

  @override
  String get commonConfirm => 'Confirmer';

  @override
  String get commonConnecting => 'Connexion…';

  @override
  String get commonDraw => 'Nul';

  @override
  String get commonHome => 'Domicile';

  @override
  String get commonRefresh => 'Actualiser';

  @override
  String get commonRetry => 'Réessayer';

  @override
  String get commonSeeVip => 'Voir l\'accès VIP';

  @override
  String get commonToday => 'Aujourd\'hui';

  @override
  String get commonYesterday => 'Hier';

  @override
  String countdownDays(int days, String time) {
    return '$days j $time';
  }

  @override
  String detailChecked(String date) {
    return 'Vérifié : $date';
  }

  @override
  String get detailFormationPending => 'Formation en attente';

  @override
  String get detailH2hTitle => 'Historique des confrontations (H2H)';

  @override
  String get detailInjuries => 'Absences signalées';

  @override
  String get detailLineups => 'Compositions';

  @override
  String get detailLineupsPending => 'Compositions pas encore confirmées.';

  @override
  String get detailNoH2h => 'Aucune confrontation enregistrée pour ce match.';

  @override
  String get detailNoInjuries => 'Aucune absence dans le rapport disponible.';

  @override
  String get detailNoInjuriesCheck =>
      'Aucune vérification des absences disponible.';

  @override
  String get detailNoPicks => 'Aucun pronostic publié pour ce match.';

  @override
  String get detailNoStarters => 'Aucun titulaire confirmé.';

  @override
  String get detailReferee => 'Arbitre';

  @override
  String get detailRefereePending => 'Arbitre à confirmer.';

  @override
  String get detailTabAlerts => 'Alertes';

  @override
  String get detailTabH2h => 'H2H';

  @override
  String get detailTabPredictions => 'Pronostics';

  @override
  String get detailTabStats => 'Analyse';

  @override
  String get detailVipPickNotice => 'Ce match a un pronostic VIP';

  @override
  String get dictAwayDefault => 'l\'équipe à l\'extérieur';

  @override
  String get dictHomeDefault => 'l\'équipe à domicile';

  @override
  String dictOddsAbove(String fair) {
    return 'La cote publiée dépasse la cote juste ($fair).';
  }

  @override
  String dictOddsBelow(String fair) {
    return 'La cote publiée est inférieure à la cote juste ($fair) ; l\'intérêt réside dans la probabilité, pas dans le prix.';
  }

  @override
  String dictPick(String pick, String percent) {
    return '$pick avec une probabilité calculée de $percent.';
  }

  @override
  String get dictPickDefault => 'Le pronostic';

  @override
  String dictXg(
    String total,
    String home,
    String homeXg,
    String away,
    String awayXg,
  ) {
    return 'Les cotes du marché sans marge impliquent $total buts attendus ($home $homeXg · $away $awayXg).';
  }

  @override
  String get disclaimerProbability =>
      'Une probabilité n\'est pas une certitude. Décidez en connaissance de cause et jouez de manière responsable.';

  @override
  String get factsAbsences => 'Absences';

  @override
  String get factsDrew => 'Nul';

  @override
  String get factsHideLineup => 'Masquer les onze';

  @override
  String factsInCompetition(String competition) {
    return 'En $competition';
  }

  @override
  String get factsLastLineup => 'Dernière composition connue';

  @override
  String get factsLastMatch => 'Dernier match';

  @override
  String factsLineupMeta(String rival, String date) {
    return 'contre $rival · $date';
  }

  @override
  String get factsLineupNote =>
      'C\'est la composition de ce match, pas une prévision pour celui d\'aujourd\'hui.';

  @override
  String get factsLost => 'Perdu';

  @override
  String get factsNoLineup => 'Aucune composition enregistrée pour l\'instant.';

  @override
  String get factsNoResult => 'Aucun match précédent enregistré.';

  @override
  String get factsSeeAlerts => 'Voir les alertes';

  @override
  String get factsShowLineup => 'Voir les onze';

  @override
  String get factsTitle => 'Données du match';

  @override
  String factsVs(String score, String rival) {
    return '$score contre $rival';
  }

  @override
  String get factsWon => 'Gagné';

  @override
  String get famCardsSubtitle =>
      'Lignes de moins de cartons avec appui historique';

  @override
  String get famCardsTitle => 'Cartons';

  @override
  String get famCornersSubtitle =>
      'Plus et moins de corners sur le match complet';

  @override
  String get famCornersTeamSubtitle =>
      'Domicile et extérieur, chacun avec sa propre ligne';

  @override
  String get famCornersTeamTitle => 'Corners par équipe';

  @override
  String get famCornersTitle => 'Total de corners';

  @override
  String get famDoubleChanceSubtitle =>
      'Deux résultats possibles en une sélection';

  @override
  String get famDoubleChanceTitle => 'Double chance';

  @override
  String get famGoalsSubtitle =>
      'Totaux avec des lignes évaluées historiquement';

  @override
  String get famGoalsTitle => 'Buts du match';

  @override
  String get famHandicapSubtitle => 'Lignes de protection et nul remboursé';

  @override
  String get famHandicapTitle => 'Handicap asiatique';

  @override
  String get famNbaSubtitle =>
      'Évaluation exploratoire · en attente de confirmation';

  @override
  String get famNbaTeamTitle => 'NBA · Points par équipe';

  @override
  String get famNbaTotalTitle => 'NBA · Total du match';

  @override
  String get famNbaWinnerTitle => 'NBA · Vainqueur';

  @override
  String get famTeamGoalsSubtitle =>
      'Au moins un but de l\'équipe à domicile ou à l\'extérieur';

  @override
  String get famTeamGoalsTitle => 'Une équipe marque';

  @override
  String get famWinnerSubtitle => 'Résultat 1X2 à haute probabilité';

  @override
  String get famWinnerTitle => 'Vainqueur du match';

  @override
  String get featAgenda => 'Calendrier temporairement indisponible';

  @override
  String get featBalance => 'Suivi en préparation';

  @override
  String get featCommunity => 'Communauté en préparation';

  @override
  String get featLanguages => 'Traductions en préparation';

  @override
  String get featMatchData => 'Données du match temporairement indisponibles';

  @override
  String get featMeasurement => 'Mesure en préparation';

  @override
  String get featNba => 'Modèle NBA en entraînement';

  @override
  String get featNotifications => 'Notifications en préparation';

  @override
  String get featPurchases => 'Achats en préparation';

  @override
  String get featStats => 'Statistiques temporairement indisponibles';

  @override
  String get featVip => 'Accès VIP temporairement indisponible';

  @override
  String get featureTraining => 'Modèle en entraînement';

  @override
  String get fixtureFinished => 'TERMINÉ';

  @override
  String get fixtureLive => 'EN DIRECT';

  @override
  String get fixtureLocalTime => 'HEURE LOCALE';

  @override
  String get fixtureStartsIn => 'DÉBUT DANS';

  @override
  String get fixtureTbd => 'À CONFIRMER';

  @override
  String get forecastCanFail =>
      'Un pronostic peut échouer ; la probabilité ne garantit pas le résultat.';

  @override
  String get forecastFeatured => 'EN VEDETTE';

  @override
  String get forecastFree => 'GRATUIT';

  @override
  String get forecastHalfTime => 'MI-TEMPS';

  @override
  String get forecastInPlay => 'EN COURS';

  @override
  String get forecastLiveScore => 'Score en direct';

  @override
  String forecastLiveScoreAgo(int minutes) {
    return 'Score en direct · mis à jour il y a $minutes min';
  }

  @override
  String get forecastMarketNote =>
      'Probabilités calculées à partir des cotes du marché sans marge : cette ligue n\'a pas de modèle propre.';

  @override
  String get forecastOddsAtPublish => 'Cote à la publication';

  @override
  String forecastProbCalc(String percent) {
    return '$percent prob. calculée';
  }

  @override
  String get forecastSeeStats => 'Voir les statistiques du match';

  @override
  String get forecastSourceMarket => 'COTES DU MARCHÉ';

  @override
  String get forecastSourceModel => 'MODÈLE PROPRE';

  @override
  String get forecastTitle => 'ANALYSE STATISTIQUE';

  @override
  String get forecastUnlocked => 'DÉBLOQUÉ';

  @override
  String get forecastVerdictTitle => '💡  VERDICT DU MODÈLE';

  @override
  String get formatScheduleUnavailable => 'Horaire non disponible';

  @override
  String get groupBtts => 'LES DEUX ÉQUIPES MARQUENT';

  @override
  String get groupCards => 'CARTONS';

  @override
  String get groupCorners => 'CORNERS';

  @override
  String get groupDoubleChance => 'DOUBLE CHANCE';

  @override
  String get groupDrawNoBet => 'REMBOURSÉ SI NUL';

  @override
  String get groupFirstHalf => '1RE MI-TEMPS';

  @override
  String get groupGoals => 'BUTS';

  @override
  String get groupHandicap => 'HANDICAP';

  @override
  String get groupResult => 'RÉSULTAT';

  @override
  String get groupSpecials => 'SPÉCIAUX';

  @override
  String get groupTeamGoals => 'BUTS PAR ÉQUIPE';

  @override
  String get guideBody1 =>
      'Si un pronostic a 75 % de probabilité, le modèle s\'attend à ce qu\'il se réalise environ 3 fois sur 4 lorsqu\'une situation similaire se répète. Cela signifie que 1 fois sur 4, il ne se réalisera pas. Aucune donnée ne garantit un résultat précis.';

  @override
  String get guideBody2 =>
      'La cote est fixée par un bookmaker et inclut sa marge. Comparer la probabilité du modèle à celle qu\'implique la cote aide à juger si le prix est raisonnable ; cela n\'assure pas le résultat.';

  @override
  String get guideBody3 =>
      'Ils sont publiés avec leur probabilité et leur cote de référence avant le coup d\'envoi et ne peuvent pas être modifiés. Vous pouvez donc comparer le taux de réussite historique réel à celui qui était annoncé.';

  @override
  String get guideBody4 =>
      'Dans un combiné, la probabilité conjointe est le produit de celle de chaque sélection ; elle baisse donc vite quand on ajoute des matchs. Une cote élevée reflète généralement exactement cela.';

  @override
  String get guideBody5 =>
      'Chaque défi avance par étapes et la suivante ne compte que si la précédente est réussie. Consultez l\'avancement et l\'historique, défis ratés compris, avant d\'en suivre un.';

  @override
  String get guideBody6 =>
      'QuantFut n\'est pas un bookmaker et ne garantit aucun gain. Si vous décidez de parier, ne misez que de l\'argent que vous pouvez perdre et seulement si vous êtes majeur. Si le jeu cesse d\'être un loisir, demandez de l\'aide.';

  @override
  String get guideHead1 => 'Une probabilité n\'est pas une certitude';

  @override
  String get guideHead2 => 'La cote est un prix, pas l\'avis du modèle';

  @override
  String get guideHead3 => 'Chaque pronostic est scellé avant le match';

  @override
  String get guideHead4 => 'Plus de sélections, moins de probabilité';

  @override
  String get guideHead5 => 'On monte un palier à la fois';

  @override
  String get guideHead6 => 'C\'est de l\'information et du divertissement';

  @override
  String get guideSubtitle => 'Apprenez à lire les données avant de décider.';

  @override
  String get guideTitle => 'Guide des pronostics';

  @override
  String get guideTopic1 => 'PROBABILITÉ';

  @override
  String get guideTopic2 => 'COTE';

  @override
  String get guideTopic3 => 'HAUTE PROBABILITÉ';

  @override
  String get guideTopic4 => 'COMBINÉ';

  @override
  String get guideTopic5 => 'DÉFI ESCALIER';

  @override
  String get guideTopic6 => 'RESPONSABILITÉ';

  @override
  String get homeBannerClose => 'Fermer l\'avis';

  @override
  String get homeByDate => 'Matchs par date et heure';

  @override
  String homeForecastAt(String when, String mexico) {
    return 'Pronostic le $when ($mexico heure du Mexique)';
  }

  @override
  String get homeForecastPending => 'Pronostic en attente';

  @override
  String get homeMenuTooltip => 'Menu';

  @override
  String get homeNoMatchesDay => 'Aucun match ce jour-là.';

  @override
  String get homeSeeAll => 'Tout voir';

  @override
  String homeTicketJoint(String percent) {
    return 'Prob. conjointe $percent';
  }

  @override
  String homeTicketLegs(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count sélections',
      one: '$count sélection',
    );
    return '$_temp0';
  }

  @override
  String homeTicketOdds(String value) {
    return 'Cote $value';
  }

  @override
  String get homeTicketsEmpty => 'Pas encore de tickets aujourd\'hui';

  @override
  String get homeTicketsTitle => 'Tickets du jour';

  @override
  String get homeToday => 'Aujourd\'hui';

  @override
  String get homeTomorrow => 'Demain';

  @override
  String get inboxEmpty => 'Vous n\'avez pas encore d\'alertes.';

  @override
  String get inboxMatch => 'Match';

  @override
  String get inboxTitle => 'Alertes';

  @override
  String ladderActiveCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count défis en cours',
      one: '1 défi en cours',
    );
    return '$_temp0';
  }

  @override
  String get ladderBalance => 'solde actuel';

  @override
  String get ladderChance => 'de le terminer';

  @override
  String get ladderEmpty => 'Aucun défi actif publié.';

  @override
  String ladderEstimateNote(String avg) {
    return 'Estimation : probabilité du palier en cours et moyenne des autres ($avg). Ce n\'est pas une garantie.';
  }

  @override
  String get ladderFreeHint =>
      'Un palier gratuit : celui de plus forte probabilité.';

  @override
  String get ladderHideSteps => 'Masquer les paliers';

  @override
  String get ladderHistoryDone => 'Réussi';

  @override
  String get ladderHistoryEmpty =>
      'Aucun défi n\'est encore clos. Quand l\'un se termine, il apparaît ici avec son résultat.';

  @override
  String ladderHistoryFailedAt(int step) {
    return 'Échec au palier $step';
  }

  @override
  String ladderHistoryRate(String rate) {
    return 'Taux de réussite : $rate';
  }

  @override
  String ladderHistoryResult(String roi) {
    return 'Résultat cumulé : $roi';
  }

  @override
  String get ladderHistoryShown =>
      'Affichage des derniers défis réussis et du dernier échoué.';

  @override
  String ladderHistorySummary(int done, int closed) {
    return '$done réussis sur $closed clos';
  }

  @override
  String get ladderHistoryTitle => 'Historique des défis';

  @override
  String get ladderNoteInPlay =>
      'Un palier attend son résultat. Le défi est toujours en cours.';

  @override
  String get ladderNoteToPick =>
      'Le prochain palier reste à choisir ; cela peut prendre des jours. Le défi est toujours en cours.';

  @override
  String ladderRemaining(int remaining) {
    String _temp0 = intl.Intl.pluralLogic(
      remaining,
      locale: localeName,
      other: 'il en reste $remaining',
      one: 'il en reste 1',
    );
    return '$_temp0';
  }

  @override
  String get ladderShowSteps => 'Voir les paliers';

  @override
  String get ladderStatusInPlay => 'En jeu';

  @override
  String get ladderStatusToPick => 'À choisir';

  @override
  String ladderTitle(Object id, int steps) {
    String _temp0 = intl.Intl.pluralLogic(
      steps,
      locale: localeName,
      other: '$steps paliers',
      one: '$steps palier',
    );
    return 'Défi n° $id · $_temp0';
  }

  @override
  String ladderWonOf(int won, int goal) {
    return '$won sur $goal gagnés';
  }

  @override
  String get languageFirstBadge => 'Configuration de la langue';

  @override
  String get languageFirstHint =>
      'Choisissez la langue de l\'analyse pour une meilleure expérience';

  @override
  String get languageFirstTitle => 'Choisissez votre langue';

  @override
  String get languageHint =>
      'Choisissez la langue. Elle est enregistrée sur cet appareil et dans votre compte.';

  @override
  String get languageTitle => 'Langue de l\'application';

  @override
  String get ledgerAd => 'Vidéo avec récompense';

  @override
  String get ledgerAttendance => 'Présence';

  @override
  String get ledgerInvitee => 'Récompense de bienvenue';

  @override
  String get ledgerOffer => 'Offre terminée';

  @override
  String get ledgerReferralReversal => 'Récompense de parrainage annulée';

  @override
  String get ledgerReferrer => 'Récompense de parrainage';

  @override
  String get ledgerReversal => 'Offre annulée';

  @override
  String get ledgerUnlock => 'Pronostic débloqué';

  @override
  String get levelHigh => 'HAUTE PROB.';

  @override
  String get levelModerate => 'MODÉRÉE';

  @override
  String get levelSolid => 'SOLIDE';

  @override
  String get lineAwayScores =>
      'L\'équipe à l\'extérieur marque · plus de 0,5 but';

  @override
  String get lineDoubleChance => 'Double chance · 1X / X2 / 12';

  @override
  String lineHandicap(String line) {
    return 'Handicap $line';
  }

  @override
  String get lineHomeScores => 'L\'équipe à domicile marque · plus de 0,5 but';

  @override
  String lineTeamCorners(String team, String side, String line) {
    String _temp0 = intl.Intl.selectLogic(side, {
      'over': 'plus de $line corners',
      'other': 'moins de $line corners',
    });
    return '$team : $_temp0';
  }

  @override
  String get lineWinner => 'Vainqueur · sélection à haute probabilité';

  @override
  String get maintenanceNotice =>
      'Nous effectuons une maintenance. Certaines fonctions peuvent être plus lentes.';

  @override
  String get marketAwayScores => 'L\'équipe à l\'extérieur marque';

  @override
  String get marketBtts => 'Les deux équipes marquent';

  @override
  String get marketCards => 'Cartons';

  @override
  String get marketCorners => 'Corners';

  @override
  String get marketCornersAway => 'Corners de l\'équipe à l\'extérieur';

  @override
  String get marketCornersHome => 'Corners de l\'équipe à domicile';

  @override
  String get marketDoubleChance => 'Double chance';

  @override
  String get marketGoals => 'Buts';

  @override
  String get marketGoalsAway => 'Buts de l\'équipe à l\'extérieur';

  @override
  String get marketGoalsHome => 'Buts de l\'équipe à domicile';

  @override
  String get marketHandicap => 'Handicap';

  @override
  String get marketHomeScores => 'L\'équipe à domicile marque';

  @override
  String get marketHtBtts => 'Les deux équipes marquent en 1re mi-temps';

  @override
  String get marketHtGoal => 'But en 1re mi-temps';

  @override
  String get marketResult1x2 => 'Résultat 1X2';

  @override
  String get marketUnknown => 'Marché';

  @override
  String get marketWinToNil => 'Gagne sans encaisser';

  @override
  String get marketsAndResults => 'Marchés et résultats';

  @override
  String marketsEvidenceAt(String date) {
    return 'Données au $date';
  }

  @override
  String get marketsFamiliesRadar => 'familles de marchés sur le radar';

  @override
  String marketsHistoricHit(String percent) {
    return 'réussite historique $percent';
  }

  @override
  String get marketsInReview => 'En cours de révision : aucune ligne confirmée';

  @override
  String get marketsModelActive => 'MODÈLE ACTIF';

  @override
  String get marketsNoLineLabel => 'aucune ligne confirmée';

  @override
  String get marketsNoPublications => 'Aucune publication pour le moment';

  @override
  String get marketsNoResolved => 'Aucun pronostic résolu';

  @override
  String marketsPublished(int won, int cases) {
    return 'Publié $won/$cases';
  }

  @override
  String marketsPublishedWon(int won, int cases, String percent) {
    return '$won/$cases publiés gagnés · $percent';
  }

  @override
  String get marketsRadarNote =>
      'L\'anneau est le taux de réussite historique de la meilleure ligne validée de chaque marché ; « Publié » désigne les pronostics déjà résolus. Ce sont des pronostics d\'avant-match, pas des alertes en direct, et aucune probabilité ne garantit un résultat.';

  @override
  String mdCornersTotal(Object total) {
    return 'corners · total $total';
  }

  @override
  String get mdEmptyHistory =>
      'Aucun pronostic résolu sur ce marché pour le moment.';

  @override
  String get mdEmptyToday =>
      'Aucun pronostic disponible pour le moment sur ce marché. Ils apparaissent lorsque le modèle les publie, avant le match.';

  @override
  String get mdHitRate => 'Taux de réussite';

  @override
  String get mdLineConfirmed => 'Confirmée';

  @override
  String get mdLineNotDeployed => 'Non déployée';

  @override
  String get mdLineReview => 'En cours de révision';

  @override
  String get mdLineShort => 'Échantillon court';

  @override
  String get mdLoadError => 'Impossible de charger l\'historique.';

  @override
  String get mdModel => 'MODÈLE';

  @override
  String get mdNoDate => 'Sans date';

  @override
  String get mdOverall => 'Général';

  @override
  String get mdTabPrevious => 'Précédents';

  @override
  String mdTabToday(int count) {
    return 'Aujourd\'hui ($count)';
  }

  @override
  String get mdValidatedLines => 'Lignes validées';

  @override
  String get mmChance => 'OPPORTUNITÉ';

  @override
  String get mmDisclaimer =>
      'Il s\'agit d\'une analyse du modèle, pas d\'un conseil de pari. La « cote juste » est 1/probabilité : ce n\'est pas une cote de bookmaker. Un pronostic peut échouer.';

  @override
  String get mmFairOdds => 'cote juste';

  @override
  String mmGroupCount(String group, int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count marchés',
      one: '$count marché',
    );
    return '$group · $_temp0';
  }

  @override
  String mmLocked(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count verrouillés',
      one: '$count verrouillé',
    );
    return '$_temp0';
  }

  @override
  String mmOpen(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count ouverts',
      one: '$count ouvert',
    );
    return '$_temp0';
  }

  @override
  String mmProb(int value) {
    return '$value % prob.';
  }

  @override
  String get mmPublishedOdds => 'cote publiée';

  @override
  String get mmScoresTitle => 'Scores les plus probables';

  @override
  String get mmScoresVip =>
      'Les scores les plus probables sont réservés aux VIP.';

  @override
  String get mmTitle => 'Marchés du match';

  @override
  String get moreApp => 'App';

  @override
  String get moreGuide => 'Guide des pronostics';

  @override
  String get moreGuideSub => 'Comment lire probabilités, cotes et défis';

  @override
  String get moreLearn => 'Apprendre';

  @override
  String get moreLegal => 'Mentions légales';

  @override
  String get moreRate => 'Noter l\'app';

  @override
  String get moreRateSub => 'Partagez votre avis';

  @override
  String get moreShare => 'Partager l\'app';

  @override
  String get moreShareMessage =>
      'Découvrez QuantFut : des probabilités de football basées sur les données, sans promesses. https://pronosticosdeportivos.pro';

  @override
  String get moreShareSub => 'Invitez vos amis';

  @override
  String get moreStoreError =>
      'Impossible d\'ouvrir la boutique d\'applications.';

  @override
  String get navCoins => 'Coins';

  @override
  String get navHome => 'Accueil';

  @override
  String get navMarkets => 'Marchés';

  @override
  String get navPredictions => 'Pronostics';

  @override
  String get navProfile => 'Profil';

  @override
  String noteExpectedAverage(String value) {
    return 'Moyenne attendue : $value';
  }

  @override
  String noteExpectedGoals(String value) {
    return 'Buts attendus : $value';
  }

  @override
  String noteXg(String home, String homeValue, String away, String awayValue) {
    return 'xG : $home $homeValue · $away $awayValue';
  }

  @override
  String get notificationIosPending =>
      'Les notifications iOS attendent la configuration d\'Apple.';

  @override
  String get notificationPermissionDenied =>
      'Activez l\'autorisation dans les réglages de l\'appareil.';

  @override
  String get outcomeLoss => 'Perdu';

  @override
  String get outcomePush => 'Remboursé';

  @override
  String get outcomeWin => 'Gagné';

  @override
  String parleyChipLine(int count, String min, String max) {
    return 'Jusqu\'à $count combinés · cote $min–$max';
  }

  @override
  String parleyDayCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count combinés',
      one: '$count combiné',
    );
    return '$_temp0';
  }

  @override
  String parleyDaySettled(int won, int settled) {
    return '$won/$settled gagnés';
  }

  @override
  String get parleyDisclaimer =>
      'Il est choisi selon la probabilité, pas selon la valeur, et chaque sélection réduit la marge. Un combiné peut échouer : multiplier les cotes multiplie aussi le risque.';

  @override
  String get parleyFewNote =>
      'Avec peu de combinés, le taux réel ne prouve encore rien.';

  @override
  String get parleyFreeChip => '1 gratuit par jour';

  @override
  String get parleyFreeNote =>
      'Un gratuit par jour (celui de plus faible cote) ; les autres, VIP.';

  @override
  String get parleyHistoryTitle => 'Historique du Combiné';

  @override
  String get parleyInactiveBody =>
      'Une fois activé, vous verrez ici les combinés du jour, scellés avant le début des matchs.';

  @override
  String get parleyInactiveTitle => 'Le Combiné n\'est pas encore actif';

  @override
  String get parleyInfoTitle => 'Comment un combiné est choisi';

  @override
  String parleyJointProb(String percent, int legs) {
    String _temp0 = intl.Intl.pluralLogic(
      legs,
      locale: localeName,
      other: '$legs sélections',
      one: '$legs sélection',
    );
    return '$percent de probabilité conjointe · $_temp0';
  }

  @override
  String get parleyLoadError => 'Impossible de charger le Combiné.';

  @override
  String get parleyNoHistory =>
      'Il n\'y a pas encore d\'historique de combinés. Il apparaîtra ici dès que le premier sera réglé.';

  @override
  String get parleyNoneBody =>
      'Le modèle ne publie pas de combiné s\'il n\'en trouve pas dans le respect des règles.';

  @override
  String get parleyNoneTitle => 'Pas de combinés aujourd\'hui';

  @override
  String parleyOddsBetween(String min, String max) {
    return 'Cote entre $min et $max';
  }

  @override
  String get parleyOutcomeLoss => 'Perdu';

  @override
  String get parleyOutcomePending => 'En attente';

  @override
  String get parleyOutcomeVoid => 'Annulé';

  @override
  String get parleyOutcomeWin => 'Gagné';

  @override
  String get parleyPastDays => 'Jours précédents';

  @override
  String parleyRange(int count, String min, String max) {
    return 'De 1 à $count combinés · cote entre $min et $max · le plus probable de chaque palier';
  }

  @override
  String parleyResultScore(Object score) {
    return 'Résultat $score';
  }

  @override
  String get parleySealed => 'Combinés scellés avant les matchs';

  @override
  String parleyStep(Object step) {
    return 'PALIER $step';
  }

  @override
  String parleySummary(Object hits, Object total) {
    return '$hits/$total combinés gagnés';
  }

  @override
  String parleySummaryPromised(String value) {
    return ' contre $value % promis';
  }

  @override
  String parleySummaryReal(String value) {
    return ' · $value % réel';
  }

  @override
  String pickOddsAtPublish(Object book) {
    return 'Cote à la publication · $book';
  }

  @override
  String pickProbability(String percent) {
    return 'Probabilité $percent';
  }

  @override
  String get pickSeeAnalysis => 'Voir l\'analyse du match';

  @override
  String get pickSourceNA => 'Source non disponible';

  @override
  String pickUnlockCoins(Object cost) {
    return 'Débloquer pour $cost pièces';
  }

  @override
  String get pickUnlockPrompt => 'Débloquez le pronostic et sa cote.';

  @override
  String get pickUnlockVip => 'Débloquer le pronostic VIP';

  @override
  String picksAllHeading(int count) {
    return 'Pronostics · $count';
  }

  @override
  String get picksBestProb => 'Probabilité la plus forte';

  @override
  String picksCoinsShort(Object cost) {
    return '$cost pièces';
  }

  @override
  String get picksEmpty =>
      'Aucun pronostic publié en attente dans cette plage.';

  @override
  String picksFreeHeading(int count) {
    return 'Gratuits · $count';
  }

  @override
  String get picksLockedHide => 'Masquer la liste';

  @override
  String get picksLockedHint =>
      'Avec VIP, vous voyez le pronostic, la probabilité et l\'analyse';

  @override
  String get picksLockedShow => 'Voir la liste';

  @override
  String picksLockedTitle(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count pronostics de plus avec VIP',
      one: '1 pronostic de plus avec VIP',
    );
    return '$_temp0';
  }

  @override
  String picksRangeHint(int min, int max, int free) {
    return '$min–$max % de probabilité · jusqu\'à $free gratuits';
  }

  @override
  String get picksSeeAnalysis => 'Voir l\'analyse';

  @override
  String get picksTomorrow => 'Demain';

  @override
  String picksTrainingReasons(String reasons) {
    return 'Modèle en entraînement · $reasons';
  }

  @override
  String picksTrustDetail(int hits, int total) {
    return '$hits sur $total pronostics';
  }

  @override
  String picksTrustPromised(String percent) {
    return 'Promis : $percent';
  }

  @override
  String get picksTrustTitle => 'Taux de réussite historique';

  @override
  String get prefsAdsBody =>
      'Partage avec Meta des données chiffrées de votre compte, de l\'appareil et de vos achats pour mesurer quelles publicités fonctionnent. En Californie, le désactiver équivaut à « Ne pas partager mes données ».';

  @override
  String get prefsAdsTitle => 'Mesure des publicités (Meta)';

  @override
  String get prefsAnalyticsBody =>
      'Aide à améliorer l\'application grâce à des données sur les écrans utilisés. Facultatif.';

  @override
  String get prefsAnalyticsTitle => 'Mesure d\'utilisation';

  @override
  String get prefsDeleteAccount => 'Demander la suppression de mon compte';

  @override
  String get prefsDeleteAccountHint =>
      'Consultez les étapes et le contact de Saptain LTD.';

  @override
  String get prefsDiagnosticsBody =>
      'Envoie des informations techniques à Firebase et à Sentry pour diagnostiquer les pannes. Facultatif.';

  @override
  String get prefsDiagnosticsTitle => 'Rapports d\'erreurs et de performance';

  @override
  String get prefsInbox => 'Boîte des alertes';

  @override
  String get prefsLanguageNote =>
      'La langue s\'applique à toute l\'application et est enregistrée comme préférence.';

  @override
  String get prefsNote =>
      'Vous pouvez utiliser les fonctions de base sans activer la mesure ni le diagnostic. Modifier ces options ne supprime pas automatiquement les données déjà envoyées.';

  @override
  String get prefsNotificationsOff =>
      'Disponible une fois la connexion avec Google terminée.';

  @override
  String get prefsNotificationsOn =>
      'Vous pouvez les désactiver à tout moment. Les alertes peuvent s\'afficher sur l\'écran verrouillé.';

  @override
  String get prefsNotificationsTitle => 'Notifications QuantFut';

  @override
  String get prefsPrivacyRights => 'Confidentialité et vos droits';

  @override
  String get prefsTitle => 'Confidentialité et préférences';

  @override
  String get privacyUpdateBody =>
      'Vous pouvez désormais vous abonner via Google Play ou l\'App Store, et la mesure d\'utilisation, le diagnostic et la mesure publicitaire Meta sont activés. Vous pouvez les désactiver dans Préférences.';

  @override
  String get privacyUpdateOk => 'Compris';

  @override
  String get privacyUpdateRead => 'Lire la politique';

  @override
  String get privacyUpdateTitle => 'Nous avons mis à jour la confidentialité';

  @override
  String get probBarAway => 'Ext.';

  @override
  String get probBarDraw => 'Nul';

  @override
  String get probBarHome => 'Dom.';

  @override
  String get profileAppVersion => 'Version de l\'application';

  @override
  String get profileBalance => 'Solde et suivi';

  @override
  String get profileConnected => 'QuantFut · Connecté au serveur';

  @override
  String get profileCreateAccount => 'Créer un compte';

  @override
  String get profileCreateOne => 'Créer un compte';

  @override
  String get profileEmail => 'E-mail';

  @override
  String get profileEmailPending => 'E-mail en attente de vérification';

  @override
  String get profileEmailVerified => 'E-mail vérifié';

  @override
  String get profileForgot => 'J\'ai oublié mon mot de passe';

  @override
  String get profileForgotSent =>
      'Si le compte existe, vous recevrez les instructions par e-mail.';

  @override
  String get profileFreePlan => 'Forfait gratuit';

  @override
  String get profileGeneral => 'Général';

  @override
  String get profileHaveAccount => 'J\'ai déjà un compte';

  @override
  String get profileLanguage => 'Langue';

  @override
  String get profileMeasurement => 'Mesure et erreurs';

  @override
  String get profileNotifications => 'Notifications';

  @override
  String get profileOddsFormat => 'Format des cotes';

  @override
  String get profileOddsFormatValue =>
      'Décimal · Cotes enregistrées à la publication';

  @override
  String get profilePassword => 'Mot de passe';

  @override
  String get profilePreferences => 'Préférences';

  @override
  String get profileRefreshAccess => 'Actualiser mon accès';

  @override
  String get profileSeePlans => 'Voir les offres VIP';

  @override
  String get profileSendVerification => 'Envoyer l\'e-mail de vérification';

  @override
  String get profileSignIn => 'Se connecter';

  @override
  String get profileSignOut => 'Se déconnecter';

  @override
  String get profileTitle => 'Profil et paramètres';

  @override
  String profileValidUntil(String date) {
    return 'Validité : $date';
  }

  @override
  String get profileVerificationSent => 'E-mail de vérification envoyé.';

  @override
  String get profileVipActive => 'Accès VIP actif';

  @override
  String get profileYourAccount => 'Votre compte QuantFut';

  @override
  String resultLabel(String score) {
    return 'Résultat : $score';
  }

  @override
  String get rewardsAttendanceSub =>
      'Une fois par jour · réinitialisé à 00:00 UTC';

  @override
  String get rewardsAttendanceTitle => 'Présence quotidienne';

  @override
  String get rewardsAvailable => 'Disponible';

  @override
  String get rewardsCheckIn => 'Pointer ma présence';

  @override
  String get rewardsCheckInNote =>
      'Une fois par jour UTC. Si vous manquez un jour, la série repart de zéro.';

  @override
  String rewardsChipRate(Object cost) {
    return '$cost pièces = 1 pronostic';
  }

  @override
  String rewardsChipStreak(int days) {
    String _temp0 = intl.Intl.pluralLogic(
      days,
      locale: localeName,
      other: 'Série de $days jours',
      one: 'Série de 1 jour',
    );
    return '$_temp0';
  }

  @override
  String rewardsClaimCta(Object coins) {
    return 'Pointer ma présence · +$coins';
  }

  @override
  String rewardsClaimed(Object coins) {
    return '+$coins pièces';
  }

  @override
  String get rewardsClaimedToday => 'Réclamée aujourd\'hui';

  @override
  String get rewardsCodeCopied => 'Code copié.';

  @override
  String get rewardsCodeRegistered => 'Code d\'invitation enregistré.';

  @override
  String rewardsComingSoon(String names) {
    return 'Bientôt : $names';
  }

  @override
  String get rewardsCopy => 'Copier';

  @override
  String rewardsCopyCode(Object code) {
    return 'Copier mon code · $code';
  }

  @override
  String rewardsDay(int number) {
    return 'Jour $number';
  }

  @override
  String get rewardsDebt => 'Solde en attente à cause de récompenses annulées.';

  @override
  String get rewardsEarnTitle => 'Gagnez des pièces aujourd\'hui';

  @override
  String get rewardsEnough => 'Vous avez assez de pièces pour un déblocage.';

  @override
  String get rewardsGo => 'Aller';

  @override
  String rewardsInviteChip(Object coins) {
    return '+$coins pour vous';
  }

  @override
  String rewardsInviteCondition(Object min) {
    return 'Après vérification de l\'e-mail et $min pièces gagnées en offres confirmées.';
  }

  @override
  String rewardsInviteFriend(Object coins) {
    return 'Votre ami reçoit +$coins en saisissant votre code';
  }

  @override
  String rewardsInviteReward(Object referrer, Object invitee) {
    return 'Vous +$referrer · Votre ami +$invitee pièces';
  }

  @override
  String get rewardsInviteTitle => 'Invitez vos amis';

  @override
  String get rewardsInviterCode => 'Code de la personne qui vous a invité';

  @override
  String get rewardsLedgerEmpty => 'Aucun mouvement pour le moment.';

  @override
  String get rewardsLedgerLess => 'Voir moins';

  @override
  String get rewardsLedgerMore => 'Voir plus';

  @override
  String get rewardsLedgerTitle => 'Mes mouvements';

  @override
  String rewardsMissing(int missing) {
    String _temp0 = intl.Intl.pluralLogic(
      missing,
      locale: localeName,
      other: 'Il manque $missing pièces pour votre prochain déblocage.',
      one: 'Il manque $missing pièce pour votre prochain déblocage.',
    );
    return '$_temp0';
  }

  @override
  String get rewardsMissingUnknown =>
      'Il manque — pièces pour votre prochain déblocage.';

  @override
  String get rewardsMyCoins => 'Mes pièces';

  @override
  String rewardsNextIn(String time) {
    return 'Prochaine présence dans $time';
  }

  @override
  String get rewardsOfferAvailable =>
      'Offres selon votre pays et votre appareil';

  @override
  String get rewardsOfferPending => 'En attente d\'activation';

  @override
  String get rewardsOffersConfig =>
      'Ce fournisseur n’est pas encore prêt. Réessayez plus tard.';

  @override
  String get rewardsOffersCta => 'Voir les offres';

  @override
  String get rewardsOffersLead => 'Terminez des offres et recevez des pièces.';

  @override
  String get rewardsOffersLoadFailed =>
      'Impossible d’ouvrir les offres. Vérifiez votre connexion et réessayez.';

  @override
  String get rewardsOffersTimeout =>
      'Le chargement des offres a pris trop de temps. Réessayez.';

  @override
  String get rewardsOffersTitle => 'Offres pour gagner des pièces';

  @override
  String get rewardsOffersUnavailable =>
      'Aucune offre disponible pour le moment. Réessayez plus tard.';

  @override
  String get rewardsOperationDone => 'Opération confirmée.';

  @override
  String get rewardsPaste => 'Coller le code';

  @override
  String get rewardsPasteEmpty =>
      'Aucun code d\'invitation dans le presse-papiers.';

  @override
  String rewardsReferralStats(Object registered, Object qualified) {
    return '$registered inscrits · $qualified validés';
  }

  @override
  String get rewardsRefreshBalance => 'Actualiser le solde';

  @override
  String get rewardsRegisterCode => 'Enregistrer le code';

  @override
  String get rewardsShare => 'Partager mon code';

  @override
  String rewardsShareMessage(String code, String link) {
    return 'Utilise mon code d\'invitation $code dans QuantFut : dans Coins, saisis-le dans « Code de la personne qui t\'a invité ». Tout est expliqué ici : $link';
  }

  @override
  String get rewardsSignIn => 'Connectez-vous';

  @override
  String get rewardsSignInHint =>
      'Connectez-vous depuis Profil pour enregistrer votre solde, pointer votre présence et utiliser un code de parrainage.';

  @override
  String rewardsStreak(int days) {
    String _temp0 = intl.Intl.pluralLogic(
      days,
      locale: localeName,
      other: '$days jours',
      one: '$days jour',
    );
    return 'Série de présence · $_temp0';
  }

  @override
  String get rewardsTermsTitle => 'Règles et conditions';

  @override
  String rewardsUnlockFor(Object cost) {
    return 'Débloquez un pronostic pour $cost pièces';
  }

  @override
  String get selBttsNo => 'Les deux équipes ne marquent pas';

  @override
  String get selBttsYes => 'Les deux équipes marquent';

  @override
  String selCards(String side, String line) {
    String _temp0 = intl.Intl.selectLogic(side, {
      'over': 'Plus de $line cartons',
      'other': 'Moins de $line cartons',
    });
    return '$_temp0';
  }

  @override
  String selCorners(String side, String line) {
    String _temp0 = intl.Intl.selectLogic(side, {
      'over': 'Plus de $line corners',
      'other': 'Moins de $line corners',
    });
    return '$_temp0';
  }

  @override
  String selCornersTeam(String side, String line, String team) {
    String _temp0 = intl.Intl.selectLogic(side, {
      'over': 'Plus de $line corners de $team',
      'other': 'Moins de $line corners de $team',
    });
    return '$_temp0';
  }

  @override
  String selDrawNoBet(String team) {
    return '$team gagne (le nul est remboursé)';
  }

  @override
  String selEitherNoDraw(String home, String away) {
    return '$home ou $away (sans nul)';
  }

  @override
  String selGoals(String side, String line) {
    String _temp0 = intl.Intl.selectLogic(side, {
      'over': 'Plus de $line buts',
      'other': 'Moins de $line buts',
    });
    return '$_temp0';
  }

  @override
  String selHandicapLong(String team, String line) {
    return '$team $line (handicap asiatique)';
  }

  @override
  String selHandicapShort(String team, String line) {
    return '$team $line';
  }

  @override
  String selHomeWins(String team) {
    return '$team gagne';
  }

  @override
  String get selHtBttsNo => 'Les deux équipes ne marquent pas en 1re mi-temps';

  @override
  String get selHtGoalYes => 'Il y aura un but en 1re mi-temps';

  @override
  String selTeamOrDraw(String team) {
    return '$team ou nul';
  }

  @override
  String selTeamScores(String team) {
    return '$team marque';
  }

  @override
  String selWinToNil(String team) {
    return '$team gagne sans encaisser';
  }

  @override
  String get shellNeedCoinsBody =>
      'Gagnez des pièces avec la présence quotidienne et les offres pour débloquer ce pronostic.';

  @override
  String get shellNeedCoinsCta => 'Gagner des pièces';

  @override
  String get shellNeedCoinsTitle => 'Il vous manque des pièces';

  @override
  String get shellNewAlert => 'Nouvelle alerte QuantFut';

  @override
  String get shellSignInForCoins =>
      'Connectez-vous depuis Profil pour utiliser vos pièces.';

  @override
  String shellUnlockBody(Object cost) {
    return '$cost pièces seront déduites de votre solde. L\'accès correspond à ce pronostic.';
  }

  @override
  String get shellUnlockTitle => 'Débloquer le pronostic';

  @override
  String get shellView => 'Voir';

  @override
  String get splashTagline => 'FOOTBALL · NBA · STATISTIQUES';

  @override
  String get startupFailed =>
      'Impossible de démarrer QuantFut. Veuillez réessayer.';

  @override
  String get startupLoading => 'Démarrage de QuantFut';

  @override
  String statAveragesNote(Object homeN, Object awayN) {
    return 'Moyennes de $homeN matchs de l\'équipe à domicile et $awayN de celle à l\'extérieur. La couverture des tirs, corners et xG peut être partielle.';
  }

  @override
  String get statBestAway => 'Meilleure victoire à l\'extérieur';

  @override
  String get statBestHome => 'Meilleure victoire à domicile';

  @override
  String get statCleanSheet => 'Clean sheets';

  @override
  String get statCompareNote =>
      'Les barres comparent les valeurs enregistrées ; elles ne représentent pas des probabilités de victoire. Moins de buts encaissés est préférable.';

  @override
  String get statCompareTitle => 'Comparaison des équipes';

  @override
  String get statDrawStreak => 'Série de nuls';

  @override
  String get statFormLegend =>
      'V : victoire · N : nul · D : défaite. Plus récent à gauche.';

  @override
  String get statFormNA => 'Forme non disponible.';

  @override
  String get statFormTitle => 'Forme des équipes';

  @override
  String get statGoalsAgainst => 'Buts encaissés';

  @override
  String get statGoalsAvgNote =>
      'Buts marqués par match ; ce n\'est pas la projection de buts du modèle.';

  @override
  String get statGoalsAvgTitle => 'MOYENNE HISTORIQUE DE BUTS';

  @override
  String get statGoalsFor => 'Buts marqués';

  @override
  String statH2hSummary(
    Object n,
    Object home,
    Object homeWins,
    Object away,
    Object awayWins,
    Object draws,
  ) {
    return 'Sur $n confrontations enregistrées : $home a gagné $homeWins, $away a gagné $awayWins et il y a eu $draws nuls.';
  }

  @override
  String get statH2hTitle => 'Face à face';

  @override
  String statLastMatches(int count) {
    return '$count derniers matchs enregistrés';
  }

  @override
  String get statMinutesNA =>
      'La répartition par minute n\'est pas disponible pour ce match.';

  @override
  String get statMinutesTitle => 'Buts par minute';

  @override
  String get statNeedsAccess =>
      'Le pronostic de ce match nécessite un accès VIP ou un déblocage avec des pièces.';

  @override
  String get statOnTargetShort => 'Cadrés';

  @override
  String get statOver25 => 'Plus de 2,5 buts';

  @override
  String statPickProbOdds(String percent, String odds) {
    return 'Probabilité $percent · Cote @ $odds';
  }

  @override
  String statPlayed(Object played) {
    return '$played matchs';
  }

  @override
  String statPoints(Object points) {
    return '$points points';
  }

  @override
  String get statPoissonNA =>
      'La distribution de Poisson et les scores probables ne sont pas encore disponibles dans les données de ce match.';

  @override
  String get statPoissonTitle => 'Distribution de buts de Poisson';

  @override
  String statPosition(Object position) {
    return 'Position $position';
  }

  @override
  String get statProbNA => 'Probabilités du modèle pas encore disponibles.';

  @override
  String get statProbTitle => 'PROBABILITÉ DE VICTOIRE · 1X2';

  @override
  String get statPublishedPick => 'PRONOSTIC PUBLIÉ';

  @override
  String get statRadarNeeds =>
      'La comparaison graphique nécessite au moins trois indicateurs disponibles pour les deux équipes.';

  @override
  String get statRadarNote =>
      'Échelle relative par axe. Une surface plus grande n\'implique pas une plus forte probabilité de gagner.';

  @override
  String get statResDraw => 'N';

  @override
  String get statResLoss => 'D';

  @override
  String get statResWin => 'V';

  @override
  String statResultsAvailable(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count résultats disponibles',
      one: '$count résultat disponible',
    );
    return '$_temp0';
  }

  @override
  String get statSeasonTitle => 'Saison et résultats récents';

  @override
  String get statShots => 'Tirs';

  @override
  String get statShotsOnTarget => 'Tirs cadrés';

  @override
  String get statStandingNA => 'Classement non disponible.';

  @override
  String get statSummaryTitle => 'Résumé du pronostic';

  @override
  String get statTeamStatsTitle => 'Statistiques de l\'équipe';

  @override
  String get statWinStreak => 'Série de victoires';

  @override
  String get statXgHistoric => 'xG historique';

  @override
  String get streamHighProb => 'Haute probabilité';

  @override
  String get streamLadder => 'Défi Escalier';

  @override
  String get streamParley => 'Combiné';

  @override
  String tileFairOdds(String value) {
    return 'Cote juste $value';
  }

  @override
  String get tileFavorite => 'Favori 1X2';

  @override
  String tileFavoriteLead(String team, int pts) {
    return '$team · +$pts pts';
  }

  @override
  String get tileFavoriteNA => 'Probabilités non disponibles';

  @override
  String get tileGoalsNA => 'Historique insuffisant';

  @override
  String get tileGoalsTrend => 'Tendance buts';

  @override
  String get tileOver25Model => 'Plus de 2,5 selon le modèle';

  @override
  String get tileOver25Recent => 'Plus de 2,5 sur leurs derniers matchs';

  @override
  String get tileProbability => 'Probabilité';

  @override
  String get tileXg => 'xG projeté';

  @override
  String tileXgCaption(String home, String away) {
    return '$home domicile · $away extérieur';
  }

  @override
  String get tileXgNA => 'Disponible sur les marchés de buts';

  @override
  String get titleAsianHandicap => 'Handicap asiatique';

  @override
  String get titleDrawNoBet => 'Remboursé si match nul';

  @override
  String titleTeamGoals(String team) {
    return 'Buts de $team';
  }

  @override
  String get titleTotalCards => 'Total de cartons';

  @override
  String get titleTotalCorners => 'Total de corners';

  @override
  String get titleTotalGoals => 'Total de buts';

  @override
  String get titleWinner => 'Vainqueur du match';

  @override
  String get tooltipVip => 'VIP';

  @override
  String get vipActivate => 'Activer l\'accès VIP';

  @override
  String get vipActive => 'Votre accès VIP est actif.';

  @override
  String get vipBadge => '✦  ACCÈS VIP';

  @override
  String get vipBenefit1Body => 'Chaque pronostic est scellé avant le match';

  @override
  String get vipBenefit1Title => 'Historique vérifiable';

  @override
  String vipBenefit2Body(int min, int max) {
    return 'Tous les pronostics de $min à $max %, sans quota gratuit';
  }

  @override
  String get vipBenefit2Title => 'Haute probabilité complète';

  @override
  String get vipBenefit3Body => 'Tous les paliers en attente, pas seulement un';

  @override
  String get vipBenefit3Title => 'Défi Escalier complet';

  @override
  String get vipBenefit4Body =>
      'Cote publiée, probabilité et xG de chaque pronostic';

  @override
  String get vipBenefit4Title => 'Cotes et analyse du match';

  @override
  String get vipBestPrice => '★ MEILLEUR PRIX';

  @override
  String get vipCheckAccess => 'Vérifier mon accès';

  @override
  String get vipCheckSignIn =>
      'Connectez-vous depuis Profil pour vérifier votre accès.';

  @override
  String vipDays(int days) {
    String _temp0 = intl.Intl.pluralLogic(
      days,
      locale: localeName,
      other: '$days jours',
      one: '$days jour',
    );
    return '$_temp0';
  }

  @override
  String get vipFreeAccess => 'Votre compte a un accès gratuit.';

  @override
  String get vipGranted => 'C\'est fait ! Votre accès VIP est actif.';

  @override
  String get vipHistoryNote =>
      'Historique public et scellé ; les échantillons par marché sont petits et un pronostic peut échouer.';

  @override
  String get vipIntro =>
      'Tous les pronostics Haute probabilité et du Défi Escalier tant que votre abonnement est en cours.';

  @override
  String get vipLinked => '🔒  Votre accès VIP est lié à votre compte';

  @override
  String get vipManage =>
      'Vous avez déjà Plus. Modifiez ou résiliez votre forfait dans la boutique.';

  @override
  String vipMonthly(String amount) {
    return '≈ $amount/mois';
  }

  @override
  String vipMonths(int months) {
    String _temp0 = intl.Intl.pluralLogic(
      months,
      locale: localeName,
      other: '$months mois',
      one: '$months mois',
    );
    return '$_temp0';
  }

  @override
  String get vipNoExpiry => 'Sans expiration';

  @override
  String get vipPaymentRequired =>
      'La souscription nécessite un canal de paiement configuré.';

  @override
  String get vipPending =>
      'Paiement en attente. Vous aurez accès dès que la boutique le confirmera.';

  @override
  String get vipPickLabel => 'Pronostic VIP';

  @override
  String get vipPlansSoon =>
      'Les offres s\'afficheront lorsqu\'elles seront disponibles.';

  @override
  String get vipPricesNote => 'Prix du catalogue du serveur.';

  @override
  String get vipPurchasesPending =>
      'Achats en préparation : rien n\'est encore facturé depuis l\'application.';

  @override
  String get vipRestore => 'Restaurer les achats';

  @override
  String get vipStatRecorded => 'Taux de réussite enregistré';

  @override
  String get vipStatResolved => 'Résolus';

  @override
  String get vipStoreFailed =>
      'Impossible de confirmer l\'achat. Nous réessaierons à la prochaine ouverture de l\'app.';

  @override
  String get vipStoreTerms =>
      'Se renouvelle automatiquement au même prix jusqu\'à ce que vous le résiliiez dans la boutique.';

  @override
  String get vipStoreUnavailable =>
      'La boutique n\'est pas disponible sur cet appareil.';

  @override
  String get vipSubscribe => 'M\'abonner';

  @override
  String get vipVerifying => 'Vérification de l\'achat auprès de la boutique…';

  @override
  String get welcome1Body =>
      'Découvrez le côté statistique du sport : matchs, analyses et pronostics du projet que vous connaissez déjà sur le web.';

  @override
  String get welcome1Title => 'Football et NBA,\nsous un autre angle';

  @override
  String get welcome2Body =>
      'La forme récente, les confrontations directes et les statistiques aident à comprendre ce qui peut se passer. Commencez par les données.';

  @override
  String get welcome2Title => 'Chaque match,\navec plus de contexte';

  @override
  String get welcome3Body =>
      'Buts, corners, handicap et statistiques de la NBA. Découvrez ce que mesure chaque analyse avant d\'interpréter une sélection.';

  @override
  String get welcome3Title => 'Plus de marchés.\nPlus d\'informations.';

  @override
  String get welcome4Body =>
      'Un pronostic se comprend aussi après le match. L\'historique permet de comparer les estimations aux résultats.';

  @override
  String get welcome4Title => 'Les résultats,\nen un coup d\'œil';

  @override
  String get welcome5Body =>
      'Une probabilité n\'est pas une certitude. Explorez le contenu, examinez le contexte et forgez votre propre jugement.';

  @override
  String get welcome5Title => 'Tout commence\npar s\'informer';

  @override
  String welcomeGoTo(int number) {
    return 'Aller à l\'écran d\'accueil $number';
  }

  @override
  String get welcomeNext => 'Suivant';

  @override
  String welcomeScreenOf(int page, int total) {
    return 'Écran $page sur $total';
  }

  @override
  String get welcomeSkip => 'Passer';

  @override
  String get welcomeStart => 'Commencer';

  @override
  String get updateTitle => 'Mise à jour disponible';

  @override
  String get updateRequired => 'Mettez QuantFut à jour pour continuer.';

  @override
  String get updateOptional =>
      'Une nouvelle version de QuantFut est disponible.';

  @override
  String get updateNow => 'Mettre à jour';

  @override
  String get updateLater => 'Plus tard';

  @override
  String get updateStoreError => 'Impossible d’ouvrir la boutique. Réessayez.';
}
