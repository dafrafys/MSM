// Redirige selon la date choisie
function goToDate() {
    const date = document.getElementById("datePicker").value;
    const errorElement = document.getElementById("dateError");

    if (!date) {
        errorElement.textContent = "Veuillez choisir une date avant de continuer.";
        return;
    }

    // Pas d'erreur -> on efface le message
    errorElement.textContent = "";

    // Redirige proprement vers la même page avec la date
    const baseUrl = "{{ url_for('HuddleHome') }}";
    window.location.href = `${baseUrl}?session_date=${date}`;
}


// Décode les séquences \uXXXX / \UXXXXXXXX en vrais caractères (émoticônes…)
function decodeUnicode(str) {
  return str
    .replace(/\\U([0-9A-Fa-f]{8})/g, (_, g1) => String.fromCodePoint(parseInt(g1, 16)))
    .replace(/\\u([0-9A-Fa-f]{4})/g, (_, g1) => String.fromCharCode(parseInt(g1, 16)));
}
// ------- Badge & Panel -------

const icon   = document.getElementById('bg-status-icon');
const panel  = document.getElementById('bg-status-panel');
const listEl = document.getElementById('bg-status-list');
const badge  = document.getElementById('bg-status-badge');

// Mémorise combien de logs on a déjà chargé depuis le serveur
let previousLogCount = 0;

// Affiche / masque le panneau
function toggleBgPanel() {
  panel.style.display = panel.style.display === 'block' ? 'none' : 'block';
  if (panel.style.display === 'block') {
    loadBgLogs();
    // Quand on ouvre, on considère qu'on a "lu" les nouveaux logs serveur
    previousLogCount = 0;
    badge.style.display = 'none';
  }
}

// ------- Chargement & affichage des logs (avec préservation des logs locaux) -------

async function loadBgLogs() {
  try {
    const res = await fetch('/api/logs');
    const { logs } = await res.json();

    // 1. Récupère tous les messages déjà affichés (locaux ou serveurs)
    const existingMessages = new Set(
      Array.from(listEl.querySelectorAll("li")).map(li => li.textContent)
    );

    // 2. Ajoute les logs serveur qui ne sont pas encore présents
    logs.forEach(line => {
      const decoded = decodeUnicode(line);
      if (!existingMessages.has(decoded)) {
        const li = document.createElement('li');
        li.textContent = decoded;
        li.classList.add('server-log');
        listEl.appendChild(li);
      }
    });

    // 3. Met à jour le badge si nouveaux logs serveur
    const newCount = logs.length - previousLogCount;
    if (newCount > 0) {
      badge.textContent = newCount;
      badge.style.display = 'inline-flex';
    } else {
      badge.style.display = 'none';
    }

    previousLogCount = logs.length;
  }
  catch (e) {
    console.error('Impossible de charger les logs :', e);
  }
}
// ------- Réception de logs plan d'action -------

function handlePlanActionResponse(json) {
  const time = new Date().toLocaleTimeString();
  const li = document.createElement('li');
  li.classList.add('local-log');
  if (json.excel_ok) {
    li.textContent = `✅ [${time}] Export Excel réussi`;
  } else {
    li.textContent = `⚠️ [${time}] Excel : ${json.excel_msg}`;
  }
  listEl.prepend(li);

  panel.style.display = 'block';
  badge.style.display = 'none';


  // Incrémente le badge (nouveau message local)
  const current = parseInt(badge.textContent || '0', 10);
  badge.textContent = current + 1;
  badge.style.display = 'inline-flex';
}

// ------- Log enrichi (générique) -------

function pushLog(message, type = "info") {
  const time = new Date().toLocaleTimeString();
  const li = document.createElement("li");
  li.textContent = `[${time}] ${message}`;
  li.className = `log-item log-${type}`;
  li.classList.add('local-log');
  listEl.prepend(li);

  // Met à jour le badge
  const current = parseInt(badge.textContent || "0", 10);
  badge.textContent = current + 1;
  badge.style.display = "inline-flex";

  // 🟢 Ouvre automatiquement le panneau si fermé
  if (panel.style.display !== 'block') {
    panel.style.display = 'block';
    previousLogCount = 0;  // on considère que tout est nouveau
    badge.style.display = 'none';
  }
}

// ------- Gestion stockage local (facultatif, si tu veux persister les logs) -------

function saveLogsToLocal(logs) {
  localStorage.setItem('logs', JSON.stringify(logs));
}

function loadLogsFromLocal() {
  const raw = localStorage.getItem('logs');
  return raw ? JSON.parse(raw) : [];
}

// ------- Nettoyage manuel -------

function clearLogs() {
  listEl.innerHTML = '';
  badge.textContent = '0';
  badge.style.display = 'none';
  localStorage.removeItem('logs');
}

// ------- Initialisation -------

icon.addEventListener('click', toggleBgPanel);
window.handlePlanActionResponse = handlePlanActionResponse;
