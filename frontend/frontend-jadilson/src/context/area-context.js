import { createContext, useContext } from "react";

// Áreas de atuação disponíveis no filtro global. "todas" não filtra nada.
export const AREAS = [
  { id: "todas", rotulo: "Todas as áreas", cor: "bg-ink-muted" },
  { id: "bancario", rotulo: "Bancário", cor: "bg-primary" },
  { id: "previdenciario", rotulo: "Previdenciário", cor: "bg-accent" },
  { id: "consumidor", rotulo: "Consumidor", cor: "bg-status-ok" },
];

export const AreaContext = createContext({ area: "todas", setArea: () => {} });

/** Área selecionada na sidebar. As telas usam `area` para filtrar seus dados. */
export function useArea() {
  return useContext(AreaContext);
}

