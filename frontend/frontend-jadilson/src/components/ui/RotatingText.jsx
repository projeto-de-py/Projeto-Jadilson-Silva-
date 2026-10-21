import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { cn } from "@/lib/cn";

/**
 * Texto rotativo (inspirado no RotatingText do React Bits), sem o fundo/pílula:
 * cada letra sobe com um pequeno atraso e a palavra anterior sai para cima.
 * Leitores de tela recebem só a palavra atual, sem a animação por letra.
 */
export function RotatingText({
  textos,
  intervalo = 2600,
  stagger = 0.03,
  className,
  letraClassName,
}) {
  const [indice, setIndice] = useState(0);

  useEffect(() => {
    if (textos.length < 2) return undefined;
    const id = setInterval(() => setIndice((i) => (i + 1) % textos.length), intervalo);
    return () => clearInterval(id);
  }, [textos.length, intervalo]);

  const atual = textos[indice];
  const letras = useMemo(() => Array.from(atual), [atual]);

  return (
    <span className={cn("relative inline-flex overflow-hidden pb-[0.12em]", className)}>
      <span className="sr-only">{atual}</span>
      <AnimatePresence mode="popLayout" initial={false}>
        <motion.span key={atual} aria-hidden="true" className="inline-flex whitespace-pre">
          {letras.map((letra, i) => (
            <motion.span
              key={`${atual}-${i}`}
              className={cn("inline-block", letraClassName)}
              initial={{ y: "110%", opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: "-110%", opacity: 0 }}
              transition={{
                type: "spring",
                damping: 28,
                stiffness: 360,
                delay: i * stagger,
              }}
            >
              {letra}
            </motion.span>
          ))}
        </motion.span>
      </AnimatePresence>
    </span>
  );
}
