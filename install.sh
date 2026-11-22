#!/usr/bin/env bash
# Installeur de la console G one, pour Raspberry Pi OS Lite (64 bits).
#
#   curl -fsSL https://raw.githubusercontent.com/GermainChavigny/GOneRaspberryPiOSLite/master/install.sh | sudo bash
#
# Options (après « sudo bash -s -- ») :
#   --ref <tag|branche>   version à installer (défaut : dernière release, sinon master)
#   --user <nom>          utilisateur de la console (défaut : celui qui lance sudo)
#   --no-reboot           ne pas redémarrer à la fin
#
# Le même script sert aux mises à jour automatiques (scripts/update.sh).
set -euo pipefail

main() {
    local repo="${GONE_REPO:-GermainChavigny/GOneRaspberryPiOSLite}"
    local prefix=/opt/gone
    local ref="${GONE_REF:-}" user="${GONE_USER:-${SUDO_USER:-}}" reboot=yes

    while [ $# -gt 0 ]; do
        case "$1" in
            --ref) ref="$2"; shift 2 ;;
            --user) user="$2"; shift 2 ;;
            --no-reboot) reboot=no; shift ;;
            *) echo "Option inconnue : $1" >&2; exit 2 ;;
        esac
    done

    [ "$(id -u)" -eq 0 ] || { echo "À lancer avec sudo." >&2; exit 1; }
    if [ -z "$user" ] || [ "$user" = root ]; then
        user="$(getent passwd 1000 | cut -d: -f1 || true)"
    fi
    getent passwd "$user" >/dev/null || { echo "Utilisateur introuvable : préciser --user <nom>." >&2; exit 1; }

    if ! command -v curl >/dev/null || ! command -v tar >/dev/null; then
        apt-get update -y
        apt-get install -y curl ca-certificates tar
    fi

    if [ -z "$ref" ]; then
        ref="$(curl -fsSL --max-time 20 "https://api.github.com/repos/$repo/releases/latest" 2>/dev/null \
            | sed -n 's/.*"tag_name": *"\([^"]*\)".*/\1/p' | head -n 1 || true)"
        [ -n "$ref" ] || ref=master
    fi
    local version="$ref"
    case "$ref" in
        v[0-9]*) ;;
        *) version="dev-${ref//\//-}-$(date +%Y%m%d%H%M%S)" ;;
    esac

    echo "==> G one : installation de $version pour l'utilisateur $user"
    mkdir -p "$prefix/releases"
    rm -rf "$prefix"/releases/.download.*
    local tmp dest="$prefix/releases/$version"
    tmp="$(mktemp -d "$prefix/releases/.download.XXXXXX")"
    # shellcheck disable=SC2064  # $tmp doit être développé maintenant
    trap "rm -rf '$tmp'" EXIT
    curl -fsSL --max-time 300 "https://github.com/$repo/archive/$ref.tar.gz" \
        | tar -xz -C "$tmp" --strip-components=1 --no-same-owner
    [ -f "$tmp/gone/__main__.py" ] && [ -f "$tmp/scripts/setup-system.sh" ] \
        || { echo "Archive inattendue : installation annulée." >&2; exit 1; }
    echo "$version" > "$tmp/VERSION"
    rm -rf "$tmp/legacy" "$tmp/tests" "$tmp/.github"
    chmod 755 "$tmp" "$tmp"/install.sh "$tmp"/scripts/*.sh "$tmp"/system/*.sh
    rm -rf "$dest"
    mv "$tmp" "$dest"
    trap - EXIT

    echo "==> Configuration du système"
    bash "$dest/scripts/setup-system.sh" "$user"

    # Bascule : « previous » garde l'ancienne version pour un retour arrière automatique.
    local old=""
    [ -L "$prefix/current" ] && old="$(readlink -f "$prefix/current" || true)"
    if [ -n "$old" ] && [ "$old" != "$dest" ] && [ -d "$old" ]; then
        ln -sfn "$old" "$prefix/previous"
    fi
    ln -sfn "$dest" "$prefix/current.new"
    mv -Tf "$prefix/current.new" "$prefix/current"
    rm -f /var/lib/gone/failcount

    local keep_previous="" release
    [ -L "$prefix/previous" ] && keep_previous="$(readlink -f "$prefix/previous" || true)"
    for release in "$prefix"/releases/*; do
        [ "$release" = "$dest" ] || [ "$release" = "$keep_previous" ] || rm -rf "$release"
    done

    echo "==> G one $version installé."
    if [ "$reboot" = yes ]; then
        echo "Redémarrage dans 5 secondes (Ctrl+C pour annuler)…"
        sleep 5
        systemctl reboot
    else
        echo "Redémarrer la console pour l'utiliser : sudo reboot"
    fi
}

# Tout le script est dans main() : un téléchargement coupé en route n'exécute rien.
main "$@"
