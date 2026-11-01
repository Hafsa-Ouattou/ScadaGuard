import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from collections import Counter

COULEUR_PRIMAIRE = "#0B4F8A"
COULEUR_PRIMAIRE_2 = "#0E6BA8"
COULEURS_NIVEAU = {"INFO": "#0E6BA8", "SUSPECT": "#B9770E", "CRITIQUE": "#C0392B"}


def figure_repartition_niveaux(evenements):
    
    compteur = Counter(e[1] for e in evenements)
    fig, ax = plt.subplots(figsize=(4, 3.2), dpi=95)

    if not compteur:
        ax.text(0.5, 0.5, "Aucune donnée pour le moment", ha="center", va="center", fontsize=9)
        ax.axis("off")
        return fig

    ordre = ["INFO", "SUSPECT", "CRITIQUE"]
    niveaux = [n for n in ordre if n in compteur] + [n for n in compteur if n not in ordre]
    valeurs = [compteur[n] for n in niveaux]
    total = sum(valeurs)
    couleurs = [COULEURS_NIVEAU.get(n, "#888888") for n in niveaux]

 
    explosion = [0.08 if (v / total) < 0.08 else 0 for v in valeurs]

    parts, _ = ax.pie(
        valeurs, colors=couleurs, startangle=90, explode=explosion,
        wedgeprops={"linewidth": 1, "edgecolor": "white"}
    )

    etiquettes = [f"{n} — {v} ({v / total * 100:.0f}%)" for n, v in zip(niveaux, valeurs)]
    ax.legend(parts, etiquettes, loc="center left", bbox_to_anchor=(1.0, 0.5),
              fontsize=8, frameon=False)

    ax.set_title("Répartition par niveau", fontsize=10, fontweight="bold")
    fig.tight_layout()
    return fig


def figure_evenements_par_module(evenements):
    compteur = Counter(e[2] for e in evenements)
    fig, ax = plt.subplots(figsize=(4, 3.4), dpi=100)

    if not compteur:
        ax.text(0.5, 0.5, "Aucune donnée pour le moment", ha="center", va="center", fontsize=9)
        ax.axis("off")
        return fig

    modules = list(compteur.keys())
    valeurs = [compteur[m] for m in modules]
    barres = ax.bar(modules, valeurs, color=COULEUR_PRIMAIRE)
    ax.bar_label(barres, fontsize=8)
    ax.set_title("Évènements par module", fontsize=10, fontweight="bold")
    ax.set_ylabel("Nombre d'évènements", fontsize=8)
    ax.tick_params(axis="x", labelsize=8)
    ax.tick_params(axis="y", labelsize=8)
    fig.tight_layout()
    return fig


def statistiques_resume(evenements):
    compteur_niveaux = Counter(e[1] for e in evenements)
    return {
        "total": len(evenements),
        "critique": compteur_niveaux.get("CRITIQUE", 0),
        "suspect": compteur_niveaux.get("SUSPECT", 0),
        "info": compteur_niveaux.get("INFO", 0),
    }
