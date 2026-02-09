// utils.js — shared helpers (storage, formatting, safety)

const Utils = (() => {
  // ---------- Number formatting ----------
  function formatNumber(x) {
    if (!Number.isFinite(x)) return "Error";
    const y = Math.round((x + Number.EPSILON) * 1e12) / 1e12;
    if (Math.abs(y) >= 1e12) return y.toExponential(6);
    return String(y);
  }

  // ---------- String helpers ----------
  function clamp(str, max = 140) {
    return str.length > max ? str.slice(0, max) + "…" : str;
  }

  // ---------- LocalStorage ----------
  function save(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
  }

  function load(key, fallback) {
    try {
      const v = JSON.parse(localStorage.getItem(key));
      return v === null || v === undefined ? fallback : v;
    } catch {
      return fallback;
    }
  }

  // ---------- History ----------
  const HIST_KEY = "calc_history";
  function addHistory(expr, res) {
    const list = load(HIST_KEY, []);
    list.unshift({ expr, res, t: Date.now() });
    save(HIST_KEY, list.slice(0, 50));
  }

  function getHistory() {
    return load(HIST_KEY, []);
  }

  function clearHistory() {
    save(HIST_KEY, []);
  }

  // ---------- Theme ----------
  const THEME_KEY = "calc_theme";
  function setTheme(theme) {
    if (theme === "light") {
      document.documentElement.setAttribute("data-theme", "light");
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
    save(THEME_KEY, theme);
  }

  function getTheme() {
    return load(THEME_KEY, "dark");
  }

  // ---------- Memory ----------
  const MEM_KEY = "calc_memory";
  function getMemory() {
    return load(MEM_KEY, 0);
  }

  function setMemory(v) {
    save(MEM_KEY, v);
  }

  return {
    formatNumber,
    clamp,
    save,
    load,
    addHistory,
    getHistory,
    clearHistory,
    setTheme,
    getTheme,
    getMemory,
    setMemory
  };
})();
