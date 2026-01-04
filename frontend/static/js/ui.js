// ===========================
// ui.js
// shared UI helpers
// ===========================

export function showToast(message, type = "success") {
  const containerId = "toaster-container";
  let container = document.getElementById(containerId);
  if (!container) {
    container = document.createElement("div");
    container.id = containerId;
    container.classList.add("cv-toaster");
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `cv-toast cv-toast--${type}`;
  toast.textContent = message;

  container.appendChild(toast);

  setTimeout(() => {
    toast.remove();
  }, 3000);
}

export function showModal(title, content) {
  const modalBackdrop = document.createElement("div");
  modalBackdrop.className = "cv-modal-backdrop active";
  modalBackdrop.innerHTML = `
    <div class="cv-modal">
      <div class="cv-modal-header">
        <h3>${title}</h3>
        <button id="close-modal">✕</button>
      </div>
      <div class="cv-modal-body">${content}</div>
    </div>
  `;
  document.body.appendChild(modalBackdrop);

  modalBackdrop.querySelector("#close-modal").addEventListener("click", () => {
    modalBackdrop.remove();
  });
}
