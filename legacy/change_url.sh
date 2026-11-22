#!/bin/bash
# Change l'URL de l'onglet Chromium en cours via le port de débogage

NEW_URL="$1"

# Récupère l'URL de débogage du premier onglet
DEBUG_URL=$(curl -s http://localhost:9222/json | grep -o 'ws://[^"]*' | head -n 1)

if [ -z "$DEBUG_URL" ]; then
  echo "⚠️ Impossible de récupérer le WebSocket Debug URL."
  exit 1
fi

# Envoie une commande de navigation via WebSocket
echo "{\"id\":1,\"method\":\"Page.navigate\",\"params\":{\"url\":\"$NEW_URL\"}}" | \
  ./websocat -n1 "$DEBUG_URL"
