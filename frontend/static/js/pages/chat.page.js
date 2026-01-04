// js/pages/chat.page.js
// Combined chat logic: websocket + REST fallback + UI rendering + demo reply
import { getCurrentUser } from "../auth.js";

/* Config: override by setting these in a global config.js if you prefer.
   If you already load a config module, remove these and import instead. */
const WS_URL = window.WS_URL ?? null; // set globally (e.g. in config.js) if available
const POST_URL = window.POST_URL ?? "/messages"; // fallback REST endpoint

// DOM
const messagesEl = document.getElementById("messages");
const form = document.getElementById("messageForm");
const input = document.getElementById("messageInput");
const usersListEl = document.getElementById("usersList");

// Current user (try to get from auth.js, fallback to demo)
const authUser = (() => {
  try {
    const u = getCurrentUser();
    if (u && u.id) return u;
  } catch (e) { /* ignore */ }
  return { id: "you-123", name: "Anubhab Das", email: "anubhab@example.com" };
})();
const currentUser = authUser;

// State
let messages = [];
let participants = [
  { id: currentUser.id, name: currentUser.name, email: currentUser.email },
  { id: "u1", name: "Alice", email: "alice@mail.com" },
  { id: "u2", name: "Bob", email: "bob@mail.com" },
];

let ws = null;

/* ------------------ helpers ------------------ */
function initialsFor(user) {
  if (!user) return "?";
  if (user.name) {
    const parts = user.name.trim().split(/\s+/);
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return parts[0].slice(0, 2).toUpperCase();
  }
  if (user.email) {
    const left = user.email.split("@")[0];
    return left.slice(0, 2).toUpperCase();
  }
  return "??";
}

function formatTime(ts) {
  const d = new Date(ts || Date.now());
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function createAvatarEl(user) {
  const a = document.createElement("div");
  a.className = "avatar";
  a.textContent = initialsFor(user);
  return a;
}

function createMessageElement(msg) {
  const row = document.createElement("div");
  row.className = "message-row" + (msg.user && msg.user.id === currentUser.id ? " me" : "");

  const avatar = createAvatarEl(msg.user || {});
  const bubble = document.createElement("div");
  bubble.className = "message" + (msg.user && msg.user.id === currentUser.id ? " me" : "");

  // meta: name • email • time
  const meta = document.createElement("div");
  meta.className = "meta";
  const nameSpan = document.createElement("span");
  nameSpan.textContent = msg.user?.name || "Unknown";
  nameSpan.style.fontWeight = "600";

  // optional email (small)
  if (msg.user?.email) {
    const emailSpan = document.createElement("span");
    emailSpan.textContent = msg.user.email;
    emailSpan.style.opacity = "0.9";
    emailSpan.style.fontSize = "12px";
    emailSpan.style.marginLeft = "6px";
    meta.appendChild(nameSpan);
    meta.appendChild(emailSpan);
  } else {
    meta.appendChild(nameSpan);
  }

  const timeSpan = document.createElement("span");
  timeSpan.className = "time-pill";
  timeSpan.textContent = formatTime(msg.timestamp);
  timeSpan.style.marginLeft = "8px";
  meta.appendChild(timeSpan);

  const body = document.createElement("div");
  body.className = "body";
  body.textContent = msg.text;

  // pending indicator (small)
  if (msg.pending) {
    const pend = document.createElement("span");
    pend.textContent = " • sending…";
    pend.style.fontSize = "12px";
    pend.style.color = "var(--muted)";
    pend.style.marginLeft = "6px";
    meta.appendChild(pend);
  }

  bubble.appendChild(meta);
  bubble.appendChild(body);

  // layout: mine => bubble then avatar, others => avatar then bubble
  if (msg.user && msg.user.id === currentUser.id) {
    row.appendChild(bubble);
    row.appendChild(avatar);
  } else {
    row.appendChild(avatar);
    row.appendChild(bubble);
  }

  row.dataset.msgId = msg.id || "";
  return row;
}

/* ------------------ render ------------------ */
function renderAllMessages() {
  messagesEl.innerHTML = "";
  messages.forEach((m) => messagesEl.appendChild(createMessageElement(m)));
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function pushMessage(msg) {
  messages.push(msg);
  messagesEl.appendChild(createMessageElement(msg));
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function renderParticipants() {
  usersListEl.innerHTML = "";
  participants.forEach((p) => {
    const row = document.createElement("div");
    row.className = "participant";
    const av = createAvatarEl(p);
    const meta = document.createElement("div");
    meta.className = "p-meta";
    const nm = document.createElement("div");
    nm.className = "p-name";
    nm.textContent = p.name || "Unknown";
    const em = document.createElement("div");
    em.className = "p-email";
    em.textContent = p.email || "";
    meta.appendChild(nm);
    meta.appendChild(em);
    row.appendChild(av);
    row.appendChild(meta);
    usersListEl.appendChild(row);
  });
}

/* ------------------ networking ------------------ */
async function sendMessageToServer(msg) {
  // try ws first
  if (ws && ws.readyState === WebSocket.OPEN) {
    try {
      ws.send(JSON.stringify({ type: "message", payload: msg }));
      return { ok: true, via: "ws" };
    } catch (e) {
      console.warn("ws send failed", e);
    }
  }

  // fallback to POST
  try {
    const res = await fetch(POST_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(msg),
    });
    if (res.ok) return { ok: true, via: "post" };
    return { ok: false, status: res.status };
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

/* ------------------ send handling ------------------ */
async function handleSend(text) {
  text = (text || "").trim();
  if (!text) return;

  const tempMsg = {
    id: `_tmp_${Date.now()}`,
    user: currentUser,
    text,
    timestamp: Date.now(),
    pending: true,
  };
  pushMessage(tempMsg);
  input.value = "";

  const result = await sendMessageToServer({
    id: tempMsg.id,
    user: currentUser,
    text: tempMsg.text,
    timestamp: tempMsg.timestamp,
  });

  if (result.ok) {
    // mark as delivered (remove pending flag)
    const m = messages.find((mm) => mm.id === tempMsg.id);
    if (m) {
      delete m.pending;
      // re-render that message node (simple approach: re-render all)
      renderAllMessages();
    }
  } else {
    console.warn("failed to send msg", result);
    // leave pending but visually we could mark failed — leaving as-is for now
  }

  // If there's no backend, simulate a quick reply from faculty (keeps UX lively)
  if (!WS_URL && (!window.POST_URL || window.POST_URL === "/messages")) {
    setTimeout(() => {
      const reply = {
        id: `sim_${Date.now()}`,
        user: { id: "faculty-1", name: "Faculty Bot", email: "faculty@college.edu" },
        text: `Reply to "${text}" from faculty`,
        timestamp: Date.now(),
      };
      pushMessage(reply);
    }, 600);
  }
}

/* ------------------ websocket setup ------------------ */
function setupWebSocket() {
  if (!WS_URL) return;
  try {
    ws = new WebSocket(WS_URL);
    ws.addEventListener("open", () => console.log("ws open"));
    ws.addEventListener("message", (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.type === "message" && msg.payload) {
          const exists = messages.some((m) => m.id === msg.payload.id);
          if (!exists) pushMessage(msg.payload);
        } else if (msg.type === "participants" && msg.payload) {
          participants = msg.payload;
          renderParticipants();
        }
      } catch (err) {
        console.error("ws parse", err);
      }
    });
    ws.addEventListener("close", () => console.log("ws closed"));
    ws.addEventListener("error", (e) => console.warn("ws error", e));
  } catch (e) {
    console.warn("ws init failed", e);
  }
}

/* ------------------ demo init ------------------ */
function loadDemo() {
  messages = [
    {
      id: "s1",
      user: { id: "u1", name: "Alice", email: "alice@mail.com" },
      text: "Welcome to Group!",
      timestamp: Date.now() - 60000,
    },
    {
      id: "s2",
      user: { id: "u2", name: "Bob", email: "bob@mail.com" },
      text: "hi",
      timestamp: Date.now() - 30000,
    },
  ];
  renderAllMessages();
  renderParticipants();
}

/* ------------------ DOM events ------------------ */
form.addEventListener("submit", (e) => {
  e.preventDefault();
  handleSend(input.value);
});

// allow Enter key on input as well (works, but form submit already handles it)
input.addEventListener("keypress", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    handleSend(input.value);
  }
});

/* ------------------ initialization ------------------ */
(function init() {
  loadDemo();
  setupWebSocket();
})();
