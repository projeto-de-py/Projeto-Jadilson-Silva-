import {
  IconHouse,
  IconFolder,
  IconClock,
  IconCalendar,
  IconPerson2,
  IconGearshape,
  IconDocumentOnDocument,
  IconBanknote,
} from "symbols-react";

export const navegacao = [
  { to: "/home", rotulo: "Início", icone: IconHouse, grupo: "Visão geral" },
  { to: "/processos", rotulo: "Processos", icone: IconFolder, grupo: "Visão geral" },
  { to: "/prazos", rotulo: "Prazos", icone: IconClock, grupo: "Visão geral" },
  { to: "/agenda", rotulo: "Agenda", icone: IconCalendar, grupo: "Visão geral" },
  { to: "/documentos", rotulo: "Documentos", icone: IconDocumentOnDocument, grupo: "Visão geral" },
  { to: "/financeiro", rotulo: "Financeiro", icone: IconBanknote, grupo: "Escritório" },
  { to: "/clientes", rotulo: "Clientes", icone: IconPerson2, grupo: "Escritório" },
  // Configurações alteram dados globais do escritório: o backend exige
  // administrador e o menu só o exibe para quem pode acessar.
  { to: "/configuracoes", rotulo: "Configurações", icone: IconGearshape, grupo: "Escritório", somenteAdmin: true },
];

/** Itens visíveis para o usuário (oculta os restritos a administrador). */
export function navegacaoPara(user) {
  return navegacao.filter((item) => !item.somenteAdmin || user?.administrador);
}

export function navegacaoAgrupada(user) {
  const grupos = [];
  for (const item of navegacaoPara(user)) {
    let grupo = grupos.find((g) => g.nome === item.grupo);
    if (!grupo) {
      grupo = { nome: item.grupo, itens: [] };
      grupos.push(grupo);
    }
    grupo.itens.push(item);
  }
  return grupos;
}

export function tituloDaRota(caminho) {
  const item = navegacao.find((entrada) => caminho.startsWith(entrada.to));
  return item?.rotulo ?? "Jadilson Silva Adv.";
}
