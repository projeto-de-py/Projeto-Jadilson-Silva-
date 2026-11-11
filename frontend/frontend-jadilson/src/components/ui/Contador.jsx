import { animated, useSpring } from "@react-spring/web";
import { reactSpring } from "@/lib/motion";

/** Contador numérico animado com física de mola (@react-spring/web). */
export function Contador({ valor = 0, className }) {
  const { numero, opacity, y } = useSpring({
    from: { numero: 0, opacity: 0, y: 6 },
    to: { numero: Number(valor) || 0, opacity: 1, y: 0 },
    config: reactSpring.gentle,
  });

  return (
    <animated.span
      className={className}
      style={{
        opacity,
        transform: y.to((v) => `translate3d(0, ${v}px, 0)`),
      }}
    >
      {numero.to((n) => Math.round(n))}
    </animated.span>
  );
}
