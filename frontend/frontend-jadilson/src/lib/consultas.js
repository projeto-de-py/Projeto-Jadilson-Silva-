import { apiJson } from "@/lib/api";

/**
 * Consultas a APIs públicas, feitas PELO SERVIDOR (o navegador nunca chama BrasilAPI,
 * Banco Central ou DataJud direto). O backend valida a entrada, guarda em cache e
 * limita o uso; aqui só montamos as chamadas.
 *
 *   feriados  -> BrasilAPI        cep, cnpj -> BrasilAPI
 *   juros     -> Banco Central    processo  -> DataJud (CNJ)
 *
 * Todas lançam Error com `status` e a mensagem do servidor (ver `apiJson`).
 */
export const consultas = {
  /** Feriados nacionais de `anos` anos seguidos a partir de `ano`: [{ data, nome, tipo }]. */
  feriados: (ano, anos = 3) => apiJson(`consultas/feriados/${ano}?anos=${anos}`),

  /** Endereço de um CEP: { cep, estado, cidade, bairro, rua }. */
  cep: (cep) => apiJson(`consultas/cep/${String(cep).replace(/\D/g, "")}`),

  /** Dados públicos de um CNPJ: { razao_social, nome_fantasia, situacao, municipio, uf }. */
  cnpj: (cnpj) => apiJson(`consultas/cnpj/${String(cnpj).replace(/\D/g, "")}`),

  /** Modalidades de juros que o sistema sabe comparar: [{ slug, nome, unidade }]. */
  seriesJuros: () => apiJson("consultas/juros/series"),

  /** Compara a taxa do contrato (% ao mês) com a média do Banco Central no mês do contrato. */
  compararJuros: (csrf, { serie, dataContrato, taxaMensal }) =>
    apiJson("consultas/juros/comparar", {
      method: "POST",
      csrf,
      body: { serie, data_contrato: dataContrato, taxa_contrato_mensal: taxaMensal },
    }),

  /** Andamentos de um processo no DataJud: { numero, tribunal, encontrado, instancias[] }. */
  processo: (numeroCnj) => apiJson(`consultas/processos/${encodeURIComponent(numeroCnj)}`),
};

/** "5,2" ou "5.2" -> "5.2" (string aceita pela API) ou null se não for um número positivo. */
export function taxaParaApi(texto) {
  const n = Number(String(texto).trim().replace(",", "."));
  return Number.isFinite(n) && n > 0 && n <= 100 ? String(n) : null;
}
