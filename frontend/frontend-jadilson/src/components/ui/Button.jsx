import React from "react";
import { motion } from "motion/react";
import { ThinkingOrb } from "thinking-orbs";
import { spring } from "@/lib/motion";
import { cn } from "@/lib/cn";

const variants = {
  primary: "bg-primary text-primary-foreground hover:bg-primary-hover",
  secondary:
    "bg-surface text-ink border border-border hover:bg-surface-muted hover:text-ink",
  ghost: "text-ink hover:bg-surface-muted",
  danger:
    "bg-status-vencido text-destructive-foreground hover:bg-status-vencido-ink",
};

export function Button({
  variant = "primary",
  loading = false,
  disabled = false,
  asChild = false,
  className,
  children,
  ...props
}) {
  const classes = cn(
    "inline-flex items-center justify-center font-medium whitespace-nowrap transition-colors",
    "h-10 gap-2 rounded-input px-4 text-14",
    "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-bg focus-visible:outline-none",
    "disabled:pointer-events-none disabled:opacity-50",
    variants[variant] ?? variants.primary,
    className,
  );

  if (asChild) {
    return React.cloneElement(children, {
      className: cn(classes, children.props.className),
    });
  }

  return (
    <motion.button
      type="button"
      whileTap={{ scale: 0.96 }}
      transition={spring.snappy}
      className={classes}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading && <ThinkingOrb state="working" size={20} theme="dark" />}
      {children}
    </motion.button>
  );
}
