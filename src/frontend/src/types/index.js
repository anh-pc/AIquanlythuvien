/**
 * File types & hằng số dùng chung của Frontend
 */

export const PAGE_SIZE_DEFAULT = 10;

export const COPY_STATUS_LABELS = {
  available: "Còn trong kho",
  borrowed: "Đang mượn",
  damaged: "Hư hỏng",
  lost: "Thất lạc",
};

export const LOAN_STATUS_LABELS = {
  borrowed: "Đang mượn",
  overdue: "Quá hạn",
  returned: "Đã trả",
};

/**
 * Chuyển chuỗi ngày ISO YYYY-MM-DD sang định dạng hiển thị Việt Nam dd/mm/yyyy (UX5).
 */
export function formatDateVN(isoDateStr) {
  if (!isoDateStr) return "—";
  const clean = String(isoDateStr).slice(0, 10);
  const parts = clean.split("-");
  if (parts.length !== 3) return clean;
  return `${parts[2]}/${parts[1]}/${parts[0]}`;
}

export function formatCurrencyVN(amount) {
  const num = Number(amount || 0);
  return `${num.toLocaleString("vi-VN")} đ`;
}

export function escapeHtml(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
