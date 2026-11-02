import { createContext, useContext } from "react";

// Dados da sessão que as telas precisam (ex.: token CSRF para chamadas de escrita).
export const SessaoContext = createContext({ csrf: null });

export function useSessao() {
  return useContext(SessaoContext);
}
