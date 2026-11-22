#!/bin/bash

# Fonction pour vérifier et installer un paquet apt
check_apt() {
    if dpkg -s "$1" >/dev/null 2>&1; then
        echo "Le paquet $1 est déjà installé."
    else
        echo "Le paquet $1 n'est pas installé. Installation en cours..."
        sudo apt-get update -y
        sudo apt-get install -y "$1"
        if dpkg -s "$1" >/dev/null 2>&1; then
            echo "Le paquet $1 a été installé avec succès."
        else
            echo "L'installation du paquet $1 a échoué. Veuillez vérifier manuellement."
        fi
    fi
}

# Fonction pour vérifier et installer flatpak
check_flatpak() {
    if command -v flatpak >/dev/null 2>&1; then
        echo "Flatpak est déjà installé."
    else
        echo "Flatpak n'est pas installé. Installation en cours..."
        sudo apt-get update -y
        sudo apt-get install -y flatpak
        if command -v flatpak >/dev/null 2>&1; then
            echo "Flatpak a été installé avec succès."
        else
            echo "L'installation de Flatpak a échoué. Veuillez vérifier manuellement."
            return
        fi
    fi
}

# Fonction pour vérifier et ajouter le dépôt Flathub
check_flathub() {
    if flatpak remotes | grep -q flathub; then
        echo "Le dépôt Flathub est déjà configuré."
    else
        echo "Ajout du dépôt Flathub..."
        sudo flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
    fi
}

# Fonction pour vérifier et installer un paquet flatpak
check_flatpak_package() {
    if flatpak list | grep -q "$1"; then
        echo "Le paquet Flatpak $1 est déjà installé."
    else
        echo "Le paquet Flatpak $1 n'est pas installé. Installation en cours..."
        sudo flatpak install -y flathub "$1"
        if flatpak list | grep -q "$1"; then
            echo "Le paquet Flatpak $1 a été installé avec succès."
        else
            echo "L'installation du paquet Flatpak $1 a échoué. Veuillez vérifier manuellement."
        fi
    fi
}

# --- Vérification des paquets apt ---
APT_PACKAGES=("xserver-xorg" "x11-xserver-utils" "xinit" "openbox")
for pkg in "${APT_PACKAGES[@]}"; do
    check_apt "$pkg"
done

# --- Vérification et installation de Flatpak ---
check_flatpak
check_flathub

# --- Vérification et installation de Chromium via Flatpak ---
check_flatpak_package "org.chromium.Chromium"




# Vérifie si lsof est installé
if command -v lsof >/dev/null 2>&1; then
    echo "lsof est déjà installé."
else
    echo "lsof n'est pas installé. Installation en cours..."
    sudo apt-get update -y
    sudo apt-get install -y lsof

    # Vérifie si l'installation a réussi
    if command -v lsof >/dev/null 2>&1; then
        echo "lsof a été installé avec succès."
    else
        echo "L'installation de lsof a échoué. Veuillez vérifier manuellement."
    fi
fi



# Vérifie si mcopy est disponible
if command -v mcopy >/dev/null 2>&1; then
    echo "La commande mcopy est déjà installée."
else
    echo "La commande mcopy n'est pas installée. Installation en cours..."

    # Met à jour la liste des paquets
    sudo apt-get update -y

    # Installe le paquet mtools
    sudo apt-get install -y mtools

    # Vérifie si l'installation a réussi
    if command -v mcopy >/dev/null 2>&1; then
        echo "La commande mcopy a été installée avec succès."
    else
        echo "L'installation de mcopy a échoué. Veuillez vérifier manuellement."
    fi
fi


# Vérifie si evtest est disponible
if command -v evtest >/dev/null 2>&1; then
    echo "La commande evtest est déjà installée."
else
    echo "La commande evtest n'est pas installée. Installation en cours..."

    sudo apt-get update -y

    sudo apt-get install evtest -y

    # Vérifie si l'installation a réussi
    if command -v evtest >/dev/null 2>&1; then
        echo "La commande evtest a été installée avec succès."
    else
        echo "L'installation de evtest a échoué. Veuillez vérifier manuellement."
    fi
fi


# Vérifie si xdotool est installé
if command -v xdotool >/dev/null 2>&1; then
    echo "xdotool est déjà installé."
else
    echo "xdotool n'est pas installé. Installation en cours..."
    sudo apt-get update -y
    sudo apt-get install -y xdotool

    # Vérifie si l'installation a réussi
    if command -v xdotool >/dev/null 2>&1; then
        echo "xdotool a été installé avec succès."
    else
        echo "L'installation de xdotool a échoué. Veuillez vérifier manuellement."
        exit 1
    fi
fi


# Vérifie si gpio est disponible
if command -v gpio >/dev/null 2>&1; then
    echo "La commande gpio est déjà installée."
else
    echo "La commande gpio n'est pas installée. Installation en cours..."
    
    sudo apt install ./wiringpi_3.16_arm64.deb

    # Vérifie si l'installation a réussi
    if command -v gpio >/dev/null 2>&1; then
        echo "La commande gpio a été installée avec succès."
    else
        echo "L'installation de gpio a échoué. Veuillez vérifier manuellement."
    fi
fi



