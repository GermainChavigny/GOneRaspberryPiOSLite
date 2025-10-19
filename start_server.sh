#!/bin/bash

# Vérifie si un chemin est passé en paramètre
if [ -z "$1" ]; then
    echo "Usage: $0 <chemin_du_dossier>"
    exit 1
fi

SERVER_PATH="$1"

# Appelle le script pour libérer le port
./free_port.sh 8000

echo "Démarrage du serveur..."

# Démarre le serveur Python sur le chemin spécifié
python3 -m http.server 8000 --directory "$SERVER_PATH" &

echo "Serveur démarré sur http://localhost:8000"
