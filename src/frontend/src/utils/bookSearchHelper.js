/**
 * Helper tìm kiếm & lọc sách/thể loại phía Admin
 * Hỗ trợ debounce (~300ms), xử lý race condition (AbortController + requestId),
 * và chuẩn hoá state bộ lọc mà không cần sửa đổi file API client dùng chung.
 */
import { API_BASE_URL } from "../api/client.js";

export const DEBOUNCE_DELAY_MS = 300;
export const CATEGORY_SEARCH_LIMIT = 15;

export function createDebounce(fn, delayMs = DEBOUNCE_DELAY_MS) {
  let timerId = null;

  function debounced(...args) {
    if (timerId !== null) {
      clearTimeout(timerId);
    }
    timerId = setTimeout(() => {
      timerId = null;
      fn(...args);
    }, delayMs);
  }

  debounced.cancel = () => {
    if (timerId !== null) {
      clearTimeout(timerId);
      timerId = null;
    }
  };

  debounced.flush = (...args) => {
    debounced.cancel();
    fn(...args);
  };

  return debounced;
}

export function createRaceGuard() {
  let currentToken = 0;
  let currentController = null;

  return {
    next() {
      if (currentController) {
        currentController.abort();
      }
      currentToken += 1;
      currentController = typeof AbortController !== "undefined" ? new AbortController() : null;
      return {
        token: currentToken,
        signal: currentController ? currentController.signal : undefined,
      };
    },
    isLatest(token) {
      return token === currentToken;
    },
  };
}

export function buildBooksQueryString({ keyword = "", categoryId = null, page = 1, pageSize = 5 }) {
  const params = new URLSearchParams();
  const trimmed = typeof keyword === "string" ? keyword.trim() : "";
  if (trimmed.length > 0) {
    params.set("keyword", trimmed);
  }
  if (categoryId !== null && categoryId !== undefined && categoryId !== "") {
    params.set("category_id", String(categoryId));
  }
  params.set("page", String(page));
  params.set("page_size", String(pageSize));
  return params.toString();
}

export async function fetchAdminBooks({ keyword = "", categoryId = null, page = 1, pageSize = 5 }, signal) {
  const qs = buildBooksQueryString({ keyword, categoryId, page, pageSize });
  const res = await fetch(`${API_BASE_URL}/books?${qs}`, { signal });
  if (!res.ok) {
    throw new Error("Không tải được danh sách sách");
  }
  return res.json();
}

export async function fetchAdminCategories({ keyword = "", limit = CATEGORY_SEARCH_LIMIT }, signal) {
  const params = new URLSearchParams();
  const trimmed = typeof keyword === "string" ? keyword.trim() : "";
  if (trimmed.length > 0) {
    params.set("keyword", trimmed);
  }
  params.set("limit", String(limit));
  const res = await fetch(`${API_BASE_URL}/categories?${params.toString()}`, { signal });
  if (!res.ok) {
    throw new Error("Không tải được danh sách thể loại");
  }
  return res.json();
}
