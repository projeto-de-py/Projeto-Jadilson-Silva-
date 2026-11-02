import { useCallback, useEffect, useState } from "react";
import { apiJson } from "@/lib/api";

/**
 * Carrega dados de GET /api/<caminho> e expõe { dados, carregando, erro, recarregar }.
 * `caminho` null desliga a busca. "Carregando" é derivado: a resposta guardada ainda
 * não é a da busca atual (evita setState síncrono dentro do efeito).
 */
export function useApiDados(caminho) {
  const [versao, setVersao] = useState(0);
  const [resposta, setResposta] = useState({ chave: null, dados: null, erro: null });
  const chave = caminho ? `${caminho}#${versao}` : null;

  useEffect(() => {
    if (!chave) return undefined;
    const controle = new AbortController();
    apiJson(caminho, { signal: controle.signal })
      .then((dados) => setResposta({ chave, dados, erro: null }))
      .catch((erro) => {
        if (erro?.name !== "AbortError") setResposta({ chave, dados: null, erro });
      });
    return () => controle.abort();
  }, [chave, caminho]);

  const recarregar = useCallback(() => setVersao((v) => v + 1), []);
  const atual = resposta.chave === chave;
  return {
    dados: atual ? resposta.dados : null,
    erro: atual ? resposta.erro : null,
    carregando: Boolean(chave) && !atual,
    recarregar,
  };
}
