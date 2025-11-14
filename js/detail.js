(() => {
  const CLEARBIT_BASE = "https://logo.clearbit.com/";
  const STORAGE_KEYS =
    window.__BLD_STORAGE_KEYS ||
    Object.freeze({
      RECENTS: "bld::recent",
    });
  const page = document.body;
  if (!page.classList.contains("detail")) {
    return;
  }

  const detailId = page.getAttribute("data-distro");
  let lightboxEscHandler = null;
  enhanceLogo();
  initScreenshots();
  rememberRecentlyViewed(detailId);

  function enhanceLogo() {
    const logo = document.querySelector(".hero-logo img");
    if (!logo) return;
    logo.referrerPolicy = "no-referrer";
    logo.decoding = "async";
    const domain = logo.dataset.domain || "";
    let triedClearbit = false;
    logo.addEventListener("error", () => {
      if (!triedClearbit && domain) {
        triedClearbit = true;
        logo.src = `${CLEARBIT_BASE}${domain}`;
        return;
      }
      swapWithInitials(logo);
    });
  }

  function swapWithInitials(img) {
    const wrapper = img.closest(".hero-logo");
    if (!wrapper || wrapper.dataset.fallback === "true") {
      return;
    }
    wrapper.dataset.fallback = "true";
    const placeholder = document.createElement("span");
    placeholder.className = "logo-placeholder detail";
    placeholder.textContent = initials(wrapper.dataset.name || img.alt || "?");
    img.replaceWith(placeholder);
  }

  function initScreenshots() {
    const nodes = document.querySelectorAll(".screenshot-card, .screenshot-item");
    if (!nodes.length) return;
    nodes.forEach((node) => {
      const src = node.getAttribute("data-full") || node.getAttribute("data-src");
      if (!src) return;
      if (node.classList.contains("screenshot-card")) {
        if (!node.hasAttribute("tabindex")) {
          node.tabIndex = 0;
        }
        node.setAttribute("role", "button");
      }
      node.addEventListener("click", () => openLightbox(src));
      node.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          openLightbox(src);
        }
      });
    });
  }

  function openLightbox(src) {
    if (!src) return;
    closeLightbox();
    const overlay = document.createElement("div");
    overlay.className = "lightbox";
    overlay.tabIndex = -1;
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.innerHTML = `
      <button type="button" aria-label="Close screenshot">&times;</button>
      <img src="${src}" alt="Enlarged screenshot" />
    `;
    overlay.addEventListener("click", (event) => {
      if (event.target === overlay) {
        closeLightbox();
      }
    });
    overlay.querySelector("button").addEventListener("click", closeLightbox);
    document.body.appendChild(overlay);
    overlay.focus();
    lightboxEscHandler = (event) => {
      if (event.key === "Escape") {
        closeLightbox();
      }
    };
    document.addEventListener("keydown", lightboxEscHandler);
  }

  function closeLightbox() {
    const overlay = document.querySelector(".lightbox");
    if (overlay) {
      overlay.remove();
    }
    if (lightboxEscHandler) {
      document.removeEventListener("keydown", lightboxEscHandler);
      lightboxEscHandler = null;
    }
  }

  function rememberRecentlyViewed(id) {
    if (!id) return;
    try {
      const key = STORAGE_KEYS.RECENTS;
      const list = JSON.parse(localStorage.getItem(key) || "[]");
      const filtered = list.filter((entry) => entry.id !== id);
      filtered.unshift({ id, viewedAt: Date.now() });
      localStorage.setItem(key, JSON.stringify(filtered.slice(0, 6)));
    } catch (error) {
      /* noop */
    }
  }

  function initials(text = "") {
    return text
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((word) => word[0])
      .join("")
      .toUpperCase();
  }
})();
