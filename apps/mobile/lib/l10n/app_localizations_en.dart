// ignore: unused_import
import 'package:intl/intl.dart' as intl;

import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get accessBody1 =>
      'A statistical model calculates the probabilities. A probability is not a certainty.';

  @override
  String get accessBody2 =>
      'Every day, the most likely ones, with their real historical hit rate.';

  @override
  String get accessBody3 =>
      'Follow each challenge\'s progress and how much is left to complete it.';

  @override
  String get accessBody4 =>
      'With its odds and joint probability, so you know what you risk.';

  @override
  String get accessBody5 =>
      'Check in, complete offers and invite friends to unlock predictions.';

  @override
  String get accessCardBody =>
      'Keep your progress and coins on all your devices.';

  @override
  String get accessCardTitle => 'Sign in to continue';

  @override
  String get accessConsent =>
      'I am at least 18 years old and I accept the terms and the privacy policy.';

  @override
  String get accessConsentNeeded => 'Tick the box to continue.';

  @override
  String accessConsentRich(String terms, String privacy) {
    return 'I am 18 or older and I accept the $terms and the $privacy.';
  }

  @override
  String get accessContinueWithGoogle => 'Continue with Google';

  @override
  String get accessDisclaimer =>
      'For information and entertainment only. Predictions do not guarantee results.';

  @override
  String get accessDocumentOpenError => 'The document could not be opened.';

  @override
  String get accessForgotLink => 'Recover previous password';

  @override
  String get accessForgotSent =>
      'If the account exists, you will receive instructions by email.';

  @override
  String get accessGenericError =>
      'Sign-in could not be completed. Please try again.';

  @override
  String get accessGoogleError =>
      'Could not sign in with Google. Please try again.';

  @override
  String get accessKicker1 => 'REAL PROBABILITIES';

  @override
  String get accessKicker2 => 'HIGH PROBABILITY';

  @override
  String get accessKicker3 => 'LADDER CHALLENGE';

  @override
  String get accessKicker4 => 'PARLAY';

  @override
  String get accessKicker5 => 'COINS';

  @override
  String get accessLinkButton => 'Link my account';

  @override
  String get accessLinkEmail => 'Email of your previous account';

  @override
  String get accessLinkIntro =>
      'Link your previous account to keep your balance and access.';

  @override
  String get accessLinkPassword => 'Previous password';

  @override
  String get accessOtherAccount => 'Use another account';

  @override
  String get accessPreparingDocs => 'We are preparing the sign-in documents.';

  @override
  String get accessPrivacy => 'Privacy policy';

  @override
  String get accessRetry => 'Retry sign-in';

  @override
  String get accessTagline =>
      'Matches, analysis and history. A probability is not a certainty.';

  @override
  String get accessTerms => 'Terms of use';

  @override
  String get accessTitle1 => 'Understand every match with data.';

  @override
  String get accessTitle2 => 'Predictions with their hit rate in view.';

  @override
  String get accessTitle3 => 'Climb step by step.';

  @override
  String get accessTitle4 => 'A ticket sealed before the matches.';

  @override
  String get accessTitle5 => 'Earn coins and unlock.';

  @override
  String get adsCardTitle => 'Rewarded videos';

  @override
  String get adsFootnote =>
      'Coins are credited when the video ends. If you close it early, you get no coins.';

  @override
  String get adsLimitReached =>
      'Today\'s limit reached. Come back after 00:00 UTC.';

  @override
  String get adsLoading => 'Loading video…';

  @override
  String get adsPending => 'Your coins will arrive shortly.';

  @override
  String adsProgress(int used, int cap) {
    return 'Today: $used of $cap';
  }

  @override
  String get adsUnavailable =>
      'No videos are available right now. Try again later.';

  @override
  String get adsVerifying => 'Verifying your reward…';

  @override
  String adsWaitFor(String time) {
    return 'Next video in $time';
  }

  @override
  String adsWatchCta(int coins) {
    return 'Watch video · +$coins coins';
  }

  @override
  String alertsAbsencesOf(String team) {
    return '$team absences';
  }

  @override
  String get alertsAdvantage => 'Advantage';

  @override
  String get alertsAdvantageEmpty => 'No advantages reported.';

  @override
  String alertsChecked(String when) {
    return 'Checked $when';
  }

  @override
  String get alertsDisadvantage => 'Disadvantage';

  @override
  String get alertsDisadvantageEmpty => 'No disadvantages reported.';

  @override
  String get alertsDoubt => 'Doubtful';

  @override
  String get alertsNoCheck =>
      'There is no absence check for this match yet. If its league has no data, that does not mean nobody is injured.';

  @override
  String get alertsNote =>
      'Absences can change until kickoff. The official lineup is published shortly before the match.';

  @override
  String get alertsOut => 'Unavailable';

  @override
  String get alertsReasonFoot => 'Ankle or foot injury';

  @override
  String get alertsReasonIllness => 'Illness';

  @override
  String get alertsReasonInjury => 'Injury';

  @override
  String get alertsReasonKnee => 'Knee injury';

  @override
  String get alertsReasonKnock => 'Knock';

  @override
  String get alertsReasonMuscle => 'Muscle injury';

  @override
  String get alertsReasonSuspension => 'Suspension';

  @override
  String get alertsReasonUnknown => 'Reason not given';

  @override
  String get alertsSource => 'Source: API-Football';

  @override
  String alertsSummary(int out, int doubt) {
    String _temp0 = intl.Intl.pluralLogic(
      out,
      locale: localeName,
      other: '$out absences',
      one: '1 absence',
    );
    String _temp1 = intl.Intl.pluralLogic(
      doubt,
      locale: localeName,
      other: '$doubt doubts',
      one: '1 doubt',
    );
    return '$_temp0 · $_temp1';
  }

  @override
  String get alertsSuspended => 'Suspended';

  @override
  String get apiGoogleNotVerified => 'Google could not verify the sign-in.';

  @override
  String get apiInvalidResponse => 'Invalid response from the server.';

  @override
  String get apiInvalidSession => 'Invalid session.';

  @override
  String apiLoadFailed(int status) {
    return 'The information could not be loaded (HTTP $status).';
  }

  @override
  String get apiOffline =>
      'Could not connect. Check your connection and try again.';

  @override
  String get apiSessionExpired => 'Please sign in again.';

  @override
  String get apiSignInWithGoogle => 'Sign in with Google.';

  @override
  String get artAnalyzeEach => 'ANALYZE EACH PICK';

  @override
  String get artCorners => 'CORNERS';

  @override
  String get artFootball => 'FOOTBALL';

  @override
  String get artForm => 'FORM';

  @override
  String get artGoals => 'GOALS';

  @override
  String get artHeadToHead => 'HEAD TO HEAD';

  @override
  String get artHeading0 => 'FOOTBALL + NBA';

  @override
  String get artHeading1 => 'CONTEXT MATTERS';

  @override
  String get artHeading2 => 'EXPLORE THE MARKETS';

  @override
  String get artHeading3 => 'HISTORY AT A GLANCE';

  @override
  String get artHeading4 => 'DATA + YOUR JUDGMENT';

  @override
  String get artNba => 'NBA';

  @override
  String get artStats => 'STATISTICS';

  @override
  String get artTagline => 'ANALYZE. COMPARE. EXPLORE.';

  @override
  String get artTransparency => 'TRANSPARENCY';

  @override
  String get bannerAwaiting => 'MATCH PLAYED · awaiting the official result';

  @override
  String get bannerLive => 'MATCH IN PLAY · prediction sealed before kickoff';

  @override
  String bannerLost(String score) {
    return 'LOST$score · prediction sealed before kickoff';
  }

  @override
  String bannerWon(String score) {
    return 'WON$score · prediction sealed before kickoff';
  }

  @override
  String get calendarEmpty => 'There are no matches for these filters.';

  @override
  String calendarMatchesCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count matches',
      one: '$count match',
    );
    return '$_temp0';
  }

  @override
  String get calendarPickDate => 'Choose date';

  @override
  String get calendarSearchHint => 'Search teams or leagues';

  @override
  String get calendarTitle => 'Calendar · local time';

  @override
  String casesCount(int count, String formatted) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$formatted cases',
      one: '$formatted case',
    );
    return '$_temp0';
  }

  @override
  String get commonAll => 'All';

  @override
  String get commonAway => 'Away';

  @override
  String get commonCancel => 'Cancel';

  @override
  String get commonClose => 'Close';

  @override
  String get commonConfirm => 'Confirm';

  @override
  String get commonConnecting => 'Connecting…';

  @override
  String get commonDraw => 'Draw';

  @override
  String get commonHome => 'Home';

  @override
  String get commonRefresh => 'Refresh';

  @override
  String get commonRetry => 'Retry';

  @override
  String get commonSeeVip => 'View VIP access';

  @override
  String get commonToday => 'Today';

  @override
  String get commonYesterday => 'Yesterday';

  @override
  String countdownDays(int days, String time) {
    return '${days}d $time';
  }

  @override
  String detailChecked(String date) {
    return 'Checked: $date';
  }

  @override
  String get detailFormationPending => 'Formation pending';

  @override
  String get detailH2hTitle => 'Head-to-head history (H2H)';

  @override
  String get detailInjuries => 'Reported absences';

  @override
  String get detailLineups => 'Lineups';

  @override
  String get detailLineupsPending => 'Lineups not confirmed yet.';

  @override
  String get detailNoFeatured =>
      'No prediction for this match qualifies as featured (odds 1.20 to 1.60 and probability 74% to 85%). The open ones are in the list below.';

  @override
  String get detailNoH2h => 'There are no recorded meetings for this match.';

  @override
  String get detailNoInjuries => 'No absences in the available report.';

  @override
  String get detailNoInjuriesCheck => 'No absence check is available.';

  @override
  String get detailNoPicks =>
      'There are no published predictions for this match.';

  @override
  String get detailNoSealedModel =>
      'There is no sealed prediction for this match. The model\'s estimates are below.';

  @override
  String get detailNoSealedModelVip =>
      'There is no sealed prediction for this match. The model\'s estimates are below, with VIP.';

  @override
  String get detailNoStarters => 'No confirmed starters.';

  @override
  String get detailReferee => 'Referee';

  @override
  String get detailRefereePending => 'Referee to be confirmed.';

  @override
  String get detailTabAlerts => 'Alerts';

  @override
  String get detailTabH2h => 'H2H';

  @override
  String get detailTabPredictions => 'Predictions';

  @override
  String get detailTabStats => 'Analysis';

  @override
  String get detailVipPickNotice => 'This match has a VIP prediction';

  @override
  String get dictAwayDefault => 'the away side';

  @override
  String get dictHomeDefault => 'the home side';

  @override
  String dictOddsAbove(String fair) {
    return 'The published odds are above the fair odds ($fair).';
  }

  @override
  String dictOddsBelow(String fair) {
    return 'The published odds are below the fair odds ($fair); the appeal is in the probability, not the price.';
  }

  @override
  String dictPick(String pick, String percent) {
    return '$pick with a calculated probability of $percent.';
  }

  @override
  String get dictPickDefault => 'The prediction';

  @override
  String dictXg(
    String total,
    String home,
    String homeXg,
    String away,
    String awayXg,
  ) {
    return 'Margin-free market odds imply $total expected goals ($home $homeXg · $away $awayXg).';
  }

  @override
  String get disclaimerProbability =>
      'A probability is not a certainty. Decide with information and play responsibly.';

  @override
  String get factsAbsences => 'Absences';

  @override
  String get factsDrew => 'Drew';

  @override
  String get factsHideLineup => 'Hide the eleven';

  @override
  String factsInCompetition(String competition) {
    return 'In $competition';
  }

  @override
  String get factsLastLineup => 'Last known lineup';

  @override
  String get factsLastMatch => 'Last match';

  @override
  String factsLineupMeta(String rival, String date) {
    return 'vs $rival · $date';
  }

  @override
  String get factsLineupNote =>
      'This is that match\'s lineup, not a prediction for today\'s.';

  @override
  String get factsLost => 'Lost';

  @override
  String get factsNoLineup => 'No lineup saved yet.';

  @override
  String get factsNoResult => 'No previous matches recorded.';

  @override
  String get factsSeeAlerts => 'See alerts';

  @override
  String get factsShowLineup => 'Show the eleven';

  @override
  String get factsTitle => 'Match facts';

  @override
  String factsVs(String score, String rival) {
    return '$score vs $rival';
  }

  @override
  String get factsWon => 'Won';

  @override
  String get famCardsSubtitle => 'Under-cards lines with historical backing';

  @override
  String get famCardsTitle => 'Cards';

  @override
  String get famCornersSubtitle => 'Over and under corners for the whole match';

  @override
  String get famCornersTeamSubtitle => 'Home and away, each with its own line';

  @override
  String get famCornersTeamTitle => 'Corners by team';

  @override
  String get famCornersTitle => 'Total corners';

  @override
  String get famDoubleChanceSubtitle =>
      'Two possible outcomes in one selection';

  @override
  String get famDoubleChanceTitle => 'Double chance';

  @override
  String get famGoalsSubtitle => 'Totals with historically evaluated lines';

  @override
  String get famGoalsTitle => 'Match goals';

  @override
  String get famHandicapSubtitle => 'Protection lines and draw with refund';

  @override
  String get famHandicapTitle => 'Asian handicap';

  @override
  String get famNbaSubtitle => 'Exploratory evaluation · pending confirmation';

  @override
  String get famNbaTeamTitle => 'NBA · Team points';

  @override
  String get famNbaTotalTitle => 'NBA · Game total';

  @override
  String get famNbaWinnerTitle => 'NBA · Winner';

  @override
  String get famTeamGoalsSubtitle =>
      'At least one goal by the home or away side';

  @override
  String get famTeamGoalsTitle => 'A team scores';

  @override
  String get famWinnerSubtitle => 'High-probability 1X2 result';

  @override
  String get famWinnerTitle => 'Match winner';

  @override
  String get featAgenda => 'Schedule temporarily unavailable';

  @override
  String get featBalance => 'Tracking in preparation';

  @override
  String get featCommunity => 'Community in preparation';

  @override
  String get featLanguages => 'Translations in preparation';

  @override
  String get featMatchData => 'Match data temporarily unavailable';

  @override
  String get featMeasurement => 'Measurement in preparation';

  @override
  String get featNba => 'NBA model in training';

  @override
  String get featNotifications => 'Notifications in preparation';

  @override
  String get featPurchases => 'Purchases in preparation';

  @override
  String get featStats => 'Statistics temporarily unavailable';

  @override
  String get featVip => 'VIP access temporarily unavailable';

  @override
  String get featureTraining => 'Model in training';

  @override
  String get fixtureFinished => 'FINISHED';

  @override
  String get fixtureLive => 'LIVE';

  @override
  String get fixtureLocalTime => 'LOCAL TIME';

  @override
  String get fixtureStartsIn => 'STARTS IN';

  @override
  String get fixtureTbd => 'TO BE CONFIRMED';

  @override
  String get forecastCanFail =>
      'A prediction can fail; probability does not guarantee the result.';

  @override
  String get forecastFeatured => 'FEATURED';

  @override
  String get forecastFree => 'FREE';

  @override
  String get forecastHalfTime => 'HALF-TIME';

  @override
  String get forecastInPlay => 'IN PLAY';

  @override
  String get forecastLiveScore => 'Live score';

  @override
  String forecastLiveScoreAgo(int minutes) {
    return 'Live score · updated $minutes min ago';
  }

  @override
  String get forecastMarketNote =>
      'Probabilities calculated from margin-free market odds: this league has no model of its own.';

  @override
  String get forecastOddsAtPublish => 'Odds at publication';

  @override
  String forecastProbCalc(String percent) {
    return '$percent calculated prob.';
  }

  @override
  String get forecastSeeStats => 'View match statistics';

  @override
  String get forecastSourceMarket => 'MARKET ODDS';

  @override
  String get forecastSourceModel => 'OWN MODEL';

  @override
  String get forecastTitle => 'STATISTICAL ANALYSIS';

  @override
  String get forecastUnlocked => 'UNLOCKED';

  @override
  String get forecastVerdictTitle => '💡  MODEL VERDICT';

  @override
  String get formatScheduleUnavailable => 'Time not available';

  @override
  String get groupBtts => 'BOTH TEAMS TO SCORE';

  @override
  String get groupCards => 'CARDS';

  @override
  String get groupCorners => 'CORNERS';

  @override
  String get groupDoubleChance => 'DOUBLE CHANCE';

  @override
  String get groupDrawNoBet => 'DRAW NO BET';

  @override
  String get groupFirstHalf => '1ST HALF';

  @override
  String get groupGoals => 'GOALS';

  @override
  String get groupHandicap => 'HANDICAP';

  @override
  String get groupResult => 'RESULT';

  @override
  String get groupSpecials => 'SPECIALS';

  @override
  String get groupTeamGoals => 'TEAM GOALS';

  @override
  String get guideBody1 =>
      'If a prediction has a 75% probability, the model expects it to come true about 3 times out of 4 when a similar situation repeats. That means 1 in 4 will not. No data guarantees a specific result.';

  @override
  String get guideBody2 =>
      'Odds are set by a bookmaker and include its margin. Comparing the model\'s probability with the one implied by the odds helps you judge whether the price is reasonable; it does not ensure the result.';

  @override
  String get guideBody3 =>
      'They are published with their probability and reference odds before kickoff and cannot be edited. That is why you can compare the real historical hit rate with the promised one.';

  @override
  String get guideBody4 =>
      'In a parlay, the joint probability is the product of each selection\'s, so it drops quickly as you add matches. A high price usually reflects exactly that.';

  @override
  String get guideBody5 =>
      'Each challenge goes in steps and the next one only counts if the previous one is met. Check the progress and the history, failed challenges included, before following one.';

  @override
  String get guideBody6 =>
      'QuantFut is not a bookmaker and does not ensure profits. If you decide to bet, only use money you can afford to lose and only if you are of legal age. If gambling stops being a pastime, ask for help.';

  @override
  String get guideHead1 => 'A probability is not a certainty';

  @override
  String get guideHead2 => 'Odds are a price, not the model\'s opinion';

  @override
  String get guideHead3 => 'Every prediction is sealed before the match';

  @override
  String get guideHead4 => 'More selections, lower probability';

  @override
  String get guideHead5 => 'You move up one step at a time';

  @override
  String get guideHead6 => 'It is information and entertainment';

  @override
  String get guideSubtitle => 'Learn to read the data before you decide.';

  @override
  String get guideTitle => 'Predictions guide';

  @override
  String get guideTopic1 => 'PROBABILITY';

  @override
  String get guideTopic2 => 'ODDS';

  @override
  String get guideTopic3 => 'HIGH PROBABILITY';

  @override
  String get guideTopic4 => 'PARLAY';

  @override
  String get guideTopic5 => 'LADDER CHALLENGE';

  @override
  String get guideTopic6 => 'RESPONSIBILITY';

  @override
  String get homeBannerClose => 'Dismiss notice';

  @override
  String get homeByDate => 'Matches by date and time';

  @override
  String homeForecastAt(String when, String mexico) {
    return 'Forecast on $when ($mexico Mexico time)';
  }

  @override
  String get homeForecastPending => 'Forecast pending';

  @override
  String get homeMenuTooltip => 'Menu';

  @override
  String get homeNoMatchesDay => 'No matches on this day.';

  @override
  String get homeSeeAll => 'See all';

  @override
  String homeTicketJoint(String percent) {
    return 'Joint prob. $percent';
  }

  @override
  String homeTicketLegs(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count selections',
      one: '$count selection',
    );
    return '$_temp0';
  }

  @override
  String homeTicketOdds(String value) {
    return 'Odds $value';
  }

  @override
  String get homeTicketsEmpty => 'No tickets yet today';

  @override
  String get homeTicketsTitle => 'Tickets of the day';

  @override
  String get homeToday => 'Today';

  @override
  String get homeTomorrow => 'Tomorrow';

  @override
  String get inboxEmpty => 'You have no alerts yet.';

  @override
  String get inboxMatch => 'Match';

  @override
  String get inboxTitle => 'Alerts';

  @override
  String ladderActiveCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count challenges in progress',
      one: '1 challenge in progress',
    );
    return '$_temp0';
  }

  @override
  String get ladderBalance => 'current balance';

  @override
  String get ladderChance => 'to complete';

  @override
  String get ladderEmpty => 'There are no active challenges published.';

  @override
  String ladderEstimateNote(String avg) {
    return 'Estimate: uses the probability of the step in play and the average of the rest ($avg). Not a guarantee.';
  }

  @override
  String get ladderFreeHint =>
      'One free step: the one with the highest probability.';

  @override
  String get ladderHideSteps => 'Hide steps';

  @override
  String get ladderHistoryDone => 'Completed';

  @override
  String get ladderHistoryEmpty =>
      'No challenges have closed yet. When one ends, it will show up here with its result.';

  @override
  String get ladderHistoryExpired => 'Expired before completion';

  @override
  String ladderHistoryFailedAt(int step) {
    return 'Failed at step $step';
  }

  @override
  String ladderHistoryRate(String rate) {
    return 'Completion rate: $rate';
  }

  @override
  String ladderHistoryResult(String roi) {
    return 'Cumulative result: $roi';
  }

  @override
  String get ladderHistoryShown =>
      'Showing the latest completed challenges and the latest failed one.';

  @override
  String ladderHistorySummary(int done, int closed) {
    return '$done completed of $closed closed';
  }

  @override
  String get ladderHistoryTitle => 'Challenge history';

  @override
  String get ladderNoteInPlay =>
      'A step is waiting for its result. The challenge is still alive.';

  @override
  String get ladderNoteToPick =>
      'The next step is yet to be picked; it can take days. The challenge is still alive.';

  @override
  String ladderRemaining(int remaining) {
    String _temp0 = intl.Intl.pluralLogic(
      remaining,
      locale: localeName,
      other: '$remaining to go',
      one: '1 to go',
    );
    return '$_temp0';
  }

  @override
  String get ladderShowSteps => 'Show steps';

  @override
  String get ladderStatusInPlay => 'In play';

  @override
  String get ladderStatusToPick => 'Pick pending';

  @override
  String ladderTitle(Object id, int steps) {
    String _temp0 = intl.Intl.pluralLogic(
      steps,
      locale: localeName,
      other: '$steps steps',
      one: '$steps step',
    );
    return 'Challenge #$id · $_temp0';
  }

  @override
  String ladderWonOf(int won, int goal) {
    return '$won of $goal won';
  }

  @override
  String get languageFirstBadge => 'Language setup';

  @override
  String get languageFirstHint =>
      'Set the language of your analysis for a better experience';

  @override
  String get languageFirstTitle => 'Select your language';

  @override
  String get languageHint =>
      'Choose your language. It is saved on this device and in your account.';

  @override
  String get languageTitle => 'App language';

  @override
  String get ledgerAd => 'Rewarded video';

  @override
  String get ledgerAttendance => 'Check-in';

  @override
  String get ledgerInvitee => 'Welcome reward';

  @override
  String get ledgerOffer => 'Offer completed';

  @override
  String get ledgerReferralReversal => 'Referral reward reversed';

  @override
  String get ledgerReferrer => 'Referral reward';

  @override
  String get ledgerReversal => 'Offer voided';

  @override
  String get ledgerUnlock => 'Prediction unlocked';

  @override
  String get levelHigh => 'HIGH PROB.';

  @override
  String get levelModerate => 'MODERATE';

  @override
  String get levelSolid => 'SOLID';

  @override
  String get lineAwayScores => 'Away team scores · over 0.5 goals';

  @override
  String get lineDoubleChance => 'Double chance · 1X / X2 / 12';

  @override
  String lineHandicap(String line) {
    return 'Handicap $line';
  }

  @override
  String get lineHomeScores => 'Home team scores · over 0.5 goals';

  @override
  String lineTeamCorners(String team, String side, String line) {
    String _temp0 = intl.Intl.selectLogic(side, {
      'over': 'over $line corners',
      'other': 'under $line corners',
    });
    return '$team: $_temp0';
  }

  @override
  String get lineWinner => 'Winner · high-probability selection';

  @override
  String get maintenanceNotice =>
      'We are performing maintenance. Some features may take longer.';

  @override
  String get marketAwayScores => 'Away team scores';

  @override
  String get marketBtts => 'Both teams to score';

  @override
  String get marketCards => 'Cards';

  @override
  String get marketCorners => 'Corners';

  @override
  String get marketCornersAway => 'Away corners';

  @override
  String get marketCornersHome => 'Home corners';

  @override
  String get marketDoubleChance => 'Double chance';

  @override
  String get marketGoals => 'Goals';

  @override
  String get marketGoalsAway => 'Away goals';

  @override
  String get marketGoalsHome => 'Home goals';

  @override
  String get marketHandicap => 'Handicap';

  @override
  String get marketHomeScores => 'Home team scores';

  @override
  String get marketHtBtts => 'Both teams to score in the 1st half';

  @override
  String get marketHtGoal => 'Goal in the 1st half';

  @override
  String get marketResult1x2 => '1X2 result';

  @override
  String get marketUnknown => 'Market';

  @override
  String get marketWinToNil => 'Win to nil';

  @override
  String get marketsAndResults => 'Markets and results';

  @override
  String marketsEvidenceAt(String date) {
    return 'Evidence as of $date';
  }

  @override
  String get marketsFamiliesRadar => 'market families on the radar';

  @override
  String marketsHistoricHit(String percent) {
    return 'historical hit rate $percent';
  }

  @override
  String get marketsInReview => 'Under review: no confirmed line';

  @override
  String get marketsModelActive => 'MODEL ACTIVE';

  @override
  String get marketsNoLineLabel => 'no confirmed line';

  @override
  String get marketsNoPublications => 'No publications yet';

  @override
  String get marketsNoResolved => 'No resolved predictions';

  @override
  String marketsPublished(int won, int cases) {
    return 'Published $won/$cases';
  }

  @override
  String marketsPublishedWon(int won, int cases, String percent) {
    return '$won/$cases published predictions won · $percent';
  }

  @override
  String get marketsRadarNote =>
      'The ring is the historical hit rate of each market\'s best validated line; “Published” are the predictions already resolved. They are pre-match predictions, not live alerts, and no probability guarantees a result.';

  @override
  String get matchAwaitingResult => 'Awaiting result';

  @override
  String mdCornersTotal(Object total) {
    return 'corners · total $total';
  }

  @override
  String get mdEmptyHistory =>
      'There are no resolved predictions in this market yet.';

  @override
  String get mdEmptyToday =>
      'There are no predictions available right now for this market. They appear when the model publishes them, before the match.';

  @override
  String get mdHitRate => 'Hit rate';

  @override
  String get mdLineConfirmed => 'Confirmed';

  @override
  String get mdLineNotDeployed => 'Not deployed';

  @override
  String get mdLineReview => 'Under review';

  @override
  String get mdLineShort => 'Small sample';

  @override
  String get mdLoadError => 'The history could not be loaded.';

  @override
  String get mdModel => 'MODEL';

  @override
  String get mdNoDate => 'No date';

  @override
  String get mdOverall => 'Overall';

  @override
  String get mdTabPrevious => 'Previous';

  @override
  String mdTabToday(int count) {
    return 'Today ($count)';
  }

  @override
  String get mdValidatedLines => 'Validated lines';

  @override
  String get mmChance => 'VALUE';

  @override
  String get mmDisclaimer =>
      'This is model analysis, not a betting recommendation. “Fair odds” is 1/probability: it is not a bookmaker\'s price. A prediction can fail.';

  @override
  String get mmFairOdds => 'fair odds';

  @override
  String mmGroupCount(String group, int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count markets',
      one: '$count market',
    );
    return '$group · $_temp0';
  }

  @override
  String mmLocked(int count) {
    return '$count locked';
  }

  @override
  String mmOpen(int count) {
    return '$count open';
  }

  @override
  String mmProb(int value) {
    return '$value% prob.';
  }

  @override
  String get mmPublishedOdds => 'published odds';

  @override
  String get mmScoresTitle => 'Most likely scores';

  @override
  String get mmScoresVip => 'The most likely scores are for VIP.';

  @override
  String get mmTitle => 'Match markets';

  @override
  String get moreApp => 'App';

  @override
  String get moreGuide => 'Predictions guide';

  @override
  String get moreGuideSub => 'How to read probabilities, odds and challenges';

  @override
  String get moreLearn => 'Learn';

  @override
  String get moreLegal => 'Legal';

  @override
  String get moreRate => 'Rate the app';

  @override
  String get moreRateSub => 'Share your opinion';

  @override
  String get moreShare => 'Share the app';

  @override
  String get moreShareMessage =>
      'Check out QuantFut: football probabilities backed by data, no promises. https://pronosticosdeportivos.pro';

  @override
  String get moreShareSub => 'Invite your friends';

  @override
  String get moreStoreError => 'Could not open the app store.';

  @override
  String get navCoins => 'Coins';

  @override
  String get navHome => 'Home';

  @override
  String get navMarkets => 'Markets';

  @override
  String get navPredictions => 'Predictions';

  @override
  String get navProfile => 'Profile';

  @override
  String noteExpectedAverage(String value) {
    return 'Expected average: $value';
  }

  @override
  String noteExpectedGoals(String value) {
    return 'Expected goals: $value';
  }

  @override
  String noteXg(String home, String homeValue, String away, String awayValue) {
    return 'xG: $home $homeValue · $away $awayValue';
  }

  @override
  String get notificationIosPending =>
      'iOS notifications are waiting for Apple configuration.';

  @override
  String get notificationPermissionDenied =>
      'Enable the permission from your device settings.';

  @override
  String get outcomeLoss => 'Lost';

  @override
  String get outcomePush => 'Refund';

  @override
  String get outcomeWin => 'Won';

  @override
  String parleyChipLine(int count, String min, String max) {
    return 'Up to $count parlays · odds $min–$max';
  }

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
    return '$won/$settled won';
  }

  @override
  String get parleyDisclaimer =>
      'It is chosen by probability, not by value, and each leg reduces the margin. A parlay can fail: multiplying odds also multiplies the risk.';

  @override
  String get parleyFewNote =>
      'With few parlays the actual rate does not prove anything yet.';

  @override
  String get parleyFreeChip => '1 free per day';

  @override
  String get parleyFreeNote =>
      'One free per day (the lowest odds); the rest are VIP.';

  @override
  String get parleyHistoryTitle => 'Parlay history';

  @override
  String get parleyInactiveBody =>
      'When it is activated you will see the day\'s parlays here, sealed before the matches start.';

  @override
  String get parleyInactiveTitle => 'The Parlay is not active yet';

  @override
  String get parleyInfoTitle => 'How a parlay is chosen';

  @override
  String parleyJointProb(String percent, int legs) {
    String _temp0 = intl.Intl.pluralLogic(
      legs,
      locale: localeName,
      other: '$legs legs',
      one: '$legs leg',
    );
    return '$percent joint probability · $_temp0';
  }

  @override
  String get parleyLoadError => 'The Parlay could not be loaded.';

  @override
  String get parleyNoHistory =>
      'There is no parlay history yet. It will appear here once the first one settles.';

  @override
  String get parleyNoneBody =>
      'The model does not publish a parlay if it cannot find one within the rules.';

  @override
  String get parleyNoneTitle => 'No parlays today';

  @override
  String parleyOddsBetween(String min, String max) {
    return 'Odds between $min and $max';
  }

  @override
  String get parleyOutcomeLoss => 'Lost';

  @override
  String get parleyOutcomePending => 'Pending';

  @override
  String get parleyOutcomeVoid => 'Void';

  @override
  String get parleyOutcomeWin => 'Won';

  @override
  String get parleyPastDays => 'Previous days';

  @override
  String parleyRange(int count, String min, String max) {
    return 'From 1 to $count parlays · odds between $min and $max · the most likely of each step';
  }

  @override
  String parleyResultScore(Object score) {
    return 'Result $score';
  }

  @override
  String get parleySealed => 'Parlays sealed before the matches';

  @override
  String parleyStep(Object step) {
    return 'STEP $step';
  }

  @override
  String parleySummary(Object hits, Object total) {
    return '$hits/$total parlays won';
  }

  @override
  String parleySummaryPromised(String value) {
    return ' vs $value% promised';
  }

  @override
  String parleySummaryReal(String value) {
    return ' · $value% actual';
  }

  @override
  String pickOddsAtPublish(Object book) {
    return 'Odds at publication · $book';
  }

  @override
  String pickProbability(String percent) {
    return 'Probability $percent';
  }

  @override
  String get pickSeeAnalysis => 'View match analysis';

  @override
  String get pickSourceNA => 'Source not available';

  @override
  String pickUnlockCoins(Object cost) {
    return 'Unlock for $cost coins';
  }

  @override
  String get pickUnlockPrompt => 'Unlock the prediction and its odds.';

  @override
  String get pickUnlockVip => 'Unlock VIP prediction';

  @override
  String picksAllHeading(int count) {
    return 'Predictions · $count';
  }

  @override
  String get picksBestProb => 'Highest probability';

  @override
  String picksCoinsShort(Object cost) {
    return '$cost coins';
  }

  @override
  String get picksEmpty =>
      'There are no published predictions pending in this range.';

  @override
  String picksFreeHeading(int count) {
    return 'Free · $count';
  }

  @override
  String get picksLockedHide => 'Hide the list';

  @override
  String get picksLockedHint =>
      'With VIP you see the pick, the probability and the analysis';

  @override
  String get picksLockedShow => 'Show the list';

  @override
  String picksLockedTitle(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count more predictions with VIP',
      one: '1 more prediction with VIP',
    );
    return '$_temp0';
  }

  @override
  String picksRangeHint(int min, int max, int free) {
    return '$min–$max% probability · $free% free';
  }

  @override
  String get picksSeeAnalysis => 'See analysis';

  @override
  String get picksTomorrow => 'Tomorrow';

  @override
  String picksTrainingReasons(String reasons) {
    return 'Model in training · $reasons';
  }

  @override
  String picksTrustDetail(int hits, int total) {
    return '$hits of $total predictions';
  }

  @override
  String picksTrustPromised(String percent) {
    return 'Promised: $percent';
  }

  @override
  String get picksTrustTitle => 'Hit rate to date';

  @override
  String get prefsAdsBody =>
      'Shares encrypted account, device and purchase data with Meta to measure which ads work. In California, turning it off means “Do not share my data”.';

  @override
  String get prefsAdsTitle => 'Ad measurement (Meta)';

  @override
  String get prefsAnalyticsBody =>
      'Helps improve the app with data about the screens used. It is optional.';

  @override
  String get prefsAnalyticsTitle => 'Usage measurement';

  @override
  String get prefsDeleteAccount => 'Request deletion of my account';

  @override
  String get prefsDeleteAccountHint =>
      'See the steps and the contact details of Saptain LTD.';

  @override
  String get prefsDiagnosticsBody =>
      'Sends technical information to Firebase and Sentry to diagnose failures. It is optional.';

  @override
  String get prefsDiagnosticsTitle => 'Error and performance reports';

  @override
  String get prefsInbox => 'Alerts inbox';

  @override
  String get prefsLanguageNote =>
      'The language applies to the whole app and is saved as a preference.';

  @override
  String get prefsNote =>
      'You can use the basic features without enabling measurement or diagnostics. Changing these options does not automatically delete data already sent.';

  @override
  String get prefsNotificationsOff =>
      'Available once Google sign-in is complete.';

  @override
  String get prefsNotificationsOn =>
      'You can turn them off whenever you like. Alerts may appear on the lock screen.';

  @override
  String get prefsNotificationsTitle => 'QuantFut notifications';

  @override
  String get prefsPrivacyRights => 'Privacy and your rights';

  @override
  String get prefsTitle => 'Privacy and preferences';

  @override
  String get privacyUpdateBody =>
      'You can now subscribe with Google Play or the App Store, and usage measurement, diagnostics and Meta ad measurement are turned on. You can turn them off in Preferences.';

  @override
  String get privacyUpdateOk => 'Got it';

  @override
  String get privacyUpdateRead => 'Read the policy';

  @override
  String get privacyUpdateTitle => 'We updated our privacy notice';

  @override
  String get probBarAway => 'Away';

  @override
  String get probBarDraw => 'Draw';

  @override
  String get probBarHome => 'Home';

  @override
  String get profileAppVersion => 'App version';

  @override
  String get profileBalance => 'Balance and tracking';

  @override
  String get profileConnected => 'QuantFut · Connected to the server';

  @override
  String get profileCreateAccount => 'Create account';

  @override
  String get profileCreateOne => 'Create an account';

  @override
  String get profileEmail => 'Email';

  @override
  String get profileEmailPending => 'Email pending verification';

  @override
  String get profileEmailVerified => 'Email verified';

  @override
  String get profileForgot => 'I forgot my password';

  @override
  String get profileForgotSent =>
      'If the account exists, you will receive the instructions by email.';

  @override
  String get profileFreePlan => 'Free plan';

  @override
  String get profileGeneral => 'General';

  @override
  String get profileHaveAccount => 'I already have an account';

  @override
  String get profileLanguage => 'Language';

  @override
  String get profileMeasurement => 'Measurement and errors';

  @override
  String get profileNotifications => 'Notifications';

  @override
  String get profileOddsFormat => 'Odds format';

  @override
  String get profileOddsFormatValue => 'Decimal · Odds recorded at publication';

  @override
  String get profilePassword => 'Password';

  @override
  String get profilePreferences => 'Preferences';

  @override
  String get profileRefreshAccess => 'Refresh my access';

  @override
  String get profileSeePlans => 'View VIP plans';

  @override
  String get profileSendVerification => 'Send verification email';

  @override
  String get profileSignIn => 'Sign in';

  @override
  String get profileSignOut => 'Sign out';

  @override
  String get profileTitle => 'Profile and settings';

  @override
  String profileValidUntil(String date) {
    return 'Valid until: $date';
  }

  @override
  String get profileVerificationSent => 'Verification email sent.';

  @override
  String get profileVipActive => 'VIP access active';

  @override
  String get profileYourAccount => 'Your QuantFut account';

  @override
  String resultLabel(String score) {
    return 'Result: $score';
  }

  @override
  String get rewardsAttendanceSub => 'Once a day · resets at 00:00 UTC';

  @override
  String get rewardsAttendanceTitle => 'Daily check-in';

  @override
  String get rewardsAvailable => 'Available';

  @override
  String get rewardsCheckIn => 'Check in';

  @override
  String get rewardsCheckInNote =>
      'Once per UTC day. If you skip a day, the streak resets.';

  @override
  String rewardsChipRate(Object cost) {
    return '$cost coins = 1 prediction';
  }

  @override
  String rewardsChipStreak(int days) {
    String _temp0 = intl.Intl.pluralLogic(
      days,
      locale: localeName,
      other: '$days-day streak',
      one: '1-day streak',
    );
    return '$_temp0';
  }

  @override
  String rewardsClaimCta(Object coins) {
    return 'Check in · +$coins';
  }

  @override
  String rewardsClaimed(Object coins) {
    return '+$coins coins';
  }

  @override
  String get rewardsClaimedToday => 'Claimed today';

  @override
  String get rewardsCodeCopied => 'Code copied.';

  @override
  String get rewardsCodeRegistered => 'Invitation code registered.';

  @override
  String rewardsComingSoon(String names) {
    return 'Coming soon: $names';
  }

  @override
  String get rewardsCopy => 'Copy';

  @override
  String rewardsCopyCode(Object code) {
    return 'Copy my code · $code';
  }

  @override
  String rewardsDay(int number) {
    return 'Day $number';
  }

  @override
  String get rewardsDebt => 'Balance pending due to voided rewards.';

  @override
  String get rewardsEarnTitle => 'Earn coins today';

  @override
  String get rewardsEnough => 'You have enough coins for an unlock.';

  @override
  String get rewardsGo => 'Go';

  @override
  String rewardsInviteChip(Object coins) {
    return '+$coins for you';
  }

  @override
  String rewardsInviteCondition(Object min) {
    return 'After verifying the email and completing $min coins in confirmed offers.';
  }

  @override
  String rewardsInviteFriend(Object coins) {
    return 'Your friend gets +$coins when they enter your code';
  }

  @override
  String rewardsInviteReward(Object referrer, Object invitee) {
    return 'You +$referrer · Your friend +$invitee coins';
  }

  @override
  String get rewardsInviteTitle => 'Invite your friends';

  @override
  String get rewardsInviterCode => 'Code of the person who invited you';

  @override
  String get rewardsLedgerEmpty => 'There are no transactions yet.';

  @override
  String get rewardsLedgerLess => 'Show less';

  @override
  String get rewardsLedgerMore => 'Show more';

  @override
  String get rewardsLedgerTitle => 'My transactions';

  @override
  String rewardsMissing(int missing) {
    String _temp0 = intl.Intl.pluralLogic(
      missing,
      locale: localeName,
      other: '$missing coins left until your next unlock.',
      one: '$missing coin left until your next unlock.',
    );
    return '$_temp0';
  }

  @override
  String get rewardsMissingUnknown => '— coins left until your next unlock.';

  @override
  String get rewardsMyCoins => 'My coins';

  @override
  String rewardsNextIn(String time) {
    return 'Next check-in in $time';
  }

  @override
  String get rewardsOfferAvailable =>
      'Offers depend on your country and device';

  @override
  String get rewardsOfferPending => 'Pending activation';

  @override
  String get rewardsOffersConfig =>
      'This provider isn\'t ready yet. Try again later.';

  @override
  String get rewardsOffersCta => 'See offers';

  @override
  String get rewardsOffersLead => 'Complete offers and receive coins.';

  @override
  String get rewardsOffersLoadFailed =>
      'We couldn\'t open the offers. Check your connection and try again.';

  @override
  String get rewardsOffersTimeout =>
      'The offers took too long to load. Try again.';

  @override
  String get rewardsOffersTitle => 'Offers to earn coins';

  @override
  String get rewardsOffersUnavailable =>
      'No offers are available right now. Try again later.';

  @override
  String get rewardsOperationDone => 'Operation confirmed.';

  @override
  String get rewardsPaste => 'Paste code';

  @override
  String get rewardsPasteEmpty =>
      'There is no invitation code on the clipboard.';

  @override
  String rewardsReferralStats(Object registered, Object qualified) {
    return '$registered registered · $qualified validated';
  }

  @override
  String get rewardsRefreshBalance => 'Refresh balance';

  @override
  String get rewardsRegisterCode => 'Register code';

  @override
  String get rewardsShare => 'Share my code';

  @override
  String rewardsShareMessage(String code, String link) {
    return 'Use my invitation code $code in QuantFut: in Coins, enter it under “Code of who invited you”. Everything is explained here: $link';
  }

  @override
  String get rewardsSignIn => 'Sign in';

  @override
  String get rewardsSignInHint =>
      'Sign in from Profile to save your balance, check in and use a referral code.';

  @override
  String rewardsStreak(int days) {
    String _temp0 = intl.Intl.pluralLogic(
      days,
      locale: localeName,
      other: '$days days',
      one: '$days day',
    );
    return 'Check-in streak · $_temp0';
  }

  @override
  String get rewardsTermsTitle => 'Rules and conditions';

  @override
  String rewardsUnlockFor(Object cost) {
    return 'Unlock a prediction for $cost coins';
  }

  @override
  String get selBttsNo => 'Both teams do not score';

  @override
  String get selBttsYes => 'Both teams score';

  @override
  String selCards(String side, String line) {
    String _temp0 = intl.Intl.selectLogic(side, {
      'over': 'Over $line cards',
      'other': 'Under $line cards',
    });
    return '$_temp0';
  }

  @override
  String selCorners(String side, String line) {
    String _temp0 = intl.Intl.selectLogic(side, {
      'over': 'Over $line corners',
      'other': 'Under $line corners',
    });
    return '$_temp0';
  }

  @override
  String selCornersTeam(String side, String line, String team) {
    String _temp0 = intl.Intl.selectLogic(side, {
      'over': 'Over $line $team corners',
      'other': 'Under $line $team corners',
    });
    return '$_temp0';
  }

  @override
  String selDrawNoBet(String team) {
    return '$team to win (draw refunds)';
  }

  @override
  String selEitherNoDraw(String home, String away) {
    return '$home or $away (no draw)';
  }

  @override
  String selGoals(String side, String line) {
    String _temp0 = intl.Intl.selectLogic(side, {
      'over': 'Over $line goals',
      'other': 'Under $line goals',
    });
    return '$_temp0';
  }

  @override
  String selHandicapLong(String team, String line) {
    return '$team $line (Asian handicap)';
  }

  @override
  String selHandicapShort(String team, String line) {
    return '$team $line';
  }

  @override
  String selHomeWins(String team) {
    return '$team to win';
  }

  @override
  String get selHtBttsNo => 'Both teams do not score in the 1st half';

  @override
  String get selHtGoalYes => 'There will be a goal in the 1st half';

  @override
  String selTeamGoalsLine(String side, String line, String team) {
    String _temp0 = intl.Intl.selectLogic(side, {
      'over': 'Over $line $team goals',
      'other': 'Under $line $team goals',
    });
    return '$_temp0';
  }

  @override
  String selTeamOrDraw(String team) {
    return '$team or draw';
  }

  @override
  String selTeamScores(String team) {
    return '$team to score';
  }

  @override
  String selWinToNil(String team) {
    return '$team wins without conceding';
  }

  @override
  String get shellNeedCoinsBody =>
      'Earn coins with the daily check-in and offers to unlock this prediction.';

  @override
  String get shellNeedCoinsCta => 'Earn coins';

  @override
  String get shellNeedCoinsTitle => 'You need more coins';

  @override
  String get shellNewAlert => 'New QuantFut alert';

  @override
  String get shellSignInForCoins => 'Sign in from Profile to use your coins.';

  @override
  String shellUnlockBody(Object cost) {
    return '$cost coins will be deducted from your balance. Access applies to this prediction.';
  }

  @override
  String get shellUnlockTitle => 'Unlock prediction';

  @override
  String get shellView => 'View';

  @override
  String get splashTagline => 'FOOTBALL · NBA · STATISTICS';

  @override
  String get startupFailed => 'We could not start QuantFut. Please try again.';

  @override
  String get startupLoading => 'Starting QuantFut';

  @override
  String statAveragesNote(Object homeN, Object awayN) {
    return 'Averages from $homeN matches of the home side and $awayN of the away side. Coverage of shots, corners and xG may be partial.';
  }

  @override
  String get statBestAway => 'Best away win';

  @override
  String get statBestHome => 'Best home win';

  @override
  String get statCleanSheet => 'Clean sheets';

  @override
  String get statCompareNote =>
      'The bars compare recorded values; they do not represent win probabilities. Fewer goals conceded is better.';

  @override
  String get statCompareTitle => 'Team comparison';

  @override
  String get statDrawStreak => 'Draw streak';

  @override
  String get statFormLegend =>
      'W: won · D: draw · L: lost. Most recent on the left.';

  @override
  String get statFormNA => 'Form not available.';

  @override
  String get statFormTitle => 'Team form';

  @override
  String get statGoalsAgainst => 'Goals against';

  @override
  String get statGoalsAvgNote =>
      'Goals scored per match; this is not the model\'s goal projection.';

  @override
  String get statGoalsAvgTitle => 'HISTORICAL GOALS AVERAGE';

  @override
  String get statGoalsFor => 'Goals for';

  @override
  String statH2hSummary(
    Object n,
    Object home,
    Object homeWins,
    Object away,
    Object awayWins,
    Object draws,
  ) {
    return 'In $n recorded meetings: $home won $homeWins, $away won $awayWins and there were $draws draws.';
  }

  @override
  String get statH2hTitle => 'Head to head';

  @override
  String statLastMatches(int count) {
    return 'Last $count recorded matches';
  }

  @override
  String get statMinutesNA =>
      'The distribution by minute is not available for this match.';

  @override
  String get statMinutesTitle => 'Goals per minute';

  @override
  String get statNeedsAccess =>
      'This match\'s prediction requires VIP access or an unlock with coins.';

  @override
  String get statOnTargetShort => 'On target';

  @override
  String get statOver25 => 'Over 2.5 goals';

  @override
  String statPickProbOdds(String percent, String odds) {
    return 'Probability $percent · Odds @ $odds';
  }

  @override
  String statPlayed(Object played) {
    return '$played played';
  }

  @override
  String statPoints(Object points) {
    return '$points points';
  }

  @override
  String get statPoissonNA =>
      'The Poisson distribution and likely scores are not yet available in this match\'s delivery.';

  @override
  String get statPoissonTitle => 'Poisson goal distribution';

  @override
  String statPosition(Object position) {
    return 'Position $position';
  }

  @override
  String get statProbNA => 'Model probabilities not available yet.';

  @override
  String get statProbTitle => 'WIN PROBABILITY · 1X2';

  @override
  String get statPublishedPick => 'PUBLISHED PREDICTION';

  @override
  String get statRadarNeeds =>
      'The chart comparison needs at least three metrics available for both teams.';

  @override
  String get statRadarNote =>
      'Relative scale per axis. A larger area does not imply a higher chance of winning.';

  @override
  String get statResDraw => 'D';

  @override
  String get statResLoss => 'L';

  @override
  String get statResWin => 'W';

  @override
  String statResultsAvailable(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count results available',
      one: '$count result available',
    );
    return '$_temp0';
  }

  @override
  String get statSeasonTitle => 'Season and recent results';

  @override
  String get statShots => 'Shots';

  @override
  String get statShotsOnTarget => 'Shots on target';

  @override
  String get statStandingNA => 'Standings not available.';

  @override
  String get statSummaryTitle => 'Prediction summary';

  @override
  String get statTeamStatsTitle => 'Team statistics';

  @override
  String get statWinStreak => 'Winning streak';

  @override
  String get statXgHistoric => 'Historical xG';

  @override
  String get streamHighProb => 'High probability';

  @override
  String get streamLadder => 'Ladder Challenge';

  @override
  String get streamParley => 'Parlay';

  @override
  String tileFairOdds(String value) {
    return 'Fair odds $value';
  }

  @override
  String get tileFavorite => '1X2 favorite';

  @override
  String tileFavoriteLead(String team, int pts) {
    return '$team · +$pts pts';
  }

  @override
  String get tileFavoriteNA => 'Probabilities not available';

  @override
  String get tileGoalsNA => 'Insufficient history';

  @override
  String get tileGoalsTrend => 'Goals trend';

  @override
  String get tileOver25Model => 'Over 2.5 according to the model';

  @override
  String get tileOver25Recent => 'Over 2.5 in their recent matches';

  @override
  String get tileProbability => 'Probability';

  @override
  String get tileXg => 'Projected xG';

  @override
  String tileXgCaption(String home, String away) {
    return '$home home · $away away';
  }

  @override
  String get tileXgNA => 'Available in goals markets';

  @override
  String get titleAsianHandicap => 'Asian handicap';

  @override
  String get titleDrawNoBet => 'Draw no bet';

  @override
  String titleTeamGoals(String team) {
    return '$team goals';
  }

  @override
  String get titleTotalCards => 'Total cards';

  @override
  String get titleTotalCorners => 'Total corners';

  @override
  String get titleTotalGoals => 'Total goals';

  @override
  String get titleWinner => 'Match winner';

  @override
  String get tooltipVip => 'VIP';

  @override
  String get updateLater => 'Later';

  @override
  String get updateNow => 'Update now';

  @override
  String get updateOptional => 'A new version of QuantFut is available.';

  @override
  String get updateRequired => 'Update QuantFut to continue.';

  @override
  String get updateStoreError => 'Could not open the store. Please try again.';

  @override
  String get updateTitle => 'Update available';

  @override
  String get vipAccessButton => 'VIP access';

  @override
  String get vipActivate => 'Activate VIP access';

  @override
  String get vipActive => 'Your VIP access is active.';

  @override
  String get vipBadge => '✦  VIP ACCESS';

  @override
  String get vipBenefit1Body => 'Every prediction is sealed before the match';

  @override
  String get vipBenefit1Title => 'Verifiable history';

  @override
  String vipBenefit2Body(int min, int max) {
    return 'All picks from $min to $max%, no free quota';
  }

  @override
  String get vipBenefit2Title => 'Full High Probability';

  @override
  String get vipBenefit3Body => 'All pending steps, not just one';

  @override
  String get vipBenefit3Title => 'Full Ladder Challenge';

  @override
  String get vipBenefit4Body =>
      'Published odds, probability and xG for every pick';

  @override
  String get vipBenefit4Title => 'Odds and match analysis';

  @override
  String get vipBestPrice => '★ BEST PRICE';

  @override
  String get vipCheckAccess => 'Check my access';

  @override
  String get vipCheckSignIn => 'Sign in from Profile to check your access.';

  @override
  String vipDays(int days) {
    String _temp0 = intl.Intl.pluralLogic(
      days,
      locale: localeName,
      other: '$days days',
      one: '$days day',
    );
    return '$_temp0';
  }

  @override
  String get vipFreeAccess => 'Your account has free access.';

  @override
  String get vipGranted => 'Done! Your VIP access is active.';

  @override
  String get vipHistoryNote =>
      'Public, sealed history; samples per market are small and a prediction can fail.';

  @override
  String get vipIntro =>
      'All High Probability and Ladder Challenge predictions while your subscription is active.';

  @override
  String get vipLinked => '🔒  Your VIP access is linked to your account';

  @override
  String get vipManage =>
      'You already have Plus. Change or cancel your plan in the store.';

  @override
  String vipMonthly(String amount) {
    return '≈ $amount/month';
  }

  @override
  String vipMonths(int months) {
    String _temp0 = intl.Intl.pluralLogic(
      months,
      locale: localeName,
      other: '$months months',
      one: '$months month',
    );
    return '$_temp0';
  }

  @override
  String get vipNoExpiry => 'No expiry';

  @override
  String get vipPaymentRequired =>
      'Subscribing requires a configured payment channel.';

  @override
  String get vipPending =>
      'Payment pending. You will get access as soon as the store confirms it.';

  @override
  String get vipPickLabel => 'VIP prediction';

  @override
  String get vipPlansSoon => 'Plans will be shown when they are available.';

  @override
  String get vipPricesNote => 'Prices from the server catalog.';

  @override
  String get vipPurchasesPending =>
      'Purchases in preparation: nothing is charged from the app yet.';

  @override
  String get vipRestore => 'Restore purchases';

  @override
  String get vipStatRecorded => 'Recorded hit rate';

  @override
  String get vipStatResolved => 'Resolved';

  @override
  String get vipStoreFailed =>
      'The purchase could not be confirmed. We will retry when you reopen the app.';

  @override
  String get vipStoreTerms =>
      'Renews automatically at the same price until you cancel it in the store.';

  @override
  String get vipStoreUnavailable =>
      'The store is not available on this device.';

  @override
  String get vipSubscribe => 'Subscribe';

  @override
  String get vipVerifying => 'Verifying the purchase with the store…';

  @override
  String get welcome1Body =>
      'Discover the statistical side of sport: matches, analysis and predictions from the project you already know on the web.';

  @override
  String get welcome1Title => 'Football and NBA,\nfrom a new angle';

  @override
  String get welcome2Body =>
      'Recent form, head-to-head and statistics help you understand what might happen. Start with the data.';

  @override
  String get welcome2Title => 'Every match,\nwith more context';

  @override
  String get welcome3Body =>
      'Goals, corners, handicap and NBA statistics. Learn what each analysis measures before interpreting a selection.';

  @override
  String get welcome3Title => 'More markets.\nMore information.';

  @override
  String get welcome4Body =>
      'A prediction can also be understood after the match. The history lets you compare estimates with results.';

  @override
  String get welcome4Title => 'Results,\nat a glance';

  @override
  String get welcome5Body =>
      'A probability is not a certainty. Explore the content, review the context and form your own judgment.';

  @override
  String get welcome5Title => 'It all starts\nwith being informed';

  @override
  String welcomeGoTo(int number) {
    return 'Go to welcome screen $number';
  }

  @override
  String get welcomeNext => 'Next';

  @override
  String welcomeScreenOf(int page, int total) {
    return 'Screen $page of $total';
  }

  @override
  String get welcomeSkip => 'Skip';

  @override
  String get welcomeStart => 'Get started';
}
