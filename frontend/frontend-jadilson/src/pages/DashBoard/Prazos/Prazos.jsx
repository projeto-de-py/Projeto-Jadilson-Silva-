import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import {
  IconClock,
  IconMagnifyingglass,
  IconExclamationmarkTriangle,
  IconCalendar,
  IconHammer,
  IconDocument,
  IconCheckmarkCircle,
  IconCheckmarkCircleFill,
  IconFunction,
  IconFlameFill,
} from "symbols-react";
import { Card, Badge, Button, Input, Select, EmptyState } from "@/components/ui";
import { ModalCalculadoraPrazos } from "@/components/modais/ModalCalculadoraPrazos";
import { PRAZOS } from "@/data/escritorio";
import { classificar, nivelRisco, pontuarRisco } from "@/lib/prazos";
import { cn } from "@/lib/cn";

const BARRA_RISCO = {
  vencido: "bg-status-vencido",
  hoje: "bg-status-hoje",
  atencao: "bg-status-atencao",
  ok: "bg-status-ok",
};

function formatarData(iso) {
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const GRUPOS = [
  { id: "vencidos", titulo: "Vencidos", descricao: "Exigem atenção imediata", icone: IconExclamationmarkTriangle, cor: "text-status-vencido", barra: "bg-status-vencido" },
  { id: "hoje", titulo: "Vencem hoje", descricao: "Prioridade máxima do dia", icone: IconClock, cor: "text-status-hoje-ink", barra: "bg-status-hoje" },
  { id: "proximos", titulo: "Próximos dias", descricao: "Planeje-se com antecedência", icone: IconCalendar, cor: "text-primary", barra: "bg-primary" },
];

export function Prazos() {
  const [busca, setBusca] = useState("");
  const [filtroArea, setFiltroArea] = useState("TODAS");
  const [cumpridos, setCumpridos] = useState(() => new Set());
  const [calcAberta, setCalcAberta] = useState(false);

  const alternar = (id) =>
    setCumpridos((atual) => {
      const novo = new Set(atual);
      if (novo.has(id)) novo.delete(id);
      else novo.add(id);
      return novo;
    });

  const prazosProcessados = useMemo(() => {
    const termo = busca.toLowerCase();
    return PRAZOS.map((p) => ({ ...p, ...classificar(p.diasRestantes), icone: p.tipo === "Audiência" ? IconHammer : IconDocument }))
      .filter((p) => {
        const matchBusca =
          p.titulo.toLowerCase().includes(termo) ||
          p.cliente.toLowerCase().includes(termo) ||
          p.processo.toLowerCase().includes(termo);
        const matchArea = filtroArea === "TODAS" || p.area === filtroArea;
        return matchBusca && matchArea;
      })
      .sort((a, b) => a.diasRestantes - b.diasRestantes);
  }, [busca, filtroArea]);

  const abertos = prazosProcessados.filter((p) => !cumpridos.has(p.id));
  const porGrupo = (id) => abertos.filter((p) => p.grupo === id);
  const concluidos = prazosProcessados.filter((p) => cumpridos.has(p.id));

  const total = PRAZOS.length;
  const progresso = Math.round((cumpridos.size / total) * 100);

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-heading text-24 font-bold tracking-tight text-ink">Central de Prazos</h2>
          <p className="text-14 text-ink-muted">
            Prazos e audiências ordenados por urgência, com pontuação de risco.
          </p>
        </div>
        <Button variant="primary" onClick={() => setCalcAberta(true)} className="gap-2 shrink-0">
          <IconFunction className="size-4" fill="currentColor" />
          Calcular prazo
        </Button>
      </div>

      {/* Resumo + progresso */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {GRUPOS.map((g) => (
          <Card key={g.id} className="relative overflow-hidden p-6">
            <span className={cn("absolute inset-x-0 top-0 h-0.5", g.barra)} />
            <div className="flex items-center justify-between">
              <p className="text-13 text-ink-muted">{g.titulo}</p>
              <g.icone className={cn("size-4", g.cor)} fill="currentColor" />
            </div>
            <p className="font-heading text-28 mt-2 font-bold tabular-nums text-ink">{porGrupo(g.id).length}</p>
          </Card>
        ))}
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <p className="text-13 text-ink-muted">Cumpridos nesta sessão</p>
            <IconCheckmarkCircleFill className="size-4 text-status-ok" fill="currentColor" />
          </div>
          <p className="font-heading text-28 mt-2 font-bold tabular-nums text-ink">
            {cumpridos.size}<span className="text-16 text-ink-muted font-medium"> / {total}</span>
          </p>
          <div className="bg-surface-muted mt-2 h-1.5 overflow-hidden rounded-badge">
            <motion.div
              className="bg-status-ok h-full rounded-badge"
              animate={{ width: `${progresso}%` }}
              transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
            />
          </div>
        </Card>
      </div>

      {/* Filtros */}
      <div className="bg-surface border-border flex flex-col gap-4 rounded-card border p-4 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <IconMagnifyingglass
            fill="currentColor"
            className="text-ink-muted pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2"
          />
          <Input
            placeholder="Buscar por título, cliente ou número do processo..."
            className="ps-9"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
          />
        </div>
        <div className="sm:w-56">
          <Select value={filtroArea} onChange={(e) => setFiltroArea(e.target.value)} className="h-10 text-14">
            <option value="TODAS">Todas as áreas</option>
            <option value="Bancário">Bancário</option>
            <option value="Previdenciário">Previdenciário</option>
            <option value="Consumidor">Consumidor</option>
          </Select>
        </div>
      </div>

      {prazosProcessados.length === 0 ? (
        <EmptyState icon={IconClock} titulo="Nenhum prazo encontrado" descricao="Nenhum prazo corresponde aos filtros aplicados." />
      ) : (
        <div className="space-y-8">
          {GRUPOS.map((g) => {
            const itens = porGrupo(g.id);
            if (itens.length === 0) return null;
            return (
              <section key={g.id} className="space-y-4">
                <div className="flex items-center gap-2">
                  <g.icone className={cn("size-4", g.cor)} fill="currentColor" />
                  <h3 className="text-14 font-semibold text-ink">{g.titulo}</h3>
                  <span className="text-ink-muted text-12">· {g.descricao}</span>
                </div>
                <div className="space-y-2">
                  <AnimatePresence initial={false}>
                    {itens.map((prazo) => (
                      <LinhaPrazo key={prazo.id} prazo={prazo} barra={g.barra} aoAlternar={() => alternar(prazo.id)} />
                    ))}
                  </AnimatePresence>
                </div>
              </section>
            );
          })}

          {concluidos.length > 0 && (
            <section className="space-y-4">
              <div className="flex items-center gap-2">
                <IconCheckmarkCircleFill className="size-4 text-status-ok" fill="currentColor" />
                <h3 className="text-14 font-semibold text-ink">Cumpridos</h3>
              </div>
              <div className="space-y-2">
                <AnimatePresence initial={false}>
                  {concluidos.map((prazo) => (
                    <LinhaPrazo key={prazo.id} prazo={prazo} barra="bg-status-ok" cumprido aoAlternar={() => alternar(prazo.id)} />
                  ))}
                </AnimatePresence>
              </div>
            </section>
          )}
        </div>
      )}

      <ModalCalculadoraPrazos open={calcAberta} onOpenChange={setCalcAberta} />
    </div>
  );
}

function LinhaPrazo({ prazo, barra, cumprido = false, aoAlternar }) {
  const pontos = pontuarRisco(prazo);
  const nivel = nivelRisco(pontos);
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.98 }}
      transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
    >
      <Card className={cn("relative flex flex-col gap-4 overflow-hidden p-4 pl-6 transition-colors hover:border-primary/40 sm:flex-row sm:items-center", cumprido && "opacity-60")}>
        <span className={cn("absolute inset-y-0 left-0 w-1", barra)} />
        <button
          type="button"
          onClick={aoAlternar}
          aria-label={cumprido ? "Reabrir prazo" : "Marcar como cumprido"}
          aria-pressed={cumprido}
          className="text-ink-muted hover:text-status-ok shrink-0 transition-colors"
        >
          {cumprido ? (
            <IconCheckmarkCircleFill className="size-6 text-status-ok" fill="currentColor" />
          ) : (
            <IconCheckmarkCircle className="size-6" fill="currentColor" />
          )}
        </button>

        <div className="min-w-0 flex-1">
          <p className={cn("text-14 font-semibold text-ink truncate", cumprido && "line-through")}>{prazo.titulo}</p>
          <p className="text-12 text-ink-muted truncate">
            <span className="text-ink font-medium">{prazo.cliente}</span> · {prazo.processo}
          </p>
          <p className="text-12 text-ink-muted/80 flex items-center gap-2 truncate">
            <prazo.icone className="size-3" fill="currentColor" />
            {prazo.vara} · {prazo.tipo}
          </p>
        </div>

        {!cumprido && (
          <div className="hidden w-28 shrink-0 md:block">
            <div className="flex items-center justify-between text-11 text-ink-muted">
              <span className="inline-flex items-center gap-1">
                <IconFlameFill className="size-3" fill="currentColor" />
                Risco
              </span>
              <span className="tabular-nums">{pontos}</span>
            </div>
            <div className="bg-surface-muted mt-1 h-1.5 overflow-hidden rounded-badge">
              <div className={cn("h-full rounded-badge", BARRA_RISCO[nivel.tom])} style={{ width: `${pontos}%` }} />
            </div>
            <p className="text-11 text-ink-muted mt-1">{nivel.rotulo}</p>
          </div>
        )}

        <div className="flex shrink-0 items-center justify-between gap-1 sm:flex-col sm:items-end sm:justify-center">
          <Badge tone={cumprido ? "cumprido" : prazo.tom}>{cumprido ? "Cumprido" : prazo.rotulo}</Badge>
          <span className="text-12 font-medium text-ink-muted tabular-nums">{formatarData(prazo.dataLimite)}</span>
        </div>
      </Card>
    </motion.div>
  );
}
