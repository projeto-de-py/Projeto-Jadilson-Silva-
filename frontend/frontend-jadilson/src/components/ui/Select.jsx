import { ChevronDown } from "lucide-react";
import { Field } from "./Field";
import { cn } from "@/lib/cn";

const baseClasses = [
  "h-10 w-full appearance-none rounded-input border border-input bg-surface px-3 pe-9 text-14",
  "focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
  "disabled:cursor-not-allowed disabled:opacity-50",
].join(" ");

export function Select({
  label,
  hint,
  error,
  id,
  className,
  children,
  ...props
}) {
  const select = (
    <div className="relative">
      <select
        id={id}
        aria-invalid={error ? true : undefined}
        className={cn(
          baseClasses,
          error && "border-status-vencido focus-visible:ring-status-vencido",
          className,
        )}
        {...props}
      >
        {children}
      </select>
      <ChevronDown
        aria-hidden="true"
        className="text-ink-muted pointer-events-none absolute end-3 top-1/2 size-4 -translate-y-1/2"
      />
    </div>
  );

  if (!label && !hint && !error) {
    return select;
  }

  return (
    <Field label={label} hint={hint} error={error} id={id}>
      {select}
    </Field>
  );
}
