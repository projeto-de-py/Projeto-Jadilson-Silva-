export async function api(path, { method = 'GET', body, csrf } = {}) {
  let response;
  try {
    response = await fetch(`/api/auth/${path}`, {
      method,
      credentials: 'same-origin',
      headers: {
        ...(method !== 'GET' ? { 'Content-Type': 'application/json' } : {}),
        ...(csrf ? { 'X-CSRF-Token': csrf } : {}),
      },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
  } catch {
    throw new Error('Não foi possível conectar ao servidor. Tente novamente.');
  }
  if (!response.ok) {
    const messages = {
      401: path === 'login' ? 'E-mail ou senha inválidos.' : 'Sua sessão expirou. Entre novamente.',
      403: 'Não foi possível autorizar esta ação. Atualize a página e tente novamente.',
      422: 'Confira o e-mail e a senha informados.',
      429: 'Muitas tentativas. Aguarde cinco minutos e tente novamente.',
    };
    const error = new Error(messages[response.status] || 'Serviço temporariamente indisponível. Tente novamente.');
    error.status = response.status;
    throw error;
  }
  return response.status === 204 ? null : response.json();
}

/** Chamadas à IA (/api/ia/*): devolve o JSON ou lança Error com `status` e a mensagem do servidor. */
export async function apiIA(caminho, { method = 'POST', body, csrf, signal } = {}) {
  let response;
  try {
    response = await fetch(`/api/ia/${caminho}`, {
      method,
      credentials: 'same-origin',
      signal,
      headers: {
        ...(method !== 'GET' ? { 'Content-Type': 'application/json' } : {}),
        ...(csrf ? { 'X-CSRF-Token': csrf } : {}),
      },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
  } catch (falha) {
    if (falha?.name === 'AbortError') throw falha;
    const erro = new Error('Não foi possível conectar ao servidor.');
    erro.status = 0;
    throw erro;
  }
  if (!response.ok) {
    let detalhe = '';
    try {
      const corpo = await response.json();
      if (typeof corpo?.detail === 'string') detalhe = corpo.detail;
    } catch {
      /* corpo sem JSON */
    }
    const padrao = {
      401: 'Sua sessão expirou. Entre novamente.',
      403: 'Não foi possível autorizar esta ação. Atualize a página e tente novamente.',
      429: 'Você atingiu o limite de pedidos à IA. Aguarde um pouco e tente de novo.',
    };
    const erro = new Error(detalhe || padrao[response.status] || 'A IA está indisponível no momento.');
    erro.status = response.status;
    throw erro;
  }
  return response.json();
}

function mensagemDoCorpo(corpo) {
  const d = corpo?.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d) && d.length) {
    // erro de validação (422): "campo: mensagem"
    return d.slice(0, 3).map((e) => `${(e.loc || []).slice(1).join('.') || 'campo'}: ${e.msg}`).join('; ');
  }
  return '';
}

export async function apiJson(caminho, { method = 'GET', body, csrf, signal } = {}) {
  let response;
  try {
    response = await fetch(`/api/${caminho}`, {
      method,
      credentials: 'same-origin',
      signal,
      headers: {
        ...(body ? { 'Content-Type': 'application/json' } : {}),
        ...(csrf && method !== 'GET' ? { 'X-CSRF-Token': csrf } : {}),
      },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
  } catch (falha) {
    if (falha?.name === 'AbortError') throw falha;
    const erro = new Error('Não foi possível conectar ao servidor.');
    erro.status = 0;
    throw erro;
  }
  if (!response.ok) {
    let corpo = null;
    try {
      corpo = await response.json();
    } catch {
      /* sem JSON */
    }
    const padrao = {
      401: 'Sua sessão expirou. Entre novamente.',
      403: 'Esta ação é restrita ao advogado principal.',
      404: 'Registro não encontrado.',
      429: 'Muitas tentativas. Aguarde um pouco.',
    };
    const erro = new Error(mensagemDoCorpo(corpo) || padrao[response.status] || 'Serviço indisponível no momento.');
    erro.status = response.status;
    throw erro;
  }
  return response.status === 204 ? null : response.json();
}
