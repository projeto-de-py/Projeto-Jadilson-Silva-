import { apiJson } from "@/lib/api";

/**
 * Consultas a APIs públicas, feitas PELO SERVIDOR (o navegador nunca chama BrasilAPI,
 * Banco Central ou DataJud direto). O backend valida a entrada, guarda em cache e
 * limita o uso; aqui só montamos as chamadas.
 *
 *   feriados  -> BrasilAPI        cep, cnpj -> BrasilAPI
 *   juros     -> Banco Central
 *
 * Todas lançam Error com `status` e a mensagem do servidor (ver `apiJson`).
 */
export const consultas = {
  feriados: (ano, anos = 3) => apiJson(`consultas/feriados/${ano}?anos=${anos}`),

  cep: (cep) => apiJson(`consultas/cep/${String(cep).replace(/\D/g, "")}`),

  cnpj: (cnpj) => apiJson(`consultas/cnpj/${String(cnpj).replace(/\D/g, "")}`),

  seriesJuros: () => apiJson("consultas/juros/series"),

  compararJuros: (csrf, { serie, dataContrato, taxaMensal }) =>
    apiJson("consultas/juros/comparar", {
      method: "POST",
      csrf,
      body: { serie, data_contrato: dataContrato, taxa_contrato_mensal: taxaMensal },
    })
};

export function taxaParaApi(texto) {
  const n = Number(String(texto).trim().replace(",", "."));
  return Number.isFinite(n) && n > 0 && n <= 100 ? String(n) : null;
}
