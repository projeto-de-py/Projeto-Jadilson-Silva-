import { cn } from "@/lib/cn";

const sizes = {
  sm: "size-8 text-12",
  md: "size-10 text-14",
  lg: "size-12 text-16",
};

function iniciaisDe(nome) {
  return nome
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((parte) => parte[0])
    .join("")
    .toUpperCase();
}

export function Avatar({ nome = "", src, size = "md", className, ...props }) {
  if (src) {
    return (
      <img
        src={src}
        alt={nome}
        className={cn(
          "rounded-badge object-cover",
          sizes[size] ?? sizes.md,
          className,
        )}
        {...props}
      />
    );
  }

  return (
    <span
      aria-label={nome}
      title={nome}
      className={cn(
        "bg-primary-soft text-primary inline-flex items-center justify-center rounded-badge font-medium",
        sizes[size] ?? sizes.md,
        className,
      )}
      {...props}
    >
      {iniciaisDe(nome) || "?"}
    </span>
  );
}
