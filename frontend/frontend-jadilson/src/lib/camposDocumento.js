import { Mark, mergeAttributes } from "@tiptap/core";

/**
 * Preenche os marcadores da peça ([NOME DO CLIENTE], [CPF], [VARA]...) com os dados do
 * processo e do cliente vinculados.
 *
 * O texto preenchido recebe a marca `campoAuto` (<span data-campo="cliente">). Ao vincular
 * OUTRO processo, trocamos o conteúdo de todo trecho marcado: sem a marca não saberíamos o que
 * veio do cliente antigo e o que o advogado escreveu. Na exportação para PDF é um <span> comum.
 */

export const CampoAuto = Mark.create({
  name: "campoAuto",
  inclusive: false,
  excludes: "campoAuto",
  addAttributes() {
    return {
      campo: {
        default: null,
        parseHTML: (el) => el.getAttribute("data-campo"),
        renderHTML: (atributos) => ({ "data-campo": atributos.campo }),
      },
    };
  },
  parseHTML() {
    return [{ tag: "span[data-campo]" }];
  },
  renderHTML({ HTMLAttributes }) {
    return ["span", mergeAttributes({ class: "campo-auto" }, HTMLAttributes), 0];
  },
});

// `colchetes`: marcadores que o campo substitui. `valorAnterior`: também troca o valor do processo
// anterior que esteja no texto sem marca (peça criada já preenchida).
const CAMPOS = {
  cliente: { marcador: "[NOME DO CLIENTE]", colchetes: ["NOME DO CLIENTE", "NOME DO RECLAMANTE", "NOME DO AUTOR"], valorAnterior: true },
  numero: { marcador: "[NÚMERO DO PROCESSO]", colchetes: ["NÚMERO DO PROCESSO", "Nº DO PROCESSO"], valorAnterior: true },
  vara: { marcador: "[VARA]", colchetes: ["VARA"], valorAnterior: true },
  numeroDaVara: { marcador: "[NÚMERO]", colchetes: [], padraoExtra: "\\[NÚMERO\\](?=ª VARA)" },
  valorCausa: { marcador: "[VALOR DA CAUSA]", colchetes: ["VALOR DA CAUSA"], valorAnterior: true },
  cpf: { marcador: "[CPF]", colchetes: ["CPF"], valorAnterior: true },
};

const SEM_DADO = new Set(["", "A definir", "Não informado", "Foro / Vara em definição"]);
const MIN_CARACTERES_VALOR_ANTERIOR = 4;

const util = (valor) => (typeof valor === "string" && !SEM_DADO.has(valor.trim()) ? valor.trim() : "");
const escapar = (texto) => texto.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** Valores que o sistema sabe. RG, endereço e estado civil continuam para o advogado. */
export function dadosDoProcesso(processo, cliente) {
  if (!processo) return {};
  const vara = util(processo.vara);
  const documento = String(cliente?.documento ?? "");
  const numero = util(processo.numero);
  return {
    cliente: util(processo.cliente) || util(cliente?.nome),
    numero: numero.startsWith("CASO-") ? "" : numero,
    vara,
    numeroDaVara: /^(\d+)\s*ª/.exec(vara)?.[1] ?? "",
    valorCausa: util(processo.valorCausa),
    cpf: documento.replace(/\D/g, "").length === 11 ? documento : "", // [CNPJ] é da outra parte: nunca preenchemos
  };
}

function expressaoDe(campo, anteriores) {
  const { colchetes, padraoExtra, valorAnterior } = CAMPOS[campo];
  const fontes = colchetes.map((c) => `\\[${escapar(c)}\\]`);
  if (padraoExtra) fontes.push(padraoExtra);
  const antigo = util(anteriores?.[campo]);
  if (valorAnterior && antigo.length >= MIN_CARACTERES_VALOR_ANTERIOR) fontes.push(escapar(antigo));
  return fontes.length ? new RegExp(fontes.join("|"), "gi") : null;
}

function trocasDoDocumento(doc, tipoMarca, novos, anteriores) {
  const expressoes = Object.fromEntries(Object.keys(CAMPOS).map((c) => [c, novos[c] ? expressaoDe(c, anteriores) : null]));
  const trocas = [];

  doc.descendants((no, pos) => {
    if (!no.isText) return;
    const marca = no.marks.find((m) => m.type === tipoMarca);

    if (marca) {
      const valor = novos[marca.attrs.campo];
      // Sem o dado no novo cliente (ex.: CPF), volta o marcador: melhor "[CPF]" visível que o CPF de outra pessoa.
      if (!valor) trocas.push({ from: pos, to: pos + no.nodeSize, texto: CAMPOS[marca.attrs.campo]?.marcador ?? no.text, marcas: no.marks.filter((m) => m.type !== tipoMarca) });
      else if (valor !== no.text) trocas.push({ from: pos, to: pos + no.nodeSize, texto: valor, marcas: no.marks });
      return;
    }

    for (const [campo, expressao] of Object.entries(expressoes)) {
      if (!expressao) continue;
      for (const m of no.text.matchAll(expressao)) {
        if (m[0] === novos[campo]) continue;
        trocas.push({ from: pos + m.index, to: pos + m.index + m[0].length, texto: novos[campo], marcas: [...no.marks, tipoMarca.create({ campo })] });
      }
    }
  });
  return trocas;
}

/** Preenche ou atualiza os marcadores do documento. Devolve quantos trechos mudaram. */
export function preencherCampos(editor, novos, anteriores = {}) {
  const { state } = editor;
  const tipoMarca = state.schema.marks.campoAuto;
  if (!tipoMarca) return 0;

  const trocas = trocasDoDocumento(state.doc, tipoMarca, novos, anteriores);
  if (!trocas.length) return 0;

  const tr = state.tr;
  for (const t of trocas.sort((a, b) => b.from - a.from)) {
    tr.replaceWith(t.from, t.to, state.schema.text(t.texto, t.marcas)); // do fim para o começo: posições não se deslocam
  }
  tr.setMeta("preventUpdate", true); // não dispara o autocompletar da IA; quem chama salva o documento
  editor.view.dispatch(tr);
  return trocas.length;
}
