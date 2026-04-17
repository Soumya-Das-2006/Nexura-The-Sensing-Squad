/**
 * translator.js — Nexura Multi-Language Translation System v3
 * ─────────────────────────────────────────────────────────────
 * Features:
 *  • Full DOM text-node scan with smart filtering
 *  • Placeholder translation (input, textarea)
 *  • Batched API requests (max 50 per call)
 *  • Parallel chunk dispatch (up to 3 concurrent)
 *  • localStorage cache per language
 *  • Restore original English on lang switch
 *  • Text-to-Speech with start / stop toggle
 *  • Auto-detect browser language
 *  • Premium loading bar + slide-in error toast
 *  • ARIA / keyboard accessible
 */

(function () {
  "use strict";

  /* ══════════════════════════════════════════════════════════════
     1. Configuration
  ══════════════════════════════════════════════════════════════ */

  const LANGUAGES = [
    { code: "en", name: "English",   native: "English",     flag: "🇬🇧" },
    { code: "hi", name: "Hindi",     native: "हिंदी",        flag: "🇮🇳" },
    { code: "gu", name: "Gujarati",  native: "ગુજરાતી",      flag: "🇮🇳" },
    { code: "bn", name: "Bengali",   native: "বাংলা",        flag: "🇧🇩" },
    { code: "ta", name: "Tamil",     native: "தமிழ்",        flag: "🇮🇳" },
    { code: "te", name: "Telugu",    native: "తెలుగు",       flag: "🇮🇳" },
    { code: "mr", name: "Marathi",   native: "मराठी",        flag: "🇮🇳" },
    { code: "kn", name: "Kannada",   native: "ಕನ್ನಡ",        flag: "🇮🇳" },
    { code: "ml", name: "Malayalam", native: "മലയാളം",       flag: "🇮🇳" },
    { code: "pa", name: "Punjabi",   native: "ਪੰਜਾਬੀ",      flag: "🇮🇳" },
    { code: "ur", name: "Urdu",      native: "اردو",          flag: "🇵🇰" },
    { code: "or", name: "Odia",      native: "ଓଡ଼ିଆ",         flag: "🇮🇳" },
    { code: "as", name: "Assamese",  native: "অসমীয়া",      flag: "🇮🇳" },
  ];

  const LANG_MAP           = new Map(LANGUAGES.map((l) => [l.code, l]));
  const STORAGE_KEY        = "selectedLanguage";
  const CACHE_PREFIX       = "translation_cache_v3_";
  const MAX_PER_BATCH      = 50;
  const MAX_NODES          = 5000;
  const MAX_UNCACHED       = 3000;
  const MAX_CONCURRENT     = 3;
  const ENDPOINT           =
    document.body?.dataset?.translateEndpoint ||
    window.TRANSLATE_ENDPOINT ||
    "/translate/";

  /* ══════════════════════════════════════════════════════════════
     2. State
  ══════════════════════════════════════════════════════════════ */

  const originalTextByNode        = new Map(); // WeakMap can't iterate; Map is fine here
  const originalPlaceholderByEl   = new Map();
  let   _ttsActive                = false;
  let   _currentLang              = "en";
  let   _toastTimer               = null;

  /* ══════════════════════════════════════════════════════════════
     3. Utility helpers
  ══════════════════════════════════════════════════════════════ */

  function getCsrfToken() {
    const val   = `; ${document.cookie}`;
    const parts = val.split("; csrftoken=");
    return parts.length === 2 ? parts.pop().split(";").shift() : "";
  }

  function loadCache(lang) {
    try {
      const raw = localStorage.getItem(`${CACHE_PREFIX}${lang}`);
      return raw ? JSON.parse(raw) : {};
    } catch {
      return {};
    }
  }

  function saveCache(lang, data) {
    try {
      localStorage.setItem(`${CACHE_PREFIX}${lang}`, JSON.stringify(data));
    } catch { /* quota exceeded – ignore */ }
  }

  function chunkArray(arr, size) {
    const chunks = [];
    for (let i = 0; i < arr.length; i += size) {
      chunks.push(arr.slice(i, i + size));
    }
    return chunks;
  }

  function shouldTranslate(text) {
    if (!text) return false;
    const t = text.replace(/\s+/g, " ").trim();
    return t.length >= 2 && t.length <= 800 && /[A-Za-z]/.test(t);
  }

  /* ══════════════════════════════════════════════════════════════
     4. DOM Scanning
  ══════════════════════════════════════════════════════════════ */

  const SKIP_TAGS = new Set(["SCRIPT", "STYLE", "NOSCRIPT", "CODE", "PRE",
                              "IFRAME", "SVG", "MATH", "TEXTAREA"]);

  function isVisible(el) {
    if (!el) return false;
    if (el.closest("[data-no-translate]")) return false;
    try {
      return el.getClientRects().length > 0;
    } catch {
      return false;
    }
  }

  function collectTextNodes() {
    const nodes   = [];
    const visited = new Set();

    function walk(root) {
      if (!root || nodes.length >= MAX_NODES) return;
      if (!isVisible(root)) return;

      const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
      while (walker.nextNode()) {
        if (nodes.length >= MAX_NODES) break;
        const node   = walker.currentNode;
        if (visited.has(node)) continue;
        const parent = node.parentElement;
        if (!parent || SKIP_TAGS.has(parent.tagName)) continue;

        const orig = originalTextByNode.get(node) ?? node.nodeValue;
        if (!originalTextByNode.has(node)) originalTextByNode.set(node, orig);
        if (!shouldTranslate(orig)) continue;

        visited.add(node);
        nodes.push({ node, originalText: orig });
      }
    }

    // Preferred roots first
    const roots = [
      ...document.querySelectorAll(".translatable"),
      document.querySelector("#header"),
      document.querySelector("#topbar"),
      document.querySelector("header"),
      document.querySelector("main"),
      document.querySelector("#content"),
      document.querySelector(".content-wrapper"),
      document.querySelector("#footer"),
      document.querySelector("footer"),
      document.body,
    ].filter(Boolean);

    roots.forEach(walk);
    return nodes;
  }

  function collectPlaceholders() {
    const items = [];
    document.querySelectorAll("input[placeholder], textarea[placeholder]").forEach((el) => {
      if (el.closest("[data-no-translate]")) return;
      if (
        el.dataset.translatePlaceholder !== "true" &&
        !el.classList.contains("translatable")
      ) return;

      const orig = originalPlaceholderByEl.get(el) ?? el.getAttribute("placeholder") ?? "";
      if (!originalPlaceholderByEl.has(el)) originalPlaceholderByEl.set(el, orig);
      if (!shouldTranslate(orig)) return;
      items.push({ element: el, originalText: orig });
    });
    return items;
  }

  /* ══════════════════════════════════════════════════════════════
     5. Loading Indicator
  ══════════════════════════════════════════════════════════════ */

  function setLoading(active) {
    const el = document.getElementById("translation-loading");
    if (!el) return;
    if (active) {
      el.innerHTML = `
        <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
        <span>Translating…</span>`;
      el.classList.remove("tl-error");
      el.classList.add("show");
    } else {
      el.classList.remove("show");
    }
  }

  function showToast(message, isError = true) {
    const el = document.getElementById("translation-loading");
    if (!el) return;

    clearTimeout(_toastTimer);
    el.classList.remove("show");

    // Slide-in toast via tl-toast element (if present)
    const toast = document.getElementById("tl-toast");
    if (toast) {
      toast.querySelector(".tl-toast-msg").textContent = message;
      toast.classList.add("show");
      _toastTimer = setTimeout(() => toast.classList.remove("show"), 3500);
    } else {
      // Fallback: repurpose the loading bar briefly
      el.innerHTML = `<i class="bi bi-exclamation-triangle-fill me-1"></i><span>${message}</span>`;
      el.classList.add("show", "tl-error");
      _toastTimer = setTimeout(() => el.classList.remove("show", "tl-error"), 3000);
    }
  }

  /* ══════════════════════════════════════════════════════════════
     6. API
  ══════════════════════════════════════════════════════════════ */

  async function apiTranslate(texts, lang, attempt = 0) {
    const timeout = attempt === 0 ? 30_000 : 45_000;
    const ctrl    = new AbortController();
    const tid     = setTimeout(() => ctrl.abort("timeout"), timeout);

    try {
      const res = await fetch(ENDPOINT, {
        method:  "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken":  getCsrfToken(),
        },
        body:   JSON.stringify({ target_lang: lang, texts }),
        signal: ctrl.signal,
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      if (err?.name === "AbortError" && attempt === 0 && texts.length > 1) {
        // Split and retry
        const mid = Math.ceil(texts.length / 2);
        const [lRes, rRes] = await Promise.all([
          apiTranslate(texts.slice(0, mid), lang, 1),
          apiTranslate(texts.slice(mid),    lang, 1),
        ]);
        return {
          fallback:     !!(lRes.fallback || rRes.fallback),
          translations: [...(lRes.translations ?? texts.slice(0, mid)),
                         ...(rRes.translations ?? texts.slice(mid))],
        };
      }
      if (err?.name === "AbortError") {
        return { fallback: true, timeout: true, translations: texts };
      }
      throw err;
    } finally {
      clearTimeout(tid);
    }
  }

  /* ══════════════════════════════════════════════════════════════
     7. Core Translation Orchestrator
  ══════════════════════════════════════════════════════════════ */

  async function applyLanguage(lang) {
    const code = LANG_MAP.has(lang) ? lang : "en";
    _currentLang = code;

    localStorage.setItem(STORAGE_KEY, code);
    document.documentElement.setAttribute("lang", code);
    _syncSwitcherUI(code);

    if (code === "en") {
      _restoreEnglish();
      return;
    }

    const textNodes   = collectTextNodes();
    const placeholders = collectPlaceholders();
    const cache        = loadCache(code);

    // Build full entry list
    const allEntries = [
      ...textNodes.map((e)   => ({ type: "text",        ref: e.node,    orig: e.originalText })),
      ...placeholders.map((e) => ({ type: "placeholder", ref: e.element, orig: e.originalText })),
    ];

    // Find what's missing from cache
    const missing  = [];
    const missedSet = new Set();
    allEntries.forEach(({ orig }) => {
      const clean = orig.replace(/\s+/g, " ").trim();
      if (!clean) return;
      if (!cache[clean] && !missedSet.has(clean)) {
        missedSet.add(clean);
        missing.push(clean);
      }
    });

    setLoading(true);
    try {
      let hadFailure = false;

      if (missing.length) {
        const limited = missing.slice(0, MAX_UNCACHED);
        const chunks  = chunkArray(limited, MAX_PER_BATCH);

        for (let i = 0; i < chunks.length; i += MAX_CONCURRENT) {
          const group   = chunks.slice(i, i + MAX_CONCURRENT);
          const results = await Promise.all(group.map((c) => apiTranslate(c, code)));

          group.forEach((chunk, gi) => {
            const data = results[gi] ?? {};
            if (data.fallback) {
              hadFailure = true;
              if (data.timeout) showToast("Network slow — partial translation applied.");
              return;
            }
            const translated = data.translations ?? [];
            chunk.forEach((src, si) => {
              cache[src] = translated[si] ?? src;
            });
          });
        }

        if (missing.length > MAX_UNCACHED) {
          showToast("Large page: some text was skipped. Reload to translate more.");
        }
        saveCache(code, cache);
        if (hadFailure) showToast("Some text could not be translated right now.");
      }

      // Apply to DOM
      allEntries.forEach(({ type, ref, orig }) => {
        const clean = orig.replace(/\s+/g, " ").trim();
        const result = cache[clean] ?? orig;
        if (type === "text") {
          ref.nodeValue = result;
        } else {
          ref.setAttribute("placeholder", result);
        }
      });
    } catch (err) {
      showToast("Translation service unavailable. Please try again.");
      console.warn("[Nexura Translate] Error:", err);
    } finally {
      setLoading(false);
    }
  }

  function _restoreEnglish() {
    originalTextByNode.forEach((orig, node) => {
      node.nodeValue = orig;
    });
    originalPlaceholderByEl.forEach((orig, el) => {
      el.setAttribute("placeholder", orig);
    });
  }

  /* ══════════════════════════════════════════════════════════════
     8. Language Detection
  ══════════════════════════════════════════════════════════════ */

  function getDefaultLanguage() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && LANG_MAP.has(saved)) return saved;
    const preferred = (document.body?.dataset?.defaultLanguage || "").toLowerCase();
    if (preferred && LANG_MAP.has(preferred)) return preferred;
    const browser = (navigator.language || "en").slice(0, 2).toLowerCase();
    return LANG_MAP.has(browser) ? browser : "en";
  }

  /* ══════════════════════════════════════════════════════════════
     9. UI Sync
  ══════════════════════════════════════════════════════════════ */

  function _syncSwitcherUI(code) {
    // Desktop custom dropdown: mark active option
    document.querySelectorAll(".tl-lang-option").forEach((btn) => {
      const active = btn.dataset.lang === code;
      btn.classList.toggle("active", active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });

    // Mobile sheet: mark active card
    document.querySelectorAll(".tl-sheet-lang-btn").forEach((btn) => {
      const active = btn.dataset.lang === code;
      btn.classList.toggle("active", active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });

    // Update desktop trigger label
    const triggerLabel = document.getElementById("tl-trigger-label");
    if (triggerLabel) {
      const meta = LANG_MAP.get(code);
      triggerLabel.textContent = meta ? `${meta.flag} ${meta.native}` : "🌐 English";
    }

    // Update mobile trigger label
    const mobileTriggerLabel = document.getElementById("tl-mobile-trigger-label");
    if (mobileTriggerLabel) {
      const meta = LANG_MAP.get(code);
      mobileTriggerLabel.textContent = meta ? `${meta.flag} ${meta.native}` : "🌐";
    }

    // Legacy: plain <select> fallback
    const sel = document.getElementById("language-select-desktop");
    if (sel) sel.value = code;
  }

  /* ══════════════════════════════════════════════════════════════
     10. Desktop Dropdown
  ══════════════════════════════════════════════════════════════ */

  function initDesktopDropdown() {
    const trigger = document.getElementById("tl-desktop-trigger");
    const menu    = document.getElementById("tl-desktop-menu");
    if (!trigger || !menu) return;

    // Build language options
    const scroll = menu.querySelector(".tl-menu-scroll");
    if (scroll) {
      scroll.innerHTML = "";
      LANGUAGES.forEach((lang) => {
        const btn = document.createElement("button");
        btn.type               = "button";
        btn.className          = "tl-lang-option";
        btn.dataset.lang       = lang.code;
        btn.setAttribute("role", "option");
        btn.setAttribute("aria-pressed", "false");
        btn.innerHTML = `
          <span class="tl-flag">${lang.flag}</span>
          <span class="tl-native">${lang.native}</span>
          <span class="tl-code">${lang.code.toUpperCase()}</span>
          <i class="bi bi-check2 tl-tick"></i>`;
        btn.addEventListener("click", async () => {
          closeDesktopMenu();
          await applyLanguage(lang.code);
        });
        scroll.appendChild(btn);
      });
    }

    // Open / close
    trigger.addEventListener("click", (e) => {
      e.stopPropagation();
      const open = menu.classList.toggle("open");
      trigger.setAttribute("aria-expanded", open ? "true" : "false");
    });

    document.addEventListener("click", (e) => {
      if (!menu.contains(e.target) && !trigger.contains(e.target)) {
        closeDesktopMenu();
      }
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeDesktopMenu();
    });
  }

  function closeDesktopMenu() {
    const trigger = document.getElementById("tl-desktop-trigger");
    const menu    = document.getElementById("tl-desktop-menu");
    if (menu)    menu.classList.remove("open");
    if (trigger) trigger.setAttribute("aria-expanded", "false");
  }

  /* ══════════════════════════════════════════════════════════════
     11. Mobile Bottom Sheet
  ══════════════════════════════════════════════════════════════ */

  function initMobileSheet() {
    const trigger  = document.getElementById("mobile-language-trigger");
    const overlay  = document.getElementById("tl-sheet-overlay");
    const sheet    = document.getElementById("mobile-language-menu");
    const closeBtn = document.getElementById("tl-sheet-close");
    const grid     = document.getElementById("mobile-language-options");

    if (!trigger || !overlay || !sheet || !grid) return;

    // Build language grid cards
    grid.innerHTML = "";
    LANGUAGES.forEach((lang) => {
      const btn = document.createElement("button");
      btn.type               = "button";
      btn.className          = "tl-sheet-lang-btn mobile-language-option";
      btn.dataset.lang       = lang.code;
      btn.setAttribute("aria-pressed", "false");
      btn.innerHTML = `
        <span class="tl-flag">${lang.flag}</span>
        <span class="tl-native">${lang.native}</span>
        <span class="tl-en-name">${lang.name}</span>`;
      btn.addEventListener("click", async () => {
        closeMobileSheet();
        await applyLanguage(lang.code);
      });
      grid.appendChild(btn);
    });

    // Open sheet
    trigger.addEventListener("click", openMobileSheet);
    // Close via overlay / close button
    overlay.addEventListener("click",  closeMobileSheet);
    if (closeBtn) closeBtn.addEventListener("click", closeMobileSheet);
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeMobileSheet();
    });
  }

  function openMobileSheet() {
    const overlay = document.getElementById("tl-sheet-overlay");
    const sheet   = document.getElementById("mobile-language-menu");
    if (overlay) overlay.classList.add("open");
    if (sheet)   { sheet.classList.add("open"); sheet.setAttribute("aria-hidden", "false"); }
  }

  function closeMobileSheet() {
    const overlay = document.getElementById("tl-sheet-overlay");
    const sheet   = document.getElementById("mobile-language-menu");
    if (overlay) overlay.classList.remove("open");
    if (sheet)   { sheet.classList.remove("open"); sheet.setAttribute("aria-hidden", "true"); }
  }

  /* ══════════════════════════════════════════════════════════════
     12. Text-to-Speech
  ══════════════════════════════════════════════════════════════ */

  function initTTS() {
    const btnIds = ["tts-toggle-desktop", "tts-toggle-mobile"];
    btnIds.forEach((id) => {
      const btn = document.getElementById(id);
      if (!btn) return;
      btn.addEventListener("click", toggleTTS);
    });
  }

  function toggleTTS() {
    if (!("speechSynthesis" in window)) {
      showToast("Text-to-Speech is not supported in this browser.", false);
      return;
    }

    if (_ttsActive) {
      window.speechSynthesis.cancel();
      _ttsActive = false;
      _updateTTSButtonState(false);
      return;
    }

    const text = _getPageText();
    if (!text) return;

    const utt  = new SpeechSynthesisUtterance(text);
    utt.lang   = _currentLang;
    utt.rate   = 0.92;
    utt.onend  = () => { _ttsActive = false; _updateTTSButtonState(false); };
    utt.onerror = () => { _ttsActive = false; _updateTTSButtonState(false); };

    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utt);
    _ttsActive = true;
    _updateTTSButtonState(true);
  }

  function _getPageText() {
    const roots = [
      ...document.querySelectorAll(".translatable"),
      document.querySelector("main"),
      document.querySelector(".content-wrapper"),
    ].filter(Boolean);

    return roots
      .map((el) => el.textContent.trim())
      .filter(Boolean)
      .join(". ")
      .slice(0, 10_000);
  }

  function _updateTTSButtonState(speaking) {
    ["tts-toggle-desktop", "tts-toggle-mobile"].forEach((id) => {
      const btn = document.getElementById(id);
      if (!btn) return;
      btn.classList.toggle("speaking", speaking);
      btn.setAttribute("aria-label", speaking ? "Stop reading" : "Read page aloud");
      const icon = btn.querySelector("i");
      if (icon) {
        icon.className = speaking
          ? "bi bi-stop-circle-fill"
          : "bi bi-volume-up-fill";
      }
    });
  }

  /* ══════════════════════════════════════════════════════════════
     13. Legacy <select> Support
  ══════════════════════════════════════════════════════════════ */

  function initLegacySelect() {
    const sel = document.getElementById("language-select-desktop");
    if (!sel) return;
    sel.addEventListener("change", (e) => applyLanguage(e.target.value));
  }

  /* ══════════════════════════════════════════════════════════════
     14. Bootstrap
  ══════════════════════════════════════════════════════════════ */

  document.addEventListener("DOMContentLoaded", async () => {
    initDesktopDropdown();
    initMobileSheet();
    initTTS();
    initLegacySelect();

    const lang = getDefaultLanguage();
    await applyLanguage(lang);
  });

})();
