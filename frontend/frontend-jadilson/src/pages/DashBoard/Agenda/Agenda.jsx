import { useMemo, useState } from "react";
import {
  addDays,
  addMonths,
  addWeeks,
  eachDayOfInterval,
  endOfMonth,
  endOfWeek,
  format,
  isSameDay,
  isSameMonth,
  isToday,
  startOfMonth,
  startOfWeek,
  subDays,
  subMonths,
  subWeeks,
} from "date-fns";
import { ptBR } from "date-fns/locale";
import {
  IconChevronLeft,
  IconChevronRight,
  IconPlus,
  IconClock,
  IconMappin,
  IconTextAlignleft,
  IconTrash,
  IconCalendar,
} from "symbols-react";
import { Button, Badge, Drawer, EmptyState, Field, Input, Modal, Select, Textarea } from "@/components/ui";
import { HOJE } from "@/lib/prazos";
import { cn } from "@/lib/cn";

const TIPOS = {
  "Audiência": { ponto: "bg-status-vencido", chip: "bg-status-vencido-soft text-status-vencido-ink", tom: "vencido" },
  "Audiência Virtual": { ponto: "bg-status-atencao", chip: "bg-status-atencao-soft text-status-atencao-ink", tom: "atencao" },
  "Reunião": { ponto: "bg-primary", chip: "bg-primary-soft text-ink", tom: "primary" },
  "Conciliação": { ponto: "bg-status-ok", chip: "bg-status-ok-soft text-status-ok-ink", tom: "ok" },
  "Despacho": { ponto: "bg-ink-muted", chip: "bg-surface-muted text-ink-muted", tom: "neutral" },
};
const NOMES_TIPOS = Object.keys(TIPOS);

const VISOES = [
  { id: "mes", rotulo: "Mês" },
  { id: "semana", rotulo: "Semana" },
  { id: "dia", rotulo: "Dia" },
  { id: "lista", rotulo: "Lista" },
];

const HORA_INICIO = 7;
const HORA_FIM = 20;
const ALTURA_HORA = 56;
const HORAS = Array.from({ length: HORA_FIM - HORA_INICIO }, (_, i) => HORA_INICIO + i);

const EVENTOS_INICIAIS = [
  { id: 1, data: new Date(2026, 9, 20, 9, 0), duracao: 90, titulo: "Audiência de instrução previdenciária", local: "Juizado Especial Federal", descricao: "Cliente: Carlos Eduardo Lima", tipo: "Audiência" },
  { id: 2, data: new Date(2026, 9, 21, 14, 0), duracao: 60, titulo: "Reunião de alinhamento estratégico", local: "Escritório", descricao: "Cliente: Construtora Alagoas Ltda.", tipo: "Reunião" },
  { id: 3, data: new Date(2026, 9, 21, 14, 30), duracao: 45, titulo: "Conciliação virtual - ação consumerista", local: "Google Meet", descricao: "Cliente: Patrícia Gomes Barreto", tipo: "Audiência Virtual" },
  { id: 4, data: new Date(2026, 9, 22, 10, 30), duracao: 60, titulo: "Conciliação prévia", local: "Juizado Especial Cível", descricao: "Cliente: Patrícia Gomes Barreto", tipo: "Conciliação" },
  { id: 5, data: new Date(2026, 9, 25, 16, 0), duracao: 30, titulo: "Despacho com o Magistrado", local: "Gabinete 2ª Vara Cível", descricao: "", tipo: "Despacho" },
  { id: 6, data: new Date(2026, 9, 30, 11, 0), duracao: 90, titulo: "Audiência de embargos à execução", local: "Vara Cível Empresarial", descricao: "Cliente: Construtora Alagoas Ltda.", tipo: "Audiência" },
];

const DIAS_SEMANA = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"];

function diasDoMes(ref) {
  return eachDayOfInterval({
    start: startOfWeek(startOfMonth(ref)),
    end: endOfWeek(endOfMonth(ref)),
  });
}

// Distribui eventos sobrepostos em colunas lado a lado (como no Notion Calendar).
function posicionar(eventos) {
  const ordenados = [...eventos].sort((a, b) => a.data - b.data);
  const colunas = [];
  const resultado = ordenados.map((e) => {
    const fim = e.data.getTime() + e.duracao * 60000;
    let col = colunas.findIndex((ultimoFim) => ultimoFim <= e.data.getTime());
    if (col === -1) col = colunas.length;
    colunas[col] = fim;
    return { ...e, col };
  });
  return resultado.map((e) => ({ ...e, total: colunas.length }));
}

export function Agenda() {
  const [ref, setRef] = useState(HOJE);
  const [visao, setVisao] = useState("mes");
  const [eventos, setEventos] = useState(EVENTOS_INICIAIS);
  const [ocultos, setOcultos] = useState(() => new Set());
  const [selecionado, setSelecionado] = useState(null);
  const [novo, setNovo] = useState(null);

  const visiveis = useMemo(() => eventos.filter((e) => !ocultos.has(e.tipo)), [eventos, ocultos]);
  const doDia = (dia) => visiveis.filter((e) => isSameDay(e.data, dia)).sort((a, b) => a.data - b.data);

  function navegar(sentido) {
    const f = sentido > 0
      ? { mes: addMonths, semana: addWeeks, dia: addDays, lista: addMonths }
      : { mes: subMonths, semana: subWeeks, dia: subDays, lista: subMonths };
    setRef((r) => f[visao](r, 1));
  }

  function alternarTipo(tipo) {
    setOcultos((atual) => {
      const copia = new Set(atual);
      if (copia.has(tipo)) copia.delete(tipo);
      else copia.add(tipo);
      return copia;
    });
  }

  function abrirNovo(dia, hora = 9) {
    const d = new Date(dia);
    d.setHours(hora, 0, 0, 0);
    setNovo({ titulo: "", tipo: "Audiência", dia: format(d, "yyyy-MM-dd"), hora: format(d, "HH:mm"), duracao: 60, local: "", descricao: "" });
  }

  function salvarNovo(e) {
    e.preventDefault();
    if (!novo.titulo.trim()) return;
    const [h, m] = novo.hora.split(":").map(Number);
    const [ano, mes, dia] = novo.dia.split("-").map(Number);
    setEventos((prev) => [
      ...prev,
      { id: Date.now(), data: new Date(ano, mes - 1, dia, h, m), duracao: Number(novo.duracao) || 60, titulo: novo.titulo.trim(), local: novo.local.trim(), descricao: novo.descricao.trim(), tipo: novo.tipo },
    ]);
    setRef(new Date(ano, mes - 1, dia));
    setNovo(null);
  }

  function excluir(id) {
    setEventos((prev) => prev.filter((e) => e.id !== id));
    setSelecionado(null);
  }

  const titulo = useMemo(() => {
    if (visao === "dia") return format(ref, "d 'de' MMMM 'de' yyyy", { locale: ptBR });
    if (visao === "semana") {
      const ini = startOfWeek(ref);
      const fim = endOfWeek(ref);
      return isSameMonth(ini, fim)
        ? `${format(ini, "d")} – ${format(fim, "d 'de' MMMM yyyy", { locale: ptBR })}`
        : `${format(ini, "d MMM", { locale: ptBR })} – ${format(fim, "d MMM yyyy", { locale: ptBR })}`;
    }
    return format(ref, "MMMM 'de' yyyy", { locale: ptBR });
  }, [ref, visao]);

  return (
    <div className="space-y-6">
      {/* Barra de ferramentas */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-4">
          <h2 className="font-heading text-24 font-bold tracking-tight text-ink whitespace-nowrap first-letter:uppercase">{titulo}</h2>
          <div className="flex items-center gap-1">
            <button type="button" aria-label="Anterior" onClick={() => navegar(-1)} className="text-ink-muted hover:bg-surface-muted hover:text-ink flex size-10 items-center justify-center rounded-input transition-colors">
              <IconChevronLeft className="size-4" fill="currentColor" />
            </button>
            <button type="button" onClick={() => setRef(HOJE)} className="text-13 text-ink hover:bg-surface-muted h-10 rounded-input px-4 font-medium transition-colors">
              Hoje
            </button>
            <button type="button" aria-label="Próximo" onClick={() => navegar(1)} className="text-ink-muted hover:bg-surface-muted hover:text-ink flex size-10 items-center justify-center rounded-input transition-colors">
              <IconChevronRight className="size-4" fill="currentColor" />
            </button>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-4">
          <div role="group" aria-label="Visão da agenda" className="bg-surface-muted border-border flex rounded-input border p-1">
            {VISOES.map((v) => (
              <button
                key={v.id}
                type="button"
                aria-pressed={visao === v.id}
                onClick={() => setVisao(v.id)}
                className={cn(
                  "text-13 h-8 rounded-input px-4 font-medium transition-colors",
                  visao === v.id ? "bg-primary text-primary-foreground" : "text-ink-muted hover:text-ink",
                )}
              >
                {v.rotulo}
              </button>
            ))}
          </div>
          <Button variant="primary" className="gap-2" onClick={() => abrirNovo(ref)}>
            <IconPlus className="size-4" fill="currentColor" />
            Novo evento
          </Button>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[256px_1fr]">
        {/* Lateral: mini calendário + calendários */}
        <aside className="grid gap-6 md:grid-cols-2 xl:block xl:space-y-6">
          <MiniCalendario ref_={ref} aoEscolher={setRef} eventos={visiveis} />

          <div className="bg-surface border-border rounded-card border p-4">
            <p className="text-12 text-ink-muted px-2 pb-2 font-medium">Calendários</p>
            <ul className="space-y-1">
              {NOMES_TIPOS.map((tipo) => {
                const ativo = !ocultos.has(tipo);
                return (
                  <li key={tipo}>
                    <button
                      type="button"
                      onClick={() => alternarTipo(tipo)}
                      aria-pressed={ativo}
                      className="hover:bg-surface-muted flex w-full items-center gap-3 rounded-input px-2 py-2 text-left transition-colors"
                    >
                      <span className={cn("flex size-4 items-center justify-center rounded-[5px] border", ativo ? cn(TIPOS[tipo].ponto, "border-transparent") : "border-border")}>
                        {ativo && <span className="bg-bg size-1.5 rounded-full" />}
                      </span>
                      <span className={cn("text-13 flex-1", ativo ? "text-ink" : "text-ink-muted")}>{tipo}</span>
                      <span className="text-11 text-ink-muted tabular-nums">{eventos.filter((e) => e.tipo === tipo).length}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        </aside>

        {/* Visões */}
        <div className="bg-surface border-border min-w-0 overflow-hidden rounded-card border">
          {visao === "mes" && <VisaoMes ref_={ref} doDia={doDia} aoCriar={abrirNovo} aoAbrir={setSelecionado} aoEscolherDia={(d) => { setRef(d); setVisao("dia"); }} />}
          {(visao === "semana" || visao === "dia") && (
            <VisaoHoras
              dias={visao === "dia" ? [ref] : eachDayOfInterval({ start: startOfWeek(ref), end: endOfWeek(ref) })}
              doDia={doDia}
              aoCriar={abrirNovo}
              aoAbrir={setSelecionado}
            />
          )}
          {visao === "lista" && <VisaoLista ref_={ref} visiveis={visiveis} aoAbrir={setSelecionado} />}
        </div>
      </div>

      {/* Detalhe do evento */}
      <Drawer
        open={!!selecionado}
        onOpenChange={(v) => !v && setSelecionado(null)}
        titulo={selecionado?.titulo ?? "Evento"}
        footer={
          selecionado && (
            <Button variant="secondary" className="gap-2 text-status-vencido-ink" onClick={() => excluir(selecionado.id)}>
              <IconTrash className="size-4" fill="currentColor" />
              Excluir evento
            </Button>
          )
        }
      >
        {selecionado && (
          <div className="space-y-6">
            <Badge tone={TIPOS[selecionado.tipo].tom}>{selecionado.tipo}</Badge>
            <dl className="space-y-4">
              <div className="flex items-start gap-4">
                <IconCalendar className="text-ink-muted mt-0.5 size-4 shrink-0" fill="currentColor" />
                <dd className="text-14 text-ink capitalize">{format(selecionado.data, "EEEE, d 'de' MMMM 'de' yyyy", { locale: ptBR })}</dd>
              </div>
              <div className="flex items-start gap-4">
                <IconClock className="text-ink-muted mt-0.5 size-4 shrink-0" fill="currentColor" />
                <dd className="text-14 text-ink tabular-nums">
                  {format(selecionado.data, "HH:mm")} – {format(new Date(selecionado.data.getTime() + selecionado.duracao * 60000), "HH:mm")}
                </dd>
              </div>
              {selecionado.local && (
                <div className="flex items-start gap-4">
                  <IconMappin className="text-ink-muted mt-0.5 size-4 shrink-0" fill="currentColor" />
                  <dd className="text-14 text-ink">{selecionado.local}</dd>
                </div>
              )}
              {selecionado.descricao && (
                <div className="flex items-start gap-4">
                  <IconTextAlignleft className="text-ink-muted mt-0.5 size-4 shrink-0" fill="currentColor" />
                  <dd className="text-14 text-ink-muted">{selecionado.descricao}</dd>
                </div>
              )}
            </dl>
          </div>
        )}
      </Drawer>

      {/* Novo evento */}
      <Modal
        open={!!novo}
        onOpenChange={(v) => !v && setNovo(null)}
        titulo="Novo evento"
        descricao="Audiências, reuniões e despachos do escritório."
      >
        {novo && (
          <form onSubmit={salvarNovo} className="space-y-4">
            <Field label="Título" id="ev-titulo">
              <Input id="ev-titulo" autoFocus required maxLength={120} value={novo.titulo} onChange={(e) => setNovo({ ...novo, titulo: e.target.value })} placeholder="Ex.: Audiência de conciliação" />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Tipo" id="ev-tipo">
                <Select id="ev-tipo" value={novo.tipo} onChange={(e) => setNovo({ ...novo, tipo: e.target.value })}>
                  {NOMES_TIPOS.map((t) => <option key={t}>{t}</option>)}
                </Select>
              </Field>
              <Field label="Duração" id="ev-duracao">
                <Select id="ev-duracao" value={novo.duracao} onChange={(e) => setNovo({ ...novo, duracao: e.target.value })}>
                  {[30, 45, 60, 90, 120].map((d) => <option key={d} value={d}>{d} min</option>)}
                </Select>
              </Field>
              <Field label="Data" id="ev-dia">
                <Input id="ev-dia" type="date" required value={novo.dia} onChange={(e) => setNovo({ ...novo, dia: e.target.value })} />
              </Field>
              <Field label="Hora" id="ev-hora">
                <Input id="ev-hora" type="time" required value={novo.hora} onChange={(e) => setNovo({ ...novo, hora: e.target.value })} />
              </Field>
            </div>
            <Field label="Local" id="ev-local">
              <Input id="ev-local" maxLength={120} value={novo.local} onChange={(e) => setNovo({ ...novo, local: e.target.value })} placeholder="Vara, escritório ou link da reunião" />
            </Field>
            <Field label="Notas" id="ev-notas">
              <Textarea id="ev-notas" maxLength={500} value={novo.descricao} onChange={(e) => setNovo({ ...novo, descricao: e.target.value })} />
            </Field>
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="secondary" onClick={() => setNovo(null)}>Cancelar</Button>
              <Button type="submit">Salvar evento</Button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
}

function MiniCalendario({ ref_, aoEscolher, eventos }) {
  const [mes, setMes] = useState(ref_);
  const dias = diasDoMes(mes);
  return (
    <div className="bg-surface border-border rounded-card border p-4">
      <div className="flex items-center justify-between pb-2">
        <p className="text-14 text-ink px-2 font-semibold capitalize">{format(mes, "MMMM yyyy", { locale: ptBR })}</p>
        <div className="flex">
          <button type="button" aria-label="Mês anterior" onClick={() => setMes((m) => subMonths(m, 1))} className="text-ink-muted hover:text-ink flex size-8 items-center justify-center rounded-input transition-colors">
            <IconChevronLeft className="size-3.5" fill="currentColor" />
          </button>
          <button type="button" aria-label="Próximo mês" onClick={() => setMes((m) => addMonths(m, 1))} className="text-ink-muted hover:text-ink flex size-8 items-center justify-center rounded-input transition-colors">
            <IconChevronRight className="size-3.5" fill="currentColor" />
          </button>
        </div>
      </div>
      <div className="text-11 text-ink-muted grid grid-cols-7 pb-1 text-center uppercase">
        {DIAS_SEMANA.map((d) => <span key={d}>{d[0]}</span>)}
      </div>
      <div className="grid grid-cols-7 gap-y-1">
        {dias.map((dia) => {
          const temEvento = eventos.some((e) => isSameDay(e.data, dia));
          const escolhido = isSameDay(dia, ref_);
          return (
            <button
              key={dia.toISOString()}
              type="button"
              onClick={() => aoEscolher(dia)}
              className={cn(
                "text-12 relative mx-auto flex size-8 items-center justify-center rounded-full tabular-nums transition-colors",
                !isSameMonth(dia, mes) && "text-ink-muted/40",
                isToday(dia) && !escolhido && "text-primary font-bold",
                escolhido ? "bg-primary text-primary-foreground font-semibold" : "hover:bg-surface-muted",
              )}
            >
              {format(dia, "d")}
              {temEvento && !escolhido && <span className="bg-accent absolute bottom-1 size-1 rounded-full" />}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function Chip({ evento, aoAbrir, compacto = false }) {
  return (
    <button
      type="button"
      onClick={(e) => { e.stopPropagation(); aoAbrir(evento); }}
      className={cn("text-12 flex w-full items-center gap-2 truncate rounded-[8px] px-2 py-1 text-left font-medium transition-opacity hover:opacity-80", TIPOS[evento.tipo].chip)}
    >
      <span className={cn("size-1.5 shrink-0 rounded-full", TIPOS[evento.tipo].ponto)} />
      {!compacto && <span className="text-11 tabular-nums opacity-70">{format(evento.data, "HH:mm")}</span>}
      <span className="truncate">{evento.titulo}</span>
    </button>
  );
}

function VisaoMes({ ref_, doDia, aoCriar, aoAbrir, aoEscolherDia }) {
  const dias = diasDoMes(ref_);
  return (
    <div>
      <div className="border-border text-12 text-ink-muted grid grid-cols-7 border-b text-center capitalize">
        {DIAS_SEMANA.map((d) => <span key={d} className="py-3">{d}</span>)}
      </div>
      <div className="grid grid-cols-7">
        {dias.map((dia, i) => {
          const eventos = doDia(dia);
          return (
            <div
              key={dia.toISOString()}
              role="button"
              tabIndex={0}
              aria-label={`Criar evento em ${format(dia, "d 'de' MMMM", { locale: ptBR })}`}
              onClick={() => aoCriar(dia)}
              onKeyDown={(e) => e.key === "Enter" && aoCriar(dia)}
              className={cn(
                "border-border hover:bg-surface-muted/50 min-h-32 cursor-pointer space-y-1 border-b p-2 transition-colors",
                i % 7 !== 6 && "border-r",
                !isSameMonth(dia, ref_) && "bg-bg/40",
              )}
            >
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); aoEscolherDia(dia); }}
                className={cn(
                  "text-12 flex size-6 items-center justify-center rounded-full tabular-nums",
                  isToday(dia) ? "bg-primary text-primary-foreground font-bold" : isSameMonth(dia, ref_) ? "text-ink" : "text-ink-muted/50",
                )}
              >
                {format(dia, "d")}
              </button>
              {eventos.slice(0, 3).map((e) => <Chip key={e.id} evento={e} aoAbrir={aoAbrir} />)}
              {eventos.length > 3 && <p className="text-11 text-ink-muted px-2">+{eventos.length - 3} mais</p>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function VisaoHoras({ dias, doDia, aoCriar, aoAbrir }) {
  const agora = new Date(HOJE.getFullYear(), HOJE.getMonth(), HOJE.getDate(), 10, 30);
  const colunas = `56px repeat(${dias.length}, minmax(0, 1fr))`;
  return (
    <div className="max-h-[680px] overflow-auto">
      <div className="bg-surface border-border sticky top-0 z-10 grid border-b" style={{ gridTemplateColumns: colunas }}>
        <span />
        {dias.map((dia) => (
          <div key={dia.toISOString()} className="py-3 text-center">
            <p className="text-12 text-ink-muted capitalize">{format(dia, "EEE", { locale: ptBR })}</p>
            <p className={cn("text-16 mx-auto mt-1 flex size-8 items-center justify-center rounded-full font-semibold tabular-nums", isToday(dia) ? "bg-primary text-primary-foreground" : "text-ink")}>
              {format(dia, "d")}
            </p>
          </div>
        ))}
      </div>

      <div className="relative grid" style={{ gridTemplateColumns: colunas }}>
        <div>
          {HORAS.map((h) => (
            <div key={h} style={{ height: ALTURA_HORA }} className="text-11 text-ink-muted pr-2 text-right tabular-nums">
              <span className="relative -top-2">{String(h).padStart(2, "0")}:00</span>
            </div>
          ))}
        </div>

        {dias.map((dia) => (
          <div key={dia.toISOString()} className="border-border relative border-l">
            {HORAS.map((h) => (
              <button
                key={h}
                type="button"
                aria-label={`Criar evento às ${h}:00`}
                onClick={() => aoCriar(dia, h)}
                style={{ height: ALTURA_HORA }}
                className="border-border hover:bg-surface-muted/50 block w-full border-t transition-colors"
              />
            ))}
            {posicionar(doDia(dia)).map((e) => {
              const inicio = e.data.getHours() + e.data.getMinutes() / 60 - HORA_INICIO;
              if (inicio < 0 || inicio >= HORA_FIM - HORA_INICIO) return null;
              return (
                <button
                  key={e.id}
                  type="button"
                  onClick={() => aoAbrir(e)}
                  className={cn("absolute overflow-hidden rounded-[10px] border-l-[3px] px-2 py-1 text-left transition-opacity hover:opacity-80", TIPOS[e.tipo].chip, "border-current")}
                  style={{
                    top: inicio * ALTURA_HORA + 1,
                    height: Math.max((e.duracao / 60) * ALTURA_HORA - 2, 24),
                    left: `calc(${(e.col / e.total) * 100}% + 2px)`,
                    width: `calc(${100 / e.total}% - 4px)`,
                  }}
                >
                  <p className="text-12 truncate font-semibold">{e.titulo}</p>
                  <p className="text-11 truncate tabular-nums opacity-70">{format(e.data, "HH:mm")}{e.local ? ` · ${e.local}` : ""}</p>
                </button>
              );
            })}
            {isToday(dia) && (
              <span
                aria-hidden="true"
                className="bg-status-vencido pointer-events-none absolute inset-x-0 h-px"
                style={{ top: (agora.getHours() + agora.getMinutes() / 60 - HORA_INICIO) * ALTURA_HORA }}
              >
                <span className="bg-status-vencido absolute -top-1 -left-1 size-2 rounded-full" />
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function VisaoLista({ ref_, visiveis, aoAbrir }) {
  const doMes = visiveis.filter((e) => isSameMonth(e.data, ref_)).sort((a, b) => a.data - b.data);
  const grupos = [];
  for (const e of doMes) {
    const ultimo = grupos[grupos.length - 1];
    if (ultimo && isSameDay(ultimo.dia, e.data)) ultimo.itens.push(e);
    else grupos.push({ dia: e.data, itens: [e] });
  }
  if (grupos.length === 0) {
    return <EmptyState icon={IconCalendar} titulo="Nenhum evento neste mês" descricao="Crie um evento ou ajuste os calendários na lateral." />;
  }
  return (
    <ul className="divide-border divide-y">
      {grupos.map((g) => (
        <li key={g.dia.toISOString()} className="flex gap-6 p-6">
          <div className="w-16 shrink-0 text-center">
            <p className={cn("font-heading text-28 font-bold tabular-nums", isToday(g.dia) ? "text-primary" : "text-ink")}>{format(g.dia, "dd")}</p>
            <p className="text-12 text-ink-muted capitalize">{format(g.dia, "EEE", { locale: ptBR })}</p>
          </div>
          <ul className="min-w-0 flex-1 space-y-2">
            {g.itens.map((e) => (
              <li key={e.id}>
                <button type="button" onClick={() => aoAbrir(e)} className="hover:bg-surface-muted flex w-full items-center gap-4 rounded-input p-2 text-left transition-colors">
                  <span className={cn("h-10 w-1 shrink-0 rounded-full", TIPOS[e.tipo].ponto)} />
                  <span className="text-13 text-ink-muted w-12 shrink-0 tabular-nums">{format(e.data, "HH:mm")}</span>
                  <span className="min-w-0 flex-1">
                    <span className="text-14 text-ink block truncate font-medium">{e.titulo}</span>
                    <span className="text-12 text-ink-muted block truncate">{e.local}</span>
                  </span>
                  <Badge tone={TIPOS[e.tipo].tom}>{e.tipo}</Badge>
                </button>
              </li>
            ))}
          </ul>
        </li>
      ))}
    </ul>
  );
}
