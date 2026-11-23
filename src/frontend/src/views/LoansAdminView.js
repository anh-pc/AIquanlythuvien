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
 * Màn 4: Quản lý Mượn / Trả / Gia hạn & Phiếu quá hạn (F4, F5, F6, F10, NV1–NV5, UX1–UX7)
 */
export function createLoansAdminView() {
  const section = document.createElement("section");
  section.className = "admin-view loans-admin-view";
  section.setAttribute("aria-labelledby", "loans-heading");

  const state = {
    q: "",
    status: "",
    page: 1,
    pageSize: PAGE_SIZE_DEFAULT,
    items: [],
    total: 0,
    totalPages: 0,
    isLoading: true,
    errorMessage: "",
    selectedReader: null,
    selectedCopy: null,
  };

  const loansRaceGuard = createRaceGuard();

  section.innerHTML = `
    <div class="view-header">
      <div>
        <h2 id="loans-heading" class="view-title">Nghiệp vụ Mượn / Trả / Gia hạn Sách</h2>
        <p class="view-subtitle">Tạo phiếu mượn mới (tối đa 5 cuốn, hạn 14 ngày), trả sách (bình thường/hư hỏng/thất lạc), gia hạn (+7 ngày, tối đa 2 lần) và theo dõi phí phạt quá hạn (1.000 đ/ngày)</p>
      </div>
    </div>

    <div id="loans-toast" class="toast-banner hidden" role="status" aria-live="polite"></div>

    <!-- Khu vực Tạo Phiếu Mượn Mới (UX2: chọn độc giả và bản sao bằng ô gõ tìm) -->
    <div class="sub-panel borrow-create-panel" role="region" aria-label="Tạo phiếu mượn sách mới">
      <h3 class="panel-title">Lập phiếu mượn sách mới (NV1)</h3>
      <form id="create-loan-form" novalidate>
        <div class="form-grid">
          <div class="form-group">
            <label class="filter-label" for="loan-reader-search">1. Tìm & Chọn Độc giả *</label>
            <input
              type="text"
              id="loan-reader-search"
              class="search-input input-no-icon"
              placeholder="Gõ tên hoặc mã thẻ độc giả (ví dụ: DG001, Nguyễn Minh Tuấn)..."
              autocomplete="off"
            />
            <div id="loan-reader-results" class="Quick-search-list hidden" role="listbox" aria-label="Gợi ý độc giả"></div>
            <div id="loan-reader-picked" class="picked-badge hidden"></div>
          </div>

          <div class="form-group">
            <label class="filter-label" for="loan-copy-search">2. Tìm & Chọn Bản sao sách (Còn trong kho) *</label>
            <input
              type="text"
              id="loan-copy-search"
              class="search-input input-no-icon"
              placeholder="Gõ tên sách hoặc mã bản sao (ví dụ: Python, BS-001)..."
              autocomplete="off"
            />
            <div id="loan-copy-results" class="Quick-search-list hidden" role="listbox" aria-label="Gợi ý bản sao sách"></div>
            <div id="loan-copy-picked" class="picked-badge hidden"></div>
          </div>

          <div class="form-group">
            <label class="filter-label" for="loan-note-input">3. Ghi chú phiếu mượn</label>
            <input
              type="text"
              id="loan-note-input"
              class="search-input input-no-icon"
              placeholder="Ghi chú thêm (tuỳ chọn)..."
            />
          </div>
        </div>
        <div id="create-loan-error" class="field-error hidden" role="alert"></div>
        <div class="form-actions">
          <button type="submit" class="btn-primary" id="btn-submit-borrow">Mượn sách</button>
        </div>
      </form>
    </div>

    <!-- Bộ lọc Danh sách Phiếu mượn -->
    <div class="filter-toolbar" role="search" aria-label="Tìm kiếm và lọc phiếu mượn">
      <div class="filter-field search-field">
        <label class="filter-label" for="loan-search-input">Tra cứu phiếu mượn</label>
        <div class="search-input-wrapper">
          <span class="search-icon" aria-hidden="true">🔍</span>
          <input
            type="search"
            id="loan-search-input"
            class="search-input"
            placeholder="Tìm theo tên sách, mã bản sao (BS-...), tên hoặc mã thẻ độc giả..."
            aria-label="Tìm kiếm phiếu mượn"
            autocomplete="off"
          />
        </div>
      </div>

      <div class="filter-field">
        <label class="filter-label" for="loan-status-filter">Trạng thái phiếu</label>
        <select id="loan-status-filter" class="select-input" aria-label="Lọc trạng thái phiếu mượn">
          <option value="">Tất cả trạng thái</option>
          <option value="borrowed">Đang mượn (Còn hạn)</option>
          <option value="overdue">Quá hạn (Cần thu hồi)</option>
          <option value="returned">Đã trả</option>
        </select>
      </div>

      <div class="filter-actions">
        <button type="button" id="btn-clear-loan-filters" class="btn-secondary" disabled>
          ✕ Xoá bộ lọc
        </button>
      </div>
    </div>

    <div class="status-summary-bar">
      <div id="loans-summary" class="result-summary" role="status" aria-live="polite"></div>
    </div>

    <div id="loans-error" class="error-banner hidden" role="alert"></div>

    <!-- Modal / Panel Trả sách (chọn tình trạng trả: normal / damaged / lost - NV3) -->
    <div id="return-modal-panel" class="sub-panel hidden" role="region" aria-label="Xác nhận trả sách"></div>

    <div class="table-container">
      <table class="admin-table" aria-label="Bảng danh sách phiếu mượn">
        <thead>
          <tr>
            <th>Mã phiếu</th>
            <th>Đầu sách & Bản sao</th>
            <th>Độc giả</th>
            <th>Ngày mượn</th>
            <th>Hạn trả</th>
            <th>Ngày trả</th>
            <th>Gia hạn</th>
            <th>Trạng thái & Phí phạt</th>
            <th>Thao tác</th>
          </tr>
        </thead>
        <tbody id="loans-tbody"></tbody>
      </table>
    </div>

    <div id="loans-pagination"></div>
  `;

  const toastEl = section.querySelector("#loans-toast");
  const errorBanner = section.querySelector("#loans-error");
  const summaryEl = section.querySelector("#loans-summary");
  const tbody = section.querySelector("#loans-tbody");
  const paginationMount = section.querySelector("#loans-pagination");
  const searchInput = section.querySelector("#loan-search-input");
  const statusSelect = section.querySelector("#loan-status-filter");
  const clearBtn = section.querySelector("#btn-clear-loan-filters");
  const returnPanel = section.querySelector("#return-modal-panel");

  const readerSearchInput = section.querySelector("#loan-reader-search");
  const readerResultsEl = section.querySelector("#loan-reader-results");
  const readerPickedEl = section.querySelector("#loan-reader-picked");
  const copySearchInput = section.querySelector("#loan-copy-search");
  const copyResultsEl = section.querySelector("#loan-copy-results");
  const copyPickedEl = section.querySelector("#loan-copy-picked");
  const createLoanForm = section.querySelector("#create-loan-form");
  const createLoanErr = section.querySelector("#create-loan-error");

  function showToast(msg) {
    toastEl.textContent = `✓ ${msg}`;
    toastEl.classList.remove("hidden");
    setTimeout(() => toastEl.classList.add("hidden"), 4500);
  }

  // --- Combobox gõ tìm Độc giả khi lập phiếu mượn (UX2) ---
  const debouncedReaderLookup = createDebounce(async (kw) => {
    try {
      const data = await apiRequest(`/readers?q=${encodeURIComponent(kw)}&page_size=8`);
      const items = data.items || [];
      readerResultsEl.innerHTML = "";
      if (items.length === 0) {
        readerResultsEl.innerHTML = `<div class="dropdown-empty">Không tìm thấy độc giả</div>`;
      } else {
        for (const r of items) {
          const item = document.createElement("div");
          item.className = "dropdown-option";
          item.innerHTML = `
            <span><strong>${escapeHtml(r.card_no)}</strong> — ${escapeHtml(r.full_name)}</span>
            <span class="sub-meta">${r.is_active ? `Đang mượn: ${r.active_loans_count}/5` : "Đã khoá thẻ"}</span>
          `;
          item.addEventListener("click", () => {
            state.selectedReader = r;
            readerSearchInput.value = `${r.card_no} - ${r.full_name}`;
            readerResultsEl.classList.add("hidden");
            readerPickedEl.classList.remove("hidden");
            readerPickedEl.textContent = `Đã chọn độc giả: ${r.full_name} (${r.card_no}) — Đang mượn ${r.active_loans_count}/5 cuốn`;
            createLoanErr.classList.add("hidden");
          });
          readerResultsEl.appendChild(item);
        }
      }
      readerResultsEl.classList.remove("hidden");
    } catch {
      readerResultsEl.classList.add("hidden");
    }
  }, 250);

  readerSearchInput.addEventListener("focus", () => {
    debouncedReaderLookup(readerSearchInput.value.trim());
  });
  readerSearchInput.addEventListener("input", () => {
    state.selectedReader = null;
    readerPickedEl.classList.add("hidden");
    debouncedReaderLookup(readerSearchInput.value.trim());
  });

  // --- Combobox gõ tìm Bản sao Còn trong kho khi lập phiếu mượn (UX2) ---
  const debouncedCopyLookup = createDebounce(async (kw) => {
    try {
      const data = await apiRequest(
        `/copies?q=${encodeURIComponent(kw)}&status=available&page_size=10`
      );
      const items = data.items || [];
      copyResultsEl.innerHTML = "";
      if (items.length === 0) {
        copyResultsEl.innerHTML = `<div class="dropdown-empty">Không có bản sao 'Còn trong kho' phù hợp</div>`;
      } else {
        for (const c of items) {
          const item = document.createElement("div");
          item.className = "dropdown-option";
          item.innerHTML = `
            <span><strong>${escapeHtml(c.barcode)}</strong> — ${escapeHtml(c.book_title || "")}</span>
            <span class="status-badge badge-available">Còn trong kho</span>
          `;
          item.addEventListener("click", () => {
            state.selectedCopy = c;
            copySearchInput.value = `${c.barcode} - ${c.book_title}`;
            copyResultsEl.classList.add("hidden");
            copyPickedEl.classList.remove("hidden");
            copyPickedEl.textContent = `Đã chọn bản sao: ${c.barcode} (${c.book_title})`;
            createLoanErr.classList.add("hidden");
          });
          copyResultsEl.appendChild(item);
        }
      }
      copyResultsEl.classList.remove("hidden");
    } catch {
      copyResultsEl.classList.add("hidden");
    }
  }, 250);

  copySearchInput.addEventListener("focus", () => {
    debouncedCopyLookup(copySearchInput.value.trim());
  });
  copySearchInput.addEventListener("input", () => {
    state.selectedCopy = null;
    copyPickedEl.classList.add("hidden");
    debouncedCopyLookup(copySearchInput.value.trim());
  });

  document.addEventListener("click", (e) => {
    if (!readerSearchInput.contains(e.target) && !readerResultsEl.contains(e.target)) {
      readerResultsEl.classList.add("hidden");
    }
    if (!copySearchInput.contains(e.target) && !copyResultsEl.contains(e.target)) {
      copyResultsEl.classList.add("hidden");
    }
  });

  createLoanForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    createLoanErr.classList.add("hidden");

    if (!state.selectedReader) {
      createLoanErr.textContent = "Vui lòng gõ tìm và chọn một độc giả từ danh sách gợi ý.";
      createLoanErr.classList.remove("hidden");
      return;
    }
    if (!state.selectedCopy) {
      createLoanErr.textContent = "Vui lòng gõ tìm và chọn một bản sao sách còn trong kho.";
      createLoanErr.classList.remove("hidden");
      return;
    }

    const noteVal = section.querySelector("#loan-note-input").value.trim();
    try {
      const created = await apiRequest("/loans", {
        method: "POST",
        body: JSON.stringify({
          reader_id: state.selectedReader.id,
          copy_id: state.selectedCopy.id,
          note: noteVal || null,
        }),
      });
      showToast(
        `Lập phiếu mượn #${created.id} thành công: "${created.book_title}" (${created.copy_barcode}) cho ${created.reader_name}. Hạn trả: ${formatDateVN(created.due_date)}.`
      );
      state.selectedReader = null;
      state.selectedCopy = null;
      createLoanForm.reset();
      readerPickedEl.classList.add("hidden");
      copyPickedEl.classList.add("hidden");
      loadLoans();
    } catch (err) {
      createLoanErr.textContent = err.message || "Không thể lập phiếu mượn.";
      createLoanErr.classList.remove("hidden");
    }
  });

  function hasFilter() {
    return state.q.trim().length > 0 || state.status !== "";
  }

  async function loadLoans() {
    const { token, signal } = loansRaceGuard.next();
    state.isLoading = true;
    state.errorMessage = "";
    clearBtn.disabled = !hasFilter();

    const params = new URLSearchParams({
      page: String(state.page),
      page_size: String(state.pageSize),
    });
    if (state.q.trim()) params.set("q", state.q.trim());
    if (state.status) params.set("status", state.status);

    try {
      const data = await apiRequest(`/loans?${params.toString()}`, { signal });
      if (!loansRaceGuard.isLatest(token)) return;
      state.items = data.items || [];
      state.total = data.total || 0;
      state.totalPages = data.total_pages || 0;
      state.isLoading = false;
      renderTable();
    } catch (err) {
      if (err && err.name === "AbortError") return;
      if (!loansRaceGuard.isLatest(token)) return;
      state.isLoading = false;
      state.errorMessage = err.message || "Không tải được danh sách phiếu mượn.";
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
          <button type="button" class="btn-retry" id="btn-retry-loans">Thử lại</button>
        </div>
      `;
      errorBanner.querySelector("#btn-retry-loans").addEventListener("click", loadLoans);
    } else {
      errorBanner.classList.add("hidden");
    }

    summaryEl.textContent = `Tìm thấy ${state.total} phiếu mượn`;
    tbody.innerHTML = "";

    if (state.items.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="9" class="empty-cell">Không tìm thấy phiếu mượn nào phù hợp bộ lọc.</td>
        </tr>
      `;
    } else {
      for (const ln of state.items) {
        const tr = document.createElement("tr");
        if (ln.status === "overdue") {
          tr.className = "row-overdue";
        }
        const isUnreturned = !ln.returned_at;
        const canRenew = isUnreturned && ln.status !== "overdue" && ln.renew_count < 2;

        const conditionBadge =
          ln.return_condition === "damaged"
            ? `<div class="sub-meta text-danger">Trả: Hư hỏng</div>`
            : ln.return_condition === "lost"
            ? `<div class="sub-meta text-danger">Trả: Thất lạc</div>`
            : ln.return_condition === "normal"
            ? `<div class="sub-meta text-success">Trả: Bình thường</div>`
            : "";

        tr.innerHTML = `
          <td><strong>#${ln.id}</strong></td>
          <td>
            <strong>${escapeHtml(ln.book_title)}</strong>
            <div class="sub-meta">Mã bản sao: <strong class="col-mono">${escapeHtml(ln.copy_barcode)}</strong></div>
          </td>
          <td>
            <strong>${escapeHtml(ln.reader_name)}</strong>
            <div class="sub-meta">${escapeHtml(ln.reader_card_no)}</div>
          </td>
          <td>${formatDateVN(ln.borrowed_at)}</td>
          <td><strong>${formatDateVN(ln.due_date)}</strong></td>
          <td>
            ${formatDateVN(ln.returned_at)}
            ${conditionBadge}
          </td>
          <td>${ln.renew_count} / 2 lần</td>
          <td>
            <div>
              <span class="status-badge badge-loan-${ln.status}">
                ${escapeHtml(LOAN_STATUS_LABELS[ln.status] || ln.status)}
                ${ln.status === "overdue" ? ` (Trễ ${ln.overdue_days} ngày)` : ""}
              </span>
            </div>
            ${
              ln.fine_amount > 0
                ? `<div class="fine-text">Phí phạt: <strong>${formatCurrencyVN(ln.fine_amount)}</strong></div>`
                : ln.estimated_fine > 0
                ? `<div class="fine-text">Phạt tạm tính: <strong>${formatCurrencyVN(ln.estimated_fine)}</strong></div>`
                : ""
            }
          </td>
          <td>
            ${
              isUnreturned
                ? `
                <div class="row-actions">
                  <button type="button" class="btn-primary-sm btn-open-return">Trả sách</button>
                  <button
                    type="button"
                    class="btn-action btn-renew"
                    ${!canRenew ? 'title="Chỉ gia hạn phiếu chưa quá hạn và dưới 2 lần"' : ""}
                  >
                    Gia hạn
                  </button>
                </div>
              `
                : `<span class="sub-meta">Đã hoàn tất</span>`
            }
          </td>
        `;

        const returnBtn = tr.querySelector(".btn-open-return");
        if (returnBtn) {
          returnBtn.addEventListener("click", () => openReturnPanel(ln));
        }

        const renewBtn = tr.querySelector(".btn-renew");
        if (renewBtn) {
          renewBtn.addEventListener("click", () => handleRenewLoan(ln));
        }

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
            loadLoans();
          },
        })
      );
    }
  }

  function openReturnPanel(loan) {
    returnPanel.classList.remove("hidden");
    returnPanel.innerHTML = `
      <div class="sub-panel-header">
        <div>
          <h3 class="panel-title">Trả sách cho Phiếu mượn #${loan.id}</h3>
          <p class="view-subtitle">
            Sách: <strong>${escapeHtml(loan.book_title)}</strong> (Bản sao: <strong>${escapeHtml(loan.copy_barcode)}</strong>) —
            Độc giả: <strong>${escapeHtml(loan.reader_name)} (${escapeHtml(loan.reader_card_no)})</strong>
            ${
              loan.overdue_days > 0
                ? ` — <span class="text-danger">Quá hạn ${loan.overdue_days} ngày (Phí phạt: ${formatCurrencyVN(loan.estimated_fine)})</span>`
                : ""
            }
          </p>
        </div>
      </div>
      <form id="confirm-return-form" class="inline-form">
        <label class="filter-label" for="return-condition-select">Tình trạng bản sao khi trả (NV3):</label>
        <select id="return-condition-select" class="select-input">
          <option value="normal">Bình thường (Đưa về Còn trong kho)</option>
          <option value="damaged">Hư hỏng (Chuyển bản sao sang Hư hỏng)</option>
          <option value="lost">Thất lạc (Chuyển bản sao sang Thất lạc)</option>
        </select>
        <label class="filter-label" for="return-note-input">Ghi chú trả:</label>
        <input type="text" id="return-note-input" class="search-input input-no-icon" placeholder="Ghi chú tình trạng sách..." />
        <button type="submit" class="btn-primary">Xác nhận trả sách</button>
        <button type="button" class="btn-secondary" id="btn-cancel-return">Huỷ</button>
      </form>
    `;

    returnPanel.querySelector("#btn-cancel-return").addEventListener("click", () => {
      returnPanel.classList.add("hidden");
    });

    returnPanel.querySelector("#confirm-return-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const cond = returnPanel.querySelector("#return-condition-select").value;
      const note = returnPanel.querySelector("#return-note-input").value.trim();

      if (cond === "damaged" || cond === "lost") {
        const condVN = cond === "damaged" ? "Hư hỏng" : "Thất lạc";
        const ok = window.confirm(
          `Bạn đang ghi nhận trả sách với tình trạng "${condVN}". Bản sao ${loan.copy_barcode} sẽ ngừng cho mượn. Bạn có chắc chắn không?`
        );
        if (!ok) return;
      }

      try {
        const returned = await apiRequest(`/loans/${loan.id}/return`, {
          method: "POST",
          body: JSON.stringify({ return_condition: cond, note: note || null }),
        });
        returnPanel.classList.add("hidden");
        const fineMsg =
          returned.fine_amount > 0
            ? ` — Phí phạt trả trễ: ${formatCurrencyVN(returned.fine_amount)}`
            : "";
        showToast(
          `Đã nhận trả sách phiếu #${returned.id} (${returned.copy_barcode})${fineMsg}.`
        );
        loadLoans();
      } catch (err) {
        state.errorMessage = err.message;
        renderTable();
      }
    });
  }

  async function handleRenewLoan(loan) {
    try {
      const renewed = await apiRequest(`/loans/${loan.id}/renew`, {
        method: "POST",
      });
      showToast(
        `Đã gia hạn phiếu #${renewed.id} (Lần ${renewed.renew_count}/2) — Hạn trả mới: ${formatDateVN(renewed.due_date)}.`
      );
      loadLoans();
    } catch (err) {
      state.errorMessage = err.message;
      renderTable();
    }
  }

  const debouncedSearch = createDebounce(() => {
    state.page = 1;
    loadLoans();
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
    state.status = e.target.value;
    state.page = 1;
    loadLoans();
  });

  clearBtn.addEventListener("click", () => {
    debouncedSearch.cancel();
    state.q = "";
    state.status = "";
    state.page = 1;
    searchInput.value = "";
    statusSelect.value = "";
    loadLoans();
  });

  loadLoans();
  return section;
}
