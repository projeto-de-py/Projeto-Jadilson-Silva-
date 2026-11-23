import { useState } from "react";
import { Badge, Button } from "@/components/ui";
import { apiIA } from "@/lib/api";
import { useSessao } from "@/context/sessao";

/**
 * "Conferir citações": envia o texto da peça ao modelo de entidades (treinado pela equipe) e
 * lista o que ele achou, com a confiança de cada item. É apoio à revisão: o modelo não
 * confirma que a citação existe.
 */

const GRUPOS = [
  { titulo: "Leis e decisões citadas", tipos: ["LEGISLACAO", "JURISPRUDENCIA"] },
  { titulo: "Pessoas", tipos: ["PESSOA"] },
  { titulo: "Datas", tipos: ["TEMPO"] },
  { titulo: "Órgãos e locais", tipos: ["ORGANIZACAO", "LOCAL"] },
];

const FAIXA = {
  alta: { tom: "ok", rotulo: "Identificado" },
  media: { tom: "atencao", rotulo: "Conferir" },
  baixa: { tom: "neutral", rotulo: "Incerto" },
};

export function PainelEntidades({ obterTexto, aoLocalizar }) {
  const { csrf } = useSessao();
  const [estado, setEstado] = useState({ fase: "parado", dados: null, erro: "" });
  const [mostrarIncertos, setMostrarIncertos] = useState(false);

  async function conferir() {
    const texto = obterTexto().trim();
    if (!texto) {
      setEstado({ fase: "erro", dados: null, erro: "Escreva alguma coisa na peça antes de conferir." });
      return;
    }
    setEstado({ fase: "carregando", dados: null, erro: "" });
    try {
      const dados = await apiIA("entidades", { csrf, body: { texto: texto.slice(0, 20000) } });
      setEstado({ fase: "pronto", dados, erro: "" });
    } catch (falha) {
      setEstado({ fase: "erro", dados: null, erro: falha.message });
    }
  }

  const todos = estado.dados?.entidades ?? [];
  const incertos = todos.filter((e) => e.faixa === "baixa").length;
  const itens = mostrarIncertos ? todos : todos.filter((e) => e.faixa !== "baixa");
  const nada = estado.fase === "pronto" && todos.length === 0;

  return (
    <div className="space-y-3">
      <Button variant="secondary" className="w-full" onClick={conferir} loading={estado.fase === "carregando"}>
        Conferir citações e nomes
      </Button>
      <p className="text-12 text-ink-muted">Destaca leis, decisões, pessoas e datas da peça, com a confiança do modelo. Não confirma que a citação existe.</p>

      {estado.fase === "erro" && (
        <p role="alert" className="text-status-vencido-ink text-13">{estado.erro}</p>
      )}
      {nada && <p className="text-13 text-ink-muted">O modelo não encontrou citações ou nomes neste texto.</p>}

      {GRUPOS.map((g) => {
        const lista = itens.filter((e) => g.tipos.includes(e.tipo));
        if (!lista.length) return null;
        return (
          <section key={g.titulo} className="space-y-1">
            <h4 className="text-12 text-ink-muted font-medium">{g.titulo} ({lista.length})</h4>
            <ul className="space-y-1">
              {lista.map((e) => {
                const faixa = FAIXA[e.faixa] ?? FAIXA.baixa;
                return (
                  <li key={`${e.inicio}-${e.fim}`}>
                    <button
                      type="button"
                      onClick={() => aoLocalizar?.(e.texto)}
                      title={`Confiança ${Math.round(e.confianca * 100)}%. Clique para localizar no texto.`}
                      className="hover:bg-surface-muted flex w-full items-center justify-between gap-2 rounded-input px-2 py-1 text-left transition-colors"
                    >
                      <span className="text-13 text-ink min-w-0 flex-1 truncate">{e.texto}</span>
                      <Badge tone={faixa.tom} className="shrink-0 px-2 py-0.5">{faixa.rotulo} {Math.round(e.confianca * 100)}%</Badge>
                    </button>
                  </li>
                );
              })}
            </ul>
          </section>
        );
      })}
      {estado.fase === "pronto" && incertos > 0 && (
        <button type="button" onClick={() => setMostrarIncertos((v) => !v)} className="text-12 text-primary hover:text-primary-hover font-medium">
          {mostrarIncertos ? "Ocultar itens incertos" : `Mostrar ${incertos} ${incertos === 1 ? "item incerto" : "itens incertos"} (confiança abaixo de 60%)`}
        </button>
      )}
      {estado.fase === "pronto" && estado.dados?.aviso && <p className="text-12 text-ink-muted">{estado.dados.aviso}</p>}
    </div>
  );
}
