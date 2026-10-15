"""
Página de invitación `/i/CODIGO` (2026-10-14): a donde lleva el enlace que la app comparte
junto al código de referido. Muestra el código y cómo usarlo, en el idioma del navegador
(es, en, pt, fr, it, de). Pública y SIN base de datos: no comprueba si el código existe ni lee
premios, así que no sirve para enumerar códigos y no depende de la configuración de monedas
(las cantidades las enseña la app). El código no se registra desde aquí: se escribe o pega en
Coins, dentro de los primeros 7 días de la cuenta (`rewards.referral`).
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..config import settings
from .mensajes import idioma
from .panel import CSP, ENV

router = APIRouter(include_in_schema=False)

# Los códigos son hexadecimales de 12 caracteres (`rewards.wallet`); se admite más margen.
CODIGO = re.compile(r"^[A-Za-z0-9]{6,24}$")

TEXTOS: dict[str, dict[str, str]] = {
    "es": {
        "titulo": "Te invitaron a QuantFut",
        "intro": "Un amigo te comparte su código de invitación.",
        "tu_codigo": "Código de invitación", "copiar": "Copiar código", "copiado": "Copiado",
        "como": "Cómo usarlo",
        "paso1": "Abre la app QuantFut y crea tu cuenta.",
        "paso2": "Verifica tu correo.",
        "paso3": "Ve a Coins, escribe o pega el código en «Código de quien te invitó» y toca «Registrar código». Tienes los primeros 7 días de tu cuenta.",
        "paso4": "Cuando completes ofertas confirmadas, tú y quien te invitó reciben monedas.",
        "descargar": "Descargar la app", "web": "Conocer QuantFut",
        "invalido_titulo": "Enlace de invitación no válido",
        "invalido_texto": "Este enlace no trae un código válido. Pide a tu amigo que lo comparta otra vez desde la app.",
    },
    "en": {
        "titulo": "You have been invited to QuantFut",
        "intro": "A friend is sharing their invitation code with you.",
        "tu_codigo": "Invitation code", "copiar": "Copy code", "copiado": "Copied",
        "como": "How to use it",
        "paso1": "Open the QuantFut app and create your account.",
        "paso2": "Verify your email.",
        "paso3": "Go to Coins, type or paste the code in “Code of who invited you” and tap “Register code”. You have the first 7 days of your account.",
        "paso4": "When you complete confirmed offers, you and the person who invited you receive coins.",
        "descargar": "Download the app", "web": "Learn about QuantFut",
        "invalido_titulo": "Invalid invitation link",
        "invalido_texto": "This link does not carry a valid code. Ask your friend to share it again from the app.",
    },
    "pt": {
        "titulo": "Você foi convidado para o QuantFut",
        "intro": "Um amigo está compartilhando o código de convite dele com você.",
        "tu_codigo": "Código de convite", "copiar": "Copiar código", "copiado": "Copiado",
        "como": "Como usar",
        "paso1": "Abra o app QuantFut e crie sua conta.",
        "paso2": "Verifique seu e-mail.",
        "paso3": "Vá em Coins, digite ou cole o código em “Código de quem convidou você” e toque em “Registrar código”. Você tem os primeiros 7 dias da sua conta.",
        "paso4": "Quando você concluir ofertas confirmadas, você e quem convidou recebem moedas.",
        "descargar": "Baixar o app", "web": "Conhecer o QuantFut",
        "invalido_titulo": "Link de convite inválido",
        "invalido_texto": "Este link não traz um código válido. Peça ao seu amigo para compartilhar de novo pelo app.",
    },
    "fr": {
        "titulo": "Vous êtes invité sur QuantFut",
        "intro": "Un ami partage avec vous son code d'invitation.",
        "tu_codigo": "Code d'invitation", "copiar": "Copier le code", "copiado": "Copié",
        "como": "Comment l'utiliser",
        "paso1": "Ouvrez l'application QuantFut et créez votre compte.",
        "paso2": "Vérifiez votre e-mail.",
        "paso3": "Allez dans Coins, saisissez ou collez le code dans « Code de la personne qui vous a invité » puis touchez « Enregistrer le code ». Vous avez les 7 premiers jours de votre compte.",
        "paso4": "Quand vous terminez des offres confirmées, vous et la personne qui vous a invité recevez des pièces.",
        "descargar": "Télécharger l'application", "web": "Découvrir QuantFut",
        "invalido_titulo": "Lien d'invitation non valide",
        "invalido_texto": "Ce lien ne contient pas de code valide. Demandez à votre ami de le partager à nouveau depuis l'application.",
    },
    "it": {
        "titulo": "Sei stato invitato su QuantFut",
        "intro": "Un amico condivide con te il suo codice invito.",
        "tu_codigo": "Codice invito", "copiar": "Copia codice", "copiado": "Copiato",
        "como": "Come usarlo",
        "paso1": "Apri l'app QuantFut e crea il tuo account.",
        "paso2": "Verifica la tua email.",
        "paso3": "Vai in Coins, scrivi o incolla il codice in «Codice di chi ti ha invitato» e tocca «Registra codice». Hai i primi 7 giorni del tuo account.",
        "paso4": "Quando completi offerte confermate, tu e chi ti ha invitato ricevete monete.",
        "descargar": "Scarica l'app", "web": "Scopri QuantFut",
        "invalido_titulo": "Link di invito non valido",
        "invalido_texto": "Questo link non contiene un codice valido. Chiedi al tuo amico di condividerlo di nuovo dall'app.",
    },
    "de": {
        "titulo": "Du wurdest zu QuantFut eingeladen",
        "intro": "Ein Freund teilt seinen Einladungscode mit dir.",
        "tu_codigo": "Einladungscode", "copiar": "Code kopieren", "copiado": "Kopiert",
        "como": "So funktioniert es",
        "paso1": "Öffne die QuantFut-App und erstelle dein Konto.",
        "paso2": "Bestätige deine E-Mail-Adresse.",
        "paso3": "Gehe zu Coins, gib den Code bei „Code der Person, die dich eingeladen hat“ ein oder füge ihn ein und tippe auf „Code registrieren“. Du hast die ersten 7 Tage deines Kontos.",
        "paso4": "Wenn du bestätigte Angebote abschließt, erhalten du und die einladende Person Münzen.",
        "descargar": "App herunterladen", "web": "QuantFut kennenlernen",
        "invalido_titulo": "Ungültiger Einladungslink",
        "invalido_texto": "Dieser Link enthält keinen gültigen Code. Bitte deinen Freund, ihn erneut aus der App zu teilen.",
    },
}


@router.get("/i/{code}")
def invitacion(code: str, request: Request):
    lang = idioma(request.headers.get("accept-language"))
    valido = bool(CODIGO.match(code))
    html = ENV.get_template("cuenta/invitacion.html").render(
        t=TEXTOS[lang], lang=lang, codigo=code.upper() if valido else None,
        descargar=settings.app_download_url)
    return HTMLResponse(html, status_code=200 if valido else 404,
                        headers={"Cache-Control": "no-store", "Content-Security-Policy": CSP,
                                 "X-Robots-Tag": "noindex, nofollow", "Referrer-Policy": "no-referrer"})
