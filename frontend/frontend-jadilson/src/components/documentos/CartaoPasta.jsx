import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";
import { IconSquareAndPencil } from "symbols-react";
import { Pasta } from "@/components/ui/Pasta";
import { cn } from "@/lib/cn";

const plural = (n, singular, pluralForma) => `${n} ${n === 1 ? singular : pluralForma}`;

/** Pasta (de cliente, do advogado ou avulsa): a pasta animada e, embaixo, o nome e o resumo. */
export function CartaoPasta({ pasta, aoAbrir, aoPersonalizar }) {
  const total = pasta.docs.length;
  const detalhe = [plural(total, "documento", "documentos")];
  if (pasta.tipo === "cliente") detalhe.push(plural(pasta.processos.length, "processo", "processos"));

  return (
    <div className="group relative">
      <button
        type="button"
        onClick={aoAbrir}
        className="focus-visible:ring-ring flex w-full flex-col items-center gap-4 rounded-card px-4 pt-6 pb-4 text-center focus-visible:ring-2 focus-visible:outline-none"
      >
        <div className={cn("transition-opacity", total === 0 && "opacity-60 group-hover:opacity-100")}>
          <Pasta contagem={total} tom={pasta.cor} />
        </div>
        <div className="w-full min-w-0 space-y-1">
          <p className="text-16 text-ink truncate font-semibold">{pasta.nome}</p>
          <p className="text-12 text-ink-muted truncate">{detalhe.join(" · ")}</p>
          <p className="text-11 text-ink-muted truncate">
            {total > 0 ? `Editado ${formatDistanceToNow(pasta.ultimoEm, { locale: ptBR, addSuffix: true })}` : "Pasta vazia"}
          </p>
        </div>
      </button>
      <button
        type="button"
        aria-label={`Personalizar a pasta ${pasta.nome}`}
        onClick={aoPersonalizar}
        className="text-ink-muted hover:text-ink hover:bg-surface-muted absolute top-3 right-3 flex size-8 items-center justify-center rounded-input opacity-0 transition focus-visible:opacity-100 group-hover:opacity-100"
      >
        <IconSquareAndPencil className="size-4" fill="currentColor" />
      </button>
    </div>
  );
}
