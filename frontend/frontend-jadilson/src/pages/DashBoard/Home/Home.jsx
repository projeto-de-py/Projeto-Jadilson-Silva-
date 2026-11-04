import { useMemo, useState } from "react";
import { NavLink, useOutletContext } from "react-router-dom";
import { motion } from "motion/react";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
  IconArrowUpRight,
  IconFolderBadgePlus,
  IconPersonBadgePlus,
  IconFolder,
  IconClock,
  IconPerson2,
  IconHammer,
  IconDocument,
  IconXmark,
} from "symbols-react";
import { Avatar, Badge, Button, Card, Contador } from "@/components/ui";
import { ModalCadastrarCliente } from "@/components/modais/ModalCadastrarCliente";
import { ModalCadastrarProcesso } from "@/components/modais/ModalCadastrarProcesso";
import { AREAS, useArea } from "@/context/area-context";
import { useCarteira } from "@/data/escritorio";
import { classificar } from "@/lib/prazos";
import { spring } from "@/lib/motion";
import { cn } from "@/lib/cn";

function saudacao() {
  const hora = new Date().getHours();
  if (hora < 12) return "Bom dia";
  if (hora < 18) return "Boa tarde";
  return "Boa noite";
}

function normalizarTexto(texto = "") {
  return String(texto)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function correspondeArea(textoArea, areaSelecionada) {
  if (!areaSelecionada || areaSelecionada === "todas") return true;
  return normalizarTexto(textoArea).includes(normalizarTexto(areaSelecionada));
}

const pagina = {
  oculto: {},
  visivel: { transition: { staggerChildren: 0.06, delayChildren: 0.04 } },
};
const entrada = {
  oculto: { opacity: 0, y: 14 },
  visivel: { opacity: 1, y: 0, transition: spring.gentle },
};

const TOM_FASE = {
  "Petição inicial": "neutral",
  "Instrução": "primary",
  "Sentença": "atencao",
  "Recursal": "vencido",
  "Concluído": "ok",
};

const dataCurta = (iso) =>
  format(new Date(iso), "dd 'de' MMM · HH:mm", { locale: ptBR }).replace(".", "");

function CabecalhoCartao({ titulo, descricao, para, rotuloLink }) {
  return (
    <div className="flex items-start justify-between gap-4 p-6 pb-4 sm:px-7 sm:pt-6">
      <div>
        <h3 className="text-18 text-ink font-semibold tracking-tight">{titulo}</h3>
        <p className="text-13 text-ink-muted mt-1">{descricao}</p>
      </div>
      <NavLink
        to={para}
        className="squircle text-13 text-ink-muted hover:text-ink hover:bg-surface-muted inline-flex shrink-0 items-center gap-1.5 rounded-input px-3 py-1.5 font-medium transition-colors"
      >
        {rotuloLink}
        <IconArrowUpRight className="size-3.5" fill="currentColor" />
      </NavLink>
    </div>
  );
}

export function Home() {
  const { user } = useOutletContext();
  const { area, setArea } = useArea();
  const { processos: todosProcessos, prazos: todosPrazos, clientes: todosClientes } = useCarteira();
  const [modalCliente, setModalCliente] = useState(false);
  const [modalProcesso, setModalProcesso] = useState(false);

  const areaAtiva = AREAS.find((a) => a.id === area) ?? AREAS[0];

  const processosFiltrados = useMemo(
    () =>
      todosProcessos.filter(
        (proc) => correspondeArea(proc.area, area) || correspondeArea(proc.tipoAcao, area),
      ),
    [todosProcessos, area],
  );

  const idsCasosVisiveis = useMemo(
    () => new Set(processosFiltrados.map((p) => p.id)),
    [processosFiltrados],
  );

  const prazosAbertos = useMemo(
    () => todosPrazos.filter((p) => !p.cumprido),
    [todosPrazos],
  );

  const prazosFiltrados = useMemo(
    () =>
      area === "todas"
        ? prazosAbertos
        : prazosAbertos.filter(
            (p) =>
              idsCasosVisiveis.has(p.casoId) ||
              correspondeArea(p.area, area) ||
              correspondeArea(p.titulo, area),
          ),
    [area, prazosAbertos, idsCasosVisiveis],
  );

  const processos = useMemo(() => {
    return processosFiltrados
      .map((proc) => {
        const prazos = prazosFiltrados
          .filter((p) => p.casoId === proc.id || p.processo === proc.numero)
          .sort((a, b) => a.diasRestantes - b.diasRestantes);
        const proximo = prazos[0];
        return { ...proc, proximo, situacao: proximo ? classificar(proximo.diasRestantes) : null };
      })
      .sort((a, b) => (a.proximo?.diasRestantes ?? 999) - (b.proximo?.diasRestantes ?? 999));
  }, [processosFiltrados, prazosFiltrados]);

  const prazosOrdenados = useMemo(
    () =>
      [...prazosFiltrados]
        .sort((a, b) => a.diasRestantes - b.diasRestantes)
        .slice(0, 6)
        .map((p) => ({ ...p, ...classificar(p.diasRestantes) })),
    [prazosFiltrados],
  );

  const clientes = useMemo(() => {
    if (area === "todas") {
      return todosClientes.map((c) => ({
        id: c.id,
        nome: c.nome,
        processos: c.processosAtivos,
        areas: c.areas?.length ? c.areas : ["Cliente cadastrado"],
      }));
    }
    return todosClientes
      .filter((c) => c.areas?.some((a) => correspondeArea(a, area)))
      .map((c) => ({
        id: c.id,
        nome: c.nome,
        processos: c.processosAtivos,
        areas: c.areas?.length ? c.areas : [areaAtiva.rotulo],
      }));
  }, [todosClientes, area, areaAtiva.rotulo]);

  const urgentes = prazosFiltrados.filter((p) => p.diasRestantes <= 0).length;
  const pertoDeVencer = prazosFiltrados.filter((p) => p.diasRestantes > 0 && p.diasRestantes <= 3).length;

  const atalhos = [
    { para: "/prazos", rotulo: "Prazos vencidos ou para hoje", valor: urgentes, icone: IconClock, destaque: urgentes > 0 },
    { para: "/prazos", rotulo: "Perto de vencer (até 3 dias)", valor: pertoDeVencer, icone: IconHammer },
    { para: "/processos", rotulo: "Processos ativos", valor: processosFiltrados.length, icone: IconFolder },
    { para: "/clientes", rotulo: "Clientes ativos", valor: clientes.length, icone: IconPerson2 },
  ];

  return (
    <motion.div className="space-y-9" variants={pagina} initial="oculto" animate="visivel">
      {/* Cabeçalho principal */}
      <motion.div
        variants={entrada}
        className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between"
      >
        <div className="space-y-1.5">
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="font-heading text-28 font-bold tracking-tight text-ink">
              {saudacao()}, Dr. {user.nome}
            </h2>
            {area !== "todas" && (
              <button
                type="button"
                onClick={() => setArea("todas")}
                aria-label={`Remover filtro de área ${areaAtiva.rotulo}`}
                className="border-border bg-surface-muted hover:border-primary/40 text-ink inline-flex items-center gap-2 rounded-badge border px-3 py-1 text-12 font-medium transition-colors"
              >
                <span className={cn("size-2 rounded-full", areaAtiva.cor)} aria-hidden="true" />
                {areaAtiva.rotulo}
                <IconXmark className="text-ink-muted size-3" fill="currentColor" />
              </button>
            )}
          </div>
          <p className="text-14 text-ink-muted">
            Acesso rápido a clientes, prazos e processos salvos no banco de dados.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <Button variant="secondary" onClick={() => setModalCliente(true)} className="gap-2">
            <IconPersonBadgePlus className="size-4 text-accent" fill="currentColor" />
            Novo Cliente
          </Button>
          <Button variant="primary" onClick={() => setModalProcesso(true)} className="gap-2">
            <IconFolderBadgePlus className="size-4" fill="currentColor" />
            Novo Processo
          </Button>
        </div>
      </motion.div>

      {/* Atalhos KPI com contagem animada por mola (@react-spring/web) */}
      <motion.ul variants={entrada} className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
        {atalhos.map((a) => (
          <li key={a.rotulo}>
            <NavLink to={a.para} className="group block rounded-card focus-visible:outline-none">
              <Card interactive className="relative flex items-center gap-4 p-6">
                <span
                  className={cn(
                    "bg-surface-muted flex size-12 shrink-0 items-center justify-center rounded-badge transition-colors",
                    a.destaque ? "text-status-vencido" : "text-accent group-hover:text-ink",
                  )}
                >
                  <a.icone className="size-5" fill="currentColor" />
                </span>
                <span className="min-w-0 flex-1">
                  <Contador
                    valor={a.valor}
                    className="font-heading text-28 text-ink block leading-none font-bold tabular-nums"
                  />
                  <span className="text-13 text-ink-muted mt-1.5 block leading-snug">{a.rotulo}</span>
                </span>
                <IconArrowUpRight
                  fill="currentColor"
                  aria-hidden="true"
                  className="text-ink-muted/40 group-hover:text-ink size-4 shrink-0 transition-transform duration-fast group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
                />
              </Card>
            </NavLink>
          </li>
        ))}
      </motion.ul>

      {/* Painel de processos */}
      <motion.div variants={entrada}>
        <Card className="overflow-hidden">
          <CabecalhoCartao
            titulo="Painel de processos"
            descricao="Fase atual e o próximo prazo de cada processo."
            para="/processos"
            rotuloLink="Ver processos"
          />
          {processos.length === 0 ? (
            <div className="border-t border-border px-6 py-10 text-center sm:px-7">
              <p className="text-14 font-medium text-ink">Nenhum processo cadastrado ainda</p>
              <p className="text-13 text-ink-muted mt-1">
                Clique em &ldquo;Novo Processo&rdquo; no topo para registrar o primeiro caso no banco de dados.
              </p>
            </div>
          ) : (
            <ul className="divide-border divide-y border-t border-border">
              {processos.map((proc) => (
                <li key={proc.id}>
                  <NavLink
                    to="/processos"
                    className="hover:bg-surface-muted/60 grid items-center gap-4 px-6 py-4.5 transition-colors sm:px-7 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)_minmax(0,1.2fr)]"
                  >
                    <div className="min-w-0 space-y-0.5">
                      <p className="text-14 text-ink truncate font-semibold">{proc.cliente}</p>
                      <p className="text-12 text-ink-muted tabular-nums truncate">{proc.numero}</p>
                      <p className="text-12 text-ink-muted truncate">{proc.vara}</p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2.5">
                      <Badge tone={TOM_FASE[proc.status] ?? "neutral"}>{proc.status}</Badge>
                      <span className="text-12 text-ink-muted">Aberto em {proc.criadoEm}</span>
                    </div>
                    {proc.proximo ? (
                      <div className="flex items-center justify-between gap-4 lg:justify-end">
                        <div className="min-w-0 lg:text-right">
                          <p className="text-13 text-ink truncate font-medium">{proc.proximo.titulo}</p>
                          <p className="text-12 text-ink-muted tabular-nums mt-0.5">
                            {dataCurta(proc.proximo.dataLimite)}
                          </p>
                        </div>
                        <Badge tone={proc.situacao.tom} className="shrink-0">
                          {proc.situacao.rotulo}
                        </Badge>
                      </div>
                    ) : (
                      <p className="text-12 text-ink-muted lg:text-right">Sem prazo em aberto</p>
                    )}
                  </NavLink>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </motion.div>

      <div className="grid gap-6 xl:grid-cols-[1.3fr_1fr]">
        {/* Próximos prazos */}
        <motion.div variants={entrada}>
          <Card className="h-full overflow-hidden">
            <CabecalhoCartao
              titulo="Próximos prazos"
              descricao="Vencimentos e audiências em ordem de data."
              para="/prazos"
              rotuloLink="Ver prazos"
            />
            {prazosOrdenados.length === 0 ? (
              <div className="border-t border-border px-6 py-10 text-center sm:px-7">
                <p className="text-14 font-medium text-ink">Nenhum prazo pendente</p>
                <p className="text-13 text-ink-muted mt-1">
                  Os prazos vinculados aos processos aparecerão aqui por ordem de urgência.
                </p>
              </div>
            ) : (
              <ul className="divide-border divide-y border-t border-border">
                {prazosOrdenados.map((p) => (
                  <li key={p.id}>
                    <NavLink
                      to="/prazos"
                      className="hover:bg-surface-muted/60 flex items-center gap-4 px-6 py-4 transition-colors sm:px-7"
                    >
                      <span className="bg-surface-muted text-accent flex size-10 shrink-0 items-center justify-center rounded-badge">
                        {p.tipo === "Audiência" ? (
                          <IconHammer className="size-4" fill="currentColor" />
                        ) : (
                          <IconDocument className="size-4" fill="currentColor" />
                        )}
                      </span>
                      <div className="min-w-0 flex-1 space-y-0.5">
                        <p className="text-14 text-ink truncate font-semibold">{p.titulo}</p>
                        <p className="text-12 text-ink-muted truncate">
                          {p.cliente} · {dataCurta(p.dataLimite)}
                        </p>
                      </div>
                      <Badge tone={p.tom} className="shrink-0">
                        {p.rotulo}
                      </Badge>
                    </NavLink>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </motion.div>

        {/* Clientes */}
        <motion.div variants={entrada}>
          <Card className="h-full overflow-hidden">
            <CabecalhoCartao
              titulo="Clientes"
              descricao="Quem você atende e quantos processos tem."
              para="/clientes"
              rotuloLink="Ver clientes"
            />
            {clientes.length === 0 ? (
              <div className="border-t border-border px-6 py-10 text-center sm:px-7">
                <p className="text-14 font-medium text-ink">Nenhum cliente cadastrado</p>
                <p className="text-13 text-ink-muted mt-1">
                  Cadastre o primeiro cliente para vincular processos e contratos.
                </p>
              </div>
            ) : (
              <ul className="divide-border divide-y border-t border-border">
                {clientes.map((c) => (
                  <li key={c.id ?? c.nome}>
                    <NavLink
                      to="/clientes"
                      className="hover:bg-surface-muted/60 flex items-center gap-4 px-6 py-4 transition-colors sm:px-7"
                    >
                      <Avatar nome={c.nome} size="md" />
                      <div className="min-w-0 flex-1 space-y-0.5">
                        <p className="text-14 text-ink truncate font-semibold">{c.nome}</p>
                        <p className="text-12 text-ink-muted truncate">{[...c.areas].join(" · ")}</p>
                      </div>
                      <span className="text-12 text-ink-muted shrink-0 tabular-nums">
                        {c.processos} {c.processos === 1 ? "processo" : "processos"}
                      </span>
                    </NavLink>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </motion.div>
      </div>

      <ModalCadastrarCliente open={modalCliente} onOpenChange={setModalCliente} />
      <ModalCadastrarProcesso open={modalProcesso} onOpenChange={setModalProcesso} />
    </motion.div>
  );
}
