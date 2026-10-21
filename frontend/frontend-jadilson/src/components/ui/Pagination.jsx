import { IconChevronLeft, IconChevronRight } from "symbols-react";
import { cn } from "@/lib/cn";

function janela(pagina, totalPaginas) {
  const inicio = Math.max(1, Math.min(pagina - 2, totalPaginas - 4));
  const fim = Math.min(totalPaginas, inicio + 4);
  const lista = [];
  for (let i = inicio; i <= fim; i++) lista.push(i);
  return lista;
}

export function Pagination({
  pagina,
  totalPaginas,
  totalItens = 0,
  porPagina = 10,
  onMudar,
  className,
}) {
  const total = Math.max(totalPaginas, 1);
  const atual = Math.min(Math.max(pagina, 1), total);
  const primeiro = totalItens === 0 ? 0 : (atual - 1) * porPagina + 1;
  const ultimo = Math.min(atual * porPagina, totalItens);

  return (
    <nav
      aria-label="Paginação"
      className={cn(
        "flex flex-wrap items-center justify-between gap-4",
        className,
      )}
    >
      <p className="text-ink-muted text-14">
        {totalItens > 0
          ? `Mostrando ${primeiro}–${ultimo} de ${totalItens}`
          : "Nenhum registro"}
      </p>

      <div className="flex items-center gap-1">
        <button
          type="button"
          aria-label="Página anterior"
          disabled={atual <= 1}
          onClick={() => onMudar?.(atual - 1)}
          className="border-border text-ink hover:bg-surface-muted flex size-10 items-center justify-center rounded-input border transition-colors disabled:pointer-events-none disabled:opacity-40"
        >
          <IconChevronLeft className="size-4" fill="currentColor" />
        </button>

        {janela(atual, total).map((numero) => (
          <button
            key={numero}
            type="button"
            aria-label={`Página ${numero}`}
            aria-current={numero === atual ? "page" : undefined}
            onClick={() => onMudar?.(numero)}
            className={cn(
              "flex size-10 items-center justify-center rounded-input text-14 font-medium transition-colors",
              numero === atual
                ? "bg-primary text-primary-foreground"
                : "text-ink hover:bg-surface-muted",
            )}
          >
            {numero}
          </button>
        ))}

        <button
          type="button"
          aria-label="Próxima página"
          disabled={atual >= total}
          onClick={() => onMudar?.(atual + 1)}
          className="border-border text-ink hover:bg-surface-muted flex size-10 items-center justify-center rounded-input border transition-colors disabled:pointer-events-none disabled:opacity-40"
        >
          <IconChevronRight className="size-4" fill="currentColor" />
        </button>
      </div>
    </nav>
  );
}
