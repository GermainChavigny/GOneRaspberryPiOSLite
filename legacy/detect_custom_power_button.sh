#!/bin/bash

gpio mode 9 in    

prev_state=0  # Initialize previous state

sleep 3

while true; do
    current_state=$(gpio read 9)

    # Detect rising edge (button pressed)
    if [ "$prev_state" -eq "0" ] && [ "$current_state" -eq "0" ]; then
        echo "Custom power button pressed."
        kill -SIGRTMIN+1 $PPID
        sleep 2  # Debounce delay to avoid multiple triggers
    fi

    prev_state=$current_state  # Update previous state
    sleep 0.1  # Sleep to avoid high CPU usage
done
