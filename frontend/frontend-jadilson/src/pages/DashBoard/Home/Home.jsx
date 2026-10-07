import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  ArrowUpRight,
  CalendarDays,
  Clock,
  FolderOpen,
  TrendingDown,
  TrendingUp,
  TriangleAlert,
} from "lucide-react";
import { NavLink } from "react-router-dom";
import {
  Badge,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui";
import { cn } from "@/lib/cn";

function token(nome) {
  return getComputedStyle(document.documentElement)
    .getPropertyValue(nome)
    .trim();
}

const kpis = [
  {
    titulo: "Prazos vencidos",
    valor: "3",
    delta: "-2 na semana",
    melhor: true,
    icone: TriangleAlert,
  },
  {
    titulo: "Vencem hoje",
    valor: "5",
    delta: "+1 hoje",
    melhor: false,
    icone: Clock,
  },
  {
    titulo: "Processos ativos",
    valor: "42",
    delta: "+12.5% no mês",
    melhor: true,
    icone: FolderOpen,
  },
  {
    titulo: "Audiências na semana",
    valor: "7",
    delta: "+2",
    melhor: true,
    icone: CalendarDays,
  },
];

const prazosMes = [
  { mes: "Jan", previstos: 28, cumpridos: 30 },
  { mes: "Fev", previstos: 31, cumpridos: 33 },
  { mes: "Mar", previstos: 34, cumpridos: 36 },
  { mes: "Abr", previstos: 36, cumpridos: 39 },
  { mes: "Mai", previstos: 35, cumpridos: 32 },
  { mes: "Jun", previstos: 38, cumpridos: 41 },
  { mes: "Jul", previstos: 41, cumpridos: 44 },
  { mes: "Ago", previstos: 43, cumpridos: 47 },
  { mes: "Set", previstos: 42, cumpridos: 40 },
  { mes: "Out", previstos: 46, cumpridos: 50 },
  { mes: "Nov", previstos: 48, cumpridos: 53 },
  { mes: "Dez", previstos: 51, cumpridos: 57 },
];

const prazosRecentes = [
  {
    id: 1,
    inicial: "C",
    titulo: "Contestação",
    sub: "0000001-12.2026.8.00.0100 · Maria Conceição",
    data: "10/10/2026",
    tom: "hoje",
    rotulo: "Vence hoje",
  },
  {
    id: 2,
    inicial: "R",
    titulo: "Recurso de apelação",
    sub: "0000042-30.2026.8.00.0100 · João Pereira",
    data: "15/10/2026",
    tom: "atencao",
    rotulo: "Faltam 5 dias",
  },
  {
    id: 3,
    inicial: "M",
    titulo: "Manifestação sobre laudo",
    sub: "0000110-05.2026.8.00.0100 · Construtora Alagoas",
    data: "28/10/2026",
    tom: "ok",
    rotulo: "Faltam 18 dias",
  },
  {
    id: 4,
    inicial: "E",
    titulo: "Embargos de declaração",
    sub: "0000233-77.2025.8.00.0100 · Ana Lúcia Santos",
    data: "01/10/2026",
    tom: "vencido",
    rotulo: "Vencido",
  },
];

const compromissos = [
  {
    id: 1,
    dia: "10",
    mes: "out",
    titulo: "Audiência inicial",
    sub: "Fórum de Maceió · Maria Conceição",
    hora: "09:00",
    tipo: "Audiência",
  },
  {
    id: 2,
    dia: "12",
    mes: "out",
    titulo: "Reunião com o cliente",
    sub: "Escritório · João Pereira",
    hora: "14:00",
    tipo: "Reunião",
  },
  {
    id: 3,
    dia: "14",
    mes: "out",
    titulo: "Conciliação",
    sub: "Fórum de Arapiraca · Construtora Alagoas",
    hora: "10:30",
    tipo: "Conciliação",
  },
  {
    id: 4,
    dia: "16",
    mes: "out",
    titulo: "Juntada de documentos",
    sub: "Peticionamento online · Ana Lúcia Santos",
    hora: "11:00",
    tipo: "Prazo",
  },
];

function Kpi({ titulo, valor, delta, melhor, icone: Icon }) {
  const Seta = delta.trim().startsWith("-") ? TrendingDown : TrendingUp;

  return (
    <Card className="p-6">
      <div className="flex items-start justify-between gap-4">
        <p className="text-14 font-medium text-ink-muted">{titulo}</p>
        <span className="bg-surface-muted text-ink-muted flex size-9 shrink-0 items-center justify-center rounded-input">
          <Icon className="size-4" aria-hidden="true" />
        </span>
      </div>
      <div className="mt-4 flex flex-wrap items-end gap-3">
        <p className="text-40 leading-none font-semibold tabular-nums">
          {valor}
        </p>
        <span
          className={cn(
            "inline-flex items-center gap-1 text-14 font-medium",
            melhor ? "text-status-ok" : "text-status-vencido",
          )}
        >
          <Seta className="size-4" aria-hidden="true" />
          {delta}
        </span>
      </div>
    </Card>
  );
}

function DicaGrafico({ active, payload, label }) {
  if (!active || !payload?.length) return null;

  return (
    <div className="bg-surface border-border rounded-input border px-3 py-2 shadow-popover">
      <p className="text-12 font-medium text-ink-muted">{label}</p>
      {payload.map((item) => (
        <p
          key={item.dataKey}
          className="text-14 font-medium tabular-nums"
          style={{ color: item.color }}
        >
          {item.name}: {item.value}
        </p>
      ))}
    </div>
  );
}

function Ponto({ cor }) {
  return (
    <span
      aria-hidden="true"
      className="size-2.5 shrink-0 rounded-badge"
      style={{ backgroundColor: cor }}
    />
  );
}

export function Home() {
  const corCumpridos = token("--color-accent");
  const corPrevistos = token("--color-status-ok");
  const corBorda = token("--color-border");
  const corTexto = token("--color-ink-muted");

  const estagios = [
    {
      rotulo: "Petição inicial",
      total: 15,
      pct: 36,
      cor: corCumpridos,
    },
    { rotulo: "Instrução", total: 13, pct: 31, cor: corPrevistos },
    {
      rotulo: "Sentença",
      total: 8,
      pct: 19,
      cor: token("--color-status-critico"),
    },
    {
      rotulo: "Recursal",
      total: 6,
      pct: 14,
      cor: token("--color-status-atencao"),
    },
  ];

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {kpis.map((kpi) => (
          <Kpi key={kpi.titulo} {...kpi} />
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="space-y-1">
              <CardTitle>Prazos do ano</CardTitle>
              <CardDescription>Cumpridos vs. previstos por mês</CardDescription>
            </div>
            <div className="text-ink-muted flex items-center gap-4 text-14">
              <span className="flex items-center gap-2">
                <Ponto cor={corCumpridos} />
                Cumpridos
              </span>
              <span className="flex items-center gap-2">
                <Ponto cor={corPrevistos} />
                Previstos
              </span>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={prazosMes}
                  margin={{ top: 8, right: 8, left: -12, bottom: 0 }}
                >
                  <defs>
                    <linearGradient
                      id="gradCumpridos"
                      x1="0"
                      y1="0"
                      x2="0"
                      y2="1"
                    >
                      <stop
                        offset="0%"
                        stopColor={corCumpridos}
                        stopOpacity={0.35}
                      />
                      <stop
                        offset="100%"
                        stopColor={corCumpridos}
                        stopOpacity={0}
                      />
                    </linearGradient>
                    <linearGradient
                      id="gradPrevistos"
                      x1="0"
                      y1="0"
                      x2="0"
                      y2="1"
                    >
                      <stop
                        offset="0%"
                        stopColor={corPrevistos}
                        stopOpacity={0.18}
                      />
                      <stop
                        offset="100%"
                        stopColor={corPrevistos}
                        stopOpacity={0}
                      />
                    </linearGradient>
                  </defs>
                  <CartesianGrid
                    stroke={corBorda}
                    strokeDasharray="3 3"
                    vertical={false}
                  />
                  <XAxis
                    dataKey="mes"
                    tickLine={false}
                    axisLine={false}
                    tick={{ fill: corTexto, fontSize: 12 }}
                  />
                  <YAxis
                    tickLine={false}
                    axisLine={false}
                    tick={{ fill: corTexto, fontSize: 12 }}
                    width={44}
                  />
                  <Tooltip
                    content={<DicaGrafico />}
                    cursor={{ stroke: corBorda }}
                  />
                  <Area
                    type="monotone"
                    dataKey="previstos"
                    name="Previstos"
                    stroke={corPrevistos}
                    strokeWidth={2}
                    fill="url(#gradPrevistos)"
                  />
                  <Area
                    type="monotone"
                    dataKey="cumpridos"
                    name="Cumpridos"
                    stroke={corCumpridos}
                    strokeWidth={2}
                    fill="url(#gradCumpridos)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="space-y-1">
              <CardTitle>Estágios dos processos</CardTitle>
              <CardDescription>Distribuição por estágio</CardDescription>
            </div>
          </CardHeader>
          <CardContent className="space-y-5">
            {estagios.map((estagio) => (
              <div key={estagio.rotulo} className="space-y-2">
                <div className="flex items-center justify-between text-14">
                  <span className="font-medium">{estagio.rotulo}</span>
                  <span className="text-ink-muted tabular-nums">
                    {estagio.total}
                    <span className="text-ink ml-2 font-semibold">
                      {estagio.pct}%
                    </span>
                  </span>
                </div>
                <div className="bg-surface-muted h-2 overflow-hidden rounded-badge">
                  <div
                    className="h-full rounded-badge transition-all"
                    style={{
                      width: `${estagio.pct}%`,
                      backgroundColor: estagio.cor,
                    }}
                  />
                </div>
              </div>
            ))}
            <div className="border-border flex items-center justify-between border-t pt-4">
              <p className="text-14 text-ink-muted">Total de processos</p>
              <p className="text-28 font-semibold tabular-nums">42</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <div className="space-y-1">
              <CardTitle>Prazos recentes</CardTitle>
              <CardDescription>Últimas movimentações</CardDescription>
            </div>
            <NavLink
              to="/prazos"
              className="text-primary hover:text-primary-hover inline-flex items-center gap-1 text-14 font-medium"
            >
              Ver todos
              <ArrowUpRight className="size-4" aria-hidden="true" />
            </NavLink>
          </CardHeader>
          <CardContent>
            <ul className="divide-border divide-y">
              {prazosRecentes.map((prazo) => (
                <li key={prazo.id} className="flex items-center gap-4 py-4">
                  <span className="bg-surface-muted text-ink flex size-10 shrink-0 items-center justify-center rounded-input text-14 font-semibold">
                    {prazo.inicial}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-14 font-semibold">
                      {prazo.titulo}
                    </p>
                    <p className="text-ink-muted truncate text-14">
                      {prazo.sub}
                    </p>
                  </div>
                  <div className="shrink-0 text-right">
                    <p className="text-14 font-medium tabular-nums">
                      {prazo.data}
                    </p>
                    <span className="mt-1 inline-block">
                      <Badge tone={prazo.tom}>{prazo.rotulo}</Badge>
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="space-y-1">
              <CardTitle>Próximos compromissos</CardTitle>
              <CardDescription>Agenda da semana</CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <ul className="divide-border divide-y">
              {compromissos.map((item) => (
                <li key={item.id} className="flex items-center gap-4 py-4">
                  <span className="border-border bg-surface-muted flex size-10 shrink-0 flex-col items-center justify-center rounded-input border leading-none">
                    <span className="text-14 font-semibold">{item.dia}</span>
                    <span className="text-12 text-ink-muted">{item.mes}</span>
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-14 font-semibold">
                      {item.titulo}
                    </p>
                    <p className="text-ink-muted truncate text-14">
                      {item.sub}
                    </p>
                  </div>
                  <div className="shrink-0 text-right">
                    <p className="text-14 font-semibold tabular-nums">
                      {item.hora}
                    </p>
                    <p className="text-ink-muted text-12">{item.tipo}</p>
                  </div>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
