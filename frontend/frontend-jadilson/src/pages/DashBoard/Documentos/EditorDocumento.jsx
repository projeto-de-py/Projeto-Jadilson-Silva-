import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
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
  IconSquareAndArrowUp,
} from "symbols-react";
import { Button, Select, Badge, useToast } from "@/components/ui";
import { CaixaIA } from "@/components/ia/CaixaIA";
import { CartaoSugestao } from "@/components/ia/CartaoSugestao";
import { ModalAssinatura } from "@/components/financeiro/ModalAssinatura";
import { ModalCompararJuros } from "@/components/consultas/ModalCompararJuros";
import { SugestoesIA, TextoFantasma, adicionarBlocos, definirFantasma, posicaoDoBloco, posicaoDoBlocoSalvo, removerBloco } from "@/components/ia/extensoes";
import { completarTexto } from "@/lib/ia";
import { useSessao } from "@/context/sessao";
import { LogoIA } from "@/components/ia/LogoIA";
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

const seletor = "h-8 rounded-[8px] px-3 text-13";

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
  const { toast } = useToast();
  const { csrf } = useSessao();
  const [processoId, setProcessoId] = useState(doc.processoId ? String(doc.processoId) : "");
  const [sugestoes, setSugestoes] = useState([]);
  const [iaAberta, setIaAberta] = useState(false);
  const [assinaturaAberta, setAssinaturaAberta] = useState(false);
  const [jurosAberto, setJurosAberto] = useState(false);
  const [iaOcupada, setIaOcupada] = useState(false); // o autocompletar não conseguiu resposta da IA
  const [alvos, setAlvos] = useState({}); // id da sugestão -> elemento onde o cartão é desenhado
  const [autoCompletar, setAutoCompletar] = useState(() => {
    try {
      return localStorage.getItem("autocompletar-ia") !== "desligado";
    } catch {
      return true;
    }
  });
  const folha = useRef(null);
  const timer = useRef(null);

  const registrarAlvo = useCallback((id, el) => {
    setAlvos((atual) => {
      if (!el) {
        if (!(id in atual)) return atual;
        const resto = { ...atual };
        delete resto[id];
        return resto;
      }
      return atual[id] === el ? atual : { ...atual, [id]: el };
    });
  }, []);

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
      SugestoesIA.configure({ aoRegistrar: registrarAlvo }),
      TextoFantasma,
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

  // Autocompletar: ao parar de digitar no fim de um parágrafo, pede a continuação.
  useEffect(() => {
    if (!editor || !autoCompletar) return undefined;
    let temporizador;
    let pedido = 0;
    let controle = null;
    const aoEditar = () => {
      clearTimeout(temporizador);
      controle?.abort(); // qualquer tecla cancela o pedido anterior
      pedido += 1;
      const meu = pedido;
      temporizador = setTimeout(async () => {
        const { state } = editor;
        const { $from, empty } = state.selection;
        if (!empty || !$from.parent.isTextblock || $from.parentOffset !== $from.parent.content.size) return;
        const textoAntes = $from.parent.textContent;
        if (textoAntes.trim().length < 12) return;
        const docNoPedido = state.doc;
        controle = new AbortController();
        let continuacao = null;
        try {
          continuacao = await completarTexto({ textoAntes, area: doc.area, csrf, sinal: controle.signal });
          if (meu === pedido) setIaOcupada(false);
        } catch {
          if (meu === pedido) setIaOcupada(true);
        }
        // Só mostra se nada mudou enquanto a resposta chegava e o cursor ainda está no editor.
        if (continuacao && meu === pedido && editor.state.doc === docNoPedido && document.activeElement === editor.view.dom) {
          definirFantasma(editor, { texto: continuacao, pos: editor.state.selection.to });
        }
      }, 800);
    };
    editor.on("update", aoEditar);
    return () => {
      editor.off("update", aoEditar);
      clearTimeout(temporizador);
      controle?.abort();
      pedido += 1;
    };
  }, [editor, autoCompletar, doc.area, csrf]);

  function alternarAutoCompletar() {
    const novo = !autoCompletar;
    setAutoCompletar(novo);
    if (!novo && editor) definirFantasma(editor, null);
    try {
      localStorage.setItem("autocompletar-ia", novo ? "ligado" : "desligado");
    } catch {
      /* sem persistência */
    }
  }

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

  function receberSugestoes(resultado) {
    const lista = resultado.sugestoes;
    if (resultado.avisos?.length) {
      toast({ tipo: "info", titulo: "Atenção", descricao: resultado.avisos.join(" ") });
    }
    if (lista.length === 0) {
      toast({ tipo: "info", titulo: "Nenhuma sugestão", descricao: "A IA não encontrou nada a acrescentar neste texto." });
      return;
    }
    const pos = posicaoDoBloco(editor.state);
    setSugestoes((atual) => [...atual, ...lista]);
    adicionarBlocos(editor, lista.map((s) => ({ id: s.id, pos })));
    toast({ tipo: "sucesso", titulo: `${lista.length} ${lista.length === 1 ? "sugestão pronta" : "sugestões prontas"}`, descricao: "Estão no texto, logo abaixo do parágrafo." });
  }

  function ignorarSugestao(sug) {
    removerBloco(editor, sug.id);
    setSugestoes((atual) => atual.filter((x) => x.id !== sug.id));
  }

  function adicionarSugestao(sug) {
    const pos = posicaoDoBlocoSalvo(editor, sug.id);
    removerBloco(editor, sug.id);
    setSugestoes((atual) => atual.filter((x) => x.id !== sug.id));
    if (pos !== null) editor.chain().focus().insertContentAt(pos, sug.html).run();
  }

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
          <LogoIA tamanho={20} />
          Perguntar à IA
          {sugestoes.length > 0 && <span className="bg-primary text-primary-foreground text-11 flex size-5 items-center justify-center rounded-full tabular-nums">{sugestoes.length}</span>}
        </Button>
        <Button variant="secondary" className="gap-2" onClick={() => setAssinaturaAberta(true)}>
          <IconSquareAndArrowUp className="size-4" fill="currentColor" />
          Enviar para assinatura
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

          <Select
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
          </Select>
          <Select
            aria-label="Fonte"
            className={cn(seletor, "w-40")}
            value={fonteAtual}
            onChange={(e) => (e.target.value ? cmd().setFontFamily(e.target.value).run() : cmd().unsetFontFamily().run())}
          >
            <option value="">Padrão (Times New Roman)</option>
            {FONTES.map((f) => <option key={f.rotulo} value={f.valor}>{f.rotulo}</option>)}
          </Select>
          <Select
            aria-label="Tamanho da fonte"
            className={cn(seletor, "w-16")}
            value={tamanhoAtual}
            onChange={(e) => (e.target.value ? cmd().setFontSize(`${e.target.value}pt`).run() : cmd().unsetFontSize().run())}
          >
            <option value="">12</option>
            {TAMANHOS.filter((t) => t !== 12).map((t) => <option key={t} value={t}>{t}</option>)}
          </Select>
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
          <Select
            aria-label="Entrelinhas"
            className={cn(seletor, "w-20")}
            value={estilo.lineHeight ?? ""}
            onChange={(e) => (e.target.value ? cmd().setLineHeight(e.target.value).run() : cmd().unsetLineHeight().run())}
          >
            <option value="">1,5</option>
            {ENTRELINHAS.filter((l) => l !== "1.5").map((l) => <option key={l} value={l}>{l.replace(".", ",")}</option>)}
          </Select>
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
              <div ref={folha} className="folha-a4" style={{ padding: PADRAO_PAGINA.margens }}>
                <EditorContent editor={editor} />
              </div>
            </div>
            {sugestoes.map((s) => (alvos[s.id] ? createPortal(<CartaoSugestao key={s.id} sugestao={s} aoAdicionar={adicionarSugestao} aoIgnorar={ignorarSugestao} />, alvos[s.id]) : null))}
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

            <section className="space-y-2">
              <h3 className="text-13 text-ink font-semibold">Ferramentas</h3>
              <Button variant="secondary" className="w-full" onClick={() => setJurosAberto(true)}>
                Comparar juros (Banco Central)
              </Button>
              <p className="text-12 text-ink-muted">Compara a taxa do contrato com a média de mercado do mês e insere o parágrafo na peça.</p>
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
          <button type="button" role="switch" aria-checked={autoCompletar} onClick={alternarAutoCompletar} className="hover:text-ink flex items-center gap-2 transition-colors">
            <span className={cn("size-2 rounded-full", autoCompletar ? "bg-status-ok" : "bg-ink-muted")} />
            Autocompletar da IA {autoCompletar ? "ligado" : "desligado"}
          </button>
          {autoCompletar && iaOcupada && (
            <span role="status" className="text-status-atencao-ink">
              IA sem resposta agora (limite do modelo gratuito). Tente de novo em instantes.
            </span>
          )}
          <div className="ml-auto flex items-center gap-1" role="group" aria-label="Zoom">
            {ZOOMS.map((z) => (
              <button key={z} type="button" aria-pressed={zoom === z} onClick={() => setZoom(z)} className={cn("h-6 rounded-[6px] px-2", zoom === z ? "bg-surface-muted text-ink" : "hover:text-ink")}>
                {z}%
              </button>
            ))}
          </div>
        </div>
      </div>

      <ModalCompararJuros open={jurosAberto} onOpenChange={setJurosAberto} aoInserir={(texto) => editor.chain().focus().insertContent(`<p>${texto.replace(/&/g, "&amp;").replace(/</g, "&lt;")}</p>`).run()} />
      <ModalAssinatura open={assinaturaAberta} onOpenChange={setAssinaturaAberta} tituloInicial={titulo} obterHtml={() => editor.getHTML()} />

      <CaixaIA
        open={iaAberta}
        onOpenChange={setIaAberta}
        processoId={processoId}
        aoMudarProcesso={setProcessoId}
        textoDocumento={editor.getText()}
        area={doc.area}
        tipoPeca={doc.tipo}
        aoSugerir={receberSugestoes}
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
        .folha-a4 .ghost-ia { color: #8d8d8d; }
        .folha-a4 .ghost-ia kbd { margin-left: 6px; padding: 0 5px; border: 1px solid #cfcfcf; border-radius: 5px; font: 11px/16px system-ui, sans-serif; color: #6b6b6b; background: #f4f4f4; vertical-align: 1px; }
        .folha-a4 .sug-bloco { margin: 10px 0 14px; text-indent: 0; text-align: left; font-family: system-ui, -apple-system, "Segoe UI", sans-serif; font-size: 13px; line-height: 1.45; }
        .folha-a4 .sug-cartao { background: #f3faf5; border: 1px solid #bfe3c9; border-radius: 16px; padding: 16px; color: #14391f; }
        .folha-a4 .sug-topo { display: flex; align-items: center; gap: 8px; font-size: 12px; color: #4b6b55; font-weight: 500; }
        .folha-a4 .sug-titulo { margin: 12px 0 4px; font-size: 14px; font-weight: 600; color: #0f2c18; text-transform: none; text-align: left; }
        .folha-a4 .sug-previa { margin: 0; color: #4b6b55; text-indent: 0; }
        .folha-a4 .sug-conteudo { margin-top: 12px; padding: 12px; background: #fff; border: 1px solid #cfe9d6; border-radius: 12px; color: #111; max-height: 240px; overflow: auto; }
        .folha-a4 .sug-conteudo p, .folha-a4 .sug-conteudo h2 { text-indent: 0; margin: 0 0 8px; font-size: 13px; text-align: left; text-transform: none; }
        .folha-a4 .sug-conteudo h2 { font-weight: 600; }
        .folha-a4 .sug-rotulo { color: #2f7a47 !important; font-size: 11px !important; font-weight: 600; }
        .folha-a4 .sug-acoes { display: flex; align-items: center; gap: 8px; margin-top: 16px; }
        .folha-a4 .sug-botao { height: 36px; padding: 0 16px; border-radius: 10px; border: 1px solid #b9d9c2; background: #fff; color: #14391f; font-size: 13px; font-weight: 500; cursor: pointer; }
        .folha-a4 .sug-botao:hover { background: #eef7f0; }
        .folha-a4 .sug-primario { background: #111; border-color: #111; color: #fff; }
        .folha-a4 .sug-primario:hover { background: #2a2a2a; }
        .folha-a4 .sug-botao:disabled { opacity: .4; cursor: default; }
        .folha-a4 .sug-selo { margin-left: auto; padding: 2px 10px; border-radius: 999px; font-size: 11px; font-weight: 600; background: #e4f2e8; color: #2f6b43; }
        .folha-a4 .sug-selo.sug-atencao { background: #fdf0d2; color: #8a5a00; }
        .folha-a4 .sug-selo.sug-critica { background: #fbdcdc; color: #9b1c1c; }
        .folha-a4 .sug-trecho { margin: 10px 0 0; font-size: 12px; color: #4b6b55; font-style: italic; text-indent: 0; }
        .folha-a4 .sug-motivo { margin: 6px 0 0; font-size: 13px; color: #14391f; text-indent: 0; }
        .folha-a4 .sug-fonte { margin: 10px 0 0; font-size: 12px; font-weight: 600; color: #8a5a00; text-indent: 0; }
        .folha-a4 .sug-link { margin-left: auto; background: none; border: 0; color: #4b6b55; font-size: 12px; cursor: pointer; text-decoration: underline; text-underline-offset: 3px; }
      `}</style>
    </div>
  );
}
