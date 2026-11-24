import { useCallback, useEffect, useMemo, useState } from "react";
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
import { useOutletContext } from "react-router-dom";
import {
  IconArrowUturnBackward,
  IconCalendar,
  IconCheckmarkCircle,
  IconChevronLeft,
  IconChevronRight,
  IconClock,
  IconMappin,
  IconPlus,
  IconSquareAndPencil,
  IconTextAlignleft,
  IconTrash,
  IconXmark,
} from "symbols-react";
import {
  Badge,
  Button,
  Drawer,
  EmptyState,
  Field,
  Input,
  Modal,
  Select,
  Textarea,
  useToast,
} from "@/components/ui";
import { HOJE } from "@/lib/prazos";
import { useCarteira } from "@/data/escritorio";
import { cn } from "@/lib/cn";
import { apiJson } from "@/lib/api";

/**
 * Agenda do escritório (Fase 6).
 *
 * Duas fontes de eventos, cada uma com seu contrato:
 * - Compromisso (`/api/compromissos`): estrutura principal. Cadastro, edição,
 *   status (cancelamento sem excluir histórico), histórico e filtros de
 *   período/responsável/status/tipo via BACKEND.
 * - EventoAgenda (`/api/agenda/eventos`): eventos legados compartilhados,
 *   preservados para leitura e exclusão (sem cadastro pela UI - a criação de
 *   compromissos passou a usar a estrutura Compromisso).
 *
 * Os filtros de período/responsável/status/tipo são enviados ao backend; a
 * lista legada (sem esses campos no contrato) é recortada localmente apenas
 * quando um filtro está ativo. Nenhum dado fictício, sem localStorage.
 */

// Visual por CÓDIGO (cobre tipos de Compromisso e de EventoAgenda).
const TIPOS = {
  AUDIENCIA: { rotulo: "Audiência", ponto: "bg-status-vencido", chip: "bg-status-vencido-soft text-status-vencido-ink", tom: "vencido" },
  AUDIENCIA_VIRTUAL: { rotulo: "Audiência Virtual", ponto: "bg-status-atencao", chip: "bg-status-atencao-soft text-status-atencao-ink", tom: "atencao" },
  REUNIAO: { rotulo: "Reunião", ponto: "bg-primary", chip: "bg-primary-soft text-ink", tom: "primary" },
  CONCILIACAO: { rotulo: "Conciliação", ponto: "bg-status-ok", chip: "bg-status-ok-soft text-status-ok-ink", tom: "ok" },
  DESPACHO: { rotulo: "Despacho", ponto: "bg-ink-muted", chip: "bg-surface-muted text-ink-muted", tom: "neutral" },
  ATENDIMENTO: { rotulo: "Atendimento", ponto: "bg-status-hoje", chip: "bg-status-hoje-soft text-status-hoje-ink", tom: "hoje" },
  DILIGENCIA: { rotulo: "Diligência", ponto: "bg-status-cumprido", chip: "bg-surface-muted text-ink-muted", tom: "neutral" },
  OUTRO: { rotulo: "Outro", ponto: "bg-ink-muted", chip: "bg-surface-muted text-ink-muted", tom: "neutral" },
};

// Tipos aceitos pelo schema CompromissoCreate/Update (Literal do backend).
const TIPOS_COMPROMISSO = ["AUDIENCIA", "REUNIAO", "ATENDIMENTO", "DILIGENCIA", "OUTRO"];

const STATUS = {
  AGENDADO: { rotulo: "Agendado", tom: "primary" },
  REALIZADO: { rotulo: "Realizado", tom: "ok" },
  CANCELADO: { rotulo: "Cancelado", tom: "neutral" },
};

const ROTULOS_HISTORICO = {
  CRIACAO: "Criação",
  ATUALIZACAO: "Atualização",
  CANCELAMENTO: "Cancelamento",
  MUDANCA_RESPONSAVEL: "Mudança de responsável",
};

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

const DIAS_SEMANA = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"];

// Paginação do /api/compromissos: teto de 10 páginas de 100 (1.000 itens);
// acima disso a UI avisa "Exibindo X de Y".
const LIMITE_PAGINA = 100;
const MAX_PAGINAS = 10;

function diasDoMes(ref) {
  return eachDayOfInterval({
    start: startOfWeek(startOfMonth(ref)),
    end: endOfWeek(endOfMonth(ref)),
  });
}

// Recorte temporal consultado ao backend por visão (yyyy-MM-dd, horário local).
function periodoDe(ref, visao) {
  if (visao === "dia") return { de: format(ref, "yyyy-MM-dd"), ate: format(ref, "yyyy-MM-dd") };
  if (visao === "semana") {
    return {
      de: format(startOfWeek(ref), "yyyy-MM-dd"),
      ate: format(endOfWeek(ref), "yyyy-MM-dd"),
    };
  }
  if (visao === "lista") {
    return {
      de: format(startOfMonth(ref), "yyyy-MM-dd"),
      ate: format(endOfMonth(ref), "yyyy-MM-dd"),
    };
  }
  // Mês: grade completa (inclui dias vizinhos exibidos na tela).
  return {
    de: format(startOfWeek(startOfMonth(ref)), "yyyy-MM-dd"),
    ate: format(endOfWeek(endOfMonth(ref)), "yyyy-MM-dd"),
  };
}

// CompromissoOut -> item de calendário.
function mapearCompromisso(c) {
  const inicio = new Date(`${c.data_inicio}`);
  const fim = new Date(`${c.data_fim}`);
  return {
    chave: `c-${c.id}`,
    fonte: "compromisso",
    id: c.id,
    titulo: c.titulo,
    tipoCodigo: c.tipo,
    data: inicio,
    dataFim: fim,
    duracao: Math.max(Math.round((fim - inicio) / 60000), 15),
    local: c.local || "",
    descricao: c.descricao || "",
    responsavelId: c.responsavel_id,
    responsavelNome: c.responsavel_nome,
    status: c.status,
    casoId: c.caso_id,
    processoId: c.processo_id,
    processoNumero: c.processo_numero,
    criadoPorId: c.criado_por,
  };
}

// EventoAgendaOut -> item de calendário (mesmo formato dos compromissos).
function mapearEventoLegado(e) {
  const inicio = new Date(`${e.inicio}`);
  return {
    chave: `e-${e.id}`,
    fonte: "evento",
    id: e.id,
    titulo: e.titulo,
    tipoCodigo: e.tipo,
    data: inicio,
    dataFim: new Date(inicio.getTime() + e.duracao * 60000),
    duracao: e.duracao,
    local: e.local || "",
    descricao: e.descricao || "",
    responsavelId: e.destinatario_id,
    responsavelNome: null,
    status: null,
    casoId: null,
    processoId: null,
    processoNumero: null,
    criadoPorId: e.criado_por_id,
  };
}

// `criado_em`/`atualizado_em` são UTC sem fuso no JSON: anexa "Z" para o
// navegador converter ao horário local na exibição.
function parseUtc(valor) {
  const texto = String(valor ?? "");
  if (!texto) return new Date(NaN);
  return new Date(/[zZ]|[+-]\d{2}:?\d{2}$/.test(texto) ? texto : `${texto}Z`);
}

// `CompromissoOut.processo_numero` vem somente com dígitos (CNJ normalizado);
// aqui só reaplica a pontuação para exibir.
function formatarCnj(valor) {
  const texto = String(valor ?? "");
  const digitos = texto.replace(/\D/g, "");
  if (digitos.length !== 20) return texto;
  return `${digitos.slice(0, 7)}-${digitos.slice(7, 9)}.${digitos.slice(9, 13)}.${digitos.slice(13, 14)}.${digitos.slice(14, 16)}.${digitos.slice(16, 20)}`;
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

function montarParams(periodo, filtros, pagina) {
  const params = new URLSearchParams({
    inicio_de: periodo.de,
    inicio_ate: periodo.ate,
    pagina: String(pagina),
    limite: String(LIMITE_PAGINA),
  });
  if (filtros.responsavelId) params.set("responsavel_id", filtros.responsavelId);
  if (filtros.status) params.set("status", filtros.status);
  if (filtros.tipo) params.set("tipo", filtros.tipo);
  return params.toString();
}

export function Agenda() {
  const { user, csrf } = useOutletContext();
  const { toast } = useToast();
  const { processos: casos } = useCarteira();

  const [ref, setRef] = useState(HOJE);
  const [visao, setVisao] = useState("mes");

  // Fonte 1: compromissos (backend, com filtros).
  const [compromissos, setCompromissos] = useState([]);
  const [totalCompromissos, setTotalCompromissos] = useState(0);
  const [carregandoPeriodo, setCarregandoPeriodo] = useState(true);
  const [falhaPeriodo, setFalhaPeriodo] = useState("");

  // Fonte 2: eventos legados (EventoAgenda, leitura/exclusão) e contribuidores.
  const [eventosLegados, setEventosLegados] = useState([]);
  const [contribuidores, setContribuidores] = useState([]);
  const [falhaBase, setFalhaBase] = useState("");
  const [carregandoBase, setCarregandoBase] = useState(true);

  const [filtros, setFiltros] = useState({ responsavelId: "", status: "", tipo: "" });
  const [ocultos, setOcultos] = useState(() => new Set());
  const [selecionado, setSelecionado] = useState(null);
  const [modal, setModal] = useState(null); // { modo: "criar"|"editar", compromisso?, dia?, hora? }

  const periodo = useMemo(() => periodoDe(ref, visao), [ref, visao]);
  const periodoChave = `${periodo.de}|${periodo.ate}|${filtros.responsavelId}|${filtros.status}|${filtros.tipo}`;

  // Carga base: contribuidores + eventos legados (uma vez; estado só em callback).
  useEffect(() => {
    let cancelado = false;
    Promise.all([apiJson("agenda/contribuidores"), apiJson("agenda/eventos")])
      .then(([listaContribuidores, listaEventos]) => {
        if (cancelado) return;
        setContribuidores(Array.isArray(listaContribuidores) ? listaContribuidores : []);
        setEventosLegados(Array.isArray(listaEventos) ? listaEventos.map(mapearEventoLegado) : []);
        setFalhaBase("");
      })
      .catch((falha) => {
        if (cancelado) return;
        setFalhaBase(falha.message || "Não foi possível carregar os contribuidores da agenda.");
      })
      .finally(() => {
        if (!cancelado) setCarregandoBase(false);
      });
    return () => {
      cancelado = true;
    };
  }, []);

  // Compromissos do período/filtros (backend). Quem navega/filtra seta o
  // carregamento antes; aqui só aplicamos a resposta nos callbacks.
  useEffect(() => {
    let cancelado = false;
    const pagina1 = apiJson(`compromissos?${montarParams(periodo, filtros, 1)}`);
    pagina1
      .then(async (primeira) => {
        const itens = Array.isArray(primeira?.itens) ? [...primeira.itens] : [];
        let total = Number(primeira?.total ?? itens.length);
        // Paginação em loop (teto MAX_PAGINAS) até esgotar o total.
        for (let pagina = 2; pagina <= MAX_PAGINAS && itens.length < total; pagina += 1) {
          const proxima = await apiJson(`compromissos?${montarParams(periodo, filtros, pagina)}`);
          const lote = Array.isArray(proxima?.itens) ? proxima.itens : [];
          if (lote.length === 0) break;
          itens.push(...lote);
          total = Number(proxima?.total ?? total);
        }
        return { itens, total };
      })
      .then(({ itens, total }) => {
        if (cancelado) return;
        setCompromissos(itens.map(mapearCompromisso));
        setTotalCompromissos(total);
        setFalhaPeriodo("");
      })
      .catch((falha) => {
        if (cancelado) return;
        setCompromissos([]);
        setTotalCompromissos(0);
        setFalhaPeriodo(falha.message || "Não foi possível carregar os compromissos.");
      })
      .finally(() => {
        if (!cancelado) setCarregandoPeriodo(false);
      });
    return () => {
      cancelado = true;
    };
    // periodoChave encapsula período + filtros (deps reais da consulta).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [periodoChave]);

  // Recarga global (botão "Tentar novamente"): refaz as duas fontes.
  const recarregar = useCallback(async () => {
    setCarregandoBase(true);
    setCarregandoPeriodo(true);
    setFalhaBase("");
    setFalhaPeriodo("");
    try {
      const [listaContribuidores, listaEventos] = await Promise.all([
        apiJson("agenda/contribuidores"),
        apiJson("agenda/eventos"),
      ]);
      setContribuidores(Array.isArray(listaContribuidores) ? listaContribuidores : []);
      setEventosLegados(Array.isArray(listaEventos) ? listaEventos.map(mapearEventoLegado) : []);
      setFalhaBase("");
    } catch (falha) {
      setFalhaBase(falha.message || "Não foi possível carregar os contribuidores da agenda.");
    } finally {
      setCarregandoBase(false);
    }
    try {
      const primeira = await apiJson(`compromissos?${montarParams(periodo, filtros, 1)}`);
      const itens = Array.isArray(primeira?.itens) ? [...primeira.itens] : [];
      let total = Number(primeira?.total ?? itens.length);
      for (let pagina = 2; pagina <= MAX_PAGINAS && itens.length < total; pagina += 1) {
        const proxima = await apiJson(`compromissos?${montarParams(periodo, filtros, pagina)}`);
        const lote = Array.isArray(proxima?.itens) ? proxima.itens : [];
        if (lote.length === 0) break;
        itens.push(...lote);
        total = Number(proxima?.total ?? total);
      }
      setCompromissos(itens.map(mapearCompromisso));
      setTotalCompromissos(total);
      setFalhaPeriodo("");
    } catch (falha) {
      setCompromissos([]);
      setTotalCompromissos(0);
      setFalhaPeriodo(falha.message || "Não foi possível carregar os compromissos.");
    } finally {
      setCarregandoPeriodo(false);
    }
  }, [periodo, filtros]);

  // Mescla compromissos + legados já filtrados (legados: recorte local mínimo).
  const itensVisiveis = useMemo(() => {
    const legados = eventosLegados.filter((e) => {
      if (filtros.status && e.status !== filtros.status) return false; // sem status no contrato
      if (filtros.tipo && e.tipoCodigo !== filtros.tipo) return false;
      if (filtros.responsavelId && e.responsavelId != null && e.responsavelId !== Number(filtros.responsavelId)) {
        return false;
      }
      return e.data >= new Date(`${periodo.de}T00:00:00`) && e.data <= new Date(`${periodo.ate}T23:59:59`);
    });
    return [...compromissos, ...legados].sort((a, b) => a.data - b.data);
  }, [compromissos, eventosLegados, filtros, periodo]);

  const visiveis = useMemo(() => itensVisiveis.filter((e) => !ocultos.has(e.tipoCodigo)), [itensVisiveis, ocultos]);
  const doDia = (dia) => visiveis.filter((e) => isSameDay(e.data, dia)).sort((a, b) => a.data - b.data);

  // Navegação: seta o carregamento só quando o recorte consultado muda.
  function irPara(novoRef) {
    const novo = periodoDe(novoRef, visao);
    if (novo.de !== periodo.de || novo.ate !== periodo.ate) setCarregandoPeriodo(true);
    setRef(novoRef);
  }

  function navegar(sentido) {
    const f = sentido > 0
      ? { mes: addMonths, semana: addWeeks, dia: addDays, lista: addMonths }
      : { mes: subMonths, semana: subWeeks, dia: subDays, lista: subMonths };
    irPara(f[visao](ref, 1));
  }

  function alternarVisao(novaVisao) {
    if (novaVisao === visao) return;
    const novo = periodoDe(ref, novaVisao);
    if (novo.de !== periodo.de || novo.ate !== periodo.ate) setCarregandoPeriodo(true);
    setVisao(novaVisao);
  }

  function mudarFiltro(campo, valor) {
    if (filtros[campo] === valor) return;
    setCarregandoPeriodo(true);
    setFiltros((atual) => ({ ...atual, [campo]: valor }));
  }

  function alternarTipo(codigo) {
    setOcultos((atual) => {
      const copia = new Set(atual);
      if (copia.has(codigo)) copia.delete(codigo);
      else copia.add(codigo);
      return copia;
    });
  }

  // ------------------------------------------------------------- escrita

  async function recarregarCompromissos() {
    const primeira = await apiJson(`compromissos?${montarParams(periodo, filtros, 1)}`);
    const itens = Array.isArray(primeira?.itens) ? [...primeira.itens] : [];
    let total = Number(primeira?.total ?? itens.length);
    for (let pagina = 2; pagina <= MAX_PAGINAS && itens.length < total; pagina += 1) {
      const proxima = await apiJson(`compromissos?${montarParams(periodo, filtros, pagina)}`);
      const lote = Array.isArray(proxima?.itens) ? proxima.itens : [];
      if (lote.length === 0) break;
      itens.push(...lote);
      total = Number(proxima?.total ?? total);
    }
    setCompromissos(itens.map(mapearCompromisso));
    setTotalCompromissos(total);
    setFalhaPeriodo("");
    setCarregandoPeriodo(false);
  }

  async function salvarCompromisso(corpo, { modo, compromissoId }) {
    const registro = modo === "editar"
      ? await apiJson(`compromissos/${compromissoId}`, { method: "PATCH", csrf, body: corpo })
      : await apiJson("compromissos", { method: "POST", csrf, body: corpo });
    await recarregarCompromissos();
    if (selecionado && compromissoId && selecionado.id === compromissoId && modo === "editar") {
      setSelecionado(mapearCompromisso(registro));
    }
    window.dispatchEvent(new CustomEvent("notificacoes:atualizar"));
    return registro;
  }

  async function mudarStatus(compromisso, novoStatus) {
    try {
      const registro = await apiJson(`compromissos/${compromisso.id}/status`, {
        method: "PATCH",
        csrf,
        body: { status: novoStatus },
      });
      await recarregarCompromissos();
      setSelecionado(mapearCompromisso(registro));
      toast({
        tipo: "sucesso",
        titulo: `Compromisso ${STATUS[novoStatus].rotulo.toLowerCase()}`,
        descricao: registro.titulo,
      });
      window.dispatchEvent(new CustomEvent("notificacoes:atualizar"));
    } catch (falha) {
      toast({
        tipo: "erro",
        titulo: "Não foi possível alterar o status",
        descricao: falha.message || "Tente novamente em instantes.",
      });
    }
  }

  async function excluirEventoLegado(item) {
    try {
      await apiJson(`agenda/eventos/${item.id}`, { method: "DELETE", csrf });
      setEventosLegados((prev) => prev.filter((evento) => evento.id !== item.id));
      setSelecionado(null);
      toast({ tipo: "sucesso", titulo: "Evento excluído", descricao: item.titulo });
    } catch (falha) {
      toast({
        tipo: "erro",
        titulo: "Não foi possível excluir o evento",
        descricao: falha.message || "Tente novamente em instantes.",
      });
    }
  }

  // Histórico do compromisso selecionado (somente leitura, sob demanda).
  // O carregamento é derivado da chave: o estado só muda nos callbacks.
  const [historico, setHistorico] = useState({ chave: null, itens: [], falha: false });

  useEffect(() => {
    if (!selecionado || selecionado.fonte !== "compromisso") return undefined;
    let cancelado = false;
    const chave = selecionado.chave;
    apiJson(`compromissos/${selecionado.id}/historico`)
      .then((lista) => {
        if (!cancelado) setHistorico({ chave, itens: Array.isArray(lista) ? lista : [], falha: false });
      })
      .catch(() => {
        if (!cancelado) setHistorico({ chave, itens: [], falha: true });
      });
    return () => {
      cancelado = true;
    };
  }, [selecionado]);

  function abrirNovo(dia, hora = 9) {
    const d = new Date(dia);
    d.setHours(hora, 0, 0, 0);
    setModal({
      modo: "criar",
      dia: format(d, "yyyy-MM-dd"),
      hora: format(d, "HH:mm"),
    });
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

  const carregando = carregandoBase || carregandoPeriodo;
  const falha = falhaBase || falhaPeriodo;
  const exibindoParcial = totalCompromissos > compromissos.length;

  return (
    <div className="space-y-6">
      {falha && (
        <div className="border-status-vencido bg-status-vencido-soft flex flex-wrap items-center justify-between gap-3 rounded-input border px-4 py-3">
          <p role="alert" className="text-13 text-status-vencido-ink">
            {falha}
          </p>
          <Button variant="secondary" onClick={() => recarregar()}>
            Tentar novamente
          </Button>
        </div>
      )}
      {carregando && (
        <p role="status" className="text-13 text-ink-muted">
          Carregando agenda...
        </p>
      )}
      {!carregando && exibindoParcial && (
        <p role="status" className="text-12 text-ink-muted">
          Exibindo {compromissos.length} de {totalCompromissos} compromissos deste recorte.
        </p>
      )}

      {/* Barra de ferramentas */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-4">
          <h2 className="font-heading text-24 font-bold tracking-tight text-ink whitespace-nowrap first-letter:uppercase">
            {titulo}
          </h2>
          <div className="flex items-center gap-1">
            <button type="button" aria-label="Anterior" onClick={() => navegar(-1)} className="text-ink-muted hover:bg-surface-muted hover:text-ink flex size-10 items-center justify-center rounded-input transition-colors">
              <IconChevronLeft className="size-4" fill="currentColor" />
            </button>
            <button type="button" onClick={() => irPara(HOJE)} className="text-13 text-ink hover:bg-surface-muted h-10 rounded-input px-4 font-medium transition-colors">
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
                onClick={() => alternarVisao(v.id)}
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
            Novo compromisso
          </Button>
        </div>
      </div>

      {/* Filtros via backend (período = visão atual) */}
      <div className="bg-surface border-border flex flex-wrap items-end gap-4 rounded-card border p-4">
        <Field label="Responsável" className="min-w-48 flex-1">
          <Select
            value={filtros.responsavelId}
            onChange={(e) => mudarFiltro("responsavelId", e.target.value)}
            aria-label="Filtrar por responsável"
          >
            <option value="">Todos</option>
            {contribuidores.map((pessoa) => (
              <option key={pessoa.id} value={String(pessoa.id)}>{pessoa.nome}</option>
            ))}
          </Select>
        </Field>
        <Field label="Status" className="min-w-40 flex-1">
          <Select
            value={filtros.status}
            onChange={(e) => mudarFiltro("status", e.target.value)}
            aria-label="Filtrar por status"
          >
            <option value="">Todos</option>
            {Object.entries(STATUS).map(([codigo, info]) => (
              <option key={codigo} value={codigo}>{info.rotulo}</option>
            ))}
          </Select>
        </Field>
        <Field label="Tipo" className="min-w-48 flex-1">
          <Select
            value={filtros.tipo}
            onChange={(e) => mudarFiltro("tipo", e.target.value)}
            aria-label="Filtrar por tipo"
          >
            <option value="">Todos</option>
            {TIPOS_COMPROMISSO.map((codigo) => (
              <option key={codigo} value={codigo}>{TIPOS[codigo].rotulo}</option>
            ))}
          </Select>
        </Field>
        {(filtros.responsavelId || filtros.status || filtros.tipo) && (
          <Button variant="ghost" onClick={() => { setCarregandoPeriodo(true); setFiltros({ responsavelId: "", status: "", tipo: "" }); }}>
            Limpar filtros
          </Button>
        )}
      </div>

      <div className="grid gap-6 xl:grid-cols-[256px_1fr]">
        {/* Lateral: mini calendário + calendários */}
        <aside className="grid gap-6 md:grid-cols-2 xl:block xl:space-y-6">
          <MiniCalendario ref_={ref} aoEscolher={irPara} eventos={visiveis} />

          <div className="bg-surface border-border rounded-card border p-4">
            <p className="text-12 text-ink-muted px-2 pb-2 font-medium">Calendários</p>
            <ul className="space-y-1">
              {Object.entries(TIPOS).map(([codigo, info]) => {
                const ativo = !ocultos.has(codigo);
                return (
                  <li key={codigo}>
                    <button
                      type="button"
                      onClick={() => alternarTipo(codigo)}
                      aria-pressed={ativo}
                      className="hover:bg-surface-muted flex w-full items-center gap-3 rounded-input px-2 py-2 text-left transition-colors"
                    >
                      <span className={cn("flex size-4 items-center justify-center rounded-[5px] border", ativo ? cn(info.ponto, "border-transparent") : "border-border")}>
                        {ativo && <span className="bg-bg size-1.5 rounded-full" />}
                      </span>
                      <span className={cn("text-13 flex-1", ativo ? "text-ink" : "text-ink-muted")}>{info.rotulo}</span>
                      <span className="text-11 text-ink-muted tabular-nums">{itensVisiveis.filter((e) => e.tipoCodigo === codigo).length}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        </aside>

        {/* Visões */}
        <div className="bg-surface border-border min-w-0 overflow-hidden rounded-card border">
          {!carregando && !falha && itensVisiveis.length === 0 ? (
            <EmptyState
              icon={IconCalendar}
              titulo="Nenhum compromisso neste período"
              descricao="Navegue para outro período ou cadastre o primeiro compromisso do escritório."
              acao={
                <Button variant="secondary" onClick={() => abrirNovo(ref)}>
                  Novo compromisso
                </Button>
              }
            />
          ) : (
            <>
              {visao === "mes" && <VisaoMes ref_={ref} doDia={doDia} aoCriar={abrirNovo} aoAbrir={setSelecionado} aoEscolherDia={(d) => { irPara(d); alternarVisao("dia"); }} />}
              {(visao === "semana" || visao === "dia") && (
                <VisaoHoras
                  dias={visao === "dia" ? [ref] : eachDayOfInterval({ start: startOfWeek(ref), end: endOfWeek(ref) })}
                  doDia={doDia}
                  aoCriar={abrirNovo}
                  aoAbrir={setSelecionado}
                />
              )}
              {visao === "lista" && <VisaoLista ref_={ref} visiveis={visiveis} aoAbrir={setSelecionado} />}
            </>
          )}
        </div>
      </div>

      {/* Detalhe do compromisso / evento legado */}
      <Drawer
        open={!!selecionado}
        onOpenChange={(v) => !v && setSelecionado(null)}
        titulo={selecionado?.titulo ?? "Compromisso"}
        footer={
          selecionado && selecionado.fonte === "compromisso" ? (
            <div className="flex w-full flex-wrap items-center justify-between gap-2">
              <Button
                variant="secondary"
                className="gap-2"
                onClick={() => setModal({ modo: "editar", compromisso: selecionado })}
              >
                <IconSquareAndPencil className="size-4" fill="currentColor" />
                Editar
              </Button>
              <div className="flex flex-wrap gap-2">
                {selecionado.status === "AGENDADO" && (
                  <>
                    <Button variant="secondary" className="gap-2" onClick={() => mudarStatus(selecionado, "REALIZADO")}>
                      <IconCheckmarkCircle className="size-4" fill="currentColor" />
                      Marcar realizado
                    </Button>
                    <Button variant="secondary" className="text-status-vencido-ink gap-2" onClick={() => mudarStatus(selecionado, "CANCELADO")}>
                      <IconXmark className="size-4" fill="currentColor" />
                      Cancelar
                    </Button>
                  </>
                )}
                {selecionado.status !== "AGENDADO" && (
                  <Button variant="secondary" className="gap-2" onClick={() => mudarStatus(selecionado, "AGENDADO")}>
                    <IconArrowUturnBackward className="size-4" fill="currentColor" />
                    Reabrir
                  </Button>
                )}
              </div>
            </div>
          ) : (
            selecionado && (selecionado.criadoPorId === user.id || user.administrador) && (
              <Button variant="secondary" className="gap-2 text-status-vencido-ink" onClick={() => excluirEventoLegado(selecionado)}>
                <IconTrash className="size-4" fill="currentColor" />
                Excluir evento
              </Button>
            )
          )
        }
      >
        {selecionado && (
          <div className="space-y-6">
            <div className="flex flex-wrap gap-2">
              <Badge tone={TIPOS[selecionado.tipoCodigo]?.tom ?? "neutral"}>
                {TIPOS[selecionado.tipoCodigo]?.rotulo ?? selecionado.tipoCodigo}
              </Badge>
              {selecionado.status && (
                <Badge tone={STATUS[selecionado.status]?.tom ?? "neutral"}>
                  {STATUS[selecionado.status]?.rotulo ?? selecionado.status}
                </Badge>
              )}
            </div>
            <dl className="space-y-4">
              <div className="flex items-start gap-4">
                <IconCalendar className="text-ink-muted mt-0.5 size-4 shrink-0" fill="currentColor" />
                <dd className="text-14 text-ink capitalize">
                  {format(selecionado.data, "EEEE, d 'de' MMMM 'de' yyyy", { locale: ptBR })}
                </dd>
              </div>
              <div className="flex items-start gap-4">
                <IconClock className="text-ink-muted mt-0.5 size-4 shrink-0" fill="currentColor" />
                <dd className="text-14 text-ink tabular-nums">
                  {format(selecionado.data, "HH:mm")} – {format(selecionado.dataFim, "HH:mm")}
                </dd>
              </div>
              {selecionado.local && (
                <div className="flex items-start gap-4">
                  <IconMappin className="text-ink-muted mt-0.5 size-4 shrink-0" fill="currentColor" />
                  <dd className="text-14 text-ink">{selecionado.local}</dd>
                </div>
              )}
              <div className="flex items-start gap-4">
                <dd className="text-14 text-ink-muted">
                  Responsável:{" "}
                  {selecionado.responsavelNome
                    ?? (selecionado.responsavelId == null
                      ? "Todos os contribuidores"
                      : contribuidores.find((pessoa) => pessoa.id === selecionado.responsavelId)?.nome ?? "Contribuidor")}
                </dd>
              </div>
              {selecionado.fonte === "compromisso" && selecionado.processoNumero && (
                <div className="flex items-start gap-4">
                  <dd className="text-14 text-ink-muted">Processo: {formatarCnj(selecionado.processoNumero)}</dd>
                </div>
              )}
              {selecionado.descricao && (
                <div className="flex items-start gap-4">
                  <IconTextAlignleft className="text-ink-muted mt-0.5 size-4 shrink-0" fill="currentColor" />
                  <dd className="text-14 text-ink-muted">{selecionado.descricao}</dd>
                </div>
              )}
            </dl>

            {selecionado.fonte === "compromisso" && (
              <section className="space-y-3">
                <h3 className="text-14 font-semibold text-ink">Histórico</h3>
                {historico.chave !== selecionado.chave ? (
                  <p role="status" className="text-13 text-ink-muted">Carregando histórico...</p>
                ) : historico.falha ? (
                  <p role="alert" className="text-13 text-status-vencido-ink">
                    Não foi possível carregar o histórico.
                  </p>
                ) : historico.itens.length === 0 ? (
                  <p className="text-13 text-ink-muted">Nenhuma alteração registrada.</p>
                ) : (
                  <ul className="divide-border space-y-2 divide-y">
                    {historico.itens.map((entrada) => (
                      <li key={entrada.id} className="flex flex-wrap items-baseline justify-between gap-2 py-2">
                        <span className="text-14 text-ink">
                          {ROTULOS_HISTORICO[entrada.operacao] ?? entrada.operacao}
                          {entrada.usuario_id && (
                            <span className="text-12 text-ink-muted">
                              {" · "}
                              {contribuidores.find((pessoa) => pessoa.id === entrada.usuario_id)?.nome ?? "Usuário"}
                            </span>
                          )}
                        </span>
                        <span className="text-12 text-ink-muted tabular-nums">
                          {format(parseUtc(entrada.criado_em), "dd/MM/yyyy HH:mm")}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            )}
          </div>
        )}
      </Drawer>

      {/* Cadastro / edição de compromisso */}
      {modal && (
        <ModalCompromisso
          modal={modal}
          onOpenChange={(aberto) => !aberto && setModal(null)}
          casos={casos}
          contribuidores={contribuidores}
          usuario={user}
          aoSalvar={salvarCompromisso}
        />
      )}
    </div>
  );
}

/**
 * Cadastro e edição de compromisso (CompromissoCreate / CompromissoUpdate).
 *
 * - Edição monta um PATCH por DIFF: só os campos alterados são enviados;
 *   `caso_id`/`processo_id` não são editáveis (schema `extra="forbid"`).
 * - Processos vêm de `GET /api/casos/{id}/processos` (o processo precisa
 *   pertencer ao caso informado - contrato do backend).
 */
function ModalCompromisso({ modal, onOpenChange, casos, contribuidores, usuario, aoSalvar }) {
  const { toast } = useToast();
  const edicao = modal.modo === "editar";
  const original = edicao ? modal.compromisso : null;

  const [salvando, setSalvando] = useState(false);
  const [tituloValor, setTitulo] = useState(() => original?.titulo ?? "");
  const [descricao, setDescricao] = useState(() => original?.descricao ?? "");
  const [tipo, setTipo] = useState(() => original?.tipoCodigo ?? "AUDIENCIA");
  const [local, setLocal] = useState(() => original?.local ?? "");
  const [diaInicio, setDiaInicio] = useState(() => (original ? format(original.data, "yyyy-MM-dd") : modal.dia));
  const [horaInicio, setHoraInicio] = useState(() => (original ? format(original.data, "HH:mm") : modal.hora));
  const [diaFim, setDiaFim] = useState(() => (original ? format(original.dataFim, "yyyy-MM-dd") : modal.dia));
  const [horaFim, setHoraFim] = useState(() => (original ? format(original.dataFim, "HH:mm") : "10:00"));
  const [responsavelId, setResponsavelId] = useState(() =>
    edicao ? String(original.responsavelId ?? usuario.id) : String(usuario.id),
  );
  const [casoId, setCasoId] = useState(() => (edicao ? String(original.casoId ?? "") : ""));
  const [processoId, setProcessoId] = useState(() => (edicao ? String(original.processoId ?? "") : ""));
  const [processosDoCaso, setProcessosDoCaso] = useState([]);
  const [carregandoProcessos, setCarregandoProcessos] = useState(false);

  // Processos do caso escolhido: carregamento setado no onChange (evento do
  // usuário); aqui apenas aplicamos a resposta nos callbacks da promise.
  useEffect(() => {
    if (edicao || !casoId) return undefined;
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
  }, [casoId, edicao]);

  async function handleSubmit(e) {
    e.preventDefault();
    const tituloTrim = tituloValor.trim();
    if (tituloTrim.length < 3) {
      toast({ tipo: "erro", titulo: "Título muito curto", descricao: "Informe ao menos 3 caracteres." });
      return;
    }
    const inicioIso = `${diaInicio}T${horaInicio}:00`;
    const fimIso = `${diaFim}T${horaFim}:00`;
    if (new Date(fimIso) <= new Date(inicioIso)) {
      toast({
        tipo: "erro",
        titulo: "Período inválido",
        descricao: "A data e hora final devem ser posteriores às iniciais.",
      });
      return;
    }
    if (!edicao && !casoId && !usuario.administrador) {
      toast({
        tipo: "erro",
        titulo: "Selecione um caso",
        descricao: "Compromissos sem caso são restritos ao advogado principal.",
      });
      return;
    }

    setSalvando(true);
    try {
      if (edicao) {
        // PATCH por diff: só o que mudou (preserva o restante no backend).
        const corpo = {};
        if (tituloTrim !== original.titulo) corpo.titulo = tituloTrim;
        if (descricao.trim() !== (original.descricao ?? "")) corpo.descricao = descricao.trim() || null;
        if (tipo !== original.tipoCodigo) corpo.tipo = tipo;
        if (inicioIso !== format(original.data, "yyyy-MM-dd'T'HH:mm':00'")) corpo.data_inicio = inicioIso;
        if (fimIso !== format(original.dataFim, "yyyy-MM-dd'T'HH:mm':00'")) corpo.data_fim = fimIso;
        if (local.trim() !== (original.local ?? "")) corpo.local = local.trim() || null;
        if (Number(responsavelId) !== (original.responsavelId ?? usuario.id)) {
          corpo.responsavel_id = Number(responsavelId);
        }
        if (Object.keys(corpo).length === 0) {
          toast({ tipo: "sucesso", titulo: "Nenhuma alteração para salvar", descricao: original.titulo });
          onOpenChange(false);
          return;
        }
        await aoSalvar(corpo, { modo: "editar", compromissoId: original.id });
        toast({ tipo: "sucesso", titulo: "Compromisso atualizado", descricao: tituloTrim });
      } else {
        const corpo = {
          titulo: tituloTrim,
          descricao: descricao.trim() || null,
          tipo,
          data_inicio: inicioIso,
          data_fim: fimIso,
          local: local.trim() || null,
          ...(casoId ? { caso_id: Number(casoId) } : {}),
          ...(casoId && processoId ? { processo_id: Number(processoId) } : {}),
          ...(responsavelId && Number(responsavelId) !== usuario.id ? { responsavel_id: Number(responsavelId) } : {}),
        };
        await aoSalvar(corpo, { modo: "criar" });
        toast({ tipo: "sucesso", titulo: "Compromisso cadastrado", descricao: tituloTrim });
      }
      window.dispatchEvent(new CustomEvent("notificacoes:atualizar"));
      onOpenChange(false);
    } catch (falha) {
      toast({
        tipo: "erro",
        titulo: edicao ? "Erro ao editar compromisso" : "Erro ao cadastrar compromisso",
        descricao: falha.message || "Verifique os dados informados.",
      });
    } finally {
      setSalvando(false);
    }
  }

  return (
    <Modal
      open
      onOpenChange={onOpenChange}
      titulo={edicao ? "Editar compromisso" : "Novo compromisso"}
      descricao={
        edicao
          ? "Ajuste os campos do compromisso. O vínculo com caso e processo é preservado."
          : "Audiências, reuniões, atendimentos e diligências do escritório."
      }
      className="max-w-lg"
      footer={
        <>
          <Button variant="ghost" type="button" onClick={() => onOpenChange(false)} disabled={salvando}>
            Cancelar
          </Button>
          <Button variant="primary" type="submit" form="form-compromisso" loading={salvando}>
            {edicao ? "Salvar alterações" : "Cadastrar compromisso"}
          </Button>
        </>
      }
    >
      <form id="form-compromisso" onSubmit={handleSubmit} className="space-y-4 pt-2">
        <Field label="Título" id="cp-titulo">
          <Input
            id="cp-titulo"
            autoFocus
            required
            maxLength={160}
            value={tituloValor}
            onChange={(e) => setTitulo(e.target.value)}
            placeholder="Ex.: Audiência de conciliação"
          />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Tipo" id="cp-tipo">
            <Select id="cp-tipo" value={tipo} onChange={(e) => setTipo(e.target.value)}>
              {TIPOS_COMPROMISSO.map((codigo) => (
                <option key={codigo} value={codigo}>{TIPOS[codigo].rotulo}</option>
              ))}
            </Select>
          </Field>
          <Field label="Responsável" id="cp-responsavel">
            <Select id="cp-responsavel" value={responsavelId} onChange={(e) => setResponsavelId(e.target.value)}>
              <option value={String(usuario.id)}>Eu (padrão)</option>
              {contribuidores
                .filter((pessoa) => pessoa.id !== usuario.id)
                .map((pessoa) => (
                  <option key={pessoa.id} value={String(pessoa.id)}>{pessoa.nome}</option>
                ))}
            </Select>
          </Field>
          <Field label="Data inicial" id="cp-dia-inicio">
            <Input id="cp-dia-inicio" type="date" required value={diaInicio} onChange={(e) => setDiaInicio(e.target.value)} />
          </Field>
          <Field label="Hora inicial" id="cp-hora-inicio">
            <Input id="cp-hora-inicio" type="time" required value={horaInicio} onChange={(e) => setHoraInicio(e.target.value)} />
          </Field>
          <Field label="Data final" id="cp-dia-fim">
            <Input id="cp-dia-fim" type="date" required value={diaFim} onChange={(e) => setDiaFim(e.target.value)} />
          </Field>
          <Field label="Hora final" id="cp-hora-fim">
            <Input id="cp-hora-fim" type="time" required value={horaFim} onChange={(e) => setHoraFim(e.target.value)} />
          </Field>
        </div>

        {edicao ? (
          <p className="text-13 text-ink-muted">
            Caso e processo vinculados são preservados e não são editáveis nesta tela.
            {original.processoNumero ? ` Processo atual: ${formatarCnj(original.processoNumero)}.` : ""}
          </p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Caso relacionado (opcional)" id="cp-caso" hint="Compromissos sem caso ficam visíveis apenas para o advogado principal.">
              <Select
                id="cp-caso"
                value={casoId}
                onChange={(e) => {
                  setCasoId(e.target.value);
                  setProcessoId("");
                  setProcessosDoCaso([]);
                  setCarregandoProcessos(Boolean(e.target.value));
                }}
              >
                <option value="">Sem caso (agenda do escritório)</option>
                {casos.map((caso) => (
                  <option key={caso.id} value={String(caso.id)}>
                    {caso.numero} · {caso.cliente}
                  </option>
                ))}
              </Select>
            </Field>
            <Field
              label="Processo judicial (opcional)"
              id="cp-processo"
              hint={casoId ? "Somente processos do caso selecionado." : "Escolha um caso para vincular um processo."}
            >
              <Select
                id="cp-processo"
                value={processoId}
                disabled={!casoId || carregandoProcessos}
                onChange={(e) => setProcessoId(e.target.value)}
              >
                <option value="">
                  {carregandoProcessos ? "Carregando processos..." : "Sem processo"}
                </option>
                {processosDoCaso.map((processo) => (
                  <option key={processo.id} value={String(processo.id)}>
                    {processo.numero_formatado || processo.numero_processo}
                  </option>
                ))}
              </Select>
            </Field>
          </div>
        )}

        <Field label="Local" id="cp-local">
          <Input
            id="cp-local"
            maxLength={200}
            value={local}
            onChange={(e) => setLocal(e.target.value)}
            placeholder="Vara, escritório ou link da reunião"
          />
        </Field>
        <Field label="Descrição" id="cp-descricao">
          <Textarea
            id="cp-descricao"
            maxLength={4000}
            value={descricao}
            onChange={(e) => setDescricao(e.target.value)}
            placeholder="Observações, partes envolvidas, pauta..."
          />
        </Field>
      </form>
    </Modal>
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

function Chip({ evento, aoAbrir }) {
  const info = TIPOS[evento.tipoCodigo] ?? TIPOS.OUTRO;
  return (
    <button
      type="button"
      onClick={(e) => { e.stopPropagation(); aoAbrir(evento); }}
      className={cn(
        "text-12 flex w-full items-center gap-2 truncate rounded-[8px] px-2 py-1 text-left font-medium transition-opacity hover:opacity-80",
        info.chip,
        evento.status === "CANCELADO" && "line-through opacity-70",
      )}
    >
      <span className={cn("size-1.5 shrink-0 rounded-full", info.ponto)} />
      <span className="text-11 tabular-nums opacity-70">{format(evento.data, "HH:mm")}</span>
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
              aria-label={`Criar compromisso em ${format(dia, "d 'de' MMMM", { locale: ptBR })}`}
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
              {eventos.slice(0, 3).map((e) => <Chip key={e.chave} evento={e} aoAbrir={aoAbrir} />)}
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
                aria-label={`Criar compromisso às ${h}:00`}
                onClick={() => aoCriar(dia, h)}
                style={{ height: ALTURA_HORA }}
                className="border-border hover:bg-surface-muted/50 block w-full border-t transition-colors"
              />
            ))}
            {posicionar(doDia(dia)).map((e) => {
              const inicio = e.data.getHours() + e.data.getMinutes() / 60 - HORA_INICIO;
              if (inicio < 0 || inicio >= HORA_FIM - HORA_INICIO) return null;
              const info = TIPOS[e.tipoCodigo] ?? TIPOS.OUTRO;
              return (
                <button
                  key={e.chave}
                  type="button"
                  onClick={() => aoAbrir(e)}
                  className={cn(
                    "absolute overflow-hidden rounded-[10px] border-l-[3px] px-2 py-1 text-left transition-opacity hover:opacity-80",
                    info.chip,
                    "border-current",
                    e.status === "CANCELADO" && "line-through opacity-70",
                  )}
                  style={{
                    top: inicio * ALTURA_HORA + 1,
                    height: Math.max((e.duracao / 60) * ALTURA_HORA - 2, 24),
                    left: `calc(${(e.col / e.total) * 100}% + 2px)`,
                    width: `calc(${100 / e.total}% - 4px)`,
                  }}
                >
                  <p className="text-12 truncate font-semibold">{e.titulo}</p>
                  <p className="text-11 truncate tabular-nums opacity-70">
                    {format(e.data, "HH:mm")}{e.local ? ` · ${e.local}` : ""}
                  </p>
                  {e.responsavelNome && (
                    <p className="text-11 truncate opacity-70">{e.responsavelNome}</p>
                  )}
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
    return (
      <EmptyState
        icon={IconCalendar}
        titulo="Nenhum compromisso neste mês"
        descricao="Crie um compromisso ou ajuste os filtros e calendários."
      />
    );
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
            {g.itens.map((e) => {
              const info = TIPOS[e.tipoCodigo] ?? TIPOS.OUTRO;
              return (
                <li key={e.chave}>
                  <button
                    type="button"
                    onClick={() => aoAbrir(e)}
                    className="hover:bg-surface-muted flex w-full items-center gap-4 rounded-input p-2 text-left transition-colors"
                  >
                    <span className={cn("h-10 w-1 shrink-0 rounded-full", info.ponto)} />
                    <span className="text-13 text-ink-muted w-12 shrink-0 tabular-nums">{format(e.data, "HH:mm")}</span>
                    <span className="min-w-0 flex-1">
                      <span className={cn("text-14 block truncate font-medium", e.status === "CANCELADO" ? "text-ink-muted line-through" : "text-ink")}>
                        {e.titulo}
                      </span>
                      <span className="text-12 text-ink-muted block truncate">
                        {e.local || "Sem local definido"}
                        {e.responsavelNome ? ` · ${e.responsavelNome}` : ""}
                      </span>
                    </span>
                    <Badge tone={info.tom}>{info.rotulo}</Badge>
                    {e.status && (
                      <Badge tone={STATUS[e.status]?.tom ?? "neutral"}>
                        {STATUS[e.status]?.rotulo ?? e.status}
                      </Badge>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        </li>
      ))}
    </ul>
  );
}
