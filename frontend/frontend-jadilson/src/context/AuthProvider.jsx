import { useCallback, useEffect, useState } from "react";
import { api } from "@/api/client";
import { AuthContext } from "@/context/auth-context";

const STORAGE_KEY = "jadilson_token";

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(STORAGE_KEY));
  const [user, setUser] = useState(null);
  // sem token salvo, ja comeca em false (nao ha nada a validar)
  const [loading, setLoading] = useState(() => Boolean(localStorage.getItem(STORAGE_KEY)));

  // Valida o token salvo no navegador ao carregar a aplicacao
  useEffect(() => {
    if (!token) return;
    let ativo = true;
    api
      .get("/auth/me", token)
      .then((u) => ativo && setUser(u))
      .catch(() => {
        // token expirado/invalido -> limpa
        localStorage.removeItem(STORAGE_KEY);
        if (ativo) {
          setToken(null);
          setUser(null);
        }
      })
      .finally(() => {
        if (ativo) setLoading(false);
      });
    return () => {
      ativo = false;
    };
  }, [token]);

  const login = useCallback(async (email, senha) => {
    const data = await api.post("/auth/login", { email, senha });
    localStorage.setItem(STORAGE_KEY, data.access_token);
    setToken(data.access_token);
    setUser(data.usuario);
    return data.usuario;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setToken(null);
    setUser(null);
    setLoading(false);
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
