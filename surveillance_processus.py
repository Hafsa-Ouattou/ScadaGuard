
import psutil

MOTS_CLES_SUSPECTS = ["temp", "tmp", "appdata\\local\\temp"]


def obtenir_processus_actifs():
    
    processus = []
    for proc in psutil.process_iter(["pid", "name", "exe", "cpu_percent"]):
        try:
            info = proc.info
            chemin = (info.get("exe") or "").lower()
            suspect = any(mot in chemin for mot in MOTS_CLES_SUSPECTS)
            processus.append({
                "pid": info["pid"],
                "nom": info["name"] or "N/A",
                "chemin": info.get("exe") or "N/A",
                "cpu": round(info.get("cpu_percent") or 0.0, 1),
                "suspect": suspect,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return processus
