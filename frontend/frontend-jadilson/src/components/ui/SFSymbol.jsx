import { cn } from "@/lib/cn";

export function SFSymbol({ icon: Icon, className, ...props }) {
  if (!Icon) return null;
  return (
    <Icon
      fill="currentColor"
      className={cn("size-4 shrink-0", className)}
      aria-hidden="true"
      {...props}
    />
  );
}
