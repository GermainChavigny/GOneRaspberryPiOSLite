#!/usr/bin/env bash
# Lancé à la connexion automatique sur tty1 (voir ~/.bashrc) : démarre l'affichage.
# Journal : ~/.gone-kiosk.log
exec startx /opt/gone/current/system/xsession.sh -- -nocursor > "$HOME/.gone-kiosk.log" 2>&1
