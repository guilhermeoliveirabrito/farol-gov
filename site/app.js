// farol-gov: pagina de resultados
//
// Regra da casa: nada aqui usa innerHTML. O detalhe de cada check pode trazer texto
// vindo do servidor avaliado (header Location, mensagem de erro TLS), entao tudo
// entra como textContent. A CSP com Trusted Types faz o navegador barrar qualquer deslize.
//
// Desempenho: a pagina abre so com dados/resumo.json (uma linha por municipio).
// O detalhe de cada check fica em dados/uf/XX.json e so e baixado quando alguem abre uma cidade.

const REPO = "https://github.com/guilhermeoliveirabrito/farol-gov";
const POR_PAGINA = 30;

const ITENS = {
  https: ["HTTPS com certificado válido", "Garante que o que você digita no site não viaja aberto pela rede."],
  redirect: ["HTTP leva para HTTPS", "Quem digita o endereço sem https cai na versão protegida."],
  tls: ["TLS 1.2 ou superior", "Usa versões atuais da criptografia, sem as que já foram quebradas."],
  hsts: ["HSTS", "Avisa o navegador para nunca aceitar a versão sem criptografia."],
  headers: ["Headers de segurança", "Bloqueia truques comuns, como esconder o site dentro de outro."],
  security_txt: ["security.txt", "Diz a quem encontrar uma falha para onde mandar o aviso."],
  dnssec: ["DNSSEC", "Assina o endereço do site para ninguém desviar você para outro lugar."],
  spf: ["SPF", "Lista quais servidores podem mandar e-mail em nome da prefeitura."],
  dmarc: ["DMARC", "Manda os provedores recusarem e-mail falso com o nome da prefeitura."],
};

const STATUS = { pass: "cumpre", warn: "parcial", fail: "não cumpre", error: "não verificado" };
const CODIGOS = { p: "pass", w: "warn", f: "fail", e: "error" };
const CONCEITOS = ["A", "B", "C", "D", "F"];

const AVISOS = {
  nao_resolve: "O domínio cadastrado no Wikidata não existe no DNS.",
  dominio_alternativo: "O domínio cadastrado não funciona; avaliamos a versão com ou sem www.",
  fora_do_gov_br: "Domínio fora do .gov.br. Fica fora do ranking até alguém confirmar que é o site oficial.",
  dominio_compartilhado: "O mesmo domínio aparece para outro município. Fica fora do ranking até revisão.",
};

// posicao aproximada de cada estado num mapa de ladrilhos (coluna, linha)
const LADRILHOS = {
  RR: [2, 1], AP: [4, 1],
  AM: [2, 2], PA: [3, 2], MA: [5, 2], CE: [6, 2], RN: [7, 2],
  AC: [1, 3], RO: [2, 3], MT: [3, 3], TO: [4, 3], PI: [5, 3], PE: [6, 3], PB: [7, 3],
  MS: [3, 4], GO: [4, 4], BA: [5, 4], SE: [6, 4], AL: [7, 4],
  DF: [4, 5], MG: [5, 5], ES: [6, 5],
  SP: [4, 6], RJ: [5, 6],
  PR: [4, 7],
  SC: [4, 8],
  RS: [3, 9],
};

const $ = (id) => document.getElementById(id);
const num = (n) => n.toLocaleString("pt-BR");
const ordemAlfabetica = new Intl.Collator("pt-BR").compare;
const reduzirMovimento = matchMedia("(prefers-reduced-motion: reduce)").matches;

let todos = [];
let ranqueados = [];
let filtrados = [];
let mostrando = 0;

// ---------- utilitarios ----------

function el(tag, attrs = {}, ...filhos) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null) continue;
    if (k === "class") e.className = v;
    else if (k === "text") e.textContent = v;
    else e.setAttribute(k, v);
  }
  for (const f of filhos) {
    if (f == null || f === false) continue;
    e.append(f instanceof Node ? f : document.createTextNode(String(f)));
  }
  return e;
}

const statusSeguro = (s) => (s in STATUS ? s : "error");
const conceitoSeguro = (c) => (CONCEITOS.includes(c) ? c : null);
const pct = (parte, total) => (total ? (100 * parte) / total : 0);
const fmtPct = (v) => v.toLocaleString("pt-BR", { maximumFractionDigits: v < 10 ? 1 : 0 }) + "%";
const fmtNota = (v) => v.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const semAcento = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const conta = (lista, check, st = "pass") => lista.filter((r) => r.st[check] === st).length;

function conceitoDaNota(n) {
  if (n >= 90) return "A";
  if (n >= 75) return "B";
  if (n >= 55) return "C";
  if (n >= 35) return "D";
  return "F";
}

function selo(r) {
  return r.conceito
    ? el("span", { class: `conceito ${r.conceito}`, text: r.conceito })
    : el("span", { class: "conceito sem", text: "–", title: "Sem nota" });
}

// quando o elemento aparece na tela, chama fn uma vez (barras e ladrilhos)
function quandoAparecer(alvo, fn) {
  if (reduzirMovimento || !("IntersectionObserver" in window)) return fn();
  const obs = new IntersectionObserver((entradas) => {
    if (entradas.some((e) => e.isIntersecting)) {
      obs.disconnect();
      fn();
    }
  }, { threshold: 0.2 });
  obs.observe(alvo);
}

async function buscarJson(url) {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

function decodificar(resumo) {
  const idx = Object.fromEntries(resumo.campos.map((c, i) => [c, i]));
  return resumo.municipios.map((l) => {
    const st = {};
    resumo.checks.forEach((c, i) => (st[c] = CODIGOS[l[idx.status][i]] || "error"));
    const municipio = String(l[idx.municipio] ?? "");
    const dominio = String(l[idx.dominio] ?? "");
    return {
      ibge: String(l[idx.ibge]),
      municipio,
      uf: String(l[idx.uf] ?? ""),
      dominio,
      lat: l[idx.lat],
      lon: l[idx.lon],
      nota: typeof l[idx.nota] === "number" ? l[idx.nota] : null,
      conceito: conceitoSeguro(l[idx.conceito]),
      acessivel: Boolean(l[idx.flags] & 1),
      ranking: Boolean(l[idx.flags] & 2),
      st,
      _busca: semAcento(`${municipio} ${dominio}`),
      _nome: semAcento(municipio),
    };
  });
}

// ===================================================================
// mapa: o facho do Farol da Barra girando sobre as prefeituras
// ===================================================================

const Mapa = (() => {
  const K = Math.cos((14 * Math.PI) / 180);
  const LARG = 42.4 * K; // de -74.2 a -31.8 de longitude
  const ALT = 39.8; // de 5.6 a -34.2 de latitude
  const proj = (lon, lat) => [(lon + 74.2) * K, 5.6 - lat];
  const FAROL = proj(-38.5325, -13.0104); // Farol da Barra, Salvador
  const VOLTA = 10000; // ms por volta completa
  const VOLTA_INICIAL = 2600; // a primeira volta e mais rapida e vai revelando o mapa
  const TAU = Math.PI * 2;

  let canvas, ctx, cores;
  let pontos = [];
  let grade = new Map();
  let escala = 1, dx = 0, dy = 0, largCss = 0, altCss = 0, largo = true;
  let angulo = -Math.PI / 2;
  let inicioAng = angulo;
  let inicio = 0, ultimo = 0, percorrido = 0;
  let modo = "ronda", alvo = null, destaque = -1;
  let rodando = false, visivel = true, quadro = 0;
  // a parte que nao muda (graticulado + pontos) fica pre-desenhada aqui
  let fundo = null;
  let raioPonto = 2;

  const tx = (x) => dx + x * escala;
  const ty = (y) => dy + y * escala;
  const jaRevelado = (p) => percorrido >= TAU || (p.ang - inicioAng + TAU * 2) % TAU <= percorrido;

  function preparar(lista, semSite) {
    pontos = [];
    for (const [ibge, nome, uf, lat, lon] of semSite) {
      if (typeof lat !== "number" || typeof lon !== "number") continue;
      const [x, y] = proj(lon, lat);
      pontos.push({ x, y, cor: "sem", r: null, nome, uf, ibge: String(ibge) });
    }
    for (const r of lista) {
      if (typeof r.lat !== "number" || typeof r.lon !== "number") continue;
      const [x, y] = proj(r.lon, r.lat);
      pontos.push({ x, y, cor: r.ranking && r.conceito ? r.conceito : "X", r, ibge: r.ibge });
    }
    // sem site por baixo; o resto em ordem pseudoaleatoria fixa, pra nenhuma cor
    // ficar sempre por cima nas regioes densas
    const mistura = (p) => Math.imul(Number(p.ibge), 2654435761) >>> 0;
    pontos.sort((a, b) => (b.cor === "sem") - (a.cor === "sem") || mistura(a) - mistura(b));
    for (const p of pontos) p.ang = Math.atan2(p.y - FAROL[1], p.x - FAROL[0]);

    grade = new Map();
    pontos.forEach((p, i) => {
      const chave = `${Math.floor(p.x)}:${Math.floor(p.y)}`;
      if (!grade.has(chave)) grade.set(chave, []);
      grade.get(chave).push(i);
    });
    return pontos.filter((p) => p.r).length;
  }

  function dimensionar() {
    largCss = canvas.clientWidth;
    altCss = canvas.clientHeight;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(largCss * dpr);
    canvas.height = Math.round(altCss * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    // no desktop o mapa ocupa o lado direito; no celular, a caixa inteira
    largo = largCss >= 900;
    const area = largo
      ? { x: largCss * 0.48, y: 60, w: largCss * 0.47, h: altCss - 150 }
      : { x: 10, y: 10, w: largCss - 20, h: altCss - 20 };
    escala = Math.min(area.w / LARG, area.h / ALT);
    dx = area.x + (area.w - LARG * escala) / 2;
    dy = area.y + (area.h - ALT * escala) / 2;
    raioPonto = Math.max(1.4, 0.2 * escala);
    prepararFundo(dpr);
  }

  function prepararFundo(dpr) {
    fundo = document.createElement("canvas");
    fundo.width = canvas.width;
    fundo.height = canvas.height;
    const f = fundo.getContext("2d");
    f.setTransform(dpr, 0, 0, dpr, 0, 0);
    const original = ctx;
    ctx = f;
    graticulado();
    ctx.globalAlpha = 0.85;
    pontosBase(() => true);
    ctx.globalAlpha = 1;
    ctx = original;
  }

  function pontosBase(filtro) {
    const r = raioPonto;
    let corAtual = null;
    ctx.beginPath();
    for (const p of pontos) {
      if (!filtro(p)) continue;
      if (p.cor !== corAtual) {
        if (corAtual) ctx.fill();
        ctx.fillStyle = cores[p.cor];
        corAtual = p.cor;
        ctx.beginPath();
      }
      const x = tx(p.x);
      const y = ty(p.y);
      ctx.moveTo(x + r, y);
      ctx.arc(x, y, r, 0, TAU);
    }
    if (corAtual) ctx.fill();
  }

  function graticulado() {
    ctx.save();
    ctx.strokeStyle = "rgba(199, 212, 224, 0.06)";
    ctx.lineWidth = 1;
    ctx.fillStyle = "rgba(199, 212, 224, 0.3)";
    ctx.font = "11px Inter, system-ui, sans-serif";
    ctx.beginPath();
    for (let lat = 5; lat >= -30; lat -= 5) {
      const y = ty(5.6 - lat);
      ctx.moveTo(tx(0), y);
      ctx.lineTo(tx(LARG), y);
      if (largo) ctx.fillText(lat === 0 ? "0°" : `${Math.abs(lat)}°S`, tx(LARG) + 10, y + 4);
    }
    for (let lon = -70; lon <= -35; lon += 5) {
      const x = tx((lon + 74.2) * K);
      ctx.moveTo(x, ty(0));
      ctx.lineTo(x, ty(ALT));
      if (largo) ctx.fillText(`${Math.abs(lon)}°O`, x - 12, ty(ALT) + 18);
    }
    ctx.stroke();
    ctx.restore();
  }

  function facho(abertura, forca) {
    const fx = tx(FAROL[0]);
    const fy = ty(FAROL[1]);
    const raio = 40 * escala;
    const grad = ctx.createRadialGradient(fx, fy, 0, fx, fy, raio);
    grad.addColorStop(0, `rgba(255, 207, 107, ${0.3 * forca})`);
    grad.addColorStop(0.35, `rgba(255, 207, 107, ${0.1 * forca})`);
    grad.addColorStop(1, "rgba(255, 207, 107, 0)");
    ctx.save();
    // o facho fica dentro da carta, sem invadir o texto
    ctx.beginPath();
    ctx.rect(tx(0) - 30, 0, largCss, altCss);
    ctx.clip();
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.moveTo(fx, fy);
    ctx.arc(fx, fy, raio, angulo - abertura, angulo + abertura * 0.12);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  }

  function desenhar(agora) {
    ctx.clearRect(0, 0, largCss, altCss);
    const apontando = modo === "aponta" && alvo;
    const r = raioPonto;

    // fundo pronto; na primeira volta ele aparece so no setor que o facho ja varreu
    ctx.save();
    if (percorrido < TAU && !reduzirMovimento) {
      const fx = tx(FAROL[0]);
      const fy = ty(FAROL[1]);
      ctx.beginPath();
      ctx.moveTo(fx, fy);
      ctx.arc(fx, fy, Math.hypot(largCss, altCss), inicioAng, inicioAng + percorrido);
      ctx.closePath();
      ctx.clip();
    }
    ctx.globalAlpha = apontando ? 0.6 : 1;
    ctx.drawImage(fundo, 0, 0, largCss, altCss);
    ctx.restore();

    facho(apontando ? 0.09 : 0.34, apontando ? 1.4 : 1);

    // brilho so nos pontos por onde o facho acabou de passar
    if (!reduzirMovimento && !apontando) {
      for (const p of pontos) {
        if (p.cor === "sem") continue;
        const atraso = (angulo - p.ang + TAU * 4) % TAU;
        if (atraso > 1 || !jaRevelado(p)) continue;
        const g = Math.exp(-atraso / 0.4);
        ctx.globalAlpha = 0.5 * g;
        ctx.fillStyle = cores[p.cor];
        ctx.beginPath();
        ctx.arc(tx(p.x), ty(p.y), r * (1 + 1.3 * g), 0, TAU);
        ctx.fill();
      }
    }
    ctx.globalAlpha = 1;

    // o farol
    const fx = tx(FAROL[0]);
    const fy = ty(FAROL[1]);
    ctx.fillStyle = "rgba(255, 207, 107, 0.22)";
    ctx.beginPath();
    ctx.arc(fx, fy, r * 4.2, 0, TAU);
    ctx.fill();
    ctx.fillStyle = "#ffcf6b";
    ctx.beginPath();
    ctx.arc(fx, fy, r * 1.8, 0, TAU);
    ctx.fill();

    // cidade escolhida: anel pulsando
    if (apontando) {
      const x = tx(alvo.x);
      const y = ty(alvo.y);
      const pulso = reduzirMovimento ? 0.5 : (Math.sin(agora / 260) + 1) / 2;
      ctx.strokeStyle = `rgba(255, 207, 107, ${0.95 - pulso * 0.55})`;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(x, y, r * (3 + pulso * 3.5), 0, TAU);
      ctx.stroke();
      ctx.fillStyle = "#fff";
      ctx.beginPath();
      ctx.arc(x, y, r * 1.7, 0, TAU);
      ctx.fill();
    }

    const d = pontos[destaque];
    if (d) {
      ctx.strokeStyle = "#fff";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(tx(d.x), ty(d.y), r + 3, 0, TAU);
      ctx.stroke();
    }
  }

  function passo(agora) {
    quadro = 0;
    const dt = Math.min(64, agora - (ultimo || agora));
    ultimo = agora;

    if (modo === "aponta" && alvo) {
      // gira pelo caminho mais curto ate a cidade
      const desejado = Math.atan2(alvo.y - FAROL[1], alvo.x - FAROL[0]);
      const delta = ((desejado - angulo + Math.PI * 3) % TAU) - Math.PI;
      angulo += delta * Math.min(1, dt / 140);
    } else if (percorrido < TAU) {
      const t = Math.min(1, (agora - inicio) / VOLTA_INICIAL);
      const novo = TAU * (1 - (1 - t) ** 3);
      angulo += novo - percorrido;
      percorrido = novo;
    } else {
      angulo += (TAU * dt) / VOLTA;
    }
    angulo = (angulo + TAU) % TAU;

    desenhar(agora);
    agendar();
  }

  function agendar() {
    if (rodando && visivel && !document.hidden && !quadro) quadro = requestAnimationFrame(passo);
  }

  function parar() {
    if (quadro) cancelAnimationFrame(quadro);
    quadro = 0;
    ultimo = 0;
  }

  function pontoNoMouse(ev) {
    const caixa = canvas.getBoundingClientRect();
    const x = (ev.clientX - caixa.left - dx) / escala;
    const y = (ev.clientY - caixa.top - dy) / escala;
    let melhor = -1;
    let menor = 0.55 * 0.55;
    for (let gx = Math.floor(x) - 1; gx <= Math.floor(x) + 1; gx++) {
      for (let gy = Math.floor(y) - 1; gy <= Math.floor(y) + 1; gy++) {
        for (const i of grade.get(`${gx}:${gy}`) || []) {
          const p = pontos[i];
          const dist = (p.x - x) ** 2 + (p.y - y) ** 2;
          if (dist < menor) {
            menor = dist;
            melhor = i;
          }
        }
      }
    }
    return melhor;
  }

  function redesenharSeParado() {
    if (!quadro) desenhar(performance.now());
  }

  function ligarEventos(aoEscolher) {
    const dica = $("dica");
    const hero = canvas.parentElement;
    canvas.addEventListener("mousemove", (ev) => {
      const i = pontoNoMouse(ev);
      if (i !== destaque) {
        destaque = i;
        redesenharSeParado();
      }
      const p = pontos[i];
      if (!p) {
        dica.hidden = true;
        canvas.style.cursor = "";
        return;
      }
      const base = hero.getBoundingClientRect();
      const caixa = canvas.getBoundingClientRect();
      let linha2 = "sem site cadastrado";
      if (p.r) linha2 = p.r.nota != null ? `nota ${fmtNota(p.r.nota)}, conceito ${p.r.conceito}` : "não respondeu";
      dica.replaceChildren(el("strong", { text: p.r ? p.r.municipio : p.nome }), ` ${p.r ? p.r.uf : p.uf}`, el("br"), el("span", { text: linha2 }));
      dica.style.left = caixa.left - base.left + tx(p.x) + "px";
      dica.style.top = caixa.top - base.top + ty(p.y) + "px";
      dica.hidden = false;
      canvas.style.cursor = p.r ? "pointer" : "";
    });
    canvas.addEventListener("mouseleave", () => {
      dica.hidden = true;
      destaque = -1;
      redesenharSeParado();
    });
    canvas.addEventListener("click", (ev) => {
      const p = pontos[pontoNoMouse(ev)];
      if (p && p.r) aoEscolher(p.r);
    });
  }

  function iniciar(lista, semSite, aoEscolher) {
    canvas = $("mapa");
    ctx = canvas.getContext("2d");
    if (preparar(lista, semSite) < 30) {
      canvas.hidden = true;
      return false;
    }
    const css = getComputedStyle(document.documentElement);
    const v = (n) => css.getPropertyValue(n).trim();
    cores = { A: v("--cA"), B: v("--cB"), C: v("--cC"), D: v("--cD"), F: v("--cF"), X: "#5f7489", sem: "#203a55" };

    dimensionar();
    inicioAng = angulo;
    inicio = performance.now();
    if (reduzirMovimento) percorrido = TAU;
    rodando = !reduzirMovimento;
    desenhar(inicio);
    agendar();

    let pendente = false;
    new ResizeObserver(() => {
      if (pendente) return;
      pendente = true;
      requestAnimationFrame(() => {
        pendente = false;
        dimensionar();
        desenhar(performance.now());
      });
    }).observe(canvas);

    // nao gasta bateria animando o que ninguem esta vendo
    new IntersectionObserver((e) => {
      visivel = e[0].isIntersecting;
      visivel ? agendar() : parar();
    }).observe(canvas);
    document.addEventListener("visibilitychange", () => (document.hidden ? parar() : agendar()));

    ligarEventos(aoEscolher);
    return true;
  }

  function apontar(r) {
    alvo = pontos.find((p) => p.r === r) || null;
    if (!alvo) return;
    modo = "aponta";
    percorrido = TAU;
    if (reduzirMovimento) {
      angulo = Math.atan2(alvo.y - FAROL[1], alvo.x - FAROL[0]);
      desenhar(performance.now());
      return;
    }
    rodando = true;
    agendar();
  }

  function ronda() {
    modo = "ronda";
    alvo = null;
    if (reduzirMovimento) return desenhar(performance.now());
    rodando = true;
    agendar();
  }

  return { iniciar, apontar, ronda };
})();

// ===================================================================
// ficha da cidade
// ===================================================================

const detalhesUf = new Map();

function carregarUf(uf) {
  if (!detalhesUf.has(uf)) {
    // guarda a promessa: duas cidades do mesmo estado nao baixam o arquivo duas vezes
    const p = buscarJson(`dados/uf/${encodeURIComponent(uf)}.json`).catch((e) => {
      detalhesUf.delete(uf);
      throw e;
    });
    detalhesUf.set(uf, p);
  }
  return detalhesUf.get(uf);
}

function linkCorrigir(check) {
  return el("a", { href: `${REPO}/blob/main/docs/como-corrigir.md#${check}`, rel: "noopener", text: "como corrigir" });
}

function listaSinais(r) {
  return el(
    "ul",
    { class: "sinais" },
    ...Object.entries(ITENS).map(([check, [nome]], i) => {
      const st = statusSeguro(r.st[check]);
      const luz = el("span", { class: `luz ${st}`, "aria-hidden": "true" });
      luz.style.setProperty("--n", i);
      return el(
        "li",
        {},
        luz,
        el(
          "div",
          {},
          el("strong", {}, nome, el("span", { class: `estado ${st}`, text: STATUS[st] })),
          el("div", { class: "info carregando", "data-check": check }, "carregando detalhe…"),
        ),
      );
    }),
  );
}

function abrirFicha(r) {
  const dialogo = $("ficha");
  const corpo = $("ficha-corpo");

  const placar = el(
    "div",
    { class: "placar" },
    selo(r),
    r.nota != null
      ? el("div", {}, el("strong", { text: fmtNota(r.nota) }), el("span", { text: r.pos ? `${r.pos}º de ${r.totalUf} cidades em ${r.uf}` : "fora do ranking" }))
      : el("div", {}, el("strong", { text: "Sem nota" }), el("span", { text: r.acessivel ? "o domínio precisa de revisão" : "o site não respondeu à verificação" })),
  );

  const copiar = el("button", { type: "button" }, "Copiar link");
  copiar.addEventListener("click", async () => {
    const url = `${location.origin}${location.pathname}#m-${r.ibge}`;
    try {
      await navigator.clipboard.writeText(url);
      copiar.textContent = "Link copiado";
    } catch {
      copiar.textContent = url;
    }
  });
  const titulo = encodeURIComponent(`Contestar resultado: ${r.municipio} (${r.dominio})`);
  const acoes = el("div", { class: "acoes" }, copiar, el("a", { href: `${REPO}/issues/new?title=${titulo}`, rel: "noopener", text: "Contestar resultado" }));

  const avisos = el("div");
  corpo.replaceChildren(
    el("h2", { id: "ficha-nome", text: r.municipio }),
    el("p", { class: "onde", text: `${r.uf}, ${r.dominio}` }),
    placar,
    avisos,
    listaSinais(r),
    acoes,
  );

  carregarUf(r.uf)
    .then((dados) => {
      const extra = dados[r.ibge];
      if (!extra || !corpo.contains(avisos)) return;
      // so troca os textos; as luzes ja acenderam e nao precisam animar de novo
      corpo.querySelectorAll(".sinais .info").forEach((info, i) => {
        const check = info.dataset.check;
        info.classList.remove("carregando");
        info.replaceChildren(String(extra.d[i] ?? ""));
        if (statusSeguro(r.st[check]) !== "pass") info.append(", ", linkCorrigir(check));
      });
      avisos.replaceChildren(...(extra.a || []).filter((a) => AVISOS[a]).map((a) => el("p", { class: "avisos", text: AVISOS[a] })));
    })
    .catch(() => {
      corpo.querySelectorAll(".sinais .carregando").forEach((i) => (i.textContent = "detalhe indisponível agora, tente abrir de novo"));
    });

  if (!dialogo.open) dialogo.showModal();
  dialogo.scrollTop = 0;
  history.replaceState(null, "", `#m-${r.ibge}`);
  Mapa.apontar(r);
}

function iniciarFicha() {
  const dialogo = $("ficha");
  $("fechar-ficha").addEventListener("click", () => dialogo.close());
  // clique no fundo escurecido fecha a gaveta
  dialogo.addEventListener("click", (ev) => {
    const c = dialogo.getBoundingClientRect();
    if (ev.target === dialogo && (ev.clientX > c.right || ev.clientX < c.left)) dialogo.close();
  });
  dialogo.addEventListener("close", () => {
    history.replaceState(null, "", location.pathname);
    Mapa.ronda();
  });
}

function abrirDoLink() {
  const m = location.hash.match(/^#m-(\d{7})$/);
  if (!m) return;
  const r = todos.find((x) => x.ibge === m[1]);
  if (r) abrirFicha(r);
}

// ===================================================================
// busca com sugestoes (combobox)
// ===================================================================

function iniciarBusca() {
  const input = $("busca");
  const lista = $("sugestoes");
  let opcoes = [];
  let ativa = -1;

  function fechar() {
    lista.hidden = true;
    input.setAttribute("aria-expanded", "false");
    input.removeAttribute("aria-activedescendant");
    ativa = -1;
  }

  function marcar(i) {
    ativa = i;
    [...lista.children].forEach((li, j) => li.setAttribute("aria-selected", String(j === i)));
    if (i >= 0) input.setAttribute("aria-activedescendant", `sug-${i}`);
  }

  function escolher(r) {
    fechar();
    input.value = r.municipio;
    abrirFicha(r);
  }

  input.addEventListener("input", () => {
    const termo = semAcento(input.value.trim());
    if (termo.length < 2) return fechar();
    // quem comeca com o que foi digitado vem primeiro
    opcoes = todos
      .filter((r) => r._busca.includes(termo))
      .sort((a, b) => b._nome.startsWith(termo) - a._nome.startsWith(termo) || ordemAlfabetica(a.municipio, b.municipio))
      .slice(0, 6);

    if (!opcoes.length) {
      lista.replaceChildren(el("li", { class: "vazio", role: "option", "aria-disabled": "true" }, "Nenhuma cidade com esse nome. Confira a grafia."));
    } else {
      lista.replaceChildren(
        ...opcoes.map((r, i) => {
          const li = el(
            "li",
            { id: `sug-${i}`, role: "option", "aria-selected": "false" },
            selo(r),
            el("span", { class: "nome" }, r.municipio, el("span", { class: "uf", text: r.uf })),
            el("span", { class: "nota", text: r.nota != null ? fmtNota(r.nota) : "sem nota" }),
          );
          li.addEventListener("mousedown", (ev) => {
            ev.preventDefault();
            escolher(r);
          });
          return li;
        }),
      );
    }
    lista.hidden = false;
    input.setAttribute("aria-expanded", "true");
    marcar(-1);
  });

  input.addEventListener("keydown", (ev) => {
    if (lista.hidden || !opcoes.length) return;
    if (ev.key === "ArrowDown") {
      ev.preventDefault();
      marcar((ativa + 1) % opcoes.length);
    } else if (ev.key === "ArrowUp") {
      ev.preventDefault();
      marcar((ativa - 1 + opcoes.length) % opcoes.length);
    } else if (ev.key === "Enter") {
      ev.preventDefault();
      escolher(opcoes[Math.max(0, ativa)]);
    } else if (ev.key === "Escape") {
      fechar();
    }
  });
  input.addEventListener("blur", () => setTimeout(fechar, 120));
}

// ===================================================================
// secoes de baixo
// ===================================================================

function itens(ok) {
  const linhas = Object.entries(ITENS)
    .map(([check, [nome, texto]]) => ({ check, nome, texto, cumpre: pct(conta(ok, check), ok.length), parcial: pct(conta(ok, check, "warn"), ok.length) }))
    .sort((a, b) => a.cumpre - b.cumpre); // o que mais falta primeiro

  const barras = [];
  const lista = $("lista-itens");
  lista.replaceChildren(
    ...linhas.map((l, i) => {
      const a = el("i", { class: "ok" });
      const b = el("i", { class: "parcial" });
      a.style.setProperty("--n", i);
      b.style.setProperty("--n", i + 0.6);
      barras.push([a, l.cumpre], [b, l.parcial]);
      return el(
        "li",
        {},
        el("div", {}, el("h3", {}, el("a", { href: `${REPO}/blob/main/docs/como-corrigir.md#${l.check}`, rel: "noopener", text: l.nome })), el("p", { text: l.texto })),
        el("div", { class: "trilho", role: "img", "aria-label": `${fmtPct(l.cumpre)} cumprem, ${fmtPct(l.parcial)} cumprem em parte` }, a, b),
        el("span", { class: "valor", text: fmtPct(l.cumpre) }),
      );
    }),
  );
  quandoAparecer(lista, () => barras.forEach(([i, v]) => (i.style.width = v + "%")));
}

function estados(ok) {
  const porUf = {};
  for (const r of ok) (porUf[r.uf] ??= []).push(r.nota);
  const linhas = Object.entries(porUf)
    .map(([uf, notas]) => ({ uf, media: notas.reduce((a, b) => a + b, 0) / notas.length, n: notas.length }))
    .sort((a, b) => b.media - a.media);

  const caixa = $("ladrilhos");
  const ranking = $("ranking-uf");
  const noRanking = {};
  const barras = [];

  ranking.replaceChildren(
    ...linhas.map((l) => {
      const i = el("i", { class: "ok" });
      barras.push([i, l.media]);
      const li = el("li", {}, el("strong", { text: l.uf }), el("div", { class: "trilho", "aria-hidden": "true" }, i), el("span", { class: "media", text: fmtNota(l.media) }));
      noRanking[l.uf] = li;
      return li;
    }),
  );

  const filtrarUf = (uf) => {
    $("filtro-uf").value = uf;
    aplicarFiltros();
    $("cidades").scrollIntoView({ block: "start" });
  };

  caixa.replaceChildren(
    ...linhas.map((l, ordem) => {
      const [col, lin] = LADRILHOS[l.uf] || [1, 1];
      const t = el(
        "button",
        { type: "button", class: `ladrilho t${conceitoDaNota(l.media)}`, role: "listitem", "aria-label": `${l.uf}: nota média ${fmtNota(l.media)}, ${l.n} cidades` },
        el("b", { text: l.uf }),
        el("span", { text: Math.round(l.media) }),
      );
      t.style.gridColumn = col;
      t.style.gridRow = lin;
      t.style.setProperty("--n", ordem);
      t.addEventListener("mouseenter", () => noRanking[l.uf]?.classList.add("ativo"));
      t.addEventListener("mouseleave", () => noRanking[l.uf]?.classList.remove("ativo"));
      t.addEventListener("click", () => filtrarUf(l.uf));
      return t;
    }),
  );
  quandoAparecer(caixa, () => {
    caixa.classList.add("visto");
    barras.forEach(([i, v]) => (i.style.width = v + "%"));
  });
}

function distribuicao(ok) {
  const cont = Object.fromEntries(CONCEITOS.map((c) => [c, 0]));
  for (const r of ok) if (r.conceito) cont[r.conceito]++;
  const barra = $("dist-barra");
  barra.replaceChildren(
    ...CONCEITOS.filter((c) => cont[c]).map((c) => {
      const p = el("span", { title: `${c}: ${num(cont[c])} cidades` });
      p.style.flexGrow = cont[c];
      p.style.background = `var(--c${c})`;
      return p;
    }),
  );
  barra.setAttribute("role", "img");
  barra.setAttribute("aria-label", CONCEITOS.map((c) => `${c}: ${fmtPct(pct(cont[c], ok.length))}`).join(", "));
  $("dist-legenda").replaceChildren(...CONCEITOS.map((c) => el("li", {}, el("b", { text: c }), fmtPct(pct(cont[c], ok.length)))));
  $("distribuicao").hidden = false;
}

// ---------- lista de cidades ----------

function linhaCidade(r) {
  const luzes = el("span", { class: "luzes", "aria-hidden": "true" }, ...Object.keys(ITENS).map((c) => el("i", { class: statusSeguro(r.st[c]) })));
  const botao = el(
    "button",
    { type: "button", class: "linha" },
    el("span", { class: "nome" }, r.municipio || r.dominio, el("span", { class: "dominio", text: r.dominio })),
    el("span", { class: "uf", text: r.uf }),
    ...(r.nota != null
      ? [luzes, el("span", { class: "nota", text: Math.round(r.nota) })]
      : [el("span", { class: "situacao", text: r.acessivel ? "fora do ranking" : "não respondeu" })]),
    selo(r),
  );
  botao.addEventListener("click", () => abrirFicha(r));
  return el("li", {}, botao);
}

function aplicarFiltros() {
  const termo = semAcento($("filtro").value.trim());
  const uf = $("filtro-uf").value;
  const conceito = $("filtro-conceito").value;
  filtrados = todos.filter((r) => {
    if (uf && r.uf !== uf) return false;
    if (conceito === "-" && r.nota != null) return false;
    if (conceito && conceito !== "-" && r.conceito !== conceito) return false;
    if (termo && !r._busca.includes(termo)) return false;
    return true;
  });
  mostrando = 0;
  $("lista").replaceChildren();
  mostrarMais();
}

function mostrarMais() {
  const proximos = filtrados.slice(mostrando, mostrando + POR_PAGINA);
  $("lista").append(...proximos.map(linhaCidade));
  mostrando += proximos.length;
  $("contagem").textContent = filtrados.length
    ? `${num(filtrados.length)} cidades, da maior nota para a menor. Toque em uma para ver o detalhe.`
    : "Nenhuma cidade com esse filtro. Confira a grafia ou procure pelo domínio do site.";
  $("mais").hidden = mostrando >= filtrados.length;
}

// ---------- topo ----------

function contarAte(elemento, valor) {
  if (reduzirMovimento) {
    elemento.textContent = num(valor);
    return;
  }
  const inicio = performance.now();
  const passo = (agora) => {
    const t = Math.min(1, (agora - inicio) / 1400);
    elemento.textContent = num(Math.round(valor * (1 - (1 - t) ** 3)));
    if (t < 1) requestAnimationFrame(passo);
  };
  requestAnimationFrame(passo);
}

function cabecalho(resumo) {
  const data = new Date(resumo.gerado_em).toLocaleDateString("pt-BR", { day: "numeric", month: "long", year: "numeric" });
  const responderam = todos.filter((r) => r.acessivel).length;
  contarAte($("n-total"), resumo.total);
  $("meta").textContent = `Última varredura em ${data}. ${num(responderam)} sites responderam.`;
  if (resumo.amostra) {
    $("aviso-amostra").textContent = `Resultado de teste com uma amostra de ${num(resumo.amostra)} sites. Os números ainda não representam o país.`;
    $("aviso-amostra").hidden = false;
  }
}

function legendaMapa(semSite) {
  const bolinha = (cor) => {
    const i = el("i");
    i.style.background = cor;
    return i;
  };
  const chaves = CONCEITOS.map((c) => el("li", {}, bolinha(`var(--c${c})`), c));
  if (semSite) chaves.push(el("li", {}, bolinha("#203a55"), `sem site cadastrado (${num(semSite)})`));
  $("chaves").replaceChildren(...chaves);
  $("legenda-mapa").hidden = false;
}

function semDados() {
  $("meta").textContent = "Ainda não há resultados publicados. A primeira varredura completa sai na próxima segunda-feira.";
  for (const id of ["itens", "estados", "cidades", "busca-caixa"]) $(id).hidden = true;
}

async function iniciar() {
  const pedidoSemSite = buscarJson("dados/sem_site.json").catch(() => []);
  let resumo;
  try {
    resumo = await buscarJson("dados/resumo.json");
    if (!Array.isArray(resumo.municipios)) throw new Error("formato inesperado");
  } catch {
    semDados();
    return;
  }

  todos = decodificar(resumo).sort((a, b) => (b.nota ?? -1) - (a.nota ?? -1) || ordemAlfabetica(a.municipio, b.municipio));
  ranqueados = todos.filter((r) => r.acessivel && r.ranking);

  // posicao de cada cidade dentro do proprio estado (todos ja esta ordenado por nota)
  const porUf = {};
  for (const r of ranqueados) r.pos = porUf[r.uf] = (porUf[r.uf] || 0) + 1;
  for (const r of ranqueados) r.totalUf = porUf[r.uf];

  cabecalho(resumo);
  iniciarBusca();
  iniciarFicha();

  const semSite = await pedidoSemSite;
  const listaSemSite = Array.isArray(semSite) ? semSite : [];
  if (Mapa.iniciar(todos, listaSemSite, abrirFicha)) legendaMapa(listaSemSite.length);

  const ufs = [...new Set(todos.map((r) => r.uf).filter(Boolean))].sort();
  $("filtro-uf").append(...ufs.map((uf) => el("option", { value: uf, text: uf })));
  aplicarFiltros();
  distribuicao(ranqueados);

  let espera;
  $("filtro").addEventListener("input", () => {
    clearTimeout(espera);
    espera = setTimeout(aplicarFiltros, 150);
  });
  $("filtro-uf").addEventListener("change", aplicarFiltros);
  $("filtro-conceito").addEventListener("change", aplicarFiltros);
  $("mais").addEventListener("click", mostrarMais);
  window.addEventListener("hashchange", abrirDoLink);

  const depois = window.requestIdleCallback || ((f) => setTimeout(f, 120));
  depois(() => {
    itens(ranqueados);
    estados(ranqueados);
    abrirDoLink();
  });
}

iniciar();
