"use strict";
// Menu de réglages de la console, piloté à la manette.
// Les manettes arrivent ici sous forme de touches (voir gone/padlogic.py) :
// joueur 1 = ZQSD + B (bleu) / V (rouge) / C (jaune), joueur 2 = flèches + K / L / M.

const KEYS = {
  z: "up", ArrowUp: "up", s: "down", ArrowDown: "down",
  q: "left", ArrowLeft: "left", d: "right", ArrowRight: "right",
  b: "ok", k: "ok", Enter: "ok",
  v: "back", l: "back", Escape: "back",
  c: "alt", m: "alt",
};
const VISIBLE_ITEMS = 7;
const LIST_HINTS = "Croix : choisir   Bleu : valider   Rouge : retour";

const $title = document.getElementById("title");
const $content = document.getElementById("content");
const $hints = document.getElementById("hints");

let screen = null;

function show(next) {
  screen = next;
  draw();
}

function draw() {
  $title.textContent = screen.title;
  $hints.textContent = screen.hints || "";
  $content.replaceChildren(...screen.render());
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

async function api(path, body) {
  const options = body === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  };
  const response = await fetch(path, options);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

// ---- écrans génériques -------------------------------------------------------

// Liste d'entrées { label, detail, run }, précédée de lignes de texte facultatives.
function listScreen({ title, lines = [], items = [], back }) {
  let index = 0;
  return {
    title,
    hints: LIST_HINTS,
    set(update) {
      if (update.lines) lines = update.lines;
      if (update.items) { items = update.items; index = Math.min(index, Math.max(0, items.length - 1)); }
      if (screen === this) draw();
    },
    render() {
      const nodes = lines.map(line => el("div", "note", line));
      const first = Math.max(0, Math.min(index - Math.floor(VISIBLE_ITEMS / 2), items.length - VISIBLE_ITEMS));
      items.slice(first, first + VISIBLE_ITEMS).forEach((item, offset) => {
        const row = el("div", first + offset === index ? "item selected" : "item");
        row.append(el("span", "", item.label), el("span", "detail", item.detail || ""));
        nodes.push(row);
      });
      return nodes;
    },
    key(action) {
      if (action === "back") return back();
      if (!items.length) return;
      if (action === "up") index = (index + items.length - 1) % items.length;
      else if (action === "down") index = (index + 1) % items.length;
      else if (action === "ok") items[index].run();
    },
  };
}

function messageScreen(title, text, next) {
  return {
    title,
    hints: "Bleu : continuer",
    render: () => [el("div", "text", text), el("div", "item selected", "OK")],
    key(action) { if (action === "ok" || action === "back") next(); },
  };
}

function busyScreen(title, text) {
  return { title, render: () => [el("div", "text", text)], key() {} };
}

// ---- menu principal ----------------------------------------------------------

function leave() {
  api("/api/exit", {}).catch(() => { location.href = "/lobby/index.html"; });
}

function menu() {
  return listScreen({
    title: "Réglages",
    back: leave,
    items: [
      { label: "Wi-Fi", run: () => show(wifiScreen()) },
      { label: "Manettes", run: () => show(padsScreen()) },
      { label: "Mise à jour", run: () => show(updateScreen()) },
      { label: "Informations", run: () => show(infoScreen()) },
      { label: "Retour au lobby", run: leave },
    ],
  });
}

// ---- Wi-Fi -------------------------------------------------------------------

function wifiScreen() {
  const self = listScreen({ title: "Wi-Fi", lines: ["Recherche des réseaux…"], back: () => show(menu()) });
  const retry = { label: "Actualiser", run: () => show(wifiScreen()) };
  api("/api/wifi/networks").then(data => {
    if (!data.ok) return self.set({ lines: [data.error], items: [retry] });
    const items = data.networks.map(network => ({
      label: network.ssid,
      detail: `${network.signal} %` + (network.active ? " · connecté" : network.secure ? "" : " · ouvert"),
      run: () => network.secure ? show(keyboardScreen(network.ssid, "")) : connect(network.ssid, "", false),
    }));
    self.set({ lines: [items.length ? "Choisissez un réseau." : "Aucun réseau trouvé."], items: [...items, retry] });
  }).catch(() => self.set({ lines: ["Recherche des réseaux impossible."], items: [retry] }));
  return self;
}

async function connect(ssid, password, secure) {
  show(busyScreen("Wi-Fi", `Connexion à ${ssid}…`));
  let result;
  try {
    result = await api("/api/wifi/connect", { ssid, password });
  } catch {
    result = { ok: false, error: "Connexion impossible." };
  }
  if (result.ok) {
    show(messageScreen("Wi-Fi", `Connecté à ${ssid}.`, () => show(menu())));
  } else {
    const retry = () => show(secure ? keyboardScreen(ssid, password) : wifiScreen());
    show(messageScreen("Wi-Fi", result.error || "Connexion impossible.", retry));
  }
}

// ---- clavier virtuel -----------------------------------------------------------

const LETTERS = ["1234567890", "azertyuiop", "qsdfghjklm", "wxcvbn.-_@"];
const SYMBOLS = ["!\"#$%&'()*", "+,-./:;<=>", "?@[\\]^_`{|", "}~"];
const ACTIONS = [["shift", "Maj"], ["symbols", "#+="], ["space", "Espace"], ["delete", "Effacer"], ["done", "Valider"]];
const COLUMNS = 10;

function keyboardScreen(ssid, initial) {
  let text = initial, shift = false, symbols = false, row = 1, col = 0;
  const layout = () => symbols ? SYMBOLS : shift ? LETTERS.map(line => line.toUpperCase()) : LETTERS;
  const width = r => r < layout().length ? layout()[r].length : ACTIONS.length;
  const clamp = () => { col = Math.min(col, width(row) - 1); };

  function press() {
    const rows = layout();
    if (row < rows.length) { text += rows[row][col]; return; }
    const action = ACTIONS[col][0];
    if (action === "shift") { shift = !shift; symbols = false; }
    else if (action === "symbols") symbols = !symbols;
    else if (action === "space") text += " ";
    else if (action === "delete") text = text.slice(0, -1);
    else if (action === "done" && text) connect(ssid, text, true);
  }

  return {
    title: "Wi-Fi",
    hints: "Bleu : taper   Rouge : effacer   Jaune : majuscules",
    render() {
      const shown = text.length > 40 ? "…" + text.slice(-39) : text;
      const keys = el("div", "keys");
      const rows = layout();
      rows.forEach((line, r) => {
        for (let c = 0; c < COLUMNS; c++) {
          const key = el("div", c < line.length ? "key" : "key empty", line[c] || "");
          if (r === row && c === col) key.classList.add("selected");
          keys.append(key);
        }
      });
      ACTIONS.forEach(([action, label], c) => {
        const key = el("div", "key wide", label);
        if ((action === "shift" && shift && !symbols) || (action === "symbols" && symbols)) key.classList.add("on");
        if (row === rows.length && c === col) key.classList.add("selected");
        keys.append(key);
      });
      return [el("div", "note", `Mot de passe pour ${ssid}`), el("div", "field", shown + "_"), keys];
    },
    key(action) {
      const last = layout().length;          // indice de la rangée d'actions
      if (action === "left") col = (col + width(row) - 1) % width(row);
      else if (action === "right") col = (col + 1) % width(row);
      else if (action === "up") {
        if (row === last) { row = last - 1; col *= 2; }
        else if (row === 0) { row = last; col = Math.floor(col / 2); }
        else row--;
      } else if (action === "down") {
        if (row === last) { row = 0; col *= 2; }
        else if (row === last - 1) { row = last; col = Math.floor(col / 2); }
        else row++;
      } else if (action === "ok") press();
      else if (action === "alt") { shift = !shift; symbols = false; }
      else if (action === "back") {
        if (!text) return show(wifiScreen());
        text = text.slice(0, -1);
      }
      clamp();
    },
  };
}

// ---- manettes ------------------------------------------------------------------

function padsScreen() {
  const describe = players => [1, 2].map(number => {
    const pad = players.find(p => p.player === number);
    return `Joueur ${number} : ${pad ? pad.name : "aucune manette"}`;
  });
  const self = listScreen({
    title: "Manettes",
    lines: ["…"],
    back: () => show(menu()),
    items: [
      { label: "Inverser joueur 1 et joueur 2",
        run: () => api("/api/players/swap", {}).then(data => self.set({ lines: describe(data.players) })).catch(() => {}) },
      { label: "Retour", run: () => show(menu()) },
    ],
  });
  const refresh = () => {
    if (screen !== self) return;
    api("/api/status").then(data => self.set({ lines: describe(data.players) })).catch(() => {});
    setTimeout(refresh, 1000);
  };
  setTimeout(refresh, 0);
  return self;
}

// ---- mise à jour -----------------------------------------------------------------

function updateScreen() {
  const self = listScreen({
    title: "Mise à jour",
    lines: ["Version installée : …"],
    back: () => show(menu()),
    items: [
      { label: "Rechercher une mise à jour", run: runUpdate },
      { label: "Retour", run: () => show(menu()) },
    ],
  });
  api("/api/status").then(data => self.set({ lines: [`Version installée : ${data.version}`] })).catch(() => {});
  return self;
}

async function runUpdate() {
  show(busyScreen("Mise à jour", "Recherche en cours…"));
  let data;
  try {
    data = await api("/api/update", {});
  } catch {
    data = { result: "error" };
  }
  if (data.result === "staged") {
    show(busyScreen("Mise à jour", "Mise à jour installée. La console redémarre…"));
  } else if (data.result === "current") {
    show(messageScreen("Mise à jour", "La console est à jour.", () => show(menu())));
  } else {
    show(messageScreen("Mise à jour", "Mise à jour impossible. Vérifiez la connexion Internet.", () => show(menu())));
  }
}

// ---- informations ------------------------------------------------------------------

function infoScreen() {
  const cards = { none: "aucune", copying: "lecture en cours", ready: "jeu prêt", error: "illisible ou sans jeu" };
  const self = listScreen({
    title: "Informations",
    lines: ["…"],
    back: () => show(menu()),
    items: [{ label: "Retour", run: () => show(menu()) }],
  });
  Promise.all([api("/api/status"), api("/api/network")]).then(([status, network]) => {
    const link = network.wifi_connected ? `Wi-Fi ${network.ssid}` : network.ethernet ? "câble Ethernet" : "non connecté";
    self.set({ lines: [
      `Version : ${status.version}`,
      `Réseau : ${link}`,
      `Adresse IP : ${network.ip || "aucune"}`,
      `Cartouche : ${cards[status.card] || status.card}`,
    ] });
  }).catch(() => self.set({ lines: ["Informations indisponibles."] }));
  return self;
}

// ---- démarrage ---------------------------------------------------------------------

addEventListener("keydown", event => {
  const action = KEYS[event.key];
  if (!action) return;
  event.preventDefault();
  if (event.repeat && action !== "up" && action !== "down" && action !== "left" && action !== "right") return;
  screen.key(action);
  draw();
});

// Le « # » de l'adresse ouvre directement un écran (pratique pour le développement).
const START = {
  "#wifi": wifiScreen, "#keyboard": () => keyboardScreen("Maison", ""),
  "#pads": padsScreen, "#update": updateScreen, "#info": infoScreen,
};
show((START[location.hash] || menu)());
