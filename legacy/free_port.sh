#!/bin/bash

# Vérifier si un paramètre est passé
if [ -z "$1" ]; then
    echo "Usage: $0 <port>"
    exit 1
fi

PORT=$1

# Vérifier si le port est utilisé
PID=$(sudo lsof -t -i :$PORT)

if [ -n "$PID" ]; then
    echo "Le port $PORT est déjà utilisé par le processus $PID. Arrêt en cours..."
    sudo kill -9 "$PID"
    echo "Processus arrêté."
else
    echo "Le port $PORT est libre."
fi
