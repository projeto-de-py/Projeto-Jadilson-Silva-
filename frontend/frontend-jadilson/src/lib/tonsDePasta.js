/**
 * Cores das pastas, derivadas dos tokens da plataforma (valem nos temas claro e escuro).
 * Cada tom vira três cores: fundo da pasta, frente de baixo e frente de cima.
 */

export const misturar = (cor, porcento) => `color-mix(in srgb, var(${cor}) ${porcento}%, var(--color-surface))`;

// [token da cor, % do fundo, % da frente (baixo), % da frente (cima), cor do número]
export const BASES_DE_PASTA = {
  neutro: ["--color-ink", 26, 38, 30, "var(--color-ink)"],
  verde: ["--color-status-ok", 62, 86, 72, "#052e16"],
  amarelo: ["--color-status-atencao", 62, 88, 74, "#422006"],
  laranja: ["--color-status-hoje", 62, 86, 72, "#431407"],
  vermelho: ["--color-status-vencido", 62, 86, 72, "#450a0a"],
  ardosia: ["--color-status-cumprido", 55, 80, 66, "#0f172a"],
};

export const TONS_DE_PASTA = [
  { id: "neutro", rotulo: "Neutro" },
  { id: "verde", rotulo: "Verde" },
  { id: "amarelo", rotulo: "Amarelo" },
  { id: "laranja", rotulo: "Laranja" },
  { id: "vermelho", rotulo: "Vermelho" },
  { id: "ardosia", rotulo: "Ardósia" },
];

/** Cor de um tom para amostras (bolinhas) fora da pasta. */
export const corDoTom = (tom) => misturar((BASES_DE_PASTA[tom] ?? BASES_DE_PASTA.neutro)[0], 80);
