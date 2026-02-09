// math.js — Safe Scientific Math Engine (NO eval)

const MathEngine = (() => {

  let angleMode = "DEG";

  function setAngleMode(mode) {
    angleMode = mode === "RAD" ? "RAD" : "DEG";
  }

  function toRadians(x) {
    return angleMode === "DEG" ? (x * Math.PI / 180) : x;
  }

  // ---------- factorial ----------
  function factorial(n) {
    if (!Number.isInteger(n) || n < 0) return NaN;
    if (n > 170) return Infinity;
    let r = 1;
    for (let i = 2; i <= n; i++) r *= i;
    return r;
  }

  // ---------- tokenizer ----------
  function tokenize(input) {
    const tokens = [];
    let i = 0;

    while (i < input.length) {
      const c = input[i];

      if (/\s/.test(c)) {
        i++;
        continue;
      }

      if (/[0-9.]/.test(c)) {
        let num = c;
        i++;
        while (i < input.length && /[0-9.]/.test(input[i])) {
          num += input[i++];
        }
        tokens.push({ type: "num", value: parseFloat(num) });
        continue;
      }

      if (/[a-z]/i.test(c)) {
        let id = c;
        i++;
        while (i < input.length && /[a-z]/i.test(input[i])) {
          id += input[i++];
        }
        tokens.push({ type: "id", value: id.toLowerCase() });
        continue;
      }

      if ("+-*/%^()!".includes(c)) {
        tokens.push({ type: "op", value: c });
        i++;
        continue;
      }

      throw new Error("Invalid character");
    }

    return tokens;
  }

  // ---------- precedence ----------
  const precedence = {
    "+": 2,
    "-": 2,
    "*": 3,
    "/": 3,
    "%": 3,
    "^": 4,
    "!": 5
  };

  const rightAssociative = { "^": true };

  // ---------- shunting-yard ----------
  function toRPN(tokens) {
    const output = [];
    const stack = [];

    let prev = null;

    for (const t of tokens) {

      if (t.type === "num") {
        output.push(t);
        prev = t;
        continue;
      }

      if (t.type === "id") {
        stack.push(t);
        prev = t;
        continue;
      }

      const op = t.value;

      // unary minus
      if (op === "-" && (!prev || prev.type === "op" && prev.value !== ")")) {
        stack.push({ type: "id", value: "neg" });
        prev = t;
        continue;
      }

      if (op === "(") {
        stack.push(t);
        prev = t;
        continue;
      }

      if (op === ")") {
        while (stack.length && stack[stack.length - 1].value !== "(") {
          output.push(stack.pop());
        }
        stack.pop(); // remove "("
        if (stack.length && stack[stack.length - 1].type === "id") {
          output.push(stack.pop());
        }
        prev = t;
        continue;
      }

      while (
        stack.length &&
        stack[stack.length - 1].value !== "(" &&
        (precedence[stack[stack.length - 1].value] > precedence[op] ||
          (precedence[stack[stack.length - 1].value] === precedence[op] &&
            !rightAssociative[op]))
      ) {
        output.push(stack.pop());
      }

      stack.push(t);
      prev = t;
    }

    while (stack.length) {
      output.push(stack.pop());
    }

    return output;
  }

  // ---------- evaluate RPN ----------
  function evalRPN(rpn, ctx = {}) {
    const stack = [];

    for (const t of rpn) {

      if (t.type === "num") {
        stack.push(t.value);
        continue;
      }

      if (t.type === "id") {
        const x = stack.pop();

        switch (t.value) {
          case "sin": stack.push(Math.sin(toRadians(x))); break;
          case "cos": stack.push(Math.cos(toRadians(x))); break;
          case "tan": stack.push(Math.tan(toRadians(x))); break;
          case "log": stack.push(Math.log10(x)); break;
          case "ln": stack.push(Math.log(x)); break;
          case "sqrt": stack.push(Math.sqrt(x)); break;
          case "neg": stack.push(-x); break;
          case "pi": stack.push(Math.PI); break;
          case "e": stack.push(Math.E); break;
          case "ans": stack.push(ctx.ans ?? 0); break;
          default: throw new Error("Unknown function");
        }
        continue;
      }

      const b = stack.pop();
      const a = stack.pop();

      switch (t.value) {
        case "+": stack.push(a + b); break;
        case "-": stack.push(a - b); break;
        case "*": stack.push(a * b); break;
        case "/": stack.push(b === 0 ? NaN : a / b); break;
        case "%": stack.push(a % b); break;
        case "^": stack.push(Math.pow(a, b)); break;
        case "!": stack.push(factorial(a)); break;
        default: throw new Error("Bad operator");
      }
    }

    if (stack.length !== 1) throw new Error("Invalid expression");
    return stack[0];
  }

  // ---------- public ----------
  function evaluate(expr, ctx = {}) {
    const tokens = tokenize(expr);
    const rpn = toRPN(tokens);
    const value = evalRPN(rpn, ctx);
    if (!Number.isFinite(value)) throw new Error("Math error");
    return value;
  }

  return {
    evaluate,
    setAngleMode
  };

})();
