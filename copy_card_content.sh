#!/bin/bash

# Vérifie si un chemin est passé en paramètre
if [ -z "$1" ]; then
    echo "Usage: $0 <chemin_du_dossier>"
    exit 1
fi

FOLDER="$1"

# Exécute la commande mcopy avec le chemin spécifié

echo "Remplacement du contenu du dossier $FOLDER ..."

./reinit_folder.sh "$FOLDER"

echo "Copie des fichiers..."

sudo mcopy -s -n -v -i /dev/sda1 ::* "$FOLDER"


# Rename icon.png to icon-ready.png
if [ -f "$FOLDER/icon.png" ]; then
  mv "$FOLDER/icon.png" "$FOLDER/icon-ready.png"
  echo "Renamed icon.png to icon-ready.png"
else
  echo "File $FOLDER/icon.png does not exist."
fi

# Check if the htmlGame/index.html file exists
if [ ! -f "$FOLDER/htmlGame/index.html" ]; then
  # Copy icon-error.png into the folder
  if [ -f "./icon-error.png" ]; then
    cp "./icon-error.png" "$FOLDER/"
    echo "Copied icon-error.png to $FOLDER"
  else
    echo "icon-error.png does not exist in the current directory."
  fi
else
  echo "File $FOLDER/htmlGame/index.html exists, no action taken."
fi
