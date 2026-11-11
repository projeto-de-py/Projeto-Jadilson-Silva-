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

export function mapearPrazoApi(p) {
  const dataIso = String(p.data_limite || "").slice(0, 10);
  const horario = p.tipo === "AUDIENCIA" ? "09:00:00" : "23:59:00";
  return {
    id: p.id,
    casoId: p.caso_id,
    titulo: p.titulo,
    processo: p.numero_processo || `CASO-${String(p.caso_id).padStart(4, "0")}`,
    cliente: p.cliente,
    area: rotuloArea(p.area),
    vara: p.vara || "Foro / Vara em definição",
    dataLimite: `${dataIso}T${horario}`,
    diasRestantes: Number(p.dias_restantes ?? 0),
    cumprido: Boolean(p.cumprido),
    tipo: p.tipo === "AUDIENCIA" ? "Audiência" : "Prazo processual",
    descricao: p.descricao || "",
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
  const [resCasos, resPrazos, resClientes] = await Promise.all([
    apiJson("casos?pagina=1&limite=100").catch(() => ({ itens: [] })),
    apiJson("prazos").catch(() => []),
    apiJson("clientes?pagina=1&limite=100").catch(() => ({ itens: [] })),
  ]);

  const listaCasosBruta = Array.isArray(resCasos?.itens)
    ? resCasos.itens
    : Array.isArray(resCasos?.items)
      ? resCasos.items
      : Array.isArray(resCasos)
        ? resCasos
        : [];
  const listaPrazosBruta = Array.isArray(resPrazos) ? resPrazos : [];
  const listaClientesBruta = Array.isArray(resClientes?.itens)
    ? resClientes.itens
    : Array.isArray(resClientes?.items)
      ? resClientes.items
      : Array.isArray(resClientes)
        ? resClientes
        : [];

  const processos = listaCasosBruta.map(mapearCasoApi);
  const prazos = listaPrazosBruta.map(mapearPrazoApi);
  const clientes = listaClientesBruta.map((cli) =>
    mapearClienteApi(cli, processos),
  );

  return {
    processos,
    prazos,
    clientes,
    clientesBrutos: listaClientesBruta,
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

  const recarregar = useCallback(async () => {
    if (!ativo) return;
    setCarregando(true);
    try {
      const dados = await carregarCarteiraApi();
      setProcessos(dados.processos);
      setPrazos(dados.prazos);
      setClientes(dados.clientes);
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
    recarregar,
    setProcessos,
    setPrazos,
    setClientes,
  };
}
