import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
  IconDocumentOnDocument,
  IconDocumentBadgePlus,
  IconArrowUpDocument,
  IconMagnifyingglass,
  IconTrash,
  IconCheckmarkCircleFill,
} from "symbols-react";
import { Badge, Button, EmptyState, Field, Input, Modal, Select, useToast } from "@/components/ui";
import { AREAS_DOC, MODELOS, modelosPorArea, preencherModelo } from "@/data/modelos";
import { PROCESSOS_INICIAIS } from "@/data/escritorio";
import { useDocumentos } from "@/lib/documentos";
import { cn } from "@/lib/cn";

const textoPuro = (html) => html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();

export function Documentos() {
  const { docs, criar, excluir } = useDocumentos();
  const navegar = useNavigate();
  const { toast } = useToast();
  const [busca, setBusca] = useState("");
  const [filtro, setFiltro] = useState("todas");
  const [novoAberto, setNovoAberto] = useState(false);
  const [paraExcluir, setParaExcluir] = useState(null);
  const arquivo = useRef(null);

  const filtrados = useMemo(() => {
    const termo = busca.toLowerCase();
    return docs
      .filter((d) => (filtro === "todas" || d.area === filtro) && (d.titulo.toLowerCase().includes(termo) || d.tipo.toLowerCase().includes(termo)))
      .sort((a, b) => b.atualizadoEm - a.atualizadoEm);
  }, [docs, busca, filtro]);

  async function importar(e) {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    const nome = f.name.replace(/\.[^.]+$/, "");
    try {
      let html;
      if (/\.docx$/i.test(f.name)) {
        const mammoth = await import("mammoth/mammoth.browser");
        const { value } = await mammoth.convertToHtml({ arrayBuffer: await f.arrayBuffer() });
        html = value;
      } else if (/\.(txt|html?)$/i.test(f.name)) {
        const texto = await f.text();
        html = /\.html?$/i.test(f.name) ? texto : texto.split(/\n{2,}/).map((p) => `<p>${p.replace(/&/g, "&amp;").replace(/</g, "&lt;")}</p>`).join("");
      } else {
        toast({ tipo: "info", titulo: "Formato não editável", descricao: "PDF não pode ser editado. Envie o arquivo em .docx, .txt ou .html." });
        return;
      }
      const doc = criar({ titulo: nome, area: "geral", tipo: "Documento importado", html: html || "<p></p>" });
      toast({ tipo: "sucesso", titulo: "Documento importado" });
      navegar(`/documentos/${doc.id}`);
    } catch {
      toast({ tipo: "erro", titulo: "Não foi possível ler o arquivo" });
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="font-heading text-24 font-bold tracking-tight text-ink">Documentos</h2>
          <p className="text-14 text-ink-muted">Redija, edite e exporte peças com modelos por área do direito.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <input ref={arquivo} type="file" accept=".docx,.txt,.html,.htm,.pdf" className="hidden" onChange={importar} />
          <Button variant="secondary" className="gap-2" onClick={() => arquivo.current?.click()}>
            <IconArrowUpDocument className="size-4" fill="currentColor" />
            Importar documento
          </Button>
          <Button variant="primary" className="gap-2" onClick={() => setNovoAberto(true)}>
            <IconDocumentBadgePlus className="size-4" fill="currentColor" />
            Novo documento
          </Button>
        </div>
      </div>

      <div className="bg-surface border-border flex flex-col gap-4 rounded-card border p-4 xl:flex-row xl:items-center">
        <div className="relative flex-1">
          <IconMagnifyingglass fill="currentColor" className="text-ink-muted pointer-events-none absolute top-1/2 left-4 size-4 -translate-y-1/2" />
          <Input placeholder="Buscar por título ou tipo de peça…" className="ps-10" value={busca} onChange={(e) => setBusca(e.target.value)} />
        </div>
        <div className="flex flex-wrap gap-2" role="group" aria-label="Filtrar por área">
          {[{ id: "todas", rotulo: "Todas" }, ...AREAS_DOC].map((a) => (
            <button
              key={a.id}
              type="button"
              aria-pressed={filtro === a.id}
              onClick={() => setFiltro(a.id)}
              className={cn("text-13 h-10 rounded-full border px-4 font-medium transition-colors", filtro === a.id ? "bg-primary text-primary-foreground border-transparent" : "border-border text-ink-muted hover:text-ink")}
            >
              {a.rotulo}
            </button>
          ))}
        </div>
      </div>

      {filtrados.length === 0 ? (
        <EmptyState
          icon={IconDocumentOnDocument}
          titulo="Nenhum documento encontrado"
          descricao={docs.length === 0 ? "Crie o primeiro documento a partir de um modelo ou importe um arquivo .docx." : "Nenhum documento corresponde à busca."}
          acao={<Button onClick={() => setNovoAberto(true)}>Novo documento</Button>}
        />
      ) : (
        <ul className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
          {filtrados.map((d) => {
            const area = AREAS_DOC.find((a) => a.id === d.area);
            return (
              <li key={d.id} className="group relative">
                <button
                  type="button"
                  onClick={() => navegar(`/documentos/${d.id}`)}
                  className="bg-surface border-border hover:border-primary/50 flex h-full w-full flex-col gap-4 rounded-card border p-6 text-left transition-colors"
                >
                  <div className="flex items-center gap-2">
                    {area && <Badge tone={area.tom}>{area.rotulo}</Badge>}
                    <span className="text-12 text-ink-muted truncate">{d.tipo}</span>
                  </div>
                  <p className="text-16 text-ink line-clamp-2 font-semibold">{d.titulo}</p>
                  <p className="text-13 text-ink-muted line-clamp-3 flex-1">{textoPuro(d.html).slice(0, 220) || "Documento vazio"}</p>
                  <p className="text-12 text-ink-muted">Editado {formatDistanceToNow(d.atualizadoEm, { locale: ptBR, addSuffix: true })}</p>
                </button>
                <button
                  type="button"
                  aria-label={`Excluir ${d.titulo}`}
                  onClick={() => setParaExcluir(d)}
                  className="text-ink-muted hover:text-status-vencido-ink hover:bg-surface-muted absolute top-4 right-4 flex size-8 items-center justify-center rounded-input opacity-0 transition focus-visible:opacity-100 group-hover:opacity-100"
                >
                  <IconTrash className="size-4" fill="currentColor" />
                </button>
              </li>
            );
          })}
        </ul>
      )}

      <ModalNovoDocumento
        open={novoAberto}
        onOpenChange={setNovoAberto}
        aoCriar={(dados) => {
          const doc = criar(dados);
          setNovoAberto(false);
          navegar(`/documentos/${doc.id}`);
        }}
      />

      <Modal
        open={!!paraExcluir}
        onOpenChange={(v) => !v && setParaExcluir(null)}
        titulo="Excluir documento?"
        descricao={paraExcluir ? `“${paraExcluir.titulo}” será removido deste navegador.` : undefined}
        footer={
          <>
            <Button variant="secondary" onClick={() => setParaExcluir(null)}>Cancelar</Button>
            <Button variant="danger" onClick={() => { excluir(paraExcluir.id); setParaExcluir(null); }}>Excluir</Button>
          </>
        }
      />
    </div>
  );
}

function ModalNovoDocumento({ open, onOpenChange, aoCriar }) {
  const [area, setArea] = useState("trabalhista");
  const [modeloId, setModeloId] = useState("reclamacao-trabalhista");
  const [processoId, setProcessoId] = useState("");
  const [titulo, setTitulo] = useState("");

  const modelos = [...modelosPorArea(area), ...(area === "geral" ? [] : [])];
  const modelo = MODELOS.find((m) => m.id === modeloId);
  const processo = PROCESSOS_INICIAIS.find((p) => String(p.id) === processoId);

  function escolherArea(id) {
    setArea(id);
    setModeloId(modelosPorArea(id)[0]?.id ?? "");
  }

  function criarDocumento(e) {
    e.preventDefault();
    if (!modelo) return;
    aoCriar({
      titulo: titulo.trim() || `${modelo.rotulo}${processo ? ` – ${processo.cliente}` : ""}`,
      area: modelo.area,
      tipo: modelo.rotulo,
      html: preencherModelo(modelo.html, processo ? { cliente: processo.cliente, numero: processo.numero, vara: processo.vara } : {}),
    });
    setTitulo("");
    setProcessoId("");
  }

  return (
    <Modal open={open} onOpenChange={onOpenChange} titulo="Novo documento" descricao="Escolha a área e o tipo de peça. O modelo já vem no padrão de formatação do escritório." className="max-w-2xl">
      <form onSubmit={criarDocumento} className="space-y-6">
        <div className="flex flex-wrap gap-2" role="group" aria-label="Área do direito">
          {AREAS_DOC.map((a) => (
            <button key={a.id} type="button" aria-pressed={area === a.id} onClick={() => escolherArea(a.id)}
              className={cn("text-13 h-10 rounded-full border px-4 font-medium transition-colors", area === a.id ? "bg-primary text-primary-foreground border-transparent" : "border-border text-ink-muted hover:text-ink")}>
              {a.rotulo}
            </button>
          ))}
        </div>

        <ul className="grid gap-2 sm:grid-cols-2" role="radiogroup" aria-label="Tipo de documento">
          {modelos.map((m) => {
            const ativo = m.id === modeloId;
            return (
              <li key={m.id}>
                <button type="button" role="radio" aria-checked={ativo} onClick={() => setModeloId(m.id)}
                  className={cn("flex h-full w-full items-start gap-3 rounded-input border p-4 text-left transition-colors", ativo ? "border-primary bg-primary-soft" : "border-border hover:bg-surface-muted")}>
                  <span className="min-w-0 flex-1">
                    <span className="text-14 text-ink block font-medium">{m.rotulo}</span>
                    <span className="text-12 text-ink-muted mt-1 block">{m.descricao}</span>
                  </span>
                  {ativo && <IconCheckmarkCircleFill className="text-primary mt-0.5 size-4 shrink-0" fill="currentColor" />}
                </button>
              </li>
            );
          })}
        </ul>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Processo (opcional)" id="nd-processo" hint="Preenche cliente e número do processo.">
            <Select id="nd-processo" value={processoId} onChange={(e) => setProcessoId(e.target.value)}>
              <option value="">Sem vínculo</option>
              {PROCESSOS_INICIAIS.map((p) => <option key={p.id} value={p.id}>{p.cliente}</option>)}
            </Select>
          </Field>
          <Field label="Título" id="nd-titulo">
            <Input id="nd-titulo" maxLength={120} value={titulo} onChange={(e) => setTitulo(e.target.value)} placeholder={modelo?.rotulo} />
          </Field>
        </div>

        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => onOpenChange(false)}>Cancelar</Button>
          <Button type="submit" disabled={!modelo}>Criar documento</Button>
        </div>
      </form>
    </Modal>
  );
}
