#!/usr/bin/env bash
# Configuration du système pour la console G one. Peut être relancé sans risque :
# chaque étape vérifie d'abord si elle est déjà faite.
# Appelé par install.sh à l'installation et à chaque mise à jour.
#   usage : setup-system.sh <utilisateur>
set -euo pipefail

USER_NAME="${1:?usage : setup-system.sh <utilisateur>}"
USER_HOME="$(getent passwd "$USER_NAME" | cut -d: -f6)"
ROOT="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
export DEBIAN_FRONTEND=noninteractive

step() { echo "  - $*"; }

# ---- paquets -------------------------------------------------------------------
PACKAGES=(
    xserver-xorg xinit x11-xserver-utils x11-xkb-utils      # affichage
    flatpak                                                 # Chromium
    pipewire pipewire-pulse wireplumber                     # son
    python3 python3-aiohttp python3-evdev python3-pyudev    # daemon
    python3-gpiozero                                        # boutons de la console
    mtools                                                  # lecture des cartouches
    network-manager rfkill curl ca-certificates             # réseau et mises à jour
)
missing=()
for package in "${PACKAGES[@]}"; do
    dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q "install ok installed" || missing+=("$package")
done
if [ "${#missing[@]}" -gt 0 ]; then
    step "Installation des paquets : ${missing[*]}"
    apt-get update -y
    apt-get install -y "${missing[@]}"
fi

# Accès aux GPIO : fourni par le dépôt Raspberry Pi (absent d'une Debian ordinaire).
if ! dpkg-query -W -f='${Status}' python3-lgpio 2>/dev/null | grep -q "install ok installed"; then
    apt-get install -y python3-lgpio \
        || echo "  ! python3-lgpio introuvable : les boutons reset et marche/arrêt peuvent ne pas répondre."
fi

if ! flatpak info org.chromium.Chromium >/dev/null 2>&1; then
    step "Installation de Chromium (Flatpak) — plusieurs minutes"
    flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
    flatpak install -y --noninteractive flathub org.chromium.Chromium
fi

# ---- utilisateur de la console -------------------------------------------------
for group in input video audio render gpio; do
    if getent group "$group" >/dev/null && ! id -nG "$USER_NAME" | tr ' ' '\n' | grep -qx "$group"; then
        usermod -aG "$group" "$USER_NAME"
    fi
done

# Connexion automatique sur le premier terminal.
mkdir -p /etc/systemd/system/getty@tty1.service.d
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf <<UNIT
[Service]
ExecStart=
ExecStart=-$(command -v agetty || echo /sbin/agetty) --autologin $USER_NAME --noclear %I \$TERM
UNIT

# Lancement de l'affichage à la connexion sur tty1 (et seulement là : SSH reste normal).
BASHRC="$USER_HOME/.bashrc"
touch "$BASHRC"
sed -i '/^# GOne Auto-Startup$/,/^fi$/d' "$BASHRC"                 # ancien lancement (main.sh)
sed -i '/^# >>> GOne kiosk >>>$/,/^# <<< GOne kiosk <<<$/d' "$BASHRC"
cat >> "$BASHRC" <<'BLOCK'
# >>> GOne kiosk >>>
if [ -z "${DISPLAY:-}" ] && [ "$(tty)" = /dev/tty1 ] && [ -f /opt/gone/current/system/kiosk-session.sh ]; then
    bash /opt/gone/current/system/kiosk-session.sh
    sleep 2
    exit
fi
# <<< GOne kiosk <<<
BLOCK
chown "$USER_NAME": "$BASHRC"

# ---- services -------------------------------------------------------------------
mkdir -p /var/lib/gone /etc/gone
if [ ! -f /etc/gone/config.toml ]; then
    cat > /etc/gone/config.toml <<'CONFIG'
# Réglages de la console G one (tous facultatifs ; valeurs par défaut en commentaire).
# gpio_reset = 17               # bouton reset (numéro BCM)
# gpio_power = 3                # bouton marche/arrêt (numéro BCM)
# settings_combo_seconds = 3.0  # maintien bleu + rouge pour ouvrir les réglages
# grab_gamepads = true          # false : les jeux voient aussi les manettes par la Gamepad API
#                               # (un appui peut alors être reçu deux fois : clavier et manette)
CONFIG
fi
[ -f /etc/gone/kiosk.env ] || cat > /etc/gone/kiosk.env <<'CONFIG'
# Affichage de la console G one.
GONE_RESOLUTION=640x480
CONFIG

install -m 644 "$ROOT"/system/gone.service "$ROOT"/system/gone-update.service \
    "$ROOT"/system/gone-update.timer /etc/systemd/system/
echo uinput > /etc/modules-load.d/gone.conf
modprobe uinput 2>/dev/null || true
systemctl daemon-reload
systemctl enable gone.service gone-update.timer >/dev/null 2>&1

# ---- Wi-Fi ----------------------------------------------------------------------
# Sur une installation neuve, le Wi-Fi reste bloqué tant qu'aucun pays n'est choisi.
if command -v raspi-config >/dev/null && rfkill list wifi 2>/dev/null | grep -q "Soft blocked: yes"; then
    step "Activation du Wi-Fi (pays : ${GONE_WIFI_COUNTRY:-FR})"
    raspi-config nonint do_wifi_country "${GONE_WIFI_COUNTRY:-FR}" || true
fi
rfkill unblock wifi 2>/dev/null || true

# ---- démarrage discret ------------------------------------------------------------
# Pas de texte ni de logo au démarrage. GONE_QUIET_BOOT=0 pour ne pas y toucher.
CMDLINE=/boot/firmware/cmdline.txt
CONFIG_TXT=/boot/firmware/config.txt
if [ "${GONE_QUIET_BOOT:-1}" = 1 ] && [ -f "$CMDLINE" ] && [ "$(wc -l < "$CMDLINE")" -le 1 ]; then
    [ -f "$CMDLINE.gone-backup" ] || cp "$CMDLINE" "$CMDLINE.gone-backup"
    line="$(tr -d '\n' < "$CMDLINE")"
    line="${line//console=tty1/console=tty3}"
    for option in quiet logo.nologo loglevel=3 vt.global_cursor_default=0; do
        case " $line " in *" $option "*) ;; *) line="$line $option" ;; esac
    done
    if [ "$line" != "$(tr -d '\n' < "$CMDLINE")" ]; then
        step "Démarrage discret (sauvegarde : $CMDLINE.gone-backup)"
        printf '%s\n' "$line" > "$CMDLINE.gone-new"
        mv "$CMDLINE.gone-new" "$CMDLINE"
    fi
    if [ -f "$CONFIG_TXT" ] && ! grep -q "^disable_splash=1" "$CONFIG_TXT"; then
        printf '\n[all]\ndisable_splash=1\n' >> "$CONFIG_TXT"
    fi
fi

step "Système configuré."
