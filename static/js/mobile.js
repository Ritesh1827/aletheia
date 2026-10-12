/* TrustTrace mobile interactions: drawer, tabbar, tables->cards, share, sticky states. */
(function () {
  "use strict";

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

  // ---- Drawer: close on ESC, scrim click, nav click; lock body scroll ----
  function shell() { return $(".shell"); }
  function setNav(open) {
    var s = shell();
    if (!s) return;
    // Alpine owns navOpen if present; keep DOM class in sync both ways.
    s.classList.toggle("nav-open", !!open);
    document.body.classList.toggle("nav-locked", !!open);
    var btn = $('[data-nav-toggle]');
    if (btn) btn.setAttribute("aria-expanded", open ? "true" : "false");
  }
  function isNavOpen() {
    var s = shell();
    return !!(s && s.classList.contains("nav-open"));
  }

  document.addEventListener("click", function (ev) {
    var t = ev.target instanceof Element ? ev.target : null;
    if (!t) return;
    if (t.closest("[data-nav-toggle]")) {
      ev.preventDefault();
      setNav(!isNavOpen());
      return;
    }
    if (t.closest("[data-nav-close]") || t.closest(".nav-scrim")) {
      setNav(false);
      return;
    }
    // Any sidebar nav link closes the drawer on mobile.
    if (t.closest(".sidebar a.nav-item") && window.innerWidth <= 900) {
      setNav(false);
    }
    // Mobile search toggle
    if (t.closest("[data-search-toggle]")) {
      var row = $(".searchbar--mobile");
      if (row) {
        var opening = !row.classList.contains("open");
        row.classList.toggle("open", opening);
        t.closest("[data-search-toggle]").setAttribute("aria-expanded", opening ? "true" : "false");
        if (opening) {
          var input = row.querySelector("input");
          if (input) setTimeout(function () { input.focus({ preventScroll: true }); }, 60);
        }
      }
    }
    // Back to top
    if (t.closest("[data-to-top]")) {
      window.scrollTo({ top: 0, behavior: "prefers-reduced-motion" in window ? "auto" : "smooth" });
      // smooth unless reduced motion
      if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        window.scrollTo(0, 0);
      }
    }
    // Share (Web Share API with clipboard fallback)
    if (t.closest("[data-share]")) {
      var el = t.closest("[data-share]");
      var title = el.getAttribute("data-share-title") || document.title;
      var text = el.getAttribute("data-share-text") || "";
      var url = el.getAttribute("data-share-url") || location.href;
      if (navigator.share) {
        navigator.share({ title: title, text: text, url: url }).catch(function () {});
      } else if (window.copyText) {
        window.copyText(url, el);
      }
    }
  });

  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape" && isNavOpen()) setNav(false);
  });

  // Keep Alpine x-data navOpen in sync if Alpine is present.
  // Alpine toggles the class via :class; observe it to manage scroll lock.
  function observeShell() {
    var s = shell();
    if (!s || !("MutationObserver" in window)) return;
    var obs = new MutationObserver(function () {
      document.body.classList.toggle("nav-locked", s.classList.contains("nav-open"));
      var btn = $('[data-nav-toggle]');
      if (btn) btn.setAttribute("aria-expanded", s.classList.contains("nav-open") ? "true" : "false");
    });
    obs.observe(s, { attributes: true, attributeFilter: ["class"] });
  }

  // ---- Tables -> cards: copy <th> text into td data-label ----
  function labelTables() {
    $all("table.queue").forEach(function (tbl) {
      var headers = $all("thead th", tbl).map(function (th) { return (th.textContent || "").trim(); });
      if (!headers.length) return;
      $all("tbody tr", tbl).forEach(function (tr) {
        $all("td", tr).forEach(function (td, i) {
          if (!td.hasAttribute("data-label") && headers[i]) td.setAttribute("data-label", headers[i]);
        });
      });
    });
  }

  // ---- Sticky topbar shadow + back-to-top visibility ----
  function onScroll() {
    var bar = $(".topbar");
    if (bar) bar.classList.toggle("is-stuck", window.scrollY > 4);
    var toTop = $("[data-to-top]");
    if (toTop) toTop.classList.toggle("show", window.scrollY > 600);
  }

  // ---- Carousel hint: hide once user scrolls the check rail ----
  function wireCarousels() {
    $all(".check-grid").forEach(function (grid) {
      var hint = grid.parentElement ? grid.parentElement.querySelector(".carousel-hint") : null;
      if (!hint) return;
      grid.addEventListener("scroll", function () {
        if (grid.scrollLeft > 24) hint.style.opacity = "0";
      }, { passive: true });
    });
  }

  // ---- Mark pages with a mobile dock so content gets bottom padding ----
  function markDock() {
    if ($(".verify-dock")) document.body.classList.add("has-dock");
  }

  // ---- htmx partial swaps may inject new tables; re-label them ----
  document.body.addEventListener("htmx:afterSwap", labelTables);

  function init() {
    observeShell();
    labelTables();
    wireCarousels();
    markDock();
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();

  window.TrustTraceMobile = { setNav: setNav, labelTables: labelTables };
})();
