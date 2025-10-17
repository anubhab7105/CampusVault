// ===========================
// paginator.js
// reusable pagination component
// ===========================

export class Paginator {
  constructor(container, totalItems, pageSize = 10, onPageChange = null) {
    this.container = container;
    this.totalItems = totalItems;
    this.pageSize = pageSize;
    this.currentPage = 1;
    this.onPageChange = onPageChange;

    this.render();
  }

  totalPages() {
    return Math.ceil(this.totalItems / this.pageSize);
  }

  goToPage(page) {
    if (page < 1 || page > this.totalPages()) return;
    this.currentPage = page;
    this.render();
    if (this.onPageChange) this.onPageChange(this.currentPage);
  }

  render() {
    this.container.innerHTML = "";

    const total = this.totalPages();

    if (total <= 1) return;

    const createBtn = (text, page) => {
      const btn = document.createElement("button");
      btn.textContent = text;
      btn.className = "cv-btn cv-btn-sm";
      btn.disabled = page === this.currentPage;
      btn.addEventListener("click", () => this.goToPage(page));
      return btn;
    };

    this.container.appendChild(createBtn("Prev", this.currentPage - 1));

    for (let i = 1; i <= total; i++) {
      this.container.appendChild(createBtn(i, i));
    }

    this.container.appendChild(createBtn("Next", this.currentPage + 1));
  }
}
