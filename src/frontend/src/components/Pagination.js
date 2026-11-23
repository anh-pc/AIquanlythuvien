/**
 * Component Phân trang dùng chung (AC9, UX5, UX6)
 */
export function renderPagination({ page, totalPages, total, onPageChange }) {
  const nav = document.createElement("nav");
  nav.className = "pagination-bar";
  nav.setAttribute("aria-label", "Phân trang danh sách sách");

  if (total <= 0 || totalPages <= 0) {
    return nav;
  }

  const info = document.createElement("div");
  info.className = "pagination-info";
  info.textContent = `Trang ${page} / ${totalPages}`;

  const controls = document.createElement("div");
  controls.className = "pagination-controls";

  const prevBtn = document.createElement("button");
  prevBtn.type = "button";
  prevBtn.className = "btn-page";
  prevBtn.textContent = "← Trang trước";
  prevBtn.disabled = page <= 1;
  prevBtn.setAttribute("aria-label", "Chuyển tới trang trước");
  prevBtn.addEventListener("click", () => {
    if (page > 1) onPageChange(page - 1);
  });
  controls.appendChild(prevBtn);

  for (let p = 1; p <= totalPages; p += 1) {
    const pageBtn = document.createElement("button");
    pageBtn.type = "button";
    pageBtn.className = `btn-page btn-page-num${p === page ? " active" : ""}`;
    pageBtn.textContent = String(p);
    pageBtn.setAttribute("aria-label", `Trang ${p}`);
    if (p === page) {
      pageBtn.setAttribute("aria-current", "page");
    }
    pageBtn.addEventListener("click", () => {
      if (p !== page) onPageChange(p);
    });
    controls.appendChild(pageBtn);
  }

  const nextBtn = document.createElement("button");
  nextBtn.type = "button";
  nextBtn.className = "btn-page";
  nextBtn.textContent = "Trang sau →";
  nextBtn.disabled = page >= totalPages;
  nextBtn.setAttribute("aria-label", "Chuyển tới trang sau");
  nextBtn.addEventListener("click", () => {
    if (page < totalPages) onPageChange(page + 1);
  });
  controls.appendChild(nextBtn);

  nav.appendChild(info);
  nav.appendChild(controls);
  return nav;
}
