import { addDays, format, isWeekend } from "date-fns";

export const HOJE = new Date(2026, 9, 20);

// Feriados nacionais (e recesso forense) usados na contagem de dias úteis.
const FERIADOS = [
  "2026-01-01", "2026-02-16", "2026-02-17", "2026-04-03", "2026-04-21",
  "2026-05-01", "2026-06-04", "2026-09-07", "2026-10-12", "2026-11-02",
  "2026-11-15", "2026-11-20", "2026-12-25",
];

// Feriados carregados do servidor (BrasilAPI). Somam-se à lista fixa acima, que continua
// valendo como plano B quando o servidor não responde.
const feriadosDoServidor = new Set();

/** Registra feriados vindos da API: aceita [{ data: "2026-01-01" }, ...]. */
export function definirFeriados(lista) {
  lista.forEach((f) => feriadosDoServidor.add(f.data));
}

export function ehFeriado(data) {
  const iso = format(data, "yyyy-MM-dd");
  return feriadosDoServidor.has(iso) || FERIADOS.includes(iso);
}

export function ehDiaUtil(data) {
  return !isWeekend(data) && !ehFeriado(data);
}

// Soma `dias` a partir de `inicio` (o dia da intimação não conta, CPC art. 224).
export function somarPrazo(inicio, dias, uteis) {
  let atual = inicio;
  let restantes = dias;
  const pulados = [];
  while (restantes > 0) {
    atual = addDays(atual, 1);
    if (!uteis || ehDiaUtil(atual)) restantes -= 1;
    else pulados.push(atual);
  }
  // Prazo que termina em dia não útil prorroga para o próximo útil.
  while (!ehDiaUtil(atual)) {
    pulados.push(atual);
    atual = addDays(atual, 1);
  }
  return { fim: atual, pulados };
}

// Situação do prazo em linguagem simples (substitui a antiga nota de risco).
export function situacaoPrazo(dias) {
  if (dias < 0) return { tom: "vencido", rotulo: "Vencido" };
  if (dias === 0) return { tom: "hoje", rotulo: "Vence hoje" };
  if (dias <= 3) return { tom: "atencao", rotulo: "Perto de vencer" };
  return { tom: "ok", rotulo: "No prazo" };
}

export function textoDias(dias) {
  if (dias < 0) return `Venceu há ${-dias} ${-dias === 1 ? "dia" : "dias"}`;
  if (dias === 0) return "Vence hoje";
  if (dias === 1) return "Falta 1 dia";
  return `Faltam ${dias} dias`;
}

export function classificar(dias) {
  const situacao = situacaoPrazo(dias);
  const grupo = dias < 0 ? "vencidos" : dias === 0 ? "hoje" : "proximos";
  return { ...situacao, grupo, detalhe: textoDias(dias) };
}
