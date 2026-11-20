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
  tls_antigo: ["Recusa TLS 1.0 e 1.1", "Não aceita conectar com versões de criptografia que já foram quebradas."],
  hsts: ["HSTS", "Avisa o navegador para nunca aceitar a versão sem criptografia."],
  headers: ["Headers de segurança", "Bloqueia truques comuns, como esconder o site dentro de outro."],
  conteudo_misto: ["Sem conteúdo misto", "A página protegida não puxa scripts e imagens por conexão aberta."],
  cookies: ["Cookies protegidos", "Os cookies só viajam com criptografia e scripts de terceiros não leem."],
  security_txt: ["security.txt", "Diz a quem encontrar uma falha para onde mandar o aviso."],
  dnssec: ["DNSSEC", "Assina o endereço do site para ninguém desviar você para outro lugar."],
  caa: ["CAA", "Diz quais empresas podem emitir certificado para o site."],
  spf: ["SPF", "Lista quais servidores podem mandar e-mail em nome da prefeitura."],
  dmarc: ["DMARC", "Manda os provedores recusarem e-mail falso com o nome da prefeitura."],
};

const STATUS = { pass: "cumpre", warn: "parcial", fail: "não cumpre", error: "não verificado", na: "novo, ainda não verificado" };
const CODIGOS = { p: "pass", w: "warn", f: "fail", e: "error", "-": "na" };
const CONCEITOS = ["A", "B", "C", "D", "F"];

const AVISOS = {
  nao_resolve: "O domínio cadastrado no Wikidata não existe no DNS.",
  dominio_alternativo: "O domínio cadastrado não funciona; avaliamos a versão com ou sem www.",
  fora_do_gov_br: "Domínio fora do .gov.br. Fica fora do ranking até alguém confirmar que é o site oficial.",
  dominio_compartilhado: "O mesmo domínio aparece para outro município. Fica fora do ranking até revisão.",
  verificacao_incompleta: "Parte dos itens não pôde ser verificada nesta semana (o servidor não respondeu a tempo). Sem nota até a próxima varredura.",
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
let ranqueados = []; // todo mundo com nota: base das medias e da adocao
let oficiais = []; // os 13 itens verificados: quem tem posicao, seta e medalha
let totalRanking = 0;
let listaOrdenada = []; // ranking primeiro, depois quem ficou sem posicao, depois sem nota
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

const fmtData = (iso, opcoes = { day: "2-digit", month: "2-digit" }) =>
  new Date(`${iso}T12:00:00`).toLocaleDateString("pt-BR", opcoes);

// seta de posicao em relacao a semana anterior: verde subiu, cinza igual, vermelha caiu
function seta(r, comTexto = false) {
  if (r.variacao == null) return comTexto ? el("span", { class: "seta nova", text: "sem comparação" }) : null;
  const v = r.variacao;
  const classe = v > 0 ? "sobe" : v < 0 ? "desce" : "igual";
  const simbolo = v > 0 ? "↑" : v < 0 ? "↓" : "=";
  const texto = v === 0 ? (comTexto ? "mesma posição" : "") : num(Math.abs(v));
  const titulo = v > 0 ? `subiu ${num(v)} posições` : v < 0 ? `caiu ${num(-v)} posições` : "mesma posição da semana anterior";
  return el("span", { class: `seta ${classe}`, title: titulo, "aria-label": titulo }, simbolo, texto && " ", texto, comTexto && v !== 0 ? (v > 0 ? " posições acima" : " posições abaixo") : null);
}

function selo(r) {
  return r.conceito
    ? el("span", { class: `conceito ${r.conceito}`, text: r.conceito })
    : el("span", { class: "conceito sem", text: "–", title: "Sem nota" });
}

// "semana de 16 a 22/11/2026"
function nomeSemana(s) {
  const ini = new Date(`${s.s}T12:00:00`);
  const fim = new Date(ini.getTime() + 6 * 86400000);
  const dia = (d) => String(d.getDate()).padStart(2, "0");
  const mes = (d) => String(d.getMonth() + 1).padStart(2, "0");
  const inicio = ini.getMonth() === fim.getMonth() ? dia(ini) : `${dia(ini)}/${mes(ini)}`;
  return `semana de ${inicio} a ${dia(fim)}/${mes(fim)}/${fim.getFullYear()}`;
}

function icone(tipo) {
  return el("i", { class: `med-icone ${tipo}`, "aria-hidden": "true" });
}

// "Ouro: semana de 16 a 22/11/2026 (em andamento)"
function semanasDaMedalha(r, tipo) {
  const desse = (r.medalhas || []).filter((m) => m.tipo === tipo);
  return `${NOME_MEDALHA[tipo]}: ` + desse.map((m) => nomeSemana(m.semana) + (m.semana.parcial ? " (em andamento)" : "")).join("; ");
}

// "ouro 2x" ao lado do nome; o title conta de quais semanas foi cada uma
function chipsMedalhas(r) {
  if (!r.medalhas?.length) return null;
  const caixa = el("span", { class: "medalhas" });
  for (const tipo of ["ouro", "prata", "bronze"]) {
    const n = r.medalhas.filter((m) => m.tipo === tipo).length;
    if (!n) continue;
    caixa.append(
      el(
        "span",
        { class: `med ${tipo}`, title: semanasDaMedalha(r, tipo), "aria-label": `${n} ${n > 1 ? "medalhas" : "medalha"} de ${tipo}` },
        icone(tipo),
        el("span", { text: `${n}x`, "aria-hidden": "true" }),
      ),
    );
  }
  return caixa;
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

// os dados ganham ?v=<versao> pra nao ficar preso no cache do GitHub Pages depois de uma varredura nova
const VERSAO_DADOS = document.querySelector('meta[name="versao-dados"]')?.content;

async function buscarJson(url) {
  const resp = await fetch(VERSAO_DADOS ? `${url}?v=${encodeURIComponent(VERSAO_DADOS)}` : url);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

// medalhas: premios.semanas tem a data de cada semana e premios[ranking].cidades[ibge] = [[indice da semana, "o"|"p"|"b"]]
const MEDALHAS = { o: "ouro", p: "prata", b: "bronze" };
const NOME_MEDALHA = { ouro: "Ouro", prata: "Prata", bronze: "Bronze" };
let semanasPremio = [];

// o premio fica em premios.oficial (formato antigo: direto em premios)
function premiosDe(premios) {
  if (premios?.oficial) return premios.oficial;
  return premios?.cidades ? premios : null;
}

function medalhasDe(premios, ibge) {
  const lista = premiosDe(premios)?.cidades?.[ibge];
  if (!Array.isArray(lista)) return [];
  return lista.filter(([i, t]) => MEDALHAS[t] && semanasPremio[i]).map(([i, t]) => ({ tipo: MEDALHAS[t], semana: semanasPremio[i] }));
}

function decodificar(resumo) {
  const idx = Object.fromEntries(resumo.campos.map((c, i) => [c, i]));
  semanasPremio = Array.isArray(resumo.premios?.semanas) ? resumo.premios.semanas : [];
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
      oficial: Boolean(l[idx.flags] & 4),
      posBr: typeof l[idx.pos] === "number" ? l[idx.pos] : null,
      ordem: typeof l[idx.ord] === "number" ? l[idx.ord] : null,
      variacao: typeof l[idx.var] === "number" ? l[idx.var] : null,
      st,
      medalhas: medalhasDe(resumo.premios, String(l[idx.ibge])),
      naoVerificados: Object.values(st).filter((v) => v === "error").length,
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
  // filtro por conceito (clicando na legenda): so esses pontos ficam acesos
  let filtroCor = null;
  let camadaFiltro = null;
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
    prepararFiltro();
  }

  function prepararFiltro() {
    camadaFiltro = null;
    if (!filtroCor || !fundo) return;
    camadaFiltro = document.createElement("canvas");
    camadaFiltro.width = canvas.width;
    camadaFiltro.height = canvas.height;
    const f = camadaFiltro.getContext("2d");
    f.setTransform(canvas.width / largCss, 0, 0, canvas.width / largCss, 0, 0);
    const original = ctx;
    ctx = f;
    pontosBase((p) => p.cor === filtroCor);
    ctx = original;
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
    ctx.globalAlpha = apontando ? 0.6 : camadaFiltro ? 0.16 : 1;
    ctx.drawImage(fundo, 0, 0, largCss, altCss);
    if (camadaFiltro) {
      ctx.globalAlpha = 1;
      ctx.drawImage(camadaFiltro, 0, 0, largCss, altCss);
    }
    ctx.restore();

    facho(apontando ? 0.09 : 0.34, apontando ? 1.4 : 1);

    // brilho so nos pontos por onde o facho acabou de passar
    if (!reduzirMovimento && !apontando) {
      for (const p of pontos) {
        if (p.cor === "sem" || (filtroCor && p.cor !== filtroCor)) continue;
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

  // null mostra todos
  function filtrar(cor) {
    filtroCor = cor;
    prepararFiltro();
    redesenharSeParado();
  }

  return { iniciar, apontar, ronda, filtrar };
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

// item "nao verificado" e falha da varredura, nao da prefeitura: explica em portugues
// e deixa a mensagem tecnica escondida pra quem quiser conferir
function explicarErro(detalhe) {
  const tecnico = String(detalhe || "");
  let texto = "Não deu para verificar nesta varredura. Esse item não conta na nota.";
  if (/^(LifetimeTimeout|NoNameservers)/.test(tecnico)) {
    texto = "O servidor de DNS da prefeitura não respondeu a tempo nesta varredura. Esse item não conta na nota.";
  } else if (/^timeout/.test(tecnico)) {
    texto = "O site não respondeu a tempo nesta varredura. Esse item não conta na nota.";
  } else if (/nao resolve/.test(tecnico)) {
    texto = "O domínio não foi encontrado no DNS.";
  }
  const partes = [texto];
  if (tecnico) {
    partes.push(el("details", { class: "tecnico" }, el("summary", { text: "detalhe técnico" }), el("code", { text: tecnico.slice(0, 200) })));
  }
  return partes;
}

function linkCorrigir(check) {
  return el("a", { href: `${REPO}/blob/main/docs/como-corrigir.md#${check}`, rel: "noopener", text: "como corrigir" });
}

// parte das cidades de cada estado que cumpre cada item (pra comparar na ficha)
let porEstado = {};
let mediaBrasil = null;

const mediaNotas = (lista) => (lista.length ? lista.reduce((a, r) => a + r.nota, 0) / lista.length : null);

function calcularPorEstado(ok) {
  const grupos = {};
  for (const r of ok) (grupos[r.uf] ??= []).push(r);
  porEstado = {};
  mediaBrasil = mediaNotas(ok);
  for (const [uf, lista] of Object.entries(grupos)) {
    porEstado[uf] = { n: lista.length, media: mediaNotas(lista) };
    for (const check of Object.keys(ITENS)) {
      const avaliados = lista.filter((r) => r.st[check] !== "na").length;
      porEstado[uf][check] = avaliados ? pct(conta(lista, check), avaliados) : null;
    }
  }
}

function listaSinais(r) {
  const estado = porEstado[r.uf];
  return el(
    "ul",
    { class: "sinais" },
    ...Object.entries(ITENS).map(([check, [nome]], i) => {
      const st = statusSeguro(r.st[check]);
      const luz = el("span", { class: `luz ${st}`, "aria-hidden": "true" });
      luz.style.setProperty("--n", i);
      const comparacao = estado && estado.n > 1 && estado[check] != null && st !== "na" && st !== "error"
        ? el("div", { class: "compara", text: `${fmtPct(estado[check])} das cidades de ${r.uf} cumprem` })
        : null;
      return el(
        "li",
        {},
        luz,
        el(
          "div",
          {},
          el("strong", {}, nome, el("span", { class: `estado ${st}`, text: STATUS[st] })),
          st === "na"
            ? el("div", { class: "info", text: "Item novo: entra na conta a partir da próxima varredura." })
            : el("div", { class: "info carregando", "data-check": check }, "carregando detalhe…"),
          comparacao,
        ),
      );
    }),
  );
}

// grafico pequeno da nota da cidade semana a semana, com a data de cada ponto
function graficoCidade(semanas) {
  const pontos = semanas.filter(([, nota]) => typeof nota === "number");
  if (pontos.length < 2) return null;
  const L = 440, A = 150, m = { e: 30, d: 14, t: 18, b: 28 };
  const xs = (i) => m.e + (i * (L - m.e - m.d)) / (pontos.length - 1);
  const ys = (n) => m.t + ((100 - n) * (A - m.t - m.b)) / 100;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", `0 0 ${L} ${A}`);
  svg.setAttribute("class", "grafico-cidade");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "Nota da cidade por semana: " + pontos.map(([d, n]) => `${fmtData(d)} ${fmtNota(n)}`).join(", "));
  const novo = (tag, attrs, texto) => {
    const e = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
    if (texto != null) e.textContent = texto;
    svg.append(e);
    return e;
  };
  for (const g of [0, 50, 100]) {
    novo("line", { x1: m.e, x2: L - m.d, y1: ys(g), y2: ys(g), class: "guia" });
    novo("text", { x: m.e - 6, y: ys(g) + 4, class: "eixo", "text-anchor": "end" }, String(g));
  }
  novo("polyline", { points: pontos.map(([, n], i) => `${xs(i)},${ys(n)}`).join(" "), class: "linha-nota" });
  pontos.forEach(([data, nota], i) => {
    novo("circle", { cx: xs(i), cy: ys(nota), r: 4, class: "ponto-nota" });
    novo("text", { x: xs(i), y: A - 8, class: "eixo", "text-anchor": "middle" }, fmtData(data));
  });
  return svg;
}

function blocoHistorico(semanas) {
  if (!semanas || !semanas.length) return null;
  const linhas = [...semanas].reverse().map(([data, nota, pos], i, todas) => {
    const anterior = todas[i + 1];
    let mudanca = null;
    if (anterior && pos != null && anterior[2] != null) mudanca = seta({ variacao: anterior[2] - pos });
    return el(
      "tr",
      {},
      el("td", { text: fmtData(data, { day: "2-digit", month: "2-digit", year: "numeric" }) }),
      el("td", { class: "num", text: typeof nota === "number" ? fmtNota(nota) : "sem nota" }),
      el("td", { class: "num" }, pos != null ? `${num(pos)}º` : "fora", mudanca ? " " : null, mudanca),
    );
  });
  return el(
    "section",
    { class: "historico-cidade" },
    el("h3", { text: "Histórico" }),
    graficoCidade(semanas),
    el(
      "table",
      {},
      el("thead", {}, el("tr", {}, el("th", { text: "Varredura" }), el("th", { class: "num", text: "Nota" }), el("th", { class: "num", text: "Ranking oficial" }))),
      el("tbody", {}, ...linhas),
    ),
  );
}

const SITE = "https://guilhermeoliveirabrito.github.io/farol-gov/";

async function copiarTexto(botao, texto, rotuloOk) {
  const original = botao.textContent;
  try {
    await navigator.clipboard.writeText(texto);
    botao.textContent = rotuloOk;
  } catch {
    botao.textContent = "Não deu para copiar";
  }
  setTimeout(() => (botao.textContent = original), 2200);
}

// selo que a prefeitura (ou quem quiser) pode colocar no proprio site
function blocoSelo(r) {
  const link = `${SITE}#m-${r.ibge}`;
  const imagem = `${SITE}selos/${r.ibge}.svg`;
  const alt = r.ranking && r.conceito ? `Segurança do site: conceito ${r.conceito} no farol-gov` : "Segurança do site no farol-gov";
  const codigo = `<a href="${link}"><img src="${imagem}" alt="${alt}"></a>`;
  const copiar = el("button", { type: "button" }, "Copiar código");
  copiar.addEventListener("click", () => copiarTexto(copiar, codigo, "Código copiado"));
  return el(
    "section",
    { class: "selo-cidade" },
    el("h3", { text: "Selo para o site" }),
    el("p", { text: "Cole este código no site da prefeitura. O selo se atualiza sozinho a cada varredura." }),
    el("img", { src: `selos/${encodeURIComponent(r.ibge)}.svg`, alt, height: "20" }),
    el("code", { text: codigo }),
    el("div", { class: "acoes" }, copiar),
  );
}

// regua de 0 a 100 com a cidade, a media do estado e a do Brasil
function regua(r) {
  const mediaUf = porEstado[r.uf]?.media;
  if (r.nota == null || !r.ranking || mediaUf == null || mediaBrasil == null) return null;
  const marca = (classe, valor, rotulo) => {
    const m = el("span", { class: `marca ${classe}` }, rotulo && el("small", { text: rotulo }));
    m.style.setProperty("--x", `${Math.max(0, Math.min(100, valor))}%`);
    return m;
  };
  const diferenca = r.nota - mediaUf;
  const comparacao = Math.abs(diferenca) < 1
    ? `Na média de ${r.uf}.`
    : `${fmtNota(Math.abs(diferenca))} pontos ${diferenca > 0 ? "acima" : "abaixo"} da média de ${r.uf}.`;
  return el(
    "figure",
    { class: "regua" },
    el(
      "div",
      {
        class: "regua-faixa",
        role: "img",
        "aria-label": `Nota ${fmtNota(r.nota)}. Média de ${r.uf}: ${fmtNota(mediaUf)}. Média do Brasil: ${fmtNota(mediaBrasil)}.`,
      },
      marca("uf", mediaUf, `${r.uf} ${fmtNota(mediaUf)}`),
      marca("br", mediaBrasil, `Brasil ${fmtNota(mediaBrasil)}`),
      marca(`cidade c${r.conceito}`, r.nota),
    ),
    el("figcaption", { text: comparacao }),
  );
}

function blocoMedalhas(r) {
  if (!r.medalhas?.length) return null;
  const ordem = { ouro: 0, prata: 1, bronze: 2 };
  const lista = [...r.medalhas].sort((a, b) => b.semana.s.localeCompare(a.semana.s) || ordem[a.tipo] - ordem[b.tipo]);
  return el(
    "section",
    { class: "medalhas-cidade" },
    el("h3", { text: "Medalhas" }),
    el(
      "ul",
      {},
      ...lista.map((m) =>
        el("li", {}, icone(m.tipo), el("b", { text: NOME_MEDALHA[m.tipo] }), ` na ${nomeSemana(m.semana)}`, m.semana.parcial ? el("span", { class: "parcial", text: "em andamento" }) : null),
      ),
    ),
  );
}

// mesmas chaves e ordem de farol/nota.py EXCELENCIA
const EXCELENCIA = {
  dmarc_reject: "DMARC com p=reject: o e-mail falso é recusado, não vai para o spam",
  dmarc_relatorios: "DMARC mandando relatórios (rua=): a prefeitura fica sabendo de quem tenta se passar por ela",
  spf_hardfail: "SPF terminando em -all: recusa quem não está na lista",
  tls13: "TLS 1.3",
  hsts_subdominios: "HSTS cobrindo os subdomínios",
  hsts_preload: "HSTS pronto para a lista de preload dos navegadores",
  hsts_2_anos: "HSTS valendo por 2 anos ou mais",
  csp: "Content-Security-Policy na página",
  referrer_policy: "Referrer-Policy: não vaza o endereço da página para outros sites",
  permissions_policy: "Permissions-Policy: desliga câmera, microfone e afins que o site não usa",
  caa_proprio: "CAA no próprio domínio",
};

// o que desempata o podio quando a nota empata; nao muda a nota
function blocoExcelencia(r, feitos) {
  if (r.nota == null || !Array.isArray(feitos)) return null;
  const tem = new Set(feitos);
  const chaves = Object.keys(EXCELENCIA);
  return el(
    "details",
    { class: "excelencia" },
    el("summary", {}, el("b", { text: "Pontos de excelência" }), ` ${tem.size} de ${chaves.length}`),
    el("p", { text: "Não mudam a nota. Servem para desempatar o pódio da semana quando duas cidades ficam com a mesma nota." }),
    el(
      "ul",
      {},
      ...chaves.map((c) => el("li", { class: tem.has(c) ? "feito" : "falta" }, el("span", { class: "marca", "aria-label": tem.has(c) ? "tem" : "não tem", text: tem.has(c) ? "✓" : "–" }), EXCELENCIA[c])),
    ),
  );
}

function abrirFicha(r) {
  const dialogo = $("ficha");
  const corpo = $("ficha-corpo");

  let posicoes = null;
  if (r.posBr != null) {
    posicoes = el(
      "div",
      { class: "posicoes" },
      el("span", {}, el("b", { text: `${num(r.posBr)}º` }), ` de ${num(totalRanking)} no Brasil`),
      el("span", {}, el("b", { text: `${r.pos}º` }), ` de ${r.totalUf} em ${r.uf}`),
      seta(r, true),
    );
  } else if (r.nota != null && r.naoVerificados) {
    const n = r.naoVerificados;
    posicoes = el(
      "div",
      { class: "posicoes fora-oficial" },
      el(
        "p",
        { class: "aviso-oficial" },
        `Fora do ranking nesta semana: ${n} ${n === 1 ? "item não pôde ser verificado" : "itens não puderam ser verificados"}. ` +
          `A nota foi calculada sem ${n === 1 ? "ele" : "eles"} e pode estar acima da real; a cidade volta a ter posição quando a varredura conseguir verificar tudo.`,
      ),
    );
  }

  const placar = el(
    "div",
    { class: "placar" },
    selo(r),
    r.nota != null
      ? el("div", {}, el("strong", { text: fmtNota(r.nota) }), el("span", { text: r.ranking ? "de 100 pontos" : "fora do ranking" }))
      : el("div", {}, el("strong", { text: "Sem nota" }), el("span", { text: r.acessivel ? "verificação incompleta ou domínio em revisão" : "o site não respondeu à verificação" })),
  );

  const url = `${location.origin}${location.pathname}#m-${r.ibge}`;
  const copiar = el("button", { type: "button" }, "Copiar link");
  copiar.addEventListener("click", () => copiarTexto(copiar, url, "Link copiado"));

  // no celular abre o menu de compartilhar do sistema (WhatsApp etc)
  let compartilhar = null;
  if (navigator.share) {
    compartilhar = el("button", { type: "button", class: "principal" }, "Compartilhar");
    const frase = r.ranking && r.conceito
      ? `${r.municipio} (${r.uf}) tem conceito ${r.conceito} na segurança do site e do e-mail da prefeitura.`
      : `Veja a segurança do site e do e-mail da prefeitura de ${r.municipio} (${r.uf}).`;
    compartilhar.addEventListener("click", () => navigator.share({ title: `${r.municipio} no farol-gov`, text: frase, url }).catch(() => {}));
  }
  const titulo = encodeURIComponent(`Contestar resultado: ${r.municipio} (${r.dominio})`);
  const acoes = el("div", { class: "acoes" }, compartilhar, copiar, el("a", { href: `${REPO}/issues/new?title=${titulo}`, rel: "noopener", text: "Contestar resultado" }));

  const avisos = el("div");
  const historicoCaixa = el("div");
  const excelenciaCaixa = el("div");
  corpo.replaceChildren(...[
    el("h2", { id: "ficha-nome", text: r.municipio }),
    el("p", { class: "onde", text: `${r.uf}, ${r.dominio}` }),
    placar,
    regua(r),
    posicoes,
    blocoMedalhas(r),
    avisos,
    listaSinais(r),
    excelenciaCaixa,
    historicoCaixa,
    acoes,
    blocoSelo(r),
  ].filter(Boolean)); // replaceChildren escreveria "null" no lugar do que nao existe

  carregarUf(r.uf)
    .then((dados) => {
      const extra = dados[r.ibge];
      if (!extra || !corpo.contains(avisos)) return;
      // so troca os textos; as luzes ja acenderam e nao precisam animar de novo
      corpo.querySelectorAll(".sinais .info[data-check]").forEach((info) => {
        const check = info.dataset.check;
        const detalhe = String(extra.d[Object.keys(ITENS).indexOf(check)] ?? "");
        const st = statusSeguro(r.st[check]);
        info.classList.remove("carregando");
        if (st === "error") {
          info.replaceChildren(...explicarErro(detalhe));
          return;
        }
        info.replaceChildren(detalhe);
        if (st !== "pass") info.append(detalhe ? ", " : "", linkCorrigir(check));
      });
      avisos.replaceChildren(...(extra.a || []).filter((a) => AVISOS[a]).map((a) => el("p", { class: "avisos", text: AVISOS[a] })));
      const hist = blocoHistorico(extra.h);
      if (hist) historicoCaixa.replaceChildren(hist);
      const ex = blocoExcelencia(r, extra.x);
      if (ex) excelenciaCaixa.replaceChildren(ex);
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
            el("span", { class: "nota" }, r.nota != null ? fmtNota(r.nota) : "sem nota", seta(r) && " ", seta(r)),
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
    .map(([check, [nome, texto]]) => {
      const avaliados = ok.filter((r) => r.st[check] !== "na").length;
      return { check, nome, texto, novo: !avaliados, cumpre: pct(conta(ok, check), avaliados), parcial: pct(conta(ok, check, "warn"), avaliados) };
    })
    // o que mais falta primeiro; itens novos, ainda sem dado, vao pro fim
    .sort((a, b) => a.novo - b.novo || a.cumpre - b.cumpre);

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
        l.novo ? el("span", { class: "valor novo", text: "novo" }) : el("span", { class: "valor", text: fmtPct(l.cumpre) }),
      );
    }),
  );
  quandoAparecer(lista, () => barras.forEach(([i, v]) => (i.style.width = v + "%")));
}

function estados(ok, semanas = []) {
  const porUf = {};
  for (const r of ok) (porUf[r.uf] ??= []).push(r.nota);
  const linhas = Object.entries(porUf)
    .map(([uf, notas]) => ({ uf, media: notas.reduce((a, b) => a + b, 0) / notas.length, n: notas.length }))
    .sort((a, b) => b.media - a.media);

  // posicao de cada estado na semana anterior, pra mostrar quem subiu e quem caiu
  const anterior = semanas.length > 1 ? semanas[semanas.length - 2].ufs : null;
  if (anterior) {
    const ordemAntes = Object.entries(anterior).sort((a, b) => b[1] - a[1]).map(([uf]) => uf);
    linhas.forEach((l, i) => {
      const antes = ordemAntes.indexOf(l.uf);
      l.variacao = antes >= 0 ? antes - i : null;
    });
  }

  const caixa = $("ladrilhos");
  const ranking = $("ranking-uf");
  const noRanking = {};
  const barras = [];

  ranking.replaceChildren(
    ...linhas.map((l) => {
      const i = el("i", { class: "ok" });
      barras.push([i, l.media]);
      const li = el(
        "li",
        {},
        el("strong", { text: l.uf }),
        el("div", { class: "trilho", "aria-hidden": "true" }, i),
        el("span", { class: "media", text: fmtNota(l.media) }),
        el("span", { class: "mov" }, seta({ variacao: l.variacao ?? null })),
      );
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
  const luzes = el(
    "span",
    { class: "luzes", "aria-hidden": "true" },
    ...Object.keys(ITENS).map((c) => {
      const st = statusSeguro(r.st[c]);
      return el("i", { class: st, title: `${ITENS[c][0]}: ${STATUS[st]}` });
    }),
  );
  const botao = el(
    "button",
    { type: "button", class: "linha" },
    el(
      "span",
      { class: "nome" },
      r.posBr != null ? el("span", { class: "pos-lista", text: `${num(r.posBr)}º` }) : null,
      r.municipio || r.dominio,
      chipsMedalhas(r),
      r.nota != null && !r.oficial && r.naoVerificados
        ? el("span", { class: "incompleta", title: "A nota foi calculada sem os itens que não puderam ser verificados", text: `${r.naoVerificados} sem verificar` })
        : null,
      el("span", { class: "dominio", text: r.dominio }),
    ),
    el("span", { class: "uf", text: r.uf }),
    ...(r.nota != null
      ? [luzes, el("span", { class: "nota", text: fmtNota(r.nota) }), el("span", { class: "mov" }, seta(r))]
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
  filtrados = listaOrdenada.filter((r) => {
    if (uf && r.uf !== uf) return false;
    if (conceito === "-" && r.nota != null) return false;
    if (conceito && conceito !== "-" && r.conceito !== conceito) return false;
    if (termo && !r._busca.includes(termo)) return false;
    return true;
  });
  const ordem = $("ordem").value;
  // todos ja vem da maior nota pra menor; os outros criterios reordenam a copia filtrada
  const semValor = (v, fallback) => (v == null ? fallback : v);
  if (ordem === "menor") filtrados.sort((a, b) => semValor(a.nota, 999) - semValor(b.nota, 999));
  else if (ordem === "subiu") filtrados.sort((a, b) => semValor(b.variacao, -1e9) - semValor(a.variacao, -1e9));
  else if (ordem === "caiu") filtrados.sort((a, b) => semValor(a.variacao, 1e9) - semValor(b.variacao, 1e9));
  else if (ordem === "nome") filtrados.sort((a, b) => ordemAlfabetica(a.municipio, b.municipio));
  mostrando = 0;
  $("lista").replaceChildren();
  $("lista").removeAttribute("aria-busy");
  mostrarMais();
}

// explica as bolinhas da lista uma vez so, em cima dela
function legendaLuzes() {
  const caixa = $("legenda-luzes");
  const item = (st, texto) => el("span", {}, el("span", { class: "luzes", "aria-hidden": "true" }, el("i", { class: st })), texto);
  caixa.replaceChildren(
    el("span", { text: `Cada bolinha é um dos ${Object.keys(ITENS).length} itens, na ordem de cima:` }),
    item("pass", "cumpre"),
    item("warn", "parcial"),
    item("fail", "não cumpre"),
    item("error", "não verificado"),
    item("na", "item novo"),
  );
  caixa.hidden = false;
}

function mostrarMais() {
  const proximos = filtrados.slice(mostrando, mostrando + POR_PAGINA);
  $("lista").append(...proximos.map(linhaCidade));
  mostrando += proximos.length;
  const criterio = { nota: "da maior nota para a menor", menor: "da menor nota para a maior", subiu: "das que mais subiram", caiu: "das que mais caíram", nome: "em ordem alfabética" }[$("ordem").value];
  $("contagem").textContent = filtrados.length
    ? `${num(filtrados.length)} cidades, ${criterio}. Toque em uma para ver o detalhe.`
    : "Nenhuma cidade com esse filtro. Confira a grafia ou procure pelo domínio do site.";
  $("mais").hidden = mostrando >= filtrados.length;
}

// ---------- baixar csv ----------

// celula que comeca com = + - @ vira formula no Excel/Sheets (CSV injection); o apostrofo neutraliza
function celulaCsv(valor) {
  let v = valor == null ? "" : String(valor);
  if (/^[=+\-@\t\r]/.test(v)) v = "'" + v;
  return /[",;\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v;
}

function baixarCsv() {
  const checks = Object.keys(ITENS);
  const cabecalho = ["ibge", "municipio", "uf", "dominio", "nota", "conceito", "posicao_brasil", "variacao_posicao", ...checks];
  const linhas = filtrados.map((r) => [r.ibge, r.municipio, r.uf, r.dominio, r.nota, r.conceito, r.posBr, r.variacao, ...checks.map((c) => r.st[c])]);
  const texto = [cabecalho, ...linhas].map((l) => l.map(celulaCsv).join(",")).join("\r\n");
  // BOM pro Excel abrir os acentos certo
  const blob = new Blob(["\ufeff" + texto], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = el("a", { href: url, download: `farol-gov-${new Date().toISOString().slice(0, 10)}.csv` });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// ---------- evolucao semana a semana ----------

const SVG_NS = "http://www.w3.org/2000/svg";

function desenharEvolucao(semanas, metrica) {
  const caixa = $("grafico-evolucao");
  const valor = (s) => (metrica === "media" ? s.media : s.adocao[metrica]);
  const pontos = semanas.map((s) => ({ s, v: valor(s) })).filter((p) => typeof p.v === "number");
  if (!pontos.length) {
    caixa.replaceChildren(el("p", { class: "vazio", text: "Esse item ainda não era verificado nessas semanas." }));
    return;
  }

  const L = 900, A = 300, m = { e: 44, d: 24, t: 28, b: 44 };
  const passo = pontos.length > 1 ? (L - m.e - m.d) / (pontos.length - 1) : 0;
  const xs = (i) => (pontos.length > 1 ? m.e + i * passo : L / 2);
  const ys = (v) => m.t + ((100 - v) * (A - m.t - m.b)) / 100;

  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", `0 0 ${L} ${A}`);
  svg.setAttribute("role", "img");
  const nome = metrica === "media" ? "Nota média" : `${ITENS[metrica][0]} (% das prefeituras)`;
  svg.setAttribute("aria-label", `${nome} por semana: ` + pontos.map((p) => `${fmtData(p.s.data, { day: "2-digit", month: "2-digit", year: "numeric" })}: ${fmtNota(p.v)}`).join("; "));
  const novo = (tag, attrs, texto, pai = svg) => {
    const e = document.createElementNS(SVG_NS, tag);
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
    if (texto != null) e.textContent = texto;
    pai.append(e);
    return e;
  };

  for (const g of [0, 25, 50, 75, 100]) {
    novo("line", { x1: m.e, x2: L - m.d, y1: ys(g), y2: ys(g), class: "guia" });
    novo("text", { x: m.e - 10, y: ys(g) + 4, class: "eixo", "text-anchor": "end" }, metrica === "media" ? String(g) : `${g}%`);
  }

  // marca as semanas em que a metodologia mudou (itens novos entraram na conta)
  pontos.forEach((p, i) => {
    if (i > 0 && p.s.metodologia !== pontos[i - 1].s.metodologia) {
      const x = (xs(i) + xs(i - 1)) / 2;
      novo("line", { x1: x, x2: x, y1: m.t - 10, y2: A - m.b, class: "marco" });
      novo("text", { x: x + 6, y: m.t - 12, class: "eixo marco-texto" }, "novos itens na nota");
    }
  });

  if (pontos.length > 1) {
    const linha = novo("polyline", { points: pontos.map((p, i) => `${xs(i)},${ys(p.v)}`).join(" "), class: "linha-evolucao" });
    if (!reduzirMovimento) {
      // a linha se desenha da esquerda pra direita
      linha.style.strokeDasharray = "2000";
      linha.style.strokeDashoffset = "2000";
      requestAnimationFrame(() => requestAnimationFrame(() => (linha.style.strokeDashoffset = "0")));
    }
  }

  const poucos = pontos.length <= 10;
  pontos.forEach((p, i) => {
    const g = novo("g", { class: "marcador", tabindex: "0" });
    novo("title", {}, `${fmtData(p.s.data, { day: "2-digit", month: "long", year: "numeric" })}: ${metrica === "media" ? fmtNota(p.v) : fmtPct(p.v)}`, g);
    novo("circle", { cx: xs(i), cy: ys(p.v), r: 6 }, null, g);
    if (poucos || i === pontos.length - 1) novo("text", { x: xs(i), y: ys(p.v) - 14, class: "valor-ponto", "text-anchor": "middle" }, metrica === "media" ? fmtNota(p.v) : fmtPct(p.v), g);
    // datas no eixo: todas quando sao poucas, senao uma sim outra nao
    if (poucos || i % 2 === 0 || i === pontos.length - 1) {
      novo("text", { x: xs(i), y: A - m.b + 22, class: "eixo", "text-anchor": "middle" }, fmtData(p.s.data, { day: "2-digit", month: "2-digit", year: "2-digit" }));
    }
  });

  caixa.replaceChildren(svg);
}

function evolucao(semanas) {
  if (!Array.isArray(semanas) || !semanas.length) return;
  const seletor = $("metrica");
  const opcoes = [["media", "Nota média"], ...Object.entries(ITENS).map(([c, [nome]]) => [c, nome])];
  seletor.replaceChildren(...opcoes.map(([v, t]) => el("option", { value: v, text: t })));
  seletor.addEventListener("change", () => desenharEvolucao(semanas, seletor.value));

  const ultima = semanas[semanas.length - 1];
  const primeira = semanas[0];
  $("evolucao-texto").textContent = semanas.length > 1
    ? `${semanas.length} varreduras, de ${fmtData(primeira.data, { day: "numeric", month: "long" })} a ${fmtData(ultima.data, { day: "numeric", month: "long", year: "numeric" })}. Passe o mouse num ponto para ver o valor.`
    : `Primeira varredura em ${fmtData(ultima.data, { day: "numeric", month: "long", year: "numeric" })}. A linha cresce a cada semana.`;
  quandoAparecer($("grafico-evolucao"), () => desenharEvolucao(semanas, "media"));
  $("evolucao").hidden = false;
}

// ---------- quem mais subiu e quem mais caiu ----------

function movimento(resumo) {
  const comVariacao = ranqueados.filter((r) => r.variacao != null && r.variacao !== 0);
  if (!comVariacao.length) return;
  const subiram = [...comVariacao].filter((r) => r.variacao > 0).sort((a, b) => b.variacao - a.variacao || b.nota - a.nota).slice(0, 8);
  const cairam = [...comVariacao].filter((r) => r.variacao < 0).sort((a, b) => a.variacao - b.variacao || a.nota - b.nota).slice(0, 8);

  const item = (r) => {
    const antes = r.posBr + r.variacao;
    const botao = el(
      "button",
      { type: "button", class: "mov-linha" },
      el("span", { class: "mov-nome" }, r.municipio, el("span", { class: "uf", text: r.uf })),
      el("span", { class: "mov-pos", text: `${num(antes)}º → ${num(r.posBr)}º` }),
      seta(r),
    );
    botao.addEventListener("click", () => abrirFicha(r));
    return el("li", {}, botao);
  };
  $("subiram").replaceChildren(...subiram.map(item));
  $("cairam").replaceChildren(...cairam.map(item));

  const subiuTotal = comVariacao.filter((r) => r.variacao > 0).length;
  const caiuTotal = comVariacao.length - subiuTotal;
  $("movimento-texto").textContent =
    `Comparação com a varredura de ${fmtData(resumo.anterior, { day: "numeric", month: "long" })}: ` +
    `${num(subiuTotal)} cidades subiram e ${num(caiuTotal)} caíram no ranking.` +
    (resumo.itens_novos > 0
      ? ` Boa parte do movimento vem ${resumo.itens_novos === 1 ? "do item que passou" : `dos ${resumo.itens_novos} itens que passaram`} a ser verificado${resumo.itens_novos === 1 ? "" : "s"} depois daquela varredura, não de mudança nos sites.`
      : "") +
    " Toque em uma para ver o detalhe.";
  $("movimento").hidden = false;
}

// ---------- medalhas: podio da semana e hall da fama ----------

function podio(semana, porIbge, atual) {
  const titulo = (tipo) => `${NOME_MEDALHA[tipo]} na ${nomeSemana(semana)}`;
  const degrau = (tipo, altura) => {
    const cidades = semana[tipo].map((ibge) => porIbge.get(ibge)).filter(Boolean);
    const nomes = cidades.length
      ? cidades.map((r) => {
          const copias = semana.g?.[tipo];
          const b = el(
            "button",
            { type: "button", class: "podio-cidade", title: titulo(tipo) },
            el("b", { text: r.municipio }),
            el("span", { text: atual ? `${r.uf}, nota ${fmtNota(r.nota)}` : r.uf }),
            // a medalha vale pra configuracao; as copias no mesmo servidor nao levam outra
            copias > 0 ? el("small", { class: "podio-copias", text: `e mais ${copias} no mesmo servidor, com a mesma configuração` }) : null,
          );
          b.addEventListener("click", () => abrirFicha(r));
          return b;
        })
      : [el("span", { class: "podio-vazio", text: "ninguém" })];
    return el("li", { class: `degrau ${tipo} ${altura}` }, el("div", { class: "podio-nomes" }, ...nomes), el("div", { class: "bloco", title: titulo(tipo) }, icone(tipo), el("span", { text: NOME_MEDALHA[tipo] })));
  };
  // prata na esquerda, ouro no meio, bronze na direita, como num podio de verdade
  return el("ol", { class: "podio", "aria-label": "Pódio" }, degrau("prata", "medio"), degrau("ouro", "alto"), degrau("bronze", "baixo"));
}

function medalhasSecao(resumo) {
  const dados = premiosDe(resumo.premios);
  if (!dados || !semanasPremio.length) return;
  const porIbge = new Map(todos.map((r) => [r.ibge, r]));

  // monta o podio de cada semana a partir das medalhas de cada cidade
  const semanas = semanasPremio.map((s, i) => ({ ...s, ouro: [], prata: [], bronze: [], x: (dados.x || [])[i] || s.x || {}, g: (dados.g || [])[i] || {} }));
  for (const [ibge, lista] of Object.entries(dados.cidades || {})) {
    for (const [i, t] of lista) if (semanas[i] && MEDALHAS[t]) semanas[i][MEDALHAS[t]].push(ibge);
  }

  const mostrar = (i) => {
    const s = semanas[i];
    $("podio-semana").textContent = s.parcial
      ? `Resultado parcial da ${nomeSemana(s)}: se houver outra varredura até domingo, o pódio pode mudar.`
      : `Resultado da ${nomeSemana(s)}, pela varredura de ${fmtData(s.d, { day: "numeric", month: "long" })}.`;
    $("podio").replaceChildren(podio(s, porIbge, i === semanas.length - 1));
    const desempates = Object.entries(s.x || {}).filter(([t, c]) => NOME_MEDALHA[t] && typeof c === "string");
    $("podio-desempate").textContent = desempates.length
      ? "Nota empatada, decidido no desempate: " + desempates.map(([t, c]) => `${NOME_MEDALHA[t].toLowerCase()} por ${c}`).join("; ") + "."
      : "";
  };
  const escolha = $("semana-podio");
  escolha.replaceChildren(...semanas.map((s, i) => el("option", { value: i, text: nomeSemana(s).replace("semana de ", "") + (s.parcial ? " (em andamento)" : "") })).reverse());
  escolha.value = String(semanas.length - 1);
  escolha.addEventListener("change", () => mostrar(Number(escolha.value)));
  mostrar(semanas.length - 1);

  const hall = (dados.hall || []).map(([ibge, o, p, b, pontos, pos]) => ({ r: porIbge.get(String(ibge)), o, p, b, pontos, pos })).filter((h) => h.r);
  const contagem = (r, tipo, n) => (n ? el("span", { class: `med ${tipo}`, title: semanasDaMedalha(r, tipo) }, icone(tipo), el("span", { text: `${n}x` })) : el("span", { "aria-hidden": "true" }));
  $("hall").replaceChildren(
    ...hall.map((h) => {
      const b = el(
        "button",
        { type: "button", class: "hall-linha" },
        el("span", { class: "hall-pos", text: `${h.pos}º` }),
        el("span", { class: "hall-nome" }, h.r.municipio, el("span", { class: "uf", text: h.r.uf })),
        el("span", { class: "hall-medalhas" }, contagem(h.r, "ouro", h.o), contagem(h.r, "prata", h.p), contagem(h.r, "bronze", h.b)),
        el("span", { class: "hall-pontos", text: `${num(h.pontos)} pts` }),
      );
      b.addEventListener("click", () => abrirFicha(h.r));
      return el("li", {}, b);
    }),
  );
  $("medalhas").hidden = false;
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
  const contagem = Object.fromEntries(CONCEITOS.map((c) => [c, ranqueados.filter((r) => r.conceito === c).length]));
  // cada conceito da legenda e um botao: clicar acende so aquelas prefeituras no mapa
  const botoes = CONCEITOS.map((c) => {
    const b = el("button", { type: "button", "aria-pressed": "false", title: `Mostrar só as prefeituras com conceito ${c} (${num(contagem[c])})` }, bolinha(`var(--c${c})`), c);
    b.addEventListener("click", () => {
      const ativo = b.getAttribute("aria-pressed") === "true";
      botoes.forEach((x) => x.setAttribute("aria-pressed", "false"));
      b.setAttribute("aria-pressed", String(!ativo));
      Mapa.filtrar(ativo ? null : c);
    });
    return b;
  });
  const chaves = botoes.map((b) => el("li", {}, b));
  if (semSite) chaves.push(el("li", { class: "sem-site" }, bolinha("#203a55"), `sem site cadastrado (${num(semSite)})`));
  $("chaves").replaceChildren(...chaves);
  $("legenda-mapa").hidden = false;
}

function semDados() {
  $("meta").textContent = "Ainda não há resultados publicados. A primeira varredura completa sai na próxima segunda-feira.";
  for (const id of ["itens", "evolucao", "movimento", "estados", "cidades", "busca-caixa"]) $(id).hidden = true;
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

  // nota igual: segue a ordem de desempate do podio (vem pronta do build), depois o nome
  todos = decodificar(resumo).sort(
    (a, b) => (b.nota ?? -1) - (a.nota ?? -1) || (a.ordem ?? 1e9) - (b.ordem ?? 1e9) || ordemAlfabetica(a.municipio, b.municipio),
  );
  ranqueados = todos.filter((r) => r.acessivel && r.ranking);
  oficiais = todos.filter((r) => r.acessivel && r.oficial);
  // resumo antigo (antes do ranking oficial) nao tem o campo: trata todo mundo como oficial
  // resumo antigo (antes de exigir os 13 itens) nao tem o bit: quem tem posicao entra
  if (!resumo.campos.includes("posg") && !oficiais.length) {
    for (const r of ranqueados) r.oficial = r.posBr != null;
    oficiais = ranqueados.filter((r) => r.oficial);
  }
  totalRanking = resumo.oficiais || oficiais.length;
  listaOrdenada = [...oficiais, ...todos.filter((r) => !(r.acessivel && r.oficial))];
  calcularPorEstado(ranqueados);

  // posicao de cada cidade dentro do proprio estado (todos ja esta ordenado por nota)
  const porUf = {};
  for (const r of oficiais) r.pos = porUf[r.uf] = (porUf[r.uf] || 0) + 1;
  for (const r of oficiais) r.totalUf = porUf[r.uf];

  cabecalho(resumo);
  iniciarBusca();
  iniciarFicha();

  const semSite = await pedidoSemSite;
  const listaSemSite = Array.isArray(semSite) ? semSite : [];
  if (Mapa.iniciar(todos, listaSemSite, abrirFicha)) legendaMapa(listaSemSite.length);

  const ufs = [...new Set(todos.map((r) => r.uf).filter(Boolean))].sort();
  $("filtro-uf").append(...ufs.map((uf) => el("option", { value: uf, text: uf })));
  aplicarFiltros();
  legendaLuzes();
  distribuicao(ranqueados);

  let espera;
  $("filtro").addEventListener("input", () => {
    clearTimeout(espera);
    espera = setTimeout(aplicarFiltros, 150);
  });
  $("filtro-uf").addEventListener("change", aplicarFiltros);
  $("filtro-conceito").addEventListener("change", aplicarFiltros);
  $("ordem").addEventListener("change", aplicarFiltros);
  $("baixar-csv").addEventListener("click", baixarCsv);
  $("mais").addEventListener("click", mostrarMais);
  window.addEventListener("hashchange", abrirDoLink);

  const pedidoHistorico = buscarJson("dados/historico.json").catch(() => []);
  const depois = window.requestIdleCallback || ((f) => setTimeout(f, 120));
  depois(async () => {
    itens(ranqueados);
    const semanas = await pedidoHistorico;
    const lista = Array.isArray(semanas) ? semanas : [];
    estados(ranqueados, lista);
    evolucao(lista);
    if (resumo.anterior) movimento(resumo);
    medalhasSecao(resumo);
    abrirDoLink();
  });
}

iniciar();
