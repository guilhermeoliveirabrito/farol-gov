// farol-gov: pagina de resultados
//
// Regra da casa: nada aqui usa innerHTML. O detalhe de cada check pode trazer texto
// vindo do servidor avaliado (header Location, mensagem de erro TLS), entao tudo
// entra como textContent. A CSP com Trusted Types faz o navegador barrar qualquer deslize.

const REPO = "https://github.com/guilhermeoliveirabrito/farol-gov";
const POR_PAGINA = 40;
const SVG = "http://www.w3.org/2000/svg";

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
const noRanking = (r) => r.acessivel && r.ranking !== false;
const passa = (lista, check) => lista.filter((r) => r.checks[check]?.status === "pass").length;

// ---------- mapa ----------

// projecao simples (equiretangular corrigida pela latitude media do pais).
// pro Brasil inteiro a distorcao e pequena e o formato fica reconhecivel.
const ESCALA_LON = Math.cos((14 * Math.PI) / 180);
const px = (lon) => (lon + 74.2) * ESCALA_LON;
const py = (lat) => 5.6 - lat;

function ponto(lon, lat, classe, animar) {
  const c = document.createElementNS(SVG, "circle");
  c.setAttribute("cx", px(lon).toFixed(2));
  c.setAttribute("cy", py(lat).toFixed(2));
  c.setAttribute("r", "0.21");
  c.setAttribute("class", `p ${classe}`);
  // o facho passa de leste (-34) a oeste (-74) em pouco mais de 1s
  if (animar) c.style.animationDelay = (((-34 - lon) / 40) * 1.2).toFixed(2) + "s";
  return c;
}

function desenharMapa(lista, semSite) {
  const comCoord = lista.filter((r) => typeof r.lat === "number" && typeof r.lon === "number");
  // dado antigo sem coordenada: melhor nao mostrar mapa nenhum do que um mapa vazio
  if (comCoord.length < 30) return;

  const svg = $("mapa");
  // vai ate -32 de longitude pra caber Fernando de Noronha
  svg.setAttribute("viewBox", `0 0 ${(42.4 * ESCALA_LON).toFixed(2)} 39.8`);
  const animar = !matchMedia("(prefers-reduced-motion: reduce)").matches;

  const gSem = document.createElementNS(SVG, "g");
  for (const [, , , lat, lon] of semSite) {
    if (typeof lat === "number" && typeof lon === "number") gSem.append(ponto(lon, lat, "sem", animar));
  }

  const gCom = document.createElementNS(SVG, "g");
  gCom.setAttribute("class", "com");
  comCoord.forEach((r, i) => {
    const classe = "c" + (noRanking(r) && conceitoSeguro(r.conceito) ? r.conceito : "X");
    const c = ponto(r.lon, r.lat, classe, animar);
    c.dataset.i = i;
    gCom.append(c);
  });

  svg.replaceChildren(gSem, gCom);
  const fig = $("mapa-fig");
  if (animar) fig.classList.add("animar");

  const chaves = CONCEITOS.map((c) => el("li", {}, el("i", { class: "c" + c }), c));
  if (semSite.length) chaves.push(el("li", {}, el("i", { class: "sem" }), `sem site (${num(semSite.length)})`));
  $("chaves").replaceChildren(...chaves);

  // dica ao passar o mouse; clique abre o municipio na lista
  const dica = $("dica");
  gCom.addEventListener("mousemove", (ev) => {
    const r = comCoord[ev.target.dataset.i];
    if (!r) return;
    const caixa = fig.getBoundingClientRect();
    const nota = r.nota != null ? `nota ${num(r.nota)}, conceito ${r.conceito}` : "sem nota";
    dica.replaceChildren(el("strong", { text: r.municipio }), ` ${r.uf}`, el("br"), el("span", { text: nota }));
    dica.style.left = ev.clientX - caixa.left + "px";
    dica.style.top = ev.clientY - caixa.top + "px";
    dica.hidden = false;
  });
  gCom.addEventListener("mouseleave", () => (dica.hidden = true));
  gCom.addEventListener("click", (ev) => {
    const r = comCoord[ev.target.dataset.i];
    if (r) location.hash = `m-${r.ibge}`;
  });

  fig.hidden = false;
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
  for (const r of ok) if (conceitoSeguro(r.conceito)) cont[r.conceito]++;

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
        el("td", {}, el("strong", { text: nome }), el("div", { class: "info" }, c.detalhe, ajuda && ", ", ajuda)),
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
    const st = ok.map((r) => r.checks[check]?.status);
    const atende = pct(st.filter((s) => s === "pass").length, ok.length);
    const parcial = pct(st.filter((s) => s === "warn").length, ok.length);
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

function cabecalho(dados) {
  const data = new Date(dados.gerado_em).toLocaleDateString("pt-BR", { day: "numeric", month: "long", year: "numeric" });
  const acessiveis = dados.resultados.filter((r) => r.acessivel).length;
  $("meta").textContent =
    `Última varredura em ${data}: ${num(dados.total)} sites verificados, ${num(acessiveis)} responderam.`;

  if (dados.amostra) {
    $("aviso-amostra").textContent =
      `Resultado de teste com uma amostra de ${num(dados.amostra)} sites, não a varredura completa. ` +
      "Os números ainda não representam o país.";
    $("aviso-amostra").hidden = false;
  }
}

function semDados() {
  $("meta").textContent = "Ainda não há resultados publicados. A primeira varredura completa sai na próxima segunda-feira.";
  for (const id of ["cidades", "estados", "itens"]) $(id).hidden = true;
  document.querySelector(".busca-hero").hidden = true;
}

async function buscarJson(url) {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

async function iniciar() {
  let dados;
  try {
    dados = await buscarJson("dados/latest.json");
    if (!Array.isArray(dados.resultados)) throw new Error("formato inesperado");
  } catch {
    semDados();
    return;
  }
  // a lista de municipios sem site e opcional, so serve pro mapa
  const semSite = await buscarJson("dados/sem_site.json")
    .then((d) => (Array.isArray(d) ? d : []))
    .catch(() => []);

  // melhores primeiro; sem nota vai pro fim
  todos = dados.resultados
    .filter((r) => r && typeof r === "object" && r.checks)
    .map((r) => ({ ...r, municipio: String(r.municipio ?? ""), _busca: semAcento(`${r.municipio} ${r.dominio}`) }))
    .sort((a, b) => (b.nota ?? -1) - (a.nota ?? -1) || a.municipio.localeCompare(b.municipio, "pt-BR"));
  const ok = todos.filter(noRanking);

  cabecalho(dados);
  desenharMapa(todos, semSite);
  achados(ok);
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
  $("busca-hero").addEventListener("keydown", (ev) => ev.key === "Enter" && buscarDoTopo());
  $("ir-busca").addEventListener("click", buscarDoTopo);
  $("filtro-uf").addEventListener("change", aplicarFiltros);
  $("filtro-conceito").addEventListener("change", aplicarFiltros);
  $("mais").addEventListener("click", mostrarMais);
  window.addEventListener("hashchange", abrirDoLink);
}

iniciar();
