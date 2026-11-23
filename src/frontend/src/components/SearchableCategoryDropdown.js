import {
  CATEGORY_SEARCH_LIMIT,
  DEBOUNCE_DELAY_MS,
  createDebounce,
  createRaceGuard,
  fetchAdminCategories,
} from "../utils/bookSearchHelper.js";

/**
 * Component Combobox Thể loại có tìm kiếm từ Backend (AC8, AC10, AC12, UX1, UX2, UX4, UX5, UX6).
 * Tái sử dụng được ở cả thanh Bộ lọc danh sách sách (allowAll=true, mặc định "Tất cả thể loại")
 * và trong Form Thêm/Sửa đầu sách (allowAll=false, chọn 1 thể loại cụ thể).
 */
export function createSearchableCategoryDropdown({
  onSelect,
  allowAll = true,
  labelText = "Thể loại",
  defaultText = "Tất cả thể loại",
  idPrefix = "category-dropdown",
}) {
  const container = document.createElement("div");
  container.className = "category-dropdown";

  let isOpen = false;
  let selectedCategory = { id: null, name: allowAll ? defaultText : "Chọn thể loại..." };
  let searchKeyword = "";
  let categories = [];
  let isLoading = false;
  let errorMessage = "";
  let activeIndex = -1;

  const raceGuard = createRaceGuard();
  const labelId = `${idPrefix}-label`;
  const triggerId = `${idPrefix}-trigger`;

  container.innerHTML = `
    <label class="filter-label" id="${labelId}" for="${triggerId}">
      ${labelText}
    </label>
    <div class="dropdown-control">
      <button
        type="button"
        id="${triggerId}"
        class="dropdown-trigger"
        aria-haspopup="listbox"
        aria-expanded="false"
        aria-labelledby="${labelId} ${triggerId}"
      >
        <span class="dropdown-selected-text">${selectedCategory.name}</span>
        <span class="dropdown-arrow" aria-hidden="true">▾</span>
      </button>
      <div class="dropdown-menu hidden" role="dialog" aria-label="Chọn thể loại sách">
        <div class="dropdown-search-box">
          <input
            type="text"
            class="dropdown-search-input"
            placeholder="Gõ để tìm thể loại..."
            aria-label="Tìm kiếm thể loại"
            autocomplete="off"
          />
        </div>
        <div class="dropdown-status" aria-live="polite" role="status"></div>
        <ul class="dropdown-list" role="listbox" tabindex="-1" aria-label="Danh sách thể loại"></ul>
      </div>
    </div>
  `;

  const triggerBtn = container.querySelector(".dropdown-trigger");
  const selectedTextEl = container.querySelector(".dropdown-selected-text");
  const menuEl = container.querySelector(".dropdown-menu");
  const searchInput = container.querySelector(".dropdown-search-input");
  const statusEl = container.querySelector(".dropdown-status");
  const listEl = container.querySelector(".dropdown-list");

  function getDisplayOptions() {
    const trimmed = searchKeyword.trim();
    const list = [];
    if (allowAll && trimmed === "") {
      list.push({ id: null, name: defaultText });
    }
    for (const c of categories) {
      list.push({ id: c.id, name: c.name });
    }
    return list;
  }

  function renderOptions() {
    listEl.innerHTML = "";
    statusEl.innerHTML = "";

    if (errorMessage) {
      statusEl.innerHTML = `
        <div class="dropdown-error" role="alert">
          <span>${errorMessage}</span>
          <button type="button" class="btn-retry-inline">Thử lại</button>
        </div>
      `;
      const retryBtn = statusEl.querySelector(".btn-retry-inline");
      retryBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        loadCategories(searchKeyword);
      });
      return;
    }

    if (isLoading) {
      statusEl.innerHTML = `<div class="dropdown-loading">Đang tìm thể loại...</div>`;
    }

    const options = getDisplayOptions();
    if (!isLoading && options.length === 0) {
      statusEl.innerHTML = `<div class="dropdown-empty">Không tìm thấy thể loại</div>`;
      return;
    }

    options.forEach((opt, idx) => {
      const li = document.createElement("li");
      const isSelected = selectedCategory.id === opt.id;
      const isFocused = idx === activeIndex;
      li.className = `dropdown-option${isSelected ? " selected" : ""}${isFocused ? " active" : ""}`;
      li.setAttribute("role", "option");
      li.setAttribute("aria-selected", isSelected ? "true" : "false");
      li.dataset.id = opt.id === null ? "" : String(opt.id);
      li.dataset.name = opt.name;
      li.innerHTML = `
        <span class="option-name">${opt.name}</span>
        ${isSelected ? '<span class="option-check" aria-hidden="true">✓</span>' : ""}
      `;
      li.addEventListener("click", (e) => {
        e.stopPropagation();
        chooseCategory(opt);
      });
      listEl.appendChild(li);
    });
  }

  async function loadCategories(kw) {
    const { token, signal } = raceGuard.next();
    isLoading = true;
    errorMessage = "";
    renderOptions();

    try {
      const data = await fetchAdminCategories(
        { keyword: kw, limit: CATEGORY_SEARCH_LIMIT },
        signal
      );
      if (!raceGuard.isLatest(token)) return;
      categories = Array.isArray(data.items) ? data.items : [];
      isLoading = false;
      activeIndex = getDisplayOptions().length > 0 ? 0 : -1;
      renderOptions();
    } catch (err) {
      if (err && err.name === "AbortError") return;
      if (!raceGuard.isLatest(token)) return;
      isLoading = false;
      errorMessage = "Không tải được danh sách thể loại";
      renderOptions();
    }
  }

  const debouncedSearch = createDebounce((kw) => {
    loadCategories(kw);
  }, DEBOUNCE_DELAY_MS);

  function chooseCategory(opt) {
    const changed = selectedCategory.id !== opt.id;
    selectedCategory = { id: opt.id, name: opt.name };
    selectedTextEl.textContent = opt.name;
    triggerBtn.classList.toggle("has-filter", allowAll && opt.id !== null);
    closeMenu();
    triggerBtn.focus();
    if (changed && typeof onSelect === "function") {
      onSelect(selectedCategory);
    }
  }

  function openMenu() {
    if (isOpen) return;
    isOpen = true;
    triggerBtn.setAttribute("aria-expanded", "true");
    menuEl.classList.remove("hidden");
    searchKeyword = "";
    searchInput.value = "";
    loadCategories("");
    setTimeout(() => searchInput.focus(), 10);
  }

  function closeMenu() {
    if (!isOpen) return;
    isOpen = false;
    debouncedSearch.cancel();
    triggerBtn.setAttribute("aria-expanded", "false");
    menuEl.classList.add("hidden");
    activeIndex = -1;
  }

  triggerBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    if (isOpen) {
      closeMenu();
    } else {
      openMenu();
    }
  });

  triggerBtn.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      openMenu();
    } else if (e.key === "Escape") {
      closeMenu();
    }
  });

  searchInput.addEventListener("input", (e) => {
    searchKeyword = e.target.value;
    debouncedSearch(searchKeyword);
  });

  searchInput.addEventListener("keydown", (e) => {
    const options = getDisplayOptions();
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (options.length > 0) {
        activeIndex = (activeIndex + 1) % options.length;
        renderOptions();
      }
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (options.length > 0) {
        activeIndex = (activeIndex - 1 + options.length) % options.length;
        renderOptions();
      }
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (activeIndex >= 0 && activeIndex < options.length) {
        chooseCategory(options[activeIndex]);
      }
    } else if (e.key === "Escape") {
      e.preventDefault();
      closeMenu();
      triggerBtn.focus();
    }
  });

  document.addEventListener("click", (e) => {
    if (isOpen && !container.contains(e.target)) {
      closeMenu();
    }
  });

  return {
    element: container,
    getSelectedCategory() {
      return { ...selectedCategory };
    },
    setSelectedCategory(cat) {
      selectedCategory = {
        id: cat && cat.id !== undefined ? cat.id : null,
        name: (cat && cat.name) || (allowAll ? defaultText : "Chọn thể loại..."),
      };
      selectedTextEl.textContent = selectedCategory.name;
      triggerBtn.classList.toggle("has-filter", allowAll && selectedCategory.id !== null);
    },
    resetToDefault() {
      debouncedSearch.cancel();
      selectedCategory = { id: null, name: allowAll ? defaultText : "Chọn thể loại..." };
      selectedTextEl.textContent = selectedCategory.name;
      triggerBtn.classList.remove("has-filter");
      searchKeyword = "";
      searchInput.value = "";
      closeMenu();
    },
  };
}
