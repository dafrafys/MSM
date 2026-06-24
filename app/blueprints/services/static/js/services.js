// services.js: gestion du planning (semaine/mois), activités et assignations

// Global offsets for month and week navigation
let monthOffset = 0;
let weekOffset  = 0;
let activitiesCache = [];
let currentPersonnelId = null;
let currentDate = null;
let currentActivities = [];

let pressTimer;
let pressHoldTriggered = false;


function getActivitiesForCell(cell) {
  const personnelId = cell.dataset.personnelId;
  const date = cell.dataset.date;

  if (!personnelId || !date) return [];

  return activitiesCache.filter(a =>
    a.date === date &&
    a.personnel.some(p => p.personnel_id == personnelId)
  );
}

function startPressAndHoldCell(e) {
  if (e.ctrlKey) {
    console.log("Ctrl pressé, on ne lance pas le press & hold pour reorder");
    return;
  }
  // console.log("Début du press & hold sur la cellule :", e.currentTarget);
  const cell = e.currentTarget;

  cell.pressHoldTriggered = false;
  cell.pressTimer = setTimeout(() => {
    //console.log("Press & hold cellule déclenché après 3 secondes.");

    // Toujours vérifier que cell existe encore au moment du timeout
    if (!cell || !cell.dataset) {
      console.error("Cellule non valide pour press & hold reorder");
      return;
    }

    cell.pressHoldTriggered = true;

    const personnelId = cell.dataset.personnelId;
    const date = cell.dataset.date;

    if (!personnelId || !date) {
      console.error("Attributs manquants dans la cellule pour reorder");
      return;
    }

    const activities = getActivitiesForCell(cell);
    openReorderModal(personnelId, date, activities);
  }, 3000);
}


function cancelPressAndHold(e) {
  //console.log("cancelPressAndHold appelé");
  if (e.currentTarget.pressTimer) {
    clearTimeout(e.currentTarget.pressTimer);
    e.currentTarget.pressTimer = null;
  }
  e.currentTarget.pressHoldTriggered = false;
}

// --- Modal reorder ---
function openReorderModal(personnelId, date, activities) {
  console.log(`Ouverture du modal de réordonnancement pour le personnel ${personnelId} à la date ${date}. Activités :`, activities);
  currentPersonnelId = personnelId;
  currentDate = date;
  currentActivities = [...activities];

  const list = document.getElementById('activityList');
  list.innerHTML = '';

  currentActivities.forEach((act, idx) => {
    const li = document.createElement('li');
    li.className = 'list-group-item d-flex justify-content-between align-items-center';
    li.dataset.index = idx;

    li.innerHTML = `
      <span>${act.titre}</span>
      <div>
        <button class="btn btn-sm btn-outline-secondary me-1" onclick="moveUp(${idx})" ${idx === 0 ? 'disabled' : ''}>&uarr;</button>
        <button class="btn btn-sm btn-outline-secondary" onclick="moveDown(${idx})" ${idx === currentActivities.length - 1 ? 'disabled' : ''}>&darr;</button>
      </div>
    `;

    list.appendChild(li);
  });

  const reorderModal = new bootstrap.Modal(document.getElementById('reorderModal'), {
    backdrop: false,
    keyboard: true  // pour permettre fermeture avec Échap
  });
  reorderModal.show();

  //const modalElement = document.getElementById('reorderModal');
  //modalElement.focus();  // focus sur le modal (ajoute tabindex="-1" dans le HTML)
}

// --- Fonctions déplacer dans la liste ---
function moveUp(idx) {
  if (idx <= 0) return;
  [currentActivities[idx - 1], currentActivities[idx]] = [currentActivities[idx], currentActivities[idx - 1]];
  openReorderModal(currentPersonnelId, currentDate, currentActivities);
}

function moveDown(idx) {
  if (idx >= currentActivities.length - 1) return;
  [currentActivities[idx], currentActivities[idx + 1]] = [currentActivities[idx + 1], currentActivities[idx]];
  openReorderModal(currentPersonnelId, currentDate, currentActivities);
}

//Format date Locale
function formatLocalDate(d){
 return d.getFullYear()
 + "-" + String(d.getMonth()+1).padStart(2,"0")
 + "-" + String(d.getDate()).padStart(2,"0");
}

// Compute the Monday of current week as immutable base
const initialWeekStart = (() => {
  const today = new Date();
  const day   = today.getDay();               // 0 = Sun, 1 = Mon, ..., 6 = Sat
  const monday = new Date(today);
  monday.setDate(today.getDate() - ((day + 6) % 7));  // shift back to Monday
  return formatLocalDate(monday);
// return monday.toISOString().slice(0, 10);    // "YYYY-MM-DD"
})();

// Calculate start date for a week, offset by weeks from initialWeekStart
function getWeekStartDate(offsetWeeks = 0) {
  const base = new Date(initialWeekStart);
  base.setDate(base.getDate() + offsetWeeks * 7);
  return formatLocalDate(base);
 // return base.toISOString().slice(0, 10);
}

// ── paramètres du cycle Equipe ──────────────────────────────
const REF_DAY = new Date("2025-01-08");
const CYCLE   = ["M","M","A","A","N","N","R","R","R","R"];
const OFFS    = { A:0, C:2, E:4, B:6, D:8 };

// Trie automatiquement les équipes par leur offset croissant
const TEAMS = Object
  .entries(OFFS)               // [ ['A',0], ['C',2], … ]
  .sort(([,o1],[,o2]) => o1 - o2) // tri sur la valeur
  .map(([team]) => team);        // ['A','C','E','D','B']

// retourne "M","A","N" ou "R" pour une équipe et une date
function shiftFor(team, dateObj) {
  const delta = Math.floor((dateObj - REF_DAY) / 864e5);
  const idx   = (OFFS[team] + delta + CYCLE.length) % CYCLE.length;
  return CYCLE[idx];
}

// ne prend plus `personnel`, mais utilise TEAMS
function buildPlanningEquipe(weekDays) {
  const map = {};
  weekDays.forEach(d => {
    const key = d.toISOString().slice(0,10);
    const inv = {};
    TEAMS.forEach(t => {
      const s = shiftFor(t, d);
      if (s !== "R") inv[s] = t;
    });
    map[key] = [inv.M||"", inv.A||"", inv.N||""].join("|");
  });
  return map;
}

// --- Load week via AJAX with debug JSON parsing ---
async function loadWeek(startDate) {
  const service = document.getElementById("currentRange").dataset.service;
  console.log("service_key utilisé pour la requête :", service);
  const from = new Date(startDate);
  const to = new Date(from);
  to.setDate(from.getDate() + 6);

  const fromStr = from.toISOString().slice(0, 10);
  const toStr = to.toISOString().slice(0, 10);

  // Récupérer les activités
  const resActivities = await fetch(`/services/api/activities?from=${fromStr}&to=${toStr}&service_key=${service}`);
  if (!resActivities.ok) {
    console.error("Erreur chargement activités");
    return;
  }
  const activities = await resActivities.json();
  activitiesCache = activities;

  // Récupérer les infos journalières (service info)
  const resInfo = await fetch(`/services/api/service_info?from=${fromStr}&to=${toStr}&service_key=${service}`);
  if (resInfo.ok) {
    const infosData = await resInfo.json();
    // Transforme le tableau en dictionnaire date → texte
    const infosMap = {};
    infosData.forEach(item => {
      const dateObj = new Date(item.info_date);
      const normalizedDate = dateObj.toISOString().slice(0, 10);
      infosMap[normalizedDate] = item.info_text;
    });
    window.serviceInfos = infosMap;
  } else {
    window.serviceInfos = {};
  }

  // Récupérer les renforts actifs sur la période
  const resRenforts = await fetch(`/services/api/renforts?from=${fromStr}&to=${toStr}&service_key=${service}`);
  if (!resRenforts.ok) {
    console.error("Erreur chargement renforts");
    return;
  }
  const renforts = await resRenforts.json();
  console.log("[LOG] Renforts reçus pour la période :", renforts);

  // Ne pas fusionner avec personnels fixes dans window.PERSONNEL
  // window.PERSONNEL garde la liste complète du personnel fixe (non renfort)

  // Stocker les renforts dans une variable dédiée
  window.RENFORTS = renforts;

  // Passer les deux listes séparées à updateWeekView ou gérer ici l'affichage
  updateWeekView(from, activities, window.PERSONNEL, window.RENFORTS);

  // Mise à jour de l'entête affichée
  const header = document.getElementById("currentRange");
  const numSemaine = getWeekNumber(from);
  const moisFrom = from.toLocaleString('fr-FR', { month: 'long' });
  const moisTo = to.toLocaleString('fr-FR', { month: 'long' });
  const annee = from.getFullYear();

  const moisAffiche = (moisFrom === moisTo) ? moisFrom : `${moisFrom} / ${moisTo}`;
  header.textContent = `📅 Semaine ${numSemaine} – ${moisAffiche} ${annee}`;
}


/* --- Load month via AJAX ---
async function loadMonth(offset) {
  const service  = document.getElementById("currentRange").dataset.service;
  const baseDate = new Date();
  baseDate.setMonth(baseDate.getMonth() + offset);

  const year     = baseDate.getFullYear();
  const month    = baseDate.getMonth() + 1;
  const fromStr  = `${year}-${String(month).padStart(2,'0')}-01`;
  const lastDay  = new Date(year, month, 0).getDate();
  const toStr    = `${year}-${String(month).padStart(2,'0')}-${lastDay}`;
  const url      = `/services/api/activities?from=${fromStr}&to=${toStr}&service_key=${service}`;

  const res  = await fetch(url);
  const data = await res.json();
  console.log("🔗 fetch month", url, "→", data);

  updateMonthView(data, year, month);
}*/

// --- Toggle between week and month view ---
function toggleView(view) {
  document.querySelectorAll('.calendar').forEach(el => el.classList.remove('active'));
  document.getElementById(view).classList.add('active');
  (view === "week")
    loadWeek(getWeekStartDate(weekOffset));
}

// --- Prev/Next buttons ---
document.getElementById("nextBtn").addEventListener("click", () => {
    weekOffset++;
    const nextDate = getWeekStartDate(weekOffset);
    console.log(`📅 Semaine suivante (offset=${weekOffset}) → ${nextDate}`);
    loadWeek(nextDate);
});
document.getElementById("prevBtn").addEventListener("click", () => {
    weekOffset--;
    const prevDate = getWeekStartDate(weekOffset);
    console.log(`📅 Semaine précédente (offset=${weekOffset}) → ${prevDate}`);
    loadWeek(prevDate);
});

// --- Today button ---
document.getElementById("todayBtn")?.addEventListener('click', () => {
  weekOffset = 0;
  loadWeek(initialWeekStart);
});

/* --- Helpers ---
function isMonthView() {
  return document.getElementById("month").classList.contains("active");
}*/

function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

function getWeekNumber(d) {
  d = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  const dayNum   = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(),0,1));
  return Math.ceil(((d - yearStart)/86400000 + 1)/7);
}

function getMonthMatrix(year, month) {
  const cal      = [];
  const firstDay = new Date(year, month-1,1);
  const startDay = (firstDay.getDay()+6)%7;
  const daysInMonth = new Date(year, month, 0).getDate();
  let week = Array(startDay).fill(0);
  for (let day = 1; day <= daysInMonth; day++) {
    week.push(day);
    if (week.length === 7) { cal.push(week); week = []; }
  }
  if (week.length) while (week.length < 7) week.push(0);
  cal.push(week);
  return cal;
}

// --- Sauvegarde de l’ordre dans le backend ---
async function saveOrder() {
  const payload = {
    personnel_id: currentPersonnelId,
    date: currentDate,
    ordered_activities: currentActivities.map((act, i) => ({
      activite_id: act.activite_id,
      priorité: i + 1
    }))
  };

  try {
    const res = await fetch('/services/api/activities/reorder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    console.log("Réponse reçue du serveur :", res.status);

    if (!res.ok) {
      let errorMsg = 'Erreur lors de la sauvegarde de l’ordre';
      try {
        const errData = await res.json();
        if (errData && errData.message) errorMsg = errData.message;
      } catch {}
      throw new Error(`${errorMsg} (status ${res.status})`);
    }

    pushLog('Ordre des activités mis à jour', 'success');
    bootstrap.Modal.getInstance(document.getElementById('reorderModal')).hide();

    // Rafraîchissement complet de la page
    window.location.reload();

  } catch (err) {
    pushLog(`❌ ${err.message}`, 'error');
    console.error(err);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById('saveOrderBtn').addEventListener('click', saveOrder);
});

// --- Update week view in DOM ---
function updateWeekView(startDate, activities, personnelsFixes, renforts) {
  console.log("→ Activités (raw):", activities);
  console.log("→ Collaborateurs:", window.PERSONNEL);

  let thead = document.querySelector('#planningTable thead');
  if (!thead) {
    thead = document.createElement('thead');
    thead.innerHTML = '<tr></tr>';
    document.getElementById('planningTable').prepend(thead);
  }
  const row = thead.querySelector('tr');
  row.innerHTML = '<th>Personnel</th>';

  const weekDays = [];
  const first = new Date(startDate);
  for (let i = 0; i < 7; i++) {
    const d = new Date(first);
    d.setDate(first.getDate() + i);
    weekDays.push(d);
  }

  window.planningEquipe = buildPlanningEquipe(weekDays);

  const dayNames = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'];

  weekDays.forEach((d, idx) => {
    const th = document.createElement('th');
    const jour = dayNames[idx];
    const dateNum = d.getDate().toString().padStart(2, '0');
    const key = d.toISOString().slice(0, 10);
    const shift = window.planningEquipe[key] || "";

    th.classList.add('text-center');
    th.innerHTML = `
      ${jour}<br>
      <span class="date-num">${dateNum}</span>
      ${shift ? `<br><span class="shift-label">${shift}</span>` : ''}
    `;
    row.appendChild(th);
  });

  const tbody = document.querySelector("#planningTable tbody");
  tbody.innerHTML = "";

  // Création d’un fragment pour optimiser l’insertion
  const fragment = document.createDocumentFragment();
  const personnelsTotal = [...personnelsFixes, ...renforts];

  // --- lignes par personnel ---
  personnelsTotal
    .filter(p => p.Equipe && p.nom_complet)
    .filter(p => !(p.nom_complet.toUpperCase() === "ALEXANDRE FAUGE"))
    .sort((a, b) => {
      const order = ["A", "B", "C", "D", "E"];

      const aEquipe = (a.Equipe || "").charAt(0).toUpperCase();
      const bEquipe = (b.Equipe || "").charAt(0).toUpperCase();

      if (aEquipe === "J" && bEquipe !== "J") return -1;
      if (aEquipe !== "J" && bEquipe === "J") return 1;

      const aIndex = order.indexOf(aEquipe);
      const bIndex = order.indexOf(bEquipe);

      if (aIndex === -1 && bIndex === -1) {
        return aEquipe.localeCompare(bEquipe);
      }
      if (aIndex === -1) return 1;
      if (bIndex === -1) return -1;

      if (aIndex !== bIndex) return aIndex - bIndex;

      return a.nom_complet.localeCompare(b.nom_complet);
    })
    .forEach(p => {
      const tr = document.createElement("tr");

      const tdName = document.createElement("td");
      tdName.classList.add("person-name");

      if (p.is_renfort) {
        tdName.classList.add("renfort-person-name"); // classe CSS spécifique aux renforts
      }

      const div = document.createElement("div");
      div.classList.add("person-b");
      div.dataset.personnelId = p.Personnel_Id;
      div.textContent = p.nom_complet;

      // Listener clic différent selon type de personnel
      div.addEventListener('click', e => {
        e.stopPropagation();
        if (p.is_renfort) {
          showRenfortOptionsModal(p.Personnel_Id);
        } else {
          // gestion du clic personnel fixe ou aucun comportement
          console.log('Clic personnel classique ignoré');
        }
      });

      tdName.appendChild(div);
      tr.appendChild(tdName);

      const spanEquipe = document.createElement("span");
      const displayEquipe = p.Equipe.charAt(0);
      spanEquipe.textContent = `(${displayEquipe})`;
      spanEquipe.classList.add("person-equipe");
      div.appendChild(spanEquipe);

      weekDays.forEach(day => {
        const dateStr = day.toISOString().slice(0, 10);
        const filtered = activities.filter(a =>
          a.date === dateStr &&
          a.personnel.some(pp => pp.personnel_id === p.Personnel_Id)
        );

        const td = document.createElement("td");
        td.classList.add("day-cell");
        td.dataset.date = dateStr;
        td.dataset.personnelId = p.Personnel_Id;
        //if (p.is_renfort) {
          //td.classList.add('renfort-cell');
        //}
        const titresRepos = ["REPOS", "C.P.", "A.M.", "Congés", "Congé"];
        const estRepos = filtered.some(a => {
          const titre = a.titre.toUpperCase().trim();
          return titresRepos.includes(titre);
        });
        if (estRepos) {
          td.classList.add("cell-repos"); // classe css spéciale pour griser la cellule
        }

        // === Gestion poste via cycle équipe ===
        // Récupérer le shift pour ce personnel et ce jour
        const equipe = p.Equipe.charAt(0).toUpperCase(); // Ex: "C"
        const shift = shiftFor(equipe, day);             // "M", "A", "N", ou "R"

        // Si shift "R" (repos selon cycle), griser la cellule (si pas déjà en repos)
        if (!estRepos && shift === "R") {
          td.classList.add("cell-poste");
        }

        const zone = document.createElement("div");
        zone.classList.add("activity-droppable");

        const sortedActivities = filtered.sort((a, b) => (a.priorité ?? 2) - (b.priorité ?? 2));

        sortedActivities.forEach(act => {
          const wrapper = document.createElement("div");
          wrapper.className = "titre-act";
          wrapper.dataset.activityId = act.activite_id;
          wrapper.textContent = act.titre;
          wrapper.dataset.title = act.titre;
          wrapper.dataset.comment = act.commentaire || "—";
          wrapper.dataset.email = (act.personnel[0] || {}).email || "";

          const statusSpan = document.createElement("span");
          statusSpan.className = "statut-badge";
          statusSpan.textContent = getStatusEmoji(act.statut);
          statusSpan.title = `Statut : ${act.statut}`;
          statusSpan.style.cursor = "pointer";
          statusSpan.addEventListener("click", e => {
            e.stopPropagation();
            const activityDateStr = act.date;
            cycleStatut(act.activite_id, act.statut, activityDateStr);
          });
          wrapper.appendChild(statusSpan);

          wrapper.addEventListener("click", e => {
            e.stopPropagation();
            if (wrapper.pressHoldTriggered) {
              wrapper.pressHoldTriggered = false;
              return;
            }

            const modal = new bootstrap.Modal(
              document.getElementById('activityDetailsModal')
            );
            document.getElementById('detailTitle').textContent = wrapper.dataset.title;
            document.getElementById('detailComment').textContent = wrapper.dataset.comment;

            document.getElementById('btnEditActivity').onclick = () => {
              const activityId = wrapper.dataset.activityId;
              openEditActivityModal(activityId);
            };

            document.getElementById('btnDeleteActivity').onclick = async () => {
              const aid = wrapper.dataset.activityId;
              if (!confirm("Voulez-vous vraiment supprimer cette activité ?")) return;
              const res = await fetch(`/services/api/activities/${aid}`, { method: "DELETE" });
              if (res.ok) {
                modal.hide();
                loadWeek(getWeekStartDate(weekOffset));
              } else {
                alert("Erreur lors de la suppression.");
              }
            };

            document.getElementById('btnEmailActivity').onclick = () => {
              const to = wrapper.dataset.email;
              if (!to) return alert("Aucun email disponible.");
              const subject = encodeURIComponent("Relance activité : " + wrapper.dataset.title);
              const body = encodeURIComponent(
                "Bonjour,\n\n" +
                "Je vous relance concernant l’activité \"" + wrapper.dataset.title + "\"." +
                "\n\nCommentaire :\n" + wrapper.dataset.comment + "\n\nBonne journée."
              );
              window.location.href = `mailto:${to}?subject=${subject}&body=${body}`;
            };

            modal.show();
          });

          wrapper.setAttribute("draggable", "true");
          wrapper.addEventListener("dragstart", e => {
            e.dataTransfer.setData("activiteId", act.activite_id);
            e.dataTransfer.setData("oldPid", p.Personnel_Id);
            e.dataTransfer.setData("duplicate", e.ctrlKey ? "1" : "0");
          });

          zone.appendChild(wrapper);
        });

        td.appendChild(zone);

        td.addEventListener('mousedown', startPressAndHoldCell);
        td.addEventListener('mouseup', cancelPressAndHold);
        td.addEventListener('mouseleave', cancelPressAndHold);

        td.addEventListener('click', e => {
          if (e.target.closest('.activity-droppable')) return;
          // Actions optionnelles au clic sur la cellule vide
        });

        tr.appendChild(td);
      });

      fragment.appendChild(tr);
    });

  // --- Ligne infos journalières (pour le service) ---
  const infoTr = document.createElement('tr');
  const infoTh = document.createElement('td');
    infoTh.textContent = 'INFO';
  infoTh.classList.add('info-label');
  infoTr.appendChild(infoTh);

  console.log("window.serviceInfos keys:", Object.keys(window.serviceInfos));

  weekDays.forEach(day => {
    const dateStr = day.toISOString().slice(0, 10);
    const td = document.createElement('td');
    td.classList.add('day-cell', 'service-info-cell');
    td.dataset.date = dateStr;

    // Trouver la bonne clé dans window.serviceInfos en cherchant une clé qui commence par dateStr
    let infoHtml = '';
    if (window.serviceInfos) {
      if (window.serviceInfos[dateStr] !== undefined) {
        infoHtml = window.serviceInfos[dateStr];
      } else {
        // Recherche clé commençant par dateStr (cas date+heure)
        const foundKey = Object.keys(window.serviceInfos).find(k => k.startsWith(dateStr));
        if (foundKey) {
          infoHtml = window.serviceInfos[foundKey];
        }
      }
    }

    // Affichage avec retour à la ligne HTML
    td.innerHTML = `<div class="info-text">${infoHtml}</div>`;

    infoTr.appendChild(td);
  });

  fragment.appendChild(infoTr);

  tbody.appendChild(fragment);
  attachDayCellListeners();
  attachServiceInfoListeners();  // <-- à créer pour gérer le clic sur la ligne infos
}

/* --- Update month view in DOM ---
function updateMonthView(activities, year, month) {
  const table = document.querySelector("#month table tbody");
  table.innerHTML = "";

  const matrix = getMonthMatrix(year, month);
  matrix.forEach(week => {
    const tr = document.createElement("tr");
    week.forEach(day => {
      const td = document.createElement("td");
      if (day === 0) {
        td.innerHTML = "";
      } else {
        const dateStr = `${year}-${String(month).padStart(2,'0')}-${String(day).padStart(2,'0')}`;
        td.innerHTML = `<div>${day}</div>`;
        const dayActs = activities.filter(a => a.date === dateStr);
        const zone = document.createElement("div");
        zone.classList.add("zone-activities");

        dayActs.slice(0,2).forEach(act => {
          const dot = document.createElement("span");
          dot.className = "dot";
          const type = window.TYPES.find(t => t.type_id === act.type_id);
          dot.style.backgroundColor = type?.color || 'grey';
          dot.title = act.titre;
          zone.appendChild(dot);
        });
        if (dayActs.length > 2) {
          const extra = document.createElement("div");
          extra.className = "activity-count";
          extra.textContent = `+${dayActs.length - 2} autres…`;
          zone.appendChild(extra);
        }
        td.appendChild(zone);
      }
      tr.appendChild(td);
    });
    table.appendChild(tr);
  });

  const currentRange = document.getElementById("currentRange");
  const monthNames = ["Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Août","Septembre","Octobre","Novembre","Décembre"];
  currentRange.textContent = `📅 ${monthNames[month-1]} ${year}`;
}*/

async function openEditActivityModal(activityId) {
  const act = activitiesCache.find(a => a.activite_id == activityId);
  if (!act) {
    alert("Activité introuvable");
    return;
  }

  const modalElem = document.getElementById('editActivityModal');

  modalElem.querySelector('#editTitle').value = act.titre || '';
  modalElem.querySelector('#editComment').value = act.commentaire || '';

  // Gestion soumission formulaire
  const form = modalElem.querySelector('#editActivityForm');
  form.onsubmit = async (e) => {
    e.preventDefault();

    const payload = {
      titre: modalElem.querySelector('#editTitle').value.trim(),
      commentaire: modalElem.querySelector('#editComment').value.trim(),
    };

    try {
      const res = await fetch(`/services/api/activities/${activityId}/update`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Erreur lors de la mise à jour");
      pushLog("✏️ Activité mise à jour avec succès", "success");
      bootstrap.Modal.getInstance(modalElem).hide();
      loadWeek(getWeekStartDate(weekOffset));
    } catch (err) {
      pushLog(`❌ Échec mise à jour : ${err.message}`, "error");
    }
  };

  const modal = new bootstrap.Modal(modalElem);
  modal.show();
}

// ─── Déclarez d’abord attachDayCellListeners ──────────────────────────────
function attachDayCellListeners() {
  // gestion des clics sur cellules "classiques"
  document.querySelectorAll(".day-cell").forEach(cell => {
    // Ignore les cellules infos journalières et renfort
    if (cell.classList.contains('service-info-cell')) return;

    // ► clic pour ouvrir le modal
    cell.addEventListener("click", e => {
      if (e.target.closest('.activity-droppable')) return;
      currentPersonnelId = cell.dataset.personnelId;
      document.getElementById('activityPersonnel').value = currentPersonnelId;
      const date = cell.dataset.date;
      document.getElementById('activityDate').value = date;
      new bootstrap.Modal(
        document.getElementById('createActivityModal')
      ).show();
    });

    // ► autoriser le drop
    cell.addEventListener("dragover", e => e.preventDefault());

    // ► gérer le drop
    cell.addEventListener("drop", async e => {
      e.preventDefault();
      const aid       = e.dataTransfer.getData("activiteId");
      const oldPid    = e.dataTransfer.getData("oldPid");
      const duplicate = e.dataTransfer.getData("duplicate") === "1";
      const newDate   = cell.dataset.date;
      const newPid    = cell.dataset.personnelId;

      if (duplicate) {
        // duplication…
        const act = activitiesCache.find(a => a.activite_id == aid);
        if (!act) return console.error("Activité introuvable :", aid);
        const payload = {
          titre:     act.titre,
          type_id:   act.type_id,
          description: act.description,
          periode:   act.periode,
          date_real: newDate,
          priorité:  act.priorité ?? 2,
          statut:    act.statut,
          service_key: document.getElementById("currentRange")
                                .dataset.service.toUpperCase()
        };
        const res      = await fetch("/services/api/activities", {
          method:  "POST",
          headers: { "Content-Type": "application/json" },
          body:    JSON.stringify(payload)
        });
        const { activite_id: newAid } = await res.json();
        await fetch("/services/api/assign", {
          method:  "POST",
          headers: { "Content-Type": "application/json" },
          body:    JSON.stringify({ activite_id: newAid, personnel_id: newPid })
        });
      } else {
        // déplacement…
        const res = await fetch(
          `/services/api/activities/${aid}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              date_real:        newDate,
              old_personnel_id: oldPid,
              new_personnel_id: newPid
            })
          }
        );
        if (!res.ok) throw new Error("Erreur lors du déplacement");
      }

      loadWeek(getWeekStartDate(weekOffset));
    });
  });
  document.querySelectorAll('.renfort-cell').forEach(el => {
    el.addEventListener('click', () => {
      console.log('Renfort cliqué, personnelId:', el.dataset.personnelId);
    });
  });
}

function attachServiceInfoListeners() {
  document.querySelectorAll('.service-info-cell').forEach(td => {
    td.addEventListener('click', () => {
      const date = td.dataset.date;
      const existingText = window.serviceInfos?.[date] || '';
      showServiceInfoModal(date, existingText);
    });
  });
}

function showServiceInfoModal(date, text) {
  const modalContainer = document.getElementById('serviceInfoModal');
  modalContainer.querySelector('.modal-body').innerHTML = `
    <form id="serviceInfoForm">
      <div class="mb-3">
        <label for="infoDate" class="form-label">Date</label>
        <input type="date" class="form-control" id="infoDate" name="info_date" value="${date}" readonly>
      </div>
      <div class="mb-3">
        <label for="infoText" class="form-label">Information</label>
        <textarea class="form-control" id="infoText" name="info_text" rows="4" required>${text}</textarea>
      </div>
    </form>
  `;

  const modal = new bootstrap.Modal(modalContainer);
  modal.show();


  // Gestion sauvegarde
  const saveBtn = modalContainer.querySelector('#saveInfoBtn');
  saveBtn.onclick = async () => {
    const info_text = modalContainer.querySelector('#infoText').value.trim();
    if (!info_text) return alert('Le texte est obligatoire.');

    const payload = {
      info_date: date,
      service_code: document.getElementById('currentRange').dataset.service.toUpperCase(),
      info_text,
    };

    const res = await fetch('/services/api/service_info', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      alert('Erreur lors de la sauvegarde.');
      return;
    }
    window.serviceInfos[date] = info_text; // maj locale
    modal.hide();
    loadWeek(getWeekStartDate(weekOffset)); // rafraîchir
  };

  // Gestion suppression
  const deleteBtn = modalContainer.querySelector('#deleteInfoBtn');
  deleteBtn.onclick = async () => {
    if (!confirm("Voulez-vous vraiment supprimer cette info journalière ?")) return;

    const res = await fetch(`/services/api/service_info/${date}/${document.getElementById('currentRange').dataset.service}`, {
      method: 'DELETE'
    });
    if (!res.ok) {
      alert('Erreur lors de la suppression.');
      return;
    }
    delete window.serviceInfos[date]; // maj locale
    modal.hide();
    loadWeek(getWeekStartDate(weekOffset));
  };
}


// gestion du submit juste après…
function initCreateActivityForm() {
  document.getElementById('createActivityForm').addEventListener('submit', async e => {
    e.preventDefault();
    const titre   = document.getElementById('activityTitle').value.trim();
    const type_id = document.getElementById('activityType').value;
    const desc    = document.getElementById('activityComment').value.trim();
    const periode = document.querySelector('input[name="periode"]:checked').value;
    const date    = document.getElementById('activityDate').value;
    const service = document.getElementById('activityService').value;
    const personnelId = document.getElementById('activityPersonnel').value;

    const payload = { titre, type_id, commentaire: desc, periode,
                      date_real: date, priorité: 2, statut: "Planifié",
                      service_key: service };

    try {
      const res = await fetch("/services/api/activities", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("Erreur création activité");
      const { activite_id } = await res.json();

      const assignRes = await fetch("/services/api/assign", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ activite_id, personnel_id: personnelId })
      });
      if (!assignRes.ok) throw new Error("Erreur assignation");

      pushLog(`🆕 Activité créée et assignée à ${personnelId} pour ${date}`, "success");
      loadWeek(getWeekStartDate(weekOffset));
      bootstrap.Modal.getInstance(document.getElementById('createActivityModal')).hide();
    } catch (err) {
      pushLog("❌ Échec création/assignation", "error");
    }
  });
}

// 3) Chargement initial
document.addEventListener("DOMContentLoaded", () => {
  initCreateActivityForm();
  console.log("✅ Démarrage, semaine 0 =", initialWeekStart);
  loadWeek(initialWeekStart);
});

function getStatusEmoji(statut) {
  switch (statut) {
    case "Planifié": return "📅";
    case "En cours": return "🔄";
    case "Effectué": return "🟢";
    case "En retard": return "🔴";
    case "Annulé": return "❌";
    case "À valider": return "🟡";
    default: return "❔";
  }
}

function cycleStatut(aid, current, activityDateStr) {
  const statutFutur = ["Planifié", "Effectué", "En retard"];
  const statutJourJ = ["En cours", "Effectué", "En retard"];
  const statutPasse = ["En retard", "Effectué"];

  const today = new Date().setHours(0,0,0,0);
  const actDate = new Date(activityDateStr).setHours(0,0,0,0);

  let validStatusList;

  if (actDate > today) {
    validStatusList = statutFutur;
  } else if (actDate === today) {
    validStatusList = statutJourJ;
  } else {
    validStatusList = statutPasse;
  }

  let currentIndex = validStatusList.indexOf(current);

  if (currentIndex === -1) currentIndex = 0;

  const nextIndex = (currentIndex + 1) % validStatusList.length;
  const next = validStatusList[nextIndex];

  console.log(`🔁 Cycle statut : ${current} ➜ ${next} (activité ${aid})`);

  fetch(`/services/api/activities/${aid}/status`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ statut: next })
  })
  .then(res => {
    console.log("📡 Réponse statut :", res.status);
    if (!res.ok) throw new Error("Erreur mise à jour statut");
    return res.json();
  })
  .then(() => {
    pushLog(`🔁 Statut mis à jour : ${current} ➜ ${next} (activité ${aid})`, "info");
    loadWeek(getWeekStartDate(weekOffset));
  })
  .catch(err => {
    console.error("❌ Erreur maj statut :", err);
    pushLog(" Impossible de modifier le statut de l’activité", "error");
  });
}

function formatDateHeure(isoString) {
  const d = new Date(isoString);
  // options pour jour et mois en français
  const dateOpts = { day: 'numeric', month: 'long' };
  const heureOpts = { hour: '2-digit', minute: '2-digit' };
  // ex: "22 mai"
  const datePart = d.toLocaleDateString('fr-FR', dateOpts);
  // ex: "12:42"
  const heurePart = d.toLocaleTimeString('fr-FR', heureOpts);
  return `${datePart} ${heurePart}`;
}

async function loadReport() {
  const res = await fetch("/services/api/report");
  if (!res.ok) {
    console.warn('Report non disponible:', res.status);
    document.getElementById('report-content').innerHTML =
      '<p>Rapport indisponible pour le moment.</p>';
    return;
  }
  // Vous pouvez aussi vérifier Content-Type
  const contentType = res.headers.get('Content-Type') || '';
  if (!contentType.includes('application/json')) {
    console.error('Report renvoie du HTML ou un autre format.');
    return;
  }
  const data = await res.json();

  const container = document.getElementById("report-content");
  container.innerHTML = data.length
    ? data.map(r => `<div>• ${r.message}</div>`).join("")
    : "<p>Aucun événement significatif hier.</p>";
}

async function loadWarnings() {
  const res = await fetch("/services/api/supervision");
  const container = document.getElementById("warning-content");
  if (!res.ok) {
    container.innerHTML = `<div class="warning-card">Rapport indisponible pour le moment.</div>`;
    return;
  }
  const data = await res.json();
  if (!data.length) {
    container.innerHTML = `<div class="warning-card">Aucun défaut actif.</div>`;
    return;
  }
  container.innerHTML = data.map(w => `
    <div class="warning-card">
      <h4>${w.description}</h4>
      <p><strong>Machine :</strong> ${w.machine}</p>
      <p><strong>Début :</strong> ${formatDateHeure(w.start)}</p>
      <p><strong>Fin :</strong> ${formatDateHeure(w.end)}</p>
      <p><strong>Durée :</strong> ${w.duration}</p>
    </div>
  `).join("");
}

setInterval(loadWarnings, 10000); // toutes les 10 secondes
document.addEventListener("DOMContentLoaded", () => {
  loadReport();
  loadWarnings();
});

// Recharge les renforts existants (dans le modal)
async function loadExistingRenforts() {
  const res = await fetch(`/services/api/all_renforts`);
  if (!res.ok) {
    console.error("Erreur chargement renforts");
    return;
  }
  const renforts = await res.json();

  const select = document.getElementById('existingRenfortSelect');
  const nomInput = document.getElementById('renfortName');
  const equipeSelect = document.getElementById('renfortEquipe');

  select.innerHTML = '<option value="">-- Choisir un renfort existant --</option>';

  select.onchange = () => {
    const selId = select.value;
    if (!selId) {
      nomInput.value = '';
      nomInput.disabled = false;
      equipeSelect.value = '';
      equipeSelect.disabled = false;
    } else {
      const renfort = renforts.find(r => r.Personnel_Id === selId);
      if (renfort) {
        nomInput.value = renfort.nom_complet.trim();
        nomInput.disabled = true;
        equipeSelect.value = renfort.Equipe;
        equipeSelect.disabled = true;
      }
    }
  };

  if (Array.isArray(renforts)) {
    renforts.forEach(r => {
      const opt = document.createElement('option');
      opt.value = r.Personnel_Id;
      opt.textContent = `${r.nom_complet.trim()} (${r.Equipe}) - ${r.is_active ? 'Actif' : 'Inactif'}`;
      select.appendChild(opt);
    });
  }
}



document.getElementById('renfortModal').addEventListener('shown.bs.modal', () => {
  loadExistingRenforts();
});
// Fonction pour soumettre un nouveau renfort avec validation et gestion équipe
async function submitRenfort() {
  const nom = document.getElementById("renfortName").value.trim();
  const debut = document.getElementById("renfortDebut").value;
  const fin = document.getElementById("renfortFin").value;
  const service = document.getElementById("currentRange").dataset.service.toUpperCase();
  const equipe = document.getElementById("renfortEquipe").value;

  if (!nom || !debut || !fin) {
    alert("Tous les champs sont requis.");
    return;
  }

  if (debut > fin) {
    alert("La date de début doit être inférieure ou égale à la date de fin.");
    return;
  }

  if (!equipe) {
    alert("Veuillez sélectionner une équipe.");
    return;
  }

  const submitBtn = document.querySelector('#renfortModal .btn-success');
  submitBtn.disabled = true;
  submitBtn.textContent = 'Envoi...';

  const from = getWeekStartDate(weekOffset);
  const toDate = new Date(from);
  toDate.setDate(toDate.getDate() + 6);
  const to = toDate.toISOString().slice(0, 10);

  try {
    const existingRes = await fetch(`/services/api/all_renforts`);
    if (!existingRes.ok) throw new Error('Erreur chargement renforts existants');
    const existingRenforts = await existingRes.json();

    // 2. Chercher un renfort correspondant (exemple : même nom + équipe + service)
    const renfortTrouve = existingRenforts.find(r =>
      r.nom_complet.toLowerCase() === nom.toLowerCase()
      && r.Equipe.toLowerCase() === equipe.toLowerCase()
    );

    let personnel_id;

    if (renfortTrouve) {
      // Renfort existant trouvé, on le réutilise
      personnel_id = renfortTrouve.Personnel_Id;
      console.log(`Renfort existant trouvé : ${nom} (${personnel_id})`);
    } else {
      // Pas trouvé, on crée un nouveau renfort
      const payload = {
        nom_complet: nom,
        date_debut: debut,
        date_fin: fin,
        role: "renfort",
        service_code: service,
        equipe: equipe
      };

      const createRes = await fetch("/services/api/renfort", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!createRes.ok) {
        const errorData = await createRes.json().catch(() => ({}));
        const msg = errorData.error || 'Échec de la création du renfort';
        throw new Error(msg);
      }
      const data = await createRes.json();
      personnel_id = data.personnel_id;
      console.log(`Nouveau renfort créé : ${nom} (${personnel_id})`);
    }

    pushLog(`➕ Renfort enregistré : ${nom}`, "success");
    document.getElementById("renfortForm").reset();
    bootstrap.Modal.getInstance(document.getElementById("renfortModal")).hide();

    // Recharge la liste ou la page comme tu souhaites
    loadExistingRenforts();
    document.getElementById("renfortForm").reset();

  } catch (err) {
    pushLog(`❌ Erreur ajout renfort : ${err.message}`, "error");
    alert(`Erreur lors de l'ajout du renfort : ${err.message}`);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Ajouter';
  }
  window.location.reload();
}

// Fonction pour afficher la modal d'options pour un renfort donné
function showRenfortOptionsModal(personnelId) {
  window.currentRenfortId = personnelId;

  const modal = new bootstrap.Modal(document.getElementById('renfortOptionsModal'));
  modal.show();

  const form = document.getElementById('renfortOptionsForm');
  form.reset();

  // Gestion de la prolongation de la date fin
  form.onsubmit = async e => {
    e.preventDefault();
    const newDateFin = form.renfortDateFin.value;
    if (!newDateFin) {
      alert("Veuillez renseigner une date valide");
      return;
    }
    try {
      const res = await fetch(`/services/api/renfort/${window.currentRenfortId}/prolonger`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({date_fin: newDateFin}),
      });
      if (!res.ok) {
        let errMsg = "Erreur lors de la prolongation";
        try {
          const errorData = await res.json();
          if (errorData.description) {
            errMsg = errorData.description;
            if (errorData.current_date_fin) {
              errMsg += ` (date actuelle : ${errorData.current_date_fin})`;
            }
          } else if (errorData.message) {
            errMsg = errorData.message;
          }
        } catch {
          // JSON invalide, message par défaut
        }
        throw new Error(errMsg);
      }
      alert("Date prolongée avec succès");
      modal.hide();
      loadWeek(getWeekStartDate(weekOffset));
    } catch (err) {
      alert(err.message);
    }
    loadWeek(getWeekStartDate(weekOffset));

  };
  // Bouton retirer du planning
  document.getElementById('retirerRenfortBtn').onclick = async () => {
    if (!confirm("Voulez-vous retirer ce renfort du planning ?")) return;
    try {
      const res = await fetch(`/services/api/renfort/${window.currentRenfortId}/retirer`, { method: 'POST' });
      if (!res.ok) throw new Error("Erreur lors du retrait");
      alert("Renfort retiré du planning");
      modal.hide();
      loadWeek(getWeekStartDate(weekOffset));
    } catch (err) {
      alert(err.message);
    }
  };
  /* Bouton supprimer définitivement
  document.getElementById('supprimerRenfortBtn').onclick = async () => {
    if (!confirm("Voulez-vous supprimer définitivement ce renfort ?")) return;
    try {
      const res = await fetch(`/services/api/renfort/${window.currentRenfortId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error("Erreur lors de la suppression");
      alert("Renfort supprimé définitivement");
      modal.hide();
      loadWeek(getWeekStartDate(weekOffset));
    } catch (err) {
      alert(err.message);
    }
  };*/
}
document.getElementById('printPlanningBtn').addEventListener('click', () => {
  // Trouver la vue active (semaine ou mois)
  const activeCalendar = document.querySelector('.calendar.active');
  if (!activeCalendar) {
    alert("Aucune vue active pour impression.");
    return;
  }

  const contentToPrint = activeCalendar.innerHTML;
  const printWindow = window.open('', '', 'width=900,height=700');

  printWindow.document.write('<html><head><title>Impression Planning</title>');
  // Charge le(s) fichier(s) CSS nécessaires, adapte selon ton projet
  printWindow.document.write('<link rel="stylesheet" href="/static/css/style.css">');
  printWindow.document.write(`<link rel="stylesheet" href="${servicesStaticPath}css/style_services.css">`);
  printWindow.document.write('</head><body>');
  printWindow.document.write(contentToPrint);
  printWindow.document.write('</body></html>');

  printWindow.document.close();
  printWindow.focus();

  setTimeout(() => {
    printWindow.print();
    printWindow.close();
  }, 250);
});
