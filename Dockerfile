# Utiliser une image Python officielle légère
FROM python:3.9-slim

# Définir le répertoire de travail
WORKDIR /app

# Installer les dépendances système nécessaires pour OSMnx et autres
RUN apt-get update && apt-get install -y \
    build-essential \
    libspatialindex-dev \
    && rm -rf /var/lib/apt/lists/*

# Copier les fichiers de dépendances
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source
COPY . .

# Exposer le port que l'API utilise
EXPOSE 8005

# Commande de démarrage
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8005"]
