import { motion } from "motion/react";
import { cn } from "@/lib/cn";

// Distância dos três círculos ao centro em cada estado: aberto (parado),
// trabalhando (respira) e pronto (se fecham em um só).
const ESTADOS = {
  parado: { d: [7, 8, 7], giro: 28 },
  trabalhando: { d: [5, 12, 5], giro: 3.2 },
  pronto: { d: [2, 2, 2], giro: 8 },
};

const ANGULOS = [-90, 30, 150];

/** Marca da IA: três círculos translúcidos que se sobrepõem e giram. */
export function LogoIA({ estado = "parado", tamanho = 40, cor = "var(--color-ink)", className }) {
  const { d, giro } = ESTADOS[estado] ?? ESTADOS.parado;
  return (
    <svg
      viewBox="0 0 64 64"
      width={tamanho}
      height={tamanho}
      aria-hidden="true"
      className={cn("shrink-0 overflow-visible", className)}
      style={{ filter: `drop-shadow(0 0 8px color-mix(in srgb, ${cor} 28%, transparent))` }}
    >
      {/* O giro é CSS com origem fixa no centro do desenho (32,32): assim o conjunto
          nunca sai do eixo, mesmo quando os círculos se aproximam e se afastam. */}
      <g className="logo-ia-giro" style={{ animationDuration: `${giro}s` }}>
        {ANGULOS.map((a) => {
          const rad = (a * Math.PI) / 180;
          return (
            <motion.circle
              key={a}
              r="15"
              fill={`color-mix(in srgb, ${cor} 10%, transparent)`}
              stroke={`color-mix(in srgb, ${cor} 70%, transparent)`}
              strokeWidth="1.2"
              initial={false}
              animate={{
                cx: d.map((v) => 32 + Math.cos(rad) * v),
                cy: d.map((v) => 32 + Math.sin(rad) * v),
              }}
              transition={{ duration: estado === "trabalhando" ? 1.8 : 3.2, repeat: Infinity, ease: "easeInOut" }}
            />
          );
        })}
      </g>
    </svg>
  );
}
