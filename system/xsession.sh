#!/usr/bin/env bash
# Session graphique de la console : règle l'écran et le son, puis garde Chromium ouvert
# en plein écran sur le lobby. Le daemon (gone.service) change ensuite de page à distance.

[ -r /etc/gone/kiosk.env ] && . /etc/gone/kiosk.env
RESOLUTION="${GONE_RESOLUTION:-640x480}"
URL="http://localhost:8000/lobby/index.html"
PROFILE="$HOME/.var/app/org.chromium.Chromium/config/gone-kiosk"

# Pas de mise en veille de l'écran.
xset -dpms
xset s off
xset s noblank

# Le clavier virtuel des manettes envoie des touches « physiques » : avec la disposition
# US, la touche Q donne bien « q » (et pas « a » comme en AZERTY).
setxkbmap us

OUTPUT="$(xrandr | awk '/ connected/ {print $1; exit}')"
if [ -n "$OUTPUT" ]; then
    xrandr --output "$OUTPUT" --mode "$RESOLUTION" || echo "Résolution $RESOLUTION refusée par l'écran."
fi

# Son sur la sortie HDMI, volume au maximum.
HDMI_SINK="$(wpctl status 2>/dev/null \
    | awk '/Sinks:/ {found=1; next} /Sources:/ {found=0} found' \
    | grep -i hdmi | head -n 1 | sed -E 's/[^0-9]*([0-9]+)\..*/\1/')"
if [[ "$HDMI_SINK" =~ ^[0-9]+$ ]]; then
    wpctl set-default "$HDMI_SINK"
    wpctl set-volume @DEFAULT_AUDIO_SINK@ 1.0
fi

# Attend le daemon (au plus 30 s) pour ne pas ouvrir Chromium sur une page d'erreur.
for _ in $(seq 60); do
    curl -fs -o /dev/null http://127.0.0.1:8000/api/status && break
    sleep 0.5
done

# Si Chromium plante ou se ferme, il est relancé.
while true; do
    flatpak run org.chromium.Chromium \
        --remote-debugging-port=9222 --user-data-dir="$PROFILE" \
        --kiosk --start-fullscreen --incognito --no-first-run \
        --enable-features=EnableGamepadAPI,GamepadExtensions,GamepadVibration \
        --autoplay-policy=no-user-gesture-required \
        --disable-application-cache --disable-extensions --disable-component-update \
        --noerrdialogs --disable-infobars \
        "$URL"
    sleep 1
done
