/* Arma las gráficas, la vista de tabla, la navegación y el modo exposición. */
(function () {
  "use strict";
  const D = window.DATOS;
  const G = window.Graficas;
  const { fmt, css } = G;
  const pct = (v, total = D.total, d = 1) => fmt((100 * v) / total, d) + " %";
  const sevColor = (i) => css(`--sev-${i + 1}`);
  const totHora = D.horaSeveridad.map((r) => r.reduce((a, b) => a + b, 0));
  const sevMediaHora = D.horaSeveridad.map((r, i) => r.reduce((a, c, k) => a + c * (k + 1), 0) / totHora[i]);
  const horas = totHora.map((_, i) => String(i).padStart(2, "0"));
  const MES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
  const mesLargo = (s) => { const [y, m] = s.split("-"); return `${MES[+m - 1]} ${y}`; };
  const idxMax = (a) => a.indexOf(Math.max(...a));

  // Cada gráfica: cómo dibujarla y qué tabla mostrar
  const charts = {
    estados: {
      draw: (el) => G.barrasH(el, {
        title: "Accidentes por estado", labels: D.estados.labels, values: D.estados.values,
        color: (i) => (i === 0 ? css("--bar-hi") : css("--bar")),
        extra: (i, v) => `${pct(v)} del total · ${D.estados.codigos[i]}`,
      }),
      table: () => [["Estado", "Accidentes", "% del total"], D.estados.labels.map((l, i) => [l, fmt(D.estados.values[i]), pct(D.estados.values[i])])],
    },
    ciudades: {
      draw: (el) => G.barrasH(el, {
        title: "Accidentes por ciudad", labels: D.ciudades.labels, values: D.ciudades.values,
        color: (i) => (i === 0 ? css("--bar-hi") : css("--bar")),
        extra: (i, v) => `${pct(v, D.total, 2)} del total`,
      }),
      table: () => [["Ciudad", "Accidentes", "% del total"], D.ciudades.labels.map((l, i) => [l, fmt(D.ciudades.values[i]), pct(D.ciudades.values[i], D.total, 2)])],
    },
    horas: {
      draw: (el) => G.columnas(el, {
        title: "Accidentes por hora", labels: horas, values: totHora, height: 300, barMax: 26,
        color: (i) => ([7, 8, 16, 17].includes(i) ? css("--bar-hi") : css("--bar")),
        valueLabels: [7, 16], xEvery: el.clientWidth < 600 ? 3 : 1,
        tipLabel: (i) => `${horas[i]}:00 – ${horas[i]}:59`,
        extra: (i, v) => `${pct(v)} del total`,
      }),
      table: () => [["Hora", "Accidentes", "% del total"], totHora.map((v, i) => [`${horas[i]}:00`, fmt(v), pct(v)])],
    },
    severidad: {
      draw: (el) => G.columnas(el, {
        title: "Accidentes por severidad", labels: D.severidad.labels, values: D.severidad.values, height: 280,
        color: (i) => sevColor(i), valueLabels: "all", barMax: 48, tickCount: 3,
        extra: (i, v) => `${pct(v, D.total, 2)} del total`,
      }),
      table: () => [["Nivel", "Accidentes", "% del total"], D.severidad.labels.map((l, i) => [l, fmt(D.severidad.values[i]), pct(D.severidad.values[i], D.total, 2)])],
    },
    sevHora: {
      draw: (el) => G.linea(el, {
        title: "Severidad media por hora", labels: horas, values: sevMediaHora, height: 280,
        yMin: 2.18, yMax: 2.26, tickCount: 4, yFmt: (v) => fmt(v, 2), fmt: (v) => fmt(v, 3), dots: true, area: false,
        xTick: (i) => (i % (el.clientWidth < 500 ? 6 : 3) === 0 ? horas[i] : null),
        tipLabel: (i) => `Severidad media a las ${horas[i]}:00`,
        notes: [{ i: 7, text: "07:00 · 2,19", dy: 20, anchor: "middle" }, { i: 20, text: "20:00 · 2,26", dy: -12, anchor: "middle" }],
      }),
      table: () => [["Hora", "Severidad media", "Registros"], sevMediaHora.map((v, i) => [`${horas[i]}:00`, fmt(v, 3), fmt(totHora[i])])],
    },
    clima: {
      draw: (el) => G.barrasH(el, {
        title: "Accidentes por clima", labels: D.clima.labels.map((l, i) => `${D.clima.es[i]}`), values: D.clima.values,
        color: (i) => (i === 0 ? css("--bar-hi") : css("--bar")),
        extra: (i, v) => `${D.clima.labels[i]} · ${pct(v)} del total`,
      }),
      table: () => [["Condición (original)", "Traducción", "Accidentes", "% del total"], D.clima.labels.map((l, i) => [l, D.clima.es[i], fmt(D.clima.values[i]), pct(D.clima.values[i])])],
    },
    via: {
      draw: (el) => G.barrasH(el, {
        title: "Accidentes por tipo de vía", labels: D.via.labels, values: D.via.values,
        color: (i) => (i === 0 ? css("--bar-dim") : i === 1 ? css("--bar-hi") : css("--bar")),
        extra: (i, v) => (i === 0 ? `${pct(v)} del total · sin prefijo reconocible` : `${pct(v)} del total · ${pct(v, D.via.values.slice(1).reduce((a, b) => a + b))} de las vías clasificadas`),
      }),
      table: () => [["Tipo de vía", "Accidentes", "% del total"], D.via.labels.map((l, i) => [l, fmt(D.via.values[i]), pct(D.via.values[i], D.total, 2)])],
    },
    dias: {
      draw: (el) => G.columnas(el, {
        title: "Accidentes por día", labels: D.dias.labels, values: D.dias.values, height: 280, barMax: 48,
        color: (i) => (i >= 5 ? css("--sev-1") : i === 4 ? css("--bar-hi") : css("--bar")), valueLabels: "all", tickCount: 3,
        extra: (i, v) => `${fmt(v)} · ${pct(v)} del total`,
      }),
      table: () => [["Día", "Accidentes", "% del total"], D.dias.labels.map((l, i) => [l, fmt(D.dias.values[i]), pct(D.dias.values[i])])],
    },
    duracion: {
      draw: (el) => G.columnas(el, {
        title: "Duración promedio por severidad", labels: D.duracion.labels, values: D.duracion.media, height: 300,
        color: (i) => sevColor(i), valueLabels: "all", barMax: 56, max: 200, tickCount: 4,
        fmt: (v) => fmt(v, 2) + " min", yFmt: (v) => fmt(v) + " min",
        ref: { value: D.duracion.general, label: "Promedio general · 102,24 min" },
        extra: (i) => `Desv. est. ${fmt(D.duracion.desv[i], 2)} min · ${fmt(D.duracion.casos[i])} casos`,
      }),
      table: () => [["Nivel", "Casos válidos", "Media (min)", "Desv. est. (min)"], D.duracion.labels.map((l, i) => [l, fmt(D.duracion.casos[i]), fmt(D.duracion.media[i], 2), fmt(D.duracion.desv[i], 2)])],
    },
    meses: {
      draw: (el) => {
        const m = D.mensuales;
        const iMax = idxMax(m);
        G.linea(el, {
          title: "Accidentes por mes", labels: D.meses, values: m, height: 320, tickCount: 4,
          xTick: (i) => (i % 12 === 0 ? D.meses[i].slice(0, 4) : null),
          tipLabel: (i) => mesLargo(D.meses[i]) + (i >= 84 ? " · dato parcial del dataset" : ""),
          bands: [{ from: 53.5, to: 55.5, label: "jul–ago 2020" }],
          notes: [
            { i: iMax, text: `Máx. dic 2022 · ${fmt(m[iMax])}`, anchor: "end", dy: -12 },
            { i: 54, text: `${fmt(m[54])}`, anchor: "middle", dy: 22 },
          ],
        });
      },
      table: () => [["Mes", "Accidentes"], D.meses.map((s, i) => [mesLargo(s), fmt(D.mensuales[i])])],
    },
    anios: {
      draw: (el) => G.columnas(el, {
        title: "Accidentes por año", labels: D.anios.labels.map((l) => l.replace(" (ene–mar)", "*")), values: D.anios.values, height: 300,
        color: (i) => (i === 6 ? css("--bar-hi") : css("--bar")), pattern: (i) => i === 7,
        valueLabels: el.clientWidth < 520 ? [0, 6, 7] : "all", barMax: 40, fmt: (v) => G.compact(v),
        tipLabel: (i) => D.anios.labels[i], extra: (i, v) => `${fmt(v)} accidentes`,
      }),
      table: () => [["Año", "Accidentes"], D.anios.labels.map((l, i) => [l, fmt(D.anios.values[i])])],
    },
    vehiculos: {
      draw: (el) => G.barrasH(el, {
        title: "Menciones por tipo de vehículo", labels: D.vehiculos.labels, values: D.vehiculos.values,
        color: (i) => (i === 0 ? css("--bar-hi") : css("--bar")),
        extra: (i, v) => `${pct(v, 35030)} de las menciones identificadas`,
      }),
      table: () => [["Vehículo", "Menciones", "% de identificados"], D.vehiculos.labels.map((l, i) => [l, fmt(D.vehiculos.values[i]), pct(D.vehiculos.values[i], 35030)]).concat([["Sin especificar", fmt(D.vehiculos.sinEspecificar), "—"]])],
    },
    mapa: {
      draw: (el) => {
        const names = ["California", "Florida", "Texas", "South Carolina", "New York", "North Carolina", "Virginia"];
        const bucket = (v) => (v >= 1e6 ? 4 : v >= 5e5 ? 3 : v >= 3e5 ? 2 : 1);
        const darkTheme = document.documentElement.dataset.theme === "dark" ||
          (!document.documentElement.dataset.theme && matchMedia("(prefers-color-scheme: dark)").matches);
        const estados = {};
        names.forEach((n, i) => {
          const v = D.estados.values[i], b = bucket(v);
          const lightFill = b >= 3; // relleno oscuro en tema claro
          estados[n] = {
            v, code: D.estados.codigos[i], es: D.estados.labels[i], rank: i + 1, fill: css(`--sev-${b}`),
            labelInk: darkTheme ? (b >= 3 ? "#0b0b0b" : "#ffffff") : (lightFill ? "#ffffff" : "#0b0b0b"),
            labelAt: n === "Florida" ? [800, 560] : n === "California" ? [60, 250] : n === "Virginia" ? [790, 300] : n === "New York" ? [830, 160] : null,
          };
        });
        const P = window.US_MAP.pts;
        G.mapa(el, {
          title: "Mapa de estados líderes y celdas críticas", estados, puntos: D.puntos,
          viewBox: [-235, 0, 1365, 610],
          rotulos: [
            { from: P[0], to: [880, 480], text: ["Orlando", "3.026 · celda n.º 1"] },
            { from: P[1], to: [935, 255], text: ["Nueva York", "2.953 · n.º 2"] },
            { from: P[3], to: [-20, 405], text: ["Los Angeles", "3 celdas", "2.941 · 2.841 · 2.826"], anchor: "end" },
          ],
        });
        // leyenda
        const lg = document.getElementById("map-legend");
        lg.replaceChildren();
        [[4, "≥ 1 M"], [3, "500 mil – 1 M"], [2, "300 – 500 mil"], [1, "< 300 mil"]].forEach(([b, t]) => {
          const s = document.createElement("span"); const i = document.createElement("i"); i.style.background = css(`--sev-${b}`); s.append(i, document.createTextNode(t)); lg.append(s);
        });
        const s2 = document.createElement("span"); const i2 = document.createElement("i"); i2.className = "dot"; i2.style.background = css("--hot");
        s2.append(i2, document.createTextNode("Celda crítica (top 5)")); lg.append(s2);
        const s3 = document.createElement("span"); const i3 = document.createElement("i"); i3.style.background = css("--state-none"); i3.style.outline = "1px solid " + css("--axis");
        s3.append(i3, document.createTextNode("Fuera del top 7")); lg.append(s3);
      },
      table: () => [["#", "Zona", "Latitud", "Longitud", "Accidentes"], D.puntos.map((p, i) => [String(i + 1), p.zona, fmt(p.lat, 2), fmt(p.lon, 2), fmt(p.n)])],
    },
  };

  // ---------- tabla ----------
  function renderTable(el, spec) {
    const [head, rows] = spec;
    const wrap = document.createElement("div"); wrap.className = "table-wrap";
    const t = document.createElement("table"); t.className = "data-table";
    const thead = t.createTHead().insertRow();
    head.forEach((h, k) => { const th = document.createElement("th"); th.textContent = h; if (k > 0 && /\d/.test(rows[0][k])) th.className = "n"; thead.appendChild(th); });
    const tb = t.createTBody();
    rows.forEach((r) => { const tr = tb.insertRow(); r.forEach((c, k) => { const td = tr.insertCell(); td.textContent = c; if (k > 0 && /^[\d.,\s%—-]+( min)?$/.test(c)) td.className = "n"; }); });
    wrap.appendChild(t);
    el.replaceChildren(wrap);
  }

  // ---------- montaje de tarjetas ----------
  const cards = [...document.querySelectorAll("[data-chart]")];
  cards.forEach((card) => {
    const key = card.dataset.chart;
    const spec = charts[key];
    if (!spec) return;
    card.dataset.view = "chart";
    const head = card.querySelector(".card-head");
    const tg = document.createElement("div"); tg.className = "view-toggle"; tg.setAttribute("role", "group"); tg.setAttribute("aria-label", "Vista");
    ["Gráfica", "Tabla"].forEach((label, k) => {
      const b = document.createElement("button"); b.type = "button"; b.textContent = label;
      b.setAttribute("aria-pressed", k === 0 ? "true" : "false");
      b.addEventListener("click", () => {
        card.dataset.view = k === 0 ? "chart" : "table";
        tg.querySelectorAll("button").forEach((x, j) => x.setAttribute("aria-pressed", j === k ? "true" : "false"));
        draw(card);
      });
      tg.appendChild(b);
    });
    head.appendChild(tg);
  });
  function draw(card) {
    const spec = charts[card.dataset.chart];
    const el = card.querySelector(".chart");
    const legend = card.querySelector(".legend");
    if (card.dataset.view === "table") { renderTable(el, spec.table()); if (legend) legend.style.display = "none"; }
    else { spec.draw(el); if (legend) legend.style.display = ""; }
  }
  function drawAll() { cards.forEach(draw); drawExtras(); }

  function drawExtras() {
    // Barra segmentada de cobertura de vehículos
    const seg = document.getElementById("seg-veh");
    const idc = css("--bar-hi"), noc = css("--bar-dim");
    seg.replaceChildren();
    [[35030, idc], [7151761, noc]].forEach(([v, c]) => { const s = document.createElement("span"); s.style.flex = `${Math.max(v / D.total, 0.006)} 0 0`; s.style.background = c; seg.appendChild(s); });
    document.getElementById("sw-id").style.background = idc;
    document.getElementById("sw-no").style.background = noc;
    // Tabla de puntos críticos
    const tb = document.querySelector("#tabla-puntos tbody");
    tb.replaceChildren();
    D.puntos.forEach((p, i) => {
      const tr = tb.insertRow();
      [String(i + 1), p.zona, fmt(p.n)].forEach((c, k) => { const td = tr.insertCell(); td.textContent = c; if (k === 2) td.className = "n"; });
    });
  }

  // ---------- tema ----------
  const root = document.documentElement;
  try { const saved = localStorage.getItem("tema"); if (saved) root.dataset.theme = saved; } catch (e) { /* sin almacenamiento */ }
  document.getElementById("btn-theme").addEventListener("click", () => {
    const isDark = root.dataset.theme === "dark" || (!root.dataset.theme && matchMedia("(prefers-color-scheme: dark)").matches);
    root.dataset.theme = isDark ? "light" : "dark";
    try { localStorage.setItem("tema", root.dataset.theme); } catch (e) { /* sin almacenamiento */ }
    drawAll();
  });
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { if (!root.dataset.theme) drawAll(); });

  // ---------- navegación ----------
  const sections = [...document.querySelectorAll("main > section")];
  const links = [...document.querySelectorAll(".nav a")];
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (!e.isIntersecting) return;
      links.forEach((a) => a.classList.toggle("active", a.getAttribute("href") === "#" + e.target.id));
    });
  }, { rootMargin: "-45% 0px -50% 0px" });
  sections.forEach((s) => io.observe(s));

  // ---------- modo exposición ----------
  const btnP = document.getElementById("btn-present");
  function setPresent(on) {
    const idx = currentIndex();
    document.body.classList.toggle("present", on);
    btnP.setAttribute("aria-pressed", on ? "true" : "false");
    btnP.innerHTML = on ? "■ <span>Salir</span>" : "▶ <span>Exponer</span>";
    if (on && document.documentElement.requestFullscreen && !document.fullscreenElement) document.documentElement.requestFullscreen().catch(() => {});
    if (!on && document.fullscreenElement) document.exitFullscreen().catch(() => {});
    setTimeout(() => { drawAll(); sections[idx].scrollIntoView({ behavior: "instant", block: "start" }); }, 150);
  }
  btnP.addEventListener("click", () => setPresent(!document.body.classList.contains("present")));
  function currentIndex() {
    const mid = 90;
    let idx = 0;
    sections.forEach((s, i) => { if (s.getBoundingClientRect().top <= mid) idx = i; });
    return idx;
  }
  function go(delta) {
    const i = Math.max(0, Math.min(sections.length - 1, currentIndex() + delta));
    sections[i].scrollIntoView({ behavior: "smooth", block: "start" });
  }
  document.addEventListener("keydown", (e) => {
    if (e.target.closest && e.target.closest("input, textarea")) return;
    if (e.key === "p" || e.key === "P") { setPresent(!document.body.classList.contains("present")); }
    else if (e.key === "Escape" && document.body.classList.contains("present")) setPresent(false);
    else if (document.body.classList.contains("present") && (e.key === "ArrowRight" || e.key === "PageDown" || e.key === " ")) { e.preventDefault(); go(1); }
    else if (document.body.classList.contains("present") && (e.key === "ArrowLeft" || e.key === "PageUp")) { e.preventDefault(); go(-1); }
  });
  document.addEventListener("fullscreenchange", () => { if (!document.fullscreenElement && document.body.classList.contains("present")) { document.body.classList.remove("present"); btnP.innerHTML = "▶ <span>Exponer</span>"; btnP.setAttribute("aria-pressed", "false"); drawAll(); } });

  // ---------- dibujar y redibujar al cambiar tamaño ----------
  let rt;
  window.addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(drawAll, 120); });
  drawAll();
})();
