import { IconCheckmark, IconXmark } from "symbols-react";
import { sanitizarHtml } from "@/lib/ia";

/**
 * Se o HTML sanitizado for apenas um único `<p>...</p>` sem outros blocos dentro,
 * devolve o conteúdo interno para substituições inline dentro de um parágrafo.
 */
export function conteudoParaDiff(html, inline) {
  const limpo = sanitizarHtml(html || "").trim();
  if (!inline) return limpo;
  const match = limpo.match(/^<p>([\s\S]*?)<\/p>$/i);
  if (match && !/<(?:p|h[1-6]|ul|ol|li|blockquote)\b/i.test(match[1])) {
    return match[1];
  }
  return limpo;
}

/**
 * Diff inline estilo Antigravity: o texto antigo já aparece marcado em vermelho
 * diretamente no editor (via Decoration.inline), e este widget renderiza o texto
 * novo em verde com botões compactos de Aprovar (✓) e Recusar (✕).
 */
export function DiffSugestao({ sugestao, inline, aoAprovar, aoRecusar }) {
  const htmlNovo = conteudoParaDiff(sugestao.html, inline);
  const dica = sugestao.motivo || sugestao.titulo || "Sugestão de substituição da IA";

  if (inline) {
    return (
      <span className="sug-diff-inline" title={dica}>
        <span className="sug-diff-novo" dangerouslySetInnerHTML={{ __html: htmlNovo }} />
        <span className="sug-diff-acoes" role="group" aria-label="Ações da sugestão">
          <button
            type="button"
            className="sug-diff-btn sug-diff-aprovar"
            title="Aprovar substituição"
            aria-label="Aprovar substituição"
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => aoAprovar(sugestao)}
          >
            <IconCheckmark className="size-3" fill="currentColor" />
          </button>
          <button
            type="button"
            className="sug-diff-btn sug-diff-recusar"
            title="Recusar alteração"
            aria-label="Recusar alteração"
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => aoRecusar(sugestao)}
          >
            <IconXmark className="size-3" fill="currentColor" />
          </button>
        </span>
      </span>
    );
  }

  return (
    <div className="sug-diff-bloco" role="region" aria-label="Sugestão de substituição da IA">
      <div className="sug-diff-bloco-topo">
        <span className="sug-diff-legenda" title={dica}>
          {sugestao.titulo || "Sugestão da IA"}
          {sugestao.motivo ? ` — ${sugestao.motivo}` : ""}
        </span>
        <span className="sug-diff-acoes" role="group" aria-label="Ações da sugestão">
          <button
            type="button"
            className="sug-diff-btn sug-diff-aprovar"
            title="Aprovar substituição"
            aria-label="Aprovar substituição"
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => aoAprovar(sugestao)}
          >
            <IconCheckmark className="size-3.5" fill="currentColor" />
          </button>
          <button
            type="button"
            className="sug-diff-btn sug-diff-recusar"
            title="Recusar alteração"
            aria-label="Recusar alteração"
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => aoRecusar(sugestao)}
          >
            <IconXmark className="size-3.5" fill="currentColor" />
          </button>
        </span>
      </div>
      <div className="sug-diff-novo sug-diff-novo-bloco" dangerouslySetInnerHTML={{ __html: htmlNovo }} />
      {sugestao.verificar_fonte && (
        <p className="sug-diff-fonte">Cita súmula, tema ou julgado: confira a fonte oficial antes de usar.</p>
      )}
    </div>
  );
}
