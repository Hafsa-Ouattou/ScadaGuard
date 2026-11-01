import os
import time

DOSSIER = "dossier_surveille"
os.makedirs(DOSSIER, exist_ok=True)

print("Création rapide de 15 fichiers dans", DOSSIER, "...")
for i in range(15):
    chemin = os.path.join(DOSSIER, f"fichier_test_{i}.txt")
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(f"Contenu de test numéro {i}")
    time.sleep(0.1)  # petite pause pour simuler une vraie rafale

print("Terminé. Regarde l'onglet 'Fichiers' de SCADAGuard : une alerte")
print("CRITIQUE devrait être apparue (comportement type ransomware).")
