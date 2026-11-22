# G one — logiciel de la console

Console rétro sur Raspberry Pi : un lecteur de cartouches (cartes CompactFlash), deux
manettes USB, un bouton reset et un bouton marche/arrêt. Les jeux sont des exports HTML
(Construct 3) affichés par Chromium en plein écran.

## Installation

1. Flasher **Raspberry Pi OS Lite (64 bits)** avec Raspberry Pi Imager. Dans les réglages
   de l'Imager, créer un utilisateur et, si possible, renseigner le Wi-Fi (ou brancher un
   câble Ethernet) : l'installation a besoin d'Internet.
2. Se connecter (clavier ou SSH) et lancer :

```bash
curl -fsSL https://raw.githubusercontent.com/GermainChavigny/GOneRaspberryPiOSLite/master/install.sh | sudo bash
```

La console redémarre à la fin et s'ouvre sur le lobby. Compter 10 à 20 minutes, surtout
pour le téléchargement de Chromium.

Options, à placer après `sudo bash -s --` : `--ref v2.1.0` (version précise),
`--user nom`, `--no-reboot`.

## Utilisation

| Action | Effet |
|---|---|
| Insérer une cartouche | Le jeu est copié, puis son icône apparaît dans le lobby |
| Bouton jaune (lobby, cartouche prête) | Lance le jeu |
| Bouton reset pendant un jeu | Retour au lobby |
| Bouton reset dans le lobby | Ouvre les réglages (ou les referme) |
| Bleu + rouge maintenus 3 s dans le lobby | Ouvre aussi les réglages |
| Bouton marche/arrêt | Éteint la console |

**Réglages** (à la manette : croix pour choisir, bleu pour valider, rouge pour revenir) :

- **Wi-Fi** : choisir un réseau, taper le mot de passe au clavier virtuel.
- **Manettes** : voir qui est joueur 1 et joueur 2, les inverser.
- **Mise à jour** : chercher et installer une nouvelle version tout de suite.
- **Informations** : version, réseau, adresse IP, état de la cartouche.

**Manettes.** Le joueur dépend du **port USB**, pas de l'ordre de branchement : le premier
port utilisé devient le joueur 1, le deuxième le joueur 2, et cela ne change plus. Les
manettes peuvent être branchées et débranchées à tout moment.

Les jeux reçoivent les manettes sous forme de touches de clavier :

| | Haut / bas / gauche / droite | Bleu | Rouge | Jaune |
|---|---|---|---|---|
| Joueur 1 | Z / S / Q / D | B | V | C |
| Joueur 2 | flèches | K | L | M |

Chromium ne voit plus les manettes elles-mêmes : dans un jeu, seules les conditions
« clavier » se déclenchent, les conditions « Gamepad » restent inactives. Pour un jeu qui
ne lit que la Gamepad API, mettre `grab_gamepads = false` dans `/etc/gone/config.toml`.

## Cartouches

Une cartouche est une carte formatée en FAT avec, à la racine :

- `htmlGame/index.html` : le jeu (export HTML de Construct) ;
- `icon.png` : l'icône affichée dans le lobby (facultative).

## Mises à jour automatiques

La console cherche une nouvelle release GitHub deux minutes après le démarrage, puis
toutes les 12 heures. Elle l'installe en arrière-plan ; la nouvelle version est utilisée
**au démarrage suivant**. Si elle ne démarre pas trois fois de suite, l'ancienne version
est remise en place et la version fautive n'est plus réinstallée.

Publier une version :

```bash
git tag v2.0.0
git push origin master v2.0.0
```

Le workflow `.github/workflows/release.yml` lance les tests puis crée la release.

## Organisation du code

| Dossier | Contenu |
|---|---|
| `gone/` | Le daemon Python (service `gone.service`, lancé en root) |
| `web/` | Lobby, page de transition, menu de réglages, icônes par défaut |
| `system/` | Services systemd et session graphique (Chromium) |
| `scripts/` | Configuration du système, mise à jour, retour arrière |
| `tests/` | Tests automatiques (`python3 -m pytest tests`) |
| `legacy/` | Anciens scripts shell (v1), conservés pour référence |

Modules du daemon : `cards.py` (cartouches), `gamepads.py` et `padlogic.py` (manettes),
`players.py` (joueur selon le port), `buttons.py` (GPIO), `browser.py` (pilotage de
Chromium), `web.py` (serveur local et API du menu), `wifi.py`, `app.py` (états de la
console).

Sur la console : programme dans `/opt/gone/current`, réglages dans `/etc/gone/`
(`config.toml` pour les GPIO, `kiosk.env` pour la résolution), données dans `/var/lib/gone/`.

## Dépannage

Un clavier branché sur la console donne un terminal avec `Ctrl+Alt+F2`. Sinon, passer par SSH.

```bash
journalctl -u gone -f              # journal du daemon (cartouches, manettes, boutons)
cat ~/.gone-kiosk.log              # journal de l'affichage (X, Chromium)
sudo systemctl restart gone        # relancer le daemon
sudo bash /opt/gone/current/scripts/update.sh   # forcer une mise à jour
```

Pour essayer le menu de réglages sans console, sur un ordinateur avec Python 3.11+ et
`aiohttp` : `GONE_DEV=1 GONE_STATE_DIR=/tmp/gone python3 -m gone`, puis ouvrir
`http://localhost:8000/settings/index.html` (touches ZQSD, B, V, C).
