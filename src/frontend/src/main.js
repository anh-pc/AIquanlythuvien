import { createBooksAdminView } from "./views/BooksAdminView.js";
import { createBorrowingsAdminView } from "./views/BorrowingsAdminView.js";
import { createAiAssistantView } from "./views/AiAssistantView.js";

function initApp() {
  const root = document.getElementById("app");
  if (!root) return;

  root.innerHTML = `
    <header class="app-header">
      <div class="header-inner">
        <div class="brand">
          <span class="brand-logo" aria-hidden="true">📚</span>
          <div>
            <h1 class="brand-title">AIquanlythuvien</h1>
            <span class="brand-tag">Hệ thống Quản trị Thư viện Số</span>
          </div>
        </div>
        <nav class="main-nav" aria-label="Điều hướng quản trị">
          <button type="button" class="nav-tab active" data-tab="books">Quản lý Sách</button>
          <button type="button" class="nav-tab" data-tab="borrowings">Mượn / Trả</button>
          <button type="button" class="nav-tab" data-tab="ai">Trợ lý AI</button>
        </nav>
        <div class="user-badge">
          <span class="user-role">Thủ thư:</span>
          <strong>Đặng Văn Anh (LIB001)</strong>
        </div>
      </div>
    </header>
    <main class="app-main" id="main-view-mount"></main>
  `;

  const mount = root.querySelector("#main-view-mount");
  const tabs = root.querySelectorAll(".nav-tab");

  function switchTab(tabName) {
    tabs.forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.tab === tabName);
    });
    mount.innerHTML = "";
    if (tabName === "borrowings") {
      mount.appendChild(createBorrowingsAdminView());
    } else if (tabName === "ai") {
      mount.appendChild(createAiAssistantView());
    } else {
      mount.appendChild(createBooksAdminView());
    }
  }

  tabs.forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });

  switchTab("books");
}

document.addEventListener("DOMContentLoaded", initApp);
