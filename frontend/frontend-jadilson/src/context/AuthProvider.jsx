import { useCallback, useEffect, useState } from "react";
import { api, setCsrfToken } from "@/api/client";
import { AuthContext } from "@/context/auth-context";

/**
 * Sessao gerenciada por cookie HttpOnly no servidor.
 * Nada de token no localStorage: no carregamento, /auth/me valida o cookie e
 * devolve o usuario + o token CSRF atual (para as proximas mutacoes).
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [csrf, setCsrf] = useState(null);
  // sempre comeca em true: precisa perguntar ao backend se ha sessao valida
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let ativo = true;
    api
      .get("/auth/me")
      .then((data) => {
        if (!ativo) return;
        setCsrfToken(data.csrf_token);
        setCsrf(data.csrf_token);
        setUser(data.usuario);
      })
      .catch(() => {
        // sem cookie ou expirado -> apenas segue no login
        setCsrfToken(null);
        if (ativo) {
          setCsrf(null);
          setUser(null);
        }
      })
      .finally(() => {
        if (ativo) setLoading(false);
      });
    return () => {
      ativo = false;
    };
  }, []);

  const login = useCallback(async (email, senha) => {
    const data = await api.post("/auth/login", { email, senha });
    setCsrfToken(data.csrf_token);
    setCsrf(data.csrf_token);
    setUser(data.usuario);
    return data.usuario;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout"); // backend apaga o cookie (exige CSRF)
    } catch {
      /* sessao ja invalida - segue limpando o estado local */
    }
    setCsrfToken(null);
    setCsrf(null);
    setUser(null);
    setLoading(false);
  }, []);

  return (
    <AuthContext.Provider value={{ user, csrf, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
