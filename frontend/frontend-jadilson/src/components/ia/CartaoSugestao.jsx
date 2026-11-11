import { useState } from "react";
import { LogoIA } from "@/components/ia/LogoIA";
import { sanitizarHtml } from "@/lib/ia";

/**
 * Cartão de sugestão da IA, desenhado dentro da folha (por isso usa o visual
 * claro do papel, definido em `.sug-*` no editor). Aparece logo abaixo do
 * parágrafo de referência: expandir, ler e escolher Adicionar ou Ignorar.
 */
const CATEGORIAS = {
  digitacao: "Digitação",
  gramatica: "Gramática",
  estilo: "Estilo",
  juridico: "Jurídico",
  tom: "Tom",
  risco: "Risco",
  conteudo: "Conteúdo",
};

export function CartaoSugestao({ sugestao, aoAdicionar, aoIgnorar }) {
  const [aberto, setAberto] = useState(false);
  const aviso = sugestao.tipo === "Aviso";

  return (
    <article className="sug-cartao" aria-label="Sugestão da IA">
      <header className="sug-topo">
        <LogoIA tamanho={20} cor="#111" />
        <span>Sugestão da IA · {sugestao.tipo}</span>
        {sugestao.categoria && CATEGORIAS[sugestao.categoria] && sugestao.categoria !== "conteudo" && (
          <span className={`sug-selo sug-${sugestao.severidade ?? "info"}`}>{CATEGORIAS[sugestao.categoria]}</span>
        )}
      </header>

      <h4 className="sug-titulo">{sugestao.titulo}</h4>
      {!aberto && <p className="sug-previa">{sugestao.previa}</p>}
      {aberto && (
        <>
          {sugestao.trecho && <p className="sug-trecho">Trecho: “{sugestao.trecho}”</p>}
          {sugestao.motivo && <p className="sug-motivo">{sugestao.motivo}</p>}
          <div className="sug-conteudo">
            <p className="sug-rotulo">Será acrescentado ao documento</p>
            <div dangerouslySetInnerHTML={{ __html: sanitizarHtml(sugestao.html) }} />
          </div>
        </>
      )}
      {sugestao.verificar_fonte && <p className="sug-fonte">Cita súmula, tema ou julgado: confira a fonte oficial antes de usar.</p>}

      <div className="sug-acoes">
        <button type="button" className="sug-botao sug-primario" onClick={() => aoAdicionar(sugestao)} disabled={aviso}>
          Adicionar
        </button>
        <button type="button" className="sug-botao" onClick={() => aoIgnorar(sugestao)}>
          Ignorar
        </button>
        <button type="button" className="sug-link" aria-expanded={aberto} onClick={() => setAberto((v) => !v)}>
          {aberto ? "Recolher" : "Expandir"}
        </button>
      </div>
    </article>
  );
}
