import { apiRequest } from "../api/client.js";

/**
 * View Trợ lý AI Gợi ý Sách (Google Gemini / Local Catalog Fallback)
 */
export function createAiAssistantView() {
  const section = document.createElement("section");
  section.className = "admin-view ai-assistant-view";

  section.innerHTML = `
    <div class="view-header">
      <div>
        <h2 class="view-title">Trợ lý AI Gợi ý Sách</h2>
        <p class="view-subtitle">Nhập chủ đề nghiên cứu để nhận gợi ý đầu sách phù hợp trong thư viện</p>
      </div>
    </div>
    <form id="ai-recommend-form" class="filter-toolbar">
      <div class="filter-field search-field">
        <label class="filter-label" for="ai-topic-input">Chủ đề quan tâm</label>
        <input
          type="text"
          id="ai-topic-input"
          class="search-input"
          placeholder="Ví dụ: Python, Trí tuệ nhân tạo, Kinh tế..."
          value="Python"
          required
        />
      </div>
      <div class="filter-actions">
        <button type="submit" class="btn-primary">✨ Gợi ý sách với AI</button>
      </div>
    </form>
    <div id="ai-result-box" class="ai-result-box" role="status" aria-live="polite"></div>
  `;

  const form = section.querySelector("#ai-recommend-form");
  const input = section.querySelector("#ai-topic-input");
  const resultBox = section.querySelector("#ai-result-box");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const topic = input.value.trim();
    if (!topic) return;
    resultBox.textContent = "Đang phân tích và tìm sách phù hợp...";
    try {
      const res = await apiRequest("/ai/recommend", {
        method: "POST",
        body: JSON.stringify({ topic }),
      });
      resultBox.innerHTML = `
        <div class="ai-card">
          <p><strong>Model:</strong> ${res.model} (${res.provider})</p>
          <p>${res.recommendation}</p>
        </div>
      `;
    } catch {
      resultBox.textContent = "Không thể kết nối dịch vụ gợi ý AI.";
    }
  });

  return section;
}
