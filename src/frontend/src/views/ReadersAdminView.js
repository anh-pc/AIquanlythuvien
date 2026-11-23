import { apiRequest } from "../api/client.js";
import {
  LOAN_STATUS_LABELS,
  PAGE_SIZE_DEFAULT,
  escapeHtml,
  formatCurrencyVN,
  formatDateVN,
} from "../types/index.js";
import { DEBOUNCE_DELAY_MS, createDebounce, createRaceGuard } from "../utils/bookSearchHelper.js";
import { renderPagination } from "../components/Pagination.js";

/**
 * Màn 3: Quản lý Độc giả & Lịch sử Mượn của Độc giả (F3, F8, NV7, NV8, UX1–UX7)
 */
export function createReadersAdminView() {
  const section = document.createElement("section");
  section.className = "admin-view readers-admin-view";
  section.setAttribute("aria-labelledby", "readers-heading");

  const state = {
    q: "",
    isActiveFilter: "",
    page: 1,
    pageSize: PAGE_SIZE_DEFAULT,
    items: [],
    total: 0,
    totalPages: 0,
    isLoading: true,
    errorMessage: "",
  };

  const raceGuard = createRaceGuard();
  let editingReaderId = null;

  section.innerHTML = `
    <div class="view-header">
      <div>
        <h2 id="readers-heading" class="view-title">Quản lý Độc giả & Lịch sử Mượn</h2>
        <p class="view-subtitle">Tra cứu thẻ độc giả, thêm/sửa thông tin, khoá/mở thẻ và xem lịch sử mượn chi tiết</p>
      </div>
      <div class="header-actions">
        <button type="button" class="btn-primary" id="btn-open-add-reader">+ Thêm độc giả</button>
      </div>
    </div>

    <div id="readers-toast" class="toast-banner hidden" role="status" aria-live="polite"></div>

    <div class="filter-toolbar" role="search" aria-label="Tìm kiếm và lọc độc giả">
      <div class="filter-field search-field">
        <label class="filter-label" for="reader-search-input">Tìm độc giả</label>
        <div class="search-input-wrapper">
          <span class="search-icon" aria-hidden="true">🔍</span>
          <input
            type="search"
            id="reader-search-input"
            class="search-input"
            placeholder="Tìm theo họ tên, mã thẻ (DG001), SĐT, email..."
            aria-label="Tìm độc giả theo họ tên hoặc mã thẻ"
            autocomplete="off"
          />
        </div>
      </div>

      <div class="filter-field">
        <label class="filter-label" for="reader-status-filter">Trạng thái thẻ</label>
        <select id="reader-status-filter" class="select-input" aria-label="Lọc trạng thái thẻ độc giả">
          <option value="">Tất cả trạng thái</option>
          <option value="true">Đang hoạt động</option>
          <option value="false">Đã vô hiệu hoá</option>
        </select>
      </div>

      <div class="filter-actions">
        <button type="button" id="btn-clear-reader-filters" class="btn-secondary" disabled>
          ✕ Xoá bộ lọc
        </button>
      </div>
    </div>

    <div class="status-summary-bar">
      <div id="readers-summary" class="result-summary" role="status" aria-live="polite"></div>
    </div>

    <div id="readers-error" class="error-banner hidden" role="alert"></div>

    <!-- Form Thêm / Sửa Độc giả -->
    <div id="reader-form-panel" class="sub-panel hidden" role="region" aria-label="Biểu mẫu độc giả">
      <h3 id="reader-form-title" class="panel-title">Thêm độc giả mới</h3>
      <form id="reader-form" novalidate>
        <div class="form-grid">
          <div class="form-group">
            <label class="filter-label" for="rf-name">Họ và tên *</label>
            <input type="text" id="rf-name" class="search-input input-no-icon" placeholder="Nhập họ tên độc giả..." required />
            <span class="field-error hidden" id="err-rf-name"></span>
          </div>
          <div class="form-group">
            <label class="filter-label" for="rf-card">Mã thẻ (để trống sẽ tự cấp)</label>
            <input type="text" id="rf-card" class="search-input input-no-icon" placeholder="Ví dụ: DG015" />
          </div>
          <div class="form-group">
            <label class="filter-label" for="rf-phone">Số điện thoại</label>
            <input type="text" id="rf-phone" class="search-input input-no-icon" placeholder="0912..." />
          </div>
          <div class="form-group">
            <label class="filter-label" for="rf-email">Email</label>
            <input type="email" id="rf-email" class="search-input input-no-icon" placeholder="sinhvien@student.edu.vn" />
          </div>
          <div class="form-group">
            <label class="filter-label" for="rf-address">Địa chỉ</label>
            <input type="text" id="rf-address" class="search-input input-no-icon" placeholder="Quận/Huyện, Tỉnh/Thành phố..." />
          </div>
        </div>
        <div id="reader-form-api-error" class="field-error hidden" role="alert"></div>
        <div class="form-actions">
          <button type="submit" class="btn-primary">Lưu độc giả</button>
          <button type="button" class="btn-secondary" id="btn-cancel-reader">Huỷ</button>
        </div>
      </form>
    </div>

    <!-- Panel Lịch sử mượn của một Độc giả (NV8) -->
    <div id="reader-history-panel" class="sub-panel hidden" role="region" aria-label="Lịch sử mượn sách của độc giả"></div>

    <div class="table-container">
      <table class="admin-table" aria-label="Bảng danh sách độc giả">
        <thead>
          <tr>
            <th>Mã thẻ</th>
            <th>Họ và tên</th>
            <th>Liên hệ</th>
            <th>Địa chỉ</th>
            <th>Đang mượn / Quá hạn</th>
            <th>Trạng thái thẻ</th>
            <th>Thao tác</th>
          </tr>
        </thead>
        <tbody id="readers-tbody"></tbody>
      </table>
    </div>

    <div id="readers-pagination"></div>
  `;

  const searchInput = section.querySelector("#reader-search-input");
  const statusSelect = section.querySelector("#reader-status-filter");
  const clearBtn = section.querySelector("#btn-clear-reader-filters");
  const summaryEl = section.querySelector("#readers-summary");
  const errorBanner = section.querySelector("#readers-error");
  const toastEl = section.querySelector("#readers-toast");
  const tbody = section.querySelector("#readers-tbody");
  const paginationMount = section.querySelector("#readers-pagination");
  const formPanel = section.querySelector("#reader-form-panel");
  const readerForm = section.querySelector("#reader-form");
  const historyPanel = section.querySelector("#reader-history-panel");

  function showToast(msg) {
    toastEl.textContent = `✓ ${msg}`;
    toastEl.classList.remove("hidden");
    setTimeout(() => toastEl.classList.add("hidden"), 4000);
  }

  function hasFilter() {
    return state.q.trim().length > 0 || state.isActiveFilter !== "";
  }

  async function loadReaders() {
    const { token, signal } = raceGuard.next();
    state.isLoading = true;
    state.errorMessage = "";
    clearBtn.disabled = !hasFilter();

    const params = new URLSearchParams();
    if (state.q.trim()) params.set("q", state.q.trim());
    if (state.isActiveFilter !== "") params.set("is_active", state.isActiveFilter);
    params.set("page", String(state.page));
    params.set("page_size", String(state.pageSize));

    try {
      const data = await apiRequest(`/readers?${params.toString()}`, { signal });
      if (!raceGuard.isLatest(token)) return;
      state.items = data.items || [];
      state.total = data.total || 0;
      state.totalPages = data.total_pages || 0;
      state.isLoading = false;
      renderTable();
    } catch (err) {
      if (err && err.name === "AbortError") return;
      if (!raceGuard.isLatest(token)) return;
      state.isLoading = false;
      state.errorMessage = err.message || "Không tải được danh sách độc giả.";
      renderTable();
    }
  }

  function renderTable() {
    clearBtn.disabled = !hasFilter();
    if (state.errorMessage) {
      errorBanner.classList.remove("hidden");
      errorBanner.innerHTML = `
        <div class="error-banner-content">
          <span>⚠️ ${escapeHtml(state.errorMessage)}</span>
          <button type="button" class="btn-retry" id="btn-retry-readers">Thử lại</button>
        </div>
      `;
      errorBanner.querySelector("#btn-retry-readers").addEventListener("click", loadReaders);
    } else {
      errorBanner.classList.add("hidden");
    }

    summaryEl.textContent = `Tìm thấy ${state.total} độc giả`;
    tbody.innerHTML = "";

    if (state.items.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" class="empty-cell">Không tìm thấy độc giả phù hợp.</td>
        </tr>
      `;
    } else {
      for (const r of state.items) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td class="col-mono"><strong>${escapeHtml(r.card_no)}</strong></td>
          <td><strong>${escapeHtml(r.full_name)}</strong></td>
          <td>
            <div>${escapeHtml(r.phone || "—")}</div>
            <div class="sub-meta">${escapeHtml(r.email || "")}</div>
          </td>
          <td>${escapeHtml(r.address || "—")}</td>
          <td>
            <span class="status-badge badge-borrowed">Đang mượn: ${r.active_loans_count}</span>
            ${
              r.overdue_loans_count > 0
                ? `<span class="status-badge badge-lost">Quá hạn: ${r.overdue_loans_count}</span>`
                : ""
            }
          </td>
          <td>
            <span class="status-badge ${r.is_active ? "badge-available" : "badge-lost"}">
              ${r.is_active ? "● Đang hoạt động" : "✕ Đã vô hiệu hoá"}
            </span>
          </td>
          <td>
            <div class="row-actions">
              <button type="button" class="btn-action btn-history">Lịch sử mượn</button>
              <button type="button" class="btn-action btn-edit-reader">Sửa</button>
              <button type="button" class="${r.is_active ? "btn-danger-outline" : "btn-action"} btn-toggle-status">
                ${r.is_active ? "Vô hiệu hoá" : "Kích hoạt lại"}
              </button>
            </div>
          </td>
        `;
        tr.querySelector(".btn-history").addEventListener("click", () => openReaderHistory(r));
        tr.querySelector(".btn-edit-reader").addEventListener("click", () => openReaderForm(r));
        tr.querySelector(".btn-toggle-status").addEventListener("click", () => toggleReaderStatus(r));
        tbody.appendChild(tr);
      }
    }

    paginationMount.innerHTML = "";
    if (state.totalPages > 0) {
      paginationMount.appendChild(
        renderPagination({
          page: state.page,
          totalPages: state.totalPages,
          total: state.total,
          onPageChange(p) {
            state.page = p;
            loadReaders();
          },
        })
      );
    }
  }

  async function toggleReaderStatus(reader) {
    const targetActive = !reader.is_active;
    if (!targetActive) {
      const ok = window.confirm(
        `Bạn có chắc chắn muốn vô hiệu hoá thẻ độc giả "${reader.full_name} (${reader.card_no})" không?`
      );
      if (!ok) return;
    }
    try {
      await apiRequest(`/readers/${reader.id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: targetActive }),
      });
      showToast(
        `Đã ${targetActive ? "kích hoạt lại" : "vô hiệu hoá"} độc giả ${reader.full_name}.`
      );
      loadReaders();
    } catch (err) {
      state.errorMessage = err.message;
      renderTable();
    }
  }

  function openReaderForm(reader = null) {
    historyPanel.classList.add("hidden");
    formPanel.classList.remove("hidden");
    section.querySelector("#err-rf-name").classList.add("hidden");
    section.querySelector("#reader-form-api-error").classList.add("hidden");

    if (reader) {
      editingReaderId = reader.id;
      section.querySelector("#reader-form-title").textContent = `Cập nhật độc giả ${reader.card_no}`;
      section.querySelector("#rf-name").value = reader.full_name || "";
      section.querySelector("#rf-card").value = reader.card_no || "";
      section.querySelector("#rf-phone").value = reader.phone || "";
      section.querySelector("#rf-email").value = reader.email || "";
      section.querySelector("#rf-address").value = reader.address || "";
    } else {
      editingReaderId = null;
      section.querySelector("#reader-form-title").textContent = "Thêm độc giả mới";
      readerForm.reset();
    }
    section.querySelector("#rf-name").focus();
  }

  section.querySelector("#btn-open-add-reader").addEventListener("click", () => openReaderForm(null));
  section.querySelector("#btn-cancel-reader").addEventListener("click", () => {
    formPanel.classList.add("hidden");
  });

  readerForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const nameVal = section.querySelector("#rf-name").value.trim();
    const cardVal = section.querySelector("#rf-card").value.trim();
    const phoneVal = section.querySelector("#rf-phone").value.trim();
    const emailVal = section.querySelector("#rf-email").value.trim();
    const addrVal = section.querySelector("#rf-address").value.trim();

    const errName = section.querySelector("#err-rf-name");
    const errApi = section.querySelector("#reader-form-api-error");
    errName.classList.add("hidden");
    errApi.classList.add("hidden");

    if (!nameVal) {
      errName.textContent = "Vui lòng nhập họ tên độc giả.";
      errName.classList.remove("hidden");
      return;
    }

    const payload = {
      full_name: nameVal,
      card_no: cardVal || null,
      phone: phoneVal || null,
      email: emailVal || null,
      address: addrVal || null,
    };

    try {
      if (editingReaderId) {
        await apiRequest(`/readers/${editingReaderId}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
        showToast(`Đã cập nhật thông tin độc giả "${nameVal}".`);
      } else {
        await apiRequest("/readers", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        showToast(`Đã thêm độc giả mới "${nameVal}".`);
      }
      formPanel.classList.add("hidden");
      loadReaders();
    } catch (err) {
      errApi.textContent = err.message;
      errApi.classList.remove("hidden");
    }
  });

  // --- Panel Lịch sử mượn của Độc giả (NV8) ---
  function openReaderHistory(reader) {
    formPanel.classList.add("hidden");
    historyPanel.classList.remove("hidden");

    let histStatus = "";
    let histPage = 1;

    async function renderHistory() {
      const qs = new URLSearchParams({
        page: String(histPage),
        page_size: "5",
      });
      if (histStatus) qs.set("status", histStatus);

      try {
        const data = await apiRequest(`/readers/${reader.id}/loans?${qs.toString()}`);
        const loans = data.items || [];

        historyPanel.innerHTML = `
          <div class="sub-panel-header">
            <div>
              <h3 class="panel-title">Lịch sử mượn sách: ${escapeHtml(reader.full_name)} (${escapeHtml(reader.card_no)})</h3>
              <p class="view-subtitle">Tổng số ${data.total} phiếu mượn trong lịch sử</p>
            </div>
            <div class="row-actions">
              <label class="filter-label" for="hist-status-select">Lọc trạng thái:</label>
              <select id="hist-status-select" class="select-input">
                <option value="" ${histStatus === "" ? "selected" : ""}>Tất cả phiếu</option>
                <option value="borrowed" ${histStatus === "borrowed" ? "selected" : ""}>Đang mượn</option>
                <option value="overdue" ${histStatus === "overdue" ? "selected" : ""}>Quá hạn</option>
                <option value="returned" ${histStatus === "returned" ? "selected" : ""}>Đã trả</option>
              </select>
              <button type="button" class="btn-secondary" id="btn-close-history">Đóng</button>
            </div>
          </div>

          <table class="admin-table" aria-label="Bảng lịch sử mượn của độc giả">
            <thead>
              <tr>
                <th>Mã phiếu</th>
                <th>Tên sách</th>
                <th>Mã bản sao</th>
                <th>Ngày mượn</th>
                <th>Hạn trả</th>
                <th>Ngày trả</th>
                <th>Trạng thái</th>
                <th>Phí phạt</th>
              </tr>
            </thead>
            <tbody>
              ${
                loans.length === 0
                  ? `<tr><td colspan="8" class="empty-cell">Không có phiếu mượn nào khớp trạng thái.</td></tr>`
                  : loans
                      .map(
                        (ln) => `
                  <tr class="${ln.status === "overdue" ? "row-overdue" : ""}">
                    <td>#${ln.id}</td>
                    <td><strong>${escapeHtml(ln.book_title)}</strong></td>
                    <td class="col-mono">${escapeHtml(ln.copy_barcode)}</td>
                    <td>${formatDateVN(ln.borrowed_at)}</td>
                    <td>${formatDateVN(ln.due_date)}</td>
                    <td>${formatDateVN(ln.returned_at)}</td>
                    <td>
                      <span class="status-badge badge-loan-${ln.status}">
                        ${escapeHtml(LOAN_STATUS_LABELS[ln.status] || ln.status)}
                        ${ln.status === "overdue" ? ` (Trễ ${ln.overdue_days} ngày)` : ""}
                      </span>
                    </td>
                    <td>${ln.fine_amount > 0 ? formatCurrencyVN(ln.fine_amount) : ln.estimated_fine > 0 ? `${formatCurrencyVN(ln.estimated_fine)} (tạm tính)` : "0 đ"}</td>
                  </tr>
                `
                      )
                      .join("")
              }
            </tbody>
          </table>
          <div id="hist-pagination"></div>
        `;

        historyPanel.querySelector("#btn-close-history").addEventListener("click", () => {
          historyPanel.classList.add("hidden");
        });

        historyPanel.querySelector("#hist-status-select").addEventListener("change", (e) => {
          histStatus = e.target.value;
          histPage = 1;
          renderHistory();
        });

        const histPag = historyPanel.querySelector("#hist-pagination");
        if (data.total_pages > 1) {
          histPag.appendChild(
            renderPagination({
              page: data.page,
              totalPages: data.total_pages,
              total: data.total,
              onPageChange(p) {
                histPage = p;
                renderHistory();
              },
            })
          );
        }
      } catch (err) {
        historyPanel.innerHTML = `<p class="field-error">Lỗi tải lịch sử: ${escapeHtml(err.message)}</p>`;
      }
    }

    renderHistory();
  }

  const debouncedSearch = createDebounce(() => {
    state.page = 1;
    loadReaders();
  }, DEBOUNCE_DELAY_MS);

  searchInput.addEventListener("input", (e) => {
    state.q = e.target.value;
    clearBtn.disabled = !hasFilter();
    debouncedSearch();
  });

  searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      state.q = searchInput.value;
      debouncedSearch.flush();
    }
  });

  statusSelect.addEventListener("change", (e) => {
    debouncedSearch.cancel();
    state.isActiveFilter = e.target.value;
    state.page = 1;
    loadReaders();
  });

  clearBtn.addEventListener("click", () => {
    debouncedSearch.cancel();
    state.q = "";
    state.isActiveFilter = "";
    state.page = 1;
    searchInput.value = "";
    statusSelect.value = "";
    loadReaders();
  });

  loadReaders();
  return section;
}
