#!/bin/bash
# Forcer la sortie audio HDMI sur Raspberry Pi (Wayland + PipeWire)

# --- Étape 1 : Attendre que PipeWire soit prêt
#sleep 2

# --- Étape 2 : Détection automatique de la sortie HDMI
# On cherche le numéro avant le mot "Built-in Audio Digital Stereo (HDMI)"
HDMI_SINK_ID=$(wpctl status 2>/dev/null \
  | awk '/Sinks:/{found=1;next}/Sources:/{found=0}found' \
  | grep -i "HDMI" \
  | head -n1 \
  | sed -E 's/[^0-9]*([0-9]+)\..*/\1/')

# --- Étape 3 : Forcer la sortie et le volume
if [[ "$HDMI_SINK_ID" =~ ^[0-9]+$ ]]; then
  echo "🟢 Sortie HDMI détectée : ID=$HDMI_SINK_ID"
  wpctl set-default "$HDMI_SINK_ID"
  wpctl set-volume @DEFAULT_AUDIO_SINK@ 1.0
else
  echo "🔴 Aucune sortie HDMI détectée ou ID invalide (trouvé: '$HDMI_SINK_ID')"
  echo "Liste des sorties disponibles :"
  wpctl status | grep -A5 "Sinks:"
fi
