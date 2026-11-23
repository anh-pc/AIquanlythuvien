import { PAGE_SIZE_DEFAULT } from "../types/index.js";
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
 * View Quản lý Sách phía Quản trị (AC8–AC14 & UX1–UX7)
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
  };

  const booksRaceGuard = createRaceGuard();

  section.innerHTML = `
    <div class="view-header">
      <div>
        <h2 id="books-view-heading" class="view-title">Quản lý Danh mục Sách</h2>
        <p class="view-subtitle">Tra cứu theo tên sách, lọc theo thể loại và quản lý số lượng bản sách trong kho</p>
      </div>
    </div>

    <div class="filter-toolbar" role="search" aria-label="Bộ lọc và tìm kiếm sách">
      <div class="filter-field search-field">
        <label class="filter-label" for="book-search-input">Tên sách</label>
        <div class="search-input-wrapper">
          <span class="search-icon" aria-hidden="true">🔍</span>
          <input
            type="search"
            id="book-search-input"
            class="search-input"
            placeholder="Tìm theo tên sách..."
            aria-label="Tìm theo tên sách"
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

    <div class="table-container" id="books-table-container">
      <table class="admin-table" aria-label="Bảng danh sách sách">
        <thead>
          <tr>
            <th scope="col">Mã</th>
            <th scope="col">Tên sách</th>
            <th scope="col">Tác giả</th>
            <th scope="col">Thể loại</th>
            <th scope="col">ISBN</th>
            <th scope="col">Năm XB</th>
            <th scope="col">Còn / Tổng</th>
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
  const tableContainer = section.querySelector("#books-table-container");
  const tbody = section.querySelector("#books-table-body");
  const emptyStateEl = section.querySelector("#books-empty-state");
  const paginationMount = section.querySelector("#books-pagination-mount");

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

    // Hiển thị lỗi (UX4, UX6)
    if (state.errorMessage) {
      errorBanner.classList.remove("hidden");
      errorBanner.innerHTML = `
        <div class="error-banner-content">
          <span>⚠️ ${state.errorMessage}</span>
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

    // Không hiển thị số kết quả sai hoặc empty state khi đang loading (AC13, UX7)
    if (state.isLoading && !state.hasLoadedOnce) {
      summaryEl.textContent = "Đang tải danh sách sách...";
      emptyStateEl.classList.add("hidden");
      return;
    }

    if (!state.isLoading && !state.errorMessage) {
      summaryEl.textContent = `Tìm thấy ${state.total} sách`;
    }

    // Khi đang tải tiếp mà đã có dữ liệu cũ, giữ dữ liệu cũ trên bảng để tránh nhấp nháy (UX7)
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
          <td class="col-title"><strong>${escapeHtml(book.title)}</strong></td>
          <td>${escapeHtml(book.author)}</td>
          <td><span class="category-badge">${escapeHtml(book.category_name)}</span></td>
          <td class="col-mono">${escapeHtml(book.isbn)}</td>
          <td>${book.published_year || "—"}</td>
          <td>
            <span class="stock-status ${isOut ? "stock-out" : "stock-ok"}">
              ${book.available_copies} / ${book.total_copies} ${isOut ? "(Hết bản sẵn)" : "(Còn sẵn)"}
            </span>
          </td>
          <td>
            <button
              type="button"
              class="btn-danger-outline btn-delete-book"
              data-book-id="${book.id}"
              data-book-title="${escapeHtml(book.title)}"
              aria-label="Xoá sách ${escapeHtml(book.title)}"
            >
              Xoá
            </button>
          </td>
        `;
        const delBtn = tr.querySelector(".btn-delete-book");
        delBtn.addEventListener("click", () => handleDeleteBook(book));
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
    try {
      await apiRequest(`/books/${book.id}`, { method: "DELETE" });
      if (state.items.length === 1 && state.page > 1) {
        state.page -= 1;
      }
      loadBooks();
    } catch {
      state.errorMessage = "Không thể xoá sách. Vui lòng thử lại.";
      renderView();
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

  // UX2: Nhấn Enter trong ô tìm kiếm thì tìm ngay, bỏ qua debounce, chỉ phát sinh đúng 1 request
  searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      state.keyword = searchInput.value;
      debouncedTriggerSearch.flush();
    }
  });

  // AC14 & UX4 & UX7: Xoá bộ lọc phản hồi tức thì, reset keyword, thể loại về Tất cả thể loại, về trang 1
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

  // Khởi tải lần đầu
  loadBooks();

  return section;
}

function escapeHtml(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
