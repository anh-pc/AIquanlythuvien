/**
 * File API client dùng chung của Frontend.
 * Lưu ý: Đây là file dùng chung, không sửa đổi khi mở rộng tính năng riêng lẻ.
 */

export const API_BASE_URL =
  (typeof window !== "undefined" && window.__API_BASE_URL__) ||
  "http://127.0.0.1:8000/api";

export async function apiRequest(path, options = {}) {
  const url = `${API_BASE_URL}${path}`;
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    let errorDetail = `Lỗi HTTP ${response.status}`;
    try {
      const data = await response.json();
      if (data && data.detail) {
        errorDetail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      }
    } catch {
      // Bỏ qua lỗi parse JSON
    }
    throw new Error(errorDetail);
  }

  return response.json();
}
