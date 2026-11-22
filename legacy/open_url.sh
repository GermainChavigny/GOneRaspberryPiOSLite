#!/bin/bash

# Check if the first URL is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <url1>"
    exit 1
fi

URL1=$1

echo "Open URL: $URL1"

xset -dpms
xset s off
xset s noblank

sleep 0.5

./set_screen_resolution.sh

CHROMIUM_OPTIONS="--remote-debugging-port=9222 --kiosk --start-fullscreen --incognito --enable-features=EnableGamepadAPI,GamepadExtensions,GamepadVibration --autoplay-policy=no-user-gesture-required --disable-application-cache --disable-extensions --disable-component-update --noerrdialogs --disable-infobars"

sleep 1
flatpak run org.chromium.Chromium $CHROMIUM_OPTIONS "$URL1"
