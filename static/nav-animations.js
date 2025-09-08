let navAnimationTimeout = null;
let navOverlayEl = null;

function toggleNavMenu() {
  const dropdown = document.getElementById("navDropdown");
  const toggleButton = document.querySelector(".nav-menu-toggle");

  if (dropdown.classList.contains("active")) {
    closeNavMenu();
  } else {
    openNavMenu();
  }
}

function openNavMenu() {
  const dropdown = document.getElementById("navDropdown");
  const toggleButton = document.querySelector(".nav-menu-toggle");
  const isMobile =
    window.matchMedia && window.matchMedia("(max-width: 768px)").matches;

  if (navAnimationTimeout) {
    clearTimeout(navAnimationTimeout);
    navAnimationTimeout = null;
  }

  dropdown.classList.remove("closing");

  dropdown.classList.add("active");
  toggleButton.classList.add("active");

  if (isMobile) {
    if (!navOverlayEl) {
      navOverlayEl = document.createElement("div");
      navOverlayEl.className = "nav-overlay";
      navOverlayEl.addEventListener("click", () => {
        closeNavMenu();
      });
      document.body.appendChild(navOverlayEl);
    }
    requestAnimationFrame(() => {
      navOverlayEl.classList.add("active");
    });
    document.body.classList.add("no-scroll");
  }

  const menuItems = dropdown.querySelectorAll("a");
  menuItems.forEach((item) => {
    item.style.animation = "none";
    item.offsetHeight;
    item.style.animation = null;
  });
}

function closeNavMenu() {
  const dropdown = document.getElementById("navDropdown");
  const toggleButton = document.querySelector(".nav-menu-toggle");
  const isMobile =
    window.matchMedia && window.matchMedia("(max-width: 768px)").matches;

  dropdown.classList.add("closing");
  toggleButton.classList.remove("active");

  navAnimationTimeout = setTimeout(() => {
    dropdown.classList.remove("active", "closing");
    navAnimationTimeout = null;
  }, 300);

  if (isMobile && navOverlayEl) {
    navOverlayEl.classList.remove("active");
    setTimeout(() => {
      if (navOverlayEl && navOverlayEl.parentNode) {
        navOverlayEl.parentNode.removeChild(navOverlayEl);
        navOverlayEl = null;
      }
    }, 250);
    document.body.classList.remove("no-scroll");
  }
}

function setupNavMenuOutsideClick() {
  document.addEventListener("click", function (e) {
    const navMenu = document.querySelector(".nav-menu");
    const dropdown = document.getElementById("navDropdown");
    const toggleButton = document.querySelector(".nav-menu-toggle");

    if (e.target.closest(".nav-dropdown a")) {
      return;
    }

    if (!navMenu.contains(e.target)) {
      if (dropdown.classList.contains("active")) {
        closeNavMenu();
      }
    }
  });
}

function setupNavMenuEscapeKey() {
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      const dropdown = document.getElementById("navDropdown");
      if (dropdown.classList.contains("active")) {
        closeNavMenu();
      }
    }
  });
}

function setupNavMenuItemClicks() {}

function setupNavMenuInsideClickShield() {
  const dropdown = document.getElementById("navDropdown");
  if (!dropdown) return;

  const stop = function (e) {
    e.stopPropagation();
  };
  dropdown.addEventListener("click", stop);
  dropdown.addEventListener("touchstart", stop, { passive: true });
}

function initNavMenu() {
  setupNavMenuOutsideClick();
  setupNavMenuEscapeKey();
  setupNavMenuItemClicks();
  setupNavMenuInsideClickShield();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    initNavMenu();
    try {
      if (window.twemoji && typeof window.twemoji.parse === "function") {
        window.twemoji.parse(document.body, {
          folder: "svg",
          ext: ".svg",
          base: "https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/",
          className: "twemoji",
        });
      }
    } catch (e) {}

    try {
      (function enableLenisSmoothScroll() {
        const LENIS_CSS = "https://unpkg.com/lenis@1.3.11/dist/lenis.css";
        const LENIS_JS = "https://unpkg.com/lenis@1.3.11/dist/lenis.min.js";

        if (!document.querySelector("link[data-lenis]")) {
          const link = document.createElement("link");
          link.rel = "stylesheet";
          link.href = LENIS_CSS;
          link.setAttribute("data-lenis", "true");
          document.head.appendChild(link);
        }

        function initLenis() {
          if (!window.Lenis) return;
          try {
            const lenis = new window.Lenis({ lerp: 0.07, smoothWheel: true });
            function raf(time) {
              lenis.raf(time);
              requestAnimationFrame(raf);
            }
            requestAnimationFrame(raf);
          } catch (_) {}
        }

        if (window.Lenis) {
          initLenis();
        } else if (!document.querySelector("script[data-lenis]")) {
          const script = document.createElement("script");
          script.src = LENIS_JS;
          script.async = true;
          script.defer = true;
          script.setAttribute("data-lenis", "true");
          script.onload = initLenis;
          document.head.appendChild(script);
        }
      })();
    } catch (_) {}
  });
} else {
  initNavMenu();
  try {
    if (window.twemoji && typeof window.twemoji.parse === "function") {
      window.twemoji.parse(document.body, {
        folder: "svg",
        ext: ".svg",
        base: "https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/",
        className: "twemoji",
      });
    }
  } catch (e) {}

  try {
    (function enableLenisSmoothScrollImmediate() {
      const LENIS_CSS = "https://unpkg.com/lenis@1.3.11/dist/lenis.css";
      const LENIS_JS = "https://unpkg.com/lenis@1.3.11/dist/lenis.min.js";

      if (!document.querySelector("link[data-lenis]")) {
        const link = document.createElement("link");
        link.rel = "stylesheet";
        link.href = LENIS_CSS;
        link.setAttribute("data-lenis", "true");
        document.head.appendChild(link);
      }

      function initLenis() {
        if (!window.Lenis) return;
        try {
          const lenis = new window.Lenis({ lerp: 0.07, smoothWheel: true });
          function raf(time) {
            lenis.raf(time);
            requestAnimationFrame(raf);
          }
          requestAnimationFrame(raf);
        } catch (_) {}
      }

      if (window.Lenis) {
        initLenis();
      } else if (!document.querySelector("script[data-lenis]")) {
        const script = document.createElement("script");
        script.src = LENIS_JS;
        script.async = true;
        script.defer = true;
        script.setAttribute("data-lenis", "true");
        script.onload = initLenis;
        document.head.appendChild(script);
      }
    })();
  } catch (_) {}
}
