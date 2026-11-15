import { useState, useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
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
  IconTrash,
  IconClock,
  IconPlus,
} from "symbols-react";
import { Card, Button, Badge, Input, Dropdown, Drawer, HairlineEmptyState, Modal, useToast } from "@/components/ui";
import { ModalCadastrarProcesso } from "@/components/modais/ModalCadastrarProcesso";
import { MODELOS, preencherModelo } from "@/data/modelos";
import { useDocumentos } from "@/lib/documentos";
import { exportarProcessoPdf } from "@/lib/exportarPdf";
import { PainelDataJud } from "@/components/consultas/PainelDataJud";
import { useCarteira } from "@/data/escritorio";
import { classificar } from "@/lib/prazos";
import { useSessao } from "@/context/sessao";
import { apiJson } from "@/lib/api";
import { notificarAtualizacaoDados } from "@/data/escritorio";
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

export function Processos() {
  const { processos, prazos, setProcessos } = useCarteira();
  const [modalAberto, setModalAberto] = useState(false);
  const navegar = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { docs, criar } = useDocumentos();
  const [processoSelecionado, setProcessoSelecionado] = useState(null);
  const [paraRemover, setParaRemover] = useState(null);
  const [removendo, setRemovendo] = useState(false);
  const [busca, setBusca] = useState(() => searchParams.get("busca") || "");
  const [filtroStatus, setFiltroStatus] = useState("TODOS");
  const [visao, setVisao] = useState("lista");
  const { csrf } = useSessao();
  const { toast } = useToast();

  const idUrl = searchParams.get("id");
  const processoLinha = useMemo(
    () => processoSelecionado ?? (idUrl ? processos.find((p) => String(p.id) === idUrl) ?? null : null),
    [processoSelecionado, idUrl, processos],
  );

  function setProcessoLinha(proc) {
    setProcessoSelecionado(proc);
    if (!proc && searchParams.has("id")) {
      const next = new URLSearchParams(searchParams);
      next.delete("id");
      setSearchParams(next, { replace: true });
    }
  }

  const processosFiltrados = useMemo(() => {
    const termo = busca.toLowerCase();
    return processos.filter((p) => {
      const matchStatus = filtroStatus === "TODOS" || p.status === filtroStatus;
      const matchBusca =
        p.numero.toLowerCase().includes(termo) ||
        p.cliente.toLowerCase().includes(termo) ||
        p.tipoAcao.toLowerCase().includes(termo) ||
        p.vara.toLowerCase().includes(termo);
      return matchStatus && matchBusca;
    });
  }, [processos, busca, filtroStatus]);

  const prazosDoProcesso = useMemo(() => {
    if (!processoLinha) return [];
    return prazos
      .filter((p) => p.casoId === processoLinha.id || p.processo === processoLinha.numero)
      .sort((a, b) => a.diasRestantes - b.diasRestantes);
  }, [prazos, processoLinha]);

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

  async function confirmarRemocao() {
    if (!paraRemover) return;
    setRemovendo(true);
    try {
      await apiJson(`casos/${paraRemover.id}/arquivar`, {
        method: "POST",
        csrf,
      });

      setProcessos((prev) => prev.filter((p) => p.id !== paraRemover.id));
      if (processoLinha?.id === paraRemover.id) {
        setProcessoLinha(null);
      }
      notificarAtualizacaoDados();

      toast({
        tipo: "sucesso",
        titulo: "Processo arquivado",
        descricao: `O processo ${paraRemover.numero} foi removido da listagem ativa.`,
      });
      setParaRemover(null);
    } catch (error) {
      toast({
        tipo: "erro",
        titulo: "Não foi possível remover o processo",
        descricao: error.message || "Tente novamente em instantes.",
      });
    } finally {
      setRemovendo(false);
    }
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
      <Button variant="ghost" className="h-8 gap-2 px-4 text-12 text-status-vencido-ink hover:text-status-vencido" onClick={() => setParaRemover(proc)}>
        <IconTrash className="size-3.5" fill="currentColor" />
        Remover
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
            <Dropdown
              aria-label="Filtrar por estágio"
              value={filtroStatus}
              onChange={setFiltroStatus}
              options={[
                { value: "TODOS", label: "Todos os estágios" },
                ...ETAPAS.map((e) => ({ value: e.id, label: e.id })),
              ]}
            />
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
        titulo="Detalhes do processo"
        descricao={processoLinha ? `${processoLinha.numero} · ${processoLinha.cliente}` : undefined}
        footer={processoLinha && acoes(processoLinha)}
      >
        {processoLinha && (
          <div className="space-y-8">
            <div className="bg-surface-muted/50 border-border space-y-2.5 rounded-card border p-4 text-13">
              <div className="flex items-center justify-between gap-2">
                <span className="text-ink-muted">Cliente</span>
                <button
                  type="button"
                  onClick={() => {
                    const nome = processoLinha.cliente;
                    setProcessoLinha(null);
                    navegar(`/clientes?busca=${encodeURIComponent(nome)}&cliente=${encodeURIComponent(nome)}`);
                  }}
                  className="text-primary hover:underline font-medium"
                >
                  {processoLinha.cliente}
                </button>
              </div>
              <div className="flex items-center justify-between gap-2">
                <span className="text-ink-muted">Vara / Foro</span>
                <span className="text-ink text-right font-medium">{processoLinha.vara}</span>
              </div>
              <div className="flex items-center justify-between gap-2">
                <span className="text-ink-muted">Valor da causa</span>
                <span className="text-ink font-medium tabular-nums">{processoLinha.valorCausa}</span>
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between gap-2">
                <h3 className="text-14 font-semibold text-ink flex items-center gap-2">
                  <IconClock className="size-4 text-primary" fill="currentColor" />
                  Prazos vinculados ({prazosDoProcesso.length})
                </h3>
                <Button
                  size="sm"
                  variant="secondary"
                  className="gap-1.5"
                  onClick={() => {
                    const id = processoLinha.id;
                    setProcessoLinha(null);
                    navegar(`/prazos?novo=1&processo=${id}`);
                  }}
                >
                  <IconPlus className="size-3.5" fill="currentColor" />
                  Novo prazo
                </Button>
              </div>
              {prazosDoProcesso.length === 0 ? (
                <p className="border-border text-ink-muted rounded-input border border-dashed px-4 py-3 text-12">
                  Nenhum prazo vinculado a este processo.
                </p>
              ) : (
                <ul className="space-y-2">
                  {prazosDoProcesso.map((prazo) => {
                    const sit = classificar(prazo.diasRestantes);
                    return (
                      <li
                        key={prazo.id}
                        className="border-border bg-surface-muted/40 flex items-center justify-between gap-3 rounded-input border px-3.5 py-2.5"
                      >
                        <div className="min-w-0">
                          <p className={cn("text-13 font-medium text-ink truncate", prazo.cumprido && "line-through opacity-60")}>
                            {prazo.titulo}
                          </p>
                          <p className="text-11 text-ink-muted">{prazo.tipo}</p>
                        </div>
                        <Badge tone={prazo.cumprido ? "cumprido" : sit.tom} className="shrink-0">
                          {prazo.cumprido ? "Cumprido" : sit.rotulo}
                        </Badge>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>

            <PainelDataJud key={processoLinha.id} numeroInicial={processoLinha.numero} />
            <ol className="relative space-y-6 border-l border-border pl-6">
              {montarLinhaDoTempo(processoLinha).map((ev, i) => (
                <li key={`${ev.titulo}-${i}`} className="relative">
                  <span
                    className={cn(
                      "absolute top-1 -left-7.75 size-3 rounded-full border-2 border-surface",
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

      {/* Modal de Confirmação de Remoção (Soft Delete / Arquivamento) */}
      <Modal
        open={!!paraRemover}
        onOpenChange={(aberto) => !aberto && !removendo && setParaRemover(null)}
        titulo="Remover processo?"
        descricao={
          paraRemover
            ? `Tem certeza de que deseja remover o processo "${paraRemover.numero}" (${paraRemover.cliente})? Ele será arquivado e sairá da listagem ativa.`
            : undefined
        }
        footer={
          <>
            <Button
              variant="secondary"
              type="button"
              onClick={() => setParaRemover(null)}
              disabled={removendo}
            >
              Cancelar
            </Button>
            <Button
              variant="danger"
              type="button"
              loading={removendo}
              onClick={confirmarRemocao}
              className="gap-2"
            >
              <IconTrash className="size-4" fill="currentColor" />
              Remover processo
            </Button>
          </>
        }
      />
    </div>
  );
}
