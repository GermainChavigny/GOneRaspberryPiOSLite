#!/bin/bash

# fonctionne avec linux raspberrypi 6.12.47+rpt-rpi-v8 #1 lite

cd "$(dirname "$0")" || exit 1

SERVER_FOLDER="./"
COMPACT_FLASH_FOLDER="./CompactFlash"
LOBBY_URL="http://localhost:8000/lobby/index.html"
HTML_GAME_URL="http://localhost:8000/CompactFlash/htmlGame/index.html"
HTML_GAME_FILE="./CompactFlash/htmlGame/index.html"
TRANSITION_URL="http://localhost:8000/transition/index.html"

PREVIOUS_CARD_STATE=""
WAITING_USER_GAMEPAD_INPUT=false
GAME_IS_RUNNING=false
IS_POWERING_OFF=false

chmod +x ./make_executable.sh
sudo ./make_executable.sh ./
./install_dependencies.sh
sudo ./auto_no_password_setup.sh &
./configure_auto_start.sh &
./set_hdmi_audio.sh &
./start_server.sh "$SERVER_FOLDER"
startx ./open_url.sh "$LOBBY_URL" &
./init_gamepads.sh &
./reinit_folder.sh "$COMPACT_FLASH_FOLDER"

#./hide_cursor.sh &
#./update_pcmanfm_conf.sh
#./configure_os_ui.sh
#sudo ./install_plymouth_theme.sh

# Fonction callback à exécuter lorsque le bouton B est pressé
onStartGameButtonPressed() {
    echo "Bouton B a été pressé"
    if [ "$WAITING_USER_GAMEPAD_INPUT" == true ] && [ "$IS_POWERING_OFF" == false ]; then
	    echo "Lancement du jeu..."
	    WAITING_USER_GAMEPAD_INPUT=false
	    GAME_IS_RUNNING=true
	    ./change_url.sh "$HTML_GAME_URL"
    fi
}

onCustomResetButtonPressed() {
	echo "Reset demandé"
	if [ "$GAME_IS_RUNNING" == true ] && [ "$IS_POWERING_OFF" == false ]; then
		GAME_IS_RUNNING=false
		PREVIOUS_CARD_STATE=""
		./change_url.sh "$LOBBY_URL"
	fi
}

onCustomPowerButtonPressed() {
	echo "Power off demandé"
	if [ "$IS_POWERING_OFF" == false ]; then
		GAME_IS_RUNNING=false
		IS_POWERING_OFF=true
		./change_url.sh "$TRANSITION_URL"
		sudo shutdown -h now
	fi
}

# Configure le trap pour réagir au signal USR1
trap onStartGameButtonPressed USR1
trap onCustomResetButtonPressed USR2
trap onCustomPowerButtonPressed SIGRTMIN+1

./detect_button.sh &
./detect_custom_reset_button.sh &
./detect_custom_power_button.sh &


while true; do
    # Appelle le script pour obtenir l'état actuel
    CURRENT_CARD_STATE=$(./card_state.sh)

    # Détecte un changement d'état
    if [ "$CURRENT_CARD_STATE" != "$PREVIOUS_CARD_STATE" ]; then
        echo "State changed: $PREVIOUS_CARD_STATE -> $CURRENT_CARD_STATE"
        
        if [ "$CURRENT_CARD_STATE" == "inserted" ]; then
			echo "Carte insérée, copie du contenu..."
			
			./copy_card_content.sh "$COMPACT_FLASH_FOLDER"
			
			if [ -e "$HTML_GAME_FILE" ]; then
				WAITING_USER_GAMEPAD_INPUT=true
				echo "Jeu trouvé, en attente de l'input du joueur..."
			else 
				echo "Pas de fichier trouvé à l'emplacement $HTML_GAME_FILE"
			fi
        fi
        
        
        if [ "$PREVIOUS_CARD_STATE" == "inserted" ] && [ "$CURRENT_CARD_STATE" == "removed" ]; then
			echo "Carte retirée"
			./reinit_folder.sh "$COMPACT_FLASH_FOLDER"
			if [ "$GAME_IS_RUNNING" == true ]; then
				./change_url.sh "$LOBBY_URL"
			fi
			GAME_IS_RUNNING=false
        fi
        
        PREVIOUS_CARD_STATE="$CURRENT_CARD_STATE"
    fi

    # Pause pour éviter de surcharger les vérifications
    sleep 0.4
done