export const SEM_CLIENTE = "sem-cliente";
const TOM_PADRAO = "neutro";

/**
 * Organiza os documentos em pastas.
 *
 * Onde cada documento fica (nesta ordem): na pasta personalizada escolhida (`pastaId`); no
 * cliente escolhido (`clienteId`); no cliente do processo vinculado; ou em "Sem cliente vinculado".
 *
 * Pastas de cliente só existem para quem tem processo ou documento: cliente sem nenhum dos dois
 * não ganha pasta. As pastas personalizadas aparecem sempre, mesmo vazias.
 */
export function agruparEmPastas(docs, processos, clientes, personalizadas = [], cores = {}) {
  const processoPorId = new Map(processos.map((p) => [String(p.id), p]));
  const clientesPorId = new Map(clientes.map((c) => [String(c.id), c]));
  const pastas = new Map();
  const avulsa = { id: SEM_CLIENTE, tipo: "avulsa", nome: "Sem cliente vinculado", docs: [], processos: [] };
  const personalizada = new Map(personalizadas.map((p) => [p.id, { ...p, tipo: "personalizada", docs: [], processos: [] }]));

  const pastaDoCliente = (id) => {
    const cliente = clientesPorId.get(String(id));
    if (!cliente) return null;
    if (!pastas.has(String(id))) {
      pastas.set(String(id), { id: String(id), tipo: "cliente", nome: cliente.nome, docs: [], processos: processos.filter((p) => p.clienteId === cliente.id) });
    }
    return pastas.get(String(id));
  };

  for (const c of clientes) if (processos.some((p) => p.clienteId === c.id)) pastaDoCliente(c.id);

  for (const doc of docs) {
    const clienteId = doc.clienteId ?? processoPorId.get(String(doc.processoId))?.clienteId;
    (personalizada.get(doc.pastaId) ?? pastaDoCliente(clienteId) ?? avulsa).docs.push(doc);
  }

  const todas = [...pastas.values(), ...personalizada.values(), ...(avulsa.docs.length ? [avulsa] : [])];
  return todas.map((p) => ({
    ...p,
    cor: cores[p.id] ?? p.cor ?? TOM_PADRAO,
    ultimoEm: Math.max(0, ...p.docs.map((d) => d.atualizadoEm)),
  }));
}

/** Ordem de exibição: as mais mexidas primeiro; empate pelo nome. */
export const maisRecentesPrimeiro = (pastas) =>
  [...pastas].sort((a, b) => b.ultimoEm - a.ultimoEm || a.nome.localeCompare(b.nome, "pt-BR"));

/** Divide os documentos por processo; os sem processo ficam em um grupo à parte, no fim. */
export function agruparPorProcesso(docs, processos) {
  const grupos = new Map();
  for (const doc of docs) {
    const processo = processos.find((p) => String(p.id) === String(doc.processoId)) ?? null;
    const chave = processo ? String(processo.id) : "sem-processo";
    if (!grupos.has(chave)) grupos.set(chave, { chave, processo, docs: [] });
    grupos.get(chave).docs.push(doc);
  }
  return [...grupos.values()].sort((a, b) => Number(a.chave === "sem-processo") - Number(b.chave === "sem-processo"));
}

/** Campos do documento para colocá-lo em `pasta` (null = voltar para o lugar automático). */
export function destinoDoDocumento(pasta) {
  if (!pasta) return { pastaId: undefined, clienteId: undefined };
  if (pasta.tipo === "personalizada") return { pastaId: pasta.id, clienteId: undefined };
  if (pasta.tipo === "cliente") return { pastaId: undefined, clienteId: Number(pasta.id) };
  return { pastaId: undefined, clienteId: undefined };
}
