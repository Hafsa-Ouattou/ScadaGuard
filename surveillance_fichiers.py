import os
import time
from collections import deque
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

DOSSIER_SURVEILLE = "dossier_surveille"
SEUIL_EVENEMENTS = 8      # nombre d'évènements suspects...
FENETRE_SECONDES = 5      # ...survenant dans cette fenêtre de temps


MOTS_CLES_NOTE_RANCON = [
    "readme", "decrypt", "restore_files", "how_to_decrypt",
    "ransom", "recover", "help_decrypt", "lisez-moi_dechiffrement",
]


def _ressemble_a_une_note_de_rancon(nom_fichier):
    nom = nom_fichier.lower()
    return any(mot in nom for mot in MOTS_CLES_NOTE_RANCON)


class GestionnaireFichiers(FileSystemEventHandler):
    def __init__(self, queue_alertes):
        super().__init__()
        self.queue_alertes = queue_alertes
        self.horodatages = deque()

    def _enregistrer_evenement(self, type_evenement, chemin):
        nom_fichier = os.path.basename(chemin)

        
        if _ressemble_a_une_note_de_rancon(nom_fichier):
            self.queue_alertes.put((
                "CRITIQUE", "Fichiers",
                f"Note de rançon détectée : {nom_fichier} — signature typique d'une attaque ransomware"
            ))
            return

        maintenant = time.time()
        self.horodatages.append(maintenant)

        while self.horodatages and maintenant - self.horodatages[0] > FENETRE_SECONDES:
            self.horodatages.popleft()

        if len(self.horodatages) >= SEUIL_EVENEMENTS:
            self.queue_alertes.put((
                "CRITIQUE", "Fichiers",
                f"{len(self.horodatages)} modifications de fichiers en moins de "
                f"{FENETRE_SECONDES}s — comportement typique d'un ransomware"
            ))
            self.horodatages.clear()
        else:
            self.queue_alertes.put((
                "INFO", "Fichiers", f"{type_evenement} : {os.path.basename(chemin)}"
            ))

    def on_created(self, event):
        if not event.is_directory:
            self._enregistrer_evenement("Création", event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._enregistrer_evenement("Modification", event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self._enregistrer_evenement("Renommage", event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self._enregistrer_evenement("Suppression", event.src_path)




def demarrer_surveillance(queue_alertes, dossier=DOSSIER_SURVEILLE):
    os.makedirs(dossier, exist_ok=True)
    gestionnaire = GestionnaireFichiers(queue_alertes)
    observateur = Observer()
    observateur.schedule(gestionnaire, dossier, recursive=True)
    observateur.start()
    return observateur
