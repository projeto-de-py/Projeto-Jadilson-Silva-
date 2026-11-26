import { useCallback, useEffect, useState } from "react";
import { apiJson } from "@/lib/api";

// ---------------------------------------------------------------------------
// Filtros no servidor (RF09): as telas antes baixavam os 100 primeiros
// registros e filtravam só esse recorte no navegador. Agora os filtros viram
// query params e a paginação acontece no banco. Este hook e compartilhado por
// Processos, Prazos e Clientes; cada tela continua mapeando o DTO da API para
// o formato que ja usava (mapearCasoApi/mapearPrazoApi/mapearClienteApi).
// ---------------------------------------------------------------------------

/** Monta a query string ignorando valores vazios (o select "TODOS" some). */
export function queryString(params = {}) {
  const busca = new URLSearchParams();
  for (const [chave, valor] of Object.entries(params)) {
    if (valor === undefined || valor === null || valor === "") continue;
    busca.set(chave, String(valor));
  }
  const texto = busca.toString();
  return texto ? `?${texto}` : "";
}

function useDebounce(valor, ms) {
  const [atrasado, setAtrasado] = useState(valor);
  useEffect(() => {
    const temporizador = setTimeout(() => setAtrasado(valor), ms);
    return () => clearTimeout(temporizador);
  }, [valor, ms]);
  return atrasado;
}

/**
 * @param {string} caminho endpoint sob /api (ex.: "casos", "prazos")
 * @param {object} params filtros da tela; a chave JSON e o que dispara a busca
 * @param {object} opcoes `limite`, `debounceMs`
 * @returns itens crus da API + { total, carregando, erro, pagina, carregarMais, recarregar }
 */
export function useConsultaPaginada(
  caminho,
  params,
  { limite = 100, debounceMs = 300 } = {},
) {
  // JSON e a identidade estavel: objetos literais mudam a cada render e
  // causariam refetch infinito se fossem usados diretamente como dependencia.
  const chave = JSON.stringify(params ?? {});
  const chaveAtrasada = useDebounce(chave, debounceMs);
  const [estado, setEstado] = useState({
    itens: [],
    total: 0,
    carregando: true,
    erro: "",
    pagina: 1,
  });
  const [tentativa, setTentativa] = useState(0);

  const buscar = useCallback(
    async (pagina, sinal, { paginando = false } = {}) => {
      // `carregando` e atualizado aqui (callback), nunca no corpo do efeito.
      if (!paginando) {
        // Microtarefa: evita setState sincrono no corpo do efeito (a mesma
        // regra de lint usada nas outras telas do projeto).
        Promise.resolve().then(() => {
          setEstado((anterior) => ({ ...anterior, carregando: true, erro: "" }));
        });
      }
      const filtros = JSON.parse(chaveAtrasada);
      const resposta = await apiJson(
        `${caminho}${queryString({ ...filtros, pagina, limite })}`,
        { signal: sinal },
      );
      return {
        itens: Array.isArray(resposta?.itens) ? resposta.itens : [],
        total: Number(resposta?.total ?? 0),
      };
    },
    [caminho, chaveAtrasada, limite],
  );

  useEffect(() => {
    let cancelado = false;
    const controle = new AbortController();
    buscar(1, controle.signal)
      .then(({ itens, total }) => {
        if (!cancelado) {
          setEstado({
            itens,
            total,
            carregando: false,
            erro: "",
            pagina: 1,
          });
        }
      })
      .catch((falha) => {
        if (!cancelado && falha?.name !== "AbortError") {
          setEstado({
            itens: [],
            total: 0,
            carregando: false,
            erro: falha?.message || "Não foi possível carregar os dados.",
            pagina: 1,
          });
        }
      });
    return () => {
      cancelado = true;
      controle.abort();
    };
  }, [buscar, tentativa]);

  const carregarMais = useCallback(async () => {
    const proxima = estado.pagina + 1;
    const { itens } = await buscar(proxima, undefined, { paginando: true });
    setEstado((anterior) => {
      const vistos = new Set(anterior.itens.map((item) => item.id));
      return {
        ...anterior,
        itens: [
          ...anterior.itens,
          ...itens.filter((item) => !vistos.has(item.id)),
        ],
        pagina: proxima,
      };
    });
  }, [buscar, estado.pagina]);

  const recarregar = useCallback(() => setTentativa((n) => n + 1), []);

  useEffect(() => {
    const aoAtualizar = () => recarregar();
    window.addEventListener("dados:atualizar", aoAtualizar);
    return () => window.removeEventListener("dados:atualizar", aoAtualizar);
  }, [recarregar]);

  return { ...estado, carregarMais, recarregar };
}
