// Receita "Number pop-in" (transitions.dev): entrada com blur + contador
// que sobe até o valor com easing suave (respeita prefers-reduced-motion).
import { useEffect, useRef, useState } from "react";
import { motion, useReducedMotion } from "motion/react";

export function Contador({ valor, duracao = 900, className }) {
  const reduzido = useReducedMotion();
  const [exibido, setExibido] = useState(reduzido ? valor : 0);
  const frameRef = useRef(0);

  useEffect(() => {
    if (reduzido) return;

    let inicio;
    const passo = (tempo) => {
      if (inicio === undefined) inicio = tempo;
      const p = Math.min((tempo - inicio) / duracao, 1);
      const suave = 1 - Math.pow(1 - p, 3);
      setExibido(Math.round(valor * suave));
      if (p < 1) frameRef.current = requestAnimationFrame(passo);
    };

    frameRef.current = requestAnimationFrame(passo);
    return () => cancelAnimationFrame(frameRef.current);
  }, [valor, duracao, reduzido]);

  return (
    <motion.span
      className={className}
      initial={{ opacity: 0, scale: 0.86, filter: "blur(6px)" }}
      animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
    >
      {reduzido ? valor : exibido}
    </motion.span>
  );
}
