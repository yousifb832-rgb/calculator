// app.js — Pro controller (UI + MathEngine + Utils)

const $ = (id) => document.getElementById(id);

const expressionEl = $("expression");
const resultEl = $("result");
const statusEl = $("status");
const memoryEl = $("memory");
const historyList = $("historyList");

const angleBtn = $("angleBtn");
const themeBtn = $("themeBtn");
const clearHistBtn = $("clearHistBtn");

const buttons = document.querySelectorAll(".btn");

let expression = "";
let ans = 0;
let memory = Utils.getMemory();

// ---------- Init ----------
memoryEl.textContent = `M: ${Utils.formatNumber(memory)}`;

const savedTheme = Utils.getTheme();
Utils.setTheme(savedTheme);
themeBtn.textContent = savedTheme === "light" ? "Light" : "Dark";

let angleMode = "DEG";
MathEngine.setAngleMode(angleMode);
angleBtn.textContent = angleMode;

renderHistory();
setStatus("Ready");

// ---------- Helpers ----------
function setStatus(msg) {
  statusEl.textContent = msg;
}

function updateDisplay() {
  expressionEl.textContent = Utils.clamp(expression);
}

function clearAll() {
  expression = "";
  resultEl.textContent = "0";
  updateDisplay();
  setStatus("Cleared");
}

function backspace() {
  expression = expression.slice(0, -1);
  updateDisplay();
}

function evaluate() {
  if (!expression) return;
  try {
    const value = MathEngine.evaluate(expression, { ans });
    ans = value;
    const out = Utils.formatNumber(value);
    resultEl.textContent = out;
    Utils.addHistory(expression, out);
    renderHistory();
    expression = out;
    updateDisplay();
    setStatus("OK");
  } catch (e) {
    resultEl.textContent = "Error";
    setStatus("Error");
  }
}

// ---------- History ----------
function renderHistory() {
  const list = Utils.getHistory();
  historyList.innerHTML = "";

  if (!list.length) {
    historyList.innerHTML = `<div class="item"><div class="a">No history</div><div class="b">—</div></div>`;
    return;
  }

  for (const it of list) {
    const div = document.createElement("div");
    div.className = "item";
    div.innerHTML = `
      <div class="a">${it.expr}</div>
      <div class="b">${it.res}</div>
    `;
    div.onclick = () => {
      expression = it.expr;
      resultEl.textContent = it.res;
      updateDisplay();
      setStatus("Loaded from history");
    };
    historyList.appendChild(div);
  }
}

// ---------- Buttons ----------
buttons.forEach(btn => {
  btn.addEventListener("click", () => {
    const { num, op, fn, act, mem } = btn.dataset;

    if (num) {
      expression += num;
      return updateDisplay();
    }

    if (op) {
      expression += op;
      return updateDisplay();
    }

    if (fn) {
      if (fn === "fact") expression += "!";
      else if (fn === "pow") expression += "^";
      else expression += fn + "(";
      return updateDisplay();
    }

    if (act) {
      if (act === "clear") return clearAll();
      if (act === "back") return backspace();
      if (act === "dot") { expression += "."; return updateDisplay(); }
      if (act === "(" || act === ")") { expression += act; return updateDisplay(); }
      if (act === "pi") { expression += "pi"; return updateDisplay(); }
      if (act === "e") { expression += "e"; return updateDisplay(); }
      if (act === "ans") { expression += "ans"; return updateDisplay(); }
      if (act === "neg") { expression += "-"; return updateDisplay(); }
      if (act === "eq") return evaluate();
    }

    if (mem) {
      const cur = Number(resultEl.textContent);
      if (mem === "mc") memory = 0;
      if (mem === "mr") expression += Utils.formatNumber(memory);
      if (mem === "mplus") memory += Number.isFinite(cur) ? cur : 0;
      if (mem === "mminus") memory -= Number.isFinite(cur) ? cur : 0;
      Utils.setMemory(memory);
      memoryEl.textContent = `M: ${Utils.formatNumber(memory)}`;
      setStatus(`Memory ${mem.toUpperCase()}`);
    }
  });
});

// ---------- Controls ----------
angleBtn.onclick = () => {
  angleMode = angleMode === "DEG" ? "RAD" : "DEG";
  MathEngine.setAngleMode(angleMode);
  angleBtn.textContent = angleMode;
  setStatus(`Angle: ${angleMode}`);
};

themeBtn.onclick = () => {
  const cur = Utils.getTheme();
  const next = cur === "dark" ? "light" : "dark";
  Utils.setTheme(next);
  themeBtn.textContent = next === "light" ? "Light" : "Dark";
};

clearHistBtn.onclick = () => {
  Utils.clearHistory();
  renderHistory();
  setStatus("History cleared");
};

// ---------- Keyboard ----------
document.addEventListener("keydown", (e) => {
  const k = e.key;

  if (k >= "0" && k <= "9") { expression += k; updateDisplay(); }
  else if ("+-*/%^".includes(k)) { expression += k; updateDisplay(); }
  else if (k === ".") { expression += "."; updateDisplay(); }
  else if (k === "(" || k === ")") { expression += k; updateDisplay(); }
  else if (k === "Enter" || k === "=") { e.preventDefault(); evaluate(); }
  else if (k === "Backspace") backspace();
  else if (k === "Escape") clearAll();
});
