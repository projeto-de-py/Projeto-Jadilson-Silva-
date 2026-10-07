import { cn } from "@/lib/cn";

const tones = {
  neutral: "bg-surface-muted text-ink-muted",
  primary: "bg-primary-soft text-primary",
  vencido: "bg-status-vencido-soft text-status-vencido-ink",
  hoje: "bg-status-hoje-soft text-status-hoje-ink",
  critico: "bg-status-critico-soft text-status-critico-ink",
  atencao: "bg-status-atencao-soft text-status-atencao-ink",
  ok: "bg-status-ok-soft text-status-ok-ink",
  cumprido: "bg-status-cumprido-soft text-status-cumprido-ink",
};

export function Badge({ tone = "neutral", className, children, ...props }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-badge px-2.5 py-0.5 text-12 font-medium",
        tones[tone] ?? tones.neutral,
        className,
      )}
      {...props}
    >
      {children}
    </span>
  );
}
