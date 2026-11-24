import { useCallback, useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import {
  IconCalendar,
  IconCheckmarkCircle,
  IconCheckmarkCircleFill,
  IconClock,
  IconDocument,
  IconExclamationmarkTriangle,
  IconHammer,
  IconMagnifyingglass,
  IconPlus,
  IconSquareAndPencil,
  IconTrash,
  IconXmark,
} from "symbols-react";
import {
  Card,
  Badge,
  Button,
  Input,
  Select,
  EmptyState,
  Modal,
  Field,
  Textarea,
  useToast,
} from "@/components/ui";
import { useArea } from "@/context/area-context";
import { useSessao } from "@/context/sessao";
import { mapearPrazoApi, notificarAtualizacaoDados, useCarteira } from "@/data/escritorio";
import { apiJson } from "@/lib/api";
import { classificar } from "@/lib/prazos";
import { cn } from "@/lib/cn";

// Teto do parametro `limite` da API de prazos (GET /api/prazos).
const LIMITE_PAGINA = 100;

// Tipos aceitos por `PrazoCreate`/`PrazoUpdate` (app/schemas/prazo.py).
const TIPOS_PRAZO = [
  { valor: "PROCESSUAL", rotulo: "Prazo processual" },
  { valor: "ADMINISTRATIVO", rotulo: "Administrativo" },
  { valor: "CONTRATUAL", rotulo: "Contratual" },
  { valor: "INTERNO", rotulo: "Interno" },
  { valor: "OUTRO", rotulo: "Outro" },
];

const PRIORIDADES = [
  { valor: "BAIXA", rotulo: "Baixa" },
  { valor: "MEDIA", rotulo: "Média" },
  { valor: "ALTA", rotulo: "Alta" },
  { valor: "URGENTE", rotulo: "Urgente" },
];

// Transicoes de fim de vida: rota propria no backend (nao ha PATCH /cumprido).
const TRANSICOES = {
  concluir: { ok: "Prazo concluído", falha: "Não foi possível concluir o prazo" },
  reabrir: { ok: "Prazo reaberto", falha: "Não foi possível reabrir o prazo" },
  cancelar: { ok: "Prazo cancelado", falha: "Não foi possível cancelar o prazo" },
};

function formatarData(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function normalizarTexto(texto = "") {
  return String(texto)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

const GRUPOS = [
  { id: "vencidos", titulo: "Vencidos", descricao: "Exigem atenção imediata", icone: IconExclamationmarkTriangle, cor: "text-status-vencido", barra: "bg-status-vencido" },
  { id: "hoje", titulo: "Vencem hoje", descricao: "Prioridade máxima do dia", icone: IconClock, cor: "text-status-hoje-ink", barra: "bg-status-hoje" },
  { id: "proximos", titulo: "Próximos dias", descricao: "Planeje-se com antecedência", icone: IconCalendar, cor: "text-primary", barra: "bg-primary" },
];

export function Prazos() {
  const { csrf } = useSessao();
  const { toast } = useToast();
  const { area } = useArea();
  const { processos } = useCarteira();

  // `brutos` guarda o PrazoOut exatamente como a API devolve (fonte da
  // verdade local); `prazos` abaixo e a versao ja casada com o caso para exibir.
  const [brutos, setBrutos] = useState([]);
  const [total, setTotal] = useState(0);
  const [paginaAtual, setPaginaAtual] = useState(1);
  const [carregando, setCarregando] = useState(true);
  const [falha, setFalha] = useState("");
  const [carregandoMais, setCarregandoMais] = useState(false);
  const [emTransicao, setEmTransicao] = useState(null);
  const [busca, setBusca] = useState("");
  const [filtroArea, setFiltroArea] = useState("TODAS");
  const [modal, setModal] = useState({ aberto: false, prazo: null });

  // Busca de página sem efeito colateral: quem chama aplica o resultado.
  const buscar = useCallback(async (pagina = 1) => {
    const res = await apiJson(`prazos?pagina=${pagina}&limite=${LIMITE_PAGINA}`);
    return {
      itens: Array.isArray(res?.itens) ? res.itens : [],
      total: Number(res?.total ?? 0),
    };
  }, []);

  // Recarga disparada por usuario (botao "Tentar novamente" e evento
  // `dados:atualizar`): seta o estado de carregamento antes de buscar.
  const recarregar = useCallback(async ({ suave = false } = {}) => {
    if (!suave) {
      setCarregando(true);
      setFalha("");
    }
    try {
      const { itens, total } = await buscar();
      setBrutos(itens);
      setTotal(total);
      setPaginaAtual(1);
      setFalha("");
    } catch (erro) {
      // Recarga em segundo plano falhou: mantem a lista atual na tela.
      if (!suave) {
        setBrutos([]);
        setTotal(0);
        setFalha(erro.message || "Não foi possível carregar os prazos.");
      }
    } finally {
      if (!suave) setCarregando(false);
    }
  }, [buscar]);

  useEffect(() => {
    let cancelado = false;
    // Carga inicial: `carregando` ja nasce `true` e o resultado e aplicado
    // nos callbacks da promise (mesmo padrao de `useCarteira`).
    buscar()
      .then(({ itens, total }) => {
        if (cancelado) return;
        setBrutos(itens);
        setTotal(total);
        setPaginaAtual(1);
        setFalha("");
      })
      .catch((erro) => {
        if (cancelado) return;
        setBrutos([]);
        setTotal(0);
        setFalha(erro.message || "Não foi possível carregar os prazos.");
      })
      .finally(() => {
        if (!cancelado) setCarregando(false);
      });

    // Outras telas (cadastro de caso com prazo, edicao de cliente...) avisam
    // que os dados mudaram; aqui apenas recarregamos do servidor.
    const handler = () => recarregar({ suave: true });
    window.addEventListener("dados:atualizar", handler);
    return () => {
      cancelado = true;
      window.removeEventListener("dados:atualizar", handler);
    };
  }, [buscar, recarregar]);

  const carregarMais = useCallback(async () => {
    setCarregandoMais(true);
    try {
      const proxima = paginaAtual + 1;
      const res = await apiJson(`prazos?pagina=${proxima}&limite=${LIMITE_PAGINA}`);
      const novos = Array.isArray(res?.itens) ? res.itens : [];
      setBrutos((atuais) => {
        const vistos = new Set(atuais.map((p) => p.id));
        return [...atuais, ...novos.filter((p) => !vistos.has(p.id))];
      });
      setPaginaAtual(proxima);
    } catch (erro) {
      toast({
        tipo: "erro",
        titulo: "Não foi possível carregar mais prazos",
        descricao: erro.message || "Tente novamente em instantes.",
      });
    } finally {
      setCarregandoMais(false);
    }
  }, [paginaAtual, toast]);

  async function transicionar(prazo, acao) {
    if (emTransicao) return;
    setEmTransicao(prazo.id);
    try {
      const atualizado = await apiJson(`prazos/${prazo.id}/${acao}`, {
        method: "PATCH",
        csrf,
      });
      setBrutos((atuais) => atuais.map((p) => (p.id === prazo.id ? atualizado : p)));
      notificarAtualizacaoDados();
      toast({ tipo: "sucesso", titulo: TRANSICOES[acao].ok, descricao: prazo.titulo });
    } catch (erro) {
      toast({
        tipo: "erro",
        titulo: TRANSICOES[acao].falha,
        descricao: erro.message || "Tente novamente em instantes.",
      });
    } finally {
      setEmTransicao(null);
    }
  }

  function aplicarSalvamento(bruto, { edicao } = {}) {
    setBrutos((atuais) =>
      edicao
        ? atuais.map((p) => (p.id === bruto.id ? bruto : p))
        : [bruto, ...atuais.filter((p) => p.id !== bruto.id)],
    );
    if (!edicao) setTotal((atual) => atual + 1);
    notificarAtualizacaoDados();
  }

  const prazos = useMemo(
    () => brutos.map((p) => mapearPrazoApi(p, processos)),
    [brutos, processos],
  );

  const prazosProcessados = useMemo(() => {
    const termo = busca.toLowerCase();
    return prazos
      .map((p) => ({
        ...p,
        ...classificar(p.diasRestantes),
        icone: p.tipo === "PROCESSUAL" ? IconHammer : IconDocument,
      }))
      .filter((p) => {
        const matchBusca =
          p.titulo.toLowerCase().includes(termo) ||
          normalizarTexto(p.cliente).includes(normalizarTexto(termo)) ||
          p.processo.toLowerCase().includes(termo);
        const matchAreaLocal = filtroArea === "TODAS" || p.area === filtroArea;
        const matchAreaGlobal =
          !area ||
          area === "todas" ||
          normalizarTexto(p.area).includes(normalizarTexto(area));
        return matchBusca && matchAreaLocal && matchAreaGlobal;
      })
      .sort((a, b) => a.diasRestantes - b.diasRestantes);
  }, [prazos, busca, filtroArea, area]);

  const abertos = prazosProcessados.filter((p) => p.emAberto);
  const porGrupo = (id) => abertos.filter((p) => p.grupo === id);
  const concluidos = prazosProcessados.filter((p) => p.cumprido);
  const cancelados = prazosProcessados.filter((p) => p.cancelado);

  const totalFiltrado = prazosProcessados.length;
  const progresso =
    totalFiltrado > 0 ? Math.round((concluidos.length / totalFiltrado) * 100) : 0;

  const pendencias = total > brutos.length;

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-heading text-24 font-bold tracking-tight text-ink">Central de Prazos</h2>
          <p className="text-14 text-ink-muted">
            Prazos e processos salvos no banco de dados e ordenados por urgência.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2.5">
          <Button
            variant="primary"
            onClick={() => setModal({ aberto: true, prazo: null })}
            className="shrink-0 gap-2"
          >
            <IconPlus className="size-4" fill="currentColor" />
            Novo Prazo
          </Button>
        </div>
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
            <p className="text-13 text-ink-muted">Cumpridos</p>
            <IconCheckmarkCircleFill className="size-4 text-status-ok" fill="currentColor" />
          </div>
          <p className="font-heading text-28 mt-2 font-bold tabular-nums text-ink">
            {concluidos.length}<span className="text-16 text-ink-muted font-medium"> / {totalFiltrado}</span>
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

      {carregando ? (
        <p className="text-14 text-ink-muted py-12 text-center">Carregando prazos…</p>
      ) : falha ? (
        <EmptyState
          icon={IconExclamationmarkTriangle}
          titulo="Não foi possível carregar os prazos"
          descricao={falha}
          acao={
            <Button variant="secondary" onClick={() => recarregar()}>
              Tentar novamente
            </Button>
          }
        />
      ) : prazosProcessados.length === 0 ? (
        <EmptyState
          icon={IconClock}
          titulo="Nenhum prazo encontrado"
          descricao={
            busca
              ? "Nenhum prazo corresponde aos filtros aplicados."
              : "Nenhum prazo cadastrado no banco de dados. Clique em 'Novo Prazo' acima para adicionar o primeiro."
          }
        />
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
                      <LinhaPrazo
                        key={prazo.id}
                        prazo={prazo}
                        barra={g.barra}
                        ocupado={emTransicao === prazo.id}
                        aoConcluir={() => transicionar(prazo, "concluir")}
                        aoReabrir={() => transicionar(prazo, "reabrir")}
                        aoCancelar={() => transicionar(prazo, "cancelar")}
                        aoEditar={() => setModal({ aberto: true, prazo })}
                      />
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
                    <LinhaPrazo
                      key={prazo.id}
                      prazo={prazo}
                      barra="bg-status-ok"
                      ocupado={emTransicao === prazo.id}
                      aoConcluir={() => transicionar(prazo, "concluir")}
                      aoReabrir={() => transicionar(prazo, "reabrir")}
                      aoCancelar={() => transicionar(prazo, "cancelar")}
                      aoEditar={() => setModal({ aberto: true, prazo })}
                    />
                  ))}
                </AnimatePresence>
              </div>
            </section>
          )}

          {cancelados.length > 0 && (
            <section className="space-y-4">
              <div className="flex items-center gap-2">
                <IconXmark className="size-4 text-ink-muted" fill="currentColor" />
                <h3 className="text-14 font-semibold text-ink">Cancelados</h3>
              </div>
              <div className="space-y-2">
                <AnimatePresence initial={false}>
                  {cancelados.map((prazo) => (
                    <LinhaPrazo
                      key={prazo.id}
                      prazo={prazo}
                      barra="bg-surface-muted"
                      ocupado={emTransicao === prazo.id}
                      aoConcluir={() => transicionar(prazo, "concluir")}
                      aoReabrir={() => transicionar(prazo, "reabrir")}
                      aoCancelar={() => transicionar(prazo, "cancelar")}
                      aoEditar={() => setModal({ aberto: true, prazo })}
                    />
                  ))}
                </AnimatePresence>
              </div>
            </section>
          )}

          {pendencias && (
            <div className="flex flex-col items-center gap-2">
              <p className="text-12 text-ink-muted">
                Exibindo {brutos.length} de {total} prazos.
              </p>
              <Button variant="secondary" onClick={carregarMais} loading={carregandoMais}>
                Carregar mais prazos
              </Button>
            </div>
          )}
        </div>
      )}

      <ModalPrazo
        key={`${modal.aberto ? "aberto" : "fechado"}-${modal.prazo?.id ?? "novo"}`}
        aberto={modal.aberto}
        onOpenChange={(aberto) => setModal((atual) => ({ ...atual, aberto }))}
        prazo={modal.prazo}
        casos={processos}
        aoSalvar={aplicarSalvamento}
      />
    </div>
  );
}

/** Cadastro e edicao de prazo (mesmo contrato: PrazoCreate / PrazoUpdate). */
function ModalPrazo({ aberto, onOpenChange, prazo, casos, aoSalvar }) {
  const { csrf } = useSessao();
  const { toast } = useToast();
  const edicao = Boolean(prazo);

  const [salvando, setSalvando] = useState(false);
  const [casoId, setCasoId] = useState(() => (prazo?.casoId ? String(prazo.casoId) : ""));
  const [processoId, setProcessoId] = useState(() => (prazo?.processoId ? String(prazo.processoId) : ""));
  const [processosDoCaso, setProcessosDoCaso] = useState([]);
  // Na edicao o caso ja vem definido: o estado nasce em carregamento.
  const [carregandoProcessos, setCarregandoProcessos] = useState(() =>
    Boolean(prazo?.casoId),
  );
  const [titulo, setTitulo] = useState(() => prazo?.titulo || "");
  const [dataInicio, setDataInicio] = useState(() => prazo?.dataInicio || "");
  const [dataVencimento, setDataVencimento] = useState(() => prazo?.dataVencimento || "");
  const [tipo, setTipo] = useState(() => prazo?.tipo || "PROCESSUAL");
  const [prioridade, setPrioridade] = useState(() => prazo?.prioridade || "MEDIA");
  const [descricao, setDescricao] = useState(() => prazo?.descricao || "");
  const [observacoes, setObservacoes] = useState(() => prazo?.observacoes || "");

  // Processos judiciais do caso escolhido: opcional no prazo, mas precisam
  // pertencer ao MESMO caso (validado tambem no backend). O estado de
  // carregamento e setado no onChange (evento do usuario); aqui apenas
  // aplicamos a resposta nos callbacks da promise.
  useEffect(() => {
    if (!casoId) return undefined;
    let cancelado = false;
    apiJson(`casos/${casoId}/processos`)
      .then((lista) => {
        if (!cancelado) setProcessosDoCaso(Array.isArray(lista) ? lista : []);
      })
      .catch(() => {
        if (!cancelado) setProcessosDoCaso([]);
      })
      .finally(() => {
        if (!cancelado) setCarregandoProcessos(false);
      });
    return () => {
      cancelado = true;
    };
  }, [casoId]);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!titulo.trim() || !dataVencimento) return;

    if (dataInicio && dataInicio > dataVencimento) {
      toast({
        tipo: "erro",
        titulo: "Período inválido",
        descricao: "A data inicial não pode ser posterior à data de vencimento.",
      });
      return;
    }

    const casoEscolhido = Number(casoId || 0);
    if (!edicao && !casoEscolhido) {
      toast({
        tipo: "erro",
        titulo: "Cadastre um caso primeiro",
        descricao: "Um prazo precisa estar vinculado a um caso cadastrado.",
      });
      return;
    }

    const corpo = {
      titulo: titulo.trim(),
      descricao: descricao.trim() || null,
      tipo,
      data_inicio: dataInicio || null,
      data_vencimento: dataVencimento,
      prioridade,
      observacoes: observacoes.trim() || null,
    };

    setSalvando(true);
    try {
      let bruto;
      if (edicao) {
        // caso_id nao e alteravel; processo_id so vai quando muda (null desvincula).
        if ((processoId || null) !== (prazo.processoId ?? null)) {
          corpo.processo_id = processoId ? Number(processoId) : null;
        }
        bruto = await apiJson(`prazos/${prazo.id}`, {
          method: "PATCH",
          csrf,
          body: corpo,
        });
      } else {
        bruto = await apiJson("prazos", {
          method: "POST",
          csrf,
          body: {
            ...corpo,
            caso_id: casoEscolhido,
            ...(processoId ? { processo_id: Number(processoId) } : {}),
          },
        });
      }
      aoSalvar(bruto, { edicao });
      toast({
        tipo: "sucesso",
        titulo: edicao ? "Prazo atualizado" : "Prazo salvo no banco de dados",
        descricao: bruto.titulo,
      });
      onOpenChange(false);
    } catch (erro) {
      toast({
        tipo: "erro",
        titulo: edicao ? "Erro ao salvar alterações" : "Erro ao salvar prazo",
        descricao: erro.message || "Verifique os dados informados.",
      });
    } finally {
      setSalvando(false);
    }
  }

  return (
    <Modal
      open={aberto}
      onOpenChange={onOpenChange}
      titulo={edicao ? "Editar Prazo" : "Novo Prazo"}
      descricao={
        edicao
          ? "Ajuste as informações permitidas do prazo."
          : "Registre um prazo com a data informada manualmente pelo profissional."
      }
      className="max-w-lg"
      footer={
        <>
          <Button variant="ghost" type="button" onClick={() => onOpenChange(false)} disabled={salvando}>
            Cancelar
          </Button>
          <Button variant="primary" type="submit" form="form-prazo" loading={salvando}>
            {edicao ? "Salvar Alterações" : "Salvar Prazo"}
          </Button>
        </>
      }
    >
      <form id="form-prazo" onSubmit={handleSubmit} className="space-y-4 pt-2">
        <Field label="Caso vinculado" id="pz-caso">
          {edicao ? (
            <Input
              id="pz-caso"
              disabled
              value={`${prazo.cliente} · ${prazo.processo}`}
              readOnly
            />
          ) : (
            <Select
              id="pz-caso"
              value={casoId}
              onChange={(e) => {
                setCasoId(e.target.value);
                setProcessoId("");
                setProcessosDoCaso([]);
                setCarregandoProcessos(Boolean(e.target.value));
              }}
              disabled={salvando || casos.length === 0}
              placeholder={casos.length === 0 ? "Nenhum caso cadastrado" : "Selecione o caso"}
            >
              {casos.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.cliente} · {c.numero}
                </option>
              ))}
            </Select>
          )}
        </Field>

        <Field label="Processo judicial (opcional)" id="pz-processo">
          <Select
            id="pz-processo"
            value={processoId}
            onChange={(e) => setProcessoId(e.target.value)}
            disabled={salvando || (!edicao && !casoId) || carregandoProcessos}
            placeholder={
              carregandoProcessos
                ? "Carregando processos do caso…"
                : "Sem processo vinculado"
            }
          >
            <option value="">Sem processo vinculado</option>
            {processosDoCaso.map((p) => (
              <option key={p.id} value={p.id}>
                {p.numero_formatado || p.numero_processo}
              </option>
            ))}
          </Select>
        </Field>

        <Field label="Título do prazo" id="pz-titulo">
          <Input
            id="pz-titulo"
            placeholder="Ex.: Contestação - Revisional Bancária"
            value={titulo}
            onChange={(e) => setTitulo(e.target.value)}
            disabled={salvando}
            required
          />
        </Field>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field label="Data de início (opcional)" id="pz-inicio">
            <Input
              id="pz-inicio"
              type="date"
              value={dataInicio}
              onChange={(e) => setDataInicio(e.target.value)}
              disabled={salvando}
            />
          </Field>

          <Field label="Data de vencimento" id="pz-vencimento">
            <Input
              id="pz-vencimento"
              type="date"
              value={dataVencimento}
              onChange={(e) => setDataVencimento(e.target.value)}
              disabled={salvando}
              required
            />
          </Field>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field label="Tipo" id="pz-tipo">
            <Select id="pz-tipo" value={tipo} onChange={(e) => setTipo(e.target.value)} disabled={salvando}>
              {TIPOS_PRAZO.map((t) => (
                <option key={t.valor} value={t.valor}>
                  {t.rotulo}
                </option>
              ))}
            </Select>
          </Field>

          <Field label="Prioridade" id="pz-prioridade">
            <Select
              id="pz-prioridade"
              value={prioridade}
              onChange={(e) => setPrioridade(e.target.value)}
              disabled={salvando}
            >
              {PRIORIDADES.map((p) => (
                <option key={p.valor} value={p.valor}>
                  {p.rotulo}
                </option>
              ))}
            </Select>
          </Field>
        </div>

        <Field label="Descrição (opcional)" id="pz-descricao">
          <Textarea
            id="pz-descricao"
            rows={2}
            placeholder="Detalhes sobre documentos ou providências necessárias..."
            value={descricao}
            onChange={(e) => setDescricao(e.target.value)}
            disabled={salvando}
          />
        </Field>

        <Field label="Observações internas (opcional)" id="pz-observacoes">
          <Textarea
            id="pz-observacoes"
            rows={2}
            placeholder="Anotações de equipe, protocolos, próximos passos..."
            value={observacoes}
            onChange={(e) => setObservacoes(e.target.value)}
            disabled={salvando}
          />
        </Field>
      </form>
    </Modal>
  );
}

function LinhaPrazo({
  prazo,
  barra,
  ocupado = false,
  aoConcluir,
  aoReabrir,
  aoCancelar,
  aoEditar,
}) {
  const emAberto = prazo.emAberto;
  // Em aberto o badge mantem a urgencia da tela; finalizados mostram o status.
  const situacao = emAberto ? prazo.rotulo : prazo.statusRotulo;
  const tom = prazo.cancelado
    ? "neutral"
    : prazo.cumprido
      ? "cumprido"
      : prazo.tom;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.98 }}
      transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
    >
      <Card
        className={cn(
          "relative flex flex-col gap-4 overflow-hidden p-4 pl-6 transition-colors hover:border-primary/40 sm:flex-row sm:items-center",
          !emAberto && "opacity-70",
        )}
      >
        <span className={cn("absolute inset-y-0 left-0 w-1", barra)} />
        <button
          type="button"
          onClick={emAberto ? aoConcluir : aoReabrir}
          disabled={ocupado}
          aria-label={emAberto ? "Concluir prazo" : "Reabrir prazo"}
          aria-pressed={!emAberto}
          title={emAberto ? "Concluir prazo" : "Reabrir prazo"}
          className="text-ink-muted hover:text-status-ok shrink-0 transition-colors disabled:cursor-not-allowed disabled:opacity-50"
        >
          {emAberto ? (
            <IconCheckmarkCircle className="size-6" fill="currentColor" />
          ) : prazo.cancelado ? (
            <IconXmark className="size-6" fill="currentColor" />
          ) : (
            <IconCheckmarkCircleFill className="size-6 text-status-ok" fill="currentColor" />
          )}
        </button>

        <div className="min-w-0 flex-1">
          <p className={cn("text-14 font-semibold text-ink truncate", prazo.cumprido && "line-through")}>
            {prazo.titulo}
          </p>
          <p className="text-12 text-ink-muted truncate">
            <span className="text-ink font-medium">{prazo.cliente}</span> · {prazo.processo}
          </p>
          <p className="text-12 text-ink-muted/80 flex items-center gap-2 truncate">
            <prazo.icone className="size-3" fill="currentColor" />
            {prazo.vara} · {prazo.tipoRotulo}
          </p>
        </div>

        <div className="flex shrink-0 flex-col items-start gap-1.5 sm:items-end">
          <Badge tone={tom}>{situacao}</Badge>
          <span className="text-12 font-medium text-ink-muted tabular-nums">
            {formatarData(prazo.dataVencimento)}
          </span>
          {emAberto && <span className="text-11 text-ink-muted">{prazo.detalhe}</span>}

          {emAberto && (
            <div className="mt-1 flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={aoEditar}
                disabled={ocupado}
                className="text-11 text-ink-muted hover:text-ink inline-flex items-center gap-1 transition-colors disabled:opacity-50"
              >
                <IconSquareAndPencil className="size-3" fill="currentColor" />
                Editar
              </button>
              <button
                type="button"
                onClick={aoCancelar}
                disabled={ocupado}
                className="text-11 text-ink-muted hover:text-status-vencido inline-flex items-center gap-1 transition-colors disabled:opacity-50"
              >
                <IconTrash className="size-3" fill="currentColor" />
                Cancelar
              </button>
            </div>
          )}
        </div>
      </Card>
    </motion.div>
  );
}
