// ===========================
// fileCard.js
// reusable file card component
// ===========================

export function createFileCard(file) {
  const card = document.createElement("div");
  card.className = "cv-library-card";

  card.innerHTML = `
    <div class="cv-card-info">
      <h3>${file.title}</h3>
      <p>Type: ${file.type}</p>
      ${file.facultyId ? `<p>Uploaded by: ${file.facultyId}</p>` : ""}
      <a href="#" class="cv-btn cv-btn-sm cv-btn-primary">View / Download</a>
    </div>
  `;

  return card;
}
