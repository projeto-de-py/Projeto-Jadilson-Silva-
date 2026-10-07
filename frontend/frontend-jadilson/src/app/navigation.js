import {
  CalendarClock,
  CalendarDays,
  FolderOpen,
  Home,
  Settings,
  Users,
} from "lucide-react";

export const navegacao = [
  { to: "/home", rotulo: "Início", icone: Home },
  { to: "/processos", rotulo: "Processos", icone: FolderOpen },
  { to: "/prazos", rotulo: "Prazos", icone: CalendarClock },
  { to: "/agenda", rotulo: "Agenda", icone: CalendarDays },
  { to: "/clientes", rotulo: "Clientes", icone: Users },
  { to: "/configuracoes", rotulo: "Configurações", icone: Settings },
];

export function tituloDaRota(caminho) {
  const item = navegacao.find((entrada) => caminho.startsWith(entrada.to));
  return item?.rotulo ?? "Jadilson Silva Adv.";
}
