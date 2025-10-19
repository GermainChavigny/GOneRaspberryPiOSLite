#!/bin/bash

# Vérifie si un argument est passé, sinon utilise le répertoire courant
TARGET_DIR=${1:-"./"}

# Option 1 : Seulement le répertoire courant (pas les sous-dossiers)
find "$TARGET_DIR" -maxdepth 1 -type f -name "*.sh" -exec chmod +x {} \;

# Option 2 : Inclure aussi les sous-dossiers (décommenter pour utiliser)
# find "$TARGET_DIR" -type f -name "*.sh" -exec chmod +x {} \;