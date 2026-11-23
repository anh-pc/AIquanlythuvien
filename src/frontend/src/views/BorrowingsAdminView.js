import { apiRequest } from "../api/client.js";

/**
 * View Quản lý Mượn / Trả Sách (giữ pattern UI nhất quán với Quản lý Sách)
 */
export function createBorrowingsAdminView() {
  const section = document.createElement("section");
  section.className = "admin-view borrowings-admin-view";

  section.innerHTML = `
    <div class="view-header">
      <div>
        <h2 class="view-title">Quản lý Mượn / Trả Sách</h2>
        <p class="view-subtitle">Theo dõi phiếu mượn, hạn trả và cập nhật hoàn trả sách về kho</p>
      </div>
    </div>
    <div id="borrowings-status" role="status" aria-live="polite" class="result-summary">Đang tải danh sách phiếu mượn...</div>
    <div class="table-container">
      <table class="admin-table" aria-label="Bảng danh sách phiếu mượn">
        <thead>
          <tr>
            <th>Mã phiếu</th>
            <th>Tên sách</th>
            <th>Độc giả</th>
            <th>Ngày mượn</th>
            <th>Hạn trả</th>
            <th>Ngày trả</th>
            <th>Trạng thái</th>
            <th>Thao tác</th>
          </tr>
        </thead>
        <tbody id="borrowings-tbody"></tbody>
      </table>
    </div>
  `;

  const statusEl = section.querySelector("#borrowings-status");
  const tbody = section.querySelector("#borrowings-tbody");

  async function loadBorrowings() {
    try {
      const records = await apiRequest("/borrowings");
      statusEl.textContent = `Tổng số ${records.length} phiếu mượn`;
      tbody.innerHTML = "";
      for (const r of records) {
        const tr = document.createElement("tr");
        const isBorrowed = r.status === "borrowed";
        tr.innerHTML = `
          <td>#${r.id}</td>
          <td><strong>${r.book_title}</strong></td>
          <td>${r.member_name} (${r.member_code})</td>
          <td>${new Date(r.borrow_date).toLocaleDateString("vi-VN")}</td>
          <td>${new Date(r.due_date).toLocaleDateString("vi-VN")}</td>
          <td>${r.return_date ? new Date(r.return_date).toLocaleDateString("vi-VN") : "—"}</td>
          <td>
            <span class="status-pill status-${r.status}">
              ${r.status === "borrowed" ? "Đang mượn" : r.status === "overdue" ? "Quá hạn" : "Đã trả"}
            </span>
          </td>
          <td>
            ${
              isBorrowed
                ? `<button type="button" class="btn-primary-sm btn-return" data-id="${r.id}">Xác nhận trả</button>`
                : "Hoàn tất"
            }
          </td>
        `;
        const btn = tr.querySelector(".btn-return");
        if (btn) {
          btn.addEventListener("click", async () => {
            await apiRequest(`/borrowings/${r.id}/return`, { method: "POST" });
            loadBorrowings();
          });
        }
        tbody.appendChild(tr);
      }
    } catch {
      statusEl.textContent = "Không tải được danh sách phiếu mượn.";
    }
  }

  loadBorrowings();
  return section;
}
