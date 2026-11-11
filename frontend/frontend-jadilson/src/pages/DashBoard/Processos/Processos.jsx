import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import {
  IconFolderBadgePlus,
  IconMagnifyingglass,
  IconClockBadgeCheckmark,
  IconArrowDownDocument,
  IconSquareAndPencil,
  IconListBullet,
  IconRectangle3Group,
  IconPerson,
  IconScalemass,
} from "symbols-react";
import { Card, Button, Badge, Input, Select, Drawer, HairlineEmptyState } from "@/components/ui";
import { ModalCadastrarProcesso } from "@/components/modais/ModalCadastrarProcesso";
import { MODELOS, preencherModelo } from "@/data/modelos";
import { useDocumentos } from "@/lib/documentos";
import { exportarProcessoPdf } from "@/lib/exportarPdf";
import { PainelDataJud } from "@/components/consultas/PainelDataJud";
import { useArea } from "@/context/area-context";
import { useCarteira } from "@/data/escritorio";
import { cn } from "@/lib/cn";

const ETAPAS = [
  { id: "Petição inicial", tom: "neutral", ponto: "bg-ink-muted" },
  { id: "Instrução", tom: "primary", ponto: "bg-primary" },
  { id: "Sentença", tom: "atencao", ponto: "bg-status-atencao" },
  { id: "Recursal", tom: "vencido", ponto: "bg-status-vencido" },
  { id: "Concluído", tom: "ok", ponto: "bg-status-ok" },
];
const TOM = Object.fromEntries(ETAPAS.map((e) => [e.id, e.tom]));

const MARCOS = {
  "Petição inicial": ["Petição inicial protocolada", "Distribuição ao juízo"],
  "Instrução": ["Citação da parte ré", "Contestação juntada", "Designada audiência de instrução"],
  "Sentença": ["Audiência realizada", "Alegações finais", "Autos conclusos para sentença"],
  "Recursal": ["Sentença publicada", "Recurso interposto", "Contrarrazões apresentadas"],
  "Concluído": ["Trânsito em julgado", "Arquivamento"],
};
const ORDEM = ETAPAS.map((e) => e.id);

function montarLinhaDoTempo(proc) {
  const idx = Math.max(0, ORDEM.indexOf(proc.status));
  const eventos = [];
  for (let i = 0; i <= idx; i += 1) {
    MARCOS[ORDEM[i]].forEach((titulo) => eventos.push({ titulo, etapa: ORDEM[i], atual: false }));
  }
  eventos[eventos.length - 1].atual = true;
  return eventos.reverse();
}

function normalizarTexto(texto = "") {
  return String(texto)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

export function Processos() {
  const { area } = useArea();
  const { processos, setProcessos } = useCarteira();
  const [modalAberto, setModalAberto] = useState(false);
  const navegar = useNavigate();
  const { docs, criar } = useDocumentos();
  const [processoLinha, setProcessoLinha] = useState(null);
  const [busca, setBusca] = useState("");
  const [filtroStatus, setFiltroStatus] = useState("TODOS");
  const [visao, setVisao] = useState("lista");

  const processosFiltrados = useMemo(() => {
    const termo = busca.toLowerCase();
    return processos.filter((p) => {
      const matchArea =
        !area ||
        area === "todas" ||
        normalizarTexto(p.area).includes(normalizarTexto(area)) ||
        normalizarTexto(p.tipoAcao).includes(normalizarTexto(area));
      const matchStatus = filtroStatus === "TODOS" || p.status === filtroStatus;
      const matchBusca =
        p.numero.toLowerCase().includes(termo) ||
        p.cliente.toLowerCase().includes(termo) ||
        p.tipoAcao.toLowerCase().includes(termo) ||
        p.vara.toLowerCase().includes(termo);
      return matchArea && matchStatus && matchBusca;
    });
  }, [processos, area, busca, filtroStatus]);

  function editarDocumento(proc) {
    const existente = docs.find((d) => d.processoId === proc.id || d.html.includes(proc.numero));
    if (existente) {
      navegar(`/documentos/${existente.id}`);
      return;
    }
    const areaDoc = proc.tipoAcao.toLowerCase();
    const idModelo = areaDoc.startsWith("bancário")
      ? "revisional-contrato"
      : areaDoc.startsWith("previdenciário")
        ? "aposentadoria"
        : areaDoc.startsWith("trabalhista")
          ? "reclamacao-trabalhista"
          : "em-branco";
    const modelo = MODELOS.find((m) => m.id === idModelo);
    const novo = criar({
      processoId: proc.id,
      titulo: `${modelo.rotulo} – ${proc.cliente}`,
      area: modelo.area,
      tipo: modelo.rotulo,
      html: preencherModelo(modelo.html, { cliente: proc.cliente, numero: proc.numero, vara: proc.vara }),
    });
    navegar(`/documentos/${novo.id}`);
  }

  const acoes = (proc) => (
    <div className="flex flex-wrap items-center gap-2">
      <Button variant="secondary" className="h-8 gap-2 px-4 text-12" onClick={() => setProcessoLinha(proc)}>
        <IconClockBadgeCheckmark className="size-3.5" fill="currentColor" />
        Andamentos
      </Button>
      <Button variant="ghost" className="h-8 gap-2 px-4 text-12" onClick={() => exportarProcessoPdf(proc)}>
        <IconArrowDownDocument className="size-3.5" fill="currentColor" />
        PDF
      </Button>
      <Button variant="ghost" className="h-8 gap-2 px-4 text-12 text-accent hover:text-accent-hover" onClick={() => editarDocumento(proc)}>
        <IconSquareAndPencil className="size-3.5" fill="currentColor" />
        Editar documento
      </Button>
    </div>
  );

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-heading text-24 font-bold tracking-tight text-ink">Gestão de Processos</h2>
          <p className="text-14 text-ink-muted">
            {processosFiltrados.length} {processosFiltrados.length === 1 ? "processo" : "processos"} · acompanhe por lista ou pelo funil de etapas.
          </p>
        </div>
        <Button variant="primary" onClick={() => setModalAberto(true)} className="shrink-0 gap-2">
          <IconFolderBadgePlus className="size-4" fill="currentColor" />
          Novo Processo
        </Button>
      </div>

      {/* Filtros + alternância de visão */}
      <div className="bg-surface border-border flex flex-col gap-4 rounded-card border p-4 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <IconMagnifyingglass
            fill="currentColor"
            className="text-ink-muted pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2"
          />
          <Input
            placeholder="Buscar por número CNJ, cliente, tipo de ação ou vara..."
            className="ps-9"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
          />
        </div>
        {visao === "lista" && (
          <div className="sm:w-52">
            <Select value={filtroStatus} onChange={(e) => setFiltroStatus(e.target.value)} className="h-10 text-14">
              <option value="TODOS">Todos os estágios</option>
              {ETAPAS.map((e) => (
                <option key={e.id} value={e.id}>{e.id}</option>
              ))}
            </Select>
          </div>
        )}
        <div role="group" aria-label="Modo de visualização" className="bg-surface-muted border-border flex rounded-input border p-0.5">
          {[
            { id: "lista", rotulo: "Lista", icone: IconListBullet },
            { id: "funil", rotulo: "Funil", icone: IconRectangle3Group },
          ].map((v) => (
            <button
              key={v.id}
              type="button"
              aria-pressed={visao === v.id}
              onClick={() => setVisao(v.id)}
              className={cn(
                "inline-flex h-10 items-center gap-2 rounded-input px-4 text-13 font-medium transition-colors",
                visao === v.id ? "bg-primary text-primary-foreground" : "text-ink-muted hover:text-ink",
              )}
            >
              <v.icone className="size-3.5" fill="currentColor" />
              {v.rotulo}
            </button>
          ))}
        </div>
      </div>

      {processosFiltrados.length === 0 ? (
        <HairlineEmptyState
          titulo="Nenhum processo encontrado"
          descricao={
            busca
              ? "Nenhum processo corresponde aos termos pesquisados."
              : "Nenhum processo cadastrado no banco de dados. Adicione o primeiro processo para começar."
          }
          acao={
            <Button variant="primary" onClick={() => setModalAberto(true)} className="gap-2">
              <IconFolderBadgePlus className="size-4" fill="currentColor" />
              Novo Processo
            </Button>
          }
        />
      ) : visao === "lista" ? (
        <div className="grid gap-4">
          {processosFiltrados.map((proc, i) => (
            <motion.div
              key={proc.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: Math.min(i, 8) * 0.04, duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            >
              <Card className="hover:border-primary/40 p-6 transition-colors">
                <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
                  <div className="min-w-0 flex-1 space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-heading text-16 font-semibold tabular-nums text-ink">{proc.numero}</span>
                      <Badge tone={TOM[proc.status] || "neutral"}>{proc.status}</Badge>
                      <span className="border-border bg-surface-muted text-ink-muted rounded-badge border px-2 py-0.5 text-12 font-medium">
                        {proc.tipoAcao}
                      </span>
                    </div>
                    <p className="text-14 text-ink flex items-center gap-2 font-medium">
                      <IconPerson className="size-3.5 text-accent" fill="currentColor" />
                      {proc.cliente}
                    </p>
                    <p className="text-13 text-ink-muted truncate">
                      {proc.vara} · {proc.valorCausa}
                    </p>
                    {proc.descricao && (
                      <p className="text-13 text-ink-muted/80 line-clamp-2">{proc.descricao}</p>
                    )}
                  </div>
                  <div className="border-border/60 shrink-0 border-t pt-4 lg:border-t-0 lg:pt-0">{acoes(proc)}</div>
                </div>
              </Card>
            </motion.div>
          ))}
        </div>
      ) : (
        <div className="-mx-1 overflow-x-auto pb-2">
          <div className="flex min-w-max gap-4 px-1">
            {ETAPAS.map((etapa) => {
              const coluna = processosFiltrados.filter((p) => p.status === etapa.id);
              return (
                <section key={etapa.id} className="bg-surface/60 border-border w-72 shrink-0 rounded-card border p-4">
                  <header className="flex items-center justify-between px-1 pb-4">
                    <h3 className="text-13 text-ink flex items-center gap-2 font-semibold">
                      <span className={cn("size-2 rounded-full", etapa.ponto)} />
                      {etapa.id}
                    </h3>
                    <span className="bg-surface-muted text-ink-muted rounded-badge px-2 py-0.5 text-11 tabular-nums">{coluna.length}</span>
                  </header>
                  <div className="space-y-2">
                    {coluna.length === 0 && (
                      <p className="border-border text-ink-muted rounded-input border border-dashed px-4 py-6 text-center text-12">
                        Nenhum processo
                      </p>
                    )}
                    {coluna.map((proc) => (
                      <motion.button
                        key={proc.id}
                        layout
                        type="button"
                        whileHover={{ y: -2 }}
                        onClick={() => setProcessoLinha(proc)}
                        className="bg-surface border-border hover:border-primary/50 block w-full rounded-input border p-4 text-left transition-colors"
                      >
                        <p className="text-12 text-ink-muted tabular-nums">{proc.numero}</p>
                        <p className="text-14 text-ink mt-1 font-semibold leading-snug">{proc.cliente}</p>
                        <p className="text-12 text-ink-muted mt-1 truncate">{proc.tipoAcao}</p>
                        <p className="text-12 text-accent mt-2 flex items-center gap-2 font-medium">
                          <IconScalemass className="size-3" fill="currentColor" />
                          {proc.valorCausa}
                        </p>
                      </motion.button>
                    ))}
                  </div>
                </section>
              );
            })}
          </div>
        </div>
      )}

      <Drawer
        open={!!processoLinha}
        onOpenChange={(v) => !v && setProcessoLinha(null)}
        titulo="Andamentos"
        descricao={processoLinha ? `${processoLinha.numero} · ${processoLinha.cliente}` : undefined}
        footer={processoLinha && acoes(processoLinha)}
      >
        {processoLinha && (
          <div className="space-y-8">
            <PainelDataJud key={processoLinha.id} numeroInicial={processoLinha.numero} />
            <ol className="relative space-y-6 border-l border-border pl-6">
              {montarLinhaDoTempo(processoLinha).map((ev, i) => (
                <li key={`${ev.titulo}-${i}`} className="relative">
                  <span
                    className={cn(
                      "absolute top-1 -left-[31px] size-3 rounded-full border-2 border-surface",
                      ev.atual ? "bg-primary ring-4 ring-primary/25" : "bg-border",
                    )}
                  />
                  <p className={cn("text-14 font-medium", ev.atual ? "text-ink" : "text-ink-muted")}>{ev.titulo}</p>
                  <div className="mt-1 flex items-center gap-2">
                    <Badge tone={TOM[ev.etapa]}>{ev.etapa}</Badge>
                    {ev.atual && <span className="text-11 text-primary font-semibold">Atual</span>}
                  </div>
                </li>
              ))}
            </ol>
          </div>
        )}
      </Drawer>

      <ModalCadastrarProcesso
        open={modalAberto}
        onOpenChange={setModalAberto}
        onProcessoSalvo={(novo) => setProcessos((prev) => [novo, ...prev])}
      />
    </div>
  );
}
