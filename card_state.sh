#!/bin/bash

# Vérifie l'état de la carte (0B indique qu'elle est retirée)
if lsblk -n -o NAME,SIZE | grep -q "0B"; then
    echo "removed"
else
    echo "inserted"
fi