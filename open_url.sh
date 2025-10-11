#!/bin/bash

# Check if the first URL is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <url1> [url2]"
    exit 1
fi

URL1=$1
URL2=$2

echo "Launching transition with URL: $URL1"

# Set common Chromium options
CHROMIUM_OPTIONS="--kiosk --incognito --autoplay-policy=no-user-gesture-required --disable-application-cache --enable-features=GamepadExtensions --disable-extensions --disable-component-update --noerrdialogs --disable-infobars"

# Launch Chromium with one or two URLs based on input
if [ -z "$URL2" ]; then
    flatpak run org.chromium.Chromium $CHROMIUM_OPTIONS "$URL1" &
else
    flatpak run org.chromium.Chromium $CHROMIUM_OPTIONS "$URL1" "$URL2" &
fi
