import json
import os
import datetime
import time
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash

FICHIER_UTILISATEURS = "users.json"
FICHIER_AUDIT = "audit_log.csv"

MAX_TENTATIVES = 3            # nombre d'échecs avant blocage
DUREE_BLOCAGE_SECONDES = 60   # durée du blocage temporaire

_tentatives_echouees = {}



_ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=2,
)


def _hacher_mot_de_passe(mot_de_passe):
    return _ph.hash(mot_de_passe)


def _verifier_mot_de_passe(hachage, mot_de_passe):
    try:
        return _ph.verify(hachage, mot_de_passe)
    except (VerifyMismatchError, InvalidHash):
        return False



def _charger_utilisateurs():
    if not os.path.exists(FICHIER_UTILISATEURS):
        return {}
    with open(FICHIER_UTILISATEURS, "r", encoding="utf-8") as f:
        return json.load(f)


def _sauvegarder_utilisateurs(utilisateurs):
    with open(FICHIER_UTILISATEURS, "w", encoding="utf-8") as f:
        json.dump(utilisateurs, f, indent=2, ensure_ascii=False)


def creer_utilisateur(nom_utilisateur, mot_de_passe, role="agent"):
    utilisateurs = _charger_utilisateurs()
    hachage = _hacher_mot_de_passe(mot_de_passe)
    utilisateurs[nom_utilisateur] = {"hash": hachage, "role": role}
    _sauvegarder_utilisateurs(utilisateurs)



def _enregistrer_audit(nom_utilisateur, action, resultat):
    entete_necessaire = not os.path.exists(FICHIER_AUDIT)
    with open(FICHIER_AUDIT, "a", encoding="utf-8") as f:
        if entete_necessaire:
            f.write("horodatage,utilisateur,action,resultat\n")
        horodatage = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{horodatage},{nom_utilisateur},{action},{resultat}\n")


def enregistrer_action(nom_utilisateur, action):
    _enregistrer_audit(nom_utilisateur, action, "effectuée")



def compte_bloque(nom_utilisateur):
    info = _tentatives_echouees.get(nom_utilisateur)
    if not info:
        return False, 0
    nb_echecs, dernier_echec = info
    if nb_echecs >= MAX_TENTATIVES:
        temps_ecoule = time.time() - dernier_echec
        if temps_ecoule < DUREE_BLOCAGE_SECONDES:
            return True, int(DUREE_BLOCAGE_SECONDES - temps_ecoule)
        _tentatives_echouees.pop(nom_utilisateur, None)
    return False, 0


def _enregistrer_tentative_echouee(nom_utilisateur):
    nb_echecs, _ = _tentatives_echouees.get(nom_utilisateur, (0, 0))
    _tentatives_echouees[nom_utilisateur] = (nb_echecs + 1, time.time())


def verifier_connexion(nom_utilisateur, mot_de_passe):
    """Retourne (succes: bool, message: str, role: str|None)"""
    bloque, temps_restant = compte_bloque(nom_utilisateur)
    if bloque:
        _enregistrer_audit(nom_utilisateur, "connexion",
                            f"refusée (compte bloqué, {temps_restant}s restantes)")
        return False, f"Trop de tentatives échouées. Réessayez dans {temps_restant}s.", None

    utilisateurs = _charger_utilisateurs()
    entree = utilisateurs.get(nom_utilisateur)

    if entree is None:
        _enregistrer_tentative_echouee(nom_utilisateur)
        _enregistrer_audit(nom_utilisateur, "connexion", "échec (utilisateur inconnu)")
        return False, "Nom d'utilisateur ou mot de passe incorrect.", None

    if _verifier_mot_de_passe(entree["hash"], mot_de_passe):
        _tentatives_echouees.pop(nom_utilisateur, None)
        _enregistrer_audit(nom_utilisateur, "connexion", "réussie")

        if _ph.check_needs_rehash(entree["hash"]):
            utilisateurs = _charger_utilisateurs()
            utilisateurs[nom_utilisateur]["hash"] = _hacher_mot_de_passe(mot_de_passe)
            _sauvegarder_utilisateurs(utilisateurs)

        return True, "Connexion réussie.", entree["role"]
    else:
        _enregistrer_tentative_echouee(nom_utilisateur)
        _enregistrer_audit(nom_utilisateur, "connexion", "échec (mot de passe incorrect)")
        return False, "Nom d'utilisateur ou mot de passe incorrect.", None
