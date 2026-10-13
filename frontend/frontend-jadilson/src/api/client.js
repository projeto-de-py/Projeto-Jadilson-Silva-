/**
 * Facade de acesso a API (padrao Facade).
 * Todo fetch passa por aqui - nenhum componente chama fetch direto.
 */

const BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api";

async function request(path, { method = "GET", body, token } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new Error(
      "Não foi possível conectar à API. O backend está rodando? (python main.py)",
    );
  }

  if (!res.ok) {
    let detalhe = "";
    try {
      const json = await res.json();
      if (typeof json.detail === "string") detalhe = json.detail;
    } catch {
      /* corpo sem JSON */
    }
    const erro = new Error(detalhe || `Erro ${res.status}`);
    erro.status = res.status;
    throw erro;
  }

  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  get: (path, token) => request(path, { token }),
  post: (path, body, token) => request(path, { method: "POST", body, token }),
  put: (path, body, token) => request(path, { method: "PUT", body, token }),
  del: (path, token) => request(path, { method: "DELETE", token }),
};

export { BASE_URL };
