# MSM - Management System Maintenance

Application web complète pour la gestion des activités de maintenance, des indicateurs sécurité (BBS, accidents), et la planification interactive du personnel (drag & drop).

---

## 🚀 Fonctionnalités principales

- **Huddle Home** : suivi des BBS, avancement, indicateurs sécurité en temps réel
- **Planning d’activités** : calendrier par semaine ou mois, drag & drop, assignation dynamique des membres du personnel
- **Gestion des incidents** : suivi des accidents, croix de sécurité, jours sans accident
- **Import/export de données** : synchronisation avec fichiers Excel, traitements ETL personnalisés
- **Séparation claire** entre logique métier (dossier `scripts/`) et routes / vues (dossier `app/blueprints/`)
- **Notifications, logs, reporting dynamique**

---

## 🗂️ Arborescence
MSM/
│
├── app/
│   ├── blueprints/            # Dossiers de routes Flask séparées par domaine fonctionnel
│   │   ├── __init__.py        # Enregistre les blueprints (optionnel ici si utilisé ailleurs)
│   │   ├── home/              # Blueprint "home" (tableau de bord principal)
|   |   |    ├── __init__.py   # Instancie le Blueprint home
│   │   |    ├── static/       # Fichiers statiques propres à ce blueprint
│   │   |    |   ├── css/
│   │   |    |   | └──  style-home.css
│   │   |    |   └── js/
│   │   |    |      └── home.js
│   │   |    ├── templates/
│   │   |    |    └── HuddleHome.html    # Template principal du home
│   │   |    └── routes.py    # Toutes les routes Flask liées à "home"
│   │   ├── services/         # Blueprint "services" (gestion du planning, activités…)
|   |   |    ├── __init__.py
│   │   |    ├── static/
│   │   |    |   ├── css/
│   │   |    |   | └──  style_services.css
│   │   |    |   └── js/
│   │   |    |      └── services.js
│   │   |    ├── templates/
│   │   |    |    └── planning.html
│   │   |    └── routes.py    # Routes Flask pour "services" (API planning/activité)
│   │   └── common/           # Place pour du code partagé entre blueprints si besoin
|   |   |    ├── __init__.py
│   │   |    └── __init__.py  # (possible duplication, à garder si utile)
│   ├── static/               # Statique "global" à l’app (pas lié à un blueprint précis)
|   |   ├── css/
│   |   |  └──  style.css     # Style commun global
|   |   └──  js/
│   │      └── commun.js      # JS utilitaire global (fonctions partagées)
│   ├── templates/            # Templates globaux partagés
|   |   ├── Header.html       # En-tête commun
│   |   └──  Footer.html      # Pied de page commun
│   ├── config.py             # Configuration (Dev/Prod, secrets, constantes…)
│   ├── extensions.py         # Instancie les extensions Flask (DB, login_manager, etc)
│   └── __init__.py           # Crée l’objet Flask, charge config, blueprints, etc.
│
├── scripts/                  # LOGIQUE MÉTIER/SERVICES – Pas de Flask ici !
│   ├── etl/                  # Scripts d’import/export, jobs ETL (extraction/traitement données)
│   └── services/             # Fonctions métiers (dashboard, planning, etc)
│
├── data/                     # (Vide) Pour stocker des fichiers, bases locales, exports…
├── run.py                    # Lanceur principal (dev, debug)
├── wsgi.py                   # Point d’entrée WSGI (prod, serveur web)
├── .env                      # Variables d’environnement (DB, secrets, etc)
├── requirements.txt          # Dépendances Python
├── .gitignore                # Fichiers/dossiers à ignorer par git
├── README.md                 # Documentation de base
├── Dockerfile                # Image Docker de l'app (optionnel mais +)
├── docker-compose.yml        # Orchestration services (optionnel)


---

## ⚙️ Installation & lancement

## Dépendances système

- ✅ Pilote ODBC nécessaire : `ODBC Driver 18 for SQL Server`
  - Télécharger : https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server


### 1. Prérequis

- Python 3.10+
- PostgreSQL (ou autre DB supportée)
- [Facultatif] Docker

### 2. Installation

```bash
# 1. Cloner le dépôt
git clone <votre-repo.git>
cd MSM

# 2. Installer les dépendances
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configurer les variables d’environnement
cp .env.example .env     # puis personnaliser




# README - Création d’un Dockerfile pour une application Python Flask

## Objectif

Ce document explique comment créer un Dockerfile adapté pour containeriser une application Python Flask.  
L’objectif est de construire une image Docker légère, performante, sécurisée et facilement déployable.

---

## Étapes pour réaliser un Dockerfile efficace

### 1. Choix de l’image de base

- Privilégier une image officielle Python, de préférence une version slim (ex : `python:3.11-slim`) pour limiter la taille de l’image.
- Cette image inclut déjà Python et pip.

### 2. Définition des variables d’environnement

- `PYTHONDONTWRITEBYTECODE=1` : empêche la création de fichiers `.pyc` inutiles dans le conteneur.
- `PYTHONUNBUFFERED=1` : active l’affichage immédiat des logs dans la console (utile pour le debug).

### 3. Installation des dépendances système

- Installer uniquement les packages nécessaires (ex : compilateurs, bibliothèques spécifiques) pour supporter les modules Python comme `psycopg2` ou l’accès à une base de données MS SQL via `msodbcsql17`.
- Nettoyer le cache d’installation (`apt-get clean` et suppression des listes) pour réduire la taille finale de l’image.

### 4. Création du répertoire de travail

- Définir un dossier dans le conteneur, typiquement `/app`, qui contiendra tout le code de l’application.

### 5. Copier les fichiers nécessaires dans l’image

- Copier d’abord `requirements.txt` seul pour pouvoir utiliser le cache Docker lors de l’installation des dépendances.
- Installer les dépendances Python via pip (`pip install -r requirements.txt`).
- Copier ensuite le reste du code source dans le dossier de travail.

### 6. (Optionnel) Créer un utilisateur non-root

- Pour la sécurité, éviter de faire tourner l’application avec le compte root dans le conteneur.
- Ajouter un utilisateur dédié et utiliser la directive `USER` pour changer.

### 7. Définir la commande de démarrage

- Pour le développement, la commande peut être `flask run --host=0.0.0.0`.
- En production, privilégier un serveur WSGI performant comme Gunicorn (`gunicorn -b 0.0.0.0:5000 wsgi:app`).

---

## Exemple minimal de Dockerfile

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y gcc g++ unixodbc-dev && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "-b", "0.0.0.0:5000", "wsgi:app"]

# Utilisation de Docker Compose avec fichier `.env`

## Présentation

---
Les variables d’environnement sont définies dans un fichier `.env` pour configurer la connexion aux bases et les chemins de fichiers.
---

## Fichiers clés

- `docker-compose.yml` : décrit les services, volumes, dépendances et variables d’environnement.
- `.env` : stocke les variables sensibles ou spécifiques à l’environnement (mots de passe, URI, chemins).
- `Dockerfile` : construit l’image Docker de l’application web.
- `run.py` : point d’entrée Flask qui lit la variable `APP_ENV` pour charger la configuration dev ou prod.

---

## Prérequis

- Docker et Docker Compose installés sur votre machine.
- Cloner ce projet sur votre machine locale.
- Placer un fichier `.env` correctement configuré (exemple fourni).

---

## Variables importantes dans `.env`

| Variable                    | Description                                         |
|----------------------------|-----------------------------------------------------|
| APP_ENV                    | Environnement d’exécution (`dev` ou `prod`)        |
| POSTGRES_USER              | Utilisateur PostgreSQL                              |
| POSTGRES_PASSWORD          | Mot de passe PostgreSQL                             |
| POSTGRES_DB                | Nom de la base PostgreSQL                           |
| SA_PASSWORD                | Mot de passe administrateur SQL Server             |
| SQLALCHEMY_DATABASE_URI_PROD | URI de connexion PostgreSQL pour prod (avec `db` comme host) |

---

## Commandes principales

### Lancer la stack (build + démarrage)

```bash
docker-compose up --build

# README - Configuration PostgreSQL : problème pg_hba.conf et accès distant

## Contexte

L'application Flask MSM utilise une base PostgreSQL distante (sur une VM) pour stocker ses données.  
Lors de la connexion à cette base depuis un autre serveur (ex. conteneur Docker sur une autre machine), une erreur de connexion `no pg_hba.conf entry` peut survenir.

---

## Problème rencontré

Erreur dans les logs Flask / SQLAlchemy :


Cette erreur signifie que la configuration de PostgreSQL **refuse la connexion** car l’hôte client (IP du conteneur / machine qui essaie de se connecter) n’est pas autorisé par la configuration `pg_hba.conf` de PostgreSQL.

---

## Explications techniques

- `pg_hba.conf` est le fichier de contrôle d'accès à PostgreSQL qui définit quels hôtes, utilisateurs et bases sont autorisés à se connecter, et par quel mode d’authentification.
- Par défaut, PostgreSQL autorise uniquement les connexions locales (localhost).
- Toute connexion distante doit être explicitement autorisée dans ce fichier.

---

## Étapes pour résoudre

### 1. Modifier `pg_hba.conf` sur la VM PostgreSQL

- Trouver le fichier `pg_hba.conf` (exemple sous Linux `/etc/postgresql/XX/main/pg_hba.conf` ou `/var/lib/pgsql/data/pg_hba.conf`).
- Ajouter une ligne pour autoriser l’IP du client (ici, celle de la machine ou conteneur Docker qui lance Flask) :

```conf
# Autoriser l'utilisateur huddle_user de l'IP client à accéder à la base PM en mdp (md5)
host    PM      huddle_user   172.30.206.163/32   md5
