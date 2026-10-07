import * as SwitchPrimitive from "@radix-ui/react-switch";
import { cn } from "@/lib/cn";

export function Switch({ className, ...props }) {
  return (
    <SwitchPrimitive.Root
      className={cn(
        "border-border bg-surface-muted relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-badge border transition-colors",
        "data-[state=checked]:bg-primary data-[state=checked]:border-primary",
        "disabled:cursor-not-allowed disabled:opacity-50",
        "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-bg focus-visible:outline-none",
        className,
      )}
      {...props}
    >
      <SwitchPrimitive.Thumb className="bg-surface pointer-events-none block size-5 rounded-badge shadow-sm transition-transform translate-x-0.5 data-[state=checked]:translate-x-5" />
    </SwitchPrimitive.Root>
  );
}
