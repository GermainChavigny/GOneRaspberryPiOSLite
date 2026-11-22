#!/bin/bash

# Vérifie si un chemin est passé en paramètre
if [ -z "$1" ]; then
    echo "Usage: $0 <chemin_du_dossier>"
    exit 1
fi

folder="$1"

echo "Création du dossier $folder..."
mkdir -p "$folder"

echo "Suppression du contenu du dossier existant $folder..."
sudo rm -rf "$folder"/*

echo "Opération terminée pour le dossier $folder."
