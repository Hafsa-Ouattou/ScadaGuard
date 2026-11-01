
import os
import time
import random

DOSSIER = "dossier_surveille"
NB_FICHIERS = 12
PAUSE_ENTRE_ETAPES = 2       # secondes de pause entre chaque étape (lisibilité de la démo)
PAUSE_ENTRE_FICHIERS = 0.15  # secondes entre chaque fichier d'une même étape

os.makedirs(DOSSIER, exist_ok=True)


def etape(titre):
    print(f"\n{'=' * 60}\n{titre}\n{'=' * 60}")


def chemin(nom):
    return os.path.join(DOSSIER, nom)



etape("Étape 1/4 — Dépôt de documents de travail simulés")
noms_fichiers = [f"rapport_service_{i}.txt" for i in range(NB_FICHIERS)]

for nom in noms_fichiers:
    with open(chemin(nom), "w", encoding="utf-8") as f:
        f.write(f"Document de travail — contenu original numéro {nom}\n")
    print(f"  créé : {nom}")
    time.sleep(PAUSE_ENTRE_FICHIERS)

time.sleep(PAUSE_ENTRE_ETAPES)


etape("Étape 2/4 — « Chiffrement » simulé du contenu des fichiers")
for nom in noms_fichiers:
    contenu_simule = "".join(random.choice("ABCDEF0123456789") for _ in range(200))
    with open(chemin(nom), "w", encoding="utf-8") as f:
        f.write(contenu_simule)
    print(f"  contenu réécrit : {nom}")
    time.sleep(PAUSE_ENTRE_FICHIERS)

time.sleep(PAUSE_ENTRE_ETAPES)

etape("Étape 3/4 — Renommage avec extension .locked")
noms_verrouilles = []
for nom in noms_fichiers:
    nouveau_nom = nom + ".locked"
    os.rename(chemin(nom), chemin(nouveau_nom))
    noms_verrouilles.append(nouveau_nom)
    print(f"  renommé : {nom} → {nouveau_nom}")
    time.sleep(PAUSE_ENTRE_FICHIERS)

time.sleep(PAUSE_ENTRE_ETAPES)


etape("Étape 4/4 — Suppression partielle + dépôt de la note de rançon")
for nom in noms_verrouilles[:NB_FICHIERS // 2]:
    os.remove(chemin(nom))
    print(f"  supprimé : {nom}")
    time.sleep(PAUSE_ENTRE_FICHIERS)

with open(chemin("LISEZ-MOI_DECHIFFREMENT.txt"), "w", encoding="utf-8") as f:
    f.write(
        "TOUS VOS FICHIERS ONT ÉTÉ CHIFFRÉS.\n"
        "(Ceci est une SIMULATION à but pédagogique pour SCADAGuard — "
        "aucun fichier réel n'a été chiffré.)\n"
    )
print("  déposé : LISEZ-MOI_DECHIFFREMENT.txt")

print("\nSimulation terminée. Vérifie dans SCADAGuard :")
print("  - Onglet 'Fichiers'      : la séquence complète des évènements")
print("  - Onglet 'Journal d'audit' : les alertes CRITIQUE (rafale + note de rançon)")
print("  - Email (si configuré)  : une alerte doit être arrivée sur ton téléphone")
