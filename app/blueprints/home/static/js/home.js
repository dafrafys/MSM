// home.js - Comportements de la page Huddle Home
document.getElementById('start-session-btn')
  .addEventListener('click', async () => {
    try {
      const res = await fetch('/start-session', { method: 'POST' });
      const data = await res.json();
      const statusEl = document.getElementById('session-status');

      if (data.status === 'success') {
        statusEl.innerText = `Session Huddle démarrée avec l'ID: ${data.Session_Id}`;
        await fetch('/api/clear_logs', { method: 'POST' });
        document.getElementById('bg-status-list').innerHTML = '';
        previousLogCount = 0;
        badge.style.display = 'none';
        pushLog(`🟢 Session Huddle #${data.Session_Id} démarrée`, 'success');
      } else {
        statusEl.innerText = `Erreur: ${data.message || 'Inconnue'}`;
        pushLog(`❌ Erreur démarrage session : ${data.message}`, 'error');
      }
    } catch (err) {
      console.error('Erreur démarrage session:', err);
      document.getElementById('session-status').innerText =
        'Erreur de connexion au serveur.';
    }
  });

function goToDate() {
    const date = document.getElementById("datePicker").value;
    const errorElement = document.getElementById("dateError");

    if (!date) {
        errorElement.textContent = "Veuillez choisir une date avant de continuer.";
        return;
    }

    errorElement.textContent = "";

      // Ici url_for sera interprété par Jinja côté serveur
    const baseUrl = document.body.dataset.baseUrl;
    window.location.href = `${baseUrl}?session_date=${date}`;
}

// Ferme le formulaire
function closeForm() {
  document.getElementById('impact-form-panel').classList.remove('open');
  document.getElementById('impact-form-overlay').classList.remove('show');
}

// Ouvre et préremplit le formulaire avec les données de l'impact
function openFormWithData(data) {
  const impact = data.impact;
  const form   = document.querySelector('.impact-form');

  // On met aussi à jour le champ caché impact_id
  form.querySelector('input[name="impact_id"]').value = impact.Impact_Id || impact.impact_id;

  // Préremplissage des champs
  form.querySelector('select[name="type_analyse"]'   ).value = impact.type_analyse    || 'Non couverte';
  form.querySelector('input[name="cause"]'           ).value = impact.cause           || '';
  form.querySelector('textarea[name="action"]'       ).value = impact.action          || '';
  form.querySelector('textarea[name="commentaire"]'  ).value = impact.commentaire     || '';
  form.querySelector('select[name="pilot_id"]'       ).value = impact.pilot_id        || '';
  form.querySelector('input[name="echeance"]'        ).value = impact.echeance        || '';
  form.querySelector('select[name="statut"]'         ).value = impact.statut          || 'En cours';
  //form.querySelector('input[name="priority"]'        ).value = impact.priority        || '';

  // Affichage du modal
  document.getElementById('impact-form-overlay').classList.add('show');
  document.getElementById('impact-form-panel'  ).classList.add('open');
}

document.getElementById('start-session-btn').addEventListener('click', function() {
  const btn = this;
  btn.disabled = true;
  btn.textContent = 'Démarrage en cours...';

  fetch('/start-session', { method: 'POST' })
    .then(response => response.json())
    .then(data => {
      if(data.status === 'success'){
        document.getElementById('session-status').textContent = `Session démarrée avec l'ID ${data.Session_Id}`;
      } else {
        document.getElementById('session-status').textContent = `Erreur : ${data.message || 'Problème lors du démarrage.'}`;
        btn.disabled = false;
        btn.textContent = 'Démarrer la session Huddle';
      }
    })
    .catch(() => {
      document.getElementById('session-status').textContent = 'Erreur réseau lors du démarrage.';
      btn.disabled = false;
      btn.textContent = 'Démarrer la session Huddle';
    });
});


// Initialisation au chargement de la page
document.addEventListener('DOMContentLoaded', () => {

  // lie le clic sur l'icône à l'ouverture/fermeture du panneau
  const icon = document.getElementById('bg-status-icon');
  if (icon) {
    icon.addEventListener('click', toggleBgPanel);
  }

  // Gestion des cartes d'impact
  document.querySelectorAll('.impact-card').forEach(card => {
    card.addEventListener('click', () => {
      const wasFocused = card.classList.contains('focused');
      document.querySelectorAll('.impact-card.focused')
              .forEach(c => c.classList.remove('focused'));

      if (!wasFocused) {
        card.classList.add('focused');

        // 1) On récupère l'ID et on l’injecte dans le titre
        const impactId = card.dataset.impactId;
        // console.log('impactId →', impactId);

        document.getElementById('impact-form-title').textContent =
          `Plan d'action – Impact #${impactId}`;

        // 3) On remplit **immédiatement** le champ caché
        document.querySelector('input[name="impact_id"]').value = impactId;

        // 2) On ouvre immédiatement le modal
        document.getElementById('impact-form-overlay').classList.add('show');
        document.getElementById('impact-form-panel').classList.add('open');

        // 3) Puis, en tâche de fond, on fetch pour préremplir les champs
        fetch(`/api/impact/${impactId}`)
          .then(r => r.ok ? r.json() : Promise.reject(r.status))
          .then(data => {
            console.log("Détails impact reçus :", data);
            openFormWithData(data);
          })
          .catch(err => console.error('Erreur fetch impact :', err));
      } else {
        closeForm();
      }

      document.querySelector('.impact-container')
              .classList.toggle('focus-active',
                                !!document.querySelector('.impact-card.focused'));
    });

    const closeBtn = card.querySelector('.close-btn');
    if (closeBtn) {
      closeBtn.addEventListener('click', ev => {
        ev.stopPropagation();
        card.classList.remove('focused');
        closeForm();
        document.querySelector('.impact-container')
                .classList.toggle('focus-active',
                                  !!document.querySelector('.impact-card.focused'));
      });
    }
  });

  // Interception du form PLAN D'ACTION
  const planForm = document.querySelector('.impact-form');
  if (!planForm) return;

  planForm.addEventListener('submit', function(e) {
    e.preventDefault();
    // e.currentTarget est bien ton <form>
    const form = e.currentTarget;
    const url  = form.getAttribute('action');  // "/update_plan_action"
    const data = new FormData(form);

    console.log('Envoi AJAX vers', url);

    fetch(url, {
      method: 'POST',
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      body: data
    })
    .then(r => r.json())
    .then(json => {
      if (json.status === 'success') {
        pushLog(`📝 Plan d'action enregistré pour impact #${data.get('impact_id')}`, 'success');
        handlePlanActionResponse(json);
        closeForm();
        const flashEl = document.createElement('div');
        flashEl.className = 'flash success';
        flashEl.innerText = 'Plan d’action enregistré ✅';
        document.body.prepend(flashEl);
        setTimeout(() => flashEl.remove(), 3000);
      } else {
        const flashEl = document.createElement('div');
        flashEl.className = 'flash error';      // même style que tes erreurs existantes
        flashEl.innerText = 'Veuillez remplir tous les champs du plan d’action.';
        pushLog(`⚠️ Échec enregistrement plan d’action`, 'warning');
      }
    })
    .catch(err => {
      console.error('Erreur AJAX update_plan_action', err);
      alert('Erreur de connexion au serveur.');
    });
  });

});

// Gestion Impact 31 Jours
document.addEventListener('DOMContentLoaded', () => {
  const btn                = document.getElementById('toggle-range');
  const rangeLabel         = document.querySelector('.current-range');
  const fibrageContainer   = document.getElementById('fibrage-container');
  const finissageContainer = document.getElementById('finissage-container');

  if (!btn || !rangeLabel || !fibrageContainer || !finissageContainer) return;

  let sliding = false;
  const initialRange = rangeLabel.textContent.trim();

  btn.addEventListener('click', () => {
    sliding = !sliding;
    btn.classList.toggle('is-sliding', sliding);
    rangeLabel.textContent = sliding ? '31 derniers jours' : initialRange;

    const fibUrl = sliding ? '/cards/31days/fibrage'   : '/cards/month/fibrage';
    const finUrl = sliding ? '/cards/31days/finissage' : '/cards/month/finissage';

    // Nettoyage si on revient au mois simple
    if (!sliding) {
      // Recharger les données du mois uniquement
      fetch(fibUrl)
        .then(r => r.ok ? r.text() : Promise.reject(r.status))
        .then(html => {
          fibrageContainer.innerHTML = html;
        })
        .catch(err => console.error('Erreur Fibrage (mois):', err));

      fetch(finUrl)
        .then(r => r.ok ? r.text() : Promise.reject(r.status))
        .then(html => {
          finissageContainer.innerHTML = html;
        })
        .catch(err => console.error('Erreur Finissage (mois):', err));

      return;
    }

    // Sinon, on est en mode "mois + 31 jours"
    // Fibrage
    fetch(fibUrl)
      .then(r => r.ok ? r.text() : Promise.reject(r.status))
      .then(html => {
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;
        const newCards = Array.from(tempDiv.querySelectorAll('.impact-card'));

        const existingCards = Array.from(fibrageContainer.querySelectorAll('.impact-card'));

        // Filtrer pour éviter doublons
        const existingIds = new Set(existingCards.map(c => c.dataset.impactId));
        const filteredNewCards = newCards.filter(c => !existingIds.has(c.dataset.impactId));

        // Fusionner
        const allCards = existingCards.concat(filteredNewCards);

        // Trier par date décroissante (en supposant que tu as data-impact-date au format ISO)
        allCards.sort((a, b) => {
          const dateA = new Date(a.dataset.impactDate);
          const dateB = new Date(b.dataset.impactDate);
          if (isNaN(dateA)) return 1;
          if (isNaN(dateB)) return -1;
          return dateB - dateA; // ordre décroissant
        });

        // Vider et recharger le container
        fibrageContainer.innerHTML = '';
        allCards.forEach(card => fibrageContainer.appendChild(card));
      })
      .catch(err => console.error('Erreur Fibrage (31j):', err));
    // Finissage
    fetch(finUrl)
      .then(r => r.ok ? r.text() : Promise.reject(r.status))
      .then(html => {
        console.log("Chargement impacts finissage reçu, taille HTML:", html.length);
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;

        // Log chaque impact chargé (juste un exemple)
        const impacts = Array.from(tempDiv.querySelectorAll('.impact-card'));
        console.log(`Nombre d'impacts finissage dans la réponse: ${impacts.length}`);
        impacts.forEach(card => {
          console.log(`Impact ID ${card.dataset.impactId}, pertes:`, card.querySelector('.info strong + ul')?.innerText || "Pas de pertes détaillées visibles");
        });

        const newCards = Array.from(tempDiv.querySelectorAll('.impact-card'));

        const existingCards = Array.from(finissageContainer.querySelectorAll('.impact-card'));

        // Filtrer pour éviter doublons
        const existingIds = new Set(existingCards.map(c => c.dataset.impactId));
        const filteredNewCards = newCards.filter(c => !existingIds.has(c.dataset.impactId));

        // Fusionner
        const allCards = existingCards.concat(filteredNewCards);

        // Trier par date décroissante
        allCards.sort((a, b) => {
          const dateA = new Date(a.dataset.impactDate);
          const dateB = new Date(b.dataset.impactDate);
          return dateB - dateA;
        });

        // Vider et recharger le container
        finissageContainer.innerHTML = '';
        allCards.forEach(card => finissageContainer.appendChild(card));
      })
      .catch(err => console.error('Erreur Finissage (31j):', err));
  });
});



// Fonctions pour la gestion des activités (drag & drop) ----> à retirer !!
let targetCell;

function openActivityModal(td) {
  targetCell = td;
  document.getElementById('actTitle').value = '';
  document.getElementById('activityModal').style.display = 'block';
}

function createActivity() {
  const titre = document.getElementById('actTitle').value.trim();
  const typeId = document.getElementById('actType').value;
  if (!titre) { alert('Titre requis'); return; }

  fetch('/api/activities', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ titre, type_id: typeId, date_real: targetCell.dataset.date })
  })
  .then(r => r.json())
  .then(data => {
    targetCell.innerHTML = `
      <div class="titre-act">\${titre}</div>
      <div class="zone-personnes" data-act-id="\${data.activite_id}"></div>
    `;
    targetCell.ondrop = drop;
    closeModal();
  });
}

function drop(ev) {
  ev.preventDefault();
  const nom = ev.dataTransfer.getData('text');
  const zone = ev.target.closest('.zone-personnes');
  const actId = zone.dataset.actId;
  if ([...zone.children].some(el => el.innerText === nom)) return;

  fetch('/api/assign', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ activite_id: actId, nom_complet: nom })
  });

  const badge = document.createElement('span');
  badge.className = 'person';
  badge.innerText = nom;
  badge.ondblclick = () => removePerson(actId, nom, badge);
  zone.appendChild(badge);
}

// Filtre sur les accidents !
document.addEventListener('DOMContentLoaded', () => {
  const filterSelect = document.getElementById('accident-filter');
  const accidentItems = document.querySelectorAll('.accident-item');

  if (!filterSelect) return;

  filterSelect.addEventListener('change', () => {
    const selected = filterSelect.value;
    accidentItems.forEach(item => {
      const service = item.dataset.service;
      item.style.display = (selected === 'all' || service === selected) ? '' : 'none';
    });
  });
});
