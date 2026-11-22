#!/usr/bin/env bash
# Retour arrière automatique après une mise à jour ratée.
# Lancé avant chaque démarrage du daemon : compte les démarrages qui n'ont pas tenu
# 20 secondes (le daemon remet le compteur à zéro). Au troisième, la version précédente
# est remise en place et la version fautive n'est plus jamais réinstallée.
set -u

STATE=/var/lib/gone
PREFIX=/opt/gone
mkdir -p "$STATE"

count="$(cat "$STATE/failcount" 2>/dev/null || echo 0)"
case "$count" in ''|*[!0-9]*) count=0 ;; esac

if [ "$count" -ge 3 ] && [ -L "$PREFIX/previous" ]; then
    bad="$(cat "$PREFIX/current/VERSION" 2>/dev/null || echo inconnue)"
    previous="$(readlink -f "$PREFIX/previous")"
    if [ -d "$previous" ] && [ "$previous" != "$(readlink -f "$PREFIX/current")" ]; then
        echo "GOne : $bad ne démarre pas, retour à $(cat "$previous/VERSION" 2>/dev/null)"
        echo "$bad" >> "$STATE/bad-versions"
        ln -sfn "$previous" "$PREFIX/current.new" && mv -Tf "$PREFIX/current.new" "$PREFIX/current"
        rm -f "$PREFIX/previous"
        count=0
    fi
fi

echo $((count + 1)) > "$STATE/failcount"
exit 0
