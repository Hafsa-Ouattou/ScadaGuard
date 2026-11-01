import os
import tempfile
import threading
import datetime
import queue
import hashlib
from collections import Counter
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  

import auth
import surveillance_fichiers
import surveillance_reseau
import surveillance_processus
import surveillance_usb
import notifications_email

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

app = Flask(__name__)
app.secret_key = os.environ.get("SCADAGUARD_SECRET_KEY", "change-moi-avant-la-mise-en-production")


evenements = [] 
verrou_evenements = threading.Lock()
HASH_GENESE = "0" * 64

file_alertes_fichiers = queue.Queue()
_observateur_fichiers = None
_taches_demarrees = False
_verrou_demarrage = threading.Lock()


def _calculer_hash(horodatage, niveau, module, message, hash_precedent):
    contenu = f"{horodatage}|{niveau}|{module}|{message}|{hash_precedent}".encode("utf-8")
    return hashlib.sha256(contenu).hexdigest()


def ajouter_evenement(niveau, module, message):
   
    horodatage = datetime.datetime.now().strftime("%H:%M:%S")
    with verrou_evenements:
        hash_precedent = evenements[-1]["hash"] if evenements else HASH_GENESE
        hash_actuel = _calculer_hash(horodatage, niveau, module, message, hash_precedent)
        evenements.append({
            "heure": horodatage,
            "niveau": niveau,
            "module": module,
            "message": message,
            "hash_precedent": hash_precedent,
            "hash": hash_actuel,
        })
    notifications_email.envoyer_alerte_email_async(niveau, module, message)


def verifier_integrite_journal():
    
    with verrou_evenements:
        instantane = list(evenements)

    hash_attendu = HASH_GENESE
    for i, evt in enumerate(instantane):
        if evt["hash_precedent"] != hash_attendu:
            return False, i, len(instantane)
        recalcule = _calculer_hash(evt["heure"], evt["niveau"], evt["module"], evt["message"], evt["hash_precedent"])
        if recalcule != evt["hash"]:
            return False, i, len(instantane)
        hash_attendu = evt["hash"]

    return True, None, len(instantane)


def _consommer_file_fichiers():
   
    while True:
        niveau, module, message = file_alertes_fichiers.get()  # bloquant
        ajouter_evenement(niveau, module, message)


def demarrer_taches_fond():
    
    global _observateur_fichiers, _taches_demarrees
    with _verrou_demarrage:
        if _taches_demarrees:
            return
        _observateur_fichiers = surveillance_fichiers.demarrer_surveillance(file_alertes_fichiers)
        surveillance_usb.demarrer_surveillance(file_alertes_fichiers)
        threading.Thread(target=_consommer_file_fichiers, daemon=True).start()
        _taches_demarrees = True


demarrer_taches_fond()



def connexion_requise(vue):
    @wraps(vue)
    def enveloppe(*args, **kwargs):
        if "utilisateur" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"erreur": "non_authentifie"}), 401
            return redirect(url_for("connexion"))
        return vue(*args, **kwargs)
    return enveloppe


def admin_requis(vue):
    @wraps(vue)
    def enveloppe(*args, **kwargs):
        if session.get("role") != "admin":
            return jsonify({"erreur": "acces_refuse"}), 403
        return vue(*args, **kwargs)
    return enveloppe


@app.route("/login", methods=["GET", "POST"])
def connexion():
    if request.method == "GET":
        if "utilisateur" in session:
            return redirect(url_for("tableau_de_bord"))
        return render_template("login.html", erreur=None)

    nom = request.form.get("utilisateur", "").strip()
    mdp = request.form.get("mot_de_passe", "")
    if not nom or not mdp:
        return render_template("login.html", erreur="Veuillez remplir tous les champs.")

    succes, message, role = auth.verifier_connexion(nom, mdp)
    if succes:
        session["utilisateur"] = nom
        session["role"] = role
        return redirect(url_for("tableau_de_bord"))
    return render_template("login.html", erreur=message)


@app.route("/logout")
def deconnexion():
    if "utilisateur" in session:
        auth.enregistrer_action(session["utilisateur"], "déconnexion")
    session.clear()
    return redirect(url_for("connexion"))


@app.route("/")
@connexion_requise
def tableau_de_bord():
    return render_template(
        "dashboard.html",
        utilisateur=session["utilisateur"],
        role=session["role"],
        est_admin=(session["role"] == "admin"),
    )



@app.route("/api/fichiers")
@connexion_requise
def api_fichiers():
    with verrou_evenements:
        evts_fichiers = [e for e in evenements if e["module"] == "Fichiers"]
        total = len(evts_fichiers)
        derniers = list(reversed(evts_fichiers[-100:]))
    return jsonify({
        "evenements": [{"heure": e["heure"], "niveau": e["niveau"], "message": e["message"]} for e in derniers],
        "total": total,
    })



@app.route("/api/usb")
@connexion_requise
def api_usb():
    with verrou_evenements:
        evts_usb = [e for e in evenements if e["module"] == "USB"]
        total = len(evts_usb)
        derniers = list(reversed(evts_usb[-100:]))
    return jsonify({
        "evenements": [{"heure": e["heure"], "niveau": e["niveau"], "message": e["message"]} for e in derniers],
        "total": total,
    })



@app.route("/api/reseau")
@connexion_requise
def api_reseau():
    connexions = surveillance_reseau.obtenir_connexions_actives()
    for c in connexions:
        if c["suspect"]:
            ajouter_evenement("SUSPECT", "Réseau", f"Connexion vers port inhabituel : {c['distant']}")
    return jsonify({"connexions": connexions, "total": len(connexions)})



@app.route("/api/processus")
@connexion_requise
def api_processus():
    processus = surveillance_processus.obtenir_processus_actifs()
    for p in processus:
        if p["suspect"]:
            ajouter_evenement(
                "SUSPECT", "Processus",
                f"Processus lancé depuis un dossier temporaire : {p['nom']} (PID {p['pid']})",
            )
    return jsonify({"processus": processus, "total": len(processus)})



@app.route("/api/journal")
@connexion_requise
def api_journal():
    with verrou_evenements:
        evts = list(reversed(evenements[-300:]))
        total_critiques = sum(1 for e in evenements if e["niveau"] == "CRITIQUE")
    return jsonify({
        "evenements": [
            {"heure": e["heure"], "niveau": e["niveau"], "module": e["module"], "message": e["message"]}
            for e in evts
        ],
        "total_critiques": total_critiques,
    })


@app.route("/api/journal/verifier")
@connexion_requise
def api_journal_verifier():
    
    intact, index_probleme, total = verifier_integrite_journal()
    return jsonify({
        "intact": intact,
        "index_probleme": index_probleme,
        "total_evenements": total,
    })



@app.route("/api/stats")
@connexion_requise
def api_stats():
    with verrou_evenements:
        instantane = list(evenements)
    compteur_niveaux = Counter(e["niveau"] for e in instantane)
    compteur_modules = Counter(e["module"] for e in instantane)
    ordre = ["INFO", "SUSPECT", "CRITIQUE"]
    niveaux_labels = [n for n in ordre if n in compteur_niveaux] + \
                      [n for n in compteur_niveaux if n not in ordre]
    return jsonify({
        "niveaux": {
            "labels": niveaux_labels,
            "valeurs": [compteur_niveaux[n] for n in niveaux_labels],
        },
        "modules": {
            "labels": list(compteur_modules.keys()),
            "valeurs": list(compteur_modules.values()),
        },
        "resume": {
            "total": len(instantane),
            "critique": compteur_niveaux.get("CRITIQUE", 0),
            "suspect": compteur_niveaux.get("SUSPECT", 0),
            "info": compteur_niveaux.get("INFO", 0),
        },
    })



@app.route("/api/export/excel")
@connexion_requise
@admin_requis
def export_excel():
    with verrou_evenements:
        instantane = list(evenements)

    wb = Workbook()
    feuille = wb.active
    feuille.title = "Journal d'audit"
    feuille.append(["Heure", "Niveau", "Module", "Message", "Hash (preuve d'intégrité)"])
    for cellule in feuille[1]:
        cellule.font = Font(bold=True, color="FFFFFF")
        cellule.fill = PatternFill("solid", start_color="0B4F8A")

    for evt in instantane:
        feuille.append([evt["heure"], evt["niveau"], evt["module"], evt["message"], evt["hash"][:16] + "…"])
        if evt["niveau"] == "CRITIQUE":
            for cellule in feuille[feuille.max_row]:
                cellule.fill = PatternFill("solid", start_color="FBEAE9")

    for lettre, largeur in zip("ABCDE", [12, 12, 14, 60, 20]):
        feuille.column_dimensions[lettre].width = largeur

    chemin = os.path.join(tempfile.gettempdir(), f"scadaguard_journal_{datetime.date.today()}.xlsx")
    wb.save(chemin)
    auth.enregistrer_action(session["utilisateur"], f"export_journal ({chemin})")
    return send_file(chemin, as_attachment=True,
                      download_name=f"scadaguard_journal_{datetime.date.today()}.xlsx")


@app.route("/api/export/pdf")
@connexion_requise
@admin_requis
def export_pdf():
    with verrou_evenements:
        instantane = list(evenements)

    chemin = os.path.join(tempfile.gettempdir(), f"scadaguard_journal_{datetime.date.today()}.pdf")
    document = SimpleDocTemplate(chemin, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    intact, _, _ = verifier_integrite_journal()
    elements = [
        Paragraph("SCADAGuard — Journal d'audit", styles["Title"]),
        Paragraph(
            f"ONEE Branche Eau | Généré le {datetime.date.today().strftime('%d/%m/%Y')} "
            f"| {len(instantane)} évènement(s) | Intégrité de la chaîne : "
            f"{'VÉRIFIÉE ✔' if intact else 'ALTÉRÉE ⚠️'}",
            styles["Normal"],
        ),
        Spacer(1, 14),
    ]

    donnees = [["Heure", "Niveau", "Module", "Message"]]
    lignes_critiques = []
    for i, evt in enumerate(instantane, start=1):
        donnees.append([evt["heure"], evt["niveau"], evt["module"], evt["message"]])
        if evt["niveau"] == "CRITIQUE":
            lignes_critiques.append(i)

    tableau = Table(donnees, repeatRows=1, colWidths=[60, 60, 70, 400])
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B4F8A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F7FA")]),
    ]
    for i in lignes_critiques:
        style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#FBEAE9")))
        style.append(("TEXTCOLOR", (0, i), (-1, i), colors.HexColor("#C0392B")))
    tableau.setStyle(TableStyle(style))
    elements.append(tableau)
    document.build(elements)

    auth.enregistrer_action(session["utilisateur"], f"export_pdf ({chemin})")
    return send_file(chemin, as_attachment=True,
                      download_name=f"scadaguard_journal_{datetime.date.today()}.pdf")



@app.route("/api/email/test", methods=["POST"])
@connexion_requise
@admin_requis
def api_email_test():
    ok, message = notifications_email.envoyer_email_test()
    return jsonify({"succes": ok, "message": message})


@app.route("/api/etat")
@connexion_requise
def api_etat():
    return jsonify({
        "utilisateur": session["utilisateur"],
        "role": session["role"],
        "email_configure": notifications_email.est_configure(),
    })


if __name__ == "__main__":
    
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False, threaded=True)
