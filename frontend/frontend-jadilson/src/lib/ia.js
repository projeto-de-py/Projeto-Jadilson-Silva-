import { PRAZOS } from "@/data/escritorio";
import { apiIA } from "@/lib/api";

// A IA vive no servidor (/api/ia). As funções `solicitarSugestoes` e
// `completarTexto` chamam a API; se o servidor estiver fora do ar (rede ou 5xx)
// caem no modo LOCAL abaixo, que monta sugestões simples a partir dos dados do
// processo e do texto do documento (plano B, sem IA de verdade).

export const ATALHOS_IA = [
  { id: "resumo", rotulo: "Resumir este processo" },
  { id: "contestacao", rotulo: "Redigir contestação" },
  { id: "revisar", rotulo: "Revisar o texto" },
  { id: "continuar", rotulo: "Continuar a peça" },
];

const norm = (t) => t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

export function detectarAcao(pedido) {
  const t = norm(pedido);
  if (/resum/.test(t)) return "resumo";
  if (/contest/.test(t)) return "contestacao";
  if (/revis|corrij|ortograf/.test(t)) return "revisar";
  if (/continu|prossig|segu(ir|a) (a )?pe[cç]a/.test(t)) return "continuar";
  return "livre"; // qualquer outro pedido: a IA faz o que o advogado escreveu
}

const p = (texto) => `<p>${texto}</p>`;
const h2 = (texto) => `<h2>${texto}</h2>`;

function prazosAbertos(processo) {
  if (!processo) return [];
  return PRAZOS.filter((x) => x.processo === processo.numero).sort((a, b) => a.diasRestantes - b.diasRestantes);
}

const FASES = ["Petição inicial", "Instrução", "Sentença", "Recursal", "Concluído"];

function resumo(processo) {
  if (!processo) {
    return [{
      titulo: "Vincule um processo para resumir",
      previa: "Escolha um processo na caixa da IA ou no painel lateral para eu montar o resumo.",
      html: p("[Vincule um processo para gerar o resumo com partes, pedido, fase e prazos.]"),
      tipo: "Aviso",
    }];
  }
  const prazos = prazosAbertos(processo);
  const passados = FASES.slice(0, Math.max(1, FASES.indexOf(processo.status) + 1));
  const html = [
    h2("RESUMO DO PROCESSO"),
    p(`<strong>Processo:</strong> ${processo.numero} — ${processo.vara}.`),
    p(`<strong>Cliente:</strong> ${processo.cliente}.`),
    p(`<strong>Ação:</strong> ${processo.tipoAcao}. <strong>Valor:</strong> ${processo.valorCausa}.`),
    p(`<strong>Resumo dos fatos:</strong> ${processo.descricao}`),
    p(`<strong>Fase atual:</strong> ${processo.status} (etapas já vencidas: ${passados.join(" → ")}).`),
    prazos.length
      ? p(`<strong>Prazos em aberto:</strong> ${prazos.map((x) => `${esc(x.titulo)} (${new Date(x.dataLimite).toLocaleDateString("pt-BR")})`).join("; ")}.`)
      : p("<strong>Prazos em aberto:</strong> nenhum registrado."),
    p("<em>Rascunho gerado a partir dos dados cadastrados. Confira antes de usar.</em>"),
  ].join("");
  return [{
    titulo: "Resumo do processo",
    previa: `${processo.cliente} · ${processo.status} · ${prazos.length} prazo(s) em aberto.`,
    html,
    tipo: "Resumo",
  }];
}

function contestacao(processo) {
  const cliente = processo?.cliente ?? "[NOME DO CLIENTE]";
  return [
    {
      titulo: "Preliminares",
      previa: "Impugnação do valor da causa, ilegitimidade e prescrição, quando cabíveis.",
      html: h2("II – DAS PRELIMINARES") + p(`[Examinar inépcia da inicial, ilegitimidade de parte e prescrição. Registrar que ${cliente} impugna expressamente o valor atribuído à causa, se for o caso.]`),
      tipo: "Trecho",
    },
    {
      titulo: "Mérito: impugnação específica",
      previa: "Resposta ponto a ponto aos fatos narrados na inicial (art. 341 do CPC).",
      html: h2("III – DO MÉRITO") + p(`Os fatos narrados não correspondem à realidade. ${processo?.descricao ? `Quanto a “${processo.descricao}”, ` : ""}impugna-se especificamente cada alegação, conforme o art. 341 do CPC, sob pena de presunção de veracidade.`) + p("[Detalhar a defesa com os documentos que a sustentam e a jurisprudência aplicável.]"),
      tipo: "Trecho",
    },
  ];
}

function revisar(texto) {
  const t = norm(texto);
  const achados = [];
  if (!t.includes("gratuita"))
    achados.push({
      titulo: "Justiça gratuita não requerida",
      previa: "O texto não menciona o benefício da justiça gratuita.",
      html: h2("DA JUSTIÇA GRATUITA") + p("O(A) requerente declara não possuir condições de arcar com as custas e despesas do processo sem prejuízo do próprio sustento, requerendo os benefícios da justiça gratuita, nos termos do art. 98 do CPC."),
      tipo: "Revisão",
    });
  if (!t.includes("valor da causa") && !t.includes("da-se a causa") && !t.includes("da-se à causa"))
    achados.push({
      titulo: "Valor da causa ausente",
      previa: "Não encontrei a indicação do valor da causa (art. 319, V, do CPC).",
      html: p("Dá-se à causa o valor de R$ [VALOR DA CAUSA]."),
      tipo: "Revisão",
    });
  if (!t.includes("pede deferimento"))
    achados.push({
      titulo: "Fecho da peça",
      previa: "Falta o fecho com local, data e assinatura.",
      html: p("Nestes termos,<br>pede deferimento.") + p("Paulo Afonso/BA, [DATA].") + p("[NOME DO ADVOGADO] — OAB/BA nº [NÚMERO]"),
      tipo: "Revisão",
    });
  return achados;
}

function continuar(texto, processo) {
  const t = norm(texto);
  if (!t.includes("dos pedidos")) {
    return [{
      titulo: "Seção de pedidos",
      previa: "A peça ainda não tem a seção de pedidos.",
      html: h2("DOS PEDIDOS") + p("Ante o exposto, requer:") + "<ol><li><p>a citação da parte contrária para responder à ação;</p></li><li><p>a procedência dos pedidos formulados;</p></li><li><p>a condenação em custas e honorários advocatícios;</p></li><li><p>a produção de todos os meios de prova admitidos em direito.</p></li></ol>",
      tipo: "Trecho",
    }];
  }
  return [{
    titulo: "Seção de provas",
    previa: "Parágrafo sobre os meios de prova que serão utilizados.",
    html: h2("DAS PROVAS") + p(`Protesta-se pela produção de todos os meios de prova admitidos em direito${processo ? `, em especial a documental já anexada nos autos do processo ${processo.numero}` : ""}, bem como pelo depoimento pessoal e a oitiva de testemunhas, se necessário.`),
    tipo: "Trecho",
  }];
}

const esc = (t) => String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

/** Devolve a lista de sugestões para o pedido. */
export function gerarSugestoes({ pedido, acao, processo: processoBruto, textoDocumento }) {
  // Dados cadastrados entram no HTML das sugestões: escapa para nunca virar marcação.
  const processo = processoBruto
    ? Object.fromEntries(Object.entries(processoBruto).map(([k, v]) => [k, typeof v === "string" ? esc(v) : v]))
    : null;
  const tipo = acao ?? detectarAcao(pedido);
  const lista =
    tipo === "resumo" ? resumo(processo)
    : tipo === "contestacao" ? contestacao(processo)
    : tipo === "revisar" ? revisar(textoDocumento)
    : tipo === "livre" ? [{
        titulo: "Pedido livre precisa da IA do servidor",
        previa: "O modo local só atende os atalhos (resumir, contestação, revisar, continuar).",
        html: p("O modo local não entende pedidos escritos livremente."),
        tipo: "Aviso",
      }]
    : continuar(textoDocumento, processo);
  return lista.map((s, i) => ({ ...s, id: `${Date.now()}-${i}` }));
}

/* ------------------------------------------------------------------ *
 * Autocompletar (texto fantasma). SIMULADO por regras sobre o final do *
 * texto; o backend de IA vai devolver a continuação no mesmo formato.   *
 * ------------------------------------------------------------------ */

const REGRAS_COMPLETAR = [
  [/(,\s*)?requer:?$/, " a procedência total dos pedidos, com a condenação da parte ré ao pagamento das custas e dos honorários advocatícios."],
  [/nestes termos,?$/, " pede deferimento."],
  [/respeitosamente,?$/, " à presença de Vossa Excelência, apresentar o que segue."],
  [/justi[cç]a gratuita$/, ", nos termos do art. 98 do Código de Processo Civil."],
  [/tutela de urg[eê]ncia$/, ", presentes a probabilidade do direito e o perigo de dano, conforme o art. 300 do Código de Processo Civil."],
  [/inversão do ônus da prova$/, ", nos termos do art. 6º, VIII, do Código de Defesa do Consumidor."],
  [/taxa de juros$/, " contratada, que supera a taxa média de mercado divulgada pelo Banco Central do Brasil para a modalidade,"],
  [/honor[aá]rios advocat[ií]cios$/, " de sucumbência, a serem arbitrados por Vossa Excelência."],
  [/prescri[cç][aã]o (bienal|quinquenal)$/, ", contada a partir da extinção do contrato de trabalho, nos termos do art. 7º, XXIX, da Constituição Federal."],
  [/dá-se à causa o valor de$/, " R$ [VALOR DA CAUSA]."],
];

/** Continuação curta (uma frase) para o fim do texto, ou null se não houver. */
async function completarLocal({ textoAntes }) {
  await new Promise((r) => setTimeout(r, 350)); // latência simulada
  const fim = textoAntes.trimEnd().slice(-120);
  const alvo = fim.normalize("NFC");
  for (const [regra, texto] of REGRAS_COMPLETAR) {
    if (regra.test(alvo.toLowerCase())) return texto;
  }
  return null;
}

/* ------------------------------------------------------------------ *
 * Chamadas ao servidor, com o modo local como plano B.                *
 * ------------------------------------------------------------------ */

// Erros que o advogado precisa ver. O servidor respondeu e explicou (ex.: 503 = IA sem resposta,
// 429 = limite): esconder isso atrás do modo local daria uma resposta que não é a do pedido.
const ERROS_VISIVEIS = [401, 403, 422, 429, 502, 503];

/** Dados do processo vinculado, em texto, para a IA usar como contexto (nada de CPF aqui). */
function contextoDoProcesso(processo) {
  if (!processo) return "";
  const prazos = PRAZOS.filter((x) => x.processo === processo.numero)
    .map((x) => `${x.titulo} (${new Date(x.dataLimite).toLocaleDateString("pt-BR")})`)
    .join("; ");
  return [
    `Processo: ${processo.numero} — ${processo.vara}`,
    `Cliente: ${processo.cliente}`,
    `Ação: ${processo.tipoAcao}. Valor: ${processo.valorCausa}`,
    `Fase atual: ${processo.status}. Aberto em ${processo.criadoEm}`,
    processo.descricao ? `Resumo dos fatos: ${processo.descricao}` : "",
    prazos ? `Prazos em aberto: ${prazos}` : "Prazos em aberto: nenhum registrado",
  ].filter(Boolean).join("\n");
}

/**
 * Pede sugestões ao servidor. Devolve { sugestoes, perguntas, avisos, fonte }.
 * - O processo vinculado (que ainda mora só no navegador) vai como `contexto_processo`.
 * - Se o servidor responder com erro (pedido recusado, limite, IA sem resposta), o erro é
 *   mostrado ao advogado com a explicação do servidor.
 * - Só com a rede fora (servidor inalcançável) usa o modo local e avisa.
 */
export async function solicitarSugestoes({ pedido, acao, processo, textoDocumento, area, tipoPeca, csrf }) {
  const tarefa = acao ?? detectarAcao(pedido);
  const local = () => gerarSugestoes({ pedido, acao: tarefa, processo, textoDocumento });

  try {
    const r = await apiIA("sugerir", {
      csrf,
      body: {
        tarefa,
        pedido: pedido.slice(0, 2000),
        area: area || null,
        tipo_peca: tipoPeca || null,
        texto_documento: textoDocumento.slice(0, 60000),
        contexto_processo: contextoDoProcesso(processo),
      },
    });
    return { sugestoes: r.sugestoes, perguntas: r.perguntas, avisos: r.avisos, fonte: r.simulado ? "servidor-simulado" : "servidor" };
  } catch (erro) {
    if (ERROS_VISIVEIS.includes(erro.status)) throw erro;
    return {
      sugestoes: local(),
      perguntas: [],
      avisos: ["O servidor de IA está indisponível. Estas sugestões vieram do modo local, mais simples."],
      fonte: "local",
    };
  }
}

/** Continuação curta para o texto fantasma (servidor; plano B local se ele cair). */
export async function completarTexto({ textoAntes, area, csrf, sinal }) {
  try {
    const r = await apiIA("completar", { csrf, signal: sinal, body: { texto_antes: textoAntes.slice(-3000), area: area || null } });
    return r.continuacao || null;
  } catch (erro) {
    if (erro?.name === "AbortError") return null;
    // IA sem resposta (limite gratuito, modelo saturado): quem chamou mostra o aviso.
    if ([429, 502, 503].includes(erro.status)) throw erro;
    if (erro.status > 0) return null; // 401/403/422: sem sugestão
    return completarLocal({ textoAntes }); // só com a rede fora
  }
}

const TAGS_OK = new Set(["P", "H2", "H3", "OL", "UL", "LI", "STRONG", "EM", "BR", "BLOCKQUOTE"]);

/** Defesa em profundidade: o servidor já sanea, mas o cartão nunca exibe HTML fora da lista. */
export function sanitizarHtml(html) {
  const doc = new DOMParser().parseFromString(`<body>${html}</body>`, "text/html");
  const limpar = (no) => {
    for (const filho of [...no.childNodes]) {
      if (filho.nodeType === 3) continue;
      if (filho.nodeType !== 1 || !TAGS_OK.has(filho.tagName)) {
        filho.replaceWith(...(filho.nodeType === 1 ? [...filho.childNodes] : []));
        continue;
      }
      for (const atributo of [...filho.attributes]) filho.removeAttribute(atributo.name);
      limpar(filho);
    }
  };
  limpar(doc.body);
  return doc.body.innerHTML;
}
