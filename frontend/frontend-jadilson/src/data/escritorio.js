import { useCallback, useEffect, useState } from "react";
import { apiJson } from "@/lib/api";

// Listas vazias por padrão — todos os dados reais vêm do banco SQLite via API.
export const PROCESSOS_INICIAIS = [];
export const PRAZOS = [];

const ROTULO_AREA = {
  BANCARIO: "Bancário",
  PREVIDENCIARIO: "Previdenciário",
  CONSUMIDOR: "Consumidor",
};

// Rótulos do contrato atual da API de prazos (`app/schemas/prazo.py`).
const ROTULO_TIPO_PRAZO = {
  PROCESSUAL: "Processual",
  ADMINISTRATIVO: "Administrativo",
  CONTRATUAL: "Contratual",
  INTERNO: "Interno",
  OUTRO: "Outro",
};

const ROTULO_STATUS_PRAZO = {
  PENDENTE: "Pendente",
  EM_ANDAMENTO: "Em andamento",
  CONCLUIDO: "Concluído",
  CANCELADO: "Cancelado",
};

/** Dias de hoje até `dataIso` (YYYY-MM-DD); negativo quando já venceu.

A data e sempre informada pelo profissional (a API calcula `vencido` no
servidor); aqui so se conta a diferenca para exibir a urgencia na tela. */
function diasAte(dataIso) {
  const [ano, mes, dia] = String(dataIso || "").slice(0, 10).split("-").map(Number);
  if (!ano || !mes || !dia) return 0;
  const alvo = Date.UTC(ano, mes - 1, dia);
  const agora = new Date();
  const hoje = Date.UTC(agora.getFullYear(), agora.getMonth(), agora.getDate());
  return Math.round((alvo - hoje) / 86400000);
}

const STATUS_PARA_ETAPA = {
  NOVO: "Petição inicial",
  AGUARDANDO_CLIENTE: "Petição inicial",
  EM_ANDAMENTO: "Instrução",
  AGUARDANDO_SENTENCA: "Sentença",
  SUSPENSO: "Recursal",
  CONCLUIDO: "Concluído",
};

export const ETAPA_PARA_STATUS_API = {
  "Petição inicial": "NOVO",
  "Instrução": "EM_ANDAMENTO",
  "Sentença": "AGUARDANDO_SENTENCA",
  "Recursal": "SUSPENSO",
  "Execução": "EM_ANDAMENTO",
  "Concluído": "CONCLUIDO",
};

// `ProcessoJudicial` tem enum de situacao PROPRIO (distinto do status do Caso).
// Usado ao criar o processo real via POST /api/casos/{id}/processos.
export const ETAPA_PARA_STATUS_PROCESSO = {
  "Petição inicial": "DISTRIBUIDO",
  "Instrução": "EM_ANDAMENTO",
  "Sentença": "AGUARDANDO_SENTENCA",
  "Recursal": "EM_ANDAMENTO",
  "Execução": "EM_ANDAMENTO",
  "Concluído": "BAIXADO",
};

export function extrairAreaCodigo(tipoAcao = "") {
  const texto = String(tipoAcao)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
  if (texto.includes("previdenciario")) return "PREVIDENCIARIO";
  if (texto.includes("consumidor")) return "CONSUMIDOR";
  return "BANCARIO";
}

export function rotuloArea(codigo) {
  if (!codigo) return "Bancário";
  return ROTULO_AREA[String(codigo).toUpperCase()] || String(codigo);
}

function formatarDataPtBr(isoOuData) {
  if (!isoOuData) return new Date().toLocaleDateString("pt-BR");
  const texto = String(isoOuData);
  if (/^\d{4}-\d{2}-\d{2}$/.test(texto)) {
    const [ano, mes, dia] = texto.split("-");
    return `${dia}/${mes}/${ano}`;
  }
  const d = new Date(texto);
  if (Number.isNaN(d.getTime())) return texto;
  return d.toLocaleDateString("pt-BR");
}

function formatarDocExibicao(doc) {
  if (!doc) return "Não informado";
  const digitos = String(doc).replace(/\D/g, "");
  if (digitos.length === 11) {
    return digitos.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, "$1.$2.$3-$4");
  }
  if (digitos.length === 14) {
    return digitos.replace(
      /(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/,
      "$1.$2.$3/$4-$5",
    );
  }
  return String(doc);
}

function formatarTelefoneExibicao(tel) {
  if (!tel) return "Não informado";
  const digitos = String(tel).replace(/\D/g, "");
  if (digitos.length === 11) {
    return digitos.replace(/(\d{2})(\d{5})(\d{4})/, "($1) $2-$3");
  }
  if (digitos.length === 10) {
    return digitos.replace(/(\d{2})(\d{4})(\d{4})/, "($1) $2-$3");
  }
  return String(tel);
}

export function mapearCasoApi(c) {
  const areaRot = rotuloArea(c.area);
  const titulo = c.titulo || areaRot;
  const tipoAcao = titulo.toLowerCase().includes(areaRot.toLowerCase())
    ? titulo
    : `${areaRot} - ${titulo}`;
  return {
    id: c.id,
    numero: c.numero_processo || `CASO-${String(c.id).padStart(4, "0")}`,
    cliente: c.cliente,
    clienteId: c.cliente_id,
    area: areaRot,
    areaCodigo: c.area,
    tipoAcao,
    vara: c.vara || "Foro / Vara em definição",
    status: STATUS_PARA_ETAPA[c.status] || "Petição inicial",
    statusCodigo: c.status,
    valorCausa: c.observacoes || "A definir",
    criadoEm: formatarDataPtBr(c.data_abertura || c.criado_em),
    descricao: c.descricao || "",
  };
}

/** Converte `PrazoOut` (API) para o formato usado pelas telas.

A API devolve `data_vencimento` + `status` (nao ha `data_limite`/`cumprido`/
`dias_restantes`) e NAO traz dados do caso: cliente, numero, area e vara vem
do caso vinculado (`casosMapeados`), resolvido por `caso_id`. Os campos
legados (`cumprido`, `dataLimite`, `diasRestantes`) continuam existindo no
retorno porque Home e BuscaGlobal deles dependem. */
export function mapearPrazoApi(p, casosMapeados = []) {
  const caso = casosMapeados.find((c) => c.id === p.caso_id);
  const dataIso = String(p.data_vencimento || p.data_limite || "").slice(0, 10);
  const status = p.status || (p.cumprido ? "CONCLUIDO" : "PENDENTE");
  const emAberto = status === "PENDENTE" || status === "EM_ANDAMENTO";
  return {
    id: p.id,
    casoId: p.caso_id,
    processoId: p.processo_id ?? null,
    titulo: p.titulo,
    processo:
      p.numero_processo ||
      caso?.numero ||
      `CASO-${String(p.caso_id ?? 0).padStart(4, "0")}`,
    cliente: p.cliente || caso?.cliente || "Cliente não informado",
    area: caso?.area || rotuloArea(p.area),
    vara: caso?.vara || "Foro / Vara em definição",
    dataVencimento: dataIso,
    dataInicio: p.data_inicio || null,
    dataLimite: dataIso ? `${dataIso}T23:59:00` : "",
    diasRestantes: diasAte(dataIso),
    status,
    statusRotulo: ROTULO_STATUS_PRAZO[status] || status,
    cumprido: status === "CONCLUIDO",
    cancelado: status === "CANCELADO",
    emAberto,
    vencido: Boolean(p.vencido) && emAberto,
    prioridade: p.prioridade || "MEDIA",
    tipo: p.tipo || "PROCESSUAL",
    tipoRotulo: ROTULO_TIPO_PRAZO[p.tipo] || p.tipo || "Processual",
    descricao: p.descricao || "",
    observacoes: p.observacoes || "",
    responsavelNome: p.responsavel_nome || "",
    concluidoEm: p.concluido_em || null,
  };
}

export function mapearClienteApi(cli, casosMapeados = []) {
  const digitosDoc = String(cli.cpf_cnpj || "").replace(/\D/g, "");
  const tipo = digitosDoc.length === 14 ? "PJ" : "PF";
  const processosDoCliente = casosMapeados.filter(
    (c) =>
      c.clienteId === cli.id ||
      c.cliente?.trim().toLowerCase() === cli.nome?.trim().toLowerCase(),
  );
  return {
    id: cli.id,
    nome: cli.nome,
    tipo,
    documento: formatarDocExibicao(cli.cpf_cnpj),
    telefone: formatarTelefoneExibicao(cli.telefone),
    email: cli.email || "",
    cidade: "Paulo Afonso - BA",
    processosAtivos: processosDoCliente.length,
    areas: [...new Set(processosDoCliente.map((p) => p.area))],
    criadoEm: formatarDataPtBr(cli.criado_em),
    observacoes: "",
  };
}

export async function carregarCarteiraApi() {
  // Falhas NAO sao mais silenciadas: antes `.catch(() => ({ itens: [] }))`
  // transformava qualquer queda da API em "estado vazio falso" (a tela
  // mostrava "Nenhum processo cadastrado"). Agora a falha e registrada e
  // devolvida em `erro` para a tela exibir o aviso correto.
  const falhas = [];
  const capturar = (falha) => {
    falhas.push(falha);
    return { itens: [] };
  };

  const [resCasos, resPrazos, resClientes] = await Promise.all([
    apiJson("casos?pagina=1&limite=100").catch(capturar),
    // GET /api/prazos devolve { itens, total, pagina, limite } - nunca uma lista.
    apiJson("prazos?pagina=1&limite=100").catch(capturar),
    apiJson("clientes?pagina=1&limite=100").catch(capturar),
  ]);

  const listaCasosBruta = Array.isArray(resCasos?.itens)
    ? resCasos.itens
    : Array.isArray(resCasos?.items)
      ? resCasos.items
      : Array.isArray(resCasos)
        ? resCasos
        : [];
  const listaPrazosBruta = Array.isArray(resPrazos?.itens)
    ? resPrazos.itens
    : Array.isArray(resPrazos)
      ? resPrazos
      : [];
  const listaClientesBruta = Array.isArray(resClientes?.itens)
    ? resClientes.itens
    : Array.isArray(resClientes?.items)
      ? resClientes.items
      : Array.isArray(resClientes)
        ? resClientes
        : [];

  const processos = listaCasosBruta.map(mapearCasoApi);
  const prazos = listaPrazosBruta.map((p) => mapearPrazoApi(p, processos));
  const clientes = listaClientesBruta.map((cli) =>
    mapearClienteApi(cli, processos),
  );

  return {
    processos,
    prazos,
    clientes,
    clientesBrutos: listaClientesBruta,
    // Primeira falha de carga ("" quando tudo carregou). A tela decide o
    // que exibir - o hook `useCarteira` a expõe como `erro`.
    erro: falhas.length > 0 ? falhas[0].message || String(falhas[0]) : "",
  };
}

export function notificarAtualizacaoDados() {
  window.dispatchEvent(new CustomEvent("dados:atualizar"));
}

export function useCarteira(ativo = true) {
  const [processos, setProcessos] = useState([]);
  const [prazos, setPrazos] = useState([]);
  const [clientes, setClientes] = useState([]);
  const [carregando, setCarregando] = useState(Boolean(ativo));
  // Ultima falha de carga da carteira ("" quando nao houve). Permite que as
  // telas diferenciem "lista vazia de verdade" de "API indisponivel".
  const [erro, setErro] = useState("");

  const recarregar = useCallback(async () => {
    if (!ativo) return;
    setCarregando(true);
    try {
      const dados = await carregarCarteiraApi();
      setProcessos(dados.processos);
      setPrazos(dados.prazos);
      setClientes(dados.clientes);
      setErro(dados.erro || "");
    } catch (falha) {
      setErro(falha.message || "Não foi possível carregar os dados.");
    } finally {
      setCarregando(false);
    }
  }, [ativo]);

  useEffect(() => {
    if (!ativo) return undefined;
    let cancelado = false;
    carregarCarteiraApi()
      .then((dados) => {
        if (cancelado) return;
        setProcessos(dados.processos);
        setPrazos(dados.prazos);
        setClientes(dados.clientes);
        setErro(dados.erro || "");
      })
      .catch((falha) => {
        if (cancelado) return;
        setErro(falha.message || "Não foi possível carregar os dados.");
      })
      .finally(() => {
        if (!cancelado) setCarregando(false);
      });
    const handler = () => {
      recarregar();
    };
    window.addEventListener("dados:atualizar", handler);
    return () => {
      cancelado = true;
      window.removeEventListener("dados:atualizar", handler);
    };
  }, [ativo, recarregar]);

  return {
    processos,
    prazos,
    clientes,
    carregando,
    erro,
    recarregar,
    setProcessos,
    setPrazos,
    setClientes,
  };
}
