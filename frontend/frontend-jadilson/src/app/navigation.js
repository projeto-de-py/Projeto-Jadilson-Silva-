import {
  IconHouse,
  IconFolder,
  IconClock,
  IconCalendar,
  IconPerson2,
  IconGearshape,
  IconDocumentOnDocument,
} from "symbols-react";

export const navegacao = [
  { to: "/home", rotulo: "Início", icone: IconHouse, grupo: "Visão geral" },
  { to: "/processos", rotulo: "Processos", icone: IconFolder, grupo: "Visão geral" },
  { to: "/prazos", rotulo: "Prazos", icone: IconClock, grupo: "Visão geral" },
  { to: "/agenda", rotulo: "Agenda", icone: IconCalendar, grupo: "Visão geral" },
  { to: "/documentos", rotulo: "Documentos", icone: IconDocumentOnDocument, grupo: "Visão geral" },
  { to: "/clientes", rotulo: "Clientes", icone: IconPerson2, grupo: "Escritório" },
  { to: "/configuracoes", rotulo: "Configurações", icone: IconGearshape, grupo: "Escritório" },
];

export function navegacaoAgrupada() {
  const grupos = [];
  for (const item of navegacao) {
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
