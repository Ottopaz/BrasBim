// BrasBim: planta da casa de exemplo na abertura do site.
// Medidas em centímetros. As paredes são o contorno externo menos os ambientes
// (fill-rule evenodd), e a área de cada ambiente vem do próprio contorno.
(function () {
  "use strict";

  const NS = "http://www.w3.org/2000/svg";
  const svg = document.getElementById("planta");
  if (!svg) return;

  const LARGURA = 1000, PROFUNDIDADE = 880;

  // Ambientes: contorno interno (face das paredes) e ponto do rótulo
  const ambientes = [
    { nome: "Quarto 1", pts: [[15, 15], [350, 15], [350, 440], [15, 440]] },
    { nome: "Banheiro", pts: [[360, 15], [560, 15], [560, 300], [360, 300]] },
    { nome: "Quarto 2", pts: [[570, 15], [985, 15], [985, 300], [570, 300]] },
    { nome: "Circulação", pts: [[360, 310], [985, 310], [985, 440], [360, 440]] },
    { nome: "Estar e jantar", pts: [[15, 450], [520, 450], [520, 865], [15, 865]] },
    { nome: "Serviço", pts: [[530, 450], [720, 450], [720, 620], [530, 620]] },
    { nome: "Cozinha", pts: [[730, 450], [985, 450], [985, 865], [530, 865], [530, 630], [730, 630]], rotulo: [810, 760] },
  ];

  // Vãos: retângulo que corta a parede; folha da porta com dobradiça h,
  // direção da largura d e lado para onde abre n.
  const portas = [
    { vao: [350, 340, 10, 80], h: [350, 420], d: [0, -1], n: [-1, 0], w: 80 },
    { vao: [380, 300, 70, 10], h: [380, 300], d: [1, 0], n: [0, -1], w: 70 },
    { vao: [600, 300, 80, 10], h: [680, 300], d: [-1, 0], n: [0, -1], w: 80 },
    { vao: [380, 440, 80, 10], h: [380, 450], d: [1, 0], n: [0, 1], w: 80 },
    { vao: [720, 500, 10, 80], h: [720, 580], d: [0, -1], n: [-1, 0], w: 80 },
    { vao: [520, 700, 10, 100] },
    { vao: [120, 865, 90, 15], h: [120, 865], d: [1, 0], n: [0, -1], w: 90 },
    { vao: [985, 480, 15, 80], h: [985, 560], d: [0, -1], n: [-1, 0], w: 80 },
  ];

  // Janelas nas paredes externas: [x, y, largura, profundidade]
  const janelas = [
    [100, 0, 160, 15], [420, 0, 80, 15], [700, 0, 160, 15],
    [0, 150, 15, 150], [0, 560, 15, 200], [985, 100, 15, 120],
    [300, 865, 160, 15], [780, 865, 160, 15],
  ];

  const num = (v, casas) =>
    v.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });

  function area(pts) {
    let s = 0;
    for (let i = 0; i < pts.length; i++) {
      const [x1, y1] = pts[i], [x2, y2] = pts[(i + 1) % pts.length];
      s += x1 * y2 - x2 * y1;
    }
    return Math.abs(s) / 2 / 10000; // m²
  }
  function perimetro(pts) {
    let s = 0;
    for (let i = 0; i < pts.length; i++) {
      const [x1, y1] = pts[i], [x2, y2] = pts[(i + 1) % pts.length];
      s += Math.hypot(x2 - x1, y2 - y1);
    }
    return s / 100; // m
  }
  function centro(pts) {
    const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
    return [(Math.min(...xs) + Math.max(...xs)) / 2, (Math.min(...ys) + Math.max(...ys)) / 2];
  }

  function el(nome, attrs, pai) {
    const e = document.createElementNS(NS, nome);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    (pai || svg).appendChild(e);
    return e;
  }
  const caminho = pts => "M" + pts.map(p => p.join(" ")).join("L") + "Z";

  // Margem para as cotas
  svg.setAttribute("viewBox", "-140 -150 1250 1110");

  // Grade de 1 m
  const grade = el("g", { class: "p-grade", "aria-hidden": "true" });
  for (let x = -100; x <= 1100; x += 100) el("line", { x1: x, y1: -100, x2: x, y2: 960 }, grade);
  for (let y = -100; y <= 960; y += 100) el("line", { x1: -100, y1: y, x2: 1100, y2: y }, grade);

  // Paredes
  const externo = [[0, 0], [LARGURA, 0], [LARGURA, PROFUNDIDADE], [0, PROFUNDIDADE]];
  const paredes = el("path", {
    class: "p-paredes",
    "fill-rule": "evenodd",
    d: [externo, ...ambientes.map(a => a.pts)].map(caminho).join(" "),
    "aria-hidden": "true",
  });

  const depois = el("g", { class: "p-depois", "aria-hidden": "true" });

  // Janelas: corta a parede e desenha faces e vidro
  for (const [x, y, w, h] of janelas) {
    el("rect", { class: "p-vao", x, y, width: w, height: h }, depois);
    if (w > h) {
      for (const yy of [y, y + h / 2, y + h]) el("line", { class: "p-traco", x1: x, y1: yy, x2: x + w, y2: yy }, depois);
      for (const xx of [x, x + w]) el("line", { class: "p-traco", x1: xx, y1: y, x2: xx, y2: y + h }, depois);
    } else {
      for (const xx of [x, x + w / 2, x + w]) el("line", { class: "p-traco", x1: xx, y1: y, x2: xx, y2: y + h }, depois);
      for (const yy of [y, y + h]) el("line", { class: "p-traco", x1: x, y1: yy, x2: x + w, y2: yy }, depois);
    }
  }

  // Portas: vão, folha e arco de abertura
  for (const p of portas) {
    const [x, y, w, h] = p.vao;
    el("rect", { class: "p-vao", x, y, width: w, height: h }, depois);
    if (!p.h) continue;
    const [hx, hy] = p.h, W = p.w;
    const a = [hx + p.n[0] * W, hy + p.n[1] * W];
    const b = [hx + p.d[0] * W, hy + p.d[1] * W];
    const horario = p.n[0] * p.d[1] - p.n[1] * p.d[0] > 0 ? 1 : 0;
    el("line", { class: "p-traco", x1: hx, y1: hy, x2: a[0], y2: a[1] }, depois);
    el("path", { class: "p-giro", d: `M${a[0]} ${a[1]} A${W} ${W} 0 0 ${horario} ${b[0]} ${b[1]}` }, depois);
  }

  // Cotas gerais
  const cotas = el("g", { class: "p-depois" });
  cotas.setAttribute("aria-hidden", "true");
  function cota(x1, y1, x2, y2, texto, tx, ty, girar) {
    el("line", { class: "p-cota", x1, y1, x2, y2 }, cotas);
    const vert = x1 === x2;
    for (const [x, y] of [[x1, y1], [x2, y2]]) {
      el("line", { class: "p-cota", x1: x - 12, y1: y + (vert ? -12 : 12), x2: x + 12, y2: y + (vert ? 12 : -12) }, cotas);
      el("line", { class: "p-cota", x1: vert ? x - 30 : x, y1: vert ? y : y - 30, x2: vert ? x + 30 : x, y2: vert ? y : y + 30 }, cotas);
    }
    const t = el("text", { class: "p-cota-texto", x: tx, y: ty, "text-anchor": "middle" }, cotas);
    if (girar) t.setAttribute("transform", `rotate(-90 ${tx} ${ty})`);
    t.textContent = texto;
  }
  cota(0, -80, LARGURA, -80, num(LARGURA / 100, 2), LARGURA / 2, -96);
  cota(-80, 0, -80, PROFUNDIDADE, num(PROFUNDIDADE / 100, 2), -96, PROFUNDIDADE / 2, true);

  // Ambientes: área de foco, rótulo e leitura
  const leitura = {
    classe: document.getElementById("leitura-classe"),
    nome: document.getElementById("leitura-nome"),
    dados: document.getElementById("leitura-dados"),
  };
  const total = ambientes.reduce((s, a) => s + area(a.pts), 0);
  const padrao = {
    nome: "Casa de exemplo",
    dados: `${ambientes.length} ambientes, ${num(total, 2)} m² de área útil. Passe o mouse ou use Tab nos ambientes.`,
  };
  leitura.dados.textContent = padrao.dados;

  const rotulos = el("g", { class: "p-depois", "aria-hidden": "true" });
  for (const a of ambientes) {
    const m2 = area(a.pts), per = perimetro(a.pts);
    const forma = el("path", {
      class: "p-ambiente",
      d: caminho(a.pts),
      tabindex: "0",
      role: "img",
      "aria-label": `${a.nome}, ${num(m2, 2)} metros quadrados`,
    });
    const mostrar = () => {
      forma.classList.add("ativo");
      leitura.nome.textContent = a.nome;
      leitura.dados.textContent = `Área ${num(m2, 2)} m², perímetro ${num(per, 2)} m`;
    };
    const voltar = () => {
      forma.classList.remove("ativo");
      leitura.nome.textContent = padrao.nome;
      leitura.dados.textContent = padrao.dados;
    };
    forma.addEventListener("mouseenter", mostrar);
    forma.addEventListener("focus", mostrar);
    forma.addEventListener("mouseleave", voltar);
    forma.addEventListener("blur", voltar);

    const [cx, cy] = a.rotulo || centro(a.pts);
    const t = el("text", { class: "p-rotulo", x: cx, y: cy }, rotulos);
    t.textContent = a.nome;
    const t2 = el("text", { class: "p-rotulo p-rotulo-area", x: cx, y: cy + 32 }, rotulos);
    t2.textContent = `${num(m2, 2)} m²`;
  }
  // Rótulos acima dos ambientes, sem bloquear o mouse
  svg.appendChild(rotulos);

  // Traçado das paredes: comprimento real do contorno para a animação
  paredes.style.setProperty("--comp", Math.ceil(paredes.getTotalLength()));
  svg.classList.add("desenhando");
})();
