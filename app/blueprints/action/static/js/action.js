let table;
let addModal, bootstrapAddModal;
let editModal, bootstrapEditModal;

function dateFormatter(cell) {
  let val = cell.getValue();
  if (!val) return "";
  let d = new Date(val);
  if (isNaN(d)) return val;
  return d.toLocaleDateString('fr-FR');
}

document.addEventListener('DOMContentLoaded', () => {
  // Charger liste personnel pour selects ajout + edition (édition readonly, affichage uniquement)
  fetch('/action/api/personnel')
    .then(res => res.json())
    .then(data => {
      // Select ajout (modifiable)
      const selectAdd = document.getElementById('newPersonnelId');
      data.forEach(person => {
        const option = document.createElement('option');
        option.value = person.id;
        option.textContent = person.name;
        selectAdd.appendChild(option);
      });
    })
    .catch(err => {
      console.error('Erreur chargement personnel:', err);
      alert('Impossible de charger la liste du personnel');
    });

  // Formatter date au format français
  function dateFormatter(cell) {
    let val = cell.getValue();
    if (!val) return "";
    let d = new Date(val);
    if (isNaN(d)) return val;
    return d.toLocaleDateString('fr-FR');
  }

  // Initialiser Tabulator
  table = new Tabulator("#planActionTable", {
    ajaxURL: "/action/api/plan-actions",
    ajaxConfig: "GET",
    ajaxFiltering: true, // active le filtrage côté serveur si supporté
    ajaxParams: { date_cloture: null }, // filtre envoyé au backend pour exclure clôturées
    ajaxResponse: function(url, params, response){
      console.log("Données reçues:", response);
      return response;
    },
    layout: "fitColumns",
    pagination: "local",
    paginationSize: 25,
    columns: [
      {title: "ID", field: "plan_id", hozAlign: "center", width: 50, headerSort: false},
      {title: "Date", field: "date", formatter: dateFormatter, width: 90},
      {title: "Type", field: "type", width: 100},
      {title: "Sujet", field: "sujet", width: 150, formatter:"textarea"},
      {title: "Statut", field: "statut", width: 100, hozAlign: "center",
      formatter: function(cell) {
          const progress = Number(cell.getValue()) || 0;
          let tooltipText = "";
          switch(progress) {
            case 0: tooltipText = "Pas commencé"; break;
            case 0.25: tooltipText = "Ouvert"; break;
            case 0.5: tooltipText = "En cours"; break;
            case 0.75: tooltipText = "Vérification"; break;
            case 1: tooltipText = "Terminé"; break;
            default: tooltipText = "Statut inconnu";
          }
          cell.getElement().setAttribute("title", tooltipText);
          return progressPieFormatter(cell);
        },
        cellClick: function(e, cell) {
          let progressValues = [0, 0.25, 0.5, 0.75, 1];
          let current = cell.getValue();
          let nextIndex = (progressValues.indexOf(current) + 1) % progressValues.length;
          let nextValue = progressValues[nextIndex];

          // Si on passe à la clôture (statut 1), demander confirmation
          if (nextValue === 1) {
            if (!confirm("Clôturer cette action ?")) {
              return; // Annuler l'action si refus
            }
          }

          const rowData = cell.getRow().getData();
          fetch('/action/api/plan-actions', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
              plan_id: rowData.plan_id,
              statut: nextValue,
              commentaire: rowData.commentaire || "",
              delai_revise: rowData.delai_revise || ""
            })
          }).then(res => res.json())
            .then(resp => {
              if (resp.success) {
                cell.setValue(nextValue);
              } else {
                alert('Erreur mise à jour statut');
              }
            }).catch(() => alert('Erreur réseau'));
        }
      },
      {title: "Action", field: "action", formatter:"textarea", widthGrow: 2, headerSort: false},
      {title: "Pilote", field: "pilote_nom", width: 140},
      {title: "Délai initial", field: "delai_initiale", formatter: dateFormatter, width: 100},
      {title: "Délai révisé", field: "delai_revise", formatter: dateFormatter, width: 100},
      {title: "Commentaire", field: "commentaire", formatter:"textarea", widthGrow: 2, headerSort: false},
      {
        title: "Mise à jour / Suppression",
        hozAlign: "center",
        width: 140,
        formatter: function(cell) {
          return `
            <button class="btn btn-sm btn-primary btn-edit">Modifier</button>
            <button class="btn btn-sm btn-danger btn-delete ms-2">×</button>
          `;
        },
        cellClick: function(e, cell) {
          if (e.target.classList.contains('btn-edit')) {
            openEditModal(cell.getRow().getData());
          } else if (e.target.classList.contains('btn-delete')) {
            if (confirm('Confirmer la suppression ?')) {
              const planId = cell.getRow().getData().plan_id;
              fetch(`/action/api/plan-actions/${planId}`, {
                method: 'DELETE'
              })
              .then(res => res.json())
              .then(resp => {
                if (resp.success) {
                  alert('Plan d\'action supprimé !');
                  table.replaceData();
                } else {
                  alert('Erreur : ' + resp.message);
                }
              })
              .catch(() => alert('Erreur réseau'));
            }
          }
        }
      }
    ],
  });

  // Initialisation de la deuxième table (clôturée)
  closedTable = new Tabulator("#planActionClotureTable", {
    ajaxURL: "/action/api/plan-actions?date_cloture=cloture",  
    ajaxConfig: "GET",
    layout: "fitColumns",
    pagination: "local",
    paginationSize: 25,
    columns: [
      {title: "ID", field: "plan_id", hozAlign: "center", width: 60},
      {title: "Date", field: "date", formatter: dateFormatter, width: 90},
      {title: "Type", field: "type", width: 100},
      {title: "Sujet", field: "sujet", width: 150},
      {title: "Statut", field: "statut", width: 100, hozAlign: "center", formatter: progressPieFormatter},
      {title: "Action", field: "action", formatter: "textarea", widthGrow: 2},
      {title: "Pilote", field: "pilote_nom", width: 140},
      {title: "Délai initial", field: "delai_initiale", formatter: dateFormatter, width: 100},
      {title: "Délai révisé", field: "delai_revise", formatter: dateFormatter, width: 100},
      {title: "Commentaire", field: "commentaire", formatter: "textarea", widthGrow: 2},
      {title: "Date clôture", field: "date_cloture", formatter: dateFormatter, width: 100}
    ]
  });

  // Initialisation modals Bootstrap
  addModal = document.getElementById('addActionModal');
  bootstrapAddModal = new bootstrap.Modal(addModal);

  editModal = document.getElementById('editActionModal');
  bootstrapEditModal = new bootstrap.Modal(editModal);

  // Ouvrir modal ajout
  const addBtn = document.getElementById('addActionBtn');
  addBtn.addEventListener('click', () => {
    document.getElementById('addActionForm').reset();
    // Préremplissage des dates dans le modal
    const inputDate = document.getElementById('newDate');
    const inputDelai = document.getElementById('newDelaiInitiale');

    if (inputDate) {
      const today = new Date();
      inputDate.value = today.toISOString().slice(0, 10);
    }

    if (inputDelai) {
      const today = new Date();
      let delai = new Date(today);
      if (today.getDay() === 5) { // vendredi
        delai.setDate(today.getDate() + 3);
      } else {
        delai.setDate(today.getDate() + 1);
      }
      inputDelai.value = delai.toISOString().slice(0, 10);
    }

    bootstrapAddModal.show();
  });

  // Soumission formulaire ajout
  const addForm = document.getElementById('addActionForm');
  addForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const formData = new FormData(addForm);
    const newAction = Object.fromEntries(formData.entries());
    if (!newAction.statut) {
      newAction.statut = 0.25; // valeur par défaut
    }

    fetch('/action/api/plan-actions', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(newAction)
    }).then(res => res.json())
      .then(resp => {
        if (resp.success) {
          bootstrapAddModal.hide();
          alert('Action ajoutée avec succès !');
          table.replaceData();
        } else {
          alert('Erreur : ' + resp.message);
        }
      }).catch(() => alert('Erreur réseau'));
  });

  // Soumission formulaire édition
  const editForm = document.getElementById('editActionForm');
  editForm.addEventListener('submit', (event) => {
    event.preventDefault();

    const planId = document.getElementById('planId').value;
    const commentaire = document.getElementById('editCommentaire').value;
    const delaiRevise = document.getElementById('editDelaiRevise').value;

    // Envoi uniquement des champs modifiables + ID
    const payload = {
      plan_id: planId,
      commentaire: commentaire,
      delai_revise: delaiRevise
    };
    fetch('/action/api/plan-actions', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(resp => {
      if (resp.success) {
        bootstrapEditModal.hide();
        alert("Modifications enregistrées !");
        table.replaceData();
        closedTable.replaceData();
      } else {
        alert("Erreur : " + resp.message);
      }
    })
    .catch(() => alert("Erreur réseau"));
  });

  // Toggle du filtre "suivi analyse de panne"
  const toggleButton = document.getElementById('toggleSuivi');
  let hideSuivi = false;
  toggleButton.addEventListener('click', () => {
    hideSuivi = !hideSuivi;
    if (hideSuivi) {
      table.setFilter("action", "notContains", "suivi analyse de panne");
      toggleButton.textContent = 'Afficher les actions "suivi analyse de panne"';
    } else {
      table.clearFilter();
      toggleButton.textContent = 'Masquer les actions "suivi analyse de panne"';
    }
  });
});

// Ouvre le modal édition en remplissant les champs (pilote et action en readonly)
function openEditModal(data) {
  document.getElementById('planId').value = data.plan_id || '';

  // Pilote readonly en input text (nom complet)
  document.getElementById('editPersonnelName').value = data.pilote_nom || '';

  // Action readonly (textarea)
  document.getElementById('editActionText').value = data.action || '';

  // Champs modifiables
  document.getElementById('editCommentaire').value = data.commentaire || '';
  document.getElementById('editDelaiRevise').value = data.delai_revise || '';

  bootstrapEditModal.show();
}


function progressPieFormatter(cell) {
  const progress = Number(cell.getValue()) || 0;// entre 0 et 1
  const size = 30;
  const radius = size / 2;
   const angle = progress >= 1 ? 359.9999 : progress * 360;

  // Fonction pour générer un chemin SVG d'un camembert partiel
  function describeArc(x, y, radius, startAngle, endAngle) {
    const start = polarToCartesian(x, y, radius, endAngle);
    const end = polarToCartesian(x, y, radius, startAngle);
    const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";

    return [
      "M", x, y,
      "L", start.x, start.y,
      "A", radius, radius, 0, largeArcFlag, 0, end.x, end.y,
      "Z"
    ].join(" ");
  }

  function polarToCartesian(centerX, centerY, radius, angleInDegrees) {
    var angleInRadians = (angleInDegrees-90) * Math.PI / 180.0;
    return {
      x: centerX + (radius * Math.cos(angleInRadians)),
      y: centerY + (radius * Math.sin(angleInRadians))
    };
  }

  if(progress === 0) {
    return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
      <circle cx="${radius}" cy="${radius}" r="${radius - 1}" stroke="gray" stroke-width="1" fill="none"/>
    </svg>`;
  }

  const path = describeArc(radius, radius, radius - 1, 0, angle);

  return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
    <circle cx="${radius}" cy="${radius}" r="${radius - 1}" fill="#e6e6e6" />
    <path d="${path}" fill="green" />
  </svg>`;
}
