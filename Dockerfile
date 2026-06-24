# Dockerfile

# 1. Image de base Python légère
FROM python:3.11-slim

# 2. Variables d'environnement recommandées pour Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Installation des dépendances système nécessaires (ex: psycopg2, mssql)
RUN apt-get update && apt-get install -y \
    gnupg2 curl unixodbc-dev gcc g++ \
    && curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql17 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 4. Répertoire de travail dans le conteneur
WORKDIR /app

# 5. Copier les fichiers de dépendances et installer les paquets Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copier le code de l’application
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY run.py .
COPY wsgi.py .

RUN ls -l /app

# 7. Exposer le port 5000
EXPOSE 5000

# 8. Commande de démarrage : lancer run.py qui gère l'environnement
CMD ["python", "run.py"]
