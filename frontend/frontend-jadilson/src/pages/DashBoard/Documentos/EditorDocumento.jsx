import { useEffect, useMemo, useRef, useState } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import TextAlign from "@tiptap/extension-text-align";
import { TextStyleKit } from "@tiptap/extension-text-style";
import Highlight from "@tiptap/extension-highlight";
import { Table, TableCell, TableHeader, TableRow } from "@tiptap/extension-table";
import CharacterCount from "@tiptap/extension-character-count";
import Placeholder from "@tiptap/extension-placeholder";
import {
  IconArrowUturnBackward,
  IconArrowUturnForward,
  IconBold,
  IconItalic,
  IconUnderline,
  IconStrikethrough,
  IconHighlighter,
  IconTextAlignleft,
  IconTextAligncenter,
  IconTextAlignright,
  IconTextJustify,
  IconListBullet,
  IconListNumber,
  IconQuoteOpening,
  IconTablecells,
  IconChevronLeft,
  IconArrowDownDocument,
  IconCheckmark,
  IconWandAndSparkles,
} from "symbols-react";
import { Button, Select, Badge } from "@/components/ui";
import { ModalRedatorIA } from "@/components/modais/ModalRedatorIA";
import { PROCESSOS_INICIAIS } from "@/data/escritorio";
import { AREAS_DOC } from "@/data/modelos";
import { ESTILO_DOCUMENTO, PADRAO_PAGINA, exportarDocumentoPdf, useDocumentos } from "@/lib/documentos";
import { cn } from "@/lib/cn";

const FONTES = [
  { rotulo: "Times New Roman", valor: "'Times New Roman', Times, serif" },
  { rotulo: "Arial", valor: "Arial, Helvetica, sans-serif" },
  { rotulo: "Calibri", valor: "Calibri, Carlito, sans-serif" },
  { rotulo: "Georgia", valor: "Georgia, serif" },
];
const TAMANHOS = [10, 11, 12, 13, 14, 16, 18, 20, 24];
const ENTRELINHAS = ["1", "1.15", "1.5", "2"];
const ZOOMS = [75, 100, 125];
// Converte o texto da IA em parágrafos; linhas como "I – DOS FATOS" viram seções.
function textoParaHtml(texto) {
  const escapar = (t) => t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return texto
    .split(/\n{2,}/)
    .map((bloco) => bloco.trim())
    .filter(Boolean)
    .map((bloco) => {
      const [primeira, ...resto] = bloco.split("\n");
      if (/^[IVX]+\s+[–-]\s+/.test(primeira)) {
        const corpo = resto.length ? `<p>${escapar(resto.join(" "))}</p>` : "";
        return `<h2>${escapar(primeira)}</h2>${corpo}`;
      }
      return `<p>${escapar(bloco).replace(/\n/g, "<br>")}</p>`;
    })
    .join("");
}

const PAGINA_PX = 1122.5; // 297 mm a 96 dpi

function Botao({ ativo, aoClicar, rotulo, children, disabled }) {
  return (
    <button
      type="button"
      title={rotulo}
      aria-label={rotulo}
      aria-pressed={ativo}
      disabled={disabled}
      onMouseDown={(e) => e.preventDefault()}
      onClick={aoClicar}
      className={cn(
        "flex size-8 shrink-0 items-center justify-center rounded-[8px] transition-colors disabled:opacity-40",
        ativo ? "bg-primary text-primary-foreground" : "text-ink-muted hover:bg-surface-muted hover:text-ink",
      )}
    >
      {children}
    </button>
  );
}

const Divisor = () => <span aria-hidden="true" className="bg-border mx-1 h-5 w-px shrink-0" />;

const seletor = "border-border bg-surface text-ink focus-visible:ring-ring h-8 rounded-[8px] border px-2 text-13 focus-visible:ring-2 focus-visible:outline-none";

export function EditorDocumento() {
  const { id } = useParams();
  const { docs, atualizar } = useDocumentos();
  const doc = useMemo(() => docs.find((d) => d.id === id), [docs, id]);
  if (!doc) return <Navigate to="/documentos" replace />;
  return <Editor key={doc.id} doc={doc} atualizar={atualizar} />;
}

function Editor({ doc, atualizar }) {
  const [titulo, setTitulo] = useState(doc.titulo);
  const [salvo, setSalvo] = useState(true);
  const [zoom, setZoom] = useState(100);
  const [paginas, setPaginas] = useState(1);
  const [processoId, setProcessoId] = useState("");
  const [iaAberta, setIaAberta] = useState(false);
  const folha = useRef(null);
  const timer = useRef(null);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({ heading: { levels: [1, 2, 3] } }),
      TextStyleKit,
      TextAlign.configure({ types: ["heading", "paragraph"] }),
      Highlight,
      Table.configure({ resizable: false }),
      TableRow,
      TableHeader,
      TableCell,
      CharacterCount,
      Placeholder.configure({ placeholder: "Comece a escrever a peça…" }),
    ],
    content: doc.html,
    shouldRerenderOnTransaction: true,
    editorProps: { attributes: { class: "doc", spellcheck: "true", lang: "pt-BR" } },
    onUpdate: ({ editor: ed }) => {
      setSalvo(false);
      clearTimeout(timer.current);
      timer.current = setTimeout(() => {
        atualizar(doc.id, { html: ed.getHTML() });
        setSalvo(true);
      }, 600);
    },
  });

  useEffect(() => () => clearTimeout(timer.current), []);

  // Páginas estimadas a partir da altura real da folha.
  useEffect(() => {
    if (!folha.current) return undefined;
    const medir = () => setPaginas(Math.max(1, Math.ceil(folha.current.scrollHeight / PAGINA_PX - 0.02)));
    medir();
    const obs = new ResizeObserver(medir);
    obs.observe(folha.current);
    return () => obs.disconnect();
  }, [editor]);

  if (!editor) return null;

  const cmd = () => editor.chain().focus();
  const estilo = editor.getAttributes("textStyle");
  const fonteAtual = FONTES.find((f) => f.valor === estilo.fontFamily)?.valor ?? "";
  const tamanhoAtual = estilo.fontSize ? parseInt(estilo.fontSize, 10) : "";
  const blocoAtual = editor.isActive("heading", { level: 1 }) ? "h1" : editor.isActive("heading", { level: 2 }) ? "h2" : editor.isActive("heading", { level: 3 }) ? "h3" : "p";
  const emTabela = editor.isActive("table");

  const processo = PROCESSOS_INICIAIS.find((p) => String(p.id) === processoId);
  const dadosProcesso = processo
    ? [
        ["Cliente", processo.cliente],
        ["Nº do processo", processo.numero],
        ["Vara", processo.vara],
        ["Valor da causa", processo.valorCausa],
      ]
    : [];

  const titulos = [];
  editor.state.doc.descendants((no, pos) => {
    if (no.type.name === "heading") titulos.push({ nivel: no.attrs.level, texto: no.textContent, pos });
  });

  function salvarTitulo(valor) {
    setTitulo(valor);
    atualizar(doc.id, { titulo: valor });
  }

  function irPara(pos) {
    editor.chain().focus().setTextSelection(pos + 1).scrollIntoView().run();
  }

  const area = AREAS_DOC.find((a) => a.id === doc.area);

  return (
    <div className="space-y-6">
      {/* Cabeçalho do documento */}
      <div className="flex flex-wrap items-center gap-4">
        <Link to="/documentos" aria-label="Voltar para documentos" className="text-ink-muted hover:bg-surface-muted hover:text-ink flex size-10 items-center justify-center rounded-input transition-colors">
          <IconChevronLeft className="size-4" fill="currentColor" />
        </Link>
        <div className="min-w-0 flex-1">
          <input
            value={titulo}
            onChange={(e) => salvarTitulo(e.target.value)}
            aria-label="Título do documento"
            maxLength={120}
            className="font-heading text-24 text-ink focus:border-border w-full truncate rounded-input border border-transparent bg-transparent px-2 py-1 font-bold tracking-tight focus:outline-none"
          />
          <div className="flex items-center gap-2 px-2">
            {area && <Badge tone={area.tom}>{area.rotulo}</Badge>}
            <span className="text-12 text-ink-muted">{doc.tipo}</span>
            <span className="text-12 text-ink-muted flex items-center gap-1" role="status">
              {salvo ? (<><IconCheckmark className="size-3 text-status-ok" fill="currentColor" /> Salvo</>) : "Salvando…"}
            </span>
          </div>
        </div>
        <Button variant="secondary" className="gap-2" onClick={() => setIaAberta(true)}>
          <IconWandAndSparkles className="size-4 text-accent" fill="currentColor" />
          Redigir com IA
        </Button>
        <Button variant="primary" className="gap-2" onClick={() => exportarDocumentoPdf(titulo, editor.getHTML())}>
          <IconArrowDownDocument className="size-4" fill="currentColor" />
          Exportar PDF
        </Button>
      </div>

      <div className="bg-surface border-border overflow-hidden rounded-card border">
        {/* Faixa de formatação */}
        <div className="border-border bg-surface flex flex-wrap items-center gap-1 border-b p-2" role="toolbar" aria-label="Formatação">
          <Botao rotulo="Desfazer" aoClicar={() => cmd().undo().run()} disabled={!editor.can().undo()}><IconArrowUturnBackward className="size-4" fill="currentColor" /></Botao>
          <Botao rotulo="Refazer" aoClicar={() => cmd().redo().run()} disabled={!editor.can().redo()}><IconArrowUturnForward className="size-4" fill="currentColor" /></Botao>
          <Divisor />

          <select
            aria-label="Estilo do parágrafo"
            className={cn(seletor, "w-32")}
            value={blocoAtual}
            onChange={(e) => {
              const v = e.target.value;
              if (v === "p") cmd().setParagraph().run();
              else cmd().setHeading({ level: Number(v[1]) }).run();
            }}
          >
            <option value="p">Texto normal</option>
            <option value="h1">Título</option>
            <option value="h2">Seção</option>
            <option value="h3">Subseção</option>
          </select>
          <select
            aria-label="Fonte"
            className={cn(seletor, "w-40")}
            value={fonteAtual}
            onChange={(e) => (e.target.value ? cmd().setFontFamily(e.target.value).run() : cmd().unsetFontFamily().run())}
          >
            <option value="">Padrão (Times New Roman)</option>
            {FONTES.map((f) => <option key={f.rotulo} value={f.valor}>{f.rotulo}</option>)}
          </select>
          <select
            aria-label="Tamanho da fonte"
            className={cn(seletor, "w-16")}
            value={tamanhoAtual}
            onChange={(e) => (e.target.value ? cmd().setFontSize(`${e.target.value}pt`).run() : cmd().unsetFontSize().run())}
          >
            <option value="">12</option>
            {TAMANHOS.filter((t) => t !== 12).map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <Divisor />

          <Botao rotulo="Negrito" ativo={editor.isActive("bold")} aoClicar={() => cmd().toggleBold().run()}><IconBold className="size-4" fill="currentColor" /></Botao>
          <Botao rotulo="Itálico" ativo={editor.isActive("italic")} aoClicar={() => cmd().toggleItalic().run()}><IconItalic className="size-4" fill="currentColor" /></Botao>
          <Botao rotulo="Sublinhado" ativo={editor.isActive("underline")} aoClicar={() => cmd().toggleUnderline().run()}><IconUnderline className="size-4" fill="currentColor" /></Botao>
          <Botao rotulo="Tachado" ativo={editor.isActive("strike")} aoClicar={() => cmd().toggleStrike().run()}><IconStrikethrough className="size-4" fill="currentColor" /></Botao>
          <Botao rotulo="Realçar" ativo={editor.isActive("highlight")} aoClicar={() => cmd().toggleHighlight().run()}><IconHighlighter className="size-4" fill="currentColor" /></Botao>
          <label className="relative flex size-8 shrink-0 cursor-pointer items-center justify-center rounded-[8px] hover:bg-surface-muted" title="Cor do texto">
            <span className="sr-only">Cor do texto</span>
            <span className="text-13 text-ink font-bold" style={{ borderBottom: `3px solid ${estilo.color ?? "currentColor"}` }}>A</span>
            <input type="color" className="absolute inset-0 cursor-pointer opacity-0" value={estilo.color ?? "#111111"} onChange={(e) => cmd().setColor(e.target.value).run()} />
          </label>
          <Divisor />

          <Botao rotulo="Alinhar à esquerda" ativo={editor.isActive({ textAlign: "left" })} aoClicar={() => cmd().setTextAlign("left").run()}><IconTextAlignleft className="size-4" fill="currentColor" /></Botao>
          <Botao rotulo="Centralizar" ativo={editor.isActive({ textAlign: "center" })} aoClicar={() => cmd().setTextAlign("center").run()}><IconTextAligncenter className="size-4" fill="currentColor" /></Botao>
          <Botao rotulo="Alinhar à direita" ativo={editor.isActive({ textAlign: "right" })} aoClicar={() => cmd().setTextAlign("right").run()}><IconTextAlignright className="size-4" fill="currentColor" /></Botao>
          <Botao rotulo="Justificar" ativo={editor.isActive({ textAlign: "justify" })} aoClicar={() => cmd().setTextAlign("justify").run()}><IconTextJustify className="size-4" fill="currentColor" /></Botao>
          <select
            aria-label="Entrelinhas"
            className={cn(seletor, "w-20")}
            value={estilo.lineHeight ?? ""}
            onChange={(e) => (e.target.value ? cmd().setLineHeight(e.target.value).run() : cmd().unsetLineHeight().run())}
          >
            <option value="">1,5</option>
            {ENTRELINHAS.filter((l) => l !== "1.5").map((l) => <option key={l} value={l}>{l.replace(".", ",")}</option>)}
          </select>
          <Divisor />

          <Botao rotulo="Lista com marcadores" ativo={editor.isActive("bulletList")} aoClicar={() => cmd().toggleBulletList().run()}><IconListBullet className="size-4" fill="currentColor" /></Botao>
          <Botao rotulo="Lista numerada" ativo={editor.isActive("orderedList")} aoClicar={() => cmd().toggleOrderedList().run()}><IconListNumber className="size-4" fill="currentColor" /></Botao>
          <Botao rotulo="Citação longa (recuo de 4 cm)" ativo={editor.isActive("blockquote")} aoClicar={() => cmd().toggleBlockquote().run()}><IconQuoteOpening className="size-4" fill="currentColor" /></Botao>
          <Botao rotulo="Inserir tabela" aoClicar={() => cmd().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()}><IconTablecells className="size-4" fill="currentColor" /></Botao>
          {emTabela && (
            <>
              <button type="button" onMouseDown={(e) => e.preventDefault()} onClick={() => cmd().addRowAfter().run()} className="text-12 text-ink-muted hover:text-ink h-8 rounded-[8px] px-2">+ linha</button>
              <button type="button" onMouseDown={(e) => e.preventDefault()} onClick={() => cmd().addColumnAfter().run()} className="text-12 text-ink-muted hover:text-ink h-8 rounded-[8px] px-2">+ coluna</button>
              <button type="button" onMouseDown={(e) => e.preventDefault()} onClick={() => cmd().deleteTable().run()} className="text-12 text-status-vencido-ink h-8 rounded-[8px] px-2">Excluir tabela</button>
            </>
          )}
        </div>

        <div className="grid xl:grid-cols-[1fr_288px]">
          {/* Mesa de trabalho com a folha A4 */}
          <div className="bg-surface-muted max-h-[calc(100vh-18rem)] min-h-[520px] overflow-auto p-6">
            <div className="mx-auto w-max" style={{ zoom: zoom / 100 }}>
              <div
                ref={folha}
                className="folha-a4"
                style={{ padding: PADRAO_PAGINA.margens }}
              >
                <EditorContent editor={editor} />
              </div>
            </div>
          </div>

          {/* Painel lateral */}
          <aside className="border-border space-y-6 border-t p-4 xl:border-t-0 xl:border-l">
            <section className="space-y-2">
              <h3 className="text-13 text-ink font-semibold">Dados do processo</h3>
              <Select value={processoId} onChange={(e) => setProcessoId(e.target.value)} aria-label="Processo vinculado" className="text-13">
                <option value="">Escolha um processo…</option>
                {PROCESSOS_INICIAIS.map((p) => <option key={p.id} value={p.id}>{p.cliente}</option>)}
              </Select>
              {dadosProcesso.length > 0 ? (
                <ul className="space-y-1">
                  {dadosProcesso.map(([rotulo, valor]) => (
                    <li key={rotulo}>
                      <button
                        type="button"
                        onClick={() => editor.chain().focus().insertContent(valor).run()}
                        className="hover:bg-surface-muted w-full rounded-input px-2 py-1 text-left transition-colors"
                      >
                        <span className="text-11 text-ink-muted block">{rotulo} · inserir</span>
                        <span className="text-13 text-ink block truncate">{valor}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-12 text-ink-muted">Vincule um processo para inserir cliente, número e vara com um clique.</p>
              )}
            </section>

            <section className="space-y-2">
              <h3 className="text-13 text-ink font-semibold">Estrutura</h3>
              {titulos.length === 0 ? (
                <p className="text-12 text-ink-muted">Use os estilos Título e Seção para montar o índice.</p>
              ) : (
                <ul className="space-y-0.5">
                  {titulos.map((t, i) => (
                    <li key={`${t.pos}-${i}`}>
                      <button
                        type="button"
                        onClick={() => irPara(t.pos)}
                        style={{ paddingLeft: `${(t.nivel - 1) * 12 + 8}px` }}
                        className="text-12 text-ink-muted hover:bg-surface-muted hover:text-ink w-full truncate rounded-input py-1 pr-2 text-left transition-colors"
                      >
                        {t.texto || "Sem título"}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="space-y-1">
              <h3 className="text-13 text-ink font-semibold">Padrão de formatação</h3>
              <p className="text-12 text-ink-muted">{PADRAO_PAGINA.nome}</p>
              <p className="text-12 text-ink-muted">Margens 3 cm (superior e esquerda) e 2 cm (inferior e direita) · Times New Roman 12 · entrelinhas 1,5 · citações longas com recuo de 4 cm.</p>
            </section>
          </aside>
        </div>

        {/* Barra de status */}
        <div className="border-border text-12 text-ink-muted flex flex-wrap items-center gap-x-6 gap-y-2 border-t px-4 py-2 tabular-nums">
          <span>{paginas} {paginas === 1 ? "página" : "páginas"} (A4)</span>
          <span>{editor.storage.characterCount.words()} palavras</span>
          <span>{editor.storage.characterCount.characters()} caracteres</span>
          <div className="ml-auto flex items-center gap-1" role="group" aria-label="Zoom">
            {ZOOMS.map((z) => (
              <button key={z} type="button" aria-pressed={zoom === z} onClick={() => setZoom(z)} className={cn("h-6 rounded-[6px] px-2", zoom === z ? "bg-surface-muted text-ink" : "hover:text-ink")}>
                {z}%
              </button>
            ))}
          </div>
        </div>
      </div>

      <ModalRedatorIA
        open={iaAberta}
        onOpenChange={setIaAberta}
        processo={processo ?? null}
        aoInserir={(texto) => editor.chain().focus().insertContent(textoParaHtml(texto)).run()}
      />

      <style>{`
        .folha-a4 { width: 210mm; min-height: 297mm; background-color: #fff; color: #111; box-shadow: 0 1px 3px rgb(0 0 0 / .25), 0 12px 32px rgb(0 0 0 / .18);
          background-image: linear-gradient(to bottom, transparent calc(297mm - 1px), #cfcfcf calc(297mm - 1px), #cfcfcf 297mm);
          background-size: 100% 297mm; background-repeat: repeat-y; }
        .folha-a4 .ProseMirror { outline: none; min-height: 247mm; }
        .folha-a4 .ProseMirror p.is-editor-empty:first-child::before { content: attr(data-placeholder); color: #9a9a9a; float: left; height: 0; pointer-events: none; }
        .folha-a4 .ProseMirror ::selection { background: #b8d4ff; }
        ${ESTILO_DOCUMENTO}
        .folha-a4 .ProseMirror table { table-layout: fixed; }
        .folha-a4 .ProseMirror .selectedCell { background: #dbeafe; }
      `}</style>
    </div>
  );
}
