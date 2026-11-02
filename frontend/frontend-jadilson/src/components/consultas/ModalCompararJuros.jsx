import { useState } from "react";
import { format } from "date-fns";
import { Badge, Button, Field, Input, Modal, Select } from "@/components/ui";
import { consultas, taxaParaApi } from "@/lib/consultas";
import { useApiDados } from "@/hooks/useApiDados";
import { useSessao } from "@/context/sessao";

const pct = (v) => Number(v).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** Parágrafo pronto para a petição, com os números do Banco Central. */
function paragrafoDaComparacao(r) {
  const mes = format(new Date(`${r.mes_referencia}T12:00:00`), "MM/yyyy");
  const comparacao = r.acima_da_media
    ? `supera em ${pct(r.razao)} vez(es) a taxa média de mercado`
    : "não supera a taxa média de mercado";
  return (
    `A taxa de juros contratada, de ${pct(r.taxa_contrato_mensal)}% ao mês (${pct(r.taxa_contrato_anual)}% ao ano), ${comparacao} ` +
    `divulgada pelo Banco Central do Brasil para a modalidade “${r.serie.nome}” em ${mes}, de ${pct(r.taxa_media_mensal)}% ao mês ` +
    `(${pct(r.taxa_media_anual)}% ao ano) [CONFIRA A FONTE: Sistema Gerenciador de Séries Temporais do Banco Central].`
  );
}

/**
 * Compara a taxa de juros do contrato com a taxa média do Banco Central no mês da
 * contratação (base das ações revisionais). Os números vêm do servidor.
 */
export function ModalCompararJuros({ open, onOpenChange, aoInserir }) {
  const { csrf } = useSessao();
  const series = useApiDados(open ? "consultas/juros/series" : null);
  const [serie, setSerie] = useState("credito-pessoal-nao-consignado");
  const [data, setData] = useState("");
  const [taxa, setTaxa] = useState("");
  const [resultado, setResultado] = useState(null);
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);

  async function comparar(e) {
    e.preventDefault();
    setErro("");
    setResultado(null);
    const taxaApi = taxaParaApi(taxa);
    if (!data) return setErro("Informe a data da contratação.");
    if (!taxaApi) return setErro("Informe a taxa mensal do contrato, entre 0 e 100. Ex.: 5,2");
    setCarregando(true);
    try {
      setResultado(await consultas.compararJuros(csrf, { serie, dataContrato: data, taxaMensal: taxaApi }));
    } catch (falha) {
      setErro(falha.message);
    } finally {
      setCarregando(false);
    }
  }

  return (
    <Modal open={open} onOpenChange={onOpenChange} titulo="Comparar juros com o Banco Central" descricao="Taxa média mensal de mercado no mês da contratação, por modalidade." className="max-w-xl">
      <form onSubmit={comparar} className="space-y-6">
        <Field label="Modalidade de crédito" id="juros-serie">
          <Select id="juros-serie" value={serie} onChange={(e) => setSerie(e.target.value)} disabled={series.carregando}>
            {(series.dados ?? []).map((s) => (
              <option key={s.slug} value={s.slug}>{s.nome}</option>
            ))}
          </Select>
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Data da contratação" id="juros-data">
            <Input id="juros-data" type="date" max={format(new Date(), "yyyy-MM-dd")} value={data} onChange={(e) => setData(e.target.value)} required />
          </Field>
          <Field label="Taxa do contrato (% ao mês)" id="juros-taxa">
            <Input id="juros-taxa" inputMode="decimal" placeholder="5,2" value={taxa} onChange={(e) => setTaxa(e.target.value)} required />
          </Field>
        </div>

        {erro && <p role="alert" className="text-status-vencido-ink text-13">{erro}</p>}

        {resultado && (
          <div className="bg-surface-muted/50 border-border space-y-4 rounded-card border p-6" role="status">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={resultado.acima_da_media ? "atencao" : "ok"}>{resultado.faixa}</Badge>
              <span className="text-12 text-ink-muted">Referência: {format(new Date(`${resultado.mes_referencia}T12:00:00`), "MM/yyyy")}</span>
            </div>
            <dl className="grid grid-cols-2 gap-4 text-14">
              <div><dt className="text-12 text-ink-muted">Taxa do contrato</dt><dd className="text-ink font-semibold tabular-nums">{pct(resultado.taxa_contrato_mensal)}% a.m. · {pct(resultado.taxa_contrato_anual)}% a.a.</dd></div>
              <div><dt className="text-12 text-ink-muted">Média do Banco Central</dt><dd className="text-ink font-semibold tabular-nums">{pct(resultado.taxa_media_mensal)}% a.m. · {pct(resultado.taxa_media_anual)}% a.a.</dd></div>
              <div><dt className="text-12 text-ink-muted">Diferença</dt><dd className="text-ink font-semibold tabular-nums">{pct(resultado.diferenca_pontos)} p.p.</dd></div>
              <div><dt className="text-12 text-ink-muted">Taxa ÷ média</dt><dd className="text-ink font-semibold tabular-nums">{pct(resultado.razao)}×</dd></div>
            </dl>
            <p className="text-12 text-ink-muted">{resultado.aviso}</p>
            {aoInserir && (
              <Button variant="secondary" onClick={() => { aoInserir(paragrafoDaComparacao(resultado)); onOpenChange(false); }}>
                Inserir no documento
              </Button>
            )}
          </div>
        )}

        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => onOpenChange(false)}>Fechar</Button>
          <Button type="submit" loading={carregando}>Comparar</Button>
        </div>
      </form>
    </Modal>
  );
}
