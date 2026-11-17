/* Mini librería de gráficas en SVG, sin dependencias.
 * Barras horizontales, columnas, líneas y mapa. Todas con tooltip y foco por teclado.
 */
(function () {
  "use strict";
  const NS = "http://www.w3.org/2000/svg";

  // ---------- utilidades ----------
  function el(tag, attrs, parent) {
    const node = document.createElementNS(NS, tag);
    if (attrs) for (const k in attrs) node.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(node);
    return node;
  }
  function txt(parent, x, y, content, attrs) {
    const t = el("text", Object.assign({ x, y }, attrs || {}), parent);
    t.textContent = content;
    return t;
  }
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const fmt = (n, d = 0) =>
    Number(n).toLocaleString("es-CO", { minimumFractionDigits: d, maximumFractionDigits: d });
  function compact(n) {
    if (n === 0) return "0";
    if (Math.abs(n) >= 1e6) return fmt(n / 1e6, n % 1e6 === 0 ? 0 : 1) + " M";
    if (Math.abs(n) >= 1e3) return fmt(n / 1e3, 0) + " mil";
    return fmt(n, Number.isInteger(n) ? 0 : 2);
  }
  function niceStep(raw) {
    const p = Math.pow(10, Math.floor(Math.log10(raw)));
    const f = raw / p;
    return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * p;
  }
  function ticks(min, max, count) {
    const step = niceStep((max - min) / count);
    const start = Math.floor(min / step) * step;
    const out = [];
    for (let v = start; v <= max + step * 0.999; v += step) out.push(+v.toFixed(10));
    return out;
  }
  function measure(svg, s, size, weight) {
    const t = txt(svg, -9999, -9999, s, { "font-size": size, "font-weight": weight || 400 });
    const w = t.getComputedTextLength();
    t.remove();
    return w;
  }
  function svgFor(container, w, h, label) {
    container.innerHTML = "";
    const svg = el("svg", { viewBox: `0 0 ${w} ${h}`, role: "img", "aria-label": label || "" }, container);
    return svg;
  }
  // Barra con extremo de datos redondeado (4 px) y base recta
  function hBarPath(x, y, w, h, r = 4) {
    r = Math.min(r, w, h / 2);
    if (w <= 0) return "";
    return `M${x},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h - r}Q${x + w},${y + h} ${x + w - r},${y + h}H${x}Z`;
  }
  function vBarPath(x, y, w, h, r = 4) {
    r = Math.min(r, h, w / 2);
    if (h <= 0) return "";
    return `M${x},${y + h}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h}Z`;
  }

  // ---------- tooltip ----------
  const tip = document.createElement("div");
  tip.className = "tooltip";
  tip.setAttribute("role", "status");
  document.addEventListener("DOMContentLoaded", () => document.body.appendChild(tip));
  function showTip(x, y, value, label, extra) {
    tip.replaceChildren();
    const v = document.createElement("div"); v.className = "tv"; v.textContent = value;
    const l = document.createElement("div"); l.className = "tl"; l.textContent = label;
    tip.append(v, l);
    if (extra) { const e = document.createElement("div"); e.className = "tx"; e.textContent = extra; tip.append(e); }
    tip.classList.add("show");
    const r = tip.getBoundingClientRect();
    let left = x + 14, top = y - r.height - 10;
    if (left + r.width > window.innerWidth - 8) left = x - r.width - 14;
    if (top < 64) top = y + 16;
    tip.style.left = left + "px";
    tip.style.top = top + "px";
  }
  function hideTip() { tip.classList.remove("show"); }
  function bindHover(hit, mark, getInfo) {
    const on = (e) => {
      mark && mark.classList.add("hover");
      const info = getInfo();
      let x, y;
      if (e && e.clientX !== undefined && e.type !== "focus") { x = e.clientX; y = e.clientY; }
      else { const b = (mark || hit).getBoundingClientRect(); x = b.left + b.width / 2; y = b.top; }
      showTip(x, y, info[0], info[1], info[2]);
    };
    const off = () => { mark && mark.classList.remove("hover"); hideTip(); };
    hit.addEventListener("pointermove", on);
    hit.addEventListener("pointerleave", off);
    hit.addEventListener("focus", on);
    hit.addEventListener("blur", off);
  }

  // ---------- barras horizontales ----------
  function barrasH(container, o) {
    const W = Math.max(container.clientWidth, 280);
    const n = o.values.length;
    const rowH = o.rowH || 36, barH = Math.min(22, rowH - 12);
    const top = 6, H = top + n * rowH + (o.axis ? 24 : 4);
    const svg = svgFor(container, W, H, o.title);
    const labelW = Math.min(W * 0.42, Math.max(...o.labels.map((l) => measure(svg, l, 13.5))) + 14);
    const valueW = Math.max(...o.values.map((v) => measure(svg, (o.fmt || fmt)(v), 13, 600))) + 10;
    const x0 = labelW, plotW = W - x0 - valueW;
    const max = o.max || Math.max(...o.values);
    const ink = css("--ink"), ink2 = css("--ink-2"), axis = css("--axis");
    o.values.forEach((v, i) => {
      const y = top + i * rowH;
      const color = typeof o.color === "function" ? o.color(i, v) : o.color || css("--bar");
      txt(svg, x0 - 12, y + rowH / 2 + 4.5, o.labels[i], { "font-size": 13.5, fill: ink2, "text-anchor": "end" });
      const w = Math.max(0, (plotW * v) / max);
      const mark = el("path", { d: hBarPath(x0, y + (rowH - barH) / 2, w, barH), fill: color, class: "mark" }, svg);
      txt(svg, x0 + w + 8, y + rowH / 2 + 4.5, (o.fmt || fmt)(v), { "font-size": 13, "font-weight": 600, fill: ink });
      const hit = el("rect", { x: 0, y, width: W, height: rowH, class: "hit", tabindex: 0, "aria-label": `${o.labels[i]}: ${(o.fmt || fmt)(v)}` }, svg);
      bindHover(hit, mark, () => [(o.fmt || fmt)(v), o.labels[i], o.extra ? o.extra(i, v) : null]);
    });
    el("line", { x1: x0, x2: x0, y1: top - 2, y2: top + n * rowH, stroke: axis }, svg);
  }

  // ---------- columnas ----------
  function columnas(container, o) {
    const W = Math.max(container.clientWidth, 280);
    const H = o.height || 280;
    const svg = svgFor(container, W, H, o.title);
    const n = o.values.length;
    const yFmt = o.yFmt || compact;
    const max = o.max || Math.max(...o.values, o.ref ? o.ref.value : 0);
    const tk = ticks(0, max, o.tickCount || 4);
    const left = Math.max(...tk.map((t) => measure(svg, yFmt(t), 12))) + 10;
    const right = 8, top = o.valueLabels === "none" ? 10 : 22, bottom = 28;
    const plotW = W - left - right, plotH = H - top - bottom;
    const yMax = tk[tk.length - 1];
    const y = (v) => top + plotH - (plotH * v) / yMax;
    const grid = css("--grid"), muted = css("--muted"), ink = css("--ink"), axis = css("--axis");
    tk.forEach((t) => {
      el("line", { x1: left, x2: W - right, y1: y(t), y2: y(t), stroke: t === 0 ? axis : grid }, svg);
      txt(svg, left - 8, y(t) + 4, yFmt(t), { "font-size": 12, fill: muted, "text-anchor": "end", "font-variant-numeric": "tabular-nums" });
    });
    const band = plotW / n;
    const bw = Math.min(o.barMax || 24, band * 0.72);
    o.values.forEach((v, i) => {
      const cx = left + band * (i + 0.5);
      const color = typeof o.color === "function" ? o.color(i, v) : o.color || css("--bar");
      const mark = el("path", { d: vBarPath(cx - bw / 2, y(v), bw, y(0) - y(v)), fill: color, class: "mark" }, svg);
      if (o.pattern && o.pattern(i)) mark.setAttribute("fill-opacity", "0.45");
      const show = o.valueLabels === "all" || (Array.isArray(o.valueLabels) && o.valueLabels.includes(i));
      if (show) txt(svg, cx, y(v) - 7, (o.fmt || fmt)(v), { "font-size": 12.5, "font-weight": 600, fill: ink, "text-anchor": "middle" });
      const every = o.xEvery || 1;
      if (i % every === 0) txt(svg, cx, H - 9, o.labels[i], { "font-size": 12, fill: muted, "text-anchor": "middle" });
      const hit = el("rect", { x: cx - band / 2, y: top, width: band, height: plotH, class: "hit", tabindex: 0, "aria-label": `${o.labels[i]}: ${(o.fmt || fmt)(v)}` }, svg);
      bindHover(hit, mark, () => [(o.fmt || fmt)(v), o.tipLabel ? o.tipLabel(i) : o.labels[i], o.extra ? o.extra(i, v) : null]);
    });
    if (o.ref) {
      const ry = y(o.ref.value);
      el("line", { x1: left, x2: W - right, y1: ry, y2: ry, stroke: ink, "stroke-width": 1, "stroke-dasharray": "0" , opacity: 0.55 }, svg);
      const label = o.ref.label;
      const lw = measure(svg, label, 12, 600) + 12;
      el("rect", { x: left + 4, y: ry - 20, width: lw, height: 17, rx: 4, fill: css("--surface") }, svg);
      txt(svg, left + 10, ry - 7.5, label, { "font-size": 12, "font-weight": 600, fill: ink, "text-anchor": "start" });
    }
    if (o.errors) {
      // Barras de error (± desviación estándar)
      o.values.forEach((v, i) => {
        const cx = left + band * (i + 0.5);
        const e = o.errors[i];
        const y1 = y(Math.min(v + e, yMax)), y2 = y(Math.max(v - e, 0));
        el("line", { x1: cx, x2: cx, y1, y2, stroke: ink, "stroke-width": 1.2, opacity: 0.6, "pointer-events": "none" }, svg);
        [y1, y2].forEach((yy) => el("line", { x1: cx - 6, x2: cx + 6, y1: yy, y2: yy, stroke: ink, "stroke-width": 1.2, opacity: 0.6, "pointer-events": "none" }, svg));
      });
    }
  }

  // ---------- líneas ----------
  function linea(container, o) {
    const W = Math.max(container.clientWidth, 280);
    const H = o.height || 300;
    const svg = svgFor(container, W, H, o.title);
    const vals = o.values, n = vals.length;
    const yFmt = o.yFmt || compact;
    const lo = o.yMin !== undefined ? o.yMin : 0;
    const hi = o.yMax || Math.max(...vals);
    const tk = ticks(lo, hi, o.tickCount || 4).filter((t) => t >= lo - 1e-9);
    const left = Math.max(...tk.map((t) => measure(svg, yFmt(t), 12))) + 10;
    const right = o.right || 14, top = 16, bottom = 28;
    const plotW = W - left - right, plotH = H - top - bottom;
    const yMin = tk[0], yMax = tk[tk.length - 1];
    const x = (i) => left + (plotW * i) / (n - 1);
    const y = (v) => top + plotH - (plotH * (v - yMin)) / (yMax - yMin);
    const grid = css("--grid"), muted = css("--muted"), ink = css("--ink"), lineC = css("--line"), axis = css("--axis"), surface = css("--surface");
    tk.forEach((t, k) => {
      el("line", { x1: left, x2: W - right, y1: y(t), y2: y(t), stroke: k === 0 && t === 0 ? axis : grid }, svg);
      txt(svg, left - 8, y(t) + 4, yFmt(t), { "font-size": 12, fill: muted, "text-anchor": "end" });
    });
    // Sombreado de periodos (p. ej., pandemia / dato parcial)
    (o.bands || []).forEach((b) => {
      el("rect", { x: x(b.from), y: top, width: x(b.to) - x(b.from), height: plotH, fill: css("--accent-soft") }, svg);
      txt(svg, (x(b.from) + x(b.to)) / 2, top + 12, b.label, { "font-size": 11, fill: muted, "text-anchor": "middle" });
    });
    for (let i = 0; i < n; i++) {
      const lab = o.xTick ? o.xTick(i) : o.labels[i];
      if (lab) {
        el("line", { x1: x(i), x2: x(i), y1: top + plotH, y2: top + plotH + 4, stroke: axis }, svg);
        txt(svg, x(i), H - 9, lab, { "font-size": 12, fill: muted, "text-anchor": "middle" });
      }
    }
    const pts = vals.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`);
    if (o.area !== false) el("path", { d: `M${x(0)},${y(yMin)}L${pts.join("L")}L${x(n - 1)},${y(yMin)}Z`, fill: css("--line-wash") }, svg);
    el("polyline", { points: pts.join(" "), fill: "none", stroke: lineC, "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);
    if (o.dots) vals.forEach((v, i) => el("circle", { cx: x(i), cy: y(v), r: 4, fill: lineC, stroke: surface, "stroke-width": 2 }, svg));
    // Anotaciones
    (o.notes || []).forEach((a) => {
      const ax = x(a.i), ay = y(vals[a.i]);
      el("circle", { cx: ax, cy: ay, r: 4.5, fill: lineC, stroke: surface, "stroke-width": 2 }, svg);
      const anchor = a.anchor || (ax > W * 0.75 ? "end" : "start");
      const dx = anchor === "end" ? -10 : anchor === "middle" ? 0 : 10;
      const dy = a.dy !== undefined ? a.dy : -12;
      txt(svg, ax + dx, ay + dy, a.text, { "font-size": 12.5, "font-weight": 600, fill: ink, "text-anchor": anchor });
    });
    // Capa de hover: cruz que se ajusta a la X más cercana
    const cross = el("line", { y1: top, y2: top + plotH, stroke: muted, "stroke-width": 1, opacity: 0 , "pointer-events": "none"}, svg);
    const dot = el("circle", { r: 5, fill: lineC, stroke: surface, "stroke-width": 2, opacity: 0, "pointer-events": "none" }, svg);
    const overlay = el("rect", { x: left, y: top, width: plotW, height: plotH, class: "hit", tabindex: 0, "aria-label": (o.title || "") + ". Use las flechas para recorrer los valores." }, svg);
    let cur = n - 1;
    function show(i, cx, cy) {
      cur = i;
      cross.setAttribute("x1", x(i)); cross.setAttribute("x2", x(i)); cross.setAttribute("opacity", 1);
      dot.setAttribute("cx", x(i)); dot.setAttribute("cy", y(vals[i])); dot.setAttribute("opacity", 1);
      if (cx === undefined) {
        const b = svg.getBoundingClientRect(); const s = b.width / W;
        cx = b.left + x(i) * s; cy = b.top + y(vals[i]) * s;
      }
      showTip(cx, cy, (o.fmt || fmt)(vals[i]), o.tipLabel ? o.tipLabel(i) : o.labels[i], o.extra ? o.extra(i) : null);
    }
    function hide() { cross.setAttribute("opacity", 0); dot.setAttribute("opacity", 0); hideTip(); }
    overlay.addEventListener("pointermove", (e) => {
      const b = svg.getBoundingClientRect(); const s = W / b.width;
      const px = (e.clientX - b.left) * s;
      const i = Math.max(0, Math.min(n - 1, Math.round(((px - left) / plotW) * (n - 1))));
      show(i, e.clientX, e.clientY);
    });
    overlay.addEventListener("pointerleave", hide);
    overlay.addEventListener("focus", () => show(cur));
    overlay.addEventListener("blur", hide);
    overlay.addEventListener("keydown", (e) => {
      if (e.key === "ArrowRight") { show(Math.min(n - 1, cur + 1)); e.preventDefault(); e.stopPropagation(); }
      if (e.key === "ArrowLeft") { show(Math.max(0, cur - 1)); e.preventDefault(); e.stopPropagation(); }
    });
  }

  // ---------- mapa ----------
  function mapa(container, o) {
    const M = window.US_MAP;
    const vb = o.viewBox || [0, 0, M.w, M.h];
    const svg = svgFor(container, vb[2], vb[3], o.title);
    svg.setAttribute("viewBox", vb.join(" "));
    const surface = css("--surface"), none = css("--state-none"), ink = css("--ink"), ink2 = css("--ink-2"), hot = css("--hot");
    const byName = o.estados; // { "California": {v, code, fill} }
    const g = el("g", {}, svg);
    M.states.forEach((s) => {
      const info = byName[s.n];
      const p = el("path", { d: s.d, fill: info ? info.fill : none, stroke: surface, "stroke-width": 1, class: "mark" }, g);
      if (info) {
        const hit = p;
        hit.setAttribute("tabindex", 0);
        hit.setAttribute("aria-label", `${info.es}: ${fmt(info.v)} accidentes`);
        bindHover(hit, p, () => [fmt(info.v), info.es, `Puesto ${info.rank} entre los estados`]);
      }
    });
    // etiquetas de estados con dato
    M.states.forEach((s) => {
      const info = byName[s.n];
      if (!info) return;
      const [cx, cy] = info.labelAt || s.c;
      txt(svg, cx, cy + 7, info.code, { "font-size": 20, "font-weight": 700, fill: info.labelInk, "text-anchor": "middle", "pointer-events": "none" });
    });
    // puntos críticos
    o.puntos.forEach((p, i) => {
      const [px, py] = M.pts[i];
      const c = el("circle", { cx: px, cy: py, r: 9, fill: hot, stroke: surface, "stroke-width": 2.5, class: "mark" }, svg);
      const hit = el("circle", { cx: px, cy: py, r: 14, class: "hit", tabindex: 0, "aria-label": `${p.zona}: ${fmt(p.n)} accidentes` }, svg);
      bindHover(hit, c, () => [fmt(p.n) + " accidentes", p.zona, `Celda ${p.lat.toFixed(2)}° N, ${Math.abs(p.lon).toFixed(2)}° O · puesto ${i + 1}`]);
    });
    // rótulos con línea guía
    (o.rotulos || []).forEach((r) => {
      el("line", { x1: r.from[0], y1: r.from[1], x2: r.to[0], y2: r.to[1], stroke: ink2, "stroke-width": 1, "pointer-events": "none" }, svg);
      const lines = r.text;
      lines.forEach((t, k) => txt(svg, r.to[0] + (r.anchor === "end" ? -6 : 6), r.to[1] + 7 + k * 26, t, { "font-size": k === 0 ? 24 : 20, "font-weight": k === 0 ? 700 : 400, fill: k === 0 ? ink : ink2, "text-anchor": r.anchor || "start", "pointer-events": "none" }));
    });
  }

  window.Graficas = { barrasH, columnas, linea, mapa, fmt, compact, css };
})();
