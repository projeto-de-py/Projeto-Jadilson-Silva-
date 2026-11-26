import { useCallback, useEffect, useSyncExternalStore } from "react";
import { useSessao } from "@/context/sessao";
import { useToast } from "@/components/ui";
import { apiJson } from "@/lib/api";

// ---------------------------------------------------------------------------
// Documentos vivem no banco (/api/documentos). Este modulo guarda uma copia
// compartilhada em memoria para que as telas tenham a MESMA lista sem ler
// localStorage (antes cada hook lia o navegador por conta propria).
//
// `criar` continua sincrono e devolve o documento: as telas navegam para
// /documentos/:id logo depois. Por isso o documento ganha um id temporario,
// trocado pelo id do banco quando o POST responde — o id visivel nao muda,
// evitando remontar o editor no meio da digitacao.
// ---------------------------------------------------------------------------

let docs = [];
let carregado = false;
let carregandoDocs = false;
let carregandoPromise = null;
let sequencia = 0;
const ouvintes = new Set();
const idsServidor = new Map(); // id visível -> id do banco
const criacoesPendentes = new Map(); // id temporario -> Promise do POST

function notificar() {
  for (const ouvinte of ouvintes) ouvinte(docs);
}

function assinar(ouvinte) {
  ouvintes.add(ouvinte);
  return () => ouvintes.delete(ouvinte);
}

function instantaneo() {
  return docs;
}

function instantaneoCarregando() {
  return carregandoDocs;
}

function deApi(d) {
  const documento = {
    id: String(d.id),
    titulo: d.titulo,
    area: d.area,
    tipo: d.tipo,
    html: d.html,
    atualizadoEm: new Date(d.atualizado_em).getTime(),
  };
  // O frontend chama de `processoId` o vinculo com o CASO da carteira.
  if (d.caso_id != null) documento.processoId = d.caso_id;
  if (d.cliente_id != null) documento.clienteId = d.cliente_id;
  if (d.pasta_id != null) documento.pastaId = d.pasta_id;
  return documento;
}

function paraApi(dados) {
  const corpo = {};
  if (dados.titulo !== undefined) corpo.titulo = dados.titulo;
  if (dados.area !== undefined) corpo.area = dados.area;
  if (dados.tipo !== undefined) corpo.tipo = dados.tipo;
  if (dados.html !== undefined) corpo.html = dados.html;
  if ("processoId" in dados) corpo.caso_id = dados.processoId ? Number(dados.processoId) : null;
  if ("clienteId" in dados) corpo.cliente_id = dados.clienteId != null ? Number(dados.clienteId) : null;
  if ("pastaId" in dados) corpo.pasta_id = dados.pastaId || null;
  return corpo;
}

async function carregar() {
  if (carregandoPromise) return carregandoPromise;
  carregandoDocs = true;
  notificar();
  carregandoPromise = apiJson("documentos?limite=200")
    .then((resposta) => {
      const itens = Array.isArray(resposta?.itens) ? resposta.itens : [];
      docs = itens.map(deApi);
      idsServidor.clear();
      itens.forEach((d) => idsServidor.set(String(d.id), d.id));
      carregado = true;
      notificar();
    })
    .catch(() => {
      // Sem banco, a tela mostra a lista vazia e o toast de falha nas acoes.
      carregado = true;
      notificar();
    })
    .finally(() => {
      carregandoDocs = false;
      carregandoPromise = null;
      notificar();
    });
  return carregandoPromise;
}

export function useDocumentos() {
  const lista = useSyncExternalStore(assinar, instantaneo, instantaneo);
  const carregando = useSyncExternalStore(
    assinar,
    instantaneoCarregando,
    instantaneoCarregando,
  );
  const { csrf } = useSessao();
  const { toast } = useToast();

  useEffect(() => {
    if (!carregado) carregar();
  }, []);

  const avisarErro = useCallback(
    (falha, titulo) => {
      toast({
        tipo: "erro",
        titulo,
        descricao: falha?.message || "Não foi possível conectar ao servidor.",
      });
    },
    [toast],
  );

  const criar = useCallback(
    (dados) => {
      const id = `temp-${Date.now()}-${++sequencia}`;
      const doc = { id, atualizadoEm: Date.now(), ...dados };
      docs = [doc, ...docs];
      notificar();

      const promessa = apiJson("documentos", {
        method: "POST",
        csrf,
        body: paraApi(dados),
      })
        .then((criado) => {
          idsServidor.set(id, criado.id);
          // Mantem `id` (o da URL) e so sincroniza os dados do servidor.
          docs = docs.map((d) =>
            d.id === id ? { ...deApi(criado), id } : d,
          );
          notificar();
          return criado;
        })
        .catch((falha) => {
          docs = docs.filter((d) => d.id !== id);
          idsServidor.delete(id);
          notificar();
          avisarErro(falha, "Não foi possível criar o documento");
        });
      criacoesPendentes.set(id, promessa);
      return doc;
    },
    [csrf, avisarErro],
  );

  /** Espera o POST (quando ainda pendente) e devolve o id do banco. */
  function idServidor(id) {
    return (criacoesPendentes.get(id) ?? Promise.resolve()).then(() => {
      const sid = idsServidor.get(id);
      if (sid == null) throw new Error("Documento não foi salvo no servidor.");
      return sid;
    });
  }

  const atualizar = useCallback(
    (id, parcial) => {
      docs = docs.map((d) =>
        d.id === id ? { ...d, ...parcial, atualizadoEm: Date.now() } : d,
      );
      notificar();
      idServidor(id)
        .then((sid) =>
          apiJson(`documentos/${sid}`, {
            method: "PATCH",
            csrf,
            body: paraApi(parcial),
          }),
        )
        .catch((falha) => avisarErro(falha, "Não foi possível salvar o documento"));
    },
    [csrf, avisarErro],
  );

  const excluir = useCallback(
    (id) => {
      const anterior = docs;
      docs = docs.filter((d) => d.id !== id);
      notificar();
      idServidor(id)
        .then((sid) => apiJson(`documentos/${sid}`, { method: "DELETE", csrf }))
        .then(() => {
          criacoesPendentes.delete(id);
          idsServidor.delete(id);
        })
        .catch((falha) => {
          docs = anterior;
          notificar();
          avisarErro(falha, "Não foi possível excluir o documento");
        });
    },
    [csrf, avisarErro],
  );

  /** Muda a pasta sem alterar `atualizadoEm` (não é edição de conteúdo). */
  const mover = useCallback(
    (id, destino) => {
      docs = docs.map((d) => (d.id === id ? { ...d, ...destino } : d));
      notificar();
      idServidor(id)
        .then((sid) =>
          apiJson(`documentos/${sid}/mover`, {
            method: "PATCH",
            csrf,
            body: {
              cliente_id: destino.clienteId ?? null,
              pasta_id: destino.pastaId ?? null,
            },
          }),
        )
        .catch((falha) => avisarErro(falha, "Não foi possível mover o documento"));
    },
    [csrf, avisarErro],
  );

  const recarregar = useCallback(async () => {
    carregado = false;
    await carregar();
  }, []);

  return {
    docs: lista,
    carregando,
    criar,
    atualizar,
    excluir,
    mover,
    recarregar,
  };
}

// ---------- Exportação em PDF (diálogo de impressão: "Salvar como PDF") ----------

export const PADRAO_PAGINA = {
  nome: "Padrão do escritório (ABNT)",
  margens: "30mm 20mm 20mm 30mm", // superior, direita, inferior, esquerda
  fonte: "'Times New Roman', Times, serif",
  tamanho: "12pt",
  entrelinhas: 1.5,
};

export const ESTILO_DOCUMENTO = `
  .doc { font-family: ${PADRAO_PAGINA.fonte}; font-size: ${PADRAO_PAGINA.tamanho}; line-height: ${PADRAO_PAGINA.entrelinhas}; color: #111; text-align: justify; }
  .doc p { margin: 0 0 6pt; text-indent: 1.25cm; }
  .doc p[style*="text-align: left"], .doc p[style*="text-align: center"], .doc p[style*="text-align: right"] { text-indent: 0; }
  .doc h1 { font-size: 12pt; text-align: center; text-transform: uppercase; font-weight: 700; margin: 18pt 0 12pt; }
  .doc h2 { font-size: 12pt; font-weight: 700; text-transform: uppercase; margin: 14pt 0 6pt; text-align: left; }
  .doc h3 { font-size: 12pt; font-weight: 700; margin: 10pt 0 4pt; text-align: left; }
  .doc ul, .doc ol { margin: 0 0 6pt; padding-left: 1.25cm; }
  .doc li p { text-indent: 0; margin: 0; }
  .doc blockquote { margin: 6pt 0 6pt 4cm; font-size: 10pt; line-height: 1; text-align: justify; }
  .doc blockquote p { text-indent: 0; }
  .doc table { border-collapse: collapse; width: 100%; margin: 6pt 0; }
  .doc th, .doc td { border: 1px solid #444; padding: 4pt 6pt; vertical-align: top; text-align: left; }
  .doc th { background: #f0f0f0; font-weight: 700; }
  .doc mark { background: #fff3a3; }
`;

function escapar(t) {
  return String(t ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

export function exportarDocumentoPdf(titulo, html) {
  const janela = window.open("", "_blank", "width=900,height=1000");
  if (!janela) return false;
  janela.document.write(`<!doctype html><html lang="pt-BR"><head><meta charset="utf-8" />
    <title>${escapar(titulo)}</title>
    <style>
      @page { size: A4; margin: ${PADRAO_PAGINA.margens}; }
      * { box-sizing: border-box; }
      body { margin: 0; }
      ${ESTILO_DOCUMENTO}
    </style></head>
    <body><div class="doc">${html}</div>
    <script>window.onload = () => setTimeout(() => window.print(), 250);</script>
    </body></html>`);
  janela.document.close();
  return true;
}

/**
 * Gera o PDF do documento NO NAVEGADOR e devolve em base64 (sem o prefixo "data:").
 * Usado para enviar à assinatura eletrônica. O PDF é de imagem (cada página é uma
 * foto do texto): serve para assinar, mas o texto não é selecionável.
 */
export async function gerarPdfBase64(html) {
  const { default: html2pdf } = await import("html2pdf.js");
  const raiz = document.createElement("div");
  raiz.style.cssText = "position:fixed;left:-10000px;top:0;background:#fff";
  raiz.innerHTML = `<style>${ESTILO_DOCUMENTO} .doc { width: 160mm; }</style><div class="doc">${html}</div>`;
  document.body.appendChild(raiz);
  try {
    const uri = await html2pdf()
      .set({
        margin: [30, 30, 20, 20], // topo, esquerda, base, direita (mm) = padrão do escritório
        image: { type: "jpeg", quality: 0.92 },
        html2canvas: { scale: 2, useCORS: true, backgroundColor: "#ffffff" },
        jsPDF: { unit: "mm", format: "a4", orientation: "portrait" },
        pagebreak: { mode: ["css", "legacy"] },
      })
      .from(raiz.lastElementChild)
      .outputPdf("datauristring");
    return uri.split(",")[1];
  } finally {
    raiz.remove();
  }
}
