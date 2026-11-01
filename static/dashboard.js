
document.querySelectorAll(".entete-onglet").forEach((bouton) => {
  bouton.addEventListener("click", () => {
    document.querySelectorAll(".entete-onglet").forEach((b) => b.classList.remove("actif"));
    document.querySelectorAll(".contenu-onglet").forEach((c) => c.classList.remove("actif"));
    bouton.classList.add("actif");
    document.getElementById("onglet-" + bouton.dataset.onglet).classList.add("actif");
  });
});

function echapper(texte) {
  const div = document.createElement("div");
  div.textContent = texte ?? "";
  return div.innerHTML;
}

function classeBadgeNiveau(niveau) {
  if (niveau === "CRITIQUE") return "badge-critique";
  if (niveau === "SUSPECT") return "badge-suspect";
  return "badge-info";
}

async function appelApi(url, options) {
  const reponse = await fetch(url, options);
  if (reponse.status === 401) {
    window.location.href = "/login";
    return null;
  }
  return reponse.json();
}

async function rafraichirFichiers() {
  const donnees = await appelApi("/api/fichiers");
  if (!donnees) return;
  document.getElementById("kpi-fichiers").textContent = donnees.total;

  const corps = document.getElementById("corps-fichiers");
  if (donnees.evenements.length === 0) {
    corps.innerHTML = '<tr><td colspan="2" class="vide">Aucun évènement pour le moment.</td></tr>';
    return;
  }
  corps.innerHTML = donnees.evenements.map((e) => `
    <tr class="${e.niveau === "CRITIQUE" ? "ligne-critique" : ""}">
      <td>${echapper(e.heure)}</td>
      <td>${echapper(e.message)}</td>
    </tr>`).join("");
}


async function rafraichirReseau() {
  const donnees = await appelApi("/api/reseau");
  if (!donnees) return;
  document.getElementById("kpi-reseau").textContent = donnees.total;

  const corps = document.getElementById("corps-reseau");
  if (donnees.connexions.length === 0) {
    corps.innerHTML = '<tr><td colspan="4" class="vide">Aucune connexion active détectée.</td></tr>';
    return;
  }
  corps.innerHTML = donnees.connexions.map((c) => `
    <tr class="${c.suspect ? "ligne-suspect" : ""}">
      <td>${echapper(c.local)}</td>
      <td>${echapper(c.distant)}</td>
      <td>${echapper(c.pid)}</td>
      <td><span class="badge ${c.suspect ? "badge-suspect" : "badge-normal"}">
        ${c.suspect ? "Port inhabituel" : "Normal"}</span></td>
    </tr>`).join("");
}

async function rafraichirProcessus() {
  const donnees = await appelApi("/api/processus");
  if (!donnees) return;
  document.getElementById("kpi-processus").textContent = donnees.total;

  const corps = document.getElementById("corps-processus");
  if (donnees.processus.length === 0) {
    corps.innerHTML = '<tr><td colspan="5" class="vide">Aucun processus détecté.</td></tr>';
    return;
  }
  corps.innerHTML = donnees.processus.map((p) => `
    <tr class="${p.suspect ? "ligne-critique" : ""}">
      <td>${echapper(p.pid)}</td>
      <td>${echapper(p.nom)}</td>
      <td>${echapper(p.chemin)}</td>
      <td>${echapper(p.cpu)}</td>
      <td><span class="badge ${p.suspect ? "badge-critique" : "badge-normal"}">
        ${p.suspect ? "Suspect" : "Normal"}</span></td>
    </tr>`).join("");
}


async function rafraichirJournal() {
  const donnees = await appelApi("/api/journal");
  if (!donnees) return;
  document.getElementById("kpi-alertes").textContent = donnees.total_critiques;

  const corps = document.getElementById("corps-journal");
  if (donnees.evenements.length === 0) {
    corps.innerHTML = '<tr><td colspan="4" class="vide">Aucun évènement enregistré.</td></tr>';
    return;
  }
  corps.innerHTML = donnees.evenements.map((e) => `
    <tr>
      <td>${echapper(e.heure)}</td>
      <td><span class="badge ${classeBadgeNiveau(e.niveau)}">${echapper(e.niveau)}</span></td>
      <td>${echapper(e.module)}</td>
      <td>${echapper(e.message)}</td>
    </tr>`).join("");
}


let graphiqueNiveaux = null;
let graphiqueModules = null;
const COULEURS_NIVEAU = { INFO: "#0E6BA8", SUSPECT: "#B9770E", CRITIQUE: "#C0392B" };

async function rafraichirStatistiques() {
  const donnees = await appelApi("/api/stats");
  if (!donnees) return;

  const ctxNiveaux = document.getElementById("graphique-niveaux");
  const couleursNiveaux = donnees.niveaux.labels.map((n) => COULEURS_NIVEAU[n] || "#888888");
  if (graphiqueNiveaux) {
    graphiqueNiveaux.data.labels = donnees.niveaux.labels;
    graphiqueNiveaux.data.datasets[0].data = donnees.niveaux.valeurs;
    graphiqueNiveaux.data.datasets[0].backgroundColor = couleursNiveaux;
    graphiqueNiveaux.update();
  } else {
    graphiqueNiveaux = new Chart(ctxNiveaux, {
      type: "pie",
      data: {
        labels: donnees.niveaux.labels,
        datasets: [{ data: donnees.niveaux.valeurs, backgroundColor: couleursNiveaux }],
      },
      options: { plugins: { legend: { position: "right" } } },
    });
  }

  const ctxModules = document.getElementById("graphique-modules");
  if (graphiqueModules) {
    graphiqueModules.data.labels = donnees.modules.labels;
    graphiqueModules.data.datasets[0].data = donnees.modules.valeurs;
    graphiqueModules.update();
  } else {
    graphiqueModules = new Chart(ctxModules, {
      type: "bar",
      data: {
        labels: donnees.modules.labels,
        datasets: [{ label: "Évènements", data: donnees.modules.valeurs, backgroundColor: "#0B4F8A" }],
      },
      options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } },
    });
  }
}

async function verifierEtatEmail() {
  const donnees = await appelApi("/api/etat");
  if (!donnees) return;
  const el = document.getElementById("statut-email");
  if (donnees.email_configure) {
    el.textContent = "configurées ✅";
    el.classList.add("ok");
  } else {
    el.textContent = "non configurées — voir le fichier .env";
    el.classList.add("ko");
  }
}

const boutonTestEmail = document.getElementById("bouton-test-email");
if (boutonTestEmail) {
  boutonTestEmail.addEventListener("click", async () => {
    boutonTestEmail.disabled = true;
    boutonTestEmail.textContent = "Envoi en cours…";
    const donnees = await appelApi("/api/email/test", { method: "POST" });
    const resultat = document.getElementById("resultat-test-email");
    if (donnees) {
      resultat.textContent = donnees.message;
      resultat.style.color = donnees.succes ? "var(--succes)" : "var(--danger)";
    }
    boutonTestEmail.disabled = false;
    boutonTestEmail.textContent = "Envoyer un email de test";
  });
}

async function rafraichirUsb() {
  const donnees = await appelApi("/api/usb");
  if (!donnees) return;
  document.getElementById("kpi-usb").textContent = donnees.total;

  const corps = document.getElementById("corps-usb");
  if (donnees.evenements.length === 0) {
    corps.innerHTML = '<tr><td colspan="2" class="vide">Aucun périphérique USB détecté pour le moment.</td></tr>';
    return;
  }
  corps.innerHTML = donnees.evenements.map((e) => `
    <tr class="${e.niveau === "CRITIQUE" ? "ligne-critique" : e.niveau === "SUSPECT" ? "ligne-suspect" : ""}">
      <td>${echapper(e.heure)}</td>
      <td>${echapper(e.message)}</td>
    </tr>`).join("");
}

const boutonIntegrite = document.getElementById("bouton-verifier-integrite");
if (boutonIntegrite) {
  boutonIntegrite.addEventListener("click", async () => {
    const resultat = document.getElementById("resultat-integrite");
    resultat.textContent = "Vérification en cours…";
    resultat.style.color = "var(--texte-muet)";
    const donnees = await appelApi("/api/journal/verifier");
    if (!donnees) return;
    if (donnees.intact) {
      resultat.textContent = `✅ Intègre — ${donnees.total_evenements} évènement(s) vérifié(s), aucune altération détectée.`;
      resultat.style.color = "var(--succes)";
    } else {
      resultat.textContent = `⚠️ ALTÉRATION DÉTECTÉE à l'évènement n°${donnees.index_probleme + 1} !`;
      resultat.style.color = "var(--danger)";
    }
  });
}

rafraichirFichiers();
rafraichirUsb();
rafraichirReseau();
rafraichirProcessus();
rafraichirJournal();
rafraichirStatistiques();
verifierEtatEmail();

setInterval(rafraichirFichiers, 1000);    
setInterval(rafraichirUsb, 2000);      
setInterval(rafraichirReseau, 8000);        
setInterval(rafraichirProcessus, 10000);    
setInterval(rafraichirJournal, 3000);       
setInterval(rafraichirStatistiques, 15000); 
