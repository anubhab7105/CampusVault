// ===========================
// file.page.js
// Handles file viewing & actions
// ===========================
import { state } from "../state.js";

document.addEventListener("DOMContentLoaded", () => {
  const fileContainer = document.getElementById("file-list");
  if (!fileContainer) return;

  state.uploadedFiles.forEach((f) => {
    const card = document.createElement("div");
    card.className = "cv-library-card";
    card.innerHTML = `
      <div class="cv-card-info">
        <h3>${f.title}</h3>
        <p>Type: ${f.type}</p>
        <p>Uploaded by: ${f.facultyId}</p>
        <a href="#" class="cv-btn cv-btn-sm cv-btn-primary">Download</a>
      </div>
    `;
    fileContainer.appendChild(card);
  });
});
