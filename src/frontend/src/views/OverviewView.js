import { apiRequest } from "../api/client.js";
import { escapeHtml } from "../types/index.js";

/**
 * Màn 1: Tổng quan & Thống kê (F9, NV9, UX5, UX7)
 */
export function createOverviewView({ onNavigateTab }) {
  const section = document.createElement("section");
  section.className = "admin-view overview-view";
  section.setAttribute("aria-labelledby", "overview-heading");

  section.innerHTML = `
    <div class="view-header">
      <div>
        <h2 id="overview-heading" class="view-title">Tổng quan Hoạt động Thư viện</h2>
        <p class="view-subtitle">Theo dõi số liệu đầu sách, tình trạng bản sao, phiếu đang mượn, quá hạn và top sách mượn nhiều</p>
      </div>
      <div class="header-actions">
        <button type="button" class="btn-secondary" id="btn-refresh-stats">↻ Làm mới số liệu</button>
      </div>
    </div>

    <div id="stats-error-banner" class="error-banner hidden" role="alert"></div>
    <div id="stats-content" aria-live="polite" role="status">
      <p class="result-summary">Đang tải số liệu thống kê...</p>
    </div>
  `;

  const errorBanner = section.querySelector("#stats-error-banner");
  const contentEl = section.querySelector("#stats-content");
  const refreshBtn = section.querySelector("#btn-refresh-stats");

  async function loadStats() {
    errorBanner.classList.add("hidden");
    try {
      const stats = await apiRequest("/stats");
      const c = stats.copies_by_status || {};

      contentEl.innerHTML = `
        <div class="stats-grid">
          <div class="stat-card">
            <span class="stat-label">Tổng đầu sách phục vụ</span>
            <strong class="stat-value">${stats.total_books}</strong>
            <span class="stat-meta">Tổng số bản sao: <strong>${c.total || 0}</strong></span>
          </div>
          <div class="stat-card">
            <span class="stat-label">Phiếu đang mượn</span>
            <strong class="stat-value text-primary">${stats.active_loans_count}</strong>
            <span class="stat-meta">Đã trả hoàn tất: <strong>${stats.returned_loans_count}</strong></span>
          </div>
          <div class="stat-card stat-card-warning">
            <span class="stat-label">Phiếu quá hạn chưa trả</span>
            <strong class="stat-value text-danger">${stats.overdue_loans_count}</strong>
            <span class="stat-meta">Cần thu hồi & tính phí trễ hạn</span>
          </div>
          <div class="stat-card">
            <span class="stat-label">Độc giả hoạt động</span>
            <strong class="stat-value text-success">${stats.active_readers_count}</strong>
            <span class="stat-meta">Trên tổng số <strong>${stats.total_readers_count}</strong> thẻ độc giả</span>
          </div>
        </div>

        <div class="stats-panels-row">
          <div class="stats-panel">
            <h3 class="panel-title">Tình trạng bản sao trong thư viện</h3>
            <div class="copy-status-breakdown">
              <div class="copy-stat-row">
                <span class="status-badge badge-available">● Còn trong kho</span>
                <strong>${c.available || 0} bản sao</strong>
              </div>
              <div class="copy-stat-row">
                <span class="status-badge badge-borrowed">● Đang mượn</span>
                <strong>${c.borrowed || 0} bản sao</strong>
              </div>
              <div class="copy-stat-row">
                <span class="status-badge badge-damaged">▲ Hư hỏng</span>
                <strong>${c.damaged || 0} bản sao</strong>
              </div>
              <div class="copy-stat-row">
                <span class="status-badge badge-lost">✕ Thất lạc</span>
                <strong>${c.lost || 0} bản sao</strong>
              </div>
            </div>
          </div>

          <div class="stats-panel">
            <h3 class="panel-title">Top 5 đầu sách được mượn nhiều nhất</h3>
            <table class="admin-table" aria-label="Bảng top 5 sách mượn nhiều nhất">
              <thead>
                <tr>
                  <th>Hạng</th>
                  <th>Tên đầu sách</th>
                  <th>Tác giả</th>
                  <th>Thể loại</th>
                  <th>Số lượt mượn</th>
                </tr>
              </thead>
              <tbody>
                ${(stats.top_borrowed_books || [])
                  .map(
                    (b, idx) => `
                  <tr>
                    <td><strong>#${idx + 1}</strong></td>
                    <td><strong>${escapeHtml(b.title)}</strong></td>
                    <td>${escapeHtml(b.author)}</td>
                    <td><span class="category-badge">${escapeHtml(b.category_name)}</span></td>
                    <td><span class="status-badge badge-borrowed">${b.loan_count} lượt</span></td>
                  </tr>
                `
                  )
                  .join("")}
              </tbody>
            </table>
          </div>
        </div>
      `;
    } catch (err) {
      errorBanner.classList.remove("hidden");
      errorBanner.innerHTML = `
        <div class="error-banner-content">
          <span>⚠️ Không tải được số liệu thống kê (${escapeHtml(err.message)})</span>
          <button type="button" class="btn-retry" id="btn-retry-stats">Thử lại</button>
        </div>
      `;
      errorBanner.querySelector("#btn-retry-stats").addEventListener("click", loadStats);
    }
  }

  refreshBtn.addEventListener("click", loadStats);
  loadStats();
  return section;
}
