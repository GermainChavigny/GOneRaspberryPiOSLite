#!/bin/bash

gpio mode 0 down  # Pull-down resistor for GPIO 17
gpio mode 0 in    # Set GPIO pin as input

prev_state=0  # Initialize previous state

while true; do
    current_state=$(gpio read 0)

    # Detect rising edge (button pressed)
    if [ "$prev_state" -eq "0" ] && [ "$current_state" -eq "1" ]; then
        echo "Custom reset button pressed."
        kill -USR2 $PPID
        sleep 4  # Debounce delay to avoid multiple triggers
    fi

    prev_state=$current_state  # Update previous state
    sleep 0.1  # Sleep to avoid high CPU usage
done
