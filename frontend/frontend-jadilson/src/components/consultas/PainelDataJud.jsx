import { useState } from "react";
import { format } from "date-fns";
import { Badge, Button, Field, Input } from "@/components/ui";
import { consultas } from "@/lib/consultas";

const dia = (iso) => (iso ? format(new Date(iso), "dd/MM/yyyy") : "—");

/**
 * Consulta os andamentos REAIS de um processo no DataJud (CNJ), pelo número CNJ.
 * Mostra tribunal, classe, órgão julgador e as movimentações mais recentes.
 */
export function PainelDataJud({ numeroInicial = "" }) {
  const [numero, setNumero] = useState(numeroInicial);
  const [consulta, setConsulta] = useState(null);
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);

  async function buscar(e) {
    e.preventDefault();
    setErro("");
    setConsulta(null);
    setCarregando(true);
    try {
      setConsulta(await consultas.processo(numero.trim()));
    } catch (falha) {
      setErro(falha.message);
    } finally {
      setCarregando(false);
    }
  }

  return (
    <section className="border-border bg-surface-muted/40 space-y-4 rounded-card border p-6" aria-labelledby="titulo-datajud">
      <div>
        <h3 id="titulo-datajud" className="text-14 text-ink font-semibold">Andamentos no tribunal (DataJud)</h3>
        <p className="text-12 text-ink-muted mt-1">Consulta pública do CNJ pelo número do processo.</p>
      </div>

      <form onSubmit={buscar} className="space-y-4">
        <Field label="Número CNJ" id="datajud-numero">
          <Input id="datajud-numero" placeholder="0000000-00.0000.0.00.0000" value={numero} onChange={(e) => setNumero(e.target.value)} required />
        </Field>
        <Button type="submit" loading={carregando} className="w-full">Buscar no DataJud</Button>
      </form>

      {erro && <p role="alert" className="text-status-vencido-ink text-13">{erro}</p>}

      {consulta && !consulta.encontrado && (
        <p role="status" className="text-13 text-ink-muted">
          Nenhum registro em {consulta.tribunal.toUpperCase()} para {consulta.numero}. O processo pode estar em segredo de justiça ou ainda não ter sido enviado ao DataJud.
        </p>
      )}

      {consulta?.instancias.map((i) => (
        <article key={`${i.grau}-${i.numero}`} className="space-y-4">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="primary">{i.tribunal || consulta.tribunal.toUpperCase()}</Badge>
              {i.grau && <Badge tone="neutral">{i.grau}</Badge>}
            </div>
            <p className="text-14 text-ink font-medium">{i.classe || "Classe não informada"}</p>
            <p className="text-12 text-ink-muted">{i.orgao_julgador || "Órgão não informado"} · ajuizado em {dia(i.data_ajuizamento)}</p>
            {i.assuntos.length > 0 && <p className="text-12 text-ink-muted">Assuntos: {i.assuntos.join("; ")}</p>}
          </div>
          <ol className="border-border space-y-4 border-l pl-4">
            {i.movimentos.slice(0, 15).map((m, n) => (
              <li key={`${m.data}-${n}`}>
                <p className="text-13 text-ink">{m.nome}</p>
                <p className="text-12 text-ink-muted tabular-nums">{dia(m.data)}{m.complemento ? ` · ${m.complemento}` : ""}</p>
              </li>
            ))}
          </ol>
          {i.movimentos.length > 15 && <p className="text-12 text-ink-muted">Mostrando as 15 movimentações mais recentes de {i.movimentos.length}.</p>}
        </article>
      ))}
      {consulta && <p className="text-11 text-ink-muted">{consulta.aviso}</p>}
    </section>
  );
}
