import { useState } from "react";
import { animated, useSpring } from "@react-spring/web";
import { reactSpring } from "@/lib/motion";
import { cn } from "@/lib/cn";

export function Card({ interactive = false, className, children, ...props }) {
  const [hovered, setHovered] = useState(false);
  const mola = useSpring({
    y: interactive && hovered ? -3 : 0,
    scale: interactive && hovered ? 1.008 : 1,
    config: reactSpring.snappy,
  });

  const classes = cn(
    "squircle bg-surface border border-border rounded-card transition-colors duration-fast",
    interactive && "hover:border-primary/40",
    className,
  );

  if (interactive) {
    return (
      <animated.div
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        style={{
          transform: mola.y.to(
            (y) => `translate3d(0, ${y}px, 0) scale(${mola.scale.get()})`,
          ),
        }}
        className={classes}
        {...props}
      >
        {children}
      </animated.div>
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
        "flex items-start justify-between gap-4 p-6 pb-4 sm:p-7 sm:pb-4",
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
    <h3 className={cn("text-18 font-semibold tracking-tight text-ink", className)} {...props}>
      {children}
    </h3>
  );
}

export function CardDescription({ className, children, ...props }) {
  return (
    <p className={cn("text-13 text-ink-muted leading-relaxed", className)} {...props}>
      {children}
    </p>
  );
}

export function CardContent({ className, children, ...props }) {
  return (
    <div className={cn("p-6 pt-0 sm:p-7 sm:pt-0", className)} {...props}>
      {children}
    </div>
  );
}
