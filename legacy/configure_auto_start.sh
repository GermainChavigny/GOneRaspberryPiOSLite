#!/bin/bash

# Configuration
SCRIPT_PATH="$HOME/GOneRaspberryPiOSLite/main.sh"
USER=$(whoami)
BASH_RC="$HOME/.bashrc"
FORCE=false

# Vérifier les paramètres
if [ "$1" = "--force" ]; then
    FORCE=true
fi

# Vérifications
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "Erreur: Le script $SCRIPT_PATH n'existe pas"
    exit 1
fi

if [ ! -x "$SCRIPT_PATH" ]; then
    echo "Correction des permissions d'exécution..."
    chmod +x "$SCRIPT_PATH"
fi

# Ligne à ajouter au .bashrc
STARTUP_LINE="# GOne Auto-Startup"
EXEC_LINE="exec $SCRIPT_PATH"

# Vérifier si déjà présent
if grep -q "GOne Auto-Startup" "$BASH_RC"; then
    if [ "$FORCE" = false ]; then
        echo "G one est déjà configuré dans .bashrc"
        echo "Utilisez --force pour le mettre à jour: $0 --force"
        exit 0
    else
        echo "Suppression de l'ancienne configuration..."
        sed -i '/# GOne Auto-Startup/,/exec '"$(echo $SCRIPT_PATH | sed 's/\//\\\//g')"'/d' "$BASH_RC"
    fi
fi

# Ajouter au .bashrc
echo "Ajout de G one à .bashrc..."
cat >> "$BASH_RC" << EOF

$STARTUP_LINE
if [ -z "\$SSH_CLIENT" ] && [ -z "\$SSH_TTY" ] && [ "\$TERM" != "screen" ]; then
    $EXEC_LINE
fi
EOF

echo "✓ Service configuré dans .bashrc"
echo ""
echo "Contenu ajouté:"
tail -5 "$BASH_RC"
echo ""
echo "Commandes utiles:"
echo "  Voir .bashrc: cat $BASH_RC"
echo "  Réinitialiser: sed -i '/# GOne Auto-Startup/,/exec .*/d' $BASH_RC"