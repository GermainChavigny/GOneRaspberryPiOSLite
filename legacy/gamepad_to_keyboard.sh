#!/bin/bash

# Configuration de la manette
GAMEPAD_DEVICE="${1:-/dev/input/event0}"
MAPPING_INDEX="${2:-0}"

# Mapping INDEX 0 : Manette 1 (ZQSD)
declare -A KEY_CODES_0=(
    ["BTN_THUMB2"]="c" # jaune
    ["BTN_THUMB"]="v" # rouge
    ["BTN_TRIGGER"]="b" # bleu
)

declare -A STICK_CODES_0=(
    ["UP"]="z"
    ["DOWN"]="s"
    ["LEFT"]="q"
    ["RIGHT"]="d"
)

# Mapping INDEX 1 : Manette 2 (Flèches directionnelles)
declare -A KEY_CODES_1=(
    ["BTN_THUMB2"]="m" # jaune
    ["BTN_THUMB"]="l" # rouge
    ["BTN_TRIGGER"]="k" # bleu
)

declare -A STICK_CODES_1=(
    ["UP"]="Up"
    ["DOWN"]="Down"
    ["LEFT"]="Left"
    ["RIGHT"]="Right"
)

# Sélectionner le mapping selon l'index
if [[ "$MAPPING_INDEX" == "0" ]]; then
    declare -n KEY_CODES=KEY_CODES_0
    declare -n STICK_CODES=STICK_CODES_0
    MAPPING_NAME="Manette 1 - ZQSD (INDEX 0)"
elif [[ "$MAPPING_INDEX" == "1" ]]; then
    declare -n KEY_CODES=KEY_CODES_1
    declare -n STICK_CODES=STICK_CODES_1
    MAPPING_NAME="Manette 2 - Flèches + Pavé num (INDEX 1)"
else
    echo "Erreur: INDEX doit être 0 ou 1, reçu: $MAPPING_INDEX"
    exit 1
fi

# Variables pour tracker l'état des axes
ABS_X_PRESSED="none"
ABS_Y_PRESSED="none"

# Fonction pour envoyer un événement clavier
send_key() {
    local key="$1"
    local action="$2"  # "down" ou "up"
    
    if [[ "$action" == "down" ]]; then
        DISPLAY=:0 xdotool keydown "$key" 2>/dev/null
    elif [[ "$action" == "up" ]]; then
        DISPLAY=:0 xdotool keyup "$key" 2>/dev/null
    fi
}

# Vérifier que la manette existe
if [[ ! -e "$GAMEPAD_DEVICE" ]]; then
    echo "Erreur: Manette non trouvée à $GAMEPAD_DEVICE"
    exit 1
fi

echo "=========================================="
echo "Mapping joystick → clavier"
echo "Device: $GAMEPAD_DEVICE"
echo "$MAPPING_NAME"
echo "=========================================="
echo ""
echo "Mapping des boutons :"
echo "  BTN_TRIGGER → ${KEY_CODES[BTN_TRIGGER]}"
echo "  BTN_THUMB   → ${KEY_CODES[BTN_THUMB]}"
echo "  BTN_THUMB2  → ${KEY_CODES[BTN_THUMB2]}"
echo ""
echo "Mapping de la croix directionnelle :"
echo "  HAUT   → ${STICK_CODES[UP]}"
echo "  BAS    → ${STICK_CODES[DOWN]}"
echo "  GAUCHE → ${STICK_CODES[LEFT]}"
echo "  DROITE → ${STICK_CODES[RIGHT]}"
echo ""
echo "Appuyez sur Ctrl+C pour arrêter"
echo "=========================================="
echo ""

# Tracer les événements
sudo evtest "$GAMEPAD_DEVICE" 2>/dev/null | while read -r line; do
    
    # ===== DÉTECTION DES BOUTONS =====
    
    # Appui sur un bouton (value 1)
    if [[ "$line" =~ type\ 1\ \(EV_KEY\),\ code\ [0-9]+\ \(([A-Z_0-9]+)\),\ value\ 1 ]]; then
        btn="${BASH_REMATCH[1]}"
        
        if [[ -v "KEY_CODES[$btn]" ]]; then
            key="${KEY_CODES[$btn]}"
            echo "$(date '+%H:%M:%S') | Appui    : $btn → $key"
            send_key "$key" "down"
        fi
    fi
    
    # Relâchement d'un bouton (value 0)
    if [[ "$line" =~ type\ 1\ \(EV_KEY\),\ code\ [0-9]+\ \(([A-Z_0-9]+)\),\ value\ 0 ]]; then
        btn="${BASH_REMATCH[1]}"
        
        if [[ -v "KEY_CODES[$btn]" ]]; then
            key="${KEY_CODES[$btn]}"
            echo "$(date '+%H:%M:%S') | Relâche  : $btn → $key UP"
            send_key "$key" "up"
        fi
    fi
    
    # ===== DÉTECTION DU STICK ANALOGIQUE =====
    # ABS_X : 0=gauche, 127=centre, 255=droite
    
    if [[ "$line" =~ type\ 3\ \(EV_ABS\),\ code\ 0\ \(ABS_X\),\ value\ ([0-9]+) ]]; then
        value="${BASH_REMATCH[1]}"
        
        # Relâcher l'ancienne touche
        if [[ "$ABS_X_PRESSED" != "none" ]]; then
            send_key "$ABS_X_PRESSED" "up"
        fi
        
        # Nouveau mouvement
        if (( value < 50 )); then
            echo "$(date '+%H:%M:%S') | Stick X  : GAUCHE (value=$value) → ${STICK_CODES[LEFT]}"
            send_key "${STICK_CODES[LEFT]}" "down"
            ABS_X_PRESSED="${STICK_CODES[LEFT]}"
        elif (( value > 205 )); then
            echo "$(date '+%H:%M:%S') | Stick X  : DROITE (value=$value) → ${STICK_CODES[RIGHT]}"
            send_key "${STICK_CODES[RIGHT]}" "down"
            ABS_X_PRESSED="${STICK_CODES[RIGHT]}"
        else
            echo "$(date '+%H:%M:%S') | Stick X  : Centre (value=$value)"
            ABS_X_PRESSED="none"
        fi
    fi
    
    # ABS_Y : 0=haut, 127=centre, 255=bas
    if [[ "$line" =~ type\ 3\ \(EV_ABS\),\ code\ 1\ \(ABS_Y\),\ value\ ([0-9]+) ]]; then
        value="${BASH_REMATCH[1]}"
        
        # Relâcher l'ancienne touche
        if [[ "$ABS_Y_PRESSED" != "none" ]]; then
            send_key "$ABS_Y_PRESSED" "up"
        fi
        
        # Nouveau mouvement
        if (( value < 50 )); then
            echo "$(date '+%H:%M:%S') | Stick Y  : HAUT (value=$value) → ${STICK_CODES[UP]}"
            send_key "${STICK_CODES[UP]}" "down"
            ABS_Y_PRESSED="${STICK_CODES[UP]}"
        elif (( value > 205 )); then
            echo "$(date '+%H:%M:%S') | Stick Y  : BAS (value=$value) → ${STICK_CODES[DOWN]}"
            send_key "${STICK_CODES[DOWN]}" "down"
            ABS_Y_PRESSED="${STICK_CODES[DOWN]}"
        else
            echo "$(date '+%H:%M:%S') | Stick Y  : Centre (value=$value)"
            ABS_Y_PRESSED="none"
        fi
    fi
    
done