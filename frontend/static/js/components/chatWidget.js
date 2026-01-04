// ===========================
// chatWidget.js
// reusable chat widget component
// ===========================

export class ChatWidget {
  constructor(container, user) {
    this.container = container;
    this.user = user;
    this.init();
  }

  init() {
    this.container.innerHTML = `
      <div class="cv-chat-messages" id="chat-messages"></div>
      <div class="cv-chat-input">
        <input type="text" id="chat-input" placeholder="Type a message..." />
        <button id="send-btn">Send</button>
      </div>
    `;

    this.messagesContainer = this.container.querySelector("#chat-messages");
    this.chatInput = this.container.querySelector("#chat-input");
    this.sendBtn = this.container.querySelector("#send-btn");

    this.sendBtn.addEventListener("click", () => this.sendMessage());
    this.chatInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter") this.sendMessage();
    });
  }

  appendMessage(text, self = false) {
    const msg = document.createElement("div");
    msg.className = "cv-chat-message" + (self ? " self" : "");
    msg.textContent = text;
    this.messagesContainer.appendChild(msg);
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
  }

  sendMessage() {
    const msg = this.chatInput.value.trim();
    if (!msg) return;

    this.appendMessage(msg, true);
    this.chatInput.value = "";

    // Simulated reply
    setTimeout(() => {
      this.appendMessage(`Reply to "${msg}" from system`);
    }, 700);
  }
}
