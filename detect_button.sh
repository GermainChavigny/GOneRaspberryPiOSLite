#!/bin/bash

# Function to find the gamepad device using udevadm
find_gamepad_device() {
    # Loop over all /dev/input/eventX devices
    for dev in /dev/input/event*; do
        # Use udevadm to get the device info and check if it contains "USB Gamepad"
        if udevadm info --query=all --name="$dev" 2>/dev/null | grep -q "USB_Gamepad"; then
            echo "$dev"
            #return
        fi
    done
}

# Monitor the devices for button presses
monitor_gamepad() {
    for DEVICE in $(find_gamepad_device); do
        echo "Monitoring $DEVICE for B button press..."
        sudo evtest "$DEVICE" | while read -r line; do
            # Check for the specific BTN_THUMB2 press event
            if [[ "$line" == *"type 1 (EV_KEY), code 290 (BTN_THUMB2), value 1"* ]]; then
                echo "Bouton B pressé on $DEVICE"
                # Send a signal to the parent or perform an action
                kill -USR1 $PPID
            fi
        done &
    done
}

monitor_gamepad

