// farol-gov: pagina de resultados
//
// Regra da casa: nada aqui usa innerHTML. O detalhe de cada check pode trazer texto
// vindo do servidor avaliado (header Location, mensagem de erro TLS), entao tudo
// entra como textContent. A CSP com Trusted Types faz o navegador barrar qualquer deslize.

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
const CONCEITOS = ["A", "B", "C", "D", "F"];

const AVISOS = {
  nao_resolve: "O domínio cadastrado no Wikidata não existe no DNS.",
  dominio_alternativo: "O domínio cadastrado não funciona; avaliamos a versão com/sem www.",
  fora_do_gov_br: "Domínio fora do .gov.br. Fica fora do ranking até alguém confirmar que é o site oficial.",
  dominio_compartilhado: "O mesmo domínio aparece para outro município. Fica fora do ranking até revisão.",
};

const $ = (id) => document.getElementById(id);
const num = (n) => n.toLocaleString("pt-BR");

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
function statusSeguro(s) {
  return s in STATUS ? s : "error";
}

function conceitoSeguro(c) {
  return CONCEITOS.includes(c) ? c : null;
}

function pct(parte, total) {
  return total ? (100 * parte) / total : 0;
}

function fmtPct(v) {
  return v.toLocaleString("pt-BR", { maximumFractionDigits: 1 }) + "%";
}

function barra(valor) {
  const i = el("i");
  i.style.width = Math.max(0, Math.min(100, valor)) + "%";
  return el("div", { class: "barra", "aria-hidden": "true" }, i);
}

function semAcento(s) {
  return s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

function noRanking(r) {
  return r.acessivel && r.ranking !== false;
}

// ---------- resumo do topo ----------

function indicadores(ok) {
  const conta = (check) => ok.filter((r) => r.checks[check]?.status === "pass").length;
  const cartoes = [
    [num(ok.length), "municípios no ranking", ""],
    [fmtPct(pct(conta("https"), ok.length)), "têm HTTPS com certificado válido", "https"],
    [fmtPct(pct(conta("dmarc"), ok.length)), "bloqueiam e-mail falso (DMARC)", "dmarc"],
    [fmtPct(pct(conta("dnssec"), ok.length)), "usam DNSSEC", "dnssec"],
  ];
  $("indicadores").replaceChildren(
    ...cartoes.map(([v, t, check]) =>
      el("div", { class: "indicador" + (check ? " " + check : "") }, el("strong", { text: v }), el("span", { text: t })),
    ),
  );
}

function distribuicao(ok) {
  if (!ok.length) return;
  const cont = Object.fromEntries(CONCEITOS.map((c) => [c, 0]));
  for (const r of ok) if (conceitoSeguro(r.conceito)) cont[r.conceito]++;

  const partes = CONCEITOS.filter((c) => cont[c]).map((c) => {
    const p = el("span", { class: `parte c${c}`, title: `${c}: ${num(cont[c])} municípios` });
    p.style.flexGrow = cont[c];
    return p;
  });
  $("dist-barra").replaceChildren(...partes);
  $("dist-barra").setAttribute(
    "aria-label",
    CONCEITOS.map((c) => `${c}: ${fmtPct(pct(cont[c], ok.length))}`).join(", "),
  );
  $("dist-barra").setAttribute("role", "img");

  $("dist-legenda").replaceChildren(
    ...CONCEITOS.map((c) =>
      el("li", {}, el("span", { class: `conceito ${c}`, text: c }), el("span", {}, fmtPct(pct(cont[c], ok.length)), el("small", { text: ` · ${num(cont[c])}` }))),
    ),
  );
  $("distribuicao").hidden = false;
}

// ---------- lista de municipios ----------

function tabelaDetalhes(r) {
  const corpo = el("tbody");
  for (const [check, nome] of Object.entries(NOMES)) {
    const c = r.checks[check];
    if (!c) continue;
    const st = statusSeguro(c.status);
    const ajuda = st === "pass" ? null : el("a", { href: `${REPO}/blob/main/docs/como-corrigir.md#${check}`, rel: "noopener", text: "como corrigir" });
    corpo.append(
      el(
        "tr",
        {},
        el("td", {}, el("span", { class: `status ${st}`, text: STATUS[st] })),
        el("td", {}, el("strong", { text: nome }), el("div", { class: "info" }, c.detalhe, ajuda && " · ", ajuda)),
      ),
    );
  }
  return el("table", {}, corpo);
}

function montarDetalhes(r) {
  const avisos = (r.avisos || []).filter((a) => AVISOS[a]).map((a) => el("p", { class: "avisos", text: AVISOS[a] }));

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
  const acoes = el(
    "p",
    { class: "acoes" },
    r.nota != null ? el("span", { text: `Nota ${num(r.nota)} de 100` }) : null,
    copiar,
    el("a", { href: `${REPO}/issues/new?title=${titulo}`, rel: "noopener", text: "Contestar resultado" }),
  );

  return el("div", { class: "detalhes" }, ...avisos, tabelaDetalhes(r), acoes);
}

function linhaMunicipio(r) {
  const conceito = conceitoSeguro(r.conceito);
  const selo = conceito
    ? el("span", { class: `conceito ${conceito}`, title: `Nota ${r.nota}`, text: conceito })
    : el("span", { class: "conceito sem", title: "Sem nota", text: "–" });

  const resumo = el(
    "summary",
    {},
    el("span", { class: "nome" }, r.municipio || r.dominio, el("span", { class: "dominio", text: r.dominio })),
    el("span", { class: "uf sigla", text: r.uf }),
    r.nota != null ? barra(r.nota) : el("span", { class: "uf", text: r.acessivel ? "fora do ranking" : "sem resposta" }),
    selo,
  );

  const det = el("details", { id: `m-${r.ibge}` }, resumo);
  // a tabela so e montada quando abre: com milhares de municipios faz diferenca
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
    ? `Mostrando ${num(mostrando)} de ${num(filtrados.length)} municípios`
    : "Nenhum município encontrado.";
  $("mais").hidden = mostrando >= filtrados.length;
}

// abre direto o municipio quando a pagina chega com #m-<ibge>
function abrirDoLink() {
  const m = location.hash.match(/^#m-(\d{7})$/);
  if (!m) return;
  const r = todos.find((x) => x.ibge === m[1]);
  if (!r) return;
  $("busca").value = r.municipio;
  aplicarFiltros();
  const det = document.getElementById(`m-${r.ibge}`);
  if (det) {
    det.open = true;
    det.scrollIntoView({ block: "center" });
  }
}

// ---------- estados e itens ----------

function rankingEstados(ok) {
  const porUf = {};
  for (const r of ok) (porUf[r.uf] ??= []).push(r.nota);

  const linhas = Object.entries(porUf)
    .map(([uf, notas]) => ({ uf, media: notas.reduce((a, b) => a + b, 0) / notas.length, n: notas.length }))
    .sort((a, b) => b.media - a.media);

  document.querySelector("#tabela-uf tbody").replaceChildren(
    ...linhas.map((l, i) =>
      el(
        "tr",
        {},
        el("td", { text: i + 1 }),
        el("td", {}, el("strong", { text: l.uf })),
        el("td", {}, el("div", { class: "com-barra" }, l.media.toFixed(1), barra(l.media))),
        el("td", { class: "num", text: num(l.n) }),
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
    const st = ok.map((r) => r.checks[check]?.status);
    const passa = pct(st.filter((s) => s === "pass").length, ok.length);
    const parcial = pct(st.filter((s) => s === "warn").length, ok.length);
    const a = el("i", { class: "ok" });
    const b = el("i", { class: "parcial" });
    a.style.width = passa + "%";
    b.style.width = parcial + "%";
    return el(
      "div",
      { class: "item" },
      el("a", { href: `${REPO}/blob/main/docs/como-corrigir.md#${check}`, rel: "noopener", text: nome }),
      el("div", { class: "barra", role: "img", "aria-label": `${fmtPct(passa)} atende, ${fmtPct(parcial)} parcial` }, a, b),
      el("span", { class: "valor", text: fmtPct(passa) }),
    );
  });
  $("adocao").replaceChildren(legenda, ...itens);
}

// ---------- inicio ----------

function cabecalho(dados) {
  const data = new Date(dados.gerado_em).toLocaleDateString("pt-BR", { day: "numeric", month: "long", year: "numeric" });
  const acessiveis = dados.resultados.filter((r) => r.acessivel).length;
  $("meta").textContent =
    `Última varredura em ${data}: ${num(dados.total)} domínios verificados, ${num(acessiveis)} responderam.`;

  if (dados.amostra) {
    $("aviso-amostra").textContent =
      `Resultado de teste com uma amostra de ${num(dados.amostra)} domínios, não a varredura completa. ` +
      "Os números ainda não representam o país.";
    $("aviso-amostra").hidden = false;
  }
}

function semDados() {
  $("meta").textContent = "Ainda não há resultados publicados. A primeira varredura completa sai na próxima segunda-feira.";
  for (const id of ["cidades", "estados", "itens"]) $(id).hidden = true;
}

async function iniciar() {
  let dados;
  try {
    const resp = await fetch("dados/latest.json");
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    dados = await resp.json();
    if (!Array.isArray(dados.resultados)) throw new Error("formato inesperado");
  } catch {
    semDados();
    return;
  }

  // melhores primeiro; sem nota vai pro fim
  todos = dados.resultados
    .filter((r) => r && typeof r === "object" && r.checks)
    .map((r) => ({ ...r, municipio: String(r.municipio ?? ""), _busca: semAcento(`${r.municipio} ${r.dominio}`) }))
    .sort((a, b) => (b.nota ?? -1) - (a.nota ?? -1) || a.municipio.localeCompare(b.municipio, "pt-BR"));
  const ok = todos.filter(noRanking);

  cabecalho(dados);
  indicadores(ok);
  distribuicao(ok);
  rankingEstados(ok);
  adocao(ok);

  const ufs = [...new Set(todos.map((r) => r.uf).filter(Boolean))].sort();
  $("filtro-uf").append(...ufs.map((uf) => el("option", { value: uf, text: uf })));

  aplicarFiltros();
  abrirDoLink();

  let espera;
  $("busca").addEventListener("input", () => {
    clearTimeout(espera);
    espera = setTimeout(aplicarFiltros, 150);
  });
  $("filtro-uf").addEventListener("change", aplicarFiltros);
  $("filtro-conceito").addEventListener("change", aplicarFiltros);
  $("mais").addEventListener("click", mostrarMais);
  window.addEventListener("hashchange", abrirDoLink);
}

iniciar();
