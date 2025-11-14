(() => {
  const SNAPSHOT = (window.__BLD_DATA__ && window.__BLD_DATA__.distros) || [];
  const SNAPSHOT_MAP = new Map(SNAPSHOT.map((item) => [item.id, item]));
  const LAST_UPDATED =
    (window.__BLD_DATA__ && window.__BLD_DATA__.lastUpdatedDisplay) || "Unknown";
  const STORAGE_KEYS =
    window.__BLD_STORAGE_KEYS ||
    Object.freeze({
      DATASET_CACHE: "bld::distros::v2",
      COMPARE_QUEUE: "bld::compareQueue",
      RECENTS: "bld::recent",
    });
  window.__BLD_STORAGE_KEYS = STORAGE_KEYS;
  const CACHE_TTL = 1000 * 60 * 60 * 12; // 12 hours
  const CLEARBIT_BASE = "https://logo.clearbit.com/";

  document.addEventListener("DOMContentLoaded", () => {
    const el = document.querySelector(".typewriter");
    if (!el) return;

    const words = JSON.parse(el.getAttribute("data-words") || "[]");
    if (!Array.isArray(words) || !words.length) return;

    let idx = 0;
    let current = "";
    let deleting = false;
    let speed = 90;

    // Lock wrapper height to avoid jitter or movement
    if (el.parentElement) {
      el.parentElement.style.height = "1.4em";
    }

    const type = () => {
      const word = words[idx];

      if (!deleting) {
        current = word.substring(0, current.length + 1);
      } else {
        current = word.substring(0, current.length - 1);
      }

      el.textContent = current;

      if (!deleting && current === word) {
        deleting = true;
        speed = 900; // pause before deleting
      } else if (deleting && current === "") {
        deleting = false;
        idx = (idx + 1) % words.length;
        speed = 300; // pause before typing next word
      } else {
        speed = deleting ? 50 : 90;
      }

      setTimeout(type, speed);
    };

    type();
  });

  initFooterDates();
  initNav();

  if (document.body.classList.contains("catalog")) {
    initCatalogPage();
  }

  if (document.body.classList.contains("compare")) {
    initComparePage();
  }

  function initFooterDates() {
    document.querySelectorAll(".last-updated").forEach((node) => {
      node.textContent = `Last updated ${LAST_UPDATED}`;
    });
  }

  function initNav() {
    const header = document.querySelector(".site-header");
    const nav = document.getElementById("site-nav");
    const toggle = document.getElementById("navToggle");
    if (!header || !nav || !toggle) {
      return;
    }

    const closeNav = () => {
      nav.setAttribute("data-open", "false");
      toggle.setAttribute("aria-expanded", "false");
    };

    toggle.addEventListener("click", () => {
      const open = nav.getAttribute("data-open") === "true";
      if (open) {
        closeNav();
      } else {
        nav.setAttribute("data-open", "true");
        toggle.setAttribute("aria-expanded", "true");
      }
    });

    document.addEventListener("click", (event) => {
      if (!nav.contains(event.target) && !toggle.contains(event.target)) {
        closeNav();
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeNav();
      }
    });

    const scrollLinks = document.querySelectorAll("[data-scroll]");
    scrollLinks.forEach((link) => {
      link.addEventListener("click", (event) => {
        event.preventDefault();
        const target = document.querySelector(link.getAttribute("href"));
        if (target) {
          target.scrollIntoView({ behavior: "smooth", block: "start" });
        }
        closeNav();
      });
    });

    document.querySelectorAll("[data-nav-search]").forEach((link) => {
      link.addEventListener("click", (event) => {
        const searchInput = document.getElementById("searchInput");
        if (searchInput) {
          event.preventDefault();
          searchInput.focus({ preventScroll: false });
          searchInput.scrollIntoView({ behavior: "smooth", block: "center" });
          closeNav();
        }
      });
    });
  }

  async function initCatalogPage() {
    const searchInput = document.getElementById("searchInput");
    const categoryFilter = document.getElementById("categoryFilter");
    const sortControl = document.getElementById("sortControl");
    const resetFilters = document.getElementById("resetFilters");
    const grid = document.getElementById("distroGrid");
    const skeletonGrid = document.getElementById("skeletonGrid");
    const offlineBanner = document.getElementById("offlineBanner");
    const compareTray = document.getElementById("compareTray");
    const compareCount = document.getElementById("compareCount");
    const launchCompare = document.getElementById("launchCompare");
    const resetCompare = document.getElementById("resetCompare");

    if (!searchInput || !categoryFilter || !sortControl || !grid) {
      return;
    }

    const state = {
      dataset: [],
      filtered: [],
      compareSelection: readCompareSelection(),
      offline: false,
    };

    updateCompareTrayUI();

    try {
      state.dataset = await loadDistros((offline) => {
        state.offline = offline;
      });
      state.filtered = sortData(state.dataset, sortControl.value);
      renderGrid(state.filtered);
    } catch (error) {
      grid.innerHTML =
        '<p class="empty-state" role="status">We could not load the catalog right now. Refresh or use the offline snapshot to keep browsing.</p>';
    } finally {
      if (skeletonGrid) {
        skeletonGrid.setAttribute("aria-hidden", "true");
        skeletonGrid.innerHTML = "";
      }
      if (offlineBanner && state.offline) {
        offlineBanner.setAttribute("aria-hidden", "false");
      }
    }

    const debouncedFilter = debounce(() => {
      const query = (searchInput.value || "").trim().toLowerCase();
      const category = categoryFilter.value;
      const sortBy = sortControl.value;

      const results = state.dataset
        .filter((item) => matchesQuery(item, query))
        .filter((item) => matchesCategory(item, category));

      state.filtered = sortData(results, sortBy);
      renderGrid(state.filtered);
    }, 180);

    searchInput.addEventListener("input", debouncedFilter);
    categoryFilter.addEventListener("change", debouncedFilter);
    sortControl.addEventListener("change", debouncedFilter);

    if (resetFilters) {
      resetFilters.addEventListener("click", () => {
        searchInput.value = "";
        categoryFilter.value = "all";
        sortControl.value = "popularity";
        state.filtered = sortData(state.dataset, "popularity");
        renderGrid(state.filtered);
      });
    }

    grid.addEventListener("click", (event) => {
      const card = event.target.closest("[data-distro-card]");
      if (!card) return;
      const id = card.getAttribute("data-id");
      const compareButton = event.target.closest(".compare-toggle");
      if (compareButton) {
        event.stopPropagation();
        toggleCompareSelection(id);
        compareButton.setAttribute(
          "data-active",
          String(state.compareSelection.includes(id))
        );
        return;
      }
      if (id) {
        window.location.href = `distros/${id}.html`;
      }
    });

    if (compareTray && compareCount && launchCompare && resetCompare) {
      launchCompare.addEventListener("click", () => {
        if (!state.compareSelection.length) return;
        const params = new URLSearchParams();
        params.set("ids", state.compareSelection.join(","));
        window.location.href = `compare.html?${params.toString()}`;
      });

      resetCompare.addEventListener("click", () => {
        state.compareSelection = [];
        writeCompareSelection(state.compareSelection);
        updateCompareTrayUI();
        grid.querySelectorAll(".compare-toggle").forEach((btn) => {
          btn.setAttribute("data-active", "false");
        });
      });
    }

    function renderGrid(items) {
      grid.innerHTML = "";
      if (!items.length) {
        grid.innerHTML =
          '<p class="empty-state" role="status">No distros match those filters yet. Try another category or reset the filters.</p>';
        return;
      }

      items.forEach((item, index) => {
        const card = document.createElement("article");
        card.className = "distro-card";
        card.dataset.distroCard = "true";
        card.dataset.id = item.id;
        card.style.setProperty("--delay", `${Math.min(index, 20) * 40}ms`);

        const logo = document.createElement("div");
        logo.className = "distro-logo";
        const img = document.createElement("img");
        img.alt = `${item.name} logo`;
        img.loading = "lazy";
        img.decoding = "async";
        img.referrerPolicy = "no-referrer";
        assignLogo(img, logo, item);
        logo.appendChild(img);

        const title = document.createElement("h2");
        title.textContent = item.name;

        const badgeRow = document.createElement("div");
        badgeRow.className = "badge-row";
        const status = document.createElement("span");
        status.className = "status-badge";
        status.dataset.status = item.status;
        status.textContent = item.status;
        badgeRow.appendChild(status);

        buildBadges(item).forEach((badge) => {
          const span = document.createElement("span");
          span.className = "pill";
          span.dataset.pill = badge;
          span.textContent = badge;
          badgeRow.appendChild(span);
        });

        const meta = document.createElement("div");
        meta.className = "distro-meta";
        meta.innerHTML = [
          escapeHTML(item.category || ""),
          escapeHTML(item.package_manager || ""),
          escapeHTML(item.release_model || "Release"),
        ]
          .map((text) => `<span>${text}</span>`)
          .join("");

        const actions = document.createElement("div");
        actions.className = "distro-actions";
        const compareBtn = document.createElement("button");
        compareBtn.type = "button";
        compareBtn.className = "compare-toggle";
        compareBtn.textContent = "Compare";
        compareBtn.setAttribute(
          "data-active",
          String(state.compareSelection.includes(item.id))
        );
        actions.appendChild(compareBtn);
        const link = document.createElement("span");
        link.className = "link-arrow";
        link.textContent = "View details";
        actions.appendChild(link);

        card.appendChild(logo);
        card.appendChild(title);
        card.appendChild(badgeRow);
        card.appendChild(meta);
        card.appendChild(actions);

        grid.appendChild(card);
      });
    }

    function toggleCompareSelection(id) {
      if (!id) return;
      const existingIndex = state.compareSelection.indexOf(id);
      if (existingIndex >= 0) {
        state.compareSelection.splice(existingIndex, 1);
      } else if (state.compareSelection.length < 4) {
        state.compareSelection.push(id);
      }
      writeCompareSelection(state.compareSelection);
      updateCompareTrayUI();
    }

    function updateCompareTrayUI() {
      if (!compareTray || !compareCount) return;
      compareCount.textContent = `${state.compareSelection.length}/4 selected`;
      compareTray.dataset.open = state.compareSelection.length ? "true" : "false";
    }
  }

  async function initComparePage() {
    const select = document.getElementById("compareSelect");
    const form = document.getElementById("compareForm");
    const chips = document.getElementById("selectedChips");
    const table = document.getElementById("compareTable");
    const hint = document.getElementById("compareHint");
    const clearBtn = document.getElementById("clearCompareForm");

    if (!select || !form || !chips || !table) {
      return;
    }

    let dataset = [];
    try {
      dataset = await loadDistros();
    } catch (error) {
      if (hint) {
        hint.textContent = "We could not load the compare data right now. Refresh to try again.";
      }
      return;
    }
    const map = new Map(dataset.map((item) => [item.id, item]));
    const sortedNames = [...dataset].sort((a, b) => a.name.localeCompare(b.name));
    select.innerHTML = sortedNames
      .map((item) => `<option value="${item.id}">${item.name}</option>`)
      .join("");

    let selection = readCompareSelection();
    const queryIds = new URLSearchParams(window.location.search).get("ids");
    if (queryIds) {
      selection = Array.from(
        new Set(
          queryIds
            .split(",")
            .map((id) => id.trim())
            .filter((id) => map.has(id))
        )
      ).slice(0, 4);
    }

    updateSelection();

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const value = select.value;
      if (!value || !map.has(value)) return;
      if (!selection.includes(value) && selection.length < 4) {
        selection.push(value);
        updateSelection();
      }
    });

    if (clearBtn) {
      clearBtn.addEventListener("click", () => {
        selection = [];
        updateSelection();
      });
    }

    function updateSelection() {
      selection = Array.from(new Set(selection.filter((id) => map.has(id))));
      writeCompareSelection(selection);
      if (hint) {
        hint.textContent = selection.length
          ? `Comparing ${selection.length} distro${selection.length > 1 ? "s" : ""}`
          : "Select up to four distros from the selector or catalog tray to populate this table.";
      }
      chips.innerHTML = selection
        .map((id) => {
          const name = escapeHTML(map.get(id).name);
          return `<button type="button" data-remove="${id}" aria-label="Remove ${name} from compare">${name} &times;</button>`;
        })
        .join("");
      chips.querySelectorAll("[data-remove]").forEach((btn) => {
        btn.addEventListener("click", () => {
          const id = btn.getAttribute("data-remove");
          selection = selection.filter((item) => item !== id);
          updateSelection();
        });
      });
      renderTable(selection.map((id) => map.get(id)).filter(Boolean));
      const params = new URLSearchParams();
      if (selection.length) {
        params.set("ids", selection.join(","));
      }
      const newUrl = params.toString()
        ? `${window.location.pathname}?${params.toString()}`
        : window.location.pathname;
      window.history.replaceState({}, "", newUrl);
    }

    function renderTable(items) {
      const thead = table.querySelector("thead");
      const tbody = table.querySelector("tbody");
      if (!thead || !tbody) return;
      if (!items.length) {
        thead.innerHTML = "";
        tbody.innerHTML =
          '<tr><td class="table-empty">Select up to four distros from above to start comparing.</td></tr>';
        return;
      }

      thead.innerHTML = `
        <tr>
          <th>Metric</th>
          ${items
            .map(
              (item) =>
                `<th>${escapeHTML(item.name)}<br><span class="muted-label">${escapeHTML(
                  item.release_model || "Release"
                )}</span></th>`
            )
            .join("")}
        </tr>
      `;

      const rows = [
        { label: "Category", get: (d) => d.category },
        { label: "Status", get: (d) => d.status },
        { label: "Release model", get: (d) => d.release_model || "Release" },
        { label: "Package manager", get: (d) => d.package_manager },
        { label: "Desktop environments", get: (d) => d.desktop },
        {
          label: "Hardware (minimum)",
          get: (d) => formatHardware(d.hardware_requirements && d.hardware_requirements.minimum),
        },
        {
          label: "Hardware (recommended)",
          get: (d) =>
            formatHardware(d.hardware_requirements && d.hardware_requirements.recommended),
        },
        { label: "Benchmarks", get: (d) => formatBenchmarks(d.benchmarks) },
        { label: "Pros", get: (d) => formatList(d.pros) },
        { label: "Cons", get: (d) => formatList(d.cons) },
      ];

      tbody.innerHTML = rows
        .map(
          (row) => `
          <tr>
            <th scope="row">${escapeHTML(row.label)}</th>
            ${items.map((item) => `<td>${row.get(item) || "&mdash;"}</td>`).join("")}
          </tr>
        `
        )
        .join("");
    }
  }

  function loadDistros(onFallback) {
    return new Promise(async (resolve, reject) => {
      const fallbackDataset = () => {
        if (SNAPSHOT.length) {
          onFallback && onFallback(true);
          return resolve(clone(SNAPSHOT));
        }
        reject(new Error("No dataset available"));
      };

      if (isFileProtocol()) {
        return fallbackDataset();
      }

      const cached = readCache();
      if (cached) {
        onFallback && onFallback(false);
        return resolve(cached);
      }

      try {
        const response = await fetch("api/linux_distros_full.json", { cache: "no-store" });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        const enriched = enrichDataset(data);
        saveCache(enriched);
        onFallback && onFallback(false);
        resolve(enriched);
      } catch (error) {
        if (cached) {
          onFallback && onFallback(true);
          resolve(cached);
          return;
        }
        fallbackDataset();
      }
    });
  }

  function enrichDataset(list) {
    return list.map((item) => {
      const fallback = SNAPSHOT_MAP.get(item.id) || {};
      return {
        ...fallback,
        ...item,
        release_model: fallback.release_model || item.release_model,
        popularity_rank: fallback.popularity_rank || item.popularity_rank,
      };
    });
  }

  function readCache() {
    try {
      const raw = localStorage.getItem(STORAGE_KEYS.DATASET_CACHE);
      if (!raw) return null;
      const cached = JSON.parse(raw);
      if (!cached || Date.now() - cached.savedAt > CACHE_TTL) {
        localStorage.removeItem(STORAGE_KEYS.DATASET_CACHE);
        return null;
      }
      return cached.data;
    } catch (error) {
      return null;
    }
  }

  function saveCache(data) {
    try {
      localStorage.setItem(
        STORAGE_KEYS.DATASET_CACHE,
        JSON.stringify({
          savedAt: Date.now(),
          data,
        })
      );
    } catch (error) {
      /* noop */
    }
  }

  function matchesQuery(item, query) {
    if (!query) return true;
    const haystacks = [
      item.name,
      item.category,
      item.package_manager,
      item.release_model,
      (item.pros || []).join(" "),
    ]
      .map((str) => (str || "").toLowerCase())
      .filter(Boolean);
    return haystacks.some((text) => fuzzyScore(text, query) > 0);
  }

  function matchesCategory(item, category) {
    if (category === "all") return true;
    const cat = (item.category || "").toLowerCase();
    switch (category) {
      case "beginner":
        return cat.includes("beginner") || (item.benchmarks?.beginner_score || 0) >= 8;
      case "server":
        return cat.includes("server") || ["debian", "rhel", "almalinux", "rocky", "centos"].includes(item.id);
      case "security":
        return cat.includes("security") || ["kali", "parrot", "tails", "qubes"].includes(item.id);
      case "rolling":
        return (item.release_model || "").toLowerCase() === "rolling";
      case "lts":
        return (item.release_model || "").toLowerCase() === "lts";
      default:
        return true;
    }
  }

  function sortData(list, sortBy) {
    const sorted = [...list];
    if (sortBy === "name") {
      sorted.sort((a, b) => a.name.localeCompare(b.name));
    } else if (sortBy === "beginner") {
      sorted.sort(
        (a, b) => (b.benchmarks?.beginner_score || 0) - (a.benchmarks?.beginner_score || 0)
      );
    } else if (sortBy === "resource") {
      const order = { low: 1, medium: 2, high: 3 };
      sorted.sort(
        (a, b) =>
          (order[(a.benchmarks?.resource_usage || "").toLowerCase()] || 99) -
          (order[(b.benchmarks?.resource_usage || "").toLowerCase()] || 99)
      );
    } else {
      sorted.sort((a, b) => (a.popularity_rank || 999) - (b.popularity_rank || 999));
    }
    return sorted;
  }

  function buildBadges(item) {
    const badges = [];
    if (matchesCategory(item, "beginner")) badges.push("Beginner");
    if (matchesCategory(item, "server")) badges.push("Server");
    if (matchesCategory(item, "security")) badges.push("Security");
    const release = (item.release_model || "").toUpperCase();
    if (release === "LTS" || release === "ROLLING") {
      badges.push(release);
    }
    return Array.from(new Set(badges));
  }

  function readCompareSelection() {
    try {
      const raw = localStorage.getItem(STORAGE_KEYS.COMPARE_QUEUE);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed.slice(0, 4) : [];
    } catch (error) {
      return [];
    }
  }

  function writeCompareSelection(selection) {
    try {
      localStorage.setItem(STORAGE_KEYS.COMPARE_QUEUE, JSON.stringify(selection));
    } catch (error) {
      /* noop */
    }
  }

  function handleLogoFallback(wrapper, name) {
    if (!wrapper) return;
    wrapper.classList.add("logo-fallback");
    wrapper.innerHTML = "";
    const placeholder = document.createElement("span");
    placeholder.className = "logo-placeholder";
    placeholder.textContent = initials(name);
    wrapper.appendChild(placeholder);
  }

  function initials(name = "") {
    return name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((word) => word[0])
      .join("")
      .toUpperCase();
  }

  function fuzzyScore(text, query) {
    if (!query) return 1;
    let score = 0;
    let j = 0;
    for (let i = 0; i < text.length && j < query.length; i++) {
      if (text[i] === query[j]) {
        score += 2;
        j++;
      } else if (text[i] === " " && text[i] !== query[j]) {
        score += 0.1;
      }
    }
    return j === query.length ? score : 0;
  }

  function debounce(fn, wait = 150) {
    let timeout;
    return (...args) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => fn(...args), wait);
    };
  }

  function isFileProtocol() {
    return typeof window !== "undefined" && window.location.protocol === "file:";
  }

  function clone(data) {
    return JSON.parse(JSON.stringify(data));
  }

  function assignLogo(img, wrapper, distro) {
    img.dataset.domain = extractDomain(distro.website || "");
    const sources = getLogoSources(distro);
    if (!sources.length) {
      handleLogoFallback(wrapper, distro.name);
      return;
    }
    let attempt = 0;
    const tryNext = () => {
      if (attempt < sources.length) {
        img.src = sources[attempt++];
      } else {
        img.removeEventListener("error", tryNext);
        handleLogoFallback(wrapper, distro.name);
      }
    };
    img.addEventListener("error", tryNext);
    tryNext();
  }

  function getLogoSources(distro = {}) {
    const sources = [];
    if (distro.logo) {
      sources.push(distro.logo);
    }
    const domain = extractDomain(distro.website || "");
    if (domain) {
      sources.push(`${CLEARBIT_BASE}${domain}`);
    }
    return sources;
  }

  function extractDomain(url = "") {
    try {
      return new URL(url).hostname.replace(/^www\./, "");
    } catch (error) {
      return "";
    }
  }

  function formatHardware(hw) {
    if (!hw) return "&mdash;";
    const parts = [];
    if (hw.cpu) parts.push(`CPU: ${hw.cpu}`);
    if (hw.ram) parts.push(`RAM: ${hw.ram}`);
    if (hw.storage) parts.push(`Storage: ${hw.storage}`);
    return escapeHTML(parts.join(" | ") || "&mdash;");
  }

  function formatBenchmarks(benchmarks = {}) {
    const pieces = [];
    if (benchmarks.boot_time) pieces.push(`Boot: ${benchmarks.boot_time}`);
    if (benchmarks.resource_usage) pieces.push(`Resource: ${benchmarks.resource_usage}`);
    if (benchmarks.stability_score) pieces.push(`Stability: ${benchmarks.stability_score}/10`);
    if (benchmarks.beginner_score) pieces.push(`Beginner: ${benchmarks.beginner_score}/10`);
    if (benchmarks.power_user_score) pieces.push(`Power: ${benchmarks.power_user_score}/10`);
    return escapeHTML(pieces.join(" | ") || "&mdash;");
  }

  function formatList(list = []) {
    if (!list.length) return "&mdash;";
    return `<ul>${list.map((item) => `<li>${escapeHTML(item)}</li>`).join("")}</ul>`;
  }

  function escapeHTML(value = "") {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }
})();



