#!/bin/bash
# set_screen_resolution.sh
# Force la résolution HDMI sur Raspberry Pi OS Lite (X11)

echo "🔧 Vérification de la résolution d'écran..."

# Attendre un peu que le serveur X soit prêt
sleep 1

# Détecte la sortie HDMI connectée
OUTPUT=$(xrandr | grep " connected" | awk '{print $1}')

if [ -z "$OUTPUT" ]; then
  echo "⚠️  Aucune sortie HDMI détectée."
  exit 1
fi

# Récupère la résolution actuelle
CURRENT_MODE=$(xrandr | grep "$OUTPUT connected" -A1 | tail -n1 | awk '{print $1}')

if [ "$CURRENT_MODE" = "640x480" ]; then
  echo "✅ La bonne résolution (640x480) est déjà appliquée."
else
  echo "🖥️  Résolution actuelle : $CURRENT_MODE"
  echo "➡️  Application de la résolution 640x480..."
  xrandr --output "$OUTPUT" --mode 640x480 || echo "⚠️ Impossible de changer la résolution."
fi
