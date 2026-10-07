import { motion } from "motion/react";
import { spring } from "@/lib/motion";
import { cn } from "@/lib/cn";

export function Card({ interactive = false, className, children, ...props }) {
  const classes = cn("bg-surface border border-border rounded-card", className);

  if (interactive) {
    return (
      <motion.div
        whileHover={{ y: -2 }}
        transition={spring.snappy}
        className={classes}
        {...props}
      >
        {children}
      </motion.div>
    );
  }

  return (
    <div className={classes} {...props}>
      {children}
    </div>
  );
}

export function CardHeader({ className, children, ...props }) {
  return (
    <div
      className={cn(
        "flex items-start justify-between gap-4 p-6 pb-3",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardTitle({ className, children, ...props }) {
  return (
    <h3 className={cn("text-20 font-semibold", className)} {...props}>
      {children}
    </h3>
  );
}

export function CardDescription({ className, children, ...props }) {
  return (
    <p className={cn("text-14 text-ink-muted", className)} {...props}>
      {children}
    </p>
  );
}

export function CardContent({ className, children, ...props }) {
  return (
    <div className={cn("p-6 pt-0", className)} {...props}>
      {children}
    </div>
  );
}
