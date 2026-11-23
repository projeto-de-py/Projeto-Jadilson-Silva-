import { useCallback, useEffect, useState } from "react";

// Como os documentos, as pastas do advogado ficam no navegador (localStorage) por enquanto.
const CHAVE = "pastas-documentos-v1";
const VAZIO = { personalizadas: [], cores: {} };

function ler() {
  try {
    const bruto = localStorage.getItem(CHAVE);
    if (bruto) return { ...VAZIO, ...JSON.parse(bruto) };
  } catch {
    /* sem acesso ao armazenamento */
  }
  return VAZIO;
}

/**
 * Pastas criadas pelo advogado (`personalizadas`: id, nome e cor) e as cores escolhidas para as
 * pastas automáticas (`cores`: id da pasta -> tom). Os nomes das pastas de clientes não mudam.
 */
export function usePastasPersonalizadas() {
  const [estado, setEstado] = useState(ler);

  useEffect(() => {
    try {
      localStorage.setItem(CHAVE, JSON.stringify(estado));
    } catch {
      /* armazenamento cheio ou bloqueado */
    }
  }, [estado]);

  const criar = useCallback((nome, cor) => {
    const pasta = { id: `p-${Date.now()}`, nome, cor };
    setEstado((atual) => ({ ...atual, personalizadas: [...atual.personalizadas, pasta] }));
    return pasta;
  }, []);

  const atualizar = useCallback((id, parcial) => {
    setEstado((atual) => ({ ...atual, personalizadas: atual.personalizadas.map((p) => (p.id === id ? { ...p, ...parcial } : p)) }));
  }, []);

  const excluir = useCallback((id) => {
    setEstado((atual) => ({ ...atual, personalizadas: atual.personalizadas.filter((p) => p.id !== id) }));
  }, []);

  const definirCor = useCallback((id, cor) => setEstado((atual) => ({ ...atual, cores: { ...atual.cores, [id]: cor } })), []);

  return { personalizadas: estado.personalizadas, cores: estado.cores, criar, atualizar, excluir, definirCor };
}
