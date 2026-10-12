import { createContext, useContext } from "react";

/**
 * Contexto de autenticacao.
 * Fica em arquivo proprio (sem componentes) para nao quebrar o Fast Refresh.
 */
export const AuthContext = createContext(null);

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth precisa estar dentro de <AuthProvider>");
  return ctx;
}
