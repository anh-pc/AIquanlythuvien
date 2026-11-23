/**
 * File API client dùng chung của Frontend.
 * Tự động nhận diện cùng origin khi chạy trực tiếp từ FastAPI (:8000) hoặc gọi sang :8000/api khi chạy server riêng (:5173).
 */

export const API_BASE_URL =
  (typeof window !== "undefined" && window.__API_BASE_URL__) ||
  (typeof window !== "undefined" && window.location && window.location.port === "8000"
    ? "/api"
    : "http://127.0.0.1:8000/api");

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
        errorDetail =
          typeof data.detail === "string"
            ? data.detail
            : Array.isArray(data.detail)
            ? data.detail.map((d) => d.msg || JSON.stringify(d)).join("; ")
            : JSON.stringify(data.detail);
      }
    } catch {
      // Bỏ qua lỗi parse JSON
    }
    const err = new Error(errorDetail);
    err.status = response.status;
    throw err;
  }

  return response.json();
}
