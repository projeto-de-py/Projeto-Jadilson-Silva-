import * as PopoverPrimitive from "@radix-ui/react-popover";
import { motion } from "motion/react";
import { spring } from "@/lib/motion";
import { cn } from "@/lib/cn";

export function Popover({
  trigger,
  children,
  align = "center",
  sideOffset = 8,
  className,
}) {
  return (
    <PopoverPrimitive.Root>
      <PopoverPrimitive.Trigger asChild>{trigger}</PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content sideOffset={sideOffset} align={align} asChild>
          <motion.div
            className={cn(
              "bg-surface border-border z-50 rounded-card border p-4 shadow-popover",
              "text-14",
              className,
            )}
            initial={{ opacity: 0, scale: 0.96, y: 4 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={spring.snappy}
          >
            {children}
          </motion.div>
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
