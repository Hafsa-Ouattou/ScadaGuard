
import os
import ssl
import smtplib
import threading
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

EXPEDITEUR = os.environ.get("SCADAGUARD_EMAIL_EXPEDITEUR", "scadaguard.alertes@gmail.com")
MOT_DE_PASSE = os.environ.get("SCADAGUARD_EMAIL_MOT_DE_PASSE", "").strip()
DESTINATAIRES = [d.strip() for d in os.environ.get("SCADAGUARD_EMAIL_DESTINATAIRE", "").split(",") if d.strip()]
SEUIL_NIVEAU = os.environ.get("SCADAGUARD_EMAIL_SEUIL", "CRITIQUE").upper()
COOLDOWN_SECONDES = int(os.environ.get("SCADAGUARD_EMAIL_COOLDOWN", "30"))

SERVEUR_SMTP = "smtp.gmail.com"
PORT_SMTP = 587

_NIVEAUX_ORDRE = {"INFO": 0, "SUSPECT": 1, "CRITIQUE": 2}

_dernier_envoi = 0.0
_verrou = threading.Lock()


def est_configure():
    """True si le module a de quoi envoyer un email (mot de passe + au moins un destinataire)."""
    return bool(MOT_DE_PASSE) and bool(DESTINATAIRES)


def _doit_alerter(niveau):
    return _NIVEAUX_ORDRE.get(niveau, 0) >= _NIVEAUX_ORDRE.get(SEUIL_NIVEAU, 2)


def _construire_message(niveau, module, message):
    sujet = f"🚨 SCADAGuard — Alerte {niveau} ({module})"
    corps = (
        f"Une alerte de sécurité a été détectée sur le poste de télégestion.\n\n"
        f"Niveau     : {niveau}\n"
        f"Module     : {module}\n"
        f"Détail     : {message}\n\n"
        f"— Ceci est un message automatique envoyé par SCADAGuard (ONEE - Branche Eau).\n"
        f"Ne pas répondre à cet email."
    )
    msg = MIMEMultipart()
    msg["From"] = EXPEDITEUR
    msg["To"] = ", ".join(DESTINATAIRES)
    msg["Subject"] = sujet
    msg.attach(MIMEText(corps, "plain", "utf-8"))
    return msg


def _creer_contexte_ssl():
    
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _envoyer_maintenant(niveau, module, message):
    msg = _construire_message(niveau, module, message)
    contexte = _creer_contexte_ssl()
    with smtplib.SMTP(SERVEUR_SMTP, PORT_SMTP, timeout=15) as serveur:
        serveur.starttls(context=contexte)
        serveur.login(EXPEDITEUR, MOT_DE_PASSE)
        serveur.sendmail(EXPEDITEUR, DESTINATAIRES, msg.as_string())


def envoyer_alerte_email_async(niveau, module, message):
  
    if not est_configure() or not _doit_alerter(niveau):
        return

    global _dernier_envoi
    with _verrou:
        maintenant = time.time()
        if maintenant - _dernier_envoi < COOLDOWN_SECONDES:
            return
        _dernier_envoi = maintenant

    def _tache():
        try:
            _envoyer_maintenant(niveau, module, message)
            print(f"[email] alerte envoyée à {', '.join(DESTINATAIRES)} : {niveau}/{module}")
        except Exception as erreur:
            print(f"[email] ÉCHEC d'envoi de l'alerte : {erreur}")

    threading.Thread(target=_tache, daemon=True).start()


def envoyer_email_test():
    
    if not MOT_DE_PASSE:
        return False, "Mot de passe d'application manquant (SCADAGUARD_EMAIL_MOT_DE_PASSE)."
    if not DESTINATAIRES:
        return False, "Aucun destinataire configuré (SCADAGUARD_EMAIL_DESTINATAIRE)."
    try:
        _envoyer_maintenant(
            "TEST", "Système",
            "Ceci est un email de test envoyé depuis SCADAGuard. "
            "Si vous recevez ce message, la configuration des notifications est correcte."
        )
        return True, f"Email de test envoyé à {', '.join(DESTINATAIRES)}."
    except smtplib.SMTPAuthenticationError:
        return False, ("Authentification refusée par Gmail. Vérifie que tu utilises bien un "
                        "mot de passe D'APPLICATION (pas le mot de passe normal du compte).")
    except Exception as erreur:
        return False, f"Échec de l'envoi : {erreur}"
