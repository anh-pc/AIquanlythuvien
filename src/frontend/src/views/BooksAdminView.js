import { COPY_STATUS_LABELS, PAGE_SIZE_DEFAULT, escapeHtml } from "../types/index.js";
import { apiRequest } from "../api/client.js";
import {
  DEBOUNCE_DELAY_MS,
  createDebounce,
  createRaceGuard,
  fetchAdminBooks,
} from "../utils/bookSearchHelper.js";
import { createSearchableCategoryDropdown } from "../components/SearchableCategoryDropdown.js";
import { renderPagination } from "../components/Pagination.js";

/**
 * Màn 2: Quản lý Đầu sách & Bản sao (F1, F2, F7, F11, NV6, NV7, AC8–AC14, UX1–UX7)
 */
export function createBooksAdminView() {
  const section = document.createElement("section");
  section.className = "admin-view books-admin-view";
  section.setAttribute("aria-labelledby", "books-view-heading");

  const state = {
    keyword: "",
    categoryId: null,
    categoryName: "Tất cả thể loại",
    page: 1,
    pageSize: PAGE_SIZE_DEFAULT,
    items: [],
    total: 0,
    totalPages: 0,
    isLoading: true,
    hasLoadedOnce: false,
    errorMessage: "",
    toastMessage: "",
  };

  const booksRaceGuard = createRaceGuard();

  section.innerHTML = `
    <div class="view-header">
      <div>
        <h2 id="books-view-heading" class="view-title">Quản lý Đầu sách & Bản sao</h2>
        <p class="view-subtitle">Tra cứu theo tên sách hoặc tác giả, lọc theo thể loại, thêm/sửa đầu sách và quản lý từng bản sao</p>
      </div>
      <div class="header-actions">
        <button type="button" class="btn-secondary" id="btn-open-add-category">+ Thêm thể loại</button>
        <button type="button" class="btn-primary" id="btn-open-add-book">+ Thêm đầu sách</button>
      </div>
    </div>

    <div id="books-toast-banner" class="toast-banner hidden" role="status" aria-live="polite"></div>

    <div class="filter-toolbar" role="search" aria-label="Bộ lọc và tìm kiếm sách">
      <div class="filter-field search-field">
        <label class="filter-label" for="book-search-input">Tên sách hoặc tác giả</label>
        <div class="search-input-wrapper">
          <span class="search-icon" aria-hidden="true">🔍</span>
          <input
            type="search"
            id="book-search-input"
            class="search-input"
            placeholder="Tìm theo tên sách hoặc tác giả..."
            aria-label="Tìm theo tên sách hoặc tác giả"
            autocomplete="off"
          />
        </div>
      </div>

      <div class="filter-field category-field" id="category-dropdown-mount"></div>

      <div class="filter-actions">
        <button
          type="button"
          id="btn-clear-filters"
          class="btn-secondary btn-clear-filters"
          disabled
          aria-label="Xoá bộ lọc tìm kiếm và thể loại"
        >
          ✕ Xoá bộ lọc
        </button>
      </div>
    </div>

    <div class="status-summary-bar">
      <div
        id="books-result-summary"
        class="result-summary"
        role="status"
        aria-live="polite"
      ></div>
      <div id="active-filter-chips" class="active-filter-chips"></div>
      <div id="loading-indicator" class="loading-badge hidden" aria-hidden="true">
        <span class="spinner-dot"></span> Đang tải...
      </div>
    </div>

    <div id="books-error-banner" class="error-banner hidden" role="alert"></div>

    <!-- Form Thêm / Sửa Đầu sách (dùng lại SearchableCategoryDropdown theo AC10) -->
    <div id="book-form-panel" class="sub-panel hidden" role="region" aria-label="Biểu mẫu thông tin đầu sách">
      <h3 id="book-form-title" class="panel-title">Thêm đầu sách mới</h3>
      <form id="book-form" novalidate>
        <div class="form-grid">
          <div class="form-group">
            <label class="filter-label" for="bf-title">Tên sách *</label>
            <input type="text" id="bf-title" class="search-input input-no-icon" placeholder="Nhập tên đầu sách..." required />
            <span class="field-error hidden" id="err-bf-title"></span>
          </div>
          <div class="form-group">
            <label class="filter-label" for="bf-author">Tác giả *</label>
            <input type="text" id="bf-author" class="search-input input-no-icon" placeholder="Nhập tên tác giả..." required />
            <span class="field-error hidden" id="err-bf-author"></span>
          </div>
          <div class="form-group">
            <div id="bf-category-mount"></div>
            <span class="field-error hidden" id="err-bf-category"></span>
          </div>
          <div class="form-group">
            <label class="filter-label" for="bf-isbn">Mã ISBN</label>
            <input type="text" id="bf-isbn" class="search-input input-no-icon" placeholder="Ví dụ: 978-604-..." />
          </div>
          <div class="form-group">
            <label class="filter-label" for="bf-publisher">Nhà xuất bản</label>
            <input type="text" id="bf-publisher" class="search-input input-no-icon" placeholder="Ví dụ: NXB Khoa học và Kỹ thuật" />
          </div>
          <div class="form-group">
            <label class="filter-label" for="bf-year">Năm xuất bản</label>
            <input type="number" id="bf-year" class="search-input input-no-icon" placeholder="2025" min="1900" max="2100" />
          </div>
          <div class="form-group" id="bf-copies-group">
            <label class="filter-label" for="bf-initial-copies">Số bản sao ban đầu</label>
            <input type="number" id="bf-initial-copies" class="search-input input-no-icon" value="2" min="1" max="20" />
          </div>
        </div>
        <div id="book-form-api-error" class="field-error hidden" role="alert"></div>
        <div class="form-actions">
          <button type="submit" class="btn-primary" id="btn-save-book">Lưu đầu sách</button>
          <button type="button" class="btn-secondary" id="btn-cancel-book">Huỷ</button>
        </div>
      </form>
    </div>

    <!-- Form Thêm Thể loại nhanh (F11) -->
    <div id="category-form-panel" class="sub-panel hidden" role="region" aria-label="Thêm thể loại mới">
      <h3 class="panel-title">Thêm thể loại sách mới</h3>
      <form id="category-form" novalidate>
        <div class="form-grid">
          <div class="form-group">
            <label class="filter-label" for="cf-name">Tên thể loại *</label>
            <input type="text" id="cf-name" class="search-input input-no-icon" placeholder="Ví dụ: Kiến trúc & Xây dựng" required />
          </div>
          <div class="form-group">
            <label class="filter-label" for="cf-desc">Mô tả</label>
            <input type="text" id="cf-desc" class="search-input input-no-icon" placeholder="Mô tả ngắn gọn về thể loại..." />
          </div>
        </div>
        <div id="category-form-error" class="field-error hidden" role="alert"></div>
        <div class="form-actions">
          <button type="submit" class="btn-primary">Lưu thể loại</button>
          <button type="button" class="btn-secondary" id="btn-cancel-category">Đóng</button>
        </div>
      </form>
    </div>

    <!-- Panel Quản lý Bản sao của một Đầu sách (F2, NV6) -->
    <div id="copies-panel" class="sub-panel hidden" role="region" aria-label="Quản lý bản sao sách"></div>

    <div class="table-container" id="books-table-container">
      <table class="admin-table" aria-label="Bảng danh sách sách">
        <thead>
          <tr>
            <th scope="col">Mã</th>
            <th scope="col">Tên sách</th>
            <th scope="col">Tác giả</th>
            <th scope="col">Thể loại</th>
            <th scope="col">Năm XB</th>
            <th scope="col">Tình trạng bản sao</th>
            <th scope="col">Thao tác</th>
          </tr>
        </thead>
        <tbody id="books-table-body"></tbody>
      </table>
      <div id="books-empty-state" class="empty-state hidden" role="status" aria-live="polite"></div>
    </div>

    <div id="books-pagination-mount"></div>
  `;

  const searchInput = section.querySelector("#book-search-input");
  const clearBtn = section.querySelector("#btn-clear-filters");
  const categoryMount = section.querySelector("#category-dropdown-mount");
  const summaryEl = section.querySelector("#books-result-summary");
  const chipsEl = section.querySelector("#active-filter-chips");
  const loadingBadge = section.querySelector("#loading-indicator");
  const errorBanner = section.querySelector("#books-error-banner");
  const toastBanner = section.querySelector("#books-toast-banner");
  const tableContainer = section.querySelector("#books-table-container");
  const tbody = section.querySelector("#books-table-body");
  const emptyStateEl = section.querySelector("#books-empty-state");
  const paginationMount = section.querySelector("#books-pagination-mount");

  const bookFormPanel = section.querySelector("#book-form-panel");
  const bookForm = section.querySelector("#book-form");
  const bookFormTitle = section.querySelector("#book-form-title");
  const bfCategoryMount = section.querySelector("#bf-category-mount");
  const categoryFormPanel = section.querySelector("#category-form-panel");
  const categoryForm = section.querySelector("#category-form");
  const copiesPanel = section.querySelector("#copies-panel");

  let editingBookId = null;

  function showToast(msg) {
    toastBanner.textContent = `✓ ${msg}`;
    toastBanner.classList.remove("hidden");
    setTimeout(() => toastBanner.classList.add("hidden"), 4000);
  }

  function hasActiveFilter() {
    return state.keyword.trim().length > 0 || state.categoryId !== null;
  }

  function updateClearButtonAndChips() {
    const active = hasActiveFilter();
    clearBtn.disabled = !active;

    chipsEl.innerHTML = "";
    const trimmedKw = state.keyword.trim();
    if (trimmedKw.length > 0) {
      const chip = document.createElement("span");
      chip.className = "filter-chip";
      chip.textContent = `Từ khoá: "${trimmedKw}"`;
      chipsEl.appendChild(chip);
    }
    if (state.categoryId !== null) {
      const chip = document.createElement("span");
      chip.className = "filter-chip";
      chip.textContent = `Thể loại: ${state.categoryName}`;
      chipsEl.appendChild(chip);
    }
  }

  function renderView() {
    updateClearButtonAndChips();

    loadingBadge.classList.toggle("hidden", !state.isLoading);
    tableContainer.classList.toggle("is-loading", state.isLoading);

    if (state.errorMessage) {
      errorBanner.classList.remove("hidden");
      errorBanner.innerHTML = `
        <div class="error-banner-content">
          <span>⚠️ ${escapeHtml(state.errorMessage)}</span>
          <button type="button" class="btn-retry" id="btn-retry-books">Thử lại</button>
        </div>
      `;
      errorBanner.querySelector("#btn-retry-books").addEventListener("click", () => {
        loadBooks();
      });
    } else {
      errorBanner.classList.add("hidden");
      errorBanner.innerHTML = "";
    }

    if (state.isLoading && !state.hasLoadedOnce) {
      summaryEl.textContent = "Đang tải danh sách sách...";
      emptyStateEl.classList.add("hidden");
      return;
    }

    if (!state.isLoading && !state.errorMessage) {
      summaryEl.textContent = `Tìm thấy ${state.total} sách`;
    }

    if (state.isLoading && state.hasLoadedOnce) {
      return;
    }

    tbody.innerHTML = "";

    if (!state.errorMessage && state.items.length === 0) {
      emptyStateEl.classList.remove("hidden");
      emptyStateEl.innerHTML = `
        <div class="empty-state-box">
          <p class="empty-state-title">Không tìm thấy sách phù hợp</p>
          <p class="empty-state-hint">
            ${
              hasActiveFilter()
                ? 'Hãy thử kiểm tra lại từ khoá, chọn thể loại khác hoặc nhấn nút "Xoá bộ lọc" để xem toàn bộ sách.'
                : "Hiện chưa có sách nào trong thư viện."
            }
          </p>
        </div>
      `;
    } else {
      emptyStateEl.classList.add("hidden");
      emptyStateEl.innerHTML = "";

      for (const book of state.items) {
        const tr = document.createElement("tr");
        const isOut = book.available_copies <= 0;
        tr.innerHTML = `
          <td class="col-id">#${book.id}</td>
          <td class="col-title">
            <strong>${escapeHtml(book.title)}</strong>
            ${book.isbn ? `<div class="sub-meta">ISBN: ${escapeHtml(book.isbn)}</div>` : ""}
          </td>
          <td>${escapeHtml(book.author)}</td>
          <td><span class="category-badge">${escapeHtml(book.category_name)}</span></td>
          <td>${book.published_year || "—"}</td>
          <td>
            <div class="copy-summary-badges">
              <span class="status-badge ${isOut ? "badge-lost" : "badge-available"}">
                Còn trong kho: ${book.available_copies}/${book.total_copies}
              </span>
              ${
                book.borrowed_copies > 0
                  ? `<span class="status-badge badge-borrowed">Đang mượn: ${book.borrowed_copies}</span>`
                  : ""
              }
              ${
                book.damaged_copies > 0
                  ? `<span class="status-badge badge-damaged">Hư hỏng: ${book.damaged_copies}</span>`
                  : ""
              }
              ${
                book.lost_copies > 0
                  ? `<span class="status-badge badge-lost">Thất lạc: ${book.lost_copies}</span>`
                  : ""
              }
            </div>
          </td>
          <td>
            <div class="row-actions">
              <button type="button" class="btn-action btn-copies" aria-label="Quản lý bản sao của ${escapeHtml(book.title)}">
                Bản sao (${book.total_copies})
              </button>
              <button type="button" class="btn-action btn-edit-book" aria-label="Sửa sách ${escapeHtml(book.title)}">
                Sửa
              </button>
              <button type="button" class="btn-danger-outline btn-delete-book" aria-label="Xoá sách ${escapeHtml(book.title)}">
                Xoá
              </button>
            </div>
          </td>
        `;
        tr.querySelector(".btn-copies").addEventListener("click", () => openCopiesPanel(book));
        tr.querySelector(".btn-edit-book").addEventListener("click", () => openBookForm(book));
        tr.querySelector(".btn-delete-book").addEventListener("click", () => handleDeleteBook(book));
        tbody.appendChild(tr);
      }
    }

    paginationMount.innerHTML = "";
    if (!state.errorMessage && state.totalPages > 0) {
      const paginationEl = renderPagination({
        page: state.page,
        totalPages: state.totalPages,
        total: state.total,
        onPageChange(newPage) {
          state.page = newPage;
          loadBooks();
        },
      });
      paginationMount.appendChild(paginationEl);
    }
  }

  async function handleDeleteBook(book) {
    const confirmed = window.confirm(
      `Bạn có chắc chắn muốn xoá mềm đầu sách "${book.title}" không?`
    );
    if (!confirmed) return;

    try {
      await apiRequest(`/books/${book.id}`, { method: "DELETE" });
      showToast(`Đã xoá mềm đầu sách "${book.title}".`);
      if (state.items.length === 1 && state.page > 1) {
        state.page -= 1;
      }
      loadBooks();
    } catch (err) {
      state.errorMessage = err.message || "Không thể xoá đầu sách.";
      renderView();
    }
  }

  // --- Form Thêm / Sửa Đầu sách (tái sử dụng SearchableCategoryDropdown theo AC10) ---
  const formCategoryDropdown = createSearchableCategoryDropdown({
    allowAll: false,
    labelText: "Thể loại *",
    idPrefix: "book-form-category",
    onSelect() {
      section.querySelector("#err-bf-category").classList.add("hidden");
    },
  });
  bfCategoryMount.appendChild(formCategoryDropdown.element);

  function openBookForm(book = null) {
    copiesPanel.classList.add("hidden");
    categoryFormPanel.classList.add("hidden");
    bookFormPanel.classList.remove("hidden");

    section.querySelectorAll("#book-form .field-error").forEach((el) => el.classList.add("hidden"));
    const copiesGroup = section.querySelector("#bf-copies-group");

    if (book) {
      editingBookId = book.id;
      bookFormTitle.textContent = `Cập nhật đầu sách #${book.id}`;
      section.querySelector("#bf-title").value = book.title || "";
      section.querySelector("#bf-author").value = book.author || "";
      section.querySelector("#bf-isbn").value = book.isbn || "";
      section.querySelector("#bf-publisher").value = book.publisher || "";
      section.querySelector("#bf-year").value = book.published_year || "";
      formCategoryDropdown.setSelectedCategory({
        id: book.category_id,
        name: book.category_name,
      });
      copiesGroup.classList.add("hidden");
    } else {
      editingBookId = null;
      bookFormTitle.textContent = "Thêm đầu sách mới";
      bookForm.reset();
      formCategoryDropdown.resetToDefault();
      copiesGroup.classList.remove("hidden");
    }
    section.querySelector("#bf-title").focus();
  }

  section.querySelector("#btn-open-add-book").addEventListener("click", () => openBookForm(null));
  section.querySelector("#btn-cancel-book").addEventListener("click", () => {
    bookFormPanel.classList.add("hidden");
  });

  bookForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const titleVal = section.querySelector("#bf-title").value.trim();
    const authorVal = section.querySelector("#bf-author").value.trim();
    const selectedCat = formCategoryDropdown.getSelectedCategory();
    const isbnVal = section.querySelector("#bf-isbn").value.trim();
    const pubVal = section.querySelector("#bf-publisher").value.trim();
    const yearRaw = section.querySelector("#bf-year").value.trim();
    const initialCopies = Number(section.querySelector("#bf-initial-copies").value || 1);

    const errTitle = section.querySelector("#err-bf-title");
    const errAuthor = section.querySelector("#err-bf-author");
    const errCat = section.querySelector("#err-bf-category");
    const errApi = section.querySelector("#book-form-api-error");
    [errTitle, errAuthor, errCat, errApi].forEach((el) => el.classList.add("hidden"));

    let hasErr = false;
    if (!titleVal) {
      errTitle.textContent = "Vui lòng nhập tên đầu sách.";
      errTitle.classList.remove("hidden");
      hasErr = true;
    }
    if (!authorVal) {
      errAuthor.textContent = "Vui lòng nhập tên tác giả.";
      errAuthor.classList.remove("hidden");
      hasErr = true;
    }
    if (!selectedCat || selectedCat.id === null) {
      errCat.textContent = "Vui lòng chọn thể loại cho đầu sách.";
      errCat.classList.remove("hidden");
      hasErr = true;
    }
    if (hasErr) return;

    const payload = {
      title: titleVal,
      author: authorVal,
      category_id: selectedCat.id,
      isbn: isbnVal || null,
      publisher: pubVal || null,
      published_year: yearRaw ? Number(yearRaw) : null,
    };

    try {
      if (editingBookId) {
        await apiRequest(`/books/${editingBookId}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
        showToast(`Đã cập nhật đầu sách "${titleVal}".`);
      } else {
        payload.initial_copies = initialCopies;
        await apiRequest("/books", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        showToast(`Đã thêm đầu sách "${titleVal}" kèm ${initialCopies} bản sao.`);
      }
      bookFormPanel.classList.add("hidden");
      loadBooks();
    } catch (err) {
      errApi.textContent = err.message || "Không thể lưu đầu sách.";
      errApi.classList.remove("hidden");
    }
  });

  // --- Form Thêm Thể loại (F11) ---
  section.querySelector("#btn-open-add-category").addEventListener("click", () => {
    bookFormPanel.classList.add("hidden");
    copiesPanel.classList.add("hidden");
    categoryFormPanel.classList.remove("hidden");
    categoryForm.reset();
    section.querySelector("#category-form-error").classList.add("hidden");
    section.querySelector("#cf-name").focus();
  });

  section.querySelector("#btn-cancel-category").addEventListener("click", () => {
    categoryFormPanel.classList.add("hidden");
  });

  categoryForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const nameVal = section.querySelector("#cf-name").value.trim();
    const descVal = section.querySelector("#cf-desc").value.trim();
    const errEl = section.querySelector("#category-form-error");
    errEl.classList.add("hidden");

    if (!nameVal) {
      errEl.textContent = "Vui lòng nhập tên thể loại.";
      errEl.classList.remove("hidden");
      return;
    }

    try {
      await apiRequest("/categories", {
        method: "POST",
        body: JSON.stringify({ name: nameVal, description: descVal || null }),
      });
      categoryFormPanel.classList.add("hidden");
      showToast(`Đã thêm thể loại "${nameVal}".`);
    } catch (err) {
      errEl.textContent = err.message;
      errEl.classList.remove("hidden");
    }
  });

  // --- Panel Quản lý Bản sao (F2, NV6) ---
  async function openCopiesPanel(book) {
    bookFormPanel.classList.add("hidden");
    categoryFormPanel.classList.add("hidden");
    copiesPanel.classList.remove("hidden");
    copiesPanel.innerHTML = `<p class="result-summary">Đang tải danh sách bản sao của "${escapeHtml(book.title)}"...</p>`;

    try {
      const data = await apiRequest(`/books/${book.id}/copies`);
      const copies = data.items || [];
      const suggestedBarcode = `BS-${String(book.id).padStart(3, "0")}-${String(copies.length + 1).padStart(2, "0")}`;

      copiesPanel.innerHTML = `
        <div class="sub-panel-header">
          <div>
            <h3 class="panel-title">Bản sao của sách: ${escapeHtml(book.title)}</h3>
            <p class="view-subtitle">Lưu ý (NV6): Không đổi thủ công sang/ra khỏi trạng thái "Đang mượn". Chỉ đổi giữa Còn trong kho / Hư hỏng / Thất lạc.</p>
          </div>
          <button type="button" class="btn-secondary" id="btn-close-copies">Đóng</button>
        </div>

        <form id="add-copy-form" class="inline-form">
          <label class="filter-label" for="new-copy-barcode">Mã bản sao mới</label>
          <input type="text" id="new-copy-barcode" class="search-input input-no-icon" value="${escapeHtml(suggestedBarcode)}" required />
          <label class="filter-label" for="new-copy-note">Ghi chú</label>
          <input type="text" id="new-copy-note" class="search-input input-no-icon" placeholder="Tình trạng bìa, kệ sách..." />
          <button type="submit" class="btn-primary">+ Thêm bản sao</button>
        </form>
        <div id="copies-panel-error" class="field-error hidden" role="alert"></div>

        <table class="admin-table" aria-label="Bảng bản sao của đầu sách">
          <thead>
            <tr>
              <th>Mã bản sao (Barcode)</th>
              <th>Tình trạng hiện tại</th>
              <th>Ghi chú</th>
              <th>Đổi tình trạng (NV6)</th>
            </tr>
          </thead>
          <tbody id="copies-tbody"></tbody>
        </table>
      `;

      copiesPanel.querySelector("#btn-close-copies").addEventListener("click", () => {
        copiesPanel.classList.add("hidden");
      });

      const copiesErr = copiesPanel.querySelector("#copies-panel-error");
      const copiesTbody = copiesPanel.querySelector("#copies-tbody");

      for (const c of copies) {
        const tr = document.createElement("tr");
        const isBorrowed = c.status === "borrowed";
        tr.innerHTML = `
          <td class="col-mono"><strong>${escapeHtml(c.barcode)}</strong></td>
          <td>
            <span class="status-badge badge-${c.status}">
              ${escapeHtml(COPY_STATUS_LABELS[c.status] || c.status)}
            </span>
          </td>
          <td>${escapeHtml(c.note || "—")}</td>
          <td>
            ${
              isBorrowed
                ? `<span class="sub-meta">Đang cho mượn (Trả sách ở màn Mượn/Trả)</span>`
                : `
                <div class="row-actions">
                  ${
                    c.status !== "available"
                      ? `<button type="button" class="btn-action" data-status="available">Chuyển: Còn trong kho</button>`
                      : ""
                  }
                  ${
                    c.status !== "damaged"
                      ? `<button type="button" class="btn-action" data-status="damaged">Đánh dấu: Hư hỏng</button>`
                      : ""
                  }
                  ${
                    c.status !== "lost"
                      ? `<button type="button" class="btn-danger-outline" data-status="lost">Đánh dấu: Thất lạc</button>`
                      : ""
                  }
                </div>
              `
            }
          </td>
        `;
        tr.querySelectorAll("button[data-status]").forEach((btn) => {
          btn.addEventListener("click", async () => {
            const newSt = btn.dataset.status;
            const stLabel = COPY_STATUS_LABELS[newSt];
            if (newSt === "damaged" || newSt === "lost") {
              const ok = window.confirm(
                `Xác nhận chuyển bản sao "${c.barcode}" sang tình trạng "${stLabel}"?`
              );
              if (!ok) return;
            }
            try {
              await apiRequest(`/copies/${c.id}`, {
                method: "PATCH",
                body: JSON.stringify({ status: newSt }),
              });
              showToast(`Đã cập nhật bản sao ${c.barcode} -> ${stLabel}.`);
              openCopiesPanel(book);
              loadBooks();
            } catch (err) {
              copiesErr.textContent = err.message;
              copiesErr.classList.remove("hidden");
            }
          });
        });
        copiesTbody.appendChild(tr);
      }

      copiesPanel.querySelector("#add-copy-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        copiesErr.classList.add("hidden");
        const bc = copiesPanel.querySelector("#new-copy-barcode").value.trim();
        const note = copiesPanel.querySelector("#new-copy-note").value.trim();
        try {
          await apiRequest(`/books/${book.id}/copies`, {
            method: "POST",
            body: JSON.stringify({ barcode: bc, status: "available", note: note || null }),
          });
          showToast(`Đã thêm bản sao ${bc}.`);
          openCopiesPanel(book);
          loadBooks();
        } catch (err) {
          copiesErr.textContent = err.message;
          copiesErr.classList.remove("hidden");
        }
      });
    } catch (err) {
      copiesPanel.innerHTML = `<p class="field-error">Không tải được bản sao: ${escapeHtml(err.message)}</p>`;
    }
  }

  async function loadBooks() {
    const { token, signal } = booksRaceGuard.next();
    state.isLoading = true;
    state.errorMessage = "";
    renderView();

    try {
      const data = await fetchAdminBooks(
        {
          keyword: state.keyword,
          categoryId: state.categoryId,
          page: state.page,
          pageSize: state.pageSize,
        },
        signal
      );
      if (!booksRaceGuard.isLatest(token)) return;

      state.items = Array.isArray(data.items) ? data.items : [];
      state.total = typeof data.total === "number" ? data.total : 0;
      state.page = typeof data.page === "number" ? data.page : state.page;
      state.totalPages = typeof data.total_pages === "number" ? data.total_pages : 0;
      state.isLoading = false;
      state.hasLoadedOnce = true;
      renderView();
    } catch (err) {
      if (err && err.name === "AbortError") return;
      if (!booksRaceGuard.isLatest(token)) return;

      state.isLoading = false;
      state.hasLoadedOnce = true;
      state.errorMessage = "Không tải được danh sách sách";
      renderView();
    }
  }

  const debouncedTriggerSearch = createDebounce(() => {
    state.page = 1;
    loadBooks();
  }, DEBOUNCE_DELAY_MS);

  const categoryDropdown = createSearchableCategoryDropdown({
    onSelect(selected) {
      debouncedTriggerSearch.cancel();
      state.categoryId = selected.id;
      state.categoryName = selected.name;
      state.page = 1;
      loadBooks();
    },
  });
  categoryMount.appendChild(categoryDropdown.element);

  searchInput.addEventListener("input", (e) => {
    state.keyword = e.target.value;
    updateClearButtonAndChips();
    debouncedTriggerSearch();
  });

  searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      state.keyword = searchInput.value;
      debouncedTriggerSearch.flush();
    }
  });

  clearBtn.addEventListener("click", () => {
    if (!hasActiveFilter()) return;
    debouncedTriggerSearch.cancel();
    state.keyword = "";
    state.categoryId = null;
    state.categoryName = "Tất cả thể loại";
    state.page = 1;
    searchInput.value = "";
    categoryDropdown.resetToDefault();
    loadBooks();
  });

  loadBooks();
  return section;
}
