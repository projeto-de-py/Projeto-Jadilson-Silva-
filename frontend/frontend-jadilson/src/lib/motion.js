/**
 * Presets de mola (guia 5.6).
 * Overshoot só em feedback de ação; nunca em conteúdo de leitura rápida.
 */
export const spring = {
  // botões, toggles, indicador do menu
  snappy: { type: "spring", stiffness: 500, damping: 32, mass: 0.7 },
  // modais, toasts, StatCard, "cumprir prazo"
  bouncy: { type: "spring", stiffness: 320, damping: 16, mass: 0.9 },
  // drawers, painéis grandes, layout shifts
  gentle: { type: "spring", stiffness: 180, damping: 22 },
};
