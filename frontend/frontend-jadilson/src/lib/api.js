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
