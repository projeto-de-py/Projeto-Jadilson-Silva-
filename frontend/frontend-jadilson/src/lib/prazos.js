import { addDays, format, isWeekend } from "date-fns";

export const HOJE = new Date(2026, 9, 20);

// Feriados nacionais (e recesso forense) usados na contagem de dias úteis.
const FERIADOS = [
  "2026-01-01", "2026-02-16", "2026-02-17", "2026-04-03", "2026-04-21",
  "2026-05-01", "2026-06-04", "2026-09-07", "2026-10-12", "2026-11-02",
  "2026-11-15", "2026-11-20", "2026-12-25",
];

export function ehFeriado(data) {
  return FERIADOS.includes(format(data, "yyyy-MM-dd"));
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

export function classificar(dias) {
  if (dias < 0) return { tom: "vencido", rotulo: "Vencido", grupo: "vencidos" };
  if (dias === 0) return { tom: "hoje", rotulo: "Vence hoje", grupo: "hoje" };
  if (dias <= 3) return { tom: "atencao", rotulo: `Faltam ${dias} dias`, grupo: "proximos" };
  return { tom: "ok", rotulo: `Faltam ${dias} dias`, grupo: "proximos" };
}

// Pontua o risco de cada prazo: peso por urgência, audiência e atraso.
export function pontuarRisco(prazo) {
  const d = prazo.diasRestantes;
  let pontos = d < 0 ? 100 : d === 0 ? 90 : d <= 2 ? 70 : d <= 5 ? 45 : d <= 10 ? 20 : 8;
  if (prazo.tipo === "Audiência") pontos += 5;
  return Math.min(100, pontos);
}

export function nivelRisco(pontos) {
  if (pontos >= 85) return { rotulo: "Crítico", tom: "vencido" };
  if (pontos >= 60) return { rotulo: "Alto", tom: "hoje" };
  if (pontos >= 35) return { rotulo: "Moderado", tom: "atencao" };
  return { rotulo: "Baixo", tom: "ok" };
}
