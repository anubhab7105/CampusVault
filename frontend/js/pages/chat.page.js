// ===========================
// chat.page.js
// Handles in-web chat
// ===========================
import { getCurrentUser } from "../auth.js";

document.addEventListener("DOMContentLoaded", () => {
  const messagesContainer = document.getElementById("chat-messages");
  const chatInput = document.getElementById("chat-input");
  const sendBtn = document.getElementById("send-btn");

  const user = getCurrentUser();

  function appendMessage(text, self = false) {
    const msg = document.createElement("div");
    msg.className = "cv-chat-message" + (self ? " self" : "");
    msg.textContent = text;
    messagesContainer.appendChild(msg);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  sendBtn.addEventListener("click", () => {
    const msg = chatInput.value.trim();
    if (!msg) return;
    appendMessage(msg, true);
    chatInput.value = "";

    setTimeout(() => {
      appendMessage(`Reply to "${msg}" from faculty`);
    }, 700);
  });

  chatInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendBtn.click();
  });
});
