import * as CheckboxPrimitive from "@radix-ui/react-checkbox";
import { IconCheckmark } from "symbols-react";
import { cn } from "@/lib/cn";

export function Checkbox({ className, ...props }) {
  return (
    <CheckboxPrimitive.Root
      className={cn(
        "border-input bg-surface data-[state=checked]:bg-primary data-[state=checked]:border-primary flex size-5 shrink-0 items-center justify-center rounded-[4px] border transition-colors",
        "hover:border-ink-muted",
        "disabled:cursor-not-allowed disabled:opacity-50",
        "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-bg focus-visible:outline-none",
        className,
      )}
      {...props}
    >
      <CheckboxPrimitive.Indicator className="text-primary-foreground">
        <IconCheckmark className="size-3.5" fill="currentColor" />
      </CheckboxPrimitive.Indicator>
    </CheckboxPrimitive.Root>
  );
}
