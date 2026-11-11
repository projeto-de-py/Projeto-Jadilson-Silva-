/**
 * Presets de mola física para Motion e React Spring (@react-spring/web).
 * Overshoot sutil em elementos interativos e aberturas; amortecimento crítico em leitura.
 */
export const spring = {
  // botões, toggles, indicador do menu, popovers
  snappy: { type: "spring", stiffness: 460, damping: 30, mass: 0.75 },
  // modais, toasts, cards interativos
  bouncy: { type: "spring", stiffness: 320, damping: 20, mass: 0.85 },
  // drawers, painéis grandes, transições de página
  gentle: { type: "spring", stiffness: 210, damping: 26, mass: 0.9 },
};

export const reactSpring = {
  // resposta imediata ao hover/clique e abertura de menus
  snappy: { tension: 420, friction: 28, mass: 0.75 },
  // abertura/fechamento de popovers, dropdowns e cards
  fluid: { tension: 310, friction: 24, mass: 0.85 },
  // contadores numéricos e transições suaves de layout
  gentle: { tension: 210, friction: 26, mass: 1 },
  // micro-interação com leve elasticidade
  pop: { tension: 360, friction: 19, mass: 0.8 },
};
