import { Field } from "./Field";
import { cn } from "@/lib/cn";

const baseClasses = [
  "flex min-h-24 w-full rounded-input border border-input bg-surface px-3 py-2 text-14",
  "placeholder:text-ink-muted focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
  "disabled:cursor-not-allowed disabled:opacity-50 resize-y",
].join(" ");

export function Textarea({ label, hint, error, id, className, ...props }) {
  const textarea = (
    <textarea
      id={id}
      aria-invalid={error ? true : undefined}
      className={cn(
        baseClasses,
        error && "border-status-vencido focus-visible:ring-status-vencido",
        className,
      )}
      {...props}
    />
  );

  if (!label && !hint && !error) {
    return textarea;
  }

  return (
    <Field label={label} hint={hint} error={error} id={id}>
      {textarea}
    </Field>
  );
}
