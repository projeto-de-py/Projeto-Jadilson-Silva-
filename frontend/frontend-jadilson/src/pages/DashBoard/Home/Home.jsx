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
} from "symbols-react";
import { Avatar, Badge, Button, Card } from "@/components/ui";
import { ModalCadastrarCliente } from "@/components/modais/ModalCadastrarCliente";
import { ModalCadastrarProcesso } from "@/components/modais/ModalCadastrarProcesso";
import { PROCESSOS_INICIAIS, PRAZOS } from "@/data/escritorio";
import { classificar } from "@/lib/prazos";
import { cn } from "@/lib/cn";

function saudacao() {
  const hora = new Date().getHours();
  if (hora < 12) return "Bom dia";
  if (hora < 18) return "Boa tarde";
  return "Boa noite";
}

const pagina = {
  oculto: {},
  visivel: { transition: { staggerChildren: 0.06, delayChildren: 0.05 } },
};
const entrada = {
  oculto: { opacity: 0, y: 12 },
  visivel: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.22, 1, 0.36, 1] } },
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
    <div className="flex items-start justify-between gap-4 p-6 pb-4">
      <div>
        <h3 className="text-18 text-ink font-semibold">{titulo}</h3>
        <p className="text-13 text-ink-muted mt-1">{descricao}</p>
      </div>
      <NavLink to={para} className="text-13 text-primary hover:text-primary-hover inline-flex shrink-0 items-center gap-1 font-medium">
        {rotuloLink}
        <IconArrowUpRight className="size-3.5" fill="currentColor" />
      </NavLink>
    </div>
  );
}

export function Home() {
  const { user } = useOutletContext();
  const [modalCliente, setModalCliente] = useState(false);
  const [modalProcesso, setModalProcesso] = useState(false);

  // Cada processo com o próximo prazo (o mais urgente ainda em aberto).
  const processos = useMemo(() => {
    return PROCESSOS_INICIAIS.map((proc) => {
      const prazos = PRAZOS.filter((p) => p.processo === proc.numero).sort((a, b) => a.diasRestantes - b.diasRestantes);
      const proximo = prazos[0];
      return { ...proc, proximo, situacao: proximo ? classificar(proximo.diasRestantes) : null };
    }).sort((a, b) => (a.proximo?.diasRestantes ?? 999) - (b.proximo?.diasRestantes ?? 999));
  }, []);

  const prazosOrdenados = useMemo(
    () => [...PRAZOS].sort((a, b) => a.diasRestantes - b.diasRestantes).slice(0, 6).map((p) => ({ ...p, ...classificar(p.diasRestantes) })),
    [],
  );

  const clientes = useMemo(() => {
    const mapa = new Map();
    for (const p of PROCESSOS_INICIAIS) {
      const atual = mapa.get(p.cliente) ?? { nome: p.cliente, processos: 0, areas: new Set() };
      atual.processos += 1;
      atual.areas.add(p.tipoAcao.split(" - ")[0]);
      mapa.set(p.cliente, atual);
    }
    return [...mapa.values()];
  }, []);

  const urgentes = PRAZOS.filter((p) => p.diasRestantes <= 0).length;
  const pertoDeVencer = PRAZOS.filter((p) => p.diasRestantes > 0 && p.diasRestantes <= 3).length;

  const atalhos = [
    { para: "/prazos", rotulo: "Prazos vencidos ou para hoje", valor: urgentes, icone: IconClock, destaque: urgentes > 0 },
    { para: "/prazos", rotulo: "Perto de vencer (até 3 dias)", valor: pertoDeVencer, icone: IconHammer },
    { para: "/processos", rotulo: "Processos ativos", valor: PROCESSOS_INICIAIS.length, icone: IconFolder },
    { para: "/clientes", rotulo: "Clientes ativos", valor: clientes.length, icone: IconPerson2 },
  ];

  return (
    <motion.div className="space-y-8" variants={pagina} initial="oculto" animate="visivel">
      <motion.div variants={entrada} className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-heading text-28 font-bold tracking-tight text-ink">{saudacao()}, Dr. {user.nome}</h2>
          <p className="text-14 text-ink-muted mt-1">Acesso rápido a clientes, prazos e processos do escritório.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
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

      {/* Atalhos com contagem */}
      <motion.ul variants={entrada} className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {atalhos.map((a) => (
          <li key={a.rotulo}>
            <NavLink to={a.para} className="group block">
              <Card className="hover:border-primary/50 flex items-center gap-4 p-6 transition-colors">
                <span className={cn("bg-surface-muted flex size-12 shrink-0 items-center justify-center rounded-badge", a.destaque ? "text-status-vencido" : "text-accent")}>
                  <a.icone className="size-5" fill="currentColor" />
                </span>
                <span>
                  <span className="font-heading text-28 text-ink block leading-none font-bold tabular-nums">{a.valor}</span>
                  <span className="text-13 text-ink-muted mt-1 block">{a.rotulo}</span>
                </span>
              </Card>
            </NavLink>
          </li>
        ))}
      </motion.ul>

      {/* Painel de processos */}
      <motion.div variants={entrada}>
        <Card>
          <CabecalhoCartao titulo="Painel de processos" descricao="Fase atual e o próximo prazo de cada processo." para="/processos" rotuloLink="Ver processos" />
          <ul className="divide-border divide-y border-t border-border">
            {processos.map((proc) => (
              <li key={proc.id}>
                <NavLink to="/processos" className="hover:bg-surface-muted/50 grid items-center gap-4 px-6 py-4 transition-colors lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)_minmax(0,1.2fr)]">
                  <div className="min-w-0">
                    <p className="text-14 text-ink truncate font-semibold">{proc.cliente}</p>
                    <p className="text-12 text-ink-muted tabular-nums truncate">{proc.numero}</p>
                    <p className="text-12 text-ink-muted truncate">{proc.vara}</p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={TOM_FASE[proc.status] ?? "neutral"}>{proc.status}</Badge>
                    <span className="text-12 text-ink-muted">Aberto em {proc.criadoEm}</span>
                  </div>
                  {proc.proximo ? (
                    <div className="flex items-center justify-between gap-4 lg:justify-end">
                      <div className="min-w-0 lg:text-right">
                        <p className="text-13 text-ink truncate font-medium">{proc.proximo.titulo}</p>
                        <p className="text-12 text-ink-muted tabular-nums">{dataCurta(proc.proximo.dataLimite)}</p>
                      </div>
                      <Badge tone={proc.situacao.tom} className="shrink-0">{proc.situacao.rotulo}</Badge>
                    </div>
                  ) : (
                    <p className="text-12 text-ink-muted lg:text-right">Sem prazo em aberto</p>
                  )}
                </NavLink>
              </li>
            ))}
          </ul>
        </Card>
      </motion.div>

      <div className="grid gap-6 xl:grid-cols-[1.3fr_1fr]">
        {/* Próximos prazos */}
        <motion.div variants={entrada}>
          <Card className="h-full">
            <CabecalhoCartao titulo="Próximos prazos" descricao="Vencimentos e audiências em ordem de data." para="/prazos" rotuloLink="Ver prazos" />
            <ul className="divide-border divide-y border-t border-border">
              {prazosOrdenados.map((p) => (
                <li key={p.id}>
                  <NavLink to="/prazos" className="hover:bg-surface-muted/50 flex items-center gap-4 px-6 py-4 transition-colors">
                    <span className="bg-surface-muted text-accent flex size-10 shrink-0 items-center justify-center rounded-badge">
                      {p.tipo === "Audiência" ? <IconHammer className="size-4" fill="currentColor" /> : <IconDocument className="size-4" fill="currentColor" />}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-14 text-ink truncate font-semibold">{p.titulo}</p>
                      <p className="text-12 text-ink-muted truncate">{p.cliente} · {dataCurta(p.dataLimite)}</p>
                    </div>
                    <Badge tone={p.tom} className="shrink-0">{p.rotulo}</Badge>
                  </NavLink>
                </li>
              ))}
            </ul>
          </Card>
        </motion.div>

        {/* Clientes */}
        <motion.div variants={entrada}>
          <Card className="h-full">
            <CabecalhoCartao titulo="Clientes" descricao="Quem você atende e quantos processos tem." para="/clientes" rotuloLink="Ver clientes" />
            <ul className="divide-border divide-y border-t border-border">
              {clientes.map((c) => (
                <li key={c.nome}>
                  <NavLink to="/clientes" className="hover:bg-surface-muted/50 flex items-center gap-4 px-6 py-4 transition-colors">
                    <Avatar nome={c.nome} size="md" />
                    <div className="min-w-0 flex-1">
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
          </Card>
        </motion.div>
      </div>

      <ModalCadastrarCliente open={modalCliente} onOpenChange={setModalCliente} />
      <ModalCadastrarProcesso open={modalProcesso} onOpenChange={setModalProcesso} />
    </motion.div>
  );
}
