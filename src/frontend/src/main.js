import { createOverviewView } from "./views/OverviewView.js";
import { createBooksAdminView } from "./views/BooksAdminView.js";
import { createReadersAdminView } from "./views/ReadersAdminView.js";
import { createLoansAdminView } from "./views/LoansAdminView.js";
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
            <span class="brand-tag">Hệ thống Quản lý Thư viện Số</span>
          </div>
        </div>
        <nav class="main-nav" aria-label="Điều hướng hệ thống">
          <button type="button" class="nav-tab" data-tab="overview">Tổng quan</button>
          <button type="button" class="nav-tab active" data-tab="books">Sách</button>
          <button type="button" class="nav-tab" data-tab="readers">Độc giả</button>
          <button type="button" class="nav-tab" data-tab="loans">Mượn / Trả</button>
          <button type="button" class="nav-tab" data-tab="ai">Trợ lý AI</button>
        </nav>
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
    if (tabName === "overview") {
      mount.appendChild(createOverviewView({ onNavigateTab: switchTab }));
    } else if (tabName === "readers") {
      mount.appendChild(createReadersAdminView());
    } else if (tabName === "loans") {
      mount.appendChild(createLoansAdminView());
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
