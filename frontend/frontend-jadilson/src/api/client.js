const BASE_URL = "/api"; // proxy do Vite -> http://127.0.0.1:8000/api

let csrfToken = null; // em memoria (nao em localStorage - evita vazamento)

export function setCsrfToken(token) {
  csrfToken = token || null;
}

export function getCsrfToken() {
  return csrfToken;
}

const MUTANTES = new Set(["POST", "PUT", "PATCH", "DELETE"]);

async function request(path, { method = "GET", body } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (MUTANTES.has(method) && csrfToken) headers["X-CSRF-Token"] = csrfToken;

  let res;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      credentials: "same-origin", // envia/recebe o cookie de sessao
      body: body !== undefined ? JSON.stringify(body) : undefined,
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
    const errosComuns = {
      401: "Sessão expirada. Entre novamente.",
      403: "Não foi possível autorizar esta ação.",
      429: "Muitas tentativas. Aguarde alguns minutos e tente novamente.",
    };
    const erro = new Error(detalhe || errosComuns[res.status] || `Erro ${res.status}`);
    erro.status = res.status;
    throw erro;
  }

  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: "POST", body }),
  put: (path, body) => request(path, { method: "PUT", body }),
  del: (path) => request(path, { method: "DELETE" }),
};
