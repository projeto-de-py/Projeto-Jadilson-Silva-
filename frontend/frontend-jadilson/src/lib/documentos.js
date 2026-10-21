import { useCallback, useEffect, useState } from "react";
import { MODELOS, preencherModelo } from "@/data/modelos";

// Documentos ficam no navegador (localStorage) até existir um endpoint no backend.
const CHAVE = "documentos-v1";

function ler() {
  try {
    const bruto = localStorage.getItem(CHAVE);
    if (bruto) return JSON.parse(bruto);
  } catch {
    /* sem acesso ao armazenamento */
  }
  return null;
}

function gravar(docs) {
  try {
    localStorage.setItem(CHAVE, JSON.stringify(docs));
  } catch {
    /* armazenamento cheio ou bloqueado */
  }
}

function exemplos() {
  const agora = Date.now();
  const novo = (id, modelo, titulo, dados, atraso) => ({
    id,
    titulo,
    area: modelo.area,
    tipo: modelo.rotulo,
    html: preencherModelo(modelo.html, dados),
    atualizadoEm: agora - atraso,
  });
  const m = (id) => MODELOS.find((x) => x.id === id);
  return [
    novo("doc-exemplo-1", m("revisional-contrato"), "Revisional – Maria da Conceição Silva",
      { cliente: "Maria da Conceição Silva", numero: "0000001-12.2026.8.00.0100" }, 3600_000),
    novo("doc-exemplo-2", m("auxilio-incapacidade"), "Auxílio por incapacidade – Carlos Eduardo Lima",
      { cliente: "Carlos Eduardo Lima", numero: "0000311-88.2026.8.00.0100" }, 86_400_000),
  ];
}

export function useDocumentos() {
  const [docs, setDocs] = useState(() => ler() ?? exemplos());

  useEffect(() => {
    gravar(docs);
  }, [docs]);

  const criar = useCallback((dados) => {
    const doc = { id: `doc-${Date.now()}`, atualizadoEm: Date.now(), ...dados };
    setDocs((atual) => [doc, ...atual]);
    return doc;
  }, []);

  const atualizar = useCallback((id, parcial) => {
    setDocs((atual) => atual.map((d) => (d.id === id ? { ...d, ...parcial, atualizadoEm: Date.now() } : d)));
  }, []);

  const excluir = useCallback((id) => setDocs((atual) => atual.filter((d) => d.id !== id)), []);

  return { docs, criar, atualizar, excluir };
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
