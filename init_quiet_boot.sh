#!/bin/bash

echo "Configuration du démarrage silencieux avec image..."

# Chemins
BOOT_DIR="/boot/firmware"
CONFIG_FILE="$BOOT_DIR/config.txt"
CMDLINE_FILE="$BOOT_DIR/cmdline.txt"
SPLASH_IMAGE="${1:-.}/splash.png"

# Vérifier l'image si fournie
if [ "$1" != "" ] && [ ! -f "$SPLASH_IMAGE" ]; then
    echo "Erreur: L'image $SPLASH_IMAGE n'existe pas"
    exit 1
fi

# Configuration de config.txt
echo "Configuration de $CONFIG_FILE..."

# Désactiver le splash screen standard
if ! grep -q "disable_splash=1" "$CONFIG_FILE"; then
  sudo sed -i '/^\[all\]/a disable_splash=1' "$CONFIG_FILE"
  echo "✓ Splash standard désactivé"
fi

# Mode vidéo pour éviter les messages
if ! grep -q "dtoverlay=vc4-kms-v3d" "$CONFIG_FILE"; then
  echo "dtoverlay=vc4-kms-v3d" | sudo tee -a "$CONFIG_FILE" > /dev/null
  echo "✓ Mode vidéo KMS activé"
fi

# Configuration de cmdline.txt
echo "Configuration de $CMDLINE_FILE..."

# Faire une sauvegarde
sudo cp "$CMDLINE_FILE" "$CMDLINE_FILE.bak"

# Rediriger les messages console
sudo sed -i 's/console=tty1/console=tty3/' "$CMDLINE_FILE"

# Masquer le logo Raspberry Pi
if ! grep -q "logo.nologo" "$CMDLINE_FILE"; then
  sudo sed -i 's/$/ logo.nologo/' "$CMDLINE_FILE"
  echo "✓ Logo masqué"
fi

# Réduire le niveau de log kernel
if ! grep -q "loglevel=3" "$CMDLINE_FILE"; then
  sudo sed -i 's/$/ loglevel=3/' "$CMDLINE_FILE"
  echo "✓ Logs kernel réduits"
fi

# Masquer le curseur
if ! grep -q "vt.global_cursor_default=0" "$CMDLINE_FILE"; then
  sudo sed -i 's/$/ vt.global_cursor_default=0/' "$CMDLINE_FILE"
  echo "✓ Curseur masqué"
fi

# Activer Plymouth
if ! grep -q "plymouth.enable=1" "$CMDLINE_FILE"; then
  sudo sed -i 's/$/ plymouth.enable=1/' "$CMDLINE_FILE"
  echo "✓ Plymouth activé"
fi

# Installer Plymouth si nécessaire
if ! command -v plymouth &> /dev/null; then
  echo "Installation de Plymouth..."
  sudo apt-get update -qq
  sudo apt-get install -y -qq plymouth plymouth-themes
fi

# Configurer systemd pour démarrage silencieux
echo "Configuration systemd..."
sudo mkdir -p /etc/systemd/system-preset
if ! grep -q "getty@" /etc/systemd/system-preset/99-default-preset.preset 2>/dev/null; then
  sudo tee -a /etc/systemd/system-preset/99-default-preset.preset > /dev/null << 'EOF'
disable getty@.service
disable serial-getty@.service
EOF
  echo "✓ Messages getty masqués"
fi

# Si une image est fournie, la copier comme splash
if [ "$1" != "" ] && [ -f "$SPLASH_IMAGE" ]; then
    echo "Configuration de l'image splash..."
    SPLASH_DIR="/usr/share/pixmaps"
    sudo cp "$SPLASH_IMAGE" "$SPLASH_DIR/gone-splash.png"
    echo "✓ Image copiée vers $SPLASH_DIR/gone-splash.png"
fi

echo ""
echo "✓ Démarrage silencieux configuré"
echo ""
echo "Configuration appliquée:"
echo "  - Console redirigée vers tty3"
echo "  - Logo Raspberry Pi masqué"
echo "  - Logs kernel minimisés (loglevel=3)"
echo "  - Curseur masqué"
echo "  - Plymouth activé"
[ "$1" != "" ] && echo "  - Image splash configurée"
echo ""
echo "Redémarrez pour appliquer les changements:"
echo "  sudo reboot"
echo ""
echo "Fichier de sauvegarde:"
echo "  $CMDLINE_FILE.bak"