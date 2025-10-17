// ===========================
// library.page.js
// Handles library filtering & search
// ===========================
import { FILE_TYPES } from "../config.js";

document.addEventListener("DOMContentLoaded", () => {
  const libraryContainer = document.getElementById("library-cards");
  const searchInput = document.getElementById("search-library");
  const filterSelect = document.getElementById("filter-type");

  const resources = [
    { title: "Cybersecurity Basics", type: "PDF" },
    { title: "React JS Guide", type: "PPT" },
    { title: "Python for Beginners", type: "PDF" },
    { title: "Excel Advanced Tips", type: "Excel" },
  ];

  function renderCards(filtered) {
    libraryContainer.innerHTML = "";
    filtered.forEach((r) => {
      const card = document.createElement("div");
      card.className = "cv-library-card";
      card.innerHTML = `
        <div class="cv-card-info">
          <h3>${r.title}</h3>
          <p>Type: ${r.type}</p>
          <a href="#" class="cv-btn cv-btn-sm cv-btn-primary">View</a>
        </div>
      `;
      libraryContainer.appendChild(card);
    });
  }

  renderCards(resources);

  function filterLibrary() {
    const query = searchInput.value.toLowerCase();
    const filter = filterSelect.value;

    let filtered = resources.filter((r) =>
      r.title.toLowerCase().includes(query)
    );

    if (filter !== "all") filtered = filtered.filter((r) => r.type === filter);
    renderCards(filtered);
  }

  searchInput.addEventListener("input", filterLibrary);
  filterSelect.addEventListener("change", filterLibrary);
});
