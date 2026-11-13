// farol-gov: pagina de resultados
// Nada aqui usa innerHTML com dado externo: detalhe de check pode trazer texto
// vindo do servidor avaliado (header Location, mensagem de erro TLS etc).

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

const AVISOS = {
  nao_resolve: "O domínio cadastrado no Wikidata não existe no DNS.",
  dominio_alternativo: "O domínio cadastrado não funciona; avaliamos a versão com/sem www.",
  fora_do_gov_br: "Domínio fora do .gov.br. Fica fora do ranking até alguém confirmar que é o site oficial.",
  dominio_compartilhado: "O mesmo domínio aparece para outro município. Fica fora do ranking até revisão.",
};

const REPO = "https://github.com/guilhermeoliveirabrito/farol-gov";
const POR_PAGINA = 40;

let todos = [];
let filtrados = [];
let mostrando = 0;

function el(tag, attrs = {}, ...filhos) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") e.className = v;
    else if (k === "text") e.textContent = v;
    else e.setAttribute(k, v);
  }
  for (const f of filhos) {
    if (f == null) continue;
    e.append(f instanceof Node ? f : document.createTextNode(String(f)));
  }
  return e;
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

// ---------- indicadores ----------

function indicadores(lista) {
  const ok = lista.filter(noRanking);
  const conta = (check, st = "pass") => ok.filter((r) => r.checks[check]?.status === st).length;
  const cartoes = [
    [ok.length.toLocaleString("pt-BR"), "municípios no ranking"],
    [fmtPct(pct(conta("https"), ok.length)), "com HTTPS e certificado válido"],
    [fmtPct(pct(conta("dmarc"), ok.length)), "bloqueiam e-mail falso (DMARC)"],
    [fmtPct(pct(conta("dnssec"), ok.length)), "usam DNSSEC"],
  ];
  const alvo = document.getElementById("indicadores");
  alvo.replaceChildren(...cartoes.map(([v, t]) => el("div", { class: "indicador" }, el("strong", { text: v }), el("span", { text: t }))));
}

// ---------- lista de municipios ----------

function linhaMunicipio(r) {
  const temNota = r.nota != null;
  const conceito = temNota
    ? el("span", { class: `conceito ${r.conceito}`, title: `Nota ${r.nota}` }, r.conceito)
    : el("span", { class: "conceito sem", title: "Sem nota" }, "–");

  const resumo = el(
    "summary",
    {},
    el("span", { class: "nome" }, r.municipio || r.dominio, el("span", { class: "dominio", text: r.dominio })),
    el("span", { class: "uf", text: r.uf }),
    temNota ? barra(r.nota) : el("span", { class: "uf", text: r.acessivel ? "" : "sem resposta" }),
    conceito,
  );

  const tabela = el("table");
  for (const [check, nome] of Object.entries(NOMES)) {
    const c = r.checks[check];
    if (!c) continue;
    const ajuda = el("a", { href: `${REPO}/blob/main/docs/como-corrigir.md#${check}`, text: "como corrigir" });
    tabela.append(
      el(
        "tr",
        {},
        el("td", {}, el("span", { class: `status ${c.status}`, text: STATUS[c.status] || c.status })),
        el(
          "td",
          {},
          el("strong", { text: nome }),
          el("div", { class: "info" }, c.detalhe, c.status === "pass" ? null : " · ", c.status === "pass" ? null : ajuda),
        ),
      ),
    );
  }

  const avisos = (r.avisos || []).filter((a) => AVISOS[a]).map((a) => el("p", { class: "avisos", text: AVISOS[a] }));

  const titulo = encodeURIComponent(`Contestar resultado: ${r.municipio} (${r.dominio})`);
  const acoes = el(
    "p",
    { class: "acoes" },
    temNota ? `Nota ${r.nota.toLocaleString("pt-BR")} de 100. ` : "",
    el("a", { href: `${REPO}/issues/new?title=${titulo}`, text: "Contestar este resultado" }),
  );

  return el("li", {}, el("details", {}, resumo, el("div", { class: "detalhes" }, ...avisos, tabela, acoes)));
}

function aplicarFiltros() {
  const termo = semAcento(document.getElementById("busca").value.trim());
  const uf = document.getElementById("filtro-uf").value;
  const conceito = document.getElementById("filtro-conceito").value;

  filtrados = todos.filter((r) => {
    if (uf && r.uf !== uf) return false;
    if (conceito === "-" && r.nota != null) return false;
    if (conceito && conceito !== "-" && r.conceito !== conceito) return false;
    if (termo && !semAcento(`${r.municipio} ${r.dominio}`).includes(termo)) return false;
    return true;
  });

  mostrando = 0;
  document.getElementById("lista").replaceChildren();
  mostrarMais();
}

function mostrarMais() {
  const lista = document.getElementById("lista");
  const proximos = filtrados.slice(mostrando, mostrando + POR_PAGINA);
  lista.append(...proximos.map(linhaMunicipio));
  mostrando += proximos.length;

  const total = filtrados.length.toLocaleString("pt-BR");
  document.getElementById("contagem").textContent = filtrados.length
    ? `Mostrando ${mostrando.toLocaleString("pt-BR")} de ${total} municípios`
    : "Nenhum município encontrado.";
  document.getElementById("mais").hidden = mostrando >= filtrados.length;
}

// ---------- estados ----------

function rankingEstados(lista) {
  const porUf = {};
  for (const r of lista.filter(noRanking)) (porUf[r.uf] ??= []).push(r.nota);

  const linhas = Object.entries(porUf)
    .map(([uf, notas]) => ({ uf, media: notas.reduce((a, b) => a + b, 0) / notas.length, n: notas.length }))
    .sort((a, b) => b.media - a.media);

  const tbody = document.querySelector("#tabela-uf tbody");
  tbody.replaceChildren(
    ...linhas.map((l, i) =>
      el(
        "tr",
        {},
        el("td", { text: i + 1 }),
        el("td", {}, el("strong", { text: l.uf })),
        el("td", {}, el("div", { class: "com-barra" }, l.media.toFixed(1), barra(l.media))),
        el("td", { class: "num", text: l.n }),
      ),
    ),
  );
}

// ---------- adocao ----------

function adocao(lista) {
  const ok = lista.filter(noRanking);
  const alvo = document.getElementById("adocao");
  const legenda = el("div", { class: "legenda" }, el("span", {}, el("i", { class: "ok" }), "atende"), el("span", {}, el("i", { class: "parcial" }), "parcial"));

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
      el("span", { text: nome }),
      el("div", { class: "barra", role: "img", "aria-label": `${fmtPct(passa)} atende, ${fmtPct(parcial)} parcial` }, a, b),
      el("span", { class: "valor", text: fmtPct(passa) }),
    );
  });
  alvo.replaceChildren(legenda, ...itens);
}

// ---------- inicio ----------

function cabecalho(dados) {
  const data = new Date(dados.gerado_em).toLocaleDateString("pt-BR", { day: "numeric", month: "long", year: "numeric" });
  const acessiveis = dados.resultados.filter((r) => r.acessivel).length;
  document.getElementById("meta").textContent =
    `Última varredura: ${data}. ${dados.total.toLocaleString("pt-BR")} domínios verificados, ` +
    `${acessiveis.toLocaleString("pt-BR")} responderam.`;

  if (dados.amostra) {
    const aviso = document.getElementById("aviso-amostra");
    aviso.textContent =
      `Atenção: este é um resultado de teste com uma amostra de ${dados.amostra} domínios, ` +
      "não a varredura completa. Os números ainda não representam o país.";
    aviso.hidden = false;
  }
}

function preencherUFs(lista) {
  const ufs = [...new Set(lista.map((r) => r.uf).filter(Boolean))].sort();
  document.getElementById("filtro-uf").append(...ufs.map((uf) => el("option", { value: uf, text: uf })));
}

async function iniciar() {
  let dados;
  try {
    const resp = await fetch("dados/latest.json", { cache: "no-cache" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    dados = await resp.json();
  } catch (e) {
    document.getElementById("meta").textContent =
      "Ainda não há resultados publicados. A primeira varredura completa roda na próxima segunda-feira.";
    return;
  }

  // melhores primeiro; sem nota vai pro fim
  todos = dados.resultados.slice().sort((a, b) => (b.nota ?? -1) - (a.nota ?? -1) || a.municipio.localeCompare(b.municipio, "pt-BR"));

  cabecalho(dados);
  indicadores(todos);
  preencherUFs(todos);
  rankingEstados(todos);
  adocao(todos);
  aplicarFiltros();

  let espera;
  document.getElementById("busca").addEventListener("input", () => {
    clearTimeout(espera);
    espera = setTimeout(aplicarFiltros, 150);
  });
  document.getElementById("filtro-uf").addEventListener("change", aplicarFiltros);
  document.getElementById("filtro-conceito").addEventListener("change", aplicarFiltros);
  document.getElementById("mais").addEventListener("click", mostrarMais);
}

iniciar();
