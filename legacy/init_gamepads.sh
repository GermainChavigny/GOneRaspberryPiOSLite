#!/bin/bash

# Script pour trouver automatiquement les manettes "USB Gamepad"
# en parsant /proc/bus/input/devices

echo "=========================================="
echo "Détection des manettes USB Gamepad"
echo "=========================================="
echo ""

# Parser /proc/bus/input/devices pour trouver les USB Gamepad
declare -a GAMEPADS

while IFS= read -r line; do
    if [[ "$line" =~ ^N:\ Name=\"USB\ Gamepad ]]; then
        # Ligne trouvée, chercher le Handler dans les lignes suivantes
        while IFS= read -r handler_line; do
            if [[ "$handler_line" =~ H:\ Handlers=.*event([0-9]+) ]]; then
                event_num="${BASH_REMATCH[1]}"
                GAMEPADS+=("/dev/input/event$event_num")
                break
            fi
            # Arrêter si on atteint la prochaine entrée (commence par I:)
            if [[ "$handler_line" =~ ^I: ]]; then
                break
            fi
        done
    fi
done < /proc/bus/input/devices

# Vérifier qu'on a trouvé au moins 1 manette
if [[ ${#GAMEPADS[@]} -eq 0 ]]; then
    echo "❌ Aucune manette USB Gamepad trouvée"
    echo ""
    echo "Devices trouvés :"
    cat /proc/bus/input/devices | grep "N: Name"
    exit 1
fi

GAMEPAD1="${GAMEPADS[0]}"
GAMEPAD2="${GAMEPADS[1]:-}"

echo "✅ Manette 1 → $GAMEPAD1"
if [[ -n "$GAMEPAD2" ]]; then
    echo "✅ Manette 2 → $GAMEPAD2"
fi
echo "=========================================="
echo ""
echo "Lancement des manettes..."
echo ""

# Lancer le mappeur pour la manette 1
if [[ -e "$GAMEPAD1" ]]; then
    ./gamepad_to_keyboard.sh "$GAMEPAD1" 0 &
    PID1=$!
    echo "Manette 1 (PID: $PID1) lancée avec $GAMEPAD1"
else
    echo "❌ Erreur : $GAMEPAD1 n'existe pas"
    exit 1
fi

# Lancer le mappeur pour la manette 2 si elle existe
if [[ -n "$GAMEPAD2" ]] && [[ -e "$GAMEPAD2" ]]; then
    ./gamepad_to_keyboard.sh "$GAMEPAD2" 1 &
    PID2=$!
    echo "Manette 2 (PID: $PID2) lancée avec $GAMEPAD2"
fi