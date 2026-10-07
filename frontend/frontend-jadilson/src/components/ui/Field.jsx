import { cn } from "@/lib/cn";

/**
 * Rótulo + controle + (helper | erro). Erro sempre diz como corrigir.
 */
export function Field({ label, hint, error, id, children, className }) {
  return (
    <div className={cn("space-y-1.5", className)}>
      {label && (
        <label htmlFor={id} className="text-14 block font-medium">
          {label}
        </label>
      )}
      {children}
      {error ? (
        <p role="alert" className="text-12 text-status-vencido-ink">
          {error}
        </p>
      ) : (
        hint && <p className="text-12 text-ink-muted">{hint}</p>
      )}
    </div>
  );
}
