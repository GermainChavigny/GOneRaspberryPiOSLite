#!/usr/bin/env bash
# Mise à jour automatique : installe la dernière release GitHub si elle est plus récente.
# La nouvelle version est prise en compte au prochain démarrage de la console.
# Code de sortie : 0 = déjà à jour, 10 = nouvelle version installée, autre = erreur.
set -euo pipefail

REPO="${GONE_REPO:-GermainChavigny/GOneRaspberryPiOSLite}"
STATE=/var/lib/gone
CURRENT="$(cat /opt/gone/current/VERSION 2>/dev/null || echo inconnue)"

report() {  # report <résultat> <dernière version>
    mkdir -p "$STATE"
    printf '{"checked_at": "%s", "current": "%s", "latest": "%s", "result": "%s"}\n' \
        "$(date -Iseconds)" "$CURRENT" "$2" "$1" > "$STATE/update-status.json.tmp"
    mv "$STATE/update-status.json.tmp" "$STATE/update-status.json"
}

exec 9> /run/gone-update.lock
flock -n 9 || { echo "Mise à jour déjà en cours."; exit 1; }

latest="$(curl -fsSL --max-time 20 "https://api.github.com/repos/$REPO/releases/latest" \
    | sed -n 's/.*"tag_name": *"\([^"]*\)".*/\1/p' | head -n 1)" || latest=""
if [ -z "$latest" ]; then
    echo "Aucune release trouvée (ou pas de connexion)."
    report error ""
    exit 1
fi

if grep -qxF "$latest" "$STATE/bad-versions" 2>/dev/null; then
    echo "$latest a déjà échoué sur cette console : ignorée."
    report current "$latest"
    exit 0
fi

# Plus récente si la version installée n'est pas une release (dev-…) ou si elle est inférieure.
newer=no
case "$CURRENT" in
    v[0-9]*)
        if [ "$latest" != "$CURRENT" ] && \
           [ "$(printf '%s\n%s\n' "$CURRENT" "$latest" | sort -V | tail -n 1)" = "$latest" ]; then
            newer=yes
        fi ;;
    *) newer=yes ;;
esac
if [ "$newer" = no ]; then
    echo "Déjà à jour ($CURRENT)."
    report current "$latest"
    exit 0
fi

echo "Mise à jour $CURRENT -> $latest"
# Utilisateur de la console : celui de la connexion automatique.
user="$(sed -n 's/.*--autologin \([^ ]*\).*/\1/p' /etc/systemd/system/getty@tty1.service.d/autologin.conf 2>/dev/null | head -n 1 || true)"
installer="$(mktemp)"
trap 'rm -f "$installer"' EXIT
if curl -fsSL --max-time 60 "https://raw.githubusercontent.com/$REPO/$latest/install.sh" -o "$installer" \
    && bash "$installer" --ref "$latest" --no-reboot ${user:+--user "$user"}; then
    report staged "$latest"
    exit 10
fi
report error "$latest"
exit 1
