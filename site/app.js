// farol-gov: pagina de resultados
//
// Regra da casa: nada aqui usa innerHTML. O detalhe de cada check pode trazer texto
// vindo do servidor avaliado (header Location, mensagem de erro TLS), entao tudo
// entra como textContent. A CSP com Trusted Types faz o navegador barrar qualquer deslize.
//
// Desempenho: a pagina abre so com dados/resumo.json (uma linha por municipio).
// O detalhe de cada check fica em dados/uf/XX.json e so e baixado quando alguem abre uma cidade.

const REPO = "https://github.com/guilhermeoliveirabrito/farol-gov";
const POR_PAGINA = 40;

const NOMES = {
  https: "HTTPS com certificado válido",
  redirect: "HTTP redireciona para HTTPS",
  tls: "TLS 1.2 ou superior",
  hsts: "HSTS",
  headers: "Headers de segurança",
  security_txt: "security.txt",
  dnssec: "DNSSEC",
  spf: "SPF",
  dmarc: "DMARC",
};

const STATUS = { pass: "ok", warn: "parcial", fail: "falha", error: "erro" };
const CODIGOS = { p: "pass", w: "warn", f: "fail", e: "error" };
const CONCEITOS = ["A", "B", "C", "D", "F"];

const AVISOS = {
  nao_resolve: "O domínio cadastrado no Wikidata não existe no DNS.",
  dominio_alternativo: "O domínio cadastrado não funciona; avaliamos a versão com/sem www.",
  fora_do_gov_br: "Domínio fora do .gov.br. Fica fora do ranking até alguém confirmar que é o site oficial.",
  dominio_compartilhado: "O mesmo domínio aparece para outro município. Fica fora do ranking até revisão.",
};

const $ = (id) => document.getElementById(id);
const num = (n) => n.toLocaleString("pt-BR");
const ordemAlfabetica = new Intl.Collator("pt-BR").compare;

let todos = [];
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

// so deixa passar valores conhecidos pra virar classe CSS
const statusSeguro = (s) => (s in STATUS ? s : "error");
const conceitoSeguro = (c) => (CONCEITOS.includes(c) ? c : null);

const pct = (parte, total) => (total ? (100 * parte) / total : 0);
const fmtPct = (v) => v.toLocaleString("pt-BR", { maximumFractionDigits: 1 }) + "%";

function barra(valor) {
  const i = el("i");
  i.style.width = Math.max(0, Math.min(100, valor)) + "%";
  return el("div", { class: "barra", "aria-hidden": "true" }, i);
}

const semAcento = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const passa = (lista, check) => lista.filter((r) => r.st[check] === "pass").length;

async function buscarJson(url) {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

// transforma a linha compacta do resumo.json num objeto facil de usar
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
    };
  });
}

// ---------- mapa ----------
//
// Canvas em vez de SVG: com ~5.500 pontos, um elemento por ponto pesava no DOM e na rolagem.
// Aqui e um desenho so, e a animacao inteira roda num unico requestAnimationFrame.

const ESCALA_LON = Math.cos((14 * Math.PI) / 180);
const LARGURA_MAPA = 42.4 * ESCALA_LON; // vai ate -32 de longitude pra caber Fernando de Noronha
const ALTURA_MAPA = 39.8;
const RAIO = 0.21;
const DURACAO_FACHO = 1200;

const mapa = { pontos: [], grade: new Map(), escala: 1, dx: 0, dy: 0, destaque: -1, cores: {} };

function prepararMapa(lista, semSite) {
  const proj = (lon, lat) => [(lon + 74.2) * ESCALA_LON, 5.6 - lat];
  const pontos = [];
  for (const [ibge, municipio, uf, lat, lon] of semSite) {
    if (typeof lat !== "number" || typeof lon !== "number") continue;
    const [x, y] = proj(lon, lat);
    pontos.push({ x, y, lon, cor: "sem", r: null, nome: municipio, uf, ibge });
  }
  for (const r of lista) {
    if (typeof r.lat !== "number" || typeof r.lon !== "number") continue;
    const [x, y] = proj(r.lon, r.lat);
    const cor = r.ranking && r.conceito ? r.conceito : "X";
    pontos.push({ x, y, lon: r.lon, cor, r });
  }
  // sem site por baixo; o resto em ordem pseudoaleatoria fixa (pelo codigo IBGE)
  const embaralho = (p) => Math.imul(Number(p.r ? p.r.ibge : p.ibge), 2654435761) >>> 0;
  pontos.sort((a, b) => (b.cor === "sem") - (a.cor === "sem") || embaralho(a) - embaralho(b));
  // grade espacial pra achar o ponto debaixo do mouse sem varrer tudo
  const grade = new Map();
  pontos.forEach((p, i) => {
    const chave = `${Math.floor(p.x)}:${Math.floor(p.y)}`;
    if (!grade.has(chave)) grade.set(chave, []);
    grade.get(chave).push(i);
  });
  mapa.pontos = pontos;
  mapa.grade = grade;
}

function lerCores() {
  const css = getComputedStyle(document.documentElement);
  const v = (nome) => css.getPropertyValue(nome).trim();
  mapa.cores = { A: v("--cA"), B: v("--cB"), C: v("--cC"), D: v("--cD"), F: v("--cF"), X: "#5d7186", sem: "#2a4560" };
}

function desenharMapa(progresso = 1) {
  const canvas = $("mapa");
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // o facho passa de leste (-34) a oeste (-74)
  const limite = -34 - progresso * 41;
  const r = RAIO * mapa.escala;
  // os pontos ja estao embaralhados (ver prepararMapa): assim nenhuma cor fica sempre
  // por cima nas regioes densas e o mapa nao exagera nem esconde notas boas ou ruins
  let corAtual = null;
  ctx.beginPath();
  for (const p of mapa.pontos) {
    if (p.lon < limite) continue;
    if (p.cor !== corAtual) {
      if (corAtual) ctx.fill();
      ctx.fillStyle = mapa.cores[p.cor];
      corAtual = p.cor;
      ctx.beginPath();
    }
    const x = mapa.dx + p.x * mapa.escala;
    const y = mapa.dy + p.y * mapa.escala;
    ctx.moveTo(x + r, y);
    ctx.arc(x, y, r, 0, Math.PI * 2);
  }
  if (corAtual) ctx.fill();

  const d = mapa.pontos[mapa.destaque];
  if (d && progresso >= 1) {
    ctx.strokeStyle = "#fff";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(mapa.dx + d.x * mapa.escala, mapa.dy + d.y * mapa.escala, r + 2, 0, Math.PI * 2);
    ctx.stroke();
  }
}

function dimensionarMapa() {
  const canvas = $("mapa");
  const larg = canvas.clientWidth;
  const alt = canvas.clientHeight;
  if (!larg || !alt) return;
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.round(larg * dpr);
  canvas.height = Math.round(alt * dpr);
  mapa.escala = Math.min(larg / LARGURA_MAPA, alt / ALTURA_MAPA);
  mapa.dx = (larg - LARGURA_MAPA * mapa.escala) / 2;
  mapa.dy = (alt - ALTURA_MAPA * mapa.escala) / 2;
}

function pontoNoMouse(ev) {
  const caixa = $("mapa").getBoundingClientRect();
  const x = (ev.clientX - caixa.left - mapa.dx) / mapa.escala;
  const y = (ev.clientY - caixa.top - mapa.dy) / mapa.escala;
  let melhor = -1;
  let menor = 0.6 * 0.6; // raio de busca, em graus
  for (let gx = Math.floor(x) - 1; gx <= Math.floor(x) + 1; gx++) {
    for (let gy = Math.floor(y) - 1; gy <= Math.floor(y) + 1; gy++) {
      for (const i of mapa.grade.get(`${gx}:${gy}`) || []) {
        const p = mapa.pontos[i];
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

function iniciarMapa(lista, semSite) {
  prepararMapa(lista, semSite);
  // dado antigo sem coordenada: melhor nao mostrar mapa nenhum do que um mapa vazio
  if (mapa.pontos.filter((p) => p.r).length < 30) return;

  const fig = $("mapa-fig");
  const canvas = $("mapa");
  fig.hidden = false;
  lerCores();
  dimensionarMapa();

  const chaves = CONCEITOS.map((c) => el("li", {}, el("i", { class: "c" + c }), c));
  if (semSite.length) chaves.push(el("li", {}, el("i", { class: "sem" }), `sem site (${num(semSite.length)})`));
  $("chaves").replaceChildren(...chaves);

  // a unica animacao da pagina; quem pede menos movimento ve o mapa pronto
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
    desenharMapa(1);
  } else {
    const inicio = performance.now();
    const passo = (agora) => {
      const t = Math.min(1, (agora - inicio) / DURACAO_FACHO);
      desenharMapa(1 - (1 - t) ** 2);
      if (t < 1) requestAnimationFrame(passo);
    };
    requestAnimationFrame(passo);
  }

  let pendente = false;
  new ResizeObserver(() => {
    if (pendente) return;
    pendente = true;
    requestAnimationFrame(() => {
      pendente = false;
      dimensionarMapa();
      desenharMapa(1);
    });
  }).observe(canvas);

  const dica = $("dica");
  canvas.addEventListener("mousemove", (ev) => {
    const i = pontoNoMouse(ev);
    if (i !== mapa.destaque) {
      mapa.destaque = i;
      desenharMapa(1);
    }
    const p = mapa.pontos[i];
    if (!p) {
      dica.hidden = true;
      canvas.style.cursor = "";
      return;
    }
    const caixa = fig.getBoundingClientRect();
    const quadro = canvas.getBoundingClientRect();
    let linha2 = "sem site cadastrado";
    if (p.r) linha2 = p.r.nota != null ? `nota ${num(p.r.nota)}, conceito ${p.r.conceito}` : "sem nota";
    dica.replaceChildren(el("strong", { text: p.r ? p.r.municipio : p.nome }), ` ${p.r ? p.r.uf : p.uf}`, el("br"), el("span", { text: linha2 }));
    dica.style.left = quadro.left - caixa.left + mapa.dx + p.x * mapa.escala + "px";
    dica.style.top = quadro.top - caixa.top + mapa.dy + p.y * mapa.escala + "px";
    dica.hidden = false;
    canvas.style.cursor = p.r ? "pointer" : "";
  });
  canvas.addEventListener("mouseleave", () => {
    dica.hidden = true;
    mapa.destaque = -1;
    desenharMapa(1);
  });
  canvas.addEventListener("click", (ev) => {
    const p = mapa.pontos[pontoNoMouse(ev)];
    if (p && p.r) location.hash = `m-${p.r.ibge}`;
  });
}

// ---------- achados ----------

function achados(ok) {
  if (!ok.length) return;
  const semDmarc = 1 - passa(ok, "dmarc") / ok.length;
  const semRedirect = 100 - pct(passa(ok, "redirect"), ok.length);
  const dnssec = pct(passa(ok, "dnssec"), ok.length);

  const frases = [
    [`${Math.round(semDmarc * 10)} em 10`, "prefeituras não impedem que golpistas mandem e-mails falsos usando o nome delas."],
    [fmtPct(semRedirect), "dos sites ainda abrem sem criptografia quando alguém digita o endereço sem https."],
    [fmtPct(dnssec), "das prefeituras usam DNSSEC, a assinatura que impede o desvio do endereço do site."],
  ];
  $("achados").replaceChildren(...frases.map(([n, t]) => el("p", { class: "achado" }, el("strong", { text: n }), t)));
  $("achados").hidden = false;
}

function distribuicao(ok) {
  if (!ok.length) return;
  const cont = Object.fromEntries(CONCEITOS.map((c) => [c, 0]));
  for (const r of ok) if (r.conceito) cont[r.conceito]++;

  const partes = CONCEITOS.filter((c) => cont[c]).map((c) => {
    const p = el("span", { class: `parte c${c}`, title: `${c}: ${num(cont[c])} municípios` });
    p.style.flexGrow = cont[c];
    return p;
  });
  const barraDist = $("dist-barra");
  barraDist.replaceChildren(...partes);
  barraDist.setAttribute("role", "img");
  barraDist.setAttribute("aria-label", CONCEITOS.map((c) => `${c}: ${fmtPct(pct(cont[c], ok.length))}`).join(", "));

  $("dist-legenda").replaceChildren(
    ...CONCEITOS.map((c) => el("li", {}, el("b", { text: c }), fmtPct(pct(cont[c], ok.length)))),
  );
  $("distribuicao").hidden = false;
}

// ---------- detalhes (sob demanda) ----------

const detalhesUf = new Map();

function carregarUf(uf) {
  if (!detalhesUf.has(uf)) {
    // guarda a promessa, assim duas cidades do mesmo estado nao baixam o arquivo duas vezes
    const p = buscarJson(`dados/uf/${encodeURIComponent(uf)}.json`).catch((e) => {
      detalhesUf.delete(uf);
      throw e;
    });
    detalhesUf.set(uf, p);
  }
  return detalhesUf.get(uf);
}

function tabelaDetalhes(r, textos) {
  const corpo = el("tbody");
  Object.entries(NOMES).forEach(([check, nome], i) => {
    const st = statusSeguro(r.st[check]);
    const ajuda = st === "pass" ? null : el("a", { href: `${REPO}/blob/main/docs/como-corrigir.md#${check}`, rel: "noopener", text: "como corrigir" });
    const detalhe = textos ? String(textos[i] ?? "") : "";
    corpo.append(
      el(
        "tr",
        {},
        el("td", {}, el("span", { class: `status ${st}`, text: STATUS[st] })),
        el("td", {}, el("strong", { text: nome }), el("div", { class: "info" }, detalhe, detalhe && ajuda && ", ", ajuda)),
      ),
    );
  });
  return el("table", {}, corpo);
}

function acoes(r) {
  const copiar = el("button", { type: "button", class: "link" }, "Copiar link");
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
  return el(
    "p",
    { class: "acoes" },
    r.nota != null ? el("span", { text: `Nota ${num(r.nota)} de 100` }) : null,
    copiar,
    el("a", { href: `${REPO}/issues/new?title=${titulo}`, rel: "noopener", text: "Contestar resultado" }),
  );
}

function montarDetalhes(r) {
  // mostra os status na hora e completa com os textos quando o arquivo do estado chegar
  const caixa = el("div", { class: "detalhes" }, tabelaDetalhes(r, null), acoes(r));
  carregarUf(r.uf)
    .then((dados) => {
      const extra = dados[r.ibge];
      if (!extra) return;
      const avisos = (extra.a || []).filter((a) => AVISOS[a]).map((a) => el("p", { class: "avisos", text: AVISOS[a] }));
      caixa.replaceChildren(...avisos, tabelaDetalhes(r, extra.d), acoes(r));
    })
    .catch(() => {
      caixa.append(el("p", { class: "avisos", text: "Não foi possível carregar o detalhe de cada item. Tente abrir de novo." }));
    });
  return caixa;
}

// ---------- lista de municipios ----------

function linhaMunicipio(r) {
  const selo = r.conceito
    ? el("span", { class: `conceito ${r.conceito}`, title: `Nota ${r.nota}`, text: r.conceito })
    : el("span", { class: "conceito sem", title: "Sem nota", text: "–" });

  const resumo = el(
    "summary",
    {},
    el(
      "span",
      { class: "nome" },
      el("span", { class: "nome-texto", text: r.municipio || r.dominio }),
      el("span", { class: "dominio", text: r.dominio }),
    ),
    el("span", { class: "sigla", text: r.uf }),
    r.nota != null
      ? el("span", { class: "pontos" }, el("span", { text: r.nota.toFixed(0) }), barra(r.nota))
      : el("span", { class: "situacao", text: r.acessivel ? "fora do ranking" : "não respondeu" }),
    selo,
  );

  const det = el("details", { id: `m-${r.ibge}` }, resumo);
  det.addEventListener("toggle", () => {
    if (det.open && det.childElementCount === 1) det.append(montarDetalhes(r));
    if (det.open) history.replaceState(null, "", `#m-${r.ibge}`);
  });
  return el("li", {}, det);
}

function aplicarFiltros() {
  const termo = semAcento($("busca").value.trim());
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
  $("lista").append(...proximos.map(linhaMunicipio));
  mostrando += proximos.length;

  $("contagem").textContent = filtrados.length
    ? `Mostrando ${num(mostrando)} de ${num(filtrados.length)} municípios, da maior nota para a menor.`
    : "Nenhum município com esse nome. Confira a grafia ou procure pelo domínio do site.";
  $("mais").hidden = mostrando >= filtrados.length;
}

// abre direto o municipio quando a pagina chega com #m-<ibge>
function abrirDoLink() {
  const m = location.hash.match(/^#m-(\d{7})$/);
  if (!m) return;
  const r = todos.find((x) => x.ibge === m[1]);
  if (!r) return;
  $("busca").value = r.dominio;
  $("filtro-uf").value = "";
  $("filtro-conceito").value = "";
  aplicarFiltros();
  const det = document.getElementById(`m-${r.ibge}`);
  if (det) {
    det.open = true;
    det.scrollIntoView({ block: "start" });
  }
}

function buscarDoTopo() {
  $("busca").value = $("busca-hero").value;
  aplicarFiltros();
  $("cidades").scrollIntoView({ block: "start" });
}

// ---------- estados e itens ----------

function rankingEstados(ok) {
  const porUf = {};
  for (const r of ok) (porUf[r.uf] ??= []).push(r.nota);

  const linhas = Object.entries(porUf)
    .map(([uf, notas]) => ({ uf, media: notas.reduce((a, b) => a + b, 0) / notas.length, n: notas.length }))
    .sort((a, b) => b.media - a.media);

  $("lista-uf").replaceChildren(
    ...linhas.map((l) =>
      el(
        "li",
        {},
        el("strong", { text: l.uf }),
        el("span", { class: "media", text: l.media.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) }),
        barra(l.media),
        el("span", { class: "qtd", text: `${num(l.n)} ${l.n === 1 ? "cidade" : "cidades"}` }),
      ),
    ),
  );
}

function adocao(ok) {
  const legenda = el(
    "div",
    { class: "legenda" },
    el("span", {}, el("i", { class: "ok" }), "atende"),
    el("span", {}, el("i", { class: "parcial" }), "parcial"),
  );

  const itens = Object.entries(NOMES).map(([check, nome]) => {
    const atende = pct(passa(ok, check), ok.length);
    const parcial = pct(ok.filter((r) => r.st[check] === "warn").length, ok.length);
    const a = el("i", { class: "ok" });
    const b = el("i", { class: "parcial" });
    a.style.width = atende + "%";
    b.style.width = parcial + "%";
    return el(
      "div",
      { class: "item" },
      el("a", { href: `${REPO}/blob/main/docs/como-corrigir.md#${check}`, rel: "noopener", text: nome }),
      el("div", { class: "barra", role: "img", "aria-label": `${fmtPct(atende)} atende, ${fmtPct(parcial)} parcial` }, a, b),
      el("span", { class: "valor", text: fmtPct(atende) }),
    );
  });
  $("adocao").replaceChildren(legenda, ...itens);
}

// ---------- inicio ----------

function cabecalho(resumo) {
  const data = new Date(resumo.gerado_em).toLocaleDateString("pt-BR", { day: "numeric", month: "long", year: "numeric" });
  const acessiveis = todos.filter((r) => r.acessivel).length;
  $("meta").textContent =
    `Última varredura em ${data}: ${num(resumo.total)} sites verificados, ${num(acessiveis)} responderam.`;

  if (resumo.amostra) {
    $("aviso-amostra").textContent =
      `Resultado de teste com uma amostra de ${num(resumo.amostra)} sites, não a varredura completa. ` +
      "Os números ainda não representam o país.";
    $("aviso-amostra").hidden = false;
  }
}

function semDados() {
  $("meta").textContent = "Ainda não há resultados publicados. A primeira varredura completa sai na próxima segunda-feira.";
  for (const id of ["cidades", "estados", "itens"]) $(id).hidden = true;
  document.querySelector(".busca-hero").hidden = true;
}

async function iniciar() {
  // os dois arquivos saem em paralelo; o de municipios sem site e opcional
  const pedidoSemSite = buscarJson("dados/sem_site.json").catch(() => []);
  let resumo;
  try {
    resumo = await buscarJson("dados/resumo.json");
    if (!Array.isArray(resumo.municipios)) throw new Error("formato inesperado");
  } catch {
    semDados();
    return;
  }

  // melhores primeiro; sem nota vai pro fim
  todos = decodificar(resumo).sort((a, b) => (b.nota ?? -1) - (a.nota ?? -1) || ordemAlfabetica(a.municipio, b.municipio));
  const ok = todos.filter((r) => r.acessivel && r.ranking);

  cabecalho(resumo);
  achados(ok);
  distribuicao(ok);

  const ufs = [...new Set(todos.map((r) => r.uf).filter(Boolean))].sort();
  $("filtro-uf").append(...ufs.map((uf) => el("option", { value: uf, text: uf })));
  aplicarFiltros();

  let espera;
  $("busca").addEventListener("input", () => {
    clearTimeout(espera);
    espera = setTimeout(aplicarFiltros, 150);
  });
  $("busca-hero").addEventListener("keydown", (ev) => ev.key === "Enter" && buscarDoTopo());
  $("ir-busca").addEventListener("click", buscarDoTopo);
  $("filtro-uf").addEventListener("change", aplicarFiltros);
  $("filtro-conceito").addEventListener("change", aplicarFiltros);
  $("mais").addEventListener("click", mostrarMais);
  window.addEventListener("hashchange", abrirDoLink);
  abrirDoLink();

  const semSite = await pedidoSemSite;
  iniciarMapa(todos, Array.isArray(semSite) ? semSite : []);

  // o que fica la embaixo pode esperar o navegador ficar livre
  const depois = window.requestIdleCallback || ((f) => setTimeout(f, 200));
  depois(() => {
    rankingEstados(ok);
    adocao(ok);
  });
}

iniciar();
