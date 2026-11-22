#!/bin/bash

WS_URL='ws://localhost:9222/devtools/page/71930E8CD2D18AD70BF85108E55C587E'

if [ -z "$WS_URL" ]; then
  echo "Erreur: Impossible de trouver le WebSocket"
  exit 1
fi

echo "Connexion à: $WS_URL"
echo ""

# JSON sur UNE SEULE LIGNE
REQUEST='{"id":1,"method":"Runtime.evaluate","params":{"expression":"JSON.stringify(Array.from(navigator.getGamepads()).map(g => g ? g.id : null))"}}'

echo "Envoi de la requête..."
echo "$REQUEST" | ./websocat "$WS_URL"



REQUEST='{"id":1,"method":"Runtime.evaluate","params":{"expression":"if(window.cr_getC2Runtime) { var rt = window.cr_getC2Runtime(); if(rt) { rt.updateTouchInputMode(); console.log(\"Construct2 reinitialized\"); } } else { console.log(\"Construct2 runtime not found\"); }"}}'

echo "$REQUEST" | ./websocat "$WS_URL"