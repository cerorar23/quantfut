import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_de.dart';
import 'app_localizations_en.dart';
import 'app_localizations_es.dart';
import 'app_localizations_fr.dart';
import 'app_localizations_it.dart';
import 'app_localizations_pt.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('de'),
    Locale('en'),
    Locale('es'),
    Locale('fr'),
    Locale('it'),
    Locale('pt'),
  ];

  /// Texto de la diapositiva 1.
  ///
  /// In es, this message translates to:
  /// **'Un modelo estadístico calcula las probabilidades. Una probabilidad no es una certeza.'**
  String get accessBody1;

  /// Texto de la diapositiva 2.
  ///
  /// In es, this message translates to:
  /// **'Cada día, los de mayor probabilidad, con su acierto histórico real.'**
  String get accessBody2;

  /// Texto de la diapositiva 3.
  ///
  /// In es, this message translates to:
  /// **'Sigue el avance de cada reto y cuánto falta para completarlo.'**
  String get accessBody3;

  /// Texto de la diapositiva 4.
  ///
  /// In es, this message translates to:
  /// **'Con su cuota y su probabilidad conjunta, para que sepas qué arriesgas.'**
  String get accessBody4;

  /// Texto de la diapositiva 5.
  ///
  /// In es, this message translates to:
  /// **'Marca asistencia, completa ofertas e invita amigos para desbloquear pronósticos.'**
  String get accessBody5;

  /// Texto de la tarjeta de acceso.
  ///
  /// In es, this message translates to:
  /// **'Guarda tu progreso y tus monedas en todos tus dispositivos.'**
  String get accessCardBody;

  /// Título de la tarjeta de acceso.
  ///
  /// In es, this message translates to:
  /// **'Inicia sesión para continuar'**
  String get accessCardTitle;

  /// No description provided for @accessConsent.
  ///
  /// In es, this message translates to:
  /// **'Tengo al menos 18 años y acepto los términos y la política de privacidad.'**
  String get accessConsent;

  /// No description provided for @accessConsentRequired.
  ///
  /// In es, this message translates to:
  /// **'Marca la casilla para continuar con Google.'**
  String get accessConsentRequired;

  /// Consentimiento con los dos enlaces legales dentro de la frase.
  ///
  /// In es, this message translates to:
  /// **'Tengo 18 años o más y acepto los {terms} y la {privacy}.'**
  String accessConsentRich(String terms, String privacy);

  /// No description provided for @accessContinueWithGoogle.
  ///
  /// In es, this message translates to:
  /// **'Continuar con Google'**
  String get accessContinueWithGoogle;

  /// Aviso legal bajo la tarjeta de acceso.
  ///
  /// In es, this message translates to:
  /// **'Solo con fines informativos y de entretenimiento. Los pronósticos no garantizan resultados.'**
  String get accessDisclaimer;

  /// No description provided for @accessDocumentOpenError.
  ///
  /// In es, this message translates to:
  /// **'No se pudo abrir el documento.'**
  String get accessDocumentOpenError;

  /// No description provided for @accessForgotLink.
  ///
  /// In es, this message translates to:
  /// **'Recuperar contraseña anterior'**
  String get accessForgotLink;

  /// No description provided for @accessForgotSent.
  ///
  /// In es, this message translates to:
  /// **'Si existe la cuenta, recibirás instrucciones por correo.'**
  String get accessForgotSent;

  /// No description provided for @accessFreeToStart.
  ///
  /// In es, this message translates to:
  /// **'GRATIS PARA EMPEZAR'**
  String get accessFreeToStart;

  /// No description provided for @accessGenericError.
  ///
  /// In es, this message translates to:
  /// **'No se pudo completar el acceso. Inténtalo de nuevo.'**
  String get accessGenericError;

  /// No description provided for @accessGoogleError.
  ///
  /// In es, this message translates to:
  /// **'No se pudo acceder con Google. Inténtalo de nuevo.'**
  String get accessGoogleError;

  /// Etiqueta de la diapositiva 1 de la pantalla de acceso.
  ///
  /// In es, this message translates to:
  /// **'PROBABILIDADES REALES'**
  String get accessKicker1;

  /// Etiqueta de la diapositiva 2.
  ///
  /// In es, this message translates to:
  /// **'ALTA PROBABILIDAD'**
  String get accessKicker2;

  /// Etiqueta de la diapositiva 3.
  ///
  /// In es, this message translates to:
  /// **'RETO ESCALERA'**
  String get accessKicker3;

  /// Etiqueta de la diapositiva 4.
  ///
  /// In es, this message translates to:
  /// **'PARLEY'**
  String get accessKicker4;

  /// Etiqueta de la diapositiva 5.
  ///
  /// In es, this message translates to:
  /// **'COINS'**
  String get accessKicker5;

  /// No description provided for @accessLinkButton.
  ///
  /// In es, this message translates to:
  /// **'Vincular mi cuenta'**
  String get accessLinkButton;

  /// No description provided for @accessLinkEmail.
  ///
  /// In es, this message translates to:
  /// **'Correo de tu cuenta anterior'**
  String get accessLinkEmail;

  /// No description provided for @accessLinkIntro.
  ///
  /// In es, this message translates to:
  /// **'Vincula tu cuenta anterior para conservar saldo y acceso.'**
  String get accessLinkIntro;

  /// No description provided for @accessLinkPassword.
  ///
  /// In es, this message translates to:
  /// **'Contraseña anterior'**
  String get accessLinkPassword;

  /// No description provided for @accessNoCard.
  ///
  /// In es, this message translates to:
  /// **'SIN TARJETA'**
  String get accessNoCard;

  /// No description provided for @accessOtherAccount.
  ///
  /// In es, this message translates to:
  /// **'Usar otra cuenta'**
  String get accessOtherAccount;

  /// No description provided for @accessPreparingDocs.
  ///
  /// In es, this message translates to:
  /// **'Estamos preparando los documentos de acceso.'**
  String get accessPreparingDocs;

  /// No description provided for @accessPrivacy.
  ///
  /// In es, this message translates to:
  /// **'Política de privacidad'**
  String get accessPrivacy;

  /// No description provided for @accessRetry.
  ///
  /// In es, this message translates to:
  /// **'Reintentar acceso'**
  String get accessRetry;

  /// No description provided for @accessTagline.
  ///
  /// In es, this message translates to:
  /// **'Partidos, análisis e historial. Una probabilidad no es una certeza.'**
  String get accessTagline;

  /// No description provided for @accessTerms.
  ///
  /// In es, this message translates to:
  /// **'Términos de uso'**
  String get accessTerms;

  /// Título de la diapositiva 1.
  ///
  /// In es, this message translates to:
  /// **'Entiende cada partido con datos.'**
  String get accessTitle1;

  /// Título de la diapositiva 2.
  ///
  /// In es, this message translates to:
  /// **'Pronósticos con su acierto a la vista.'**
  String get accessTitle2;

  /// Título de la diapositiva 3.
  ///
  /// In es, this message translates to:
  /// **'Sube escalón a escalón.'**
  String get accessTitle3;

  /// Título de la diapositiva 4.
  ///
  /// In es, this message translates to:
  /// **'Un boleto sellado antes de los partidos.'**
  String get accessTitle4;

  /// Título de la diapositiva 5.
  ///
  /// In es, this message translates to:
  /// **'Gana monedas y desbloquea.'**
  String get accessTitle5;

  /// Título de la tarjeta de anuncios con recompensa en Coins.
  ///
  /// In es, this message translates to:
  /// **'Videos con recompensa'**
  String get adsCardTitle;

  /// Aviso bajo el botón; describe la condición de la recompensa.
  ///
  /// In es, this message translates to:
  /// **'Las monedas se acreditan al terminar el video. Si lo cierras antes, no recibes monedas.'**
  String get adsFootnote;

  /// Se ha usado el máximo diario de videos.
  ///
  /// In es, this message translates to:
  /// **'Límite de hoy alcanzado. Vuelve después de las 00:00 UTC.'**
  String get adsLimitReached;

  /// Estado mientras se pide el ticket y se carga el anuncio.
  ///
  /// In es, this message translates to:
  /// **'Cargando video…'**
  String get adsLoading;

  /// El saldo aún no subió tras 10 s; la confirmación puede tardar.
  ///
  /// In es, this message translates to:
  /// **'Tus monedas llegarán en unos instantes.'**
  String get adsPending;

  /// Videos vistos hoy sobre el máximo diario.
  ///
  /// In es, this message translates to:
  /// **'Hoy: {used} de {cap}'**
  String adsProgress(int used, int cap);

  /// El anuncio no cargó o está desactivado en este dispositivo.
  ///
  /// In es, this message translates to:
  /// **'No hay videos disponibles ahora. Inténtalo más tarde.'**
  String get adsUnavailable;

  /// Estado tras ver el video, mientras el servidor confirma.
  ///
  /// In es, this message translates to:
  /// **'Verificando tu recompensa…'**
  String get adsVerifying;

  /// Pausa entre videos con cuenta atrás.
  ///
  /// In es, this message translates to:
  /// **'Siguiente video en {time}'**
  String adsWaitFor(String time);

  /// Botón que pide ver un video completo; dice la acción y la recompensa.
  ///
  /// In es, this message translates to:
  /// **'Ver video · +{coins} monedas'**
  String adsWatchCta(int coins);

  /// Subtítulo: de qué equipo son las bajas de la sección.
  ///
  /// In es, this message translates to:
  /// **'Bajas de {team}'**
  String alertsAbsencesOf(String team);

  /// Sección: bajas del rival, que benefician a este equipo.
  ///
  /// In es, this message translates to:
  /// **'Ventaja'**
  String get alertsAdvantage;

  /// El rival no tiene bajas reportadas.
  ///
  /// In es, this message translates to:
  /// **'Sin ventajas reportadas.'**
  String get alertsAdvantageEmpty;

  /// Player back in group training
  ///
  /// In es, this message translates to:
  /// **'Ya entrena con el grupo'**
  String get alertsBackTrainingDesc;

  /// Badge for applied injury report
  ///
  /// In es, this message translates to:
  /// **'APLICADO'**
  String get alertsBadgeApplied;

  /// Badge for doubtful player
  ///
  /// In es, this message translates to:
  /// **'DUDA'**
  String get alertsBadgeDoubt;

  /// Badge for player on international duty
  ///
  /// In es, this message translates to:
  /// **'SELECCIÓN'**
  String get alertsBadgeDuty;

  /// Badge for injured player absence
  ///
  /// In es, this message translates to:
  /// **'LESIÓN'**
  String get alertsBadgeInjury;

  /// Badge when there are no alerts
  ///
  /// In es, this message translates to:
  /// **'SIN ALERTAS'**
  String get alertsBadgeNone;

  /// Badge for pending injury report
  ///
  /// In es, this message translates to:
  /// **'PENDIENTE'**
  String get alertsBadgePending;

  /// Badge for player returning/back in training
  ///
  /// In es, this message translates to:
  /// **'VUELVE'**
  String get alertsBadgeReturns;

  /// Badge for suspended player
  ///
  /// In es, this message translates to:
  /// **'SANCIÓN'**
  String get alertsBadgeSuspension;

  /// Cuándo se comprobaron las bajas por última vez.
  ///
  /// In es, this message translates to:
  /// **'Comprobado {when}'**
  String alertsChecked(String when);

  /// Footer for alerts checking timestamp
  ///
  /// In es, this message translates to:
  /// **'COMPROBADO {when} · se actualiza cada hora'**
  String alertsCheckedFooter(String when);

  /// Sección: bajas de este equipo.
  ///
  /// In es, this message translates to:
  /// **'Desventaja'**
  String get alertsDisadvantage;

  /// Este equipo no tiene bajas reportadas.
  ///
  /// In es, this message translates to:
  /// **'Sin desventajas reportadas.'**
  String get alertsDisadvantageEmpty;

  /// Estado de un jugador con duda.
  ///
  /// In es, this message translates to:
  /// **'Duda'**
  String get alertsDoubt;

  /// Description for international duty with return date
  ///
  /// In es, this message translates to:
  /// **'Con su selección · vuelve a {when}'**
  String alertsDutyReturns(String when);

  /// Early in month
  ///
  /// In es, this message translates to:
  /// **'principios de {month}'**
  String alertsEarlyMonth(String month);

  /// Subtitle for last starting XI
  ///
  /// In es, this message translates to:
  /// **'último once, vs {rival} · {date}'**
  String alertsLastElevenVs(String rival, String date);

  /// Late in month
  ///
  /// In es, this message translates to:
  /// **'finales de {month}'**
  String alertsLateMonth(String month);

  /// Kicker above lineups pitch
  ///
  /// In es, this message translates to:
  /// **'// ALINEACIONES'**
  String get alertsLineupsKicker;

  /// Title for pitch lineups
  ///
  /// In es, this message translates to:
  /// **'ÚLTIMO ONCE CONOCIDO'**
  String get alertsLineupsTitle;

  /// Mid month
  ///
  /// In es, this message translates to:
  /// **'mediados de {month}'**
  String alertsMidMonth(String month);

  /// NBA team injury report summary
  ///
  /// In es, this message translates to:
  /// **'{count, plural, one{1 jugador en el reporte} other{{count} jugadores en el reporte}} · {minutes} min de bajas'**
  String alertsNbaReportSummary(num count, num minutes);

  /// Body when match has no alerts
  ///
  /// In es, this message translates to:
  /// **'No hay bajas ni dudas registradas para este partido.'**
  String get alertsNoAlertsBody;

  /// Title when match has no alerts
  ///
  /// In es, this message translates to:
  /// **'SIN ALERTAS'**
  String get alertsNoAlertsTitle;

  /// No hay comprobación de bajas: no equivale a «sin lesionados».
  ///
  /// In es, this message translates to:
  /// **'Todavía no hay una comprobación de bajas para este partido. Si su liga no tiene este dato, eso no significa que no haya lesionados.'**
  String get alertsNoCheck;

  /// Description when lineup is not yet confirmed
  ///
  /// In es, this message translates to:
  /// **'El once se confirma una hora antes del partido y aparecerá aquí con foto.'**
  String get alertsNoLineupDesc;

  /// Header when team has no saved lineup
  ///
  /// In es, this message translates to:
  /// **'{team} · sin alineación guardada'**
  String alertsNoLineupSaved(String team);

  /// Aviso al pie de la pestaña de alertas.
  ///
  /// In es, this message translates to:
  /// **'Las bajas pueden cambiar hasta el inicio. El once oficial se publica poco antes del partido.'**
  String get alertsNote;

  /// Estado de un jugador que no jugará.
  ///
  /// In es, this message translates to:
  /// **'No disponible'**
  String get alertsOut;

  /// Motivo de la baja.
  ///
  /// In es, this message translates to:
  /// **'Lesión de tobillo o pie'**
  String get alertsReasonFoot;

  /// Motivo de la baja.
  ///
  /// In es, this message translates to:
  /// **'Enfermedad'**
  String get alertsReasonIllness;

  /// Motivo de la baja cuando el proveedor no precisa más.
  ///
  /// In es, this message translates to:
  /// **'Lesión'**
  String get alertsReasonInjury;

  /// Motivo de la baja.
  ///
  /// In es, this message translates to:
  /// **'Lesión de rodilla'**
  String get alertsReasonKnee;

  /// Motivo de la baja.
  ///
  /// In es, this message translates to:
  /// **'Golpe'**
  String get alertsReasonKnock;

  /// Motivo de la baja.
  ///
  /// In es, this message translates to:
  /// **'Lesión muscular'**
  String get alertsReasonMuscle;

  /// Motivo de la baja.
  ///
  /// In es, this message translates to:
  /// **'Sanción'**
  String get alertsReasonSuspension;

  /// El proveedor no indica el motivo.
  ///
  /// In es, this message translates to:
  /// **'Motivo no indicado'**
  String get alertsReasonUnknown;

  /// Return date formatted
  ///
  /// In es, this message translates to:
  /// **'Vuelve a {when}'**
  String alertsReturnsWhen(String when);

  /// Proveedor de los datos de bajas.
  ///
  /// In es, this message translates to:
  /// **'Fuente: API-Football'**
  String get alertsSource;

  /// Resumen de bajas y dudas del partido.
  ///
  /// In es, this message translates to:
  /// **'{out, plural, one{1 baja} other{{out} bajas}} · {doubt, plural, one{1 duda} other{{doubt} dudas}}'**
  String alertsSummary(int out, int doubt);

  /// Estado de un jugador sancionado.
  ///
  /// In es, this message translates to:
  /// **'Sancionado'**
  String get alertsSuspended;

  /// Tennis player without issues
  ///
  /// In es, this message translates to:
  /// **'Sin incidencias en los últimos 7 días'**
  String get alertsTennisNoIssues;

  /// No description provided for @anAveragesLast10.
  ///
  /// In es, this message translates to:
  /// **'// Promedios · Últimos 10'**
  String get anAveragesLast10;

  /// No description provided for @anBttsShort.
  ///
  /// In es, this message translates to:
  /// **'AMBOS MARCAN'**
  String get anBttsShort;

  /// No description provided for @anDrawsCount.
  ///
  /// In es, this message translates to:
  /// **'{count} EMPATES'**
  String anDrawsCount(int count);

  /// No description provided for @anGoalsDiff.
  ///
  /// In es, this message translates to:
  /// **'{gf} GF · {gc} GC'**
  String anGoalsDiff(int gf, int gc);

  /// No description provided for @anGoalsPerMatchShort.
  ///
  /// In es, this message translates to:
  /// **'GOLES / PARTIDO'**
  String get anGoalsPerMatchShort;

  /// No description provided for @anH2hMatchCount.
  ///
  /// In es, this message translates to:
  /// **'// {n} PARTIDOS'**
  String anH2hMatchCount(int n);

  /// No description provided for @anHowTheyArrive.
  ///
  /// In es, this message translates to:
  /// **'Cómo llegan'**
  String get anHowTheyArrive;

  /// No description provided for @anLast5Matches.
  ///
  /// In es, this message translates to:
  /// **'// ÚLTIMOS 5 PARTIDOS'**
  String get anLast5Matches;

  /// No description provided for @anLastMatch.
  ///
  /// In es, this message translates to:
  /// **'ÚLTIMO'**
  String get anLastMatch;

  /// No description provided for @anLeagueRound.
  ///
  /// In es, this message translates to:
  /// **'// {league} · JORNADA {round}'**
  String anLeagueRound(String league, String round);

  /// No description provided for @anMetricBtts.
  ///
  /// In es, this message translates to:
  /// **'AMBOS MARCAN'**
  String get anMetricBtts;

  /// No description provided for @anMetricCleanSheet.
  ///
  /// In es, this message translates to:
  /// **'PORTERÍA A CERO'**
  String get anMetricCleanSheet;

  /// No description provided for @anMetricCorners.
  ///
  /// In es, this message translates to:
  /// **'CÓRNERS'**
  String get anMetricCorners;

  /// No description provided for @anMetricGoalsAgainst.
  ///
  /// In es, this message translates to:
  /// **'GOLES EN CONTRA'**
  String get anMetricGoalsAgainst;

  /// No description provided for @anMetricGoalsFor.
  ///
  /// In es, this message translates to:
  /// **'GOLES A FAVOR'**
  String get anMetricGoalsFor;

  /// No description provided for @anMetricOver25.
  ///
  /// In es, this message translates to:
  /// **'MÁS DE 2,5 GOLES'**
  String get anMetricOver25;

  /// No description provided for @anMetricShots.
  ///
  /// In es, this message translates to:
  /// **'TIROS'**
  String get anMetricShots;

  /// No description provided for @anMetricShotsOnTarget.
  ///
  /// In es, this message translates to:
  /// **'TIROS A PUERTA'**
  String get anMetricShotsOnTarget;

  /// No description provided for @anMetricXgAgainst.
  ///
  /// In es, this message translates to:
  /// **'xG EN CONTRA'**
  String get anMetricXgAgainst;

  /// No description provided for @anMetricXgFor.
  ///
  /// In es, this message translates to:
  /// **'xG A FAVOR'**
  String get anMetricXgFor;

  /// No description provided for @anNavForm.
  ///
  /// In es, this message translates to:
  /// **'Forma'**
  String get anNavForm;

  /// No description provided for @anNavH2h.
  ///
  /// In es, this message translates to:
  /// **'Cara a cara'**
  String get anNavH2h;

  /// No description provided for @anNavStandings.
  ///
  /// In es, this message translates to:
  /// **'Tabla'**
  String get anNavStandings;

  /// No description provided for @anNavSummary.
  ///
  /// In es, this message translates to:
  /// **'Resumen'**
  String get anNavSummary;

  /// No description provided for @anNoForm.
  ///
  /// In es, this message translates to:
  /// **'Forma no disponible'**
  String get anNoForm;

  /// No description provided for @anNoH2h.
  ///
  /// In es, this message translates to:
  /// **'Sin enfrentamientos previos registrados'**
  String get anNoH2h;

  /// No description provided for @anNoStandings.
  ///
  /// In es, this message translates to:
  /// **'Clasificación no disponible'**
  String get anNoStandings;

  /// No description provided for @anOver25Short.
  ///
  /// In es, this message translates to:
  /// **'MÁS DE 2,5'**
  String get anOver25Short;

  /// No description provided for @anPlayoff.
  ///
  /// In es, this message translates to:
  /// **'PLAY-OFF'**
  String get anPlayoff;

  /// No description provided for @anPointsOutOf.
  ///
  /// In es, this message translates to:
  /// **'{points} PTS DE 15'**
  String anPointsOutOf(int points);

  /// No description provided for @anPromotion.
  ///
  /// In es, this message translates to:
  /// **'ASCENSO'**
  String get anPromotion;

  /// No description provided for @anRadarAttack.
  ///
  /// In es, this message translates to:
  /// **'ATAQUE'**
  String get anRadarAttack;

  /// No description provided for @anRadarCorners.
  ///
  /// In es, this message translates to:
  /// **'CÓRNERS'**
  String get anRadarCorners;

  /// No description provided for @anRadarCreation.
  ///
  /// In es, this message translates to:
  /// **'CREACIÓN'**
  String get anRadarCreation;

  /// No description provided for @anRadarDefense.
  ///
  /// In es, this message translates to:
  /// **'DEFENSA'**
  String get anRadarDefense;

  /// No description provided for @anRadarFinishing.
  ///
  /// In es, this message translates to:
  /// **'REMATE'**
  String get anRadarFinishing;

  /// No description provided for @anRelegation.
  ///
  /// In es, this message translates to:
  /// **'DESCENSO'**
  String get anRelegation;

  /// No description provided for @anScopeAll.
  ///
  /// In es, this message translates to:
  /// **'TODOS'**
  String get anScopeAll;

  /// No description provided for @anScopeHomeAway.
  ///
  /// In es, this message translates to:
  /// **'CASA · FUERA'**
  String get anScopeHomeAway;

  /// No description provided for @anScopeHomeAwayCaption.
  ///
  /// In es, this message translates to:
  /// **'EN CASA · FUERA'**
  String get anScopeHomeAwayCaption;

  /// No description provided for @anScopeLast10Caption.
  ///
  /// In es, this message translates to:
  /// **'ÚLTIMOS 10 · 10'**
  String get anScopeLast10Caption;

  /// No description provided for @anSeenFrom.
  ///
  /// In es, this message translates to:
  /// **'Visto desde {team}'**
  String anSeenFrom(String team);

  /// No description provided for @anStandingsCalloutAhead.
  ///
  /// In es, this message translates to:
  /// **'{teamA} {posA}.º · {ptsA} pts · +{diff} sobre {teamB} ({posB}.º, {ptsB} pts)'**
  String anStandingsCalloutAhead(
    String teamA,
    int posA,
    int ptsA,
    int diff,
    String teamB,
    int posB,
    int ptsB,
  );

  /// No description provided for @anStandingsCalloutTied.
  ///
  /// In es, this message translates to:
  /// **'{teamA} y {teamB} empatados a {pts} pts'**
  String anStandingsCalloutTied(String teamA, String teamB, int pts);

  /// No description provided for @anStandingsTitle.
  ///
  /// In es, this message translates to:
  /// **'Clasificación'**
  String get anStandingsTitle;

  /// No description provided for @anStreakLosses.
  ///
  /// In es, this message translates to:
  /// **'{count, plural, one{1 DERROTA} other{{count} DERROTAS SEGUIDAS}}'**
  String anStreakLosses(int count);

  /// No description provided for @anStreakUnbeaten.
  ///
  /// In es, this message translates to:
  /// **'{count} SIN PERDER'**
  String anStreakUnbeaten(int count);

  /// No description provided for @anStreakWins.
  ///
  /// In es, this message translates to:
  /// **'{count, plural, one{1 VICTORIA} other{{count} VICTORIAS SEGUIDAS}}'**
  String anStreakWins(int count);

  /// No description provided for @anVenueAway.
  ///
  /// In es, this message translates to:
  /// **'FUERA'**
  String get anVenueAway;

  /// No description provided for @anVenueHome.
  ///
  /// In es, this message translates to:
  /// **'CASA'**
  String get anVenueHome;

  /// No description provided for @anViewAllMatches.
  ///
  /// In es, this message translates to:
  /// **'VER LOS {n} PARTIDOS'**
  String anViewAllMatches(int n);

  /// No description provided for @anWinsTeam.
  ///
  /// In es, this message translates to:
  /// **'{count} VICTORIAS {team}'**
  String anWinsTeam(int count, String team);

  /// No description provided for @apiGoogleNotVerified.
  ///
  /// In es, this message translates to:
  /// **'Google no pudo verificar el acceso.'**
  String get apiGoogleNotVerified;

  /// No description provided for @apiInvalidResponse.
  ///
  /// In es, this message translates to:
  /// **'Respuesta no válida del servidor.'**
  String get apiInvalidResponse;

  /// No description provided for @apiInvalidSession.
  ///
  /// In es, this message translates to:
  /// **'Sesión no válida.'**
  String get apiInvalidSession;

  /// No description provided for @apiLoadFailed.
  ///
  /// In es, this message translates to:
  /// **'No se pudo cargar la información (HTTP {status}).'**
  String apiLoadFailed(int status);

  /// No description provided for @apiOffline.
  ///
  /// In es, this message translates to:
  /// **'No se pudo conectar. Comprueba tu conexión e inténtalo de nuevo.'**
  String get apiOffline;

  /// No description provided for @apiSessionExpired.
  ///
  /// In es, this message translates to:
  /// **'Inicia sesión de nuevo.'**
  String get apiSessionExpired;

  /// No description provided for @apiSignInWithGoogle.
  ///
  /// In es, this message translates to:
  /// **'Inicia sesión con Google.'**
  String get apiSignInWithGoogle;

  /// No description provided for @artAnalyzeEach.
  ///
  /// In es, this message translates to:
  /// **'ANALIZA CADA SELECCIÓN'**
  String get artAnalyzeEach;

  /// No description provided for @artCorners.
  ///
  /// In es, this message translates to:
  /// **'CÓRNERS'**
  String get artCorners;

  /// No description provided for @artFootball.
  ///
  /// In es, this message translates to:
  /// **'FÚTBOL'**
  String get artFootball;

  /// No description provided for @artForm.
  ///
  /// In es, this message translates to:
  /// **'FORMA'**
  String get artForm;

  /// No description provided for @artGoals.
  ///
  /// In es, this message translates to:
  /// **'GOLES'**
  String get artGoals;

  /// No description provided for @artHeadToHead.
  ///
  /// In es, this message translates to:
  /// **'CARA A CARA'**
  String get artHeadToHead;

  /// Texto dibujado en la ilustración de bienvenida (mayúsculas)
  ///
  /// In es, this message translates to:
  /// **'FÚTBOL + NBA'**
  String get artHeading0;

  /// No description provided for @artHeading1.
  ///
  /// In es, this message translates to:
  /// **'EL CONTEXTO IMPORTA'**
  String get artHeading1;

  /// No description provided for @artHeading2.
  ///
  /// In es, this message translates to:
  /// **'EXPLORA LOS MERCADOS'**
  String get artHeading2;

  /// No description provided for @artHeading3.
  ///
  /// In es, this message translates to:
  /// **'HISTORIAL A LA VISTA'**
  String get artHeading3;

  /// No description provided for @artHeading4.
  ///
  /// In es, this message translates to:
  /// **'DATOS + TU CRITERIO'**
  String get artHeading4;

  /// No description provided for @artLost.
  ///
  /// In es, this message translates to:
  /// **'FALLADO'**
  String get artLost;

  /// No description provided for @artNba.
  ///
  /// In es, this message translates to:
  /// **'NBA'**
  String get artNba;

  /// No description provided for @artNotCertainty.
  ///
  /// In es, this message translates to:
  /// **'NO ES UNA CERTEZA'**
  String get artNotCertainty;

  /// No description provided for @artProbability.
  ///
  /// In es, this message translates to:
  /// **'PROBABILIDAD'**
  String get artProbability;

  /// No description provided for @artRegisteredRate.
  ///
  /// In es, this message translates to:
  /// **'ACIERTO REGISTRADO'**
  String get artRegisteredRate;

  /// No description provided for @artStats.
  ///
  /// In es, this message translates to:
  /// **'ESTADÍSTICAS'**
  String get artStats;

  /// No description provided for @artTagline.
  ///
  /// In es, this message translates to:
  /// **'ANALIZA. COMPARA. EXPLORA.'**
  String get artTagline;

  /// No description provided for @artTennis.
  ///
  /// In es, this message translates to:
  /// **'TENIS'**
  String get artTennis;

  /// No description provided for @artTransparency.
  ///
  /// In es, this message translates to:
  /// **'TRANSPARENCIA'**
  String get artTransparency;

  /// No description provided for @artWon.
  ///
  /// In es, this message translates to:
  /// **'GANADO'**
  String get artWon;

  /// No description provided for @bannerAwaiting.
  ///
  /// In es, this message translates to:
  /// **'PARTIDO JUGADO · esperando el resultado oficial'**
  String get bannerAwaiting;

  /// No description provided for @bannerLive.
  ///
  /// In es, this message translates to:
  /// **'PARTIDO EN JUEGO · pronóstico sellado antes del inicio'**
  String get bannerLive;

  /// No description provided for @bannerLost.
  ///
  /// In es, this message translates to:
  /// **'FALLADO{score} · pronóstico sellado antes del inicio'**
  String bannerLost(String score);

  /// No description provided for @bannerWon.
  ///
  /// In es, this message translates to:
  /// **'ACERTADO{score} · pronóstico sellado antes del inicio'**
  String bannerWon(String score);

  /// No description provided for @calendarEmpty.
  ///
  /// In es, this message translates to:
  /// **'No hay enfrentamientos para estos filtros.'**
  String get calendarEmpty;

  /// No description provided for @calendarMatchesCount.
  ///
  /// In es, this message translates to:
  /// **'{count, plural, one{{count} enfrentamiento} other{{count} enfrentamientos}}'**
  String calendarMatchesCount(int count);

  /// No description provided for @calendarPickDate.
  ///
  /// In es, this message translates to:
  /// **'Elegir fecha'**
  String get calendarPickDate;

  /// No description provided for @calendarSearchHint.
  ///
  /// In es, this message translates to:
  /// **'Busca equipos o ligas'**
  String get calendarSearchHint;

  /// No description provided for @calendarTitle.
  ///
  /// In es, this message translates to:
  /// **'Calendario · hora local'**
  String get calendarTitle;

  /// No description provided for @casesCount.
  ///
  /// In es, this message translates to:
  /// **'{count, plural, one{{formatted} caso} other{{formatted} casos}}'**
  String casesCount(int count, String formatted);

  /// No description provided for @commonAll.
  ///
  /// In es, this message translates to:
  /// **'Todos'**
  String get commonAll;

  /// No description provided for @commonAway.
  ///
  /// In es, this message translates to:
  /// **'Visitante'**
  String get commonAway;

  /// No description provided for @commonCancel.
  ///
  /// In es, this message translates to:
  /// **'Cancelar'**
  String get commonCancel;

  /// No description provided for @commonClose.
  ///
  /// In es, this message translates to:
  /// **'Cerrar'**
  String get commonClose;

  /// No description provided for @commonConfirm.
  ///
  /// In es, this message translates to:
  /// **'Confirmar'**
  String get commonConfirm;

  /// No description provided for @commonConnecting.
  ///
  /// In es, this message translates to:
  /// **'Conectando…'**
  String get commonConnecting;

  /// No description provided for @commonDraw.
  ///
  /// In es, this message translates to:
  /// **'Empate'**
  String get commonDraw;

  /// No description provided for @commonHome.
  ///
  /// In es, this message translates to:
  /// **'Local'**
  String get commonHome;

  /// No description provided for @commonRefresh.
  ///
  /// In es, this message translates to:
  /// **'Actualizar'**
  String get commonRefresh;

  /// No description provided for @commonRetry.
  ///
  /// In es, this message translates to:
  /// **'Reintentar'**
  String get commonRetry;

  /// No description provided for @commonSeeVip.
  ///
  /// In es, this message translates to:
  /// **'Ver acceso VIP'**
  String get commonSeeVip;

  /// No description provided for @commonToday.
  ///
  /// In es, this message translates to:
  /// **'Hoy'**
  String get commonToday;

  /// No description provided for @commonYesterday.
  ///
  /// In es, this message translates to:
  /// **'Ayer'**
  String get commonYesterday;

  /// No description provided for @countdownDays.
  ///
  /// In es, this message translates to:
  /// **'{days}d {time}'**
  String countdownDays(int days, String time);

  /// No description provided for @detailChecked.
  ///
  /// In es, this message translates to:
  /// **'Comprobado: {date}'**
  String detailChecked(String date);

  /// No description provided for @detailFeaturedPickFree.
  ///
  /// In es, this message translates to:
  /// **'PICK DESTACADO · GRATIS'**
  String get detailFeaturedPickFree;

  /// No description provided for @detailFeaturedPickUnlocked.
  ///
  /// In es, this message translates to:
  /// **'PICK DESTACADO · DESBLOQUEADO'**
  String get detailFeaturedPickUnlocked;

  /// No description provided for @detailFeaturedPickVip.
  ///
  /// In es, this message translates to:
  /// **'PICK DESTACADO · VIP'**
  String get detailFeaturedPickVip;

  /// No description provided for @detailFormationPending.
  ///
  /// In es, this message translates to:
  /// **'Formación pendiente'**
  String get detailFormationPending;

  /// No description provided for @detailH2hTitle.
  ///
  /// In es, this message translates to:
  /// **'Historial directo (H2H)'**
  String get detailH2hTitle;

  /// No description provided for @detailInjuries.
  ///
  /// In es, this message translates to:
  /// **'Bajas reportadas'**
  String get detailInjuries;

  /// No description provided for @detailLineups.
  ///
  /// In es, this message translates to:
  /// **'Alineaciones'**
  String get detailLineups;

  /// No description provided for @detailLineupsPending.
  ///
  /// In es, this message translates to:
  /// **'Alineaciones todavía no confirmadas.'**
  String get detailLineupsPending;

  /// No description provided for @detailLockedWithCoinsOrVip.
  ///
  /// In es, this message translates to:
  /// **'con monedas o VIP'**
  String get detailLockedWithCoinsOrVip;

  /// No description provided for @detailModelMarkets.
  ///
  /// In es, this message translates to:
  /// **'MERCADOS DEL MODELO'**
  String get detailModelMarkets;

  /// No description provided for @detailNoFeatured.
  ///
  /// In es, this message translates to:
  /// **'Ningún pronóstico de este partido entra en el destacado (cuota de 1,20 o más y probabilidad de 75 % o más). Los abiertos están en la lista de abajo.'**
  String get detailNoFeatured;

  /// No description provided for @detailNoH2h.
  ///
  /// In es, this message translates to:
  /// **'No hay enfrentamientos registrados para este partido.'**
  String get detailNoH2h;

  /// No description provided for @detailNoInjuries.
  ///
  /// In es, this message translates to:
  /// **'Sin bajas en el reporte disponible.'**
  String get detailNoInjuries;

  /// No description provided for @detailNoInjuriesCheck.
  ///
  /// In es, this message translates to:
  /// **'No hay una comprobación de bajas disponible.'**
  String get detailNoInjuriesCheck;

  /// No description provided for @detailNoPicks.
  ///
  /// In es, this message translates to:
  /// **'No hay pronósticos publicados para este partido.'**
  String get detailNoPicks;

  /// Detalle del partido sin pronóstico sellado, con mercados del modelo abiertos debajo.
  ///
  /// In es, this message translates to:
  /// **'No hay pronóstico sellado para este partido. Abajo tienes las estimaciones del modelo.'**
  String get detailNoSealedModel;

  /// Detalle del partido sin pronóstico sellado; los mercados del modelo de debajo están con candado VIP.
  ///
  /// In es, this message translates to:
  /// **'No hay pronóstico sellado para este partido. Abajo están las estimaciones del modelo, con VIP.'**
  String get detailNoSealedModelVip;

  /// No description provided for @detailNoStarters.
  ///
  /// In es, this message translates to:
  /// **'Sin titulares confirmados.'**
  String get detailNoStarters;

  /// No description provided for @detailOddAtPublish.
  ///
  /// In es, this message translates to:
  /// **'cuota al publicar {odd}'**
  String detailOddAtPublish(String odd);

  /// No description provided for @detailReferee.
  ///
  /// In es, this message translates to:
  /// **'Árbitro'**
  String get detailReferee;

  /// No description provided for @detailRefereePending.
  ///
  /// In es, this message translates to:
  /// **'Árbitro pendiente de confirmar.'**
  String get detailRefereePending;

  /// Pestaña del análisis del partido con bajas y dudas.
  ///
  /// In es, this message translates to:
  /// **'Alertas'**
  String get detailTabAlerts;

  /// No description provided for @detailTabH2h.
  ///
  /// In es, this message translates to:
  /// **'H2H'**
  String get detailTabH2h;

  /// No description provided for @detailTabPredictions.
  ///
  /// In es, this message translates to:
  /// **'Pronósticos'**
  String get detailTabPredictions;

  /// Pestaña de props de jugador en la ficha de partido de NBA
  ///
  /// In es, this message translates to:
  /// **'Props'**
  String get detailTabProps;

  /// No description provided for @detailTabStats.
  ///
  /// In es, this message translates to:
  /// **'Análisis'**
  String get detailTabStats;

  /// Botón para desbloquear todos los pronósticos del partido
  ///
  /// In es, this message translates to:
  /// **'DESBLOQUEAR TODO · {cost}'**
  String detailUnlockAll(Object cost);

  /// No description provided for @detailVipPickNotice.
  ///
  /// In es, this message translates to:
  /// **'Este partido tiene un pronóstico VIP'**
  String get detailVipPickNotice;

  /// No description provided for @dictAwayDefault.
  ///
  /// In es, this message translates to:
  /// **'el visitante'**
  String get dictAwayDefault;

  /// No description provided for @dictHomeDefault.
  ///
  /// In es, this message translates to:
  /// **'el local'**
  String get dictHomeDefault;

  /// No description provided for @dictOddsAbove.
  ///
  /// In es, this message translates to:
  /// **'La cuota publicada supera la cuota justa ({fair}).'**
  String dictOddsAbove(String fair);

  /// No description provided for @dictOddsBelow.
  ///
  /// In es, this message translates to:
  /// **'La cuota publicada queda por debajo de la cuota justa ({fair}); el atractivo está en la probabilidad, no en el precio.'**
  String dictOddsBelow(String fair);

  /// No description provided for @dictPick.
  ///
  /// In es, this message translates to:
  /// **'{pick} con probabilidad calculada de {percent}.'**
  String dictPick(String pick, String percent);

  /// No description provided for @dictPickDefault.
  ///
  /// In es, this message translates to:
  /// **'El pronóstico'**
  String get dictPickDefault;

  /// No description provided for @dictXg.
  ///
  /// In es, this message translates to:
  /// **'Las cuotas del mercado sin margen implican {total} goles esperados ({home} {homeXg} · {away} {awayXg}).'**
  String dictXg(
    String total,
    String home,
    String homeXg,
    String away,
    String awayXg,
  );

  /// No description provided for @disclaimerProbability.
  ///
  /// In es, this message translates to:
  /// **'Una probabilidad no es una certeza. Decide con información y juega responsablemente.'**
  String get disclaimerProbability;

  /// Fila de resumen de bajas en la tarjeta de datos.
  ///
  /// In es, this message translates to:
  /// **'Bajas'**
  String get factsAbsences;

  /// El equipo empató su último partido.
  ///
  /// In es, this message translates to:
  /// **'Empató'**
  String get factsDrew;

  /// Pliega los once titulares.
  ///
  /// In es, this message translates to:
  /// **'Ocultar los once'**
  String get factsHideLineup;

  /// Resultado más reciente del equipo en esta competición.
  ///
  /// In es, this message translates to:
  /// **'En {competition}'**
  String factsInCompetition(String competition);

  /// Once con el que el equipo jugó su último partido guardado.
  ///
  /// In es, this message translates to:
  /// **'Último once conocido'**
  String get factsLastLineup;

  /// Resultado más reciente del equipo.
  ///
  /// In es, this message translates to:
  /// **'Último partido'**
  String get factsLastMatch;

  /// Partido del que sale el último once conocido.
  ///
  /// In es, this message translates to:
  /// **'contra {rival} · {date}'**
  String factsLineupMeta(String rival, String date);

  /// Aclara que el último once no es una predicción.
  ///
  /// In es, this message translates to:
  /// **'Es el once de ese partido, no una predicción del de hoy.'**
  String get factsLineupNote;

  /// El equipo perdió su último partido.
  ///
  /// In es, this message translates to:
  /// **'Perdió'**
  String get factsLost;

  /// No hay alineación guardada de este equipo.
  ///
  /// In es, this message translates to:
  /// **'Aún no hay una alineación guardada.'**
  String get factsNoLineup;

  /// No hay resultados previos del equipo en la base.
  ///
  /// In es, this message translates to:
  /// **'Sin partidos previos registrados.'**
  String get factsNoResult;

  /// Lleva a la pestaña de alertas.
  ///
  /// In es, this message translates to:
  /// **'Ver alertas'**
  String get factsSeeAlerts;

  /// Despliega los once titulares.
  ///
  /// In es, this message translates to:
  /// **'Ver los once'**
  String get factsShowLineup;

  /// Título de la tarjeta con resultados previos, último once y bajas.
  ///
  /// In es, this message translates to:
  /// **'Datos del partido'**
  String get factsTitle;

  /// Marcador y rival de un partido.
  ///
  /// In es, this message translates to:
  /// **'{score} contra {rival}'**
  String factsVs(String score, String rival);

  /// El equipo ganó su último partido.
  ///
  /// In es, this message translates to:
  /// **'Ganó'**
  String get factsWon;

  /// No description provided for @famCardsSubtitle.
  ///
  /// In es, this message translates to:
  /// **'Líneas de menos tarjetas con respaldo histórico'**
  String get famCardsSubtitle;

  /// No description provided for @famCardsTitle.
  ///
  /// In es, this message translates to:
  /// **'Tarjetas'**
  String get famCardsTitle;

  /// No description provided for @famCornersSubtitle.
  ///
  /// In es, this message translates to:
  /// **'Más y menos córners del partido completo'**
  String get famCornersSubtitle;

  /// No description provided for @famCornersTeamSubtitle.
  ///
  /// In es, this message translates to:
  /// **'Local y visitante, con su propia línea'**
  String get famCornersTeamSubtitle;

  /// No description provided for @famCornersTeamTitle.
  ///
  /// In es, this message translates to:
  /// **'Córners por equipo'**
  String get famCornersTeamTitle;

  /// No description provided for @famCornersTitle.
  ///
  /// In es, this message translates to:
  /// **'Córners totales'**
  String get famCornersTitle;

  /// No description provided for @famDoubleChanceSubtitle.
  ///
  /// In es, this message translates to:
  /// **'Dos resultados posibles en una selección'**
  String get famDoubleChanceSubtitle;

  /// No description provided for @famDoubleChanceTitle.
  ///
  /// In es, this message translates to:
  /// **'Doble oportunidad'**
  String get famDoubleChanceTitle;

  /// No description provided for @famGoalsSubtitle.
  ///
  /// In es, this message translates to:
  /// **'Totales con líneas históricamente evaluadas'**
  String get famGoalsSubtitle;

  /// No description provided for @famGoalsTitle.
  ///
  /// In es, this message translates to:
  /// **'Goles del partido'**
  String get famGoalsTitle;

  /// No description provided for @famHandicapSubtitle.
  ///
  /// In es, this message translates to:
  /// **'Líneas de protección y empate con devolución'**
  String get famHandicapSubtitle;

  /// No description provided for @famHandicapTitle.
  ///
  /// In es, this message translates to:
  /// **'Hándicap asiático'**
  String get famHandicapTitle;

  /// No description provided for @famNbaSubtitle.
  ///
  /// In es, this message translates to:
  /// **'Evaluación exploratoria · pendiente de confirmación'**
  String get famNbaSubtitle;

  /// No description provided for @famNbaTeamTitle.
  ///
  /// In es, this message translates to:
  /// **'NBA · Puntos de equipo'**
  String get famNbaTeamTitle;

  /// No description provided for @famNbaTotalTitle.
  ///
  /// In es, this message translates to:
  /// **'NBA · Total del partido'**
  String get famNbaTotalTitle;

  /// No description provided for @famNbaWinnerTitle.
  ///
  /// In es, this message translates to:
  /// **'NBA · Ganador'**
  String get famNbaWinnerTitle;

  /// No description provided for @famTeamGoalsSubtitle.
  ///
  /// In es, this message translates to:
  /// **'Al menos un gol del local o del visitante'**
  String get famTeamGoalsSubtitle;

  /// No description provided for @famTeamGoalsTitle.
  ///
  /// In es, this message translates to:
  /// **'Marca un equipo'**
  String get famTeamGoalsTitle;

  /// No description provided for @famWinnerSubtitle.
  ///
  /// In es, this message translates to:
  /// **'Resultado 1X2 de alta probabilidad'**
  String get famWinnerSubtitle;

  /// No description provided for @famWinnerTitle.
  ///
  /// In es, this message translates to:
  /// **'Ganador del partido'**
  String get famWinnerTitle;

  /// No description provided for @featAgenda.
  ///
  /// In es, this message translates to:
  /// **'Agenda temporalmente no disponible'**
  String get featAgenda;

  /// No description provided for @featBalance.
  ///
  /// In es, this message translates to:
  /// **'Seguimiento en preparación'**
  String get featBalance;

  /// No description provided for @featCommunity.
  ///
  /// In es, this message translates to:
  /// **'Comunidad en preparación'**
  String get featCommunity;

  /// No description provided for @featLanguages.
  ///
  /// In es, this message translates to:
  /// **'Traducciones en preparación'**
  String get featLanguages;

  /// No description provided for @featMatchData.
  ///
  /// In es, this message translates to:
  /// **'Datos del partido temporalmente no disponibles'**
  String get featMatchData;

  /// No description provided for @featMeasurement.
  ///
  /// In es, this message translates to:
  /// **'Medición en preparación'**
  String get featMeasurement;

  /// No description provided for @featNba.
  ///
  /// In es, this message translates to:
  /// **'Modelo NBA en entrenamiento'**
  String get featNba;

  /// No description provided for @featNotifications.
  ///
  /// In es, this message translates to:
  /// **'Notificaciones en preparación'**
  String get featNotifications;

  /// No description provided for @featPurchases.
  ///
  /// In es, this message translates to:
  /// **'Compras en preparación'**
  String get featPurchases;

  /// No description provided for @featStats.
  ///
  /// In es, this message translates to:
  /// **'Estadísticas temporalmente no disponibles'**
  String get featStats;

  /// No description provided for @featVip.
  ///
  /// In es, this message translates to:
  /// **'Acceso VIP temporalmente no disponible'**
  String get featVip;

  /// No description provided for @featureTraining.
  ///
  /// In es, this message translates to:
  /// **'Modelo en entrenamiento'**
  String get featureTraining;

  /// No description provided for @fixtureFinished.
  ///
  /// In es, this message translates to:
  /// **'FINALIZADO'**
  String get fixtureFinished;

  /// No description provided for @fixtureLive.
  ///
  /// In es, this message translates to:
  /// **'EN VIVO'**
  String get fixtureLive;

  /// No description provided for @fixtureLocalTime.
  ///
  /// In es, this message translates to:
  /// **'HORA LOCAL'**
  String get fixtureLocalTime;

  /// No description provided for @fixtureStartsIn.
  ///
  /// In es, this message translates to:
  /// **'EMPIEZA EN'**
  String get fixtureStartsIn;

  /// No description provided for @fixtureTbd.
  ///
  /// In es, this message translates to:
  /// **'POR CONFIRMAR'**
  String get fixtureTbd;

  /// No description provided for @forecastCanFail.
  ///
  /// In es, this message translates to:
  /// **'Un pronóstico puede fallar; la probabilidad no garantiza el resultado.'**
  String get forecastCanFail;

  /// No description provided for @forecastFeatured.
  ///
  /// In es, this message translates to:
  /// **'DESTACADO'**
  String get forecastFeatured;

  /// No description provided for @forecastFree.
  ///
  /// In es, this message translates to:
  /// **'GRATUITO'**
  String get forecastFree;

  /// No description provided for @forecastHalfTime.
  ///
  /// In es, this message translates to:
  /// **'DESCANSO'**
  String get forecastHalfTime;

  /// No description provided for @forecastInPlay.
  ///
  /// In es, this message translates to:
  /// **'EN JUEGO'**
  String get forecastInPlay;

  /// No description provided for @forecastLiveScore.
  ///
  /// In es, this message translates to:
  /// **'Marcador en vivo'**
  String get forecastLiveScore;

  /// No description provided for @forecastLiveScoreAgo.
  ///
  /// In es, this message translates to:
  /// **'Marcador en vivo · actualizado hace {minutes} min'**
  String forecastLiveScoreAgo(int minutes);

  /// No description provided for @forecastMarketNote.
  ///
  /// In es, this message translates to:
  /// **'Probabilidades calculadas con las cuotas del mercado sin margen: esta liga no tiene modelo propio.'**
  String get forecastMarketNote;

  /// No description provided for @forecastOddsAtPublish.
  ///
  /// In es, this message translates to:
  /// **'Cuota al publicar'**
  String get forecastOddsAtPublish;

  /// No description provided for @forecastProbCalc.
  ///
  /// In es, this message translates to:
  /// **'{percent} prob. calculada'**
  String forecastProbCalc(String percent);

  /// No description provided for @forecastSeeStats.
  ///
  /// In es, this message translates to:
  /// **'Ver estadísticas del partido'**
  String get forecastSeeStats;

  /// No description provided for @forecastSourceMarket.
  ///
  /// In es, this message translates to:
  /// **'CUOTAS DEL MERCADO'**
  String get forecastSourceMarket;

  /// No description provided for @forecastSourceModel.
  ///
  /// In es, this message translates to:
  /// **'MODELO ALGORÍTMICO'**
  String get forecastSourceModel;

  /// No description provided for @forecastTitle.
  ///
  /// In es, this message translates to:
  /// **'MODELO ALGORÍTMICO'**
  String get forecastTitle;

  /// No description provided for @forecastUnlocked.
  ///
  /// In es, this message translates to:
  /// **'DESBLOQUEADO'**
  String get forecastUnlocked;

  /// No description provided for @forecastVerdictTitle.
  ///
  /// In es, this message translates to:
  /// **'💡  RESUMEN DEL PRONÓSTICO'**
  String get forecastVerdictTitle;

  /// No description provided for @formatScheduleUnavailable.
  ///
  /// In es, this message translates to:
  /// **'Horario no disponible'**
  String get formatScheduleUnavailable;

  /// No description provided for @groupBtts.
  ///
  /// In es, this message translates to:
  /// **'AMBOS MARCAN'**
  String get groupBtts;

  /// No description provided for @groupCards.
  ///
  /// In es, this message translates to:
  /// **'TARJETAS'**
  String get groupCards;

  /// No description provided for @groupCorners.
  ///
  /// In es, this message translates to:
  /// **'CÓRNERS'**
  String get groupCorners;

  /// No description provided for @groupDoubleChance.
  ///
  /// In es, this message translates to:
  /// **'DOBLE OPORTUNIDAD'**
  String get groupDoubleChance;

  /// No description provided for @groupDrawNoBet.
  ///
  /// In es, this message translates to:
  /// **'EMPATE NO ACCIÓN'**
  String get groupDrawNoBet;

  /// No description provided for @groupFirstHalf.
  ///
  /// In es, this message translates to:
  /// **'1ª MITAD'**
  String get groupFirstHalf;

  /// No description provided for @groupGoals.
  ///
  /// In es, this message translates to:
  /// **'GOLES'**
  String get groupGoals;

  /// No description provided for @groupHandicap.
  ///
  /// In es, this message translates to:
  /// **'HÁNDICAP'**
  String get groupHandicap;

  /// No description provided for @groupResult.
  ///
  /// In es, this message translates to:
  /// **'RESULTADO'**
  String get groupResult;

  /// No description provided for @groupSpecials.
  ///
  /// In es, this message translates to:
  /// **'ESPECIALES'**
  String get groupSpecials;

  /// No description provided for @groupTeamGoals.
  ///
  /// In es, this message translates to:
  /// **'GOLES DE EQUIPO'**
  String get groupTeamGoals;

  /// Texto del tema 1.
  ///
  /// In es, this message translates to:
  /// **'Si un pronóstico tiene 75 % de probabilidad, el modelo espera que se cumpla cerca de 3 de cada 4 veces que se repita una situación así. Eso significa que 1 de cada 4 no se cumplirá. Ningún dato garantiza un resultado concreto.'**
  String get guideBody1;

  /// Texto del tema 2.
  ///
  /// In es, this message translates to:
  /// **'La cuota la fija una casa de apuestas e incluye su margen. Comparar la probabilidad del modelo con la que implica la cuota ayuda a ver si el precio es razonable; no asegura que el resultado llegue.'**
  String get guideBody2;

  /// Texto del tema 3.
  ///
  /// In es, this message translates to:
  /// **'Se publican con su probabilidad y su cuota de referencia antes de empezar y no se pueden editar. Por eso puedes comparar el acierto histórico real con el que se prometía.'**
  String get guideBody3;

  /// Texto del tema 4.
  ///
  /// In es, this message translates to:
  /// **'En una combinada, la probabilidad conjunta es el producto de la de cada selección, así que baja rápido al añadir partidos. Una cuota alta suele reflejar justo eso.'**
  String get guideBody4;

  /// Texto del tema 5.
  ///
  /// In es, this message translates to:
  /// **'Cada reto va por pasos y el siguiente solo cuenta si se cumple el anterior. Mira el avance y el historial, incluidos los retos fallidos, antes de seguir uno.'**
  String get guideBody5;

  /// Texto del tema 6.
  ///
  /// In es, this message translates to:
  /// **'QuantFut no es una casa de apuestas ni asegura ganancias. Si decides apostar, hazlo solo con dinero que puedas perder y solo si eres mayor de edad. Si el juego deja de ser un pasatiempo, pide ayuda.'**
  String get guideBody6;

  /// Título del tema 1.
  ///
  /// In es, this message translates to:
  /// **'Una probabilidad no es una certeza'**
  String get guideHead1;

  /// Título del tema 2.
  ///
  /// In es, this message translates to:
  /// **'La cuota es un precio, no una opinión del modelo'**
  String get guideHead2;

  /// Título del tema 3.
  ///
  /// In es, this message translates to:
  /// **'Cada pronóstico se sella antes del partido'**
  String get guideHead3;

  /// Título del tema 4.
  ///
  /// In es, this message translates to:
  /// **'Más selecciones, menos probabilidad'**
  String get guideHead4;

  /// Título del tema 5.
  ///
  /// In es, this message translates to:
  /// **'Se avanza un escalón cada vez'**
  String get guideHead5;

  /// Título del tema 6.
  ///
  /// In es, this message translates to:
  /// **'Es información y entretenimiento'**
  String get guideHead6;

  /// Botón para avanzar al siguiente tema de la guía.
  ///
  /// In es, this message translates to:
  /// **'Siguiente'**
  String get guideNext;

  /// Botón para volver al tema anterior de la guía.
  ///
  /// In es, this message translates to:
  /// **'Anterior'**
  String get guidePrevious;

  /// Regla de responsabilidad 1 en la guía.
  ///
  /// In es, this message translates to:
  /// **'Solo con dinero que puedas perder'**
  String get guideRespRule1;

  /// Regla de responsabilidad 2 en la guía.
  ///
  /// In es, this message translates to:
  /// **'Solo si eres mayor de edad'**
  String get guideRespRule2;

  /// Regla de responsabilidad 3 en la guía.
  ///
  /// In es, this message translates to:
  /// **'Si deja de ser un pasatiempo, pide ayuda'**
  String get guideRespRule3;

  /// Subtítulo de la guía.
  ///
  /// In es, this message translates to:
  /// **'Aprende a leer los datos antes de decidir.'**
  String get guideSubtitle;

  /// Título de la pantalla de guía.
  ///
  /// In es, this message translates to:
  /// **'Guía de pronósticos'**
  String get guideTitle;

  /// Tema 1 de la guía.
  ///
  /// In es, this message translates to:
  /// **'PROBABILIDAD'**
  String get guideTopic1;

  /// Tema 2 de la guía.
  ///
  /// In es, this message translates to:
  /// **'CUOTA'**
  String get guideTopic2;

  /// Tema 3 de la guía.
  ///
  /// In es, this message translates to:
  /// **'ALTA PROBABILIDAD'**
  String get guideTopic3;

  /// Tema 4 de la guía.
  ///
  /// In es, this message translates to:
  /// **'PARLEY'**
  String get guideTopic4;

  /// Tema 5 de la guía.
  ///
  /// In es, this message translates to:
  /// **'RETO ESCALERA'**
  String get guideTopic5;

  /// Tema 6 de la guía.
  ///
  /// In es, this message translates to:
  /// **'RESPONSABILIDAD'**
  String get guideTopic6;

  /// Contador de temas en la guía.
  ///
  /// In es, this message translates to:
  /// **'{count} temas'**
  String guideTopicCount(int count);

  /// Insignia de empate en la lista de partidos de H2H
  ///
  /// In es, this message translates to:
  /// **'EMP'**
  String get h2hDrawBadge;

  /// Etiqueta para la tarjeta de empates en H2H de fútbol
  ///
  /// In es, this message translates to:
  /// **'EMPATES'**
  String get h2hDraws;

  /// Texto de fila cuando dos rivales nunca se han enfrentado
  ///
  /// In es, this message translates to:
  /// **'Primer duelo entre ambos'**
  String get h2hFirstDuelRow;

  /// Título de la sección de últimos enfrentamientos en H2H
  ///
  /// In es, this message translates to:
  /// **'ÚLTIMOS ENFRENTAMIENTOS'**
  String get h2hRecentMatches;

  /// No description provided for @historyWebSince.
  ///
  /// In es, this message translates to:
  /// **'Historial web desde el 26/10/2026'**
  String get historyWebSince;

  /// Título de la sección de agenda
  ///
  /// In es, this message translates to:
  /// **'Agenda'**
  String get homeAgendaTitle;

  /// Cierra el aviso de la parte superior.
  ///
  /// In es, this message translates to:
  /// **'Cerrar aviso'**
  String get homeBannerClose;

  /// No description provided for @homeByDate.
  ///
  /// In es, this message translates to:
  /// **'Partidos por fecha y horario'**
  String get homeByDate;

  /// Desbloqueos posibles con el saldo de monedas
  ///
  /// In es, this message translates to:
  /// **'{count, plural, one{Te alcanza para 1 desbloqueo} other{Te alcanza para {count} desbloqueos}}'**
  String homeCoinsUnlocks(int count);

  /// Antetítulo de la tarjeta grande de Inicio con el pronóstico de mayor probabilidad del deporte elegido.
  ///
  /// In es, this message translates to:
  /// **'Destacado del día'**
  String get homeFeatured;

  /// Aviso en Inicio cuando falla el feed de NBA o tenis; solo afecta a ese deporte y va con el botón Reintentar.
  ///
  /// In es, this message translates to:
  /// **'No se pudieron cargar los datos de este deporte.'**
  String get homeFeedError;

  /// Aviso de un partido cuyo pronóstico aún no se calcula: se calcula el mismo día a las 05:00 de México.
  ///
  /// In es, this message translates to:
  /// **'Pronóstico el {when} ({mexico} en México)'**
  String homeForecastAt(String when, String mexico);

  /// Etiqueta accesible del candado de un partido sin pronóstico todavía.
  ///
  /// In es, this message translates to:
  /// **'Pronóstico pendiente'**
  String get homeForecastPending;

  /// Título de la tarjeta de acierto en los últimos 30 días
  ///
  /// In es, this message translates to:
  /// **'Acierto · 30 días'**
  String get homeHitTitle;

  /// Botón que abre el menú Más.
  ///
  /// In es, this message translates to:
  /// **'Menú'**
  String get homeMenuTooltip;

  /// Aviso al tocar un día sin partidos.
  ///
  /// In es, this message translates to:
  /// **'No hay partidos este día.'**
  String get homeNoMatchesDay;

  /// Título de la fila horizontal de jugadores NBA con pronóstico en Inicio.
  ///
  /// In es, this message translates to:
  /// **'Jugadores con pronóstico'**
  String get homePlayersWithPicks;

  /// Lleva a la pestaña Predicciones.
  ///
  /// In es, this message translates to:
  /// **'Ver todo'**
  String get homeSeeAll;

  /// Probabilidad conjunta de un parley.
  ///
  /// In es, this message translates to:
  /// **'Prob. conjunta {percent}'**
  String homeTicketJoint(String percent);

  /// Número de selecciones de un parley.
  ///
  /// In es, this message translates to:
  /// **'{count, plural, one{{count} selección} other{{count} selecciones}}'**
  String homeTicketLegs(int count);

  /// Cuota de un boleto.
  ///
  /// In es, this message translates to:
  /// **'Cuota {value}'**
  String homeTicketOdds(String value);

  /// Tarjeta de boleto sin datos.
  ///
  /// In es, this message translates to:
  /// **'Aún no hay boletos hoy'**
  String get homeTicketsEmpty;

  /// Sección con el pronóstico de mayor probabilidad y el parley del día.
  ///
  /// In es, this message translates to:
  /// **'Boletos del día'**
  String get homeTicketsTitle;

  /// Encabezado del día de hoy en la agenda.
  ///
  /// In es, this message translates to:
  /// **'Hoy'**
  String get homeToday;

  /// Encabezado del día de mañana en la agenda.
  ///
  /// In es, this message translates to:
  /// **'Mañana'**
  String get homeTomorrow;

  /// Botón del destacado del día para ver el pronóstico gratis
  ///
  /// In es, this message translates to:
  /// **'Ver pronóstico gratis'**
  String get homeViewFreePick;

  /// No description provided for @imageCredits.
  ///
  /// In es, this message translates to:
  /// **'Fotos: Wikimedia Commons (CC BY-SA). Autores en la ficha de cada partido.'**
  String get imageCredits;

  /// No description provided for @imageUnavailable.
  ///
  /// In es, this message translates to:
  /// **'Imagen no disponible'**
  String get imageUnavailable;

  /// No description provided for @inboxEmpty.
  ///
  /// In es, this message translates to:
  /// **'Todavía no tienes avisos.'**
  String get inboxEmpty;

  /// Subtítulo explicativo cuando la bandeja de avisos está vacía.
  ///
  /// In es, this message translates to:
  /// **'Aquí verás los pronósticos nuevos, las bajas y los resultados de tus deportes.'**
  String get inboxEmptySubtitle;

  /// No description provided for @inboxMatch.
  ///
  /// In es, this message translates to:
  /// **'Partido'**
  String get inboxMatch;

  /// Etiqueta accesible del deporte de un aviso.
  ///
  /// In es, this message translates to:
  /// **'Deporte: {sport}'**
  String inboxSportTag(String sport);

  /// No description provided for @inboxTitle.
  ///
  /// In es, this message translates to:
  /// **'Avisos'**
  String get inboxTitle;

  /// Contador de avisos pendientes de leer.
  ///
  /// In es, this message translates to:
  /// **'{count} sin leer'**
  String inboxUnread(int count);

  /// Resumen sobre las tarjetas del Reto Escalera.
  ///
  /// In es, this message translates to:
  /// **'{count, plural, one{1 reto en marcha} other{{count} retos en marcha}}'**
  String ladderActiveCount(int count);

  /// No description provided for @ladderActiveReto.
  ///
  /// In es, this message translates to:
  /// **'Escalera · Reto activo'**
  String get ladderActiveReto;

  /// Etiqueta bajo el multiplicador del saldo del reto.
  ///
  /// In es, this message translates to:
  /// **'saldo actual'**
  String get ladderBalance;

  /// Etiqueta bajo la probabilidad estimada de completar el reto.
  ///
  /// In es, this message translates to:
  /// **'de completarlo'**
  String get ladderChance;

  /// No description provided for @ladderEmpty.
  ///
  /// In es, this message translates to:
  /// **'No hay retos activos publicados.'**
  String get ladderEmpty;

  /// Aviso de que la probabilidad de completar es una estimación.
  ///
  /// In es, this message translates to:
  /// **'Estimación: usa la probabilidad del escalón en juego y la media de los demás ({avg}). No es una garantía.'**
  String ladderEstimateNote(String avg);

  /// No description provided for @ladderFreeHint.
  ///
  /// In es, this message translates to:
  /// **'Un escalón gratuito: el de mayor probabilidad.'**
  String get ladderFreeHint;

  /// Pliega los escalones de un reto.
  ///
  /// In es, this message translates to:
  /// **'Ocultar escalones'**
  String get ladderHideSteps;

  /// Un reto cerrado con todos los escalones ganados.
  ///
  /// In es, this message translates to:
  /// **'Cumplido'**
  String get ladderHistoryDone;

  /// Estado vacío del historial de retos.
  ///
  /// In es, this message translates to:
  /// **'Aún no hay retos cerrados. Cuando uno termine, aparecerá aquí con su resultado.'**
  String get ladderHistoryEmpty;

  /// Un reto cerrado porque pasó su plazo (7 días) sin completar todos los escalones.
  ///
  /// In es, this message translates to:
  /// **'Expiró sin completarse'**
  String get ladderHistoryExpired;

  /// Un reto cerrado por perder un escalón.
  ///
  /// In es, this message translates to:
  /// **'Falló en el escalón {step}'**
  String ladderHistoryFailedAt(int step);

  /// Porcentaje de retos cerrados que se cumplieron.
  ///
  /// In es, this message translates to:
  /// **'Tasa de cumplidos: {rate}'**
  String ladderHistoryRate(String rate);

  /// Retorno acumulado sobre lo invertido en los retos cerrados.
  ///
  /// In es, this message translates to:
  /// **'Resultado acumulado: {roi}'**
  String ladderHistoryResult(String roi);

  /// Aviso bajo la lista del historial de retos: qué retos se enseñan.
  ///
  /// In es, this message translates to:
  /// **'Se muestran los últimos cumplidos y el último fallido.'**
  String get ladderHistoryShown;

  /// Resumen del historial de retos.
  ///
  /// In es, this message translates to:
  /// **'{done} cumplidos de {closed} cerrados'**
  String ladderHistorySummary(int done, int closed);

  /// Título de la tarjeta de retos cerrados.
  ///
  /// In es, this message translates to:
  /// **'Historial de retos'**
  String get ladderHistoryTitle;

  /// Explica que un reto con un escalón en juego sigue activo.
  ///
  /// In es, this message translates to:
  /// **'Hay un escalón esperando resultado. El reto sigue vivo.'**
  String get ladderNoteInPlay;

  /// Explica que a un reto le falta elegir el siguiente escalón y sigue activo.
  ///
  /// In es, this message translates to:
  /// **'Falta elegir el siguiente escalón; puede tardar días. El reto sigue vivo.'**
  String get ladderNoteToPick;

  /// No description provided for @ladderOddsAccumulated.
  ///
  /// In es, this message translates to:
  /// **'Cuota acumulada'**
  String get ladderOddsAccumulated;

  /// Escalones que faltan para cerrar el reto.
  ///
  /// In es, this message translates to:
  /// **'{remaining, plural, one{falta 1} other{faltan {remaining}}}'**
  String ladderRemaining(int remaining);

  /// No description provided for @ladderRestartHint.
  ///
  /// In es, this message translates to:
  /// **'Si un escalón falla, la escalera vuelve a empezar.'**
  String get ladderRestartHint;

  /// Despliega los escalones de un reto.
  ///
  /// In es, this message translates to:
  /// **'Ver escalones'**
  String get ladderShowSteps;

  /// Estado de un reto con un escalón esperando resultado.
  ///
  /// In es, this message translates to:
  /// **'En juego'**
  String get ladderStatusInPlay;

  /// Estado de un reto al que le falta elegir el siguiente escalón.
  ///
  /// In es, this message translates to:
  /// **'Por elegir'**
  String get ladderStatusToPick;

  /// No description provided for @ladderStepOf.
  ///
  /// In es, this message translates to:
  /// **'Escalón {current} de {goal}'**
  String ladderStepOf(int current, int goal);

  /// No description provided for @ladderStepProb.
  ///
  /// In es, this message translates to:
  /// **'Prob. de este escalón'**
  String get ladderStepProb;

  /// No description provided for @ladderTitle.
  ///
  /// In es, this message translates to:
  /// **'Reto #{id} · {steps, plural, one{{steps} escalón} other{{steps} escalones}}'**
  String ladderTitle(Object id, int steps);

  /// Avance de un reto.
  ///
  /// In es, this message translates to:
  /// **'{won} de {goal} ganados'**
  String ladderWonOf(int won, int goal);

  /// No description provided for @languageChangeLater.
  ///
  /// In es, this message translates to:
  /// **'Podrás cambiarlo después desde tu Perfil.'**
  String get languageChangeLater;

  /// No description provided for @languageDetected.
  ///
  /// In es, this message translates to:
  /// **'DETECTADO'**
  String get languageDetected;

  /// Etiqueta de la pantalla inicial de elección de idioma (se muestra en mayúsculas).
  ///
  /// In es, this message translates to:
  /// **'Configuración de idioma'**
  String get languageFirstBadge;

  /// Subtítulo de la pantalla inicial de elección de idioma.
  ///
  /// In es, this message translates to:
  /// **'Configura el idioma de análisis para una mejor experiencia'**
  String get languageFirstHint;

  /// Título de la pantalla inicial de elección de idioma.
  ///
  /// In es, this message translates to:
  /// **'Selecciona tu idioma'**
  String get languageFirstTitle;

  /// No description provided for @languageHint.
  ///
  /// In es, this message translates to:
  /// **'Elige el idioma. Se guarda en este dispositivo y en tu cuenta.'**
  String get languageHint;

  /// Título del selector de idioma
  ///
  /// In es, this message translates to:
  /// **'Idioma de la app'**
  String get languageTitle;

  /// Etiqueta del historial para monedas ganadas viendo un video.
  ///
  /// In es, this message translates to:
  /// **'Video con recompensa'**
  String get ledgerAd;

  /// No description provided for @ledgerAttendance.
  ///
  /// In es, this message translates to:
  /// **'Asistencia'**
  String get ledgerAttendance;

  /// No description provided for @ledgerInvitee.
  ///
  /// In es, this message translates to:
  /// **'Premio de bienvenida'**
  String get ledgerInvitee;

  /// No description provided for @ledgerOffer.
  ///
  /// In es, this message translates to:
  /// **'Oferta completada'**
  String get ledgerOffer;

  /// No description provided for @ledgerReferralReversal.
  ///
  /// In es, this message translates to:
  /// **'Premio de invitación revertido'**
  String get ledgerReferralReversal;

  /// No description provided for @ledgerReferrer.
  ///
  /// In es, this message translates to:
  /// **'Premio por invitar'**
  String get ledgerReferrer;

  /// No description provided for @ledgerReversal.
  ///
  /// In es, this message translates to:
  /// **'Oferta anulada'**
  String get ledgerReversal;

  /// No description provided for @ledgerUnlock.
  ///
  /// In es, this message translates to:
  /// **'Pronóstico desbloqueado'**
  String get ledgerUnlock;

  /// No description provided for @levelHigh.
  ///
  /// In es, this message translates to:
  /// **'ALTA PROB.'**
  String get levelHigh;

  /// No description provided for @levelModerate.
  ///
  /// In es, this message translates to:
  /// **'MODERADA'**
  String get levelModerate;

  /// No description provided for @levelSolid.
  ///
  /// In es, this message translates to:
  /// **'SÓLIDA'**
  String get levelSolid;

  /// No description provided for @lineAwayScores.
  ///
  /// In es, this message translates to:
  /// **'Marca el visitante · más de 0,5 goles'**
  String get lineAwayScores;

  /// No description provided for @lineDoubleChance.
  ///
  /// In es, this message translates to:
  /// **'Doble oportunidad · 1X / X2 / 12'**
  String get lineDoubleChance;

  /// No description provided for @lineHandicap.
  ///
  /// In es, this message translates to:
  /// **'Hándicap {line}'**
  String lineHandicap(String line);

  /// No description provided for @lineHomeScores.
  ///
  /// In es, this message translates to:
  /// **'Marca el local · más de 0,5 goles'**
  String get lineHomeScores;

  /// No description provided for @lineTeamCorners.
  ///
  /// In es, this message translates to:
  /// **'{team}: {side, select, over{más de {line} córners} other{menos de {line} córners}}'**
  String lineTeamCorners(String team, String side, String line);

  /// No description provided for @lineWinner.
  ///
  /// In es, this message translates to:
  /// **'Ganador · selección de alta probabilidad'**
  String get lineWinner;

  /// No description provided for @maintenanceNotice.
  ///
  /// In es, this message translates to:
  /// **'Estamos realizando mantenimiento. Algunas funciones pueden tardar más.'**
  String get maintenanceNotice;

  /// No description provided for @marketAwayScores.
  ///
  /// In es, this message translates to:
  /// **'Marca el visitante'**
  String get marketAwayScores;

  /// No description provided for @marketBtts.
  ///
  /// In es, this message translates to:
  /// **'Ambos marcan'**
  String get marketBtts;

  /// No description provided for @marketCards.
  ///
  /// In es, this message translates to:
  /// **'Tarjetas'**
  String get marketCards;

  /// No description provided for @marketCorners.
  ///
  /// In es, this message translates to:
  /// **'Córners'**
  String get marketCorners;

  /// No description provided for @marketCornersAway.
  ///
  /// In es, this message translates to:
  /// **'Córners del visitante'**
  String get marketCornersAway;

  /// No description provided for @marketCornersHome.
  ///
  /// In es, this message translates to:
  /// **'Córners del local'**
  String get marketCornersHome;

  /// No description provided for @marketDoubleChance.
  ///
  /// In es, this message translates to:
  /// **'Doble oportunidad'**
  String get marketDoubleChance;

  /// No description provided for @marketGoals.
  ///
  /// In es, this message translates to:
  /// **'Goles'**
  String get marketGoals;

  /// No description provided for @marketGoalsAway.
  ///
  /// In es, this message translates to:
  /// **'Goles del visitante'**
  String get marketGoalsAway;

  /// No description provided for @marketGoalsHome.
  ///
  /// In es, this message translates to:
  /// **'Goles del local'**
  String get marketGoalsHome;

  /// No description provided for @marketHandicap.
  ///
  /// In es, this message translates to:
  /// **'Hándicap'**
  String get marketHandicap;

  /// No description provided for @marketHomeScores.
  ///
  /// In es, this message translates to:
  /// **'Marca el local'**
  String get marketHomeScores;

  /// No description provided for @marketHtBtts.
  ///
  /// In es, this message translates to:
  /// **'Ambos anotan en el 1er tiempo'**
  String get marketHtBtts;

  /// No description provided for @marketHtGoal.
  ///
  /// In es, this message translates to:
  /// **'Gol en el 1er tiempo'**
  String get marketHtGoal;

  /// Selección de un mercado de línea (puntos, asistencias, total). {line} es la línea ya formateada, p. ej. 24,5.
  ///
  /// In es, this message translates to:
  /// **'Más de {line}'**
  String marketOverLine(String line);

  /// No description provided for @marketResult1x2.
  ///
  /// In es, this message translates to:
  /// **'Resultado 1X2'**
  String get marketResult1x2;

  /// Selección «menos de» de un mercado de línea (puntos, asistencias, total). {line} es la línea ya formateada, p. ej. 24,5.
  ///
  /// In es, this message translates to:
  /// **'Menos de {line}'**
  String marketUnderLine(String line);

  /// No description provided for @marketUnknown.
  ///
  /// In es, this message translates to:
  /// **'Mercado'**
  String get marketUnknown;

  /// No description provided for @marketWinToNil.
  ///
  /// In es, this message translates to:
  /// **'Gana a cero'**
  String get marketWinToNil;

  /// No description provided for @marketsAndResults.
  ///
  /// In es, this message translates to:
  /// **'Mercados y resultados'**
  String get marketsAndResults;

  /// No description provided for @marketsEvidenceAt.
  ///
  /// In es, this message translates to:
  /// **'Evidencia al {date}'**
  String marketsEvidenceAt(String date);

  /// No description provided for @marketsFamiliesRadar.
  ///
  /// In es, this message translates to:
  /// **'familias de mercado en el radar'**
  String get marketsFamiliesRadar;

  /// No description provided for @marketsHistoricHit.
  ///
  /// In es, this message translates to:
  /// **'acierto histórico {percent}'**
  String marketsHistoricHit(String percent);

  /// Aciertos sobre pronósticos publicados y resueltos.
  ///
  /// In es, this message translates to:
  /// **'{won}/{resolved} publicados'**
  String marketsHitCount(int won, int resolved);

  /// No description provided for @marketsInReview.
  ///
  /// In es, this message translates to:
  /// **'En revisión: sin línea confirmada'**
  String get marketsInReview;

  /// No description provided for @marketsModelActive.
  ///
  /// In es, this message translates to:
  /// **'MODELO ACTIVO'**
  String get marketsModelActive;

  /// No description provided for @marketsNoLineLabel.
  ///
  /// In es, this message translates to:
  /// **'sin línea confirmada'**
  String get marketsNoLineLabel;

  /// No description provided for @marketsNoPublications.
  ///
  /// In es, this message translates to:
  /// **'Sin publicaciones aún'**
  String get marketsNoPublications;

  /// No description provided for @marketsNoResolved.
  ///
  /// In es, this message translates to:
  /// **'Sin pronósticos resueltos'**
  String get marketsNoResolved;

  /// No description provided for @marketsPublished.
  ///
  /// In es, this message translates to:
  /// **'Publicado {won}/{cases}'**
  String marketsPublished(int won, int cases);

  /// No description provided for @marketsPublishedWon.
  ///
  /// In es, this message translates to:
  /// **'{won}/{cases} publicados acertados · {percent}'**
  String marketsPublishedWon(int won, int cases, String percent);

  /// No description provided for @marketsRadarNote.
  ///
  /// In es, this message translates to:
  /// **'El anillo es el acierto histórico de la mejor línea validada de cada mercado; «Publicado» son los pronósticos ya resueltos. Son pronósticos previos al partido, no alertas en vivo, y ninguna probabilidad garantiza un resultado.'**
  String get marketsRadarNote;

  /// No description provided for @marketsTabGame.
  ///
  /// In es, this message translates to:
  /// **'Partido'**
  String get marketsTabGame;

  /// No description provided for @marketsTabGames.
  ///
  /// In es, this message translates to:
  /// **'Juegos'**
  String get marketsTabGames;

  /// No description provided for @marketsTabPlayers.
  ///
  /// In es, this message translates to:
  /// **'Jugadores'**
  String get marketsTabPlayers;

  /// No description provided for @matchAwaitingResult.
  ///
  /// In es, this message translates to:
  /// **'Esperando resultado'**
  String get matchAwaitingResult;

  /// No description provided for @mdCornersTotal.
  ///
  /// In es, this message translates to:
  /// **'córners · total {total}'**
  String mdCornersTotal(Object total);

  /// No description provided for @mdEmptyHistory.
  ///
  /// In es, this message translates to:
  /// **'Todavía no hay pronósticos resueltos en este mercado.'**
  String get mdEmptyHistory;

  /// No description provided for @mdEmptyToday.
  ///
  /// In es, this message translates to:
  /// **'No hay pronósticos disponibles ahora para este mercado. Aparecen cuando el modelo los publica, antes del partido.'**
  String get mdEmptyToday;

  /// No description provided for @mdHitRate.
  ///
  /// In es, this message translates to:
  /// **'Tasa de acierto'**
  String get mdHitRate;

  /// No description provided for @mdLineConfirmed.
  ///
  /// In es, this message translates to:
  /// **'Confirmada'**
  String get mdLineConfirmed;

  /// No description provided for @mdLineNotDeployed.
  ///
  /// In es, this message translates to:
  /// **'Sin desplegar'**
  String get mdLineNotDeployed;

  /// No description provided for @mdLineReview.
  ///
  /// In es, this message translates to:
  /// **'En revisión'**
  String get mdLineReview;

  /// No description provided for @mdLineShort.
  ///
  /// In es, this message translates to:
  /// **'Muestra corta'**
  String get mdLineShort;

  /// No description provided for @mdLoadError.
  ///
  /// In es, this message translates to:
  /// **'No se pudo cargar el historial.'**
  String get mdLoadError;

  /// No description provided for @mdModel.
  ///
  /// In es, this message translates to:
  /// **'MODELO'**
  String get mdModel;

  /// No description provided for @mdNoDate.
  ///
  /// In es, this message translates to:
  /// **'Sin fecha'**
  String get mdNoDate;

  /// No description provided for @mdOverall.
  ///
  /// In es, this message translates to:
  /// **'General'**
  String get mdOverall;

  /// No description provided for @mdTabPrevious.
  ///
  /// In es, this message translates to:
  /// **'Anteriores'**
  String get mdTabPrevious;

  /// No description provided for @mdTabToday.
  ///
  /// In es, this message translates to:
  /// **'Hoy ({count})'**
  String mdTabToday(int count);

  /// No description provided for @mdValidatedLines.
  ///
  /// In es, this message translates to:
  /// **'Líneas validadas'**
  String get mdValidatedLines;

  /// No description provided for @mmChance.
  ///
  /// In es, this message translates to:
  /// **'OPORTUNIDAD'**
  String get mmChance;

  /// No description provided for @mmDisclaimer.
  ///
  /// In es, this message translates to:
  /// **'Es análisis del modelo, no una recomendación de apuesta. «Cuota justa» es 1/probabilidad: no es una cuota de casa. Un pronóstico puede fallar.'**
  String get mmDisclaimer;

  /// No description provided for @mmFairOdds.
  ///
  /// In es, this message translates to:
  /// **'cuota justa'**
  String get mmFairOdds;

  /// No description provided for @mmGroupCount.
  ///
  /// In es, this message translates to:
  /// **'{group} · {count, plural, one{{count} mercado} other{{count} mercados}}'**
  String mmGroupCount(String group, int count);

  /// No description provided for @mmLocked.
  ///
  /// In es, this message translates to:
  /// **'{count} con candado'**
  String mmLocked(int count);

  /// No description provided for @mmOpen.
  ///
  /// In es, this message translates to:
  /// **'{count, plural, one{{count} abierto} other{{count} abiertos}}'**
  String mmOpen(int count);

  /// Aviso del orden de los mercados de un partido ya jugado.
  ///
  /// In es, this message translates to:
  /// **'Acertados primero, de mayor a menor cuota'**
  String get mmOrderSettled;

  /// No description provided for @mmProb.
  ///
  /// In es, this message translates to:
  /// **'{value}% Prob.'**
  String mmProb(int value);

  /// No description provided for @mmPublishedOdds.
  ///
  /// In es, this message translates to:
  /// **'cuota publicada'**
  String get mmPublishedOdds;

  /// Etiqueta de un mercado de un partido ya jugado cuyo pronóstico no se cumplió.
  ///
  /// In es, this message translates to:
  /// **'Falló'**
  String get mmResultLoss;

  /// Etiqueta de un mercado de un partido ya jugado que se devuelve (ni acierto ni fallo).
  ///
  /// In es, this message translates to:
  /// **'Devolución'**
  String get mmResultPush;

  /// Etiqueta de un mercado de un partido ya jugado cuyo pronóstico se cumplió.
  ///
  /// In es, this message translates to:
  /// **'Acertó'**
  String get mmResultWin;

  /// No description provided for @mmScoresTitle.
  ///
  /// In es, this message translates to:
  /// **'Marcadores más probables'**
  String get mmScoresTitle;

  /// No description provided for @mmScoresVip.
  ///
  /// In es, this message translates to:
  /// **'Los marcadores más probables son para VIP.'**
  String get mmScoresVip;

  /// No description provided for @mmTitle.
  ///
  /// In es, this message translates to:
  /// **'Mercados del partido'**
  String get mmTitle;

  /// Sección del menú Más.
  ///
  /// In es, this message translates to:
  /// **'App'**
  String get moreApp;

  /// Entrada del menú que abre la guía.
  ///
  /// In es, this message translates to:
  /// **'Guía de pronósticos'**
  String get moreGuide;

  /// Subtítulo de la entrada de la guía.
  ///
  /// In es, this message translates to:
  /// **'Cómo leer probabilidades, cuotas y retos'**
  String get moreGuideSub;

  /// Sección del menú Más.
  ///
  /// In es, this message translates to:
  /// **'Aprende'**
  String get moreLearn;

  /// Sección del menú Más con términos y privacidad.
  ///
  /// In es, this message translates to:
  /// **'Legal'**
  String get moreLegal;

  /// No description provided for @moreMySportsSub.
  ///
  /// In es, this message translates to:
  /// **'Ordena y elige qué deportes ves'**
  String get moreMySportsSub;

  /// Abre la ficha de la app en la tienda.
  ///
  /// In es, this message translates to:
  /// **'Evaluar la app'**
  String get moreRate;

  /// Subtítulo de evaluar la app.
  ///
  /// In es, this message translates to:
  /// **'Comparte tu opinión'**
  String get moreRateSub;

  /// Abre el menú de compartir del sistema.
  ///
  /// In es, this message translates to:
  /// **'Compartir la app'**
  String get moreShare;

  /// Texto que se comparte con amigos.
  ///
  /// In es, this message translates to:
  /// **'Mira QuantFut: probabilidades de fútbol con datos, sin promesas. https://pronosticosdeportivos.pro'**
  String get moreShareMessage;

  /// Subtítulo de compartir la app.
  ///
  /// In es, this message translates to:
  /// **'Invita a tus amigos'**
  String get moreShareSub;

  /// Error al abrir la tienda.
  ///
  /// In es, this message translates to:
  /// **'No se pudo abrir la tienda de aplicaciones.'**
  String get moreStoreError;

  /// Subtítulo del acceso VIP en el menú Más.
  ///
  /// In es, this message translates to:
  /// **'Todos los pronósticos, sin monedas'**
  String get moreVipSubtitle;

  /// No description provided for @navCoins.
  ///
  /// In es, this message translates to:
  /// **'Coins'**
  String get navCoins;

  /// No description provided for @navHome.
  ///
  /// In es, this message translates to:
  /// **'Inicio'**
  String get navHome;

  /// No description provided for @navMarkets.
  ///
  /// In es, this message translates to:
  /// **'Mercados'**
  String get navMarkets;

  /// Etiqueta de la pestaña Picks en la barra de navegación inferior
  ///
  /// In es, this message translates to:
  /// **'Picks'**
  String get navPicks;

  /// No description provided for @navPredictions.
  ///
  /// In es, this message translates to:
  /// **'Predicciones'**
  String get navPredictions;

  /// No description provided for @navProfile.
  ///
  /// In es, this message translates to:
  /// **'Perfil'**
  String get navProfile;

  /// No description provided for @nbaAvailFootnote.
  ///
  /// In es, this message translates to:
  /// **'Los minutos de bajas suman los minutos medios de los jugadores que aparecen en el reporte. Si un equipo no envía su reporte, se avisa aquí.'**
  String get nbaAvailFootnote;

  /// No description provided for @nbaAvailKicker.
  ///
  /// In es, this message translates to:
  /// **'// REPORTE OFICIAL DE LESIONES'**
  String get nbaAvailKicker;

  /// No description provided for @nbaAvailTitle.
  ///
  /// In es, this message translates to:
  /// **'DISPONIBILIDAD'**
  String get nbaAvailTitle;

  /// Récord del equipo visitante
  ///
  /// In es, this message translates to:
  /// **'VISITANTE · {record}'**
  String nbaAwayRecord(String record);

  /// No description provided for @nbaBackToBackYesterday.
  ///
  /// In es, this message translates to:
  /// **'BACK-TO-BACK · JUGÓ AYER'**
  String get nbaBackToBackYesterday;

  /// Dominancia en métricas comparativas
  ///
  /// In es, this message translates to:
  /// **'{team} mejor en {n} de {total}'**
  String nbaCompDom(String team, int n, int total);

  /// Empate en número de métricas
  ///
  /// In es, this message translates to:
  /// **'Empate en métricas ({n} de {total})'**
  String nbaCompTied(int n, int total);

  /// No description provided for @nbaCompTitle.
  ///
  /// In es, this message translates to:
  /// **'COMPARATIVA'**
  String get nbaCompTitle;

  /// No description provided for @nbaConfEast.
  ///
  /// In es, this message translates to:
  /// **'Este'**
  String get nbaConfEast;

  /// Kicker de clasificación de conferencia NBA
  ///
  /// In es, this message translates to:
  /// **'// CONFERENCIA {conf} · {n} EQUIPOS'**
  String nbaConfStandingsKicker(String conf, int n);

  /// No description provided for @nbaConfWest.
  ///
  /// In es, this message translates to:
  /// **'Oeste'**
  String get nbaConfWest;

  /// No description provided for @nbaFactorAwayForm.
  ///
  /// In es, this message translates to:
  /// **'Rinde fuera de casa'**
  String get nbaFactorAwayForm;

  /// No description provided for @nbaFactorHomeForm.
  ///
  /// In es, this message translates to:
  /// **'Fuerte en casa'**
  String get nbaFactorHomeForm;

  /// No description provided for @nbaFactorRecordBest.
  ///
  /// In es, this message translates to:
  /// **'Mejor récord'**
  String get nbaFactorRecordBest;

  /// No description provided for @nbaFactorRecordTied.
  ///
  /// In es, this message translates to:
  /// **'Récord empatado'**
  String get nbaFactorRecordTied;

  /// No description provided for @nbaFactorRestAdvantage.
  ///
  /// In es, this message translates to:
  /// **'Más descanso'**
  String get nbaFactorRestAdvantage;

  /// No description provided for @nbaFactorRestTied.
  ///
  /// In es, this message translates to:
  /// **'Descanso igual'**
  String get nbaFactorRestTied;

  /// No description provided for @nbaFactorStreakBest.
  ///
  /// In es, this message translates to:
  /// **'Mejor racha'**
  String get nbaFactorStreakBest;

  /// No description provided for @nbaFactorStreakTied.
  ///
  /// In es, this message translates to:
  /// **'Racha igualada'**
  String get nbaFactorStreakTied;

  /// No description provided for @nbaFormLast6.
  ///
  /// In es, this message translates to:
  /// **'// ÚLTIMOS 6 PARTIDOS'**
  String get nbaFormLast6;

  /// Kicker para enfrentamientos cara a cara
  ///
  /// In es, this message translates to:
  /// **'// ÚLTIMOS {n} PARTIDOS'**
  String nbaH2hLastN(int n);

  /// Récord del equipo local
  ///
  /// In es, this message translates to:
  /// **'LOCAL · {record}'**
  String nbaHomeRecord(String record);

  /// Resumen de bajas y dudas en la cabecera del equipo
  ///
  /// In es, this message translates to:
  /// **'{bajas, plural, one{{bajas} baja} other{{bajas} bajas}} · {dudas} en duda'**
  String nbaInjuriesBadgeBajasDudas(int bajas, int dudas);

  /// Resumen de solo bajas en la cabecera del equipo
  ///
  /// In es, this message translates to:
  /// **'{bajas, plural, one{{bajas} baja} other{{bajas} bajas}}'**
  String nbaInjuriesBadgeBajasOnly(int bajas);

  /// Resumen de solo dudas en la cabecera del equipo
  ///
  /// In es, this message translates to:
  /// **'{dudas} en duda'**
  String nbaInjuriesBadgeDudasOnly(int dudas);

  /// No description provided for @nbaInjuriesClean.
  ///
  /// In es, this message translates to:
  /// **'Sin suspensiones ni bajas por lesión en el reporte oficial.'**
  String get nbaInjuriesClean;

  /// No description provided for @nbaInjuriesFullRoster.
  ///
  /// In es, this message translates to:
  /// **'Plantilla completa'**
  String get nbaInjuriesFullRoster;

  /// Etiqueta de minutos de bajas por equipo
  ///
  /// In es, this message translates to:
  /// **'Minutos · {team}'**
  String nbaInjuriesImpactMinutes(String team);

  /// Etiqueta de puntos de bajas por equipo
  ///
  /// In es, this message translates to:
  /// **'Puntos · {team}'**
  String nbaInjuriesImpactPoints(String team);

  /// No description provided for @nbaInjuriesImpactTitle.
  ///
  /// In es, this message translates to:
  /// **'Impacto estimado en el modelo por bajas'**
  String get nbaInjuriesImpactTitle;

  /// No description provided for @nbaInjuriesNoReason.
  ///
  /// In es, this message translates to:
  /// **'Sin motivo reportado'**
  String get nbaInjuriesNoReason;

  /// No description provided for @nbaInjuriesNotYetSubmitted.
  ///
  /// In es, this message translates to:
  /// **'Reporte aún no enviado a la liga por el equipo (Not Yet Submitted).'**
  String get nbaInjuriesNotYetSubmitted;

  /// No description provided for @nbaInjuriesPdfLink.
  ///
  /// In es, this message translates to:
  /// **'Parte oficial NBA (PDF)'**
  String get nbaInjuriesPdfLink;

  /// No description provided for @nbaInjuriesSub.
  ///
  /// In es, this message translates to:
  /// **'Reporte oficial de disponibilidad emitido por la NBA antes del encuentro.'**
  String get nbaInjuriesSub;

  /// No description provided for @nbaInjuriesTitle.
  ///
  /// In es, this message translates to:
  /// **'Lesiones y suspensiones'**
  String get nbaInjuriesTitle;

  /// No description provided for @nbaInjuryStatusAvailable.
  ///
  /// In es, this message translates to:
  /// **'Disponible'**
  String get nbaInjuryStatusAvailable;

  /// No description provided for @nbaInjuryStatusDoubtful.
  ///
  /// In es, this message translates to:
  /// **'Poco probable'**
  String get nbaInjuryStatusDoubtful;

  /// No description provided for @nbaInjuryStatusOut.
  ///
  /// In es, this message translates to:
  /// **'Lesionado'**
  String get nbaInjuryStatusOut;

  /// No description provided for @nbaInjuryStatusProbable.
  ///
  /// In es, this message translates to:
  /// **'Probable'**
  String get nbaInjuryStatusProbable;

  /// No description provided for @nbaInjuryStatusQuestionable.
  ///
  /// In es, this message translates to:
  /// **'En duda'**
  String get nbaInjuryStatusQuestionable;

  /// No description provided for @nbaInjuryStatusSuspended.
  ///
  /// In es, this message translates to:
  /// **'Suspendido'**
  String get nbaInjuryStatusSuspended;

  /// Récord de la temporada anterior
  ///
  /// In es, this message translates to:
  /// **'Temp. pasada {record}'**
  String nbaLastSeason(String record);

  /// No description provided for @nbaLegendOut.
  ///
  /// In es, this message translates to:
  /// **'FUERA (11–15)'**
  String get nbaLegendOut;

  /// No description provided for @nbaLegendPlayIn.
  ///
  /// In es, this message translates to:
  /// **'PLAY-IN (7–10)'**
  String get nbaLegendPlayIn;

  /// No description provided for @nbaLegendPlayoffs.
  ///
  /// In es, this message translates to:
  /// **'PLAYOFFS DIRECTOS (1–6)'**
  String get nbaLegendPlayoffs;

  /// No description provided for @nbaMarginLoss.
  ///
  /// In es, this message translates to:
  /// **'MARGEN EN DERROTA'**
  String get nbaMarginLoss;

  /// No description provided for @nbaMarginWin.
  ///
  /// In es, this message translates to:
  /// **'MARGEN EN VICTORIA'**
  String get nbaMarginWin;

  /// No description provided for @nbaMatchFactors.
  ///
  /// In es, this message translates to:
  /// **'FACTORES DEL PARTIDO'**
  String get nbaMatchFactors;

  /// No description provided for @nbaMetricAwayHome.
  ///
  /// In es, this message translates to:
  /// **'VISITANTE · LOCAL'**
  String get nbaMetricAwayHome;

  /// No description provided for @nbaMetricDiff.
  ///
  /// In es, this message translates to:
  /// **'DIFERENCIAL'**
  String get nbaMetricDiff;

  /// No description provided for @nbaMetricLast6.
  ///
  /// In es, this message translates to:
  /// **'ÚLTIMOS 6'**
  String get nbaMetricLast6;

  /// No description provided for @nbaMetricPointsAgainst.
  ///
  /// In es, this message translates to:
  /// **'PUNTOS EN CONTRA'**
  String get nbaMetricPointsAgainst;

  /// No description provided for @nbaMetricPointsFor.
  ///
  /// In es, this message translates to:
  /// **'PUNTOS A FAVOR'**
  String get nbaMetricPointsFor;

  /// No description provided for @nbaMetricRecord.
  ///
  /// In es, this message translates to:
  /// **'RÉCORD'**
  String get nbaMetricRecord;

  /// No description provided for @nbaMetricRestDays.
  ///
  /// In es, this message translates to:
  /// **'DESCANSO (DÍAS)'**
  String get nbaMetricRestDays;

  /// Minutos de ausencia de jugadores
  ///
  /// In es, this message translates to:
  /// **'{minutes} min de bajas'**
  String nbaMinutesMissing(int minutes);

  /// No description provided for @nbaNavAvail.
  ///
  /// In es, this message translates to:
  /// **'Disponibilidad'**
  String get nbaNavAvail;

  /// No description provided for @nbaNavComp.
  ///
  /// In es, this message translates to:
  /// **'Comparativa'**
  String get nbaNavComp;

  /// No description provided for @nbaNavProb.
  ///
  /// In es, this message translates to:
  /// **'Probabilidad'**
  String get nbaNavProb;

  /// No description provided for @nbaNoH2h.
  ///
  /// In es, this message translates to:
  /// **'Sin duelos directos registrados esta temporada'**
  String get nbaNoH2h;

  /// No description provided for @nbaNoStats.
  ///
  /// In es, this message translates to:
  /// **'Estadísticas NBA no disponibles'**
  String get nbaNoStats;

  /// Indica que un equipo jugó el día anterior
  ///
  /// In es, this message translates to:
  /// **'{team} jugó ayer (back-to-back)'**
  String nbaPlayedYesterday(String team);

  /// Promedio de puntos a favor y en contra
  ///
  /// In es, this message translates to:
  /// **'{pf} – {pa} pts'**
  String nbaPtsAvg(String pf, String pa);

  /// Puesto en la clasificación
  ///
  /// In es, this message translates to:
  /// **'{rank}.º de {total}'**
  String nbaRankOf(int rank, int total);

  /// Días de descanso
  ///
  /// In es, this message translates to:
  /// **'{count, plural, one{DESCANSÓ 1 DÍA} other{DESCANSÓ {count} DÍAS}}'**
  String nbaRestedDays(int count);

  /// Encabezado de la tarjeta de un partido de NBA que aún no tiene pronóstico sellado.
  ///
  /// In es, this message translates to:
  /// **'CUÁNDO SE AGREGA EL PRONÓSTICO'**
  String get nbaSealHeading;

  /// Explicación de un partido de NBA que empezó sin pronóstico sellado.
  ///
  /// In es, this message translates to:
  /// **'Este partido empezó sin un pronóstico sellado. QuantFut no calcula pronósticos a posteriori ni los agrega después del inicio.'**
  String get nbaSealMissedBody;

  /// Título de un partido de NBA que empezó sin pronóstico sellado.
  ///
  /// In es, this message translates to:
  /// **'Sin pronóstico previo'**
  String get nbaSealMissedTitle;

  /// Cuándo se sellará el pronóstico; {when} es fecha y hora locales ya formateadas.
  ///
  /// In es, this message translates to:
  /// **'Se agregará el {when}, antes del saque.'**
  String nbaSealPendingBody(String when);

  /// Cuando la API no da la hora prevista del sellado.
  ///
  /// In es, this message translates to:
  /// **'Se agregará poco antes del saque.'**
  String get nbaSealPendingSoon;

  /// Título cuando el pronóstico de un partido de NBA todavía no se ha sellado.
  ///
  /// In es, this message translates to:
  /// **'Pronóstico pendiente'**
  String get nbaSealPendingTitle;

  /// Kicker de temporada para la comparativa
  ///
  /// In es, this message translates to:
  /// **'// TEMPORADA {season}'**
  String nbaSeasonKicker(String season);

  /// Diferencia de puestos en la conferencia
  ///
  /// In es, this message translates to:
  /// **'{teamA} está {diff} puestos por encima de {teamB} en el {conf}.'**
  String nbaStandingsCallout(String teamA, int diff, String teamB, String conf);

  /// Empate de puestos en la conferencia
  ///
  /// In es, this message translates to:
  /// **'{teamA} y {teamB} están empatados en el {conf}.'**
  String nbaStandingsCalloutTied(String teamA, String teamB, String conf);

  /// Texto de racha
  ///
  /// In es, this message translates to:
  /// **'RACHA: {text}'**
  String nbaStreakLabel(String text);

  /// Comparación de rachas de ambos equipos
  ///
  /// In es, this message translates to:
  /// **'{teamA} lleva {countA} seguidas · {teamB} {countB}'**
  String nbaStreakSummary(String teamA, int countA, String teamB, int countB);

  /// No description provided for @nbaTotalPtsPerGame.
  ///
  /// In es, this message translates to:
  /// **'PUNTOS TOTALES POR PARTIDO'**
  String get nbaTotalPtsPerGame;

  /// No description provided for @nbaViewAllH2h.
  ///
  /// In es, this message translates to:
  /// **'VER TODOS EN H2H'**
  String get nbaViewAllH2h;

  /// No description provided for @nbaWinProbTitle.
  ///
  /// In es, this message translates to:
  /// **'PROBABILIDAD DE GANAR'**
  String get nbaWinProbTitle;

  /// No description provided for @nbaWinsLabel.
  ///
  /// In es, this message translates to:
  /// **'VICTORIAS'**
  String get nbaWinsLabel;

  /// No description provided for @noteExpectedAverage.
  ///
  /// In es, this message translates to:
  /// **'Media esperada: {value}'**
  String noteExpectedAverage(String value);

  /// No description provided for @noteExpectedGoals.
  ///
  /// In es, this message translates to:
  /// **'Goles esperados: {value}'**
  String noteExpectedGoals(String value);

  /// No description provided for @noteXg.
  ///
  /// In es, this message translates to:
  /// **'xG: {home} {homeValue} · {away} {awayValue}'**
  String noteXg(String home, String homeValue, String away, String awayValue);

  /// No description provided for @notificationIosPending.
  ///
  /// In es, this message translates to:
  /// **'Las notificaciones de iOS esperan la configuración de Apple.'**
  String get notificationIosPending;

  /// No description provided for @notificationPermissionDenied.
  ///
  /// In es, this message translates to:
  /// **'Activa el permiso desde los ajustes del dispositivo.'**
  String get notificationPermissionDenied;

  /// No description provided for @outcomeLoss.
  ///
  /// In es, this message translates to:
  /// **'Fallado'**
  String get outcomeLoss;

  /// No description provided for @outcomePush.
  ///
  /// In es, this message translates to:
  /// **'Reembolso'**
  String get outcomePush;

  /// No description provided for @outcomeWin.
  ///
  /// In es, this message translates to:
  /// **'Acertado'**
  String get outcomeWin;

  /// Resumen corto de las reglas del parley.
  ///
  /// In es, this message translates to:
  /// **'Hasta {count} parlays · cuota {min}–{max}'**
  String parleyChipLine(int count, String min, String max);

  /// No description provided for @parleyCombOddsLabel.
  ///
  /// In es, this message translates to:
  /// **'Cuota combinada'**
  String get parleyCombOddsLabel;

  /// No description provided for @parleyDayCount.
  ///
  /// In es, this message translates to:
  /// **'{count, plural, one{{count} parlay} other{{count} parlays}}'**
  String parleyDayCount(int count);

  /// No description provided for @parleyDaySelections.
  ///
  /// In es, this message translates to:
  /// **'Parley del día · {count} selecciones'**
  String parleyDaySelections(int count);

  /// No description provided for @parleyDaySettled.
  ///
  /// In es, this message translates to:
  /// **'{won}/{settled} acertados'**
  String parleyDaySettled(int won, int settled);

  /// No description provided for @parleyDisclaimer.
  ///
  /// In es, this message translates to:
  /// **'Se elige por probabilidad, no por valor, y cada pata resta margen. Un parley puede fallar: multiplicar cuotas también multiplica el riesgo.'**
  String get parleyDisclaimer;

  /// No description provided for @parleyFewNote.
  ///
  /// In es, this message translates to:
  /// **'Con pocos parlays la tasa real no demuestra nada todavía.'**
  String get parleyFewNote;

  /// Etiqueta corta: el parley gratuito del día.
  ///
  /// In es, this message translates to:
  /// **'1 gratis al día'**
  String get parleyFreeChip;

  /// No description provided for @parleyFreeNote.
  ///
  /// In es, this message translates to:
  /// **'Uno gratis al día (el de menor cuota); el resto, VIP.'**
  String get parleyFreeNote;

  /// No description provided for @parleyHistoryTitle.
  ///
  /// In es, this message translates to:
  /// **'Historial del Parley'**
  String get parleyHistoryTitle;

  /// No description provided for @parleyInactiveBody.
  ///
  /// In es, this message translates to:
  /// **'Cuando se active verás aquí los parlays del día, sellados antes de que empiecen los partidos.'**
  String get parleyInactiveBody;

  /// No description provided for @parleyInactiveTitle.
  ///
  /// In es, this message translates to:
  /// **'El Parley todavía no está activo'**
  String get parleyInactiveTitle;

  /// Título de la hoja con las reglas del parley.
  ///
  /// In es, this message translates to:
  /// **'Cómo se elige un parley'**
  String get parleyInfoTitle;

  /// No description provided for @parleyJointProb.
  ///
  /// In es, this message translates to:
  /// **'{percent} de probabilidad conjunta · {legs, plural, one{{legs} pata} other{{legs} patas}}'**
  String parleyJointProb(String percent, int legs);

  /// No description provided for @parleyJointProbLabel.
  ///
  /// In es, this message translates to:
  /// **'Prob. conjunta'**
  String get parleyJointProbLabel;

  /// No description provided for @parleyLoadError.
  ///
  /// In es, this message translates to:
  /// **'No se pudo cargar el Parley.'**
  String get parleyLoadError;

  /// Estado vacío del historial de parlays.
  ///
  /// In es, this message translates to:
  /// **'Aún no hay historial de parlays. Aparecerá aquí cuando se liquide el primero.'**
  String get parleyNoHistory;

  /// No description provided for @parleyNoneBody.
  ///
  /// In es, this message translates to:
  /// **'El modelo no publica un parley si no encuentra uno dentro de las reglas.'**
  String get parleyNoneBody;

  /// No description provided for @parleyNoneTitle.
  ///
  /// In es, this message translates to:
  /// **'Hoy no hay parlays'**
  String get parleyNoneTitle;

  /// No description provided for @parleyNotCertaintyHint.
  ///
  /// In es, this message translates to:
  /// **'Una probabilidad no es una certeza: de cada 3 parleys como este se espera acertar 1.'**
  String get parleyNotCertaintyHint;

  /// No description provided for @parleyOddsBetween.
  ///
  /// In es, this message translates to:
  /// **'Cuota entre {min} y {max}'**
  String parleyOddsBetween(String min, String max);

  /// No description provided for @parleyOutcomeLoss.
  ///
  /// In es, this message translates to:
  /// **'Falló'**
  String get parleyOutcomeLoss;

  /// No description provided for @parleyOutcomePending.
  ///
  /// In es, this message translates to:
  /// **'Pendiente'**
  String get parleyOutcomePending;

  /// No description provided for @parleyOutcomeVoid.
  ///
  /// In es, this message translates to:
  /// **'Anulado'**
  String get parleyOutcomeVoid;

  /// No description provided for @parleyOutcomeWin.
  ///
  /// In es, this message translates to:
  /// **'Acertó'**
  String get parleyOutcomeWin;

  /// No description provided for @parleyPastDays.
  ///
  /// In es, this message translates to:
  /// **'Días anteriores'**
  String get parleyPastDays;

  /// No description provided for @parleyRange.
  ///
  /// In es, this message translates to:
  /// **'De 1 a {count} parlays · cuota entre {min} y {max} · el más probable de cada escalón'**
  String parleyRange(int count, String min, String max);

  /// No description provided for @parleyResultScore.
  ///
  /// In es, this message translates to:
  /// **'Resultado {score}'**
  String parleyResultScore(Object score);

  /// No description provided for @parleySealed.
  ///
  /// In es, this message translates to:
  /// **'Parlays sellados antes de los partidos'**
  String get parleySealed;

  /// No description provided for @parleyStep.
  ///
  /// In es, this message translates to:
  /// **'ESCALÓN {step}'**
  String parleyStep(Object step);

  /// No description provided for @parleySummary.
  ///
  /// In es, this message translates to:
  /// **'{hits}/{total} parlays acertados'**
  String parleySummary(Object hits, Object total);

  /// No description provided for @parleySummaryPromised.
  ///
  /// In es, this message translates to:
  /// **' frente a {value} % prometido'**
  String parleySummaryPromised(String value);

  /// No description provided for @parleySummaryReal.
  ///
  /// In es, this message translates to:
  /// **' · {value} % real'**
  String parleySummaryReal(String value);

  /// No description provided for @parleyV2Heading.
  ///
  /// In es, this message translates to:
  /// **'Parley v2 · fútbol, tenis y NBA'**
  String get parleyV2Heading;

  /// No description provided for @parleyV2Reference.
  ///
  /// In es, this message translates to:
  /// **'Solo referencia'**
  String get parleyV2Reference;

  /// No description provided for @parleyV2SameGame.
  ///
  /// In es, this message translates to:
  /// **'Un solo partido'**
  String get parleyV2SameGame;

  /// No description provided for @pickOddsAtPublish.
  ///
  /// In es, this message translates to:
  /// **'Cuota al publicar · {book}'**
  String pickOddsAtPublish(Object book);

  /// No description provided for @pickProbability.
  ///
  /// In es, this message translates to:
  /// **'Probabilidad {percent}'**
  String pickProbability(String percent);

  /// No description provided for @pickSeeAnalysis.
  ///
  /// In es, this message translates to:
  /// **'Ver análisis del partido'**
  String get pickSeeAnalysis;

  /// No description provided for @pickSourceNA.
  ///
  /// In es, this message translates to:
  /// **'Fuente no disponible'**
  String get pickSourceNA;

  /// No description provided for @pickUnlockCoins.
  ///
  /// In es, this message translates to:
  /// **'Desbloquear por {cost} monedas'**
  String pickUnlockCoins(Object cost);

  /// No description provided for @pickUnlockPrompt.
  ///
  /// In es, this message translates to:
  /// **'Desbloquea el pronóstico y su cuota.'**
  String get pickUnlockPrompt;

  /// No description provided for @pickUnlockVip.
  ///
  /// In es, this message translates to:
  /// **'Desbloquear pronóstico VIP'**
  String get pickUnlockVip;

  /// Encabezado de la lista cuando hay pronósticos gratuitos y desbloqueados.
  ///
  /// In es, this message translates to:
  /// **'Pronósticos · {count}'**
  String picksAllHeading(int count);

  /// Etiqueta del pronóstico con la probabilidad más alta.
  ///
  /// In es, this message translates to:
  /// **'Mayor probabilidad'**
  String get picksBestProb;

  /// Botón compacto para desbloquear un pronóstico con monedas.
  ///
  /// In es, this message translates to:
  /// **'{cost} monedas'**
  String picksCoinsShort(Object cost);

  /// No description provided for @picksEmpty.
  ///
  /// In es, this message translates to:
  /// **'No hay pronósticos publicados pendientes en este rango.'**
  String get picksEmpty;

  /// Encabezado de los pronósticos gratuitos.
  ///
  /// In es, this message translates to:
  /// **'Gratis · {count}'**
  String picksFreeHeading(int count);

  /// Pliega los pronósticos bloqueados.
  ///
  /// In es, this message translates to:
  /// **'Ocultar la lista'**
  String get picksLockedHide;

  /// Qué se obtiene al desbloquear los pronósticos.
  ///
  /// In es, this message translates to:
  /// **'Con VIP ves la selección, la probabilidad y el análisis'**
  String get picksLockedHint;

  /// Despliega los pronósticos bloqueados.
  ///
  /// In es, this message translates to:
  /// **'Ver la lista'**
  String get picksLockedShow;

  /// Tarjeta que agrupa los pronósticos bloqueados.
  ///
  /// In es, this message translates to:
  /// **'{count, plural, one{1 pronóstico más con VIP} other{{count} pronósticos más con VIP}}'**
  String picksLockedTitle(int count);

  /// Rango de probabilidad de Alta probabilidad y porcentaje de los pronósticos del día que son gratis; los límites los manda el servidor.
  ///
  /// In es, this message translates to:
  /// **'{min}–{max} % de probabilidad · {free} % gratis'**
  String picksRangeHint(int min, int max, int free);

  /// Pie de la tarjeta de pronóstico que abre el análisis.
  ///
  /// In es, this message translates to:
  /// **'Ver análisis'**
  String get picksSeeAnalysis;

  /// Encabezado de día en la lista de pronósticos.
  ///
  /// In es, this message translates to:
  /// **'Mañana'**
  String get picksTomorrow;

  /// No description provided for @picksTrainingReasons.
  ///
  /// In es, this message translates to:
  /// **'Modelo en entrenamiento · {reasons}'**
  String picksTrainingReasons(String reasons);

  /// Aciertos sobre el total de pronósticos liquidados.
  ///
  /// In es, this message translates to:
  /// **'{hits} de {total} pronósticos'**
  String picksTrustDetail(int hits, int total);

  /// No description provided for @picksTrustMonthTitle.
  ///
  /// In es, this message translates to:
  /// **'Acierto de este mes'**
  String get picksTrustMonthTitle;

  /// Acierto que prometía la probabilidad media de los pronósticos.
  ///
  /// In es, this message translates to:
  /// **'Prometido: {percent}'**
  String picksTrustPromised(String percent);

  /// Título de la tarjeta con el acierto real de Alta probabilidad.
  ///
  /// In es, this message translates to:
  /// **'Acierto histórico'**
  String get picksTrustTitle;

  /// Fecha y hora en que se selló el pronóstico.
  ///
  /// In es, this message translates to:
  /// **'Sellado {when}'**
  String predictionsSealedAt(String when);

  /// No description provided for @prefsAdsBody.
  ///
  /// In es, this message translates to:
  /// **'Comparte con Meta datos cifrados de tu cuenta, del dispositivo y de tus compras para medir qué anuncios funcionan. En California equivale a «No compartir mis datos» cuando lo desactivas.'**
  String get prefsAdsBody;

  /// No description provided for @prefsAdsTitle.
  ///
  /// In es, this message translates to:
  /// **'Medición de anuncios (Meta)'**
  String get prefsAdsTitle;

  /// No description provided for @prefsAnalyticsBody.
  ///
  /// In es, this message translates to:
  /// **'Ayuda a mejorar la app con datos sobre las pantallas utilizadas. Es opcional.'**
  String get prefsAnalyticsBody;

  /// No description provided for @prefsAnalyticsTitle.
  ///
  /// In es, this message translates to:
  /// **'Medición de uso'**
  String get prefsAnalyticsTitle;

  /// No description provided for @prefsDeleteAccount.
  ///
  /// In es, this message translates to:
  /// **'Solicitar eliminación de mi cuenta'**
  String get prefsDeleteAccount;

  /// No description provided for @prefsDeleteAccountHint.
  ///
  /// In es, this message translates to:
  /// **'Consulta los pasos y el contacto de Saptain LTD.'**
  String get prefsDeleteAccountHint;

  /// No description provided for @prefsDiagnosticsBody.
  ///
  /// In es, this message translates to:
  /// **'Envía información técnica a Firebase y a Sentry para diagnosticar fallos. Es opcional.'**
  String get prefsDiagnosticsBody;

  /// No description provided for @prefsDiagnosticsTitle.
  ///
  /// In es, this message translates to:
  /// **'Informes de errores y rendimiento'**
  String get prefsDiagnosticsTitle;

  /// No description provided for @prefsInbox.
  ///
  /// In es, this message translates to:
  /// **'Bandeja de avisos'**
  String get prefsInbox;

  /// No description provided for @prefsLanguageNote.
  ///
  /// In es, this message translates to:
  /// **'El idioma se aplica a toda la app y se guarda como preferencia.'**
  String get prefsLanguageNote;

  /// No description provided for @prefsNote.
  ///
  /// In es, this message translates to:
  /// **'Puedes usar las funciones básicas sin activar medición o diagnóstico. Cambiar estas opciones no borra automáticamente los datos ya enviados.'**
  String get prefsNote;

  /// No description provided for @prefsNotificationsOff.
  ///
  /// In es, this message translates to:
  /// **'Disponible cuando se complete el acceso con Google.'**
  String get prefsNotificationsOff;

  /// No description provided for @prefsNotificationsOn.
  ///
  /// In es, this message translates to:
  /// **'Puedes retirarlas cuando quieras. Los avisos pueden aparecer en la pantalla bloqueada.'**
  String get prefsNotificationsOn;

  /// No description provided for @prefsNotificationsTitle.
  ///
  /// In es, this message translates to:
  /// **'Notificaciones de QuantFut'**
  String get prefsNotificationsTitle;

  /// No description provided for @prefsPrivacyRights.
  ///
  /// In es, this message translates to:
  /// **'Privacidad y tus derechos'**
  String get prefsPrivacyRights;

  /// No description provided for @prefsTitle.
  ///
  /// In es, this message translates to:
  /// **'Privacidad y preferencias'**
  String get prefsTitle;

  /// No description provided for @privacyBullet1.
  ///
  /// In es, this message translates to:
  /// **'Suscripciones con Google Play o App Store'**
  String get privacyBullet1;

  /// No description provided for @privacyBullet2.
  ///
  /// In es, this message translates to:
  /// **'Medición de uso, diagnóstico y anuncios (Meta): activados'**
  String get privacyBullet2;

  /// No description provided for @privacyReadAndAdjust.
  ///
  /// In es, this message translates to:
  /// **'Leer la política · ajustar preferencias'**
  String get privacyReadAndAdjust;

  /// No description provided for @privacyUpdateBody.
  ///
  /// In es, this message translates to:
  /// **'Ahora puedes suscribirte con Google Play o App Store, y la medición de uso, el diagnóstico y la medición de anuncios con Meta vienen activados. Puedes desactivarlos en Preferencias.'**
  String get privacyUpdateBody;

  /// No description provided for @privacyUpdateOk.
  ///
  /// In es, this message translates to:
  /// **'Entendido'**
  String get privacyUpdateOk;

  /// No description provided for @privacyUpdateRead.
  ///
  /// In es, this message translates to:
  /// **'Leer la política'**
  String get privacyUpdateRead;

  /// No description provided for @privacyUpdateTitle.
  ///
  /// In es, this message translates to:
  /// **'Actualizamos la privacidad'**
  String get privacyUpdateTitle;

  /// No description provided for @probBarAway.
  ///
  /// In es, this message translates to:
  /// **'Visita'**
  String get probBarAway;

  /// No description provided for @probBarDraw.
  ///
  /// In es, this message translates to:
  /// **'Empate'**
  String get probBarDraw;

  /// No description provided for @probBarHome.
  ///
  /// In es, this message translates to:
  /// **'Local'**
  String get probBarHome;

  /// No description provided for @profileAppVersion.
  ///
  /// In es, this message translates to:
  /// **'Versión de la app'**
  String get profileAppVersion;

  /// No description provided for @profileBalance.
  ///
  /// In es, this message translates to:
  /// **'Balance y seguimiento'**
  String get profileBalance;

  /// No description provided for @profileCheckUpdate.
  ///
  /// In es, this message translates to:
  /// **'Buscar actualización'**
  String get profileCheckUpdate;

  /// No description provided for @profileConnected.
  ///
  /// In es, this message translates to:
  /// **'QuantFut · Conectada al servidor'**
  String get profileConnected;

  /// No description provided for @profileCreateAccount.
  ///
  /// In es, this message translates to:
  /// **'Crear cuenta'**
  String get profileCreateAccount;

  /// No description provided for @profileCreateOne.
  ///
  /// In es, this message translates to:
  /// **'Crear una cuenta'**
  String get profileCreateOne;

  /// No description provided for @profileEmail.
  ///
  /// In es, this message translates to:
  /// **'Correo electrónico'**
  String get profileEmail;

  /// No description provided for @profileEmailPending.
  ///
  /// In es, this message translates to:
  /// **'Correo pendiente de verificación'**
  String get profileEmailPending;

  /// No description provided for @profileEmailVerified.
  ///
  /// In es, this message translates to:
  /// **'Correo verificado'**
  String get profileEmailVerified;

  /// No description provided for @profileForgot.
  ///
  /// In es, this message translates to:
  /// **'Olvidé mi contraseña'**
  String get profileForgot;

  /// No description provided for @profileForgotSent.
  ///
  /// In es, this message translates to:
  /// **'Si la cuenta existe, recibirás las instrucciones por correo.'**
  String get profileForgotSent;

  /// No description provided for @profileFreePlan.
  ///
  /// In es, this message translates to:
  /// **'Plan gratuito'**
  String get profileFreePlan;

  /// No description provided for @profileGeneral.
  ///
  /// In es, this message translates to:
  /// **'General'**
  String get profileGeneral;

  /// No description provided for @profileHaveAccount.
  ///
  /// In es, this message translates to:
  /// **'Ya tengo cuenta'**
  String get profileHaveAccount;

  /// No description provided for @profileLanguage.
  ///
  /// In es, this message translates to:
  /// **'Idioma'**
  String get profileLanguage;

  /// No description provided for @profileMeasurement.
  ///
  /// In es, this message translates to:
  /// **'Medición y errores'**
  String get profileMeasurement;

  /// No description provided for @profileMySports.
  ///
  /// In es, this message translates to:
  /// **'Mis deportes'**
  String get profileMySports;

  /// No description provided for @profileMySportsDefault.
  ///
  /// In es, this message translates to:
  /// **'por defecto'**
  String get profileMySportsDefault;

  /// Botón de flecha para bajar un deporte en «Mis deportes».
  ///
  /// In es, this message translates to:
  /// **'Bajar {sport}'**
  String profileMySportsDown(String sport);

  /// No description provided for @profileMySportsHint.
  ///
  /// In es, this message translates to:
  /// **'Usa las flechas para ordenar · el primero se abre por defecto'**
  String get profileMySportsHint;

  /// No description provided for @profileMySportsLastVisible.
  ///
  /// In es, this message translates to:
  /// **'Deja al menos un deporte visible.'**
  String get profileMySportsLastVisible;

  /// No description provided for @profileMySportsSaveError.
  ///
  /// In es, this message translates to:
  /// **'No se pudo guardar el cambio. Inténtalo de nuevo.'**
  String get profileMySportsSaveError;

  /// Interruptor para mostrar u ocultar un deporte.
  ///
  /// In es, this message translates to:
  /// **'Mostrar {sport}'**
  String profileMySportsShow(String sport);

  /// Botón de flecha para subir un deporte en «Mis deportes».
  ///
  /// In es, this message translates to:
  /// **'Subir {sport}'**
  String profileMySportsUp(String sport);

  /// No description provided for @profileNotifications.
  ///
  /// In es, this message translates to:
  /// **'Notificaciones'**
  String get profileNotifications;

  /// No description provided for @profileOddsFormat.
  ///
  /// In es, this message translates to:
  /// **'Formato de cuotas'**
  String get profileOddsFormat;

  /// No description provided for @profileOddsFormatValue.
  ///
  /// In es, this message translates to:
  /// **'Decimal · Cuotas registradas al publicar'**
  String get profileOddsFormatValue;

  /// No description provided for @profilePassword.
  ///
  /// In es, this message translates to:
  /// **'Contraseña'**
  String get profilePassword;

  /// No description provided for @profilePreferences.
  ///
  /// In es, this message translates to:
  /// **'Preferencias'**
  String get profilePreferences;

  /// No description provided for @profileRefreshAccess.
  ///
  /// In es, this message translates to:
  /// **'Actualizar mi acceso'**
  String get profileRefreshAccess;

  /// No description provided for @profileSeePlans.
  ///
  /// In es, this message translates to:
  /// **'Ver planes VIP'**
  String get profileSeePlans;

  /// No description provided for @profileSendVerification.
  ///
  /// In es, this message translates to:
  /// **'Enviar correo de verificación'**
  String get profileSendVerification;

  /// No description provided for @profileSignIn.
  ///
  /// In es, this message translates to:
  /// **'Iniciar sesión'**
  String get profileSignIn;

  /// No description provided for @profileSignOut.
  ///
  /// In es, this message translates to:
  /// **'Cerrar sesión'**
  String get profileSignOut;

  /// No description provided for @profileTitle.
  ///
  /// In es, this message translates to:
  /// **'Perfil y configuración'**
  String get profileTitle;

  /// No description provided for @profileUpToDate.
  ///
  /// In es, this message translates to:
  /// **'Ya tienes la última versión.'**
  String get profileUpToDate;

  /// No description provided for @profileUpdateCheckFailed.
  ///
  /// In es, this message translates to:
  /// **'No se pudo comprobar si hay actualización. Inténtalo más tarde.'**
  String get profileUpdateCheckFailed;

  /// No description provided for @profileValidUntil.
  ///
  /// In es, this message translates to:
  /// **'Vigencia: {date}'**
  String profileValidUntil(String date);

  /// No description provided for @profileVerificationSent.
  ///
  /// In es, this message translates to:
  /// **'Correo de verificación enviado.'**
  String get profileVerificationSent;

  /// No description provided for @profileVipActive.
  ///
  /// In es, this message translates to:
  /// **'Acceso VIP activo'**
  String get profileVipActive;

  /// No description provided for @profileYourAccount.
  ///
  /// In es, this message translates to:
  /// **'Tu cuenta QuantFut'**
  String get profileYourAccount;

  /// No description provided for @propStatAssists.
  ///
  /// In es, this message translates to:
  /// **'asistencias'**
  String get propStatAssists;

  /// No description provided for @propStatPoints.
  ///
  /// In es, this message translates to:
  /// **'puntos'**
  String get propStatPoints;

  /// No description provided for @propStatRebounds.
  ///
  /// In es, this message translates to:
  /// **'rebotes'**
  String get propStatRebounds;

  /// No description provided for @propStatThrees.
  ///
  /// In es, this message translates to:
  /// **'triples'**
  String get propStatThrees;

  /// No description provided for @propsEmptyFilter.
  ///
  /// In es, this message translates to:
  /// **'No hay props disponibles en esta categoría.'**
  String get propsEmptyFilter;

  /// No description provided for @propsFilterAssists.
  ///
  /// In es, this message translates to:
  /// **'ASIST.'**
  String get propsFilterAssists;

  /// No description provided for @propsFilterPoints.
  ///
  /// In es, this message translates to:
  /// **'PUNTOS'**
  String get propsFilterPoints;

  /// No description provided for @propsFilterRebounds.
  ///
  /// In es, this message translates to:
  /// **'REBOTES'**
  String get propsFilterRebounds;

  /// No description provided for @propsFilterThrees.
  ///
  /// In es, this message translates to:
  /// **'TRIPLES'**
  String get propsFilterThrees;

  /// No description provided for @propsLastFive.
  ///
  /// In es, this message translates to:
  /// **'{count} de los últimos 5'**
  String propsLastFive(int count);

  /// Casa de apuestas y hora local de la cuota de referencia.
  ///
  /// In es, this message translates to:
  /// **'{book} · {time}'**
  String quoteBookAt(String book, String time);

  /// No description provided for @quoteNone.
  ///
  /// In es, this message translates to:
  /// **'Sin cuota'**
  String get quoteNone;

  /// No description provided for @quoteReference.
  ///
  /// In es, this message translates to:
  /// **'Cuota de referencia de la captura usada al sellar el pronóstico'**
  String get quoteReference;

  /// No description provided for @radarAttack.
  ///
  /// In es, this message translates to:
  /// **'ATAQUE'**
  String get radarAttack;

  /// No description provided for @radarCreation.
  ///
  /// In es, this message translates to:
  /// **'CREACIÓN'**
  String get radarCreation;

  /// No description provided for @radarDefense.
  ///
  /// In es, this message translates to:
  /// **'DEFENSA'**
  String get radarDefense;

  /// No description provided for @radarFinishing.
  ///
  /// In es, this message translates to:
  /// **'REMATE'**
  String get radarFinishing;

  /// No description provided for @resultLabel.
  ///
  /// In es, this message translates to:
  /// **'Resultado: {score}'**
  String resultLabel(String score);

  /// Regla de la asistencia diaria.
  ///
  /// In es, this message translates to:
  /// **'Una vez al día · se reinicia a las 00:00 UTC'**
  String get rewardsAttendanceSub;

  /// Título de la tarjeta de asistencia.
  ///
  /// In es, this message translates to:
  /// **'Asistencia diaria'**
  String get rewardsAttendanceTitle;

  /// Etiqueta: la asistencia de hoy se puede marcar.
  ///
  /// In es, this message translates to:
  /// **'Disponible'**
  String get rewardsAvailable;

  /// No description provided for @rewardsCheckIn.
  ///
  /// In es, this message translates to:
  /// **'Marcar asistencia'**
  String get rewardsCheckIn;

  /// No description provided for @rewardsCheckInNote.
  ///
  /// In es, this message translates to:
  /// **'Una vez por día UTC. Si omites un día, la racha se reinicia.'**
  String get rewardsCheckInNote;

  /// Chip con el coste de desbloquear un pronóstico.
  ///
  /// In es, this message translates to:
  /// **'{cost} monedas = 1 pronóstico'**
  String rewardsChipRate(Object cost);

  /// Chip con la racha de asistencia vigente.
  ///
  /// In es, this message translates to:
  /// **'{days, plural, one{Racha de 1 día} other{Racha de {days} días}}'**
  String rewardsChipStreak(int days);

  /// Botón de la asistencia con las monedas de hoy.
  ///
  /// In es, this message translates to:
  /// **'Marcar asistencia · +{coins}'**
  String rewardsClaimCta(Object coins);

  /// Aviso tras reclamar la asistencia.
  ///
  /// In es, this message translates to:
  /// **'+{coins} monedas'**
  String rewardsClaimed(Object coins);

  /// Etiqueta: la asistencia de hoy ya se marcó.
  ///
  /// In es, this message translates to:
  /// **'Reclamada hoy'**
  String get rewardsClaimedToday;

  /// No description provided for @rewardsCodeCopied.
  ///
  /// In es, this message translates to:
  /// **'Código copiado.'**
  String get rewardsCodeCopied;

  /// No description provided for @rewardsCodeRegistered.
  ///
  /// In es, this message translates to:
  /// **'Código de invitación registrado.'**
  String get rewardsCodeRegistered;

  /// Proveedores de ofertas aún sin activar.
  ///
  /// In es, this message translates to:
  /// **'Próximamente: {names}'**
  String rewardsComingSoon(String names);

  /// Botón corto para copiar el código de invitación.
  ///
  /// In es, this message translates to:
  /// **'Copiar'**
  String get rewardsCopy;

  /// No description provided for @rewardsCopyCode.
  ///
  /// In es, this message translates to:
  /// **'Copiar mi código · {code}'**
  String rewardsCopyCode(Object code);

  /// No description provided for @rewardsDay.
  ///
  /// In es, this message translates to:
  /// **'Día {number}'**
  String rewardsDay(int number);

  /// No description provided for @rewardsDebt.
  ///
  /// In es, this message translates to:
  /// **'Saldo pendiente por recompensas anuladas.'**
  String get rewardsDebt;

  /// Encabezado de las formas de ganar monedas.
  ///
  /// In es, this message translates to:
  /// **'Gana monedas hoy'**
  String get rewardsEarnTitle;

  /// No description provided for @rewardsEnough.
  ///
  /// In es, this message translates to:
  /// **'Tienes monedas para un desbloqueo.'**
  String get rewardsEnough;

  /// No description provided for @rewardsGo.
  ///
  /// In es, this message translates to:
  /// **'Ir'**
  String get rewardsGo;

  /// Premio de quien invita.
  ///
  /// In es, this message translates to:
  /// **'+{coins} para ti'**
  String rewardsInviteChip(Object coins);

  /// No description provided for @rewardsInviteCondition.
  ///
  /// In es, this message translates to:
  /// **'Tras verificar el correo y completar {min} monedas en ofertas confirmadas.'**
  String rewardsInviteCondition(Object min);

  /// Premio del invitado.
  ///
  /// In es, this message translates to:
  /// **'Tu amigo recibe +{coins} al registrar tu código'**
  String rewardsInviteFriend(Object coins);

  /// No description provided for @rewardsInviteReward.
  ///
  /// In es, this message translates to:
  /// **'Tú +{referrer} · Tu amigo +{invitee} monedas'**
  String rewardsInviteReward(Object referrer, Object invitee);

  /// No description provided for @rewardsInviteTitle.
  ///
  /// In es, this message translates to:
  /// **'Invita a tus amigos'**
  String get rewardsInviteTitle;

  /// No description provided for @rewardsInviterCode.
  ///
  /// In es, this message translates to:
  /// **'Código de quien te invitó'**
  String get rewardsInviterCode;

  /// No description provided for @rewardsLedgerBalance.
  ///
  /// In es, this message translates to:
  /// **'Saldo'**
  String get rewardsLedgerBalance;

  /// No description provided for @rewardsLedgerEarlier.
  ///
  /// In es, this message translates to:
  /// **'Anteriores'**
  String get rewardsLedgerEarlier;

  /// No description provided for @rewardsLedgerEarned.
  ///
  /// In es, this message translates to:
  /// **'Ganadas'**
  String get rewardsLedgerEarned;

  /// No description provided for @rewardsLedgerEmpty.
  ///
  /// In es, this message translates to:
  /// **'Todavía no hay movimientos.'**
  String get rewardsLedgerEmpty;

  /// Pliega los movimientos.
  ///
  /// In es, this message translates to:
  /// **'Ver menos'**
  String get rewardsLedgerLess;

  /// Despliega más movimientos.
  ///
  /// In es, this message translates to:
  /// **'Ver más'**
  String get rewardsLedgerMore;

  /// No description provided for @rewardsLedgerSpent.
  ///
  /// In es, this message translates to:
  /// **'Gastadas'**
  String get rewardsLedgerSpent;

  /// No description provided for @rewardsLedgerTitle.
  ///
  /// In es, this message translates to:
  /// **'Mis movimientos'**
  String get rewardsLedgerTitle;

  /// No description provided for @rewardsMissing.
  ///
  /// In es, this message translates to:
  /// **'{missing, plural, one{Falta {missing} moneda para tu próximo desbloqueo.} other{Faltan {missing} monedas para tu próximo desbloqueo.}}'**
  String rewardsMissing(int missing);

  /// No description provided for @rewardsMissingUnknown.
  ///
  /// In es, this message translates to:
  /// **'Faltan — monedas para tu próximo desbloqueo.'**
  String get rewardsMissingUnknown;

  /// No description provided for @rewardsMyCoins.
  ///
  /// In es, this message translates to:
  /// **'Mis monedas'**
  String get rewardsMyCoins;

  /// Cuenta atrás hasta poder marcar asistencia de nuevo.
  ///
  /// In es, this message translates to:
  /// **'Próxima asistencia en {time}'**
  String rewardsNextIn(String time);

  /// No description provided for @rewardsOfferAvailable.
  ///
  /// In es, this message translates to:
  /// **'Ofertas según tu país y dispositivo'**
  String get rewardsOfferAvailable;

  /// No description provided for @rewardsOfferPending.
  ///
  /// In es, this message translates to:
  /// **'Pendiente de activar'**
  String get rewardsOfferPending;

  /// No description provided for @rewardsOffersConfig.
  ///
  /// In es, this message translates to:
  /// **'Este proveedor todavía no está listo. Vuelve a intentarlo más tarde.'**
  String get rewardsOffersConfig;

  /// Botón que abre las ofertas del proveedor.
  ///
  /// In es, this message translates to:
  /// **'Ver ofertas'**
  String get rewardsOffersCta;

  /// Frase de la tarjeta de ofertas.
  ///
  /// In es, this message translates to:
  /// **'Completa ofertas y recibe monedas.'**
  String get rewardsOffersLead;

  /// No description provided for @rewardsOffersLoadFailed.
  ///
  /// In es, this message translates to:
  /// **'No pudimos abrir las ofertas. Revisa tu conexión y vuelve a intentarlo.'**
  String get rewardsOffersLoadFailed;

  /// No description provided for @rewardsOffersTimeout.
  ///
  /// In es, this message translates to:
  /// **'Las ofertas tardaron demasiado en cargar. Vuelve a intentarlo.'**
  String get rewardsOffersTimeout;

  /// No description provided for @rewardsOffersTitle.
  ///
  /// In es, this message translates to:
  /// **'Ofertas para ganar monedas'**
  String get rewardsOffersTitle;

  /// No description provided for @rewardsOffersUnavailable.
  ///
  /// In es, this message translates to:
  /// **'No hay ofertas disponibles ahora. Vuelve a intentarlo más tarde.'**
  String get rewardsOffersUnavailable;

  /// No description provided for @rewardsOperationDone.
  ///
  /// In es, this message translates to:
  /// **'Operación confirmada.'**
  String get rewardsOperationDone;

  /// Pega el código de invitación desde el portapapeles en el campo de Coins.
  ///
  /// In es, this message translates to:
  /// **'Pegar código'**
  String get rewardsPaste;

  /// Aviso al pegar cuando el portapapeles no trae un código ni un enlace de invitación.
  ///
  /// In es, this message translates to:
  /// **'No hay un código de invitación en el portapapeles.'**
  String get rewardsPasteEmpty;

  /// No description provided for @rewardsReferralStats.
  ///
  /// In es, this message translates to:
  /// **'{registered} registrados · {qualified} validados'**
  String rewardsReferralStats(Object registered, Object qualified);

  /// No description provided for @rewardsRefreshBalance.
  ///
  /// In es, this message translates to:
  /// **'Actualizar saldo'**
  String get rewardsRefreshBalance;

  /// No description provided for @rewardsRegisterCode.
  ///
  /// In es, this message translates to:
  /// **'Registrar código'**
  String get rewardsRegisterCode;

  /// Botón que comparte el código de invitación y el enlace.
  ///
  /// In es, this message translates to:
  /// **'Compartir mi código'**
  String get rewardsShare;

  /// Texto que se comparte con el código de referido y el enlace a la página de invitación.
  ///
  /// In es, this message translates to:
  /// **'Usa mi código de invitación {code} en QuantFut: en Coins escríbelo en «Código de quien te invitó». Todo explicado aquí: {link}'**
  String rewardsShareMessage(String code, String link);

  /// No description provided for @rewardsSignIn.
  ///
  /// In es, this message translates to:
  /// **'Inicia sesión'**
  String get rewardsSignIn;

  /// No description provided for @rewardsSignInHint.
  ///
  /// In es, this message translates to:
  /// **'Inicia sesión en Perfil para guardar tu saldo, marcar asistencia y usar un código de referido.'**
  String get rewardsSignInHint;

  /// No description provided for @rewardsStreak.
  ///
  /// In es, this message translates to:
  /// **'Racha de asistencia · {days, plural, one{{days} día} other{{days} días}}'**
  String rewardsStreak(int days);

  /// Sección desplegable con los términos de las monedas.
  ///
  /// In es, this message translates to:
  /// **'Reglas y condiciones'**
  String get rewardsTermsTitle;

  /// No description provided for @rewardsUnlockFor.
  ///
  /// In es, this message translates to:
  /// **'Desbloquea un pronóstico por {cost} monedas'**
  String rewardsUnlockFor(Object cost);

  /// Saldo de monedas expresado en desbloqueos posibles.
  ///
  /// In es, this message translates to:
  /// **'{count, plural, one{Tienes monedas para 1 desbloqueo.} other{Tienes monedas para {count} desbloqueos.}}'**
  String rewardsUnlocksAvailable(int count);

  /// Etiqueta de protocolo de la línea de sello (hash) de un pick
  ///
  /// In es, this message translates to:
  /// **'SELLO'**
  String get sealLabel;

  /// Etiqueta de protocolo: hora de publicación del pick
  ///
  /// In es, this message translates to:
  /// **'PUBLICADO'**
  String get sealPublished;

  /// Etiqueta de protocolo: el sello del pick fue verificado
  ///
  /// In es, this message translates to:
  /// **'VERIFICADO'**
  String get sealVerified;

  /// No description provided for @selBttsNo.
  ///
  /// In es, this message translates to:
  /// **'No marcan los dos'**
  String get selBttsNo;

  /// No description provided for @selBttsYes.
  ///
  /// In es, this message translates to:
  /// **'Marcan los dos'**
  String get selBttsYes;

  /// No description provided for @selCards.
  ///
  /// In es, this message translates to:
  /// **'{side, select, over{Más de {line} tarjetas} other{Menos de {line} tarjetas}}'**
  String selCards(String side, String line);

  /// No description provided for @selCorners.
  ///
  /// In es, this message translates to:
  /// **'{side, select, over{Más de {line} córners} other{Menos de {line} córners}}'**
  String selCorners(String side, String line);

  /// No description provided for @selCornersTeam.
  ///
  /// In es, this message translates to:
  /// **'{side, select, over{Más de {line} córners de {team}} other{Menos de {line} córners de {team}}}'**
  String selCornersTeam(String side, String line, String team);

  /// No description provided for @selDrawNoBet.
  ///
  /// In es, this message translates to:
  /// **'{team} gana (empate devuelve)'**
  String selDrawNoBet(String team);

  /// No description provided for @selEitherNoDraw.
  ///
  /// In es, this message translates to:
  /// **'{home} o {away} (sin empate)'**
  String selEitherNoDraw(String home, String away);

  /// Tenis: hándicap de juegos
  ///
  /// In es, this message translates to:
  /// **'{team} {line} juegos'**
  String selGamesHandicap(String team, String line);

  /// Tenis: total de juegos, más de
  ///
  /// In es, this message translates to:
  /// **'Más de {line} juegos'**
  String selGamesOver(String line);

  /// Tenis: total de juegos, menos de
  ///
  /// In es, this message translates to:
  /// **'Menos de {line} juegos'**
  String selGamesUnder(String line);

  /// No description provided for @selGoals.
  ///
  /// In es, this message translates to:
  /// **'{side, select, over{Más de {line} goles} other{Menos de {line} goles}}'**
  String selGoals(String side, String line);

  /// No description provided for @selHandicapLong.
  ///
  /// In es, this message translates to:
  /// **'{team} {line} (hándicap asiático)'**
  String selHandicapLong(String team, String line);

  /// No description provided for @selHandicapShort.
  ///
  /// In es, this message translates to:
  /// **'{team} {line}'**
  String selHandicapShort(String team, String line);

  /// No description provided for @selHomeWins.
  ///
  /// In es, this message translates to:
  /// **'Gana {team}'**
  String selHomeWins(String team);

  /// No description provided for @selHtBttsNo.
  ///
  /// In es, this message translates to:
  /// **'No marcan los dos en el 1T'**
  String get selHtBttsNo;

  /// No description provided for @selHtGoalYes.
  ///
  /// In es, this message translates to:
  /// **'Habrá gol en el 1T'**
  String get selHtGoalYes;

  /// NBA: prop de jugador, más de
  ///
  /// In es, this message translates to:
  /// **'{player}: más de {line} {stat}'**
  String selPlayerOver(String player, String line, String stat);

  /// NBA: prop de jugador, menos de
  ///
  /// In es, this message translates to:
  /// **'{player}: menos de {line} {stat}'**
  String selPlayerUnder(String player, String line, String stat);

  /// NBA: total de puntos del partido, más de
  ///
  /// In es, this message translates to:
  /// **'Más de {line} puntos'**
  String selPointsOver(String line);

  /// NBA: total de puntos del partido, menos de
  ///
  /// In es, this message translates to:
  /// **'Menos de {line} puntos'**
  String selPointsUnder(String line);

  /// NBA: hándicap de puntos
  ///
  /// In es, this message translates to:
  /// **'{team} {line} puntos'**
  String selSpreadPoints(String team, String line);

  /// Goles de un equipo con línea distinta de «marca» (más de 0,5).
  ///
  /// In es, this message translates to:
  /// **'{side, select, over{Más de {line} goles de {team}} other{Menos de {line} goles de {team}}}'**
  String selTeamGoalsLine(String side, String line, String team);

  /// No description provided for @selTeamOrDraw.
  ///
  /// In es, this message translates to:
  /// **'{team} o empate'**
  String selTeamOrDraw(String team);

  /// No description provided for @selTeamScores.
  ///
  /// In es, this message translates to:
  /// **'Marca {team}'**
  String selTeamScores(String team);

  /// No description provided for @selWinToNil.
  ///
  /// In es, this message translates to:
  /// **'{team} gana sin recibir gol'**
  String selWinToNil(String team);

  /// Tarjeta de familia de mercado de NBA o tenis: pronósticos aún abiertos y ya resueltos.
  ///
  /// In es, this message translates to:
  /// **'Abiertos {open} · Resueltos {resolved}'**
  String sfCounts(int open, int resolved);

  /// No description provided for @sfNbaGameTotal.
  ///
  /// In es, this message translates to:
  /// **'Total de puntos del partido'**
  String get sfNbaGameTotal;

  /// No description provided for @sfNbaHandicap.
  ///
  /// In es, this message translates to:
  /// **'Hándicap del partido'**
  String get sfNbaHandicap;

  /// No description provided for @sfNbaPlayerAssists.
  ///
  /// In es, this message translates to:
  /// **'Asistencias del jugador'**
  String get sfNbaPlayerAssists;

  /// No description provided for @sfNbaPlayerPoints.
  ///
  /// In es, this message translates to:
  /// **'Puntos del jugador'**
  String get sfNbaPlayerPoints;

  /// No description provided for @sfNbaPlayerRebounds.
  ///
  /// In es, this message translates to:
  /// **'Rebotes del jugador'**
  String get sfNbaPlayerRebounds;

  /// No description provided for @sfNbaPlayerThrees.
  ///
  /// In es, this message translates to:
  /// **'Triples del jugador'**
  String get sfNbaPlayerThrees;

  /// No description provided for @sfNbaTeamPoints.
  ///
  /// In es, this message translates to:
  /// **'Puntos por equipo'**
  String get sfNbaTeamPoints;

  /// No description provided for @sfRangeNote.
  ///
  /// In es, this message translates to:
  /// **'Pronósticos con probabilidad del 60 % al 95 %'**
  String get sfRangeNote;

  /// No description provided for @sfTennisGamesHandicap.
  ///
  /// In es, this message translates to:
  /// **'Hándicap de juegos'**
  String get sfTennisGamesHandicap;

  /// No description provided for @sfTennisGamesTotal.
  ///
  /// In es, this message translates to:
  /// **'Juegos totales'**
  String get sfTennisGamesTotal;

  /// No description provided for @sfTennisSetWinner.
  ///
  /// In es, this message translates to:
  /// **'Ganador del set'**
  String get sfTennisSetWinner;

  /// No description provided for @sfTennisSetsHandicap.
  ///
  /// In es, this message translates to:
  /// **'Hándicap de sets'**
  String get sfTennisSetsHandicap;

  /// No description provided for @sfTennisSetsTotal.
  ///
  /// In es, this message translates to:
  /// **'Total de sets'**
  String get sfTennisSetsTotal;

  /// No description provided for @sfTennisTiebreak.
  ///
  /// In es, this message translates to:
  /// **'Tie-break'**
  String get sfTennisTiebreak;

  /// Explica cómo conseguir monedas.
  ///
  /// In es, this message translates to:
  /// **'Gana monedas con la asistencia diaria y las ofertas para desbloquear este pronóstico.'**
  String get shellNeedCoinsBody;

  /// Botón que lleva a la pestaña Coins.
  ///
  /// In es, this message translates to:
  /// **'Ganar monedas'**
  String get shellNeedCoinsCta;

  /// Título del aviso al intentar desbloquear sin saldo.
  ///
  /// In es, this message translates to:
  /// **'Te faltan monedas'**
  String get shellNeedCoinsTitle;

  /// No description provided for @shellNewAlert.
  ///
  /// In es, this message translates to:
  /// **'Nuevo aviso de QuantFut'**
  String get shellNewAlert;

  /// No description provided for @shellSignInForCoins.
  ///
  /// In es, this message translates to:
  /// **'Inicia sesión en Perfil para usar tus monedas.'**
  String get shellSignInForCoins;

  /// No description provided for @shellUnlockAction.
  ///
  /// In es, this message translates to:
  /// **'Desbloquear · {cost}'**
  String shellUnlockAction(Object cost);

  /// No description provided for @shellUnlockBody.
  ///
  /// In es, this message translates to:
  /// **'Se descontarán {cost} monedas de tu saldo. El acceso corresponde a este pronóstico.'**
  String shellUnlockBody(Object cost);

  /// No description provided for @shellUnlockTitle.
  ///
  /// In es, this message translates to:
  /// **'Desbloquear pronóstico'**
  String get shellUnlockTitle;

  /// No description provided for @shellView.
  ///
  /// In es, this message translates to:
  /// **'Ver'**
  String get shellView;

  /// No description provided for @splashTagline.
  ///
  /// In es, this message translates to:
  /// **'FÚTBOL · NBA · ESTADÍSTICA'**
  String get splashTagline;

  /// No description provided for @sportAlertsNone.
  ///
  /// In es, this message translates to:
  /// **'Sin avisos para este partido.'**
  String get sportAlertsNone;

  /// No description provided for @sportAvailApplied.
  ///
  /// In es, this message translates to:
  /// **'Reporte de lesiones aplicado'**
  String get sportAvailApplied;

  /// No description provided for @sportAvailListed.
  ///
  /// In es, this message translates to:
  /// **'{count, plural, one{{count} jugador en el reporte} other{{count} jugadores en el reporte}}'**
  String sportAvailListed(int count);

  /// No description provided for @sportAvailMissingMinutes.
  ///
  /// In es, this message translates to:
  /// **'{team}: {minutes} min de bajas'**
  String sportAvailMissingMinutes(String team, String minutes);

  /// No description provided for @sportAvailNotSubmitted.
  ///
  /// In es, this message translates to:
  /// **'{team} no envió su reporte'**
  String sportAvailNotSubmitted(String team);

  /// No description provided for @sportAvailPending.
  ///
  /// In es, this message translates to:
  /// **'Reporte de lesiones pendiente'**
  String get sportAvailPending;

  /// Etiqueta de un deporte en fase de prueba (estado preview del catálogo) en Perfil → Mis deportes.
  ///
  /// In es, this message translates to:
  /// **'Beta'**
  String get sportBeta;

  /// No description provided for @sportDetailError.
  ///
  /// In es, this message translates to:
  /// **'No se pudo cargar el detalle del partido.'**
  String get sportDetailError;

  /// No description provided for @sportFamilyOthers.
  ///
  /// In es, this message translates to:
  /// **'Otros'**
  String get sportFamilyOthers;

  /// Aviso cuando el pronóstico destacado de un partido de NBA, tenis u otro deporte queda para cuentas VIP.
  ///
  /// In es, this message translates to:
  /// **'Destacado reservado para VIP'**
  String get sportFeaturedVip;

  /// Nombre del deporte fútbol en el selector
  ///
  /// In es, this message translates to:
  /// **'Fútbol'**
  String get sportFootball;

  /// No description provided for @sportH2hRecord.
  ///
  /// In es, this message translates to:
  /// **'{home} {homeWins} – {awayWins} {away}'**
  String sportH2hRecord(String home, String away, int homeWins, int awayWins);

  /// Ventana del acierto de NBA y tenis
  ///
  /// In es, this message translates to:
  /// **'Sobre los últimos {n} resueltos'**
  String sportHitWindow(int n);

  /// Último chip del selector cuando hay más de 4 deportes
  ///
  /// In es, this message translates to:
  /// **'Más'**
  String get sportMore;

  /// Nombre del deporte baloncesto (NBA) en el selector
  ///
  /// In es, this message translates to:
  /// **'NBA'**
  String get sportNba;

  /// No description provided for @sportNoticeMore.
  ///
  /// In es, this message translates to:
  /// **'Ver más'**
  String get sportNoticeMore;

  /// No description provided for @sportPhotoCredit.
  ///
  /// In es, this message translates to:
  /// **'Foto de {name}: {author} · {license}'**
  String sportPhotoCredit(String name, String author, String license);

  /// Etiqueta accesible del selector de deporte
  ///
  /// In es, this message translates to:
  /// **'Deporte'**
  String get sportSelectorLabel;

  /// No description provided for @sportStatAge.
  ///
  /// In es, this message translates to:
  /// **'Edad'**
  String get sportStatAge;

  /// No description provided for @sportStatAway.
  ///
  /// In es, this message translates to:
  /// **'Como visitante'**
  String get sportStatAway;

  /// No description provided for @sportStatBackToBack.
  ///
  /// In es, this message translates to:
  /// **'Juega día seguido'**
  String get sportStatBackToBack;

  /// No description provided for @sportStatCareer.
  ///
  /// In es, this message translates to:
  /// **'Carrera'**
  String get sportStatCareer;

  /// No description provided for @sportStatFormIndex.
  ///
  /// In es, this message translates to:
  /// **'Índice de forma'**
  String get sportStatFormIndex;

  /// No description provided for @sportStatHome.
  ///
  /// In es, this message translates to:
  /// **'Como local'**
  String get sportStatHome;

  /// No description provided for @sportStatLast6.
  ///
  /// In es, this message translates to:
  /// **'Últimos 6'**
  String get sportStatLast6;

  /// No description provided for @sportStatPointsAgainst.
  ///
  /// In es, this message translates to:
  /// **'Puntos en contra'**
  String get sportStatPointsAgainst;

  /// No description provided for @sportStatPointsFor.
  ///
  /// In es, this message translates to:
  /// **'Puntos a favor'**
  String get sportStatPointsFor;

  /// No description provided for @sportStatRank.
  ///
  /// In es, this message translates to:
  /// **'Ranking'**
  String get sportStatRank;

  /// No description provided for @sportStatRest.
  ///
  /// In es, this message translates to:
  /// **'Días de descanso'**
  String get sportStatRest;

  /// No description provided for @sportStatSeason.
  ///
  /// In es, this message translates to:
  /// **'Temporada'**
  String get sportStatSeason;

  /// No description provided for @sportStatStanding.
  ///
  /// In es, this message translates to:
  /// **'Puesto'**
  String get sportStatStanding;

  /// No description provided for @sportStatStreak.
  ///
  /// In es, this message translates to:
  /// **'Racha'**
  String get sportStatStreak;

  /// No description provided for @sportStatSurface.
  ///
  /// In es, this message translates to:
  /// **'En esta superficie'**
  String get sportStatSurface;

  /// No description provided for @sportStatsUnavailable.
  ///
  /// In es, this message translates to:
  /// **'Aún no hay estadísticas para este partido.'**
  String get sportStatsUnavailable;

  /// No description provided for @sportSurfaceClay.
  ///
  /// In es, this message translates to:
  /// **'Arcilla'**
  String get sportSurfaceClay;

  /// No description provided for @sportSurfaceGrass.
  ///
  /// In es, this message translates to:
  /// **'Hierba'**
  String get sportSurfaceGrass;

  /// No description provided for @sportSurfaceHard.
  ///
  /// In es, this message translates to:
  /// **'Dura'**
  String get sportSurfaceHard;

  /// Nombre del deporte tenis en el selector
  ///
  /// In es, this message translates to:
  /// **'Tenis'**
  String get sportTennis;

  /// Etiqueta corta en la fila de un partido cuyo destacado es solo para VIP.
  ///
  /// In es, this message translates to:
  /// **'VIP'**
  String get sportVipBadge;

  /// No description provided for @sportVipCall.
  ///
  /// In es, this message translates to:
  /// **'Conoce los planes para ver más análisis.'**
  String get sportVipCall;

  /// Aviso con el número de mercados de un partido que solo ven las cuentas VIP.
  ///
  /// In es, this message translates to:
  /// **'{count, plural, one{1 mercado más con VIP} other{{count} mercados más con VIP}}'**
  String sportVipMarkets(int count);

  /// No description provided for @startupFailed.
  ///
  /// In es, this message translates to:
  /// **'No pudimos iniciar QuantFut. Inténtalo de nuevo.'**
  String get startupFailed;

  /// No description provided for @startupLoading.
  ///
  /// In es, this message translates to:
  /// **'Iniciando QuantFut'**
  String get startupLoading;

  /// No description provided for @statAveragesNote.
  ///
  /// In es, this message translates to:
  /// **'Promedios de {homeN} partidos del local y {awayN} del visitante. La cobertura de remates, córners y xG puede ser parcial.'**
  String statAveragesNote(Object homeN, Object awayN);

  /// No description provided for @statBestAway.
  ///
  /// In es, this message translates to:
  /// **'Mejor triunfo fuera'**
  String get statBestAway;

  /// No description provided for @statBestHome.
  ///
  /// In es, this message translates to:
  /// **'Mejor triunfo en casa'**
  String get statBestHome;

  /// No description provided for @statCleanSheet.
  ///
  /// In es, this message translates to:
  /// **'Portería a cero'**
  String get statCleanSheet;

  /// No description provided for @statCompareNote.
  ///
  /// In es, this message translates to:
  /// **'Las barras comparan los valores registrados; no representan probabilidades de victoria. Menos goles recibidos es mejor.'**
  String get statCompareNote;

  /// No description provided for @statCompareTitle.
  ///
  /// In es, this message translates to:
  /// **'Comparación de equipos'**
  String get statCompareTitle;

  /// No description provided for @statDrawStreak.
  ///
  /// In es, this message translates to:
  /// **'Racha de empates'**
  String get statDrawStreak;

  /// No description provided for @statFormLegend.
  ///
  /// In es, this message translates to:
  /// **'G: ganado · E: empate · P: perdido. Más reciente a la izquierda.'**
  String get statFormLegend;

  /// No description provided for @statFormNA.
  ///
  /// In es, this message translates to:
  /// **'Forma no disponible.'**
  String get statFormNA;

  /// No description provided for @statFormTitle.
  ///
  /// In es, this message translates to:
  /// **'Forma de los equipos'**
  String get statFormTitle;

  /// No description provided for @statGoalsAgainst.
  ///
  /// In es, this message translates to:
  /// **'Goles recibidos'**
  String get statGoalsAgainst;

  /// No description provided for @statGoalsAvgNote.
  ///
  /// In es, this message translates to:
  /// **'Goles a favor por partido; no es la proyección de goles del modelo.'**
  String get statGoalsAvgNote;

  /// No description provided for @statGoalsAvgTitle.
  ///
  /// In es, this message translates to:
  /// **'PROMEDIO HISTÓRICO DE GOLES'**
  String get statGoalsAvgTitle;

  /// No description provided for @statGoalsFor.
  ///
  /// In es, this message translates to:
  /// **'Goles a favor'**
  String get statGoalsFor;

  /// No description provided for @statH2hSummary.
  ///
  /// In es, this message translates to:
  /// **'En {n} cruces registrados: {home} ganó {homeWins}, {away} ganó {awayWins} y hubo {draws} empates.'**
  String statH2hSummary(
    Object n,
    Object home,
    Object homeWins,
    Object away,
    Object awayWins,
    Object draws,
  );

  /// No description provided for @statH2hTitle.
  ///
  /// In es, this message translates to:
  /// **'Cara a cara'**
  String get statH2hTitle;

  /// No description provided for @statLastMatches.
  ///
  /// In es, this message translates to:
  /// **'Últimos {count} partidos registrados'**
  String statLastMatches(int count);

  /// No description provided for @statMinutesNA.
  ///
  /// In es, this message translates to:
  /// **'La distribución por minutos no está disponible para este partido.'**
  String get statMinutesNA;

  /// No description provided for @statMinutesTitle.
  ///
  /// In es, this message translates to:
  /// **'Goles por minuto'**
  String get statMinutesTitle;

  /// No description provided for @statNeedsAccess.
  ///
  /// In es, this message translates to:
  /// **'El pronóstico de este partido requiere acceso VIP o un desbloqueo con monedas.'**
  String get statNeedsAccess;

  /// No description provided for @statOnTargetShort.
  ///
  /// In es, this message translates to:
  /// **'A puerta'**
  String get statOnTargetShort;

  /// No description provided for @statOver25.
  ///
  /// In es, this message translates to:
  /// **'Más de 2,5 goles'**
  String get statOver25;

  /// No description provided for @statPickProbOdds.
  ///
  /// In es, this message translates to:
  /// **'Probabilidad {percent} · Cuota @ {odds}'**
  String statPickProbOdds(String percent, String odds);

  /// No description provided for @statPlayed.
  ///
  /// In es, this message translates to:
  /// **'{played} partidos'**
  String statPlayed(Object played);

  /// No description provided for @statPoints.
  ///
  /// In es, this message translates to:
  /// **'{points} puntos'**
  String statPoints(Object points);

  /// No description provided for @statPoissonNA.
  ///
  /// In es, this message translates to:
  /// **'La distribución Poisson y los marcadores probables aún no están disponibles en la entrega de este partido.'**
  String get statPoissonNA;

  /// No description provided for @statPoissonTitle.
  ///
  /// In es, this message translates to:
  /// **'Distribución de goles Poisson'**
  String get statPoissonTitle;

  /// No description provided for @statPosition.
  ///
  /// In es, this message translates to:
  /// **'Posición {position}'**
  String statPosition(Object position);

  /// No description provided for @statProbNA.
  ///
  /// In es, this message translates to:
  /// **'Probabilidades del modelo todavía no disponibles.'**
  String get statProbNA;

  /// No description provided for @statProbTitle.
  ///
  /// In es, this message translates to:
  /// **'PROBABILIDAD DE VICTORIA · 1X2'**
  String get statProbTitle;

  /// No description provided for @statPublishedPick.
  ///
  /// In es, this message translates to:
  /// **'PRONÓSTICO PUBLICADO'**
  String get statPublishedPick;

  /// No description provided for @statRadarNeeds.
  ///
  /// In es, this message translates to:
  /// **'La comparación gráfica necesita al menos tres métricas disponibles de ambos equipos.'**
  String get statRadarNeeds;

  /// No description provided for @statRadarNote.
  ///
  /// In es, this message translates to:
  /// **'Escala relativa por eje. Un área mayor no implica mayor probabilidad de ganar.'**
  String get statRadarNote;

  /// No description provided for @statResDraw.
  ///
  /// In es, this message translates to:
  /// **'E'**
  String get statResDraw;

  /// No description provided for @statResLoss.
  ///
  /// In es, this message translates to:
  /// **'P'**
  String get statResLoss;

  /// No description provided for @statResWin.
  ///
  /// In es, this message translates to:
  /// **'G'**
  String get statResWin;

  /// No description provided for @statResultsAvailable.
  ///
  /// In es, this message translates to:
  /// **'{count, plural, one{{count} resultado disponible} other{{count} resultados disponibles}}'**
  String statResultsAvailable(int count);

  /// No description provided for @statSeasonTitle.
  ///
  /// In es, this message translates to:
  /// **'Temporada y resultados recientes'**
  String get statSeasonTitle;

  /// No description provided for @statShots.
  ///
  /// In es, this message translates to:
  /// **'Remates'**
  String get statShots;

  /// No description provided for @statShotsOnTarget.
  ///
  /// In es, this message translates to:
  /// **'Remates a puerta'**
  String get statShotsOnTarget;

  /// No description provided for @statStandingNA.
  ///
  /// In es, this message translates to:
  /// **'Clasificación no disponible.'**
  String get statStandingNA;

  /// No description provided for @statSummaryTitle.
  ///
  /// In es, this message translates to:
  /// **'Resumen de predicción'**
  String get statSummaryTitle;

  /// No description provided for @statTeamStatsTitle.
  ///
  /// In es, this message translates to:
  /// **'Estadísticas del equipo'**
  String get statTeamStatsTitle;

  /// No description provided for @statWinStreak.
  ///
  /// In es, this message translates to:
  /// **'Racha de victorias'**
  String get statWinStreak;

  /// No description provided for @statXgHistoric.
  ///
  /// In es, this message translates to:
  /// **'xG histórico'**
  String get statXgHistoric;

  /// No description provided for @streamHighProb.
  ///
  /// In es, this message translates to:
  /// **'Alta probabilidad'**
  String get streamHighProb;

  /// No description provided for @streamLadder.
  ///
  /// In es, this message translates to:
  /// **'Reto Escalera'**
  String get streamLadder;

  /// No description provided for @streamParley.
  ///
  /// In es, this message translates to:
  /// **'Parley'**
  String get streamParley;

  /// Edad y país del tenista
  ///
  /// In es, this message translates to:
  /// **'{age} AÑOS · {country}'**
  String tenAgeYears(int age, String country);

  /// No description provided for @tenFormIndex.
  ///
  /// In es, this message translates to:
  /// **'ÍNDICE DE FORMA'**
  String get tenFormIndex;

  /// No description provided for @tenFormKicker.
  ///
  /// In es, this message translates to:
  /// **'// ÚLTIMOS PARTIDOS'**
  String get tenFormKicker;

  /// Diferencia de ranking entre los dos tenistas
  ///
  /// In es, this message translates to:
  /// **'{player} está {diff} puestos por encima en el ranking {circuit}.'**
  String tenGapLeader(String player, int diff, String circuit);

  /// Empate de puesto en ranking de tenis
  ///
  /// In es, this message translates to:
  /// **'{playerA} y {playerB} tienen el mismo puesto en el ranking {circuit}.'**
  String tenGapTied(String playerA, String playerB, String circuit);

  /// No description provided for @tenH2hFirstDuel.
  ///
  /// In es, this message translates to:
  /// **'PRIMER DUELO'**
  String get tenH2hFirstDuel;

  /// Explicación de primer duelo cara a cara en tenis
  ///
  /// In es, this message translates to:
  /// **'Nunca se han enfrentado. Sin historial directo, el modelo se apoya en su forma reciente y en su rendimiento sobre {surface}.'**
  String tenH2hFirstDuelDesc(String surface);

  /// Cantidad de últimos partidos en forma de tenis
  ///
  /// In es, this message translates to:
  /// **'ÚLTIMOS {count}'**
  String tenLastMatchesCount(int count);

  /// Línea de juegos esperados aproximados
  ///
  /// In es, this message translates to:
  /// **'≈ {line}'**
  String tenModelGamesExpectedApprox(String line);

  /// Explicación del cruce de juegos esperados
  ///
  /// In es, this message translates to:
  /// **'Con {line1} juegos el modelo da {p1} %; con {line2}, {p2} %: espera un partido de unos {expected} juegos.'**
  String tenModelGamesExpectedCaption(
    String line1,
    int p1,
    String line2,
    int p2,
    String expected,
  );

  /// No description provided for @tenModelGamesExpectedLabel.
  ///
  /// In es, this message translates to:
  /// **'JUEGOS ESPERADOS'**
  String get tenModelGamesExpectedLabel;

  /// Aviso simple de juegos esperados
  ///
  /// In es, this message translates to:
  /// **'El modelo espera un partido de unos {expected} juegos.'**
  String tenModelGamesExpectedSimple(String expected);

  /// Título de hándicap de juegos para un tenista
  ///
  /// In es, this message translates to:
  /// **'HÁNDICAP DE JUEGOS · {player}'**
  String tenModelHandicap(String player);

  /// Porcentaje de partido terminado en 2 sets
  ///
  /// In es, this message translates to:
  /// **'{pct}% en 2 sets'**
  String tenModelIn2Sets(int pct);

  /// Porcentaje de partido terminado en 3 sets
  ///
  /// In es, this message translates to:
  /// **'{pct}% en 3 sets'**
  String tenModelIn3Sets(int pct);

  /// No description provided for @tenModelKicker.
  ///
  /// In es, this message translates to:
  /// **'// LO QUE ESPERA EL MODELO'**
  String get tenModelKicker;

  /// No description provided for @tenModelMatchDuration.
  ///
  /// In es, this message translates to:
  /// **'DURACIÓN DEL PARTIDO'**
  String get tenModelMatchDuration;

  /// No description provided for @tenModelSet1.
  ///
  /// In es, this message translates to:
  /// **'SET 1'**
  String get tenModelSet1;

  /// No description provided for @tenModelSet2.
  ///
  /// In es, this message translates to:
  /// **'SET 2'**
  String get tenModelSet2;

  /// No description provided for @tenModelSet3.
  ///
  /// In es, this message translates to:
  /// **'SET 3'**
  String get tenModelSet3;

  /// No description provided for @tenModelSet3Footnote.
  ///
  /// In es, this message translates to:
  /// **'El 3.er set solo se juega si hay empate 1–1.'**
  String get tenModelSet3Footnote;

  /// No description provided for @tenModelSets.
  ///
  /// In es, this message translates to:
  /// **'SETS'**
  String get tenModelSets;

  /// No description provided for @tenModelTiebreak.
  ///
  /// In es, this message translates to:
  /// **'HABRÁ TIE-BREAK'**
  String get tenModelTiebreak;

  /// No description provided for @tenModelTitle.
  ///
  /// In es, this message translates to:
  /// **'MODELO'**
  String get tenModelTitle;

  /// No description provided for @tenModelTotalGames.
  ///
  /// In es, this message translates to:
  /// **'JUEGOS TOTALES · PROBABILIDAD DE «MÁS DE»'**
  String get tenModelTotalGames;

  /// Probabilidad de ganar cada set para el jugador favorito
  ///
  /// In es, this message translates to:
  /// **'{player} GANA CADA SET'**
  String tenModelWinsEachSet(String player);

  /// No description provided for @tenNavModel.
  ///
  /// In es, this message translates to:
  /// **'Modelo'**
  String get tenNavModel;

  /// No description provided for @tenNavProb.
  ///
  /// In es, this message translates to:
  /// **'Probabilidad'**
  String get tenNavProb;

  /// No description provided for @tenNavSurface.
  ///
  /// In es, this message translates to:
  /// **'Superficie'**
  String get tenNavSurface;

  /// No description provided for @tenNoStats.
  ///
  /// In es, this message translates to:
  /// **'Estadísticas de tenis no disponibles'**
  String get tenNoStats;

  /// Número de ranking individual en tenis
  ///
  /// In es, this message translates to:
  /// **'N.º {rank}'**
  String tenRankNumber(int rank);

  /// Ranking y puntos ATP/WTA
  ///
  /// In es, this message translates to:
  /// **'{rank} · {pts} pts'**
  String tenRankPts(String rank, String pts);

  /// No description provided for @tenRoundFinal.
  ///
  /// In es, this message translates to:
  /// **'Final'**
  String get tenRoundFinal;

  /// No description provided for @tenRoundQ16.
  ///
  /// In es, this message translates to:
  /// **'Dieciseisavos'**
  String get tenRoundQ16;

  /// No description provided for @tenRoundQualFinal.
  ///
  /// In es, this message translates to:
  /// **'Final de clasificación'**
  String get tenRoundQualFinal;

  /// No description provided for @tenRoundQuarterfinals.
  ///
  /// In es, this message translates to:
  /// **'Cuartos'**
  String get tenRoundQuarterfinals;

  /// No description provided for @tenRoundR128.
  ///
  /// In es, this message translates to:
  /// **'Ronda de 128'**
  String get tenRoundR128;

  /// No description provided for @tenRoundR16.
  ///
  /// In es, this message translates to:
  /// **'Octavos'**
  String get tenRoundR16;

  /// No description provided for @tenRoundR32.
  ///
  /// In es, this message translates to:
  /// **'Ronda de 32'**
  String get tenRoundR32;

  /// No description provided for @tenRoundR64.
  ///
  /// In es, this message translates to:
  /// **'Ronda de 64'**
  String get tenRoundR64;

  /// No description provided for @tenRoundSemifinals.
  ///
  /// In es, this message translates to:
  /// **'Semifinal'**
  String get tenRoundSemifinals;

  /// Rendimiento en una superficie a lo largo de la carrera
  ///
  /// In es, this message translates to:
  /// **'{surface} · CARRERA'**
  String tenSurfaceCareer(String surface);

  /// No description provided for @tenSurfaceClay.
  ///
  /// In es, this message translates to:
  /// **'TIERRA BATIDA'**
  String get tenSurfaceClay;

  /// No description provided for @tenSurfaceGrass.
  ///
  /// In es, this message translates to:
  /// **'HIERBA'**
  String get tenSurfaceGrass;

  /// No description provided for @tenSurfaceHard.
  ///
  /// In es, this message translates to:
  /// **'PISTA DURA'**
  String get tenSurfaceHard;

  /// No description provided for @tenSurfaceKicker.
  ///
  /// In es, this message translates to:
  /// **'// RENDIMIENTO POR SUPERFICIE'**
  String get tenSurfaceKicker;

  /// Rendimiento en una superficie en la temporada actual
  ///
  /// In es, this message translates to:
  /// **'{surface} · ESTA TEMPORADA'**
  String tenSurfaceSeason(String surface);

  /// No description provided for @tenSurfaceTitle.
  ///
  /// In es, this message translates to:
  /// **'SUPERFICIE'**
  String get tenSurfaceTitle;

  /// No description provided for @tenSurfaceToday.
  ///
  /// In es, this message translates to:
  /// **'HOY'**
  String get tenSurfaceToday;

  /// Porcentaje de partidos decididos a 3 sets
  ///
  /// In es, this message translates to:
  /// **'{pct}% a 3 sets'**
  String tenThreeSets(int pct);

  /// Porcentaje de partidos que tuvieron al menos un tie-break
  ///
  /// In es, this message translates to:
  /// **'{pct}% con tie-break'**
  String tenTiebreakPct(int pct);

  /// No description provided for @tenWinProbTitle.
  ///
  /// In es, this message translates to:
  /// **'PROBABILIDAD DE GANAR'**
  String get tenWinProbTitle;

  /// No description provided for @tileAllSurfaces.
  ///
  /// In es, this message translates to:
  /// **'todas las superficies'**
  String get tileAllSurfaces;

  /// No description provided for @tileBreak.
  ///
  /// In es, this message translates to:
  /// **'Quiebres logrados'**
  String get tileBreak;

  /// No description provided for @tileBtts.
  ///
  /// In es, this message translates to:
  /// **'Ambos marcan'**
  String get tileBtts;

  /// No description provided for @tileBttsCaption.
  ///
  /// In es, this message translates to:
  /// **'Partidos en que marcaron ambos: local · visita'**
  String get tileBttsCaption;

  /// No description provided for @tileConcedes.
  ///
  /// In es, this message translates to:
  /// **'Goles que encaja el rival'**
  String get tileConcedes;

  /// No description provided for @tileDraws.
  ///
  /// In es, this message translates to:
  /// **'Empates'**
  String get tileDraws;

  /// Pie de la casilla de empates con la media de la liga
  ///
  /// In es, this message translates to:
  /// **'En casa y fuera · liga {league} %'**
  String tileDrawsCaption(String league);

  /// No description provided for @tileFairOdds.
  ///
  /// In es, this message translates to:
  /// **'Cuota justa {value}'**
  String tileFairOdds(String value);

  /// No description provided for @tileFavorite.
  ///
  /// In es, this message translates to:
  /// **'Favorito 1X2'**
  String get tileFavorite;

  /// No description provided for @tileFavoriteLead.
  ///
  /// In es, this message translates to:
  /// **'{team} · +{pts} pts'**
  String tileFavoriteLead(String team, int pts);

  /// No description provided for @tileFavoriteNA.
  ///
  /// In es, this message translates to:
  /// **'Probabilidades no disponibles'**
  String get tileFavoriteNA;

  /// No description provided for @tileFormCaption.
  ///
  /// In es, this message translates to:
  /// **'Puntos: local · visita'**
  String get tileFormCaption;

  /// Etiqueta de la casilla de forma reciente
  ///
  /// In es, this message translates to:
  /// **'Forma (últ. {n})'**
  String tileFormLabel(int n);

  /// No description provided for @tileGoalsMatch.
  ///
  /// In es, this message translates to:
  /// **'Goles por partido'**
  String get tileGoalsMatch;

  /// No description provided for @tileGoalsMatchCaption.
  ///
  /// In es, this message translates to:
  /// **'Totales en sus partidos: local · visita'**
  String get tileGoalsMatchCaption;

  /// No description provided for @tileGoalsNA.
  ///
  /// In es, this message translates to:
  /// **'Historial insuficiente'**
  String get tileGoalsNA;

  /// No description provided for @tileGoalsTrend.
  ///
  /// In es, this message translates to:
  /// **'Tendencia goles'**
  String get tileGoalsTrend;

  /// No description provided for @tileH2h.
  ///
  /// In es, this message translates to:
  /// **'Cara a cara'**
  String get tileH2h;

  /// No description provided for @tileHold.
  ///
  /// In es, this message translates to:
  /// **'Saque retenido'**
  String get tileHold;

  /// No description provided for @tileHomeAway.
  ///
  /// In es, this message translates to:
  /// **'Victorias casa / fuera'**
  String get tileHomeAway;

  /// Número de partidos de cara a cara
  ///
  /// In es, this message translates to:
  /// **'{n} partidos'**
  String tileMatchesCount(int n);

  /// No description provided for @tileOver25Model.
  ///
  /// In es, this message translates to:
  /// **'Más de 2,5 según el modelo'**
  String get tileOver25Model;

  /// No description provided for @tileOver25Recent.
  ///
  /// In es, this message translates to:
  /// **'Más de 2,5 en sus últimos partidos'**
  String get tileOver25Recent;

  /// No description provided for @tilePerMatch.
  ///
  /// In es, this message translates to:
  /// **'Por partido'**
  String get tilePerMatch;

  /// No description provided for @tileProbability.
  ///
  /// In es, this message translates to:
  /// **'Probabilidad'**
  String get tileProbability;

  /// No description provided for @tileRank.
  ///
  /// In es, this message translates to:
  /// **'Ranking'**
  String get tileRank;

  /// No description provided for @tileScores.
  ///
  /// In es, this message translates to:
  /// **'Partidos con gol'**
  String get tileScores;

  /// No description provided for @tileScoresCaption.
  ///
  /// In es, this message translates to:
  /// **'Del equipo, en sus últimos partidos'**
  String get tileScoresCaption;

  /// No description provided for @tileSplitCaption.
  ///
  /// In es, this message translates to:
  /// **'Local en casa · visita fuera'**
  String get tileSplitCaption;

  /// No description provided for @tileSurfaceWins.
  ///
  /// In es, this message translates to:
  /// **'Victorias en la superficie'**
  String get tileSurfaceWins;

  /// No description provided for @tileThreeSets.
  ///
  /// In es, this message translates to:
  /// **'Partidos a tres sets'**
  String get tileThreeSets;

  /// No description provided for @tileTrendCaption.
  ///
  /// In es, this message translates to:
  /// **'Partidos con más de 2,5 goles: local · visita'**
  String get tileTrendCaption;

  /// No description provided for @tileXg.
  ///
  /// In es, this message translates to:
  /// **'xG proyectado'**
  String get tileXg;

  /// No description provided for @tileXgCaption.
  ///
  /// In es, this message translates to:
  /// **'{home} local · {away} visita'**
  String tileXgCaption(String home, String away);

  /// No description provided for @tileXgNA.
  ///
  /// In es, this message translates to:
  /// **'Disponible en mercados de goles'**
  String get tileXgNA;

  /// No description provided for @tileXgd.
  ///
  /// In es, this message translates to:
  /// **'Dif. de xG'**
  String get tileXgd;

  /// No description provided for @tileXgdCaption.
  ///
  /// In es, this message translates to:
  /// **'Por partido: local · visita'**
  String get tileXgdCaption;

  /// No description provided for @titleAsianHandicap.
  ///
  /// In es, this message translates to:
  /// **'Hándicap asiático'**
  String get titleAsianHandicap;

  /// No description provided for @titleDrawNoBet.
  ///
  /// In es, this message translates to:
  /// **'Empate no acción'**
  String get titleDrawNoBet;

  /// No description provided for @titleTeamGoals.
  ///
  /// In es, this message translates to:
  /// **'Goles de {team}'**
  String titleTeamGoals(String team);

  /// No description provided for @titleTotalCards.
  ///
  /// In es, this message translates to:
  /// **'Tarjetas totales'**
  String get titleTotalCards;

  /// No description provided for @titleTotalCorners.
  ///
  /// In es, this message translates to:
  /// **'Córners totales'**
  String get titleTotalCorners;

  /// No description provided for @titleTotalGoals.
  ///
  /// In es, this message translates to:
  /// **'Goles totales'**
  String get titleTotalGoals;

  /// No description provided for @titleWinner.
  ///
  /// In es, this message translates to:
  /// **'Ganador del partido'**
  String get titleWinner;

  /// No description provided for @tooltipVip.
  ///
  /// In es, this message translates to:
  /// **'VIP'**
  String get tooltipVip;

  /// Botón principal de desbloqueo con saldo
  ///
  /// In es, this message translates to:
  /// **'DESBLOQUEAR · {cost} MONEDAS'**
  String unlockActionCost(int cost);

  /// Etiqueta superior de saldo del usuario
  ///
  /// In es, this message translates to:
  /// **'TU SALDO'**
  String get unlockBalanceHeader;

  /// Primer beneficio del desbloqueo
  ///
  /// In es, this message translates to:
  /// **'El pronóstico, su probabilidad y la cuota'**
  String get unlockBullet1;

  /// Segundo beneficio del desbloqueo
  ///
  /// In es, this message translates to:
  /// **'Análisis, cara a cara y alertas del partido'**
  String get unlockBullet2;

  /// Tercer beneficio del desbloqueo
  ///
  /// In es, this message translates to:
  /// **'Se queda abierto para este partido'**
  String get unlockBullet3;

  /// Unidad de monedas en mayúsculas
  ///
  /// In es, this message translates to:
  /// **'MONEDAS'**
  String get unlockCoinsUnit;

  /// Etiqueta superior de costo
  ///
  /// In es, this message translates to:
  /// **'COSTO'**
  String get unlockCostHeader;

  /// Botón principal de ganar monedas cuando falta saldo
  ///
  /// In es, this message translates to:
  /// **'GANAR {count} MONEDAS'**
  String unlockEarnAction(int count);

  /// Aviso legal al pie de la hoja de desbloqueo
  ///
  /// In es, this message translates to:
  /// **'Las monedas se ganan dentro de la app. No se cobra dinero.'**
  String get unlockFooterTerms;

  /// Subtítulo de la hoja cuando no hay suficientes monedas
  ///
  /// In es, this message translates to:
  /// **'Gana monedas en unos minutos o hazte VIP'**
  String get unlockMissingSub;

  /// Título de la hoja cuando no hay suficientes monedas
  ///
  /// In es, this message translates to:
  /// **'TE FALTAN {count} MONEDAS'**
  String unlockMissingTitle(int count);

  /// Comparativa de monedas necesarias y disponibles
  ///
  /// In es, this message translates to:
  /// **'Necesitas {need} · tienes {have}'**
  String unlockNeedHave(int need, int have);

  /// Monedas restantes tras el desbloqueo
  ///
  /// In es, this message translates to:
  /// **'Te quedarán {count} monedas'**
  String unlockRemainingCoins(int count);

  /// Subtítulo de la hoja de desbloqueo cuando hay saldo
  ///
  /// In es, this message translates to:
  /// **'Se abre al instante'**
  String get unlockSheetSub;

  /// Título de la hoja de desbloqueo cuando hay saldo
  ///
  /// In es, this message translates to:
  /// **'DESBLOQUEAR PRONÓSTICO'**
  String get unlockSheetTitle;

  /// Atajo para ganar monedas con asistencia diaria
  ///
  /// In es, this message translates to:
  /// **'ASISTENCIA'**
  String get unlockShortcutAttendance;

  /// Atajo para ganar monedas con ofertas
  ///
  /// In es, this message translates to:
  /// **'OFERTAS'**
  String get unlockShortcutOffers;

  /// Atajo para ganar monedas viendo un video
  ///
  /// In es, this message translates to:
  /// **'VER UN VIDEO'**
  String get unlockShortcutVideo;

  /// Subtítulo de la tarjeta VIP sin precio
  ///
  /// In es, this message translates to:
  /// **'Sin gastar monedas'**
  String get unlockVipSubNoPrice;

  /// Subtítulo de la tarjeta VIP con precio mensual
  ///
  /// In es, this message translates to:
  /// **'Sin gastar monedas · desde {price} al mes'**
  String unlockVipSubPrice(String price);

  /// Título de la tarjeta VIP en la hoja de desbloqueo
  ///
  /// In es, this message translates to:
  /// **'O desbloquea todos con VIP'**
  String get unlockVipTitle;

  /// No description provided for @updateLater.
  ///
  /// In es, this message translates to:
  /// **'Más tarde'**
  String get updateLater;

  /// No description provided for @updateNow.
  ///
  /// In es, this message translates to:
  /// **'Actualizar ahora'**
  String get updateNow;

  /// No description provided for @updateOptional.
  ///
  /// In es, this message translates to:
  /// **'Hay una nueva versión de QuantFut disponible.'**
  String get updateOptional;

  /// No description provided for @updateRequired.
  ///
  /// In es, this message translates to:
  /// **'Actualiza QuantFut para continuar.'**
  String get updateRequired;

  /// No description provided for @updateRequiredTitle.
  ///
  /// In es, this message translates to:
  /// **'Actualiza para continuar'**
  String get updateRequiredTitle;

  /// No description provided for @updateStoreError.
  ///
  /// In es, this message translates to:
  /// **'No se pudo abrir la tienda. Inténtalo de nuevo.'**
  String get updateStoreError;

  /// No description provided for @updateTitle.
  ///
  /// In es, this message translates to:
  /// **'Actualización disponible'**
  String get updateTitle;

  /// No description provided for @updateVersion.
  ///
  /// In es, this message translates to:
  /// **'VERSIÓN'**
  String get updateVersion;

  /// No description provided for @vip7Days.
  ///
  /// In es, this message translates to:
  /// **'7 DÍAS'**
  String get vip7Days;

  /// Botón de los pronósticos bloqueados y difuminados: lleva a la compra de la suscripción VIP.
  ///
  /// In es, this message translates to:
  /// **'Acceso VIP'**
  String get vipAccessButton;

  /// No description provided for @vipActivate.
  ///
  /// In es, this message translates to:
  /// **'Activar acceso VIP'**
  String get vipActivate;

  /// No description provided for @vipActive.
  ///
  /// In es, this message translates to:
  /// **'Tu acceso VIP está activo.'**
  String get vipActive;

  /// No description provided for @vipBadge.
  ///
  /// In es, this message translates to:
  /// **'✦  ACCESO VIP'**
  String get vipBadge;

  /// No description provided for @vipBenefit1Body.
  ///
  /// In es, this message translates to:
  /// **'Cada pronóstico se sella antes del partido'**
  String get vipBenefit1Body;

  /// No description provided for @vipBenefit1Title.
  ///
  /// In es, this message translates to:
  /// **'Historial verificable'**
  String get vipBenefit1Title;

  /// No description provided for @vipBenefit2Body.
  ///
  /// In es, this message translates to:
  /// **'Todos los picks de {min} a {max} %, sin cupo gratuito'**
  String vipBenefit2Body(int min, int max);

  /// No description provided for @vipBenefit2Title.
  ///
  /// In es, this message translates to:
  /// **'Alta Probabilidad completa'**
  String get vipBenefit2Title;

  /// No description provided for @vipBenefit3Body.
  ///
  /// In es, this message translates to:
  /// **'Todos los escalones pendientes, no solo uno'**
  String get vipBenefit3Body;

  /// No description provided for @vipBenefit3Title.
  ///
  /// In es, this message translates to:
  /// **'Reto Escalera completo'**
  String get vipBenefit3Title;

  /// No description provided for @vipBenefit4Body.
  ///
  /// In es, this message translates to:
  /// **'Cuota publicada, probabilidad y xG de cada pick'**
  String get vipBenefit4Body;

  /// No description provided for @vipBenefit4Title.
  ///
  /// In es, this message translates to:
  /// **'Cuotas y análisis del partido'**
  String get vipBenefit4Title;

  /// No description provided for @vipBenefitAlertsSub.
  ///
  /// In es, this message translates to:
  /// **'Bajas y dudas antes del partido'**
  String get vipBenefitAlertsSub;

  /// No description provided for @vipBenefitAlertsTitle.
  ///
  /// In es, this message translates to:
  /// **'Análisis, H2H y alertas'**
  String get vipBenefitAlertsTitle;

  /// No description provided for @vipBenefitAllPicksSub.
  ///
  /// In es, this message translates to:
  /// **'Sin gastar monedas, en los tres deportes'**
  String get vipBenefitAllPicksSub;

  /// No description provided for @vipBenefitAllPicksTitle.
  ///
  /// In es, this message translates to:
  /// **'Todos los picks del día'**
  String get vipBenefitAllPicksTitle;

  /// No description provided for @vipBenefitCombosSub.
  ///
  /// In es, this message translates to:
  /// **'Con probabilidad conjunta y cuota'**
  String get vipBenefitCombosSub;

  /// No description provided for @vipBenefitCombosTitle.
  ///
  /// In es, this message translates to:
  /// **'Escalera y Parley completos'**
  String get vipBenefitCombosTitle;

  /// No description provided for @vipBenefitPropsSub.
  ///
  /// In es, this message translates to:
  /// **'Probabilidad, cuota y casa de apuestas'**
  String get vipBenefitPropsSub;

  /// No description provided for @vipBenefitPropsTitle.
  ///
  /// In es, this message translates to:
  /// **'Props de jugadores NBA'**
  String get vipBenefitPropsTitle;

  /// No description provided for @vipBenefitSportsBody.
  ///
  /// In es, this message translates to:
  /// **'Los mismos sellos y el mismo historial, sin suscripción'**
  String get vipBenefitSportsBody;

  /// No description provided for @vipBenefitSportsTitle.
  ///
  /// In es, this message translates to:
  /// **'NBA y tenis abiertos para todos'**
  String get vipBenefitSportsTitle;

  /// No description provided for @vipBestPrice.
  ///
  /// In es, this message translates to:
  /// **'★ MEJOR PRECIO'**
  String get vipBestPrice;

  /// No description provided for @vipCancelAnytime.
  ///
  /// In es, this message translates to:
  /// **'Cancela cuando quieras'**
  String get vipCancelAnytime;

  /// No description provided for @vipCheckAccess.
  ///
  /// In es, this message translates to:
  /// **'Comprobar mi acceso'**
  String get vipCheckAccess;

  /// No description provided for @vipCheckSignIn.
  ///
  /// In es, this message translates to:
  /// **'Inicia sesión en Perfil para comprobar tu acceso.'**
  String get vipCheckSignIn;

  /// No description provided for @vipChoosePlan.
  ///
  /// In es, this message translates to:
  /// **'ELIGE TU PLAN'**
  String get vipChoosePlan;

  /// No description provided for @vipCompareFreeHeader.
  ///
  /// In es, this message translates to:
  /// **'GRATIS'**
  String get vipCompareFreeHeader;

  /// No description provided for @vipCompareHide.
  ///
  /// In es, this message translates to:
  /// **'OCULTAR COMPARACIÓN'**
  String get vipCompareHide;

  /// No description provided for @vipCompareRow1Free.
  ///
  /// In es, this message translates to:
  /// **'10 % del día'**
  String get vipCompareRow1Free;

  /// No description provided for @vipCompareRow1Label.
  ///
  /// In es, this message translates to:
  /// **'Picks de alta probabilidad'**
  String get vipCompareRow1Label;

  /// No description provided for @vipCompareRow1Vip.
  ///
  /// In es, this message translates to:
  /// **'Todos'**
  String get vipCompareRow1Vip;

  /// No description provided for @vipCompareRow2Free.
  ///
  /// In es, this message translates to:
  /// **'Parcial'**
  String get vipCompareRow2Free;

  /// No description provided for @vipCompareRow2Label.
  ///
  /// In es, this message translates to:
  /// **'Escalera y Parley'**
  String get vipCompareRow2Label;

  /// No description provided for @vipCompareRow2Vip.
  ///
  /// In es, this message translates to:
  /// **'Completos'**
  String get vipCompareRow2Vip;

  /// No description provided for @vipCompareRow3Label.
  ///
  /// In es, this message translates to:
  /// **'Props de jugadores NBA'**
  String get vipCompareRow3Label;

  /// No description provided for @vipCompareRow4Label.
  ///
  /// In es, this message translates to:
  /// **'Análisis, H2H y alertas'**
  String get vipCompareRow4Label;

  /// No description provided for @vipCompareRow5Label.
  ///
  /// In es, this message translates to:
  /// **'Historial de aciertos'**
  String get vipCompareRow5Label;

  /// No description provided for @vipCompareRow6Free.
  ///
  /// In es, this message translates to:
  /// **'40 por pick'**
  String get vipCompareRow6Free;

  /// No description provided for @vipCompareRow6Label.
  ///
  /// In es, this message translates to:
  /// **'Desbloqueo con monedas'**
  String get vipCompareRow6Label;

  /// No description provided for @vipCompareRow6Vip.
  ///
  /// In es, this message translates to:
  /// **'No hace falta'**
  String get vipCompareRow6Vip;

  /// No description provided for @vipCompareToggle.
  ///
  /// In es, this message translates to:
  /// **'VER GRATIS VS VIP'**
  String get vipCompareToggle;

  /// No description provided for @vipCompareVipHeader.
  ///
  /// In es, this message translates to:
  /// **'VIP'**
  String get vipCompareVipHeader;

  /// No description provided for @vipDays.
  ///
  /// In es, this message translates to:
  /// **'{days, plural, one{{days} día} other{{days} días}}'**
  String vipDays(int days);

  /// No description provided for @vipDisclaimer.
  ///
  /// In es, this message translates to:
  /// **'Los pronósticos son probabilidades de un modelo estadístico: cualquier partido puede acabar distinto. Una probabilidad no es una certeza.'**
  String get vipDisclaimer;

  /// Precio mensual equivalente
  ///
  /// In es, this message translates to:
  /// **'Equivale a {price} al mes'**
  String vipEquivMonth(String price);

  /// Equivalencia mensual y diaria
  ///
  /// In es, this message translates to:
  /// **'{month} al mes · {day} al día'**
  String vipEquivMonthDay(String month, String day);

  /// No description provided for @vipFaq1A.
  ///
  /// In es, this message translates to:
  /// **'Desde Google Play › Pagos y suscripciones (o Ajustes › ID de Apple en iOS). VIP sigue activo hasta el final del periodo pagado.'**
  String get vipFaq1A;

  /// No description provided for @vipFaq1Q.
  ///
  /// In es, this message translates to:
  /// **'¿Cómo cancelo?'**
  String get vipFaq1Q;

  /// No description provided for @vipFaq2A.
  ///
  /// In es, this message translates to:
  /// **'No. Son probabilidades de un modelo estadístico; cualquier partido puede acabar distinto. Por eso el historial es público.'**
  String get vipFaq2A;

  /// No description provided for @vipFaq2Q.
  ///
  /// In es, this message translates to:
  /// **'¿Los pronósticos siempre aciertan?'**
  String get vipFaq2Q;

  /// No description provided for @vipFaq3A.
  ///
  /// In es, this message translates to:
  /// **'Muestran la cuota que publicó una casa de apuestas como referencia. En la app no se apuesta ni se mueve dinero.'**
  String get vipFaq3A;

  /// No description provided for @vipFaq3Q.
  ///
  /// In es, this message translates to:
  /// **'¿Muestran cuotas o dinero?'**
  String get vipFaq3Q;

  /// No description provided for @vipFaq4A.
  ///
  /// In es, this message translates to:
  /// **'Inicia sesión con la misma cuenta y toca «Restaurar compras».'**
  String get vipFaq4A;

  /// No description provided for @vipFaq4Q.
  ///
  /// In es, this message translates to:
  /// **'¿Cómo uso VIP en otro dispositivo?'**
  String get vipFaq4Q;

  /// No description provided for @vipFaq5A.
  ///
  /// In es, this message translates to:
  /// **'Los que tenga tu cuenta de Google Play o App Store: tarjeta, saldo o pago con operador.'**
  String get vipFaq5A;

  /// No description provided for @vipFaq5Q.
  ///
  /// In es, this message translates to:
  /// **'¿Qué métodos de pago puedo usar?'**
  String get vipFaq5Q;

  /// No description provided for @vipFaqTitle.
  ///
  /// In es, this message translates to:
  /// **'PREGUNTAS FRECUENTES'**
  String get vipFaqTitle;

  /// No description provided for @vipFreeAccess.
  ///
  /// In es, this message translates to:
  /// **'Tu cuenta tiene acceso gratuito.'**
  String get vipFreeAccess;

  /// No description provided for @vipGranted.
  ///
  /// In es, this message translates to:
  /// **'¡Listo! Tu acceso VIP está activo.'**
  String get vipGranted;

  /// No description provided for @vipHeaderTitle.
  ///
  /// In es, this message translates to:
  /// **'ACCESO VIP'**
  String get vipHeaderTitle;

  /// No description provided for @vipHeroHighlight.
  ///
  /// In es, this message translates to:
  /// **'DESBLOQUEADOS.'**
  String get vipHeroHighlight;

  /// Subtítulo de bienvenida VIP con contador total de pronósticos
  ///
  /// In es, this message translates to:
  /// **'{count} picks de fútbol, NBA y tenis, cada uno sellado antes del partido.'**
  String vipHeroSub(int count);

  /// No description provided for @vipHeroSubGeneric.
  ///
  /// In es, this message translates to:
  /// **'Picks de fútbol, NBA y tenis, cada uno sellado antes del partido.'**
  String get vipHeroSubGeneric;

  /// No description provided for @vipHeroTitle.
  ///
  /// In es, this message translates to:
  /// **'TODOS LOS PRONÓSTICOS DE HOY, '**
  String get vipHeroTitle;

  /// No description provided for @vipHistoryNote.
  ///
  /// In es, this message translates to:
  /// **'Historial público y sellado; las muestras por mercado son pequeñas y un pronóstico puede fallar.'**
  String get vipHistoryNote;

  /// No description provided for @vipIntro.
  ///
  /// In es, this message translates to:
  /// **'Desbloquea los pronósticos de Alta Probabilidad y del Reto Escalera en fútbol mientras tu suscripción esté vigente. NBA y tenis son abiertos para todos.'**
  String get vipIntro;

  /// No description provided for @vipLinked.
  ///
  /// In es, this message translates to:
  /// **'🔒  Tu acceso VIP queda vinculado a tu cuenta'**
  String get vipLinked;

  /// Fallos de pronósticos
  ///
  /// In es, this message translates to:
  /// **'{count, plural, one{1 fallo} other{{count} fallos}}'**
  String vipLostCount(int count);

  /// No description provided for @vipManage.
  ///
  /// In es, this message translates to:
  /// **'Ya tienes Plus. Cambia o cancela tu plan en la tienda.'**
  String get vipManage;

  /// No description provided for @vipMonthly.
  ///
  /// In es, this message translates to:
  /// **'≈ {amount}/mes'**
  String vipMonthly(String amount);

  /// No description provided for @vipMonths.
  ///
  /// In es, this message translates to:
  /// **'{months, plural, one{{months} mes} other{{months} meses}}'**
  String vipMonths(int months);

  /// No description provided for @vipNoExpiry.
  ///
  /// In es, this message translates to:
  /// **'Sin vencimiento'**
  String get vipNoExpiry;

  /// No description provided for @vipPaymentRequired.
  ///
  /// In es, this message translates to:
  /// **'La contratación requiere un canal de pago configurado.'**
  String get vipPaymentRequired;

  /// No description provided for @vipPending.
  ///
  /// In es, this message translates to:
  /// **'Pago pendiente. Te daremos acceso en cuanto la tienda lo confirme.'**
  String get vipPending;

  /// No description provided for @vipPerMonth.
  ///
  /// In es, this message translates to:
  /// **'al mes'**
  String get vipPerMonth;

  /// Periodo de suscripción en meses
  ///
  /// In es, this message translates to:
  /// **'cada {count} meses'**
  String vipPerMonths(int count);

  /// No description provided for @vipPerYear.
  ///
  /// In es, this message translates to:
  /// **'al año'**
  String get vipPerYear;

  /// No description provided for @vipPickLabel.
  ///
  /// In es, this message translates to:
  /// **'Pronóstico VIP'**
  String get vipPickLabel;

  /// No description provided for @vipPlansSoon.
  ///
  /// In es, this message translates to:
  /// **'Los planes se mostrarán cuando estén disponibles.'**
  String get vipPlansSoon;

  /// No description provided for @vipPricesNote.
  ///
  /// In es, this message translates to:
  /// **'Precios del catálogo del servidor.'**
  String get vipPricesNote;

  /// No description provided for @vipPrivacyPolicy.
  ///
  /// In es, this message translates to:
  /// **'Política de privacidad'**
  String get vipPrivacyPolicy;

  /// No description provided for @vipPurchasesPending.
  ///
  /// In es, this message translates to:
  /// **'Compras en preparación: aún no se cobra nada desde la app.'**
  String get vipPurchasesPending;

  /// Texto legal de renovación del plan VIP
  ///
  /// In es, this message translates to:
  /// **'Se renueva por {price} {period}. Cancela cuando quieras en {store} › Suscripciones.'**
  String vipRenewalPhrase(String price, String period, String store);

  /// No description provided for @vipRestore.
  ///
  /// In es, this message translates to:
  /// **'Restaurar compras'**
  String get vipRestore;

  /// Insignia de ahorro en planes VIP
  ///
  /// In es, this message translates to:
  /// **'AHORRA {pct}%'**
  String vipSavingsBadge(int pct);

  /// No description provided for @vipSealAppStore.
  ///
  /// In es, this message translates to:
  /// **'PAGO POR APP STORE'**
  String get vipSealAppStore;

  /// No description provided for @vipSealCancel.
  ///
  /// In es, this message translates to:
  /// **'CANCELA CUANDO QUIERAS'**
  String get vipSealCancel;

  /// No description provided for @vipSealGooglePlay.
  ///
  /// In es, this message translates to:
  /// **'PAGO POR GOOGLE PLAY'**
  String get vipSealGooglePlay;

  /// No description provided for @vipSealSealed.
  ///
  /// In es, this message translates to:
  /// **'SELLADO ANTES DEL PARTIDO'**
  String get vipSealSealed;

  /// No description provided for @vipSportsNote.
  ///
  /// In es, this message translates to:
  /// **'Cada pick sellado antes del partido. «—»: aún sin resultados para calcularlo.'**
  String get vipSportsNote;

  /// No description provided for @vipSportsTitle.
  ///
  /// In es, this message translates to:
  /// **'Acierto registrado por deporte'**
  String get vipSportsTitle;

  /// Botón principal de suscripción VIP
  ///
  /// In es, this message translates to:
  /// **'EMPEZAR VIP {plan} · {price}'**
  String vipStartCta(String plan, String price);

  /// No description provided for @vipStoreAppStore.
  ///
  /// In es, this message translates to:
  /// **'App Store'**
  String get vipStoreAppStore;

  /// No description provided for @vipStoreFailed.
  ///
  /// In es, this message translates to:
  /// **'No se pudo confirmar la compra. Lo reintentaremos al volver a abrir la app.'**
  String get vipStoreFailed;

  /// No description provided for @vipStoreGooglePlay.
  ///
  /// In es, this message translates to:
  /// **'Google Play'**
  String get vipStoreGooglePlay;

  /// No description provided for @vipStoreTerms.
  ///
  /// In es, this message translates to:
  /// **'Se renueva automáticamente al mismo precio hasta que la canceles en la tienda.'**
  String get vipStoreTerms;

  /// No description provided for @vipStoreUnavailable.
  ///
  /// In es, this message translates to:
  /// **'La tienda no está disponible en este dispositivo.'**
  String get vipStoreUnavailable;

  /// No description provided for @vipSubscribe.
  ///
  /// In es, this message translates to:
  /// **'Suscribirme'**
  String get vipSubscribe;

  /// No description provided for @vipVerifying.
  ///
  /// In es, this message translates to:
  /// **'Verificando la compra con la tienda…'**
  String get vipVerifying;

  /// No description provided for @vipWhatYouUnlock.
  ///
  /// In es, this message translates to:
  /// **'QUÉ DESBLOQUEAS'**
  String get vipWhatYouUnlock;

  /// Aciertos de pronósticos
  ///
  /// In es, this message translates to:
  /// **'{count, plural, one{1 acierto} other{{count} aciertos}}'**
  String vipWonCount(int count);

  /// No description provided for @vipYesterday.
  ///
  /// In es, this message translates to:
  /// **'AYER'**
  String get vipYesterday;

  /// No description provided for @welcome1Body.
  ///
  /// In es, this message translates to:
  /// **'Descubre el lado estadístico del deporte: partidos, análisis y pronósticos del proyecto que ya conoces en la web.'**
  String get welcome1Body;

  /// No description provided for @welcome1Title.
  ///
  /// In es, this message translates to:
  /// **'Fútbol, NBA y tenis,\ncon otra perspectiva'**
  String get welcome1Title;

  /// No description provided for @welcome2Body.
  ///
  /// In es, this message translates to:
  /// **'La forma reciente, el cara a cara y las estadísticas ayudan a entender lo que puede pasar. Empieza por los datos.'**
  String get welcome2Body;

  /// No description provided for @welcome2Title.
  ///
  /// In es, this message translates to:
  /// **'Cada partido,\ncon más contexto'**
  String get welcome2Title;

  /// No description provided for @welcome3Body.
  ///
  /// In es, this message translates to:
  /// **'Goles, córners y hándicap en fútbol, props de jugadores en la NBA y juegos en el tenis. Conoce qué mide cada análisis antes de interpretar una selección.'**
  String get welcome3Body;

  /// No description provided for @welcome3Title.
  ///
  /// In es, this message translates to:
  /// **'Más mercados.\nMás información.'**
  String get welcome3Title;

  /// No description provided for @welcome4Body.
  ///
  /// In es, this message translates to:
  /// **'Un pronóstico también se entiende después del partido. El historial permite comparar estimaciones con resultados.'**
  String get welcome4Body;

  /// No description provided for @welcome4Title.
  ///
  /// In es, this message translates to:
  /// **'Los resultados,\na la vista'**
  String get welcome4Title;

  /// No description provided for @welcome5Body.
  ///
  /// In es, this message translates to:
  /// **'Una probabilidad no es una certeza. Explora el contenido, revisa el contexto y forma tu propio criterio.'**
  String get welcome5Body;

  /// No description provided for @welcome5Title.
  ///
  /// In es, this message translates to:
  /// **'Todo empieza\npor informarte'**
  String get welcome5Title;

  /// No description provided for @welcomeGoTo.
  ///
  /// In es, this message translates to:
  /// **'Ir a bienvenida {number}'**
  String welcomeGoTo(int number);

  /// No description provided for @welcomeHistoryMatch1.
  ///
  /// In es, this message translates to:
  /// **'Mallorca – Córdoba · Más de 1,5'**
  String get welcomeHistoryMatch1;

  /// No description provided for @welcomeHistoryMatch2.
  ///
  /// In es, this message translates to:
  /// **'Fritz – Musetti · Gana Fritz'**
  String get welcomeHistoryMatch2;

  /// No description provided for @welcomeHistoryMatch3.
  ///
  /// In es, this message translates to:
  /// **'Heat – Lakers · Más de 220,5'**
  String get welcomeHistoryMatch3;

  /// No description provided for @welcomeMarket1.
  ///
  /// In es, this message translates to:
  /// **'CÓRNERS'**
  String get welcomeMarket1;

  /// No description provided for @welcomeMarket2.
  ///
  /// In es, this message translates to:
  /// **'HÁNDICAP ASIÁTICO'**
  String get welcomeMarket2;

  /// No description provided for @welcomeMarket3.
  ///
  /// In es, this message translates to:
  /// **'DOBLE OPORTUNIDAD'**
  String get welcomeMarket3;

  /// No description provided for @welcomeMarket4.
  ///
  /// In es, this message translates to:
  /// **'PROPS DE JUGADORES NBA'**
  String get welcomeMarket4;

  /// No description provided for @welcomeMarket5.
  ///
  /// In es, this message translates to:
  /// **'JUEGOS TOTALES · TENIS'**
  String get welcomeMarket5;

  /// No description provided for @welcomeMarket6.
  ///
  /// In es, this message translates to:
  /// **'AMBOS MARCAN'**
  String get welcomeMarket6;

  /// No description provided for @welcomeNext.
  ///
  /// In es, this message translates to:
  /// **'Siguiente'**
  String get welcomeNext;

  /// No description provided for @welcomeScreenOf.
  ///
  /// In es, this message translates to:
  /// **'Pantalla {page} de {total}'**
  String welcomeScreenOf(int page, int total);

  /// No description provided for @welcomeSkip.
  ///
  /// In es, this message translates to:
  /// **'Saltar'**
  String get welcomeSkip;

  /// No description provided for @welcomeStart.
  ///
  /// In es, this message translates to:
  /// **'Empezar'**
  String get welcomeStart;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) => <String>[
    'de',
    'en',
    'es',
    'fr',
    'it',
    'pt',
  ].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'de':
      return AppLocalizationsDe();
    case 'en':
      return AppLocalizationsEn();
    case 'es':
      return AppLocalizationsEs();
    case 'fr':
      return AppLocalizationsFr();
    case 'it':
      return AppLocalizationsIt();
    case 'pt':
      return AppLocalizationsPt();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
