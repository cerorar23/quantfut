"""Mensajes de la API por idioma (es, en, pt, fr, it, de).

La app envía `Accept-Language` con el idioma elegido. Los mensajes que el servidor
escribe en español (errores `HTTPException`, términos de las monedas…) se traducen aquí
con un catálogo único. Sin cabecera, o con un idioma no soportado, todo sigue en español.

Regla del proyecto: cualquier mensaje nuevo que pueda verse en la app se añade a este
catálogo con sus 5 traducciones en el mismo cambio; `tests/test_mensajes.py` lo exige
para los mensajes del código.

Orden de las traducciones en cada tupla: en, pt, fr, it, de.
"""
from __future__ import annotations

import re

IDIOMAS = ("es", "en", "pt", "fr", "it", "de")
_ORDEN = IDIOMAS[1:]

# texto en español -> (en, pt, fr, it, de)
CATALOGO: dict[str, tuple[str, str, str, str, str]] = {
    # --- monedas y desbloqueos ---
    "Asistencia desactivada": (
        "Check-in is disabled", "Presença desativada", "Pointage désactivé",
        "Presenza disattivata", "Check-in deaktiviert"),
    "Referidos desactivados": (
        "Referrals are disabled", "Indicações desativadas", "Parrainage désactivé",
        "Inviti disattivati", "Empfehlungen deaktiviert"),
    "El código se registra durante los primeros 7 días de la cuenta": (
        "The code can be registered during the first 7 days of the account",
        "O código é registrado nos primeiros 7 dias da conta",
        "Le code s'enregistre durant les 7 premiers jours du compte",
        "Il codice si registra durante i primi 7 giorni dell'account",
        "Der Code wird in den ersten 7 Tagen des Kontos registriert"),
    "Código no disponible": (
        "Code not available", "Código indisponível", "Code indisponible",
        "Codice non disponibile", "Code nicht verfügbar"),
    "No puedes usar este código": (
        "You cannot use this code", "Você não pode usar este código",
        "Vous ne pouvez pas utiliser ce code", "Non puoi usare questo codice",
        "Du kannst diesen Code nicht verwenden"),
    "Ya tienes un código registrado": (
        "You already have a registered code", "Você já tem um código registrado",
        "Vous avez déjà un code enregistré", "Hai già un codice registrato",
        "Du hast bereits einen Code registriert"),
    "Aviso no disponible": (
        "Alert not available", "Aviso indisponível", "Alerte indisponible",
        "Avviso non disponibile", "Hinweis nicht verfügbar"),
    "Desbloqueos temporalmente desactivados": (
        "Unlocks are temporarily disabled", "Desbloqueios temporariamente desativados",
        "Déblocages temporairement désactivés", "Sblocchi temporaneamente disattivati",
        "Freischaltungen vorübergehend deaktiviert"),
    "Este pronóstico no está disponible para desbloquear": (
        "This prediction is not available to unlock",
        "Este prognóstico não está disponível para desbloquear",
        "Ce pronostic n'est pas disponible au déblocage",
        "Questo pronostico non è disponibile per lo sblocco",
        "Diese Prognose kann nicht freigeschaltet werden"),
    "Proveedor todavía no configurado": (
        "Provider not configured yet", "Provedor ainda não configurado",
        "Fournisseur pas encore configuré", "Fornitore non ancora configurato",
        "Anbieter noch nicht eingerichtet"),
    "Los anuncios con recompensa no están disponibles": (
        "Rewarded ads are not available", "Os anúncios com recompensa não estão disponíveis",
        "Les publicités avec récompense ne sont pas disponibles",
        "Le pubblicità con ricompensa non sono disponibili",
        "Anzeigen mit Belohnung sind nicht verfügbar"),
    "Anuncios no disponibles en este dispositivo": (
        "Ads are not available on this device", "Anúncios indisponíveis neste dispositivo",
        "Publicités indisponibles sur cet appareil",
        "Pubblicità non disponibili su questo dispositivo",
        "Anzeigen sind auf diesem Gerät nicht verfügbar"),
    "Ya tienes un anuncio en curso": (
        "You already have an ad in progress", "Você já tem um anúncio em andamento",
        "Vous avez déjà une publicité en cours", "Hai già una pubblicità in corso",
        "Du hast bereits eine laufende Anzeige"),
    "Has alcanzado el límite de anuncios de hoy": (
        "You've reached today's ad limit", "Você atingiu o limite de anúncios de hoje",
        "Vous avez atteint la limite de publicités du jour",
        "Hai raggiunto il limite di pubblicità di oggi",
        "Du hast das Anzeigenlimit für heute erreicht"),
    "Espera un momento antes del siguiente anuncio": (
        "Wait a moment before the next ad", "Aguarde um momento antes do próximo anúncio",
        "Patientez un instant avant la prochaine publicité",
        "Attendi un momento prima della prossima pubblicità",
        "Warte einen Moment bis zur nächsten Anzeige"),
    "Inicia sesión para usar monedas": (
        "Sign in to use coins", "Inicie sessão para usar moedas",
        "Connectez-vous pour utiliser les pièces", "Accedi per usare le monete",
        "Melde dich an, um Münzen zu nutzen"),
    "Verifica tu correo antes de usar monedas": (
        "Verify your email before using coins", "Verifique seu e-mail antes de usar moedas",
        "Vérifiez votre e-mail avant d'utiliser les pièces",
        "Verifica la tua e-mail prima di usare le monete",
        "Bestätige deine E-Mail, bevor du Münzen nutzt"),
    "No tienes monedas suficientes": (
        "You do not have enough coins", "Você não tem moedas suficientes",
        "Vous n'avez pas assez de pièces", "Non hai monete sufficienti",
        "Du hast nicht genug Münzen"),
    "Configuración de monedas pendiente de instalar": (
        "Coins configuration pending installation",
        "Configuração de moedas pendente de instalação",
        "Configuration des pièces en attente d'installation",
        "Configurazione delle monete in attesa di installazione",
        "Münzkonfiguration noch nicht installiert"),
    "Recompensas temporalmente no disponibles": (
        "Rewards are temporarily unavailable", "Recompensas temporariamente indisponíveis",
        "Récompenses temporairement indisponibles", "Ricompense temporaneamente non disponibili",
        "Belohnungen vorübergehend nicht verfügbar"),
    ("Monedas sin valor monetario: canjeables solo por pronósticos. "
     "Las ofertas dependen del país y se acreditan tras la confirmación del proveedor. "
     "Una oferta anulada revierte sus monedas. La asistencia usa días UTC. "
     "Los referidos se premian una vez, después de verificar el correo y completar "
     "ofertas confirmadas por el mínimo indicado. No se premian reseñas."): (
        "Coins have no monetary value: they can only be redeemed for predictions. "
        "Offers depend on your country and are credited after the provider confirms them. "
        "A voided offer reverses its coins. Check-in uses UTC days. "
        "Referrals are rewarded once, after verifying the email and completing "
        "confirmed offers for the stated minimum. Reviews are not rewarded.",
        "As moedas não têm valor monetário: só podem ser trocadas por prognósticos. "
        "As ofertas dependem do país e são creditadas após a confirmação do provedor. "
        "Uma oferta anulada reverte suas moedas. A presença usa dias UTC. "
        "As indicações são premiadas uma vez, após verificar o e-mail e concluir "
        "ofertas confirmadas pelo mínimo indicado. Avaliações não são premiadas.",
        "Les pièces n'ont aucune valeur monétaire : elles ne sont échangeables que contre des pronostics. "
        "Les offres dépendent du pays et sont créditées après confirmation du fournisseur. "
        "Une offre annulée annule ses pièces. Le pointage utilise des jours UTC. "
        "Le parrainage est récompensé une seule fois, après vérification de l'e-mail et "
        "offres confirmées pour le minimum indiqué. Les avis ne sont pas récompensés.",
        "Le monete non hanno valore monetario: si possono scambiare solo con pronostici. "
        "Le offerte dipendono dal paese e vengono accreditate dopo la conferma del fornitore. "
        "Un'offerta annullata ripristina le sue monete. La presenza usa giorni UTC. "
        "Gli inviti vengono premiati una sola volta, dopo la verifica dell'e-mail e il "
        "completamento di offerte confermate per il minimo indicato. Le recensioni non sono premiate.",
        "Münzen haben keinen Geldwert: Sie sind nur gegen Prognosen einlösbar. "
        "Angebote hängen vom Land ab und werden nach Bestätigung des Anbieters gutgeschrieben. "
        "Ein storniertes Angebot macht seine Münzen rückgängig. Das Einchecken nutzt UTC-Tage. "
        "Empfehlungen werden einmal belohnt, nach E-Mail-Bestätigung und bestätigten "
        "Angeboten im angegebenen Mindestumfang. Bewertungen werden nicht belohnt."),
    # --- partidos y modelo ---
    "Partido no encontrado": (
        "Match not found", "Partida não encontrada", "Match introuvable",
        "Partita non trovata", "Spiel nicht gefunden"),
    "Sin cuotas 1X2 para este partido": (
        "No 1X2 odds for this match", "Sem odds 1X2 para esta partida",
        "Pas de cotes 1X2 pour ce match", "Nessuna quota 1X2 per questa partita",
        "Keine 1X2-Quoten für dieses Spiel"),
    "Todavía no hay predicción para ese partido": (
        "There is no prediction for that match yet", "Ainda não há prognóstico para essa partida",
        "Il n'y a pas encore de pronostic pour ce match",
        "Non c'è ancora un pronostico per quella partita",
        "Für dieses Spiel gibt es noch keine Prognose"),
    "Ese equipo no existe en esa liga": (
        "That team does not exist in that league", "Essa equipe não existe nessa liga",
        "Cette équipe n'existe pas dans cette ligue", "Quella squadra non esiste in quel campionato",
        "Dieses Team gibt es in dieser Liga nicht"),
    "Configuración móvil pendiente de instalar": (
        "Mobile configuration pending installation", "Configuração móvel pendente de instalação",
        "Configuration mobile en attente d'installation",
        "Configurazione mobile in attesa di installazione",
        "Mobile Konfiguration noch nicht installiert"),
    "Error interno": (
        "Internal error", "Erro interno", "Erreur interne", "Errore interno", "Interner Fehler"),
    # --- cuentas y acceso ---
    "Correo no válido": (
        "Invalid email", "E-mail inválido", "E-mail invalide", "E-mail non valida",
        "Ungültige E-Mail"),
    "Ya existe una cuenta con ese correo": (
        "An account with that email already exists", "Já existe uma conta com esse e-mail",
        "Un compte existe déjà avec cet e-mail", "Esiste già un account con quell'e-mail",
        "Es gibt bereits ein Konto mit dieser E-Mail"),
    "Sesión no válida": (
        "Invalid session", "Sessão inválida", "Session invalide", "Sessione non valida",
        "Ungültige Sitzung"),
    "Estado no válido": (
        "Invalid status", "Estado inválido", "Statut invalide", "Stato non valido",
        "Ungültiger Status"),
    "El enlace no es válido o ha caducado": (
        "The link is invalid or has expired", "O link é inválido ou expirou",
        "Le lien est invalide ou a expiré", "Il link non è valido o è scaduto",
        "Der Link ist ungültig oder abgelaufen"),
    "Correo o contraseña incorrectos": (
        "Incorrect email or password", "E-mail ou senha incorretos",
        "E-mail ou mot de passe incorrect", "E-mail o password errati",
        "E-Mail oder Passwort falsch"),
    "Cuenta suspendida": (
        "Account suspended", "Conta suspensa", "Compte suspendu", "Account sospeso",
        "Konto gesperrt"),
    "Las cuentas todavía no están abiertas": (
        "Accounts are not open yet", "As contas ainda não estão abertas",
        "Les comptes ne sont pas encore ouverts", "Gli account non sono ancora aperti",
        "Konten sind noch nicht geöffnet"),
    "Demasiados intentos, espera un momento": (
        "Too many attempts, please wait a moment", "Muitas tentativas, aguarde um momento",
        "Trop de tentatives, veuillez patienter", "Troppi tentativi, attendi un momento",
        "Zu viele Versuche, bitte warte einen Moment"),
    "El envío de correo no está disponible": (
        "Email sending is not available", "O envio de e-mail não está disponível",
        "L'envoi d'e-mails n'est pas disponible", "L'invio delle e-mail non è disponibile",
        "Der E-Mail-Versand ist nicht verfügbar"),
    "Ya enviamos varios enlaces; revisa tu correo": (
        "We already sent several links; check your email",
        "Já enviamos vários links; verifique seu e-mail",
        "Nous avons déjà envoyé plusieurs liens ; vérifiez votre e-mail",
        "Abbiamo già inviato diversi link; controlla la tua e-mail",
        "Wir haben bereits mehrere Links gesendet; prüfe deine E-Mail"),
    "Actualiza la app para continuar": (
        "Update the app to continue", "Atualize o app para continuar",
        "Mettez à jour l'application pour continuer", "Aggiorna l'app per continuare",
        "Aktualisiere die App, um fortzufahren"),
    "No se pudo comprobar esta instalación": (
        "This installation could not be verified", "Não foi possível verificar esta instalação",
        "Impossible de vérifier cette installation", "Impossibile verificare questa installazione",
        "Diese Installation konnte nicht überprüft werden"),
    "Inicia sesión": (
        "Sign in", "Inicie sessão", "Connectez-vous", "Accedi", "Melde dich an"),
    "Vuelve a iniciar sesión": (
        "Please sign in again", "Inicie sessão novamente", "Reconnectez-vous",
        "Accedi di nuovo", "Bitte melde dich erneut an"),
    "La vinculación requiere la sesión de la cuenta existente": (
        "Linking requires a session of the existing account",
        "A vinculação requer a sessão da conta existente",
        "L'association nécessite la session du compte existant",
        "Il collegamento richiede la sessione dell'account esistente",
        "Die Verknüpfung erfordert die Sitzung des bestehenden Kontos"),
    "Accede de nuevo a tu cuenta existente": (
        "Sign in again to your existing account", "Acesse novamente sua conta existente",
        "Reconnectez-vous à votre compte existant", "Accedi di nuovo al tuo account esistente",
        "Melde dich erneut bei deinem bestehenden Konto an"),
    "Activa las notificaciones primero": (
        "Turn on notifications first", "Ative as notificações primeiro",
        "Activez d'abord les notifications", "Attiva prima le notifiche",
        "Aktiviere zuerst die Benachrichtigungen"),
    "El acceso con Google todavía no está disponible": (
        "Google sign-in is not available yet", "O acesso com o Google ainda não está disponível",
        "La connexion avec Google n'est pas encore disponible",
        "L'accesso con Google non è ancora disponibile",
        "Die Anmeldung mit Google ist noch nicht verfügbar"),
    "La sesión caducó. Vuelve a iniciar sesión": (
        "Your session expired. Please sign in again", "A sessão expirou. Inicie sessão novamente",
        "La session a expiré. Reconnectez-vous", "La sessione è scaduta. Accedi di nuovo",
        "Die Sitzung ist abgelaufen. Bitte melde dich erneut an"),
    "No se pudo comprobar la sesión. Inténtalo de nuevo": (
        "The session could not be verified. Please try again",
        "Não foi possível verificar a sessão. Tente novamente",
        "Impossible de vérifier la session. Veuillez réessayer",
        "Impossibile verificare la sessione. Riprova",
        "Die Sitzung konnte nicht überprüft werden. Bitte versuche es erneut"),
    "Verifica tu correo antes de continuar": (
        "Verify your email before continuing", "Verifique seu e-mail antes de continuar",
        "Vérifiez votre e-mail avant de continuer", "Verifica la tua e-mail prima di continuare",
        "Bestätige deine E-Mail, bevor du fortfährst"),
    "Esta cuenta no está disponible": (
        "This account is not available", "Esta conta não está disponível",
        "Ce compte n'est pas disponible", "Questo account non è disponibile",
        "Dieses Konto ist nicht verfügbar"),
    "Google ya está vinculado a otra cuenta": (
        "Google is already linked to another account", "O Google já está vinculado a outra conta",
        "Google est déjà associé à un autre compte", "Google è già collegato a un altro account",
        "Google ist bereits mit einem anderen Konto verknüpft"),
    "Acepta los términos y la política de privacidad": (
        "Accept the terms and the privacy policy", "Aceite os termos e a política de privacidade",
        "Acceptez les conditions et la politique de confidentialité",
        "Accetta i termini e l'informativa sulla privacy",
        "Akzeptiere die Nutzungsbedingungen und die Datenschutzerklärung"),
    "La cuenta ya tiene otra identidad Google": (
        "The account already has another Google identity",
        "A conta já tem outra identidade Google", "Le compte a déjà une autre identité Google",
        "L'account ha già un'altra identità Google",
        "Das Konto hat bereits eine andere Google-Identität"),
    "Accede a tu cuenta existente para vincular Google": (
        "Sign in to your existing account to link Google",
        "Acesse sua conta existente para vincular o Google",
        "Connectez-vous à votre compte existant pour associer Google",
        "Accedi al tuo account esistente per collegare Google",
        "Melde dich bei deinem bestehenden Konto an, um Google zu verknüpfen"),
}

# Mensajes con números: plantilla en español con {nombre} -> traducciones con los mismos.
PATRONES: dict[str, tuple[str, str, str, str, str]] = {
    "La contraseña debe tener entre {a} y {b} caracteres": (
        "The password must be between {a} and {b} characters",
        "A senha deve ter entre {a} e {b} caracteres",
        "Le mot de passe doit contenir entre {a} et {b} caractères",
        "La password deve avere tra {a} e {b} caratteri",
        "Das Passwort muss zwischen {a} und {b} Zeichen lang sein"),
}

_REGEX = {
    re.compile("^" + re.sub(r"\\\{(\w+)\\\}", r"(?P<\1>.+?)", re.escape(es)) + "$"): tr
    for es, tr in PATRONES.items()
}


def idioma(accept_language: str | None) -> str:
    """Primer idioma soportado de la cabecera `Accept-Language` (por defecto, español)."""
    if not accept_language:
        return "es"
    for parte in accept_language.split(","):
        codigo = parte.split(";")[0].strip().lower().split("-")[0]
        if codigo in IDIOMAS:
            return codigo
    return "es"


def traducir(texto: str, lang: str) -> str:
    """Traduce un mensaje conocido; si no está en el catálogo, lo devuelve igual."""
    if lang == "es" or lang not in _ORDEN:
        return texto
    i = _ORDEN.index(lang)
    if texto in CATALOGO:
        return CATALOGO[texto][i]
    for patron, tr in _REGEX.items():
        m = patron.match(texto)
        if m:
            return tr[i].format(**m.groupdict())
    return texto


def traducir_detalle(detalle, lang: str):
    """`detail` de un error: texto o `{'code':…, 'message':…}`."""
    if isinstance(detalle, str):
        return traducir(detalle, lang)
    if isinstance(detalle, dict) and isinstance(detalle.get("message"), str):
        return {**detalle, "message": traducir(detalle["message"], lang)}
    return detalle
