import { cn } from "@/lib/cn";

export function EmptyState({ icon: Icon, titulo, descricao, acao, className }) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-4 rounded-card border border-dashed border-border bg-surface px-8 py-14 text-center",
        className,
      )}
    >
      {Icon && (
        <span className="bg-surface-muted text-ink-muted flex size-10 items-center justify-center rounded-badge">
          <Icon aria-hidden="true" className="size-5" />
        </span>
      )}
      <div className="space-y-1">
        <p className="text-16 font-medium">{titulo}</p>
        {descricao && (
          <p className="text-14 text-ink-muted mx-auto max-w-prose">
            {descricao}
          </p>
        )}
      </div>
      {acao}
    </div>
  );
}
