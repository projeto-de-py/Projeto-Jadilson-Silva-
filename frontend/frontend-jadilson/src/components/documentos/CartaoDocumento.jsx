import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";
import { IconFolder, IconTrash } from "symbols-react";
import { Badge } from "@/components/ui";
import { AREAS_DOC } from "@/data/modelos";

const textoPuro = (html) => html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
const acao = "text-ink-muted hover:bg-surface-muted absolute top-4 flex size-8 items-center justify-center rounded-input opacity-0 transition focus-visible:opacity-100 group-hover:opacity-100";

/** Cartão de um documento. `cliente` (opcional) mostra a quem pertence, útil nos resultados de busca. */
export function CartaoDocumento({ doc, cliente, aoAbrir, aoMover, aoExcluir }) {
  const area = AREAS_DOC.find((a) => a.id === doc.area);
  return (
    <li className="group relative">
      <button
        type="button"
        onClick={aoAbrir}
        className="bg-surface border-border hover:border-primary/50 flex h-full w-full flex-col gap-4 rounded-card border p-6 text-left transition-colors"
      >
        <div className="flex items-center gap-2">
          {area && <Badge tone={area.tom}>{area.rotulo}</Badge>}
          <span className="text-12 text-ink-muted truncate">{doc.tipo}</span>
        </div>
        <p className="text-16 text-ink line-clamp-2 font-semibold">{doc.titulo}</p>
        <p className="text-13 text-ink-muted line-clamp-3 flex-1">{textoPuro(doc.html).slice(0, 220) || "Documento vazio"}</p>
        <p className="text-12 text-ink-muted truncate">
          {cliente ? `${cliente} · ` : ""}Editado {formatDistanceToNow(doc.atualizadoEm, { locale: ptBR, addSuffix: true })}
        </p>
      </button>
      <button type="button" aria-label={`Mover ${doc.titulo} para outra pasta`} onClick={aoMover} className={`${acao} right-14 hover:text-ink`}>
        <IconFolder className="size-4" fill="currentColor" />
      </button>
      <button type="button" aria-label={`Excluir ${doc.titulo}`} onClick={aoExcluir} className={`${acao} right-4 hover:text-status-vencido-ink`}>
        <IconTrash className="size-4" fill="currentColor" />
      </button>
    </li>
  );
}
