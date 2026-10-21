import { Field } from "./Field";
import { cn } from "@/lib/cn";

const baseClasses = [
  "flex h-10 w-full rounded-input border border-input bg-surface px-4 py-2 text-14",
  "placeholder:text-ink-muted focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
  "disabled:cursor-not-allowed disabled:opacity-50",
].join(" ");

export function Input({
  label,
  hint,
  error,
  id,
  className,
  type = "text",
  ...props
}) {
  const input = (
    <input
      type={type}
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
    return input;
  }

  return (
    <Field label={label} hint={hint} error={error} id={id}>
      {input}
    </Field>
  );
}
