import { useMemo, useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import {
  IconArrowUpRight,
  IconArrowUp,
  IconArrowDown,
  IconCalendar,
  IconFolderBadgePlus,
  IconPersonBadgePlus,
  IconExclamationmarkCircleFill,
  IconHammer,
  IconVideo,
  IconDocument,
  IconCheckmarkCircleFill,
  IconEllipsis,
  IconSparkles,
  IconWandAndSparkles,
  IconFunction,
  IconFlameFill,
  IconShieldLefthalfFilled,
} from "symbols-react";
import { motion } from "motion/react";
import { NavLink } from "react-router-dom";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Contador,
  Select,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { ModalCadastrarCliente } from "@/components/modais/ModalCadastrarCliente";
import { ModalCadastrarProcesso } from "@/components/modais/ModalCadastrarProcesso";
import { ModalRedatorIA } from "@/components/modais/ModalRedatorIA";
import { ModalCalculadoraPrazos } from "@/components/modais/ModalCalculadoraPrazos";
import { PRAZOS } from "@/data/escritorio";
import { HOJE, nivelRisco, pontuarRisco } from "@/lib/prazos";
import { addDays, format, isSameDay } from "date-fns";
import { ptBR } from "date-fns/locale";

const COR_RISCO = {
  vencido: "bg-status-vencido",
  hoje: "bg-status-hoje",
  atencao: "bg-status-atencao",
  ok: "bg-status-ok",
};

function PainelRisco() {
  const abertos = PRAZOS.filter((p) => p.diasRestantes <= 7).map((p) => ({ ...p, pontos: pontuarRisco(p) }));
  const media = Math.round(abertos.reduce((s, p) => s + p.pontos, 0) / Math.max(abertos.length, 1));
  const nivel = nivelRisco(media);
  const semana = Array.from({ length: 7 }, (_, i) => {
    const dia = addDays(HOJE, i);
    const doDia = PRAZOS.filter((p) => isSameDay(new Date(p.dataLimite), dia));
    return { dia, qtd: doDia.length, max: Math.max(0, ...doDia.map(pontuarRisco)) };
  });
  const criticos = [...abertos].sort((a, b) => b.pontos - a.pontos).slice(0, 3);

  return (
    <Card className="p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <span className="bg-primary-soft text-primary flex size-12 items-center justify-center rounded-badge">
            <IconShieldLefthalfFilled className="size-5" fill="currentColor" />
          </span>
          <div>
            <p className="text-13 text-ink-muted">Painel de risco · próximos 7 dias</p>
            <p className="font-heading text-24 font-bold text-ink">
              <span className="tabular-nums">{media}</span>
              <span className="text-14 text-ink-muted font-medium"> /100 </span>
              <Badge tone={nivel.tom}>{nivel.rotulo}</Badge>
            </p>
          </div>
        </div>
        <div className="flex gap-2" aria-label="Mapa de calor da semana">
          {semana.map(({ dia, qtd, max }) => {
            const n = nivelRisco(max);
            return (
              <div key={dia.toISOString()} className="flex w-12 flex-col items-center gap-2">
                <span
                  title={`${qtd} prazo(s)`}
                  className={cn(
                    "flex h-12 w-full items-center justify-center rounded-input text-13 font-semibold tabular-nums",
                    qtd ? cn(COR_RISCO[n.tom], "text-bg") : "bg-surface-muted text-ink-muted",
                  )}
                >
                  {qtd || "·"}
                </span>
                <span className="text-11 text-ink-muted capitalize">{format(dia, "EEE", { locale: ptBR })}</span>
              </div>
            );
          })}
        </div>
      </div>

      <ul className="mt-6 grid gap-4 md:grid-cols-3">
        {criticos.map((p) => {
          const n = nivelRisco(p.pontos);
          return (
            <li key={p.id} className="bg-surface-muted/50 border-border rounded-input border p-4">
              <div className="flex items-center justify-between">
                <Badge tone={n.tom}>
                  <IconFlameFill className="size-3" fill="currentColor" />
                  {n.rotulo} · {p.pontos}
                </Badge>
                <span className="text-11 text-ink-muted tabular-nums">{p.diasRestantes === 0 ? "hoje" : p.diasRestantes < 0 ? "vencido" : `${p.diasRestantes}d`}</span>
              </div>
              <p className="text-13 text-ink mt-2 line-clamp-2 font-medium">{p.titulo}</p>
              <p className="text-12 text-ink-muted mt-0.5 truncate">{p.cliente}</p>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

function token(nome) {
  return getComputedStyle(document.documentElement).getPropertyValue(nome).trim();
}

function saudacao() {
  const hora = new Date().getHours();
  if (hora < 12) return "Bom dia";
  if (hora < 18) return "Boa tarde";
  return "Boa noite";
}

const pagina = {
  oculto: {},
  visivel: { transition: { staggerChildren: 0.08, delayChildren: 0.05 } },
};

const entrada = {
  oculto: { opacity: 0, y: 14 },
  visivel: { opacity: 1, y: 0, transition: { duration: 0.45, ease: [0.22, 1, 0.36, 1] } },
};

// Percentual de prazos cumpridos dentro do prazo, últimos 30 dias.
const CUMPRIMENTO_PRAZOS = [
  { dia: "16/09", valor: 86 }, { dia: "18/09", valor: 88 }, { dia: "20/09", valor: 87 },
  { dia: "22/09", valor: 90 }, { dia: "24/09", valor: 89 }, { dia: "26/09", valor: 91 },
  { dia: "28/09", valor: 93 }, { dia: "30/09", valor: 92 }, { dia: "02/10", valor: 94 },
  { dia: "04/10", valor: 93 }, { dia: "06/10", valor: 95 }, { dia: "08/10", valor: 96 },
  { dia: "10/10", valor: 95 }, { dia: "12/10", valor: 97 }, { dia: "14/10", valor: 96 },
  { dia: "16/10", valor: 98 }, { dia: "18/10", valor: 97 }, { dia: "20/10", valor: 98 },
];

const AREAS = [
  { id: "bancario", rotulo: "Bancário", total: 18, cor: "var(--color-primary)" },
  { id: "previdenciario", rotulo: "Previdenciário", total: 14, cor: "var(--color-accent)" },
  { id: "consumidor", rotulo: "Consumidor", total: 10, cor: "var(--color-status-ok)" },
];
const TOTAL_PROCESSOS = AREAS.reduce((s, a) => s + a.total, 0);

const KPIS = [
  {
    titulo: "Taxa de êxito",
    valor: 78,
    sufixo: "%",
    delta: "+4,2 pts",
    positivo: true,
    legenda: "vs. período anterior",
  },
  {
    titulo: "Processos ativos",
    valor: 42,
    sufixo: "",
    delta: "+3",
    positivo: true,
    legenda: "vs. período anterior",
  },
  {
    titulo: "Prazo médio de cumprimento",
    valor: 6,
    sufixo: " dias",
    delta: "-1,5 dia",
    positivo: true,
    legenda: "vs. período anterior",
  },
];

const PRAZOS_SEMANA = [
  {
    id: 1, titulo: "Contestação - Revisional Bancária", processo: "0000001-12.2026.8.00.0100",
    cliente: "Maria da Conceição Silva", vara: "2ª Vara Cível de Paulo Afonso",
    vencimento: "Hoje às 23:59", tom: "vencido", rotulo: "Vence hoje", icone: IconExclamationmarkCircleFill,
  },
  {
    id: 2, titulo: "Audiência de Instrução e Julgamento", processo: "0000311-88.2026.8.00.0100",
    cliente: "Carlos Eduardo Lima", vara: "Juizado Especial Federal",
    vencimento: "Hoje · 09:00", tom: "hoje", rotulo: "Audiência presencial", icone: IconHammer,
  },
  {
    id: 3, titulo: "Audiência de Conciliação Virtual", processo: "0000550-19.2026.8.00.0100",
    cliente: "Patrícia Gomes Barreto", vara: "Juizado Especial Cível · Google Meet",
    vencimento: "Amanhã · 14:30", tom: "atencao", rotulo: "Audiência virtual", icone: IconVideo,
  },
  {
    id: 4, titulo: "Recurso Ordinário (Previdenciário)", processo: "0000233-77.2025.8.00.0100",
    cliente: "Ana Lúcia Santos", vara: "Turma Recursal Previdenciária",
    vencimento: "Em 2 dias · 22/10", tom: "atencao", rotulo: "Faltam 2 dias", icone: IconDocument,
  },
  {
    id: 5, titulo: "Manifestação sobre Laudo Pericial", processo: "0000311-88.2026.8.00.0100",
    cliente: "Carlos Eduardo Lima", vara: "Juizado Especial Federal",
    vencimento: "Em 5 dias · 25/10", tom: "ok", rotulo: "Faltam 5 dias", icone: IconCheckmarkCircleFill,
  },
];

// Composição PF/PJ da carteira ativa — barras finas estilo "waveform".
const CLIENTES_BARRAS = [
  38, 52, 44, 61, 48, 70, 55, 66, 72, 58, 64, 80, 69, 75, 62, 71, 84, 67, 73, 90,
  77, 82, 95, 79, 88, 93, 85, 91, 97, 100,
];

const PROXIMO_PRAZO = {
  titulo: "Contestação — Revisional de Contrato Bancário",
  processo: "0000001-12.2026.8.00.0100",
  cliente: "Maria da Conceição Silva",
  data: "20 de outubro de 2026",
  status: "Vence hoje",
};

function RadialCarteira() {
  const total = 60;

  const ticks = Array.from({ length: total }, (_, i) => {
    const angulo = (i / total) * 360;
    let cor = "var(--color-border)";
    let limite = 0;
    for (const area of AREAS) {
      limite += (area.total / TOTAL_PROCESSOS) * total;
      if (i < limite) {
        cor = area.cor;
        break;
      }
    }
    return { angulo, cor };
  });

  return (
    <div className="relative mx-auto flex size-40 items-center justify-center">
      <svg viewBox="0 0 160 160" className="size-full -rotate-90">
        {ticks.map((t, i) => (
          <motion.line
            key={i}
            x1="80" y1="14" x2="80" y2="22"
            stroke={t.cor}
            strokeWidth="3"
            strokeLinecap="round"
            transform={`rotate(${t.angulo} 80 80)`}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 + i * 0.008, duration: 0.3 }}
          />
        ))}
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-28 font-bold tabular-nums text-ink">
          <Contador valor={TOTAL_PROCESSOS} duracao={900} />
        </span>
        <span className="text-12 text-ink-muted">processos ativos</span>
      </div>
    </div>
  );
}

function TooltipGrafico({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="border-border bg-surface rounded-input border px-4 py-2 shadow-popover">
      <p className="text-11 text-ink-muted">{label}</p>
      <p className="text-14 font-semibold text-ink tabular-nums">{payload[0].value}% no prazo</p>
    </div>
  );
}

export function Home() {
  const [modalClienteAberto, setModalClienteAberto] = useState(false);
  const [modalProcessoAberto, setModalProcessoAberto] = useState(false);
  const [modalIAAberto, setModalIAAberto] = useState(false);
  const [periodo, setPeriodo] = useState("30");
  const [calcAberta, setCalcAberta] = useState(false);

  const corArea = token("--color-primary");
  const dataFormatada = useMemo(
    () => new Date().toLocaleDateString("pt-BR", { day: "2-digit", month: "short" }),
    [],
  );

  return (
    <motion.div className="space-y-8" variants={pagina} initial="oculto" animate="visivel">
      {/* Cabeçalho: saudação + controles de período */}
      <motion.div variants={entrada} className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-heading text-28 font-bold tracking-tight text-ink">
            {saudacao()}, Dr. Jadilson
          </h2>
          <p className="text-14 text-ink-muted mt-1">
            Visão geral da carteira em Direito Bancário, Previdenciário e do Consumidor.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Select
            value={periodo}
            onChange={(e) => setPeriodo(e.target.value)}
            className="h-10 w-44 text-13"
          >
            <option value="7">Últimos 7 dias</option>
            <option value="30">Últimos 30 dias</option>
            <option value="90">Últimos 90 dias</option>
          </Select>
          <span className="border-border bg-surface-muted text-ink-muted hidden items-center gap-2 rounded-badge border px-4 py-2 text-12 sm:inline-flex">
            <IconCalendar className="size-3.5" fill="currentColor" />
            Até {dataFormatada}
          </span>
          <button
            type="button"
            aria-label="Mais opções"
            className="border-border text-ink-muted hover:bg-surface-muted hover:text-ink flex size-10 items-center justify-center rounded-input border transition-colors"
          >
            <IconEllipsis className="size-4" fill="currentColor" />
          </button>
        </div>
      </motion.div>

      {/* Ações rápidas */}
      <motion.div variants={entrada} className="flex items-center gap-4">
        <Button variant="secondary" onClick={() => setModalClienteAberto(true)} className="gap-2">
          <IconPersonBadgePlus className="size-4 text-accent" fill="currentColor" />
          Novo Cliente
        </Button>
        <Button variant="primary" onClick={() => setModalProcessoAberto(true)} className="gap-2">
          <IconFolderBadgePlus className="size-4" fill="currentColor" />
          Novo Processo
        </Button>
        <Button variant="secondary" onClick={() => setCalcAberta(true)} className="gap-2">
          <IconFunction className="size-4 text-accent" fill="currentColor" />
          Calcular prazo
        </Button>
      </motion.div>

      <motion.div variants={entrada}>
        <PainelRisco />
      </motion.div>

      {/* KPIs */}
      <motion.div variants={entrada} className="grid gap-6 sm:grid-cols-3">
        {KPIS.map((kpi) => (
          <Card key={kpi.titulo} className="p-6">
            <p className="text-13 text-ink-muted">{kpi.titulo}</p>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-28 font-bold tabular-nums text-ink">
                <Contador valor={kpi.valor} duracao={900} />
              </span>
              <span className="text-16 font-semibold text-ink-muted">{kpi.sufixo}</span>
            </div>
            <p className={cn("mt-2 flex items-center gap-1 text-12 font-medium", kpi.positivo ? "text-status-ok" : "text-status-vencido")}>
              {kpi.positivo ? (
                <IconArrowUp className="size-3" fill="currentColor" />
              ) : (
                <IconArrowDown className="size-3" fill="currentColor" />
              )}
              {kpi.delta}
              <span className="text-ink-muted font-normal">{kpi.legenda}</span>
            </p>
          </Card>
        ))}
      </motion.div>

      {/* Gráfico principal + coluna lateral */}
      <div className="grid gap-6 lg:grid-cols-3">
        <motion.div variants={entrada} className="lg:col-span-2">
          <Card className="h-full p-6">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-13 text-ink-muted">Cumprimento de prazos</p>
                <p className="font-heading text-24 font-bold tabular-nums text-ink mt-1">98%</p>
              </div>
              <Badge tone="ok">+12 pts nos últimos 30 dias</Badge>
            </div>
            <div className="mt-4 h-52">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={CUMPRIMENTO_PRAZOS} margin={{ top: 8, right: 4, left: -24, bottom: 0 }}>
                  <defs>
                    <linearGradient id="prazos-gradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={corArea} stopOpacity={0.35} />
                      <stop offset="100%" stopColor={corArea} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis
                    dataKey="dia"
                    tick={{ fill: "var(--color-ink-muted)", fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                    interval={3}
                  />
                  <YAxis
                    domain={[80, 100]}
                    tick={{ fill: "var(--color-ink-muted)", fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                    width={32}
                  />
                  <Tooltip content={<TooltipGrafico />} cursor={{ stroke: "var(--color-border)" }} />
                  <Area
                    type="monotone"
                    dataKey="valor"
                    stroke={corArea}
                    strokeWidth={2}
                    fill="url(#prazos-gradient)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </motion.div>

        <motion.div variants={entrada} className="space-y-6">
          <Card className="p-6 text-center">
            <p className="text-13 text-ink-muted text-left">Carteira de processos</p>
            <RadialCarteira />
            <div className="mt-2 flex flex-wrap items-center justify-center gap-x-4 gap-y-1">
              {AREAS.map((a) => (
                <span key={a.id} className="inline-flex items-center gap-2 text-12 text-ink-muted">
                  <span className="size-2 rounded-full" style={{ backgroundColor: a.cor }} />
                  {a.rotulo}
                </span>
              ))}
            </div>
            <NavLink to="/processos">
              <Button variant="secondary" className="mt-4 w-full gap-2">
                Ver processos
                <IconArrowUpRight className="size-3.5" fill="currentColor" />
              </Button>
            </NavLink>
          </Card>

          <Card className="p-6">
            <div className="flex items-baseline justify-between">
              <div>
                <p className="text-13 text-ink-muted">Clientes ativos</p>
                <p className="text-24 font-bold tabular-nums text-ink mt-1">
                  <Contador valor={38} duracao={900} />
                </p>
              </div>
              <span className="text-status-ok text-12 font-medium">76% PF</span>
            </div>
            <div className="mt-4 flex h-10 items-end gap-0.5">
              {CLIENTES_BARRAS.map((h, i) => (
                <span
                  key={i}
                  className={cn("flex-1 rounded-full", i % 4 === 0 ? "bg-primary" : "bg-surface-muted")}
                  style={{ height: `${h}%` }}
                />
              ))}
            </div>
            <div className="mt-2 flex items-center gap-4 text-12 text-ink-muted">
              <span className="inline-flex items-center gap-2">
                <span className="bg-primary size-2 rounded-full" /> Pessoa física
              </span>
              <span className="inline-flex items-center gap-2">
                <span className="bg-surface-muted size-2 rounded-full border border-border" /> Pessoa jurídica
              </span>
            </div>
          </Card>
        </motion.div>
      </div>

      {/* Prazos urgentes da semana */}
      <motion.div variants={entrada}>
        <Card>
          <CardHeader className="pb-4">
            <div className="space-y-1">
              <CardTitle className="text-18 font-semibold">Prazos urgentes da semana</CardTitle>
              <CardDescription>Vencimentos e audiências dos próximos 7 dias</CardDescription>
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            <ul className="divide-border/60 divide-y">
              {PRAZOS_SEMANA.map((item) => {
                const Icone = item.icone;
                return (
                  <li key={item.id} className="py-4 first:pt-0 last:pb-0 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="flex items-start gap-4 min-w-0">
                      <div className="bg-surface-muted border border-border flex size-10 shrink-0 items-center justify-center rounded-badge text-accent mt-0.5">
                        <Icone className="size-5" fill="currentColor" />
                      </div>
                      <div className="min-w-0">
                        <p className="font-semibold text-14 text-ink truncate">{item.titulo}</p>
                        <p className="text-12 text-ink-muted truncate">
                          <span className="text-ink font-medium">{item.cliente}</span> · {item.processo}
                        </p>
                        <p className="text-12 text-ink-muted/80 truncate">{item.vara}</p>
                      </div>
                    </div>
                    <div className="flex sm:flex-col items-center sm:items-end justify-between sm:justify-center gap-1 shrink-0">
                      <Badge tone={item.tom}>{item.rotulo}</Badge>
                      <span className="text-12 font-medium text-ink-muted tabular-nums">{item.vencimento}</span>
                    </div>
                  </li>
                );
              })}
            </ul>
          </CardContent>
          <div className="border-t border-border px-6 py-4 flex items-center justify-between text-13 bg-surface-muted/20 rounded-b-card">
            <span className="text-ink-muted">3 prazos exigem protocolo eletrônico urgente hoje</span>
            <NavLink to="/prazos" className="text-primary hover:text-primary-hover font-medium inline-flex items-center gap-1">
              Ver todos os prazos
              <IconArrowUpRight className="size-4" fill="currentColor" />
            </NavLink>
          </div>
        </Card>
      </motion.div>

      {/* IA, capacidade do escritório e próximo prazo fatal */}
      <div className="grid gap-6 lg:grid-cols-3">
        <motion.div variants={entrada}>
          <Card className="h-full p-6 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between">
                <p className="flex items-center gap-2 text-13 font-medium text-ink">
                  <IconSparkles className="size-3.5 text-accent" fill="currentColor" />
                  Insights com IA
                </p>
              </div>
              <p className="mt-4 text-15 text-ink leading-snug">
                3 prazos previdenciários vencem nos próximos 5 dias — nenhum deles tem minuta de peça iniciada ainda.
              </p>
            </div>
            <Button variant="secondary" className="mt-4 w-full gap-2" onClick={() => setModalIAAberto(true)}>
              <IconWandAndSparkles className="size-4" fill="currentColor" />
              Redigir com IA
            </Button>
          </Card>
        </motion.div>

        <motion.div variants={entrada}>
          <Card className="h-full p-6">
            <p className="text-13 text-ink-muted">Capacidade do escritório</p>
            <p className="text-24 font-bold text-ink mt-1">6 vagas livres</p>
            <div className="mt-4 flex h-2.5 overflow-hidden rounded-badge gap-0.5">
              <span className="bg-primary h-full" style={{ width: "61%" }} />
              <span className="bg-status-ok h-full" style={{ width: "21%" }} />
              <span className="bg-surface-muted h-full" style={{ width: "18%" }} />
            </div>
            <div className="mt-4 flex flex-wrap gap-x-4 gap-y-2 text-12 text-ink-muted">
              <span className="inline-flex items-center gap-2"><span className="bg-primary size-2 rounded-full" />Em andamento · 61%</span>
              <span className="inline-flex items-center gap-2"><span className="bg-status-ok size-2 rounded-full" />Concluídos no mês · 21%</span>
              <span className="inline-flex items-center gap-2"><span className="bg-surface-muted size-2 rounded-full border border-border" />Disponível · 18%</span>
            </div>
          </Card>
        </motion.div>

        <motion.div variants={entrada}>
          <Card className="h-full p-6">
            <p className="text-13 text-ink-muted">Próximo prazo fatal</p>
            <p className="text-15 font-semibold text-ink mt-2 leading-snug">{PROXIMO_PRAZO.titulo}</p>
            <dl className="mt-4 space-y-2 text-13">
              <div className="flex items-center justify-between">
                <dt className="text-ink-muted">Processo</dt>
                <dd className="text-ink font-medium tabular-nums">{PROXIMO_PRAZO.processo}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-ink-muted">Cliente</dt>
                <dd className="text-ink font-medium">{PROXIMO_PRAZO.cliente}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-ink-muted">Vencimento</dt>
                <dd className="text-ink font-medium">{PROXIMO_PRAZO.data}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-ink-muted">Status</dt>
                <dd><Badge tone="vencido">{PROXIMO_PRAZO.status}</Badge></dd>
              </div>
            </dl>
          </Card>
        </motion.div>
      </div>

      {/* Modais */}
      <ModalCadastrarCliente open={modalClienteAberto} onOpenChange={setModalClienteAberto} />
      <ModalCadastrarProcesso open={modalProcessoAberto} onOpenChange={setModalProcessoAberto} />
      <ModalCalculadoraPrazos open={calcAberta} onOpenChange={setCalcAberta} />
      <ModalRedatorIA open={modalIAAberto} onOpenChange={setModalIAAberto} processo={null} />
    </motion.div>
  );
}
