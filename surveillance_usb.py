import os
import time
import threading

import psutil

INTERVALLE_SECONDES = 2
EXTENSIONS_SUSPECTES = {".exe", ".bat", ".cmd", ".vbs", ".vbe", ".ps1", ".scr", ".js", ".jar"}


def _lister_lecteurs_amovibles():
    lecteurs = set()
    try:
        for partition in psutil.disk_partitions(all=False):
            opts = (partition.opts or "").lower()
            fstype = (partition.fstype or "").lower()
            if "removable" in opts or "cdrom" in opts or fstype in ("", "udf", "iso9660"):
                # Sur Windows, psutil expose 'removable' dans les options pour
                # les clés USB. On ignore les lecteurs réseau (fstype vide sur
                # certains systèmes correspond parfois à autre chose : on reste
                # prudent en ne gardant que ce qui ressemble vraiment à un
                # support amovible.
                if "removable" in opts or "cdrom" in opts:
                    lecteurs.add(partition.mountpoint)
    except Exception:
        pass
    return lecteurs


def _analyser_racine_lecteur(chemin):
    suspects = []
    try:
        with os.scandir(chemin) as it:
            for entree in it:
                if entree.is_file():
                    _, extension = os.path.splitext(entree.name)
                    if extension.lower() in EXTENSIONS_SUSPECTES:
                        suspects.append(entree.name)
    except Exception:
        pass
    return suspects


def _boucle_surveillance(queue_alertes):
    connus = _lister_lecteurs_amovibles()
    while True:
        time.sleep(INTERVALLE_SECONDES)
        try:
            actuels = _lister_lecteurs_amovibles()
        except Exception:
            continue

        nouveaux = actuels - connus
        retires = connus - actuels

        for lecteur in nouveaux:
            suspects = _analyser_racine_lecteur(lecteur)
            if suspects:
                queue_alertes.put((
                    "CRITIQUE", "USB",
                    f"Clé USB branchée ({lecteur}) contenant {len(suspects)} fichier(s) "
                    f"exécutable(s) suspect(s) : {', '.join(suspects[:5])}"
                    + (", ..." if len(suspects) > 5 else "")
                ))
            else:
                queue_alertes.put(("SUSPECT", "USB", f"Clé USB / disque amovible branché : {lecteur}"))

        for lecteur in retires:
            queue_alertes.put(("INFO", "USB", f"Clé USB / disque amovible retiré : {lecteur}"))

        connus = actuels


def demarrer_surveillance(queue_alertes):
    thread = threading.Thread(target=_boucle_surveillance, args=(queue_alertes,), daemon=True)
    thread.start()
    return thread
