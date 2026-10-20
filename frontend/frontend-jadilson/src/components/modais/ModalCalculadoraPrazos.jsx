import { useMemo, useState } from "react";
import { format, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";
import { IconFunction, IconCalendar, IconInfoCircle } from "symbols-react";
import { Modal, Input, Field, Select, Badge } from "@/components/ui";
import { HOJE, somarPrazo } from "@/lib/prazos";

const PRAZOS_COMUNS = [
  { rotulo: "Contestação (15)", dias: 15 },
  { rotulo: "Apelação / Recurso (15)", dias: 15 },
  { rotulo: "Embargos de declaração (5)", dias: 5 },
  { rotulo: "Manifestação (5)", dias: 5 },
  { rotulo: "Juizado: recurso inominado (10)", dias: 10 },
];

export function ModalCalculadoraPrazos({ open, onOpenChange }) {
  const [inicio, setInicio] = useState(format(HOJE, "yyyy-MM-dd"));
  const [dias, setDias] = useState(15);
  const [contagem, setContagem] = useState("uteis");

  const resultado = useMemo(() => {
    const n = Number(dias);
    if (!inicio || !Number.isFinite(n) || n < 1) return null;
    return somarPrazo(parseISO(inicio), n, contagem === "uteis");
  }, [inicio, dias, contagem]);

  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      titulo="Calculadora de prazos"
      descricao="Contagem a partir do dia seguinte à intimação, com prorrogação para o próximo dia útil."
    >
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2">
          {PRAZOS_COMUNS.map((p) => (
            <button
              key={p.rotulo}
              type="button"
              onClick={() => setDias(p.dias)}
              className="border-border text-ink-muted hover:text-ink hover:border-primary/60 rounded-badge border px-4 py-1 text-12 transition-colors"
            >
              {p.rotulo}
            </button>
          ))}
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="Data da intimação">
            <Input type="date" value={inicio} onChange={(e) => setInicio(e.target.value)} />
          </Field>
          <Field label="Quantidade de dias">
            <Input type="number" min={1} max={365} value={dias} onChange={(e) => setDias(e.target.value)} />
          </Field>
          <Field label="Contagem">
            <Select value={contagem} onChange={(e) => setContagem(e.target.value)}>
              <option value="uteis">Dias úteis</option>
              <option value="corridos">Dias corridos</option>
            </Select>
          </Field>
        </div>

        <div className="bg-primary-soft border-primary/30 rounded-card border p-6">
          <p className="flex items-center gap-2 text-12 text-ink-muted">
            <IconCalendar className="size-3.5 text-accent" fill="currentColor" />
            Data fatal
          </p>
          {resultado ? (
            <>
              <p className="font-heading text-24 mt-1 font-bold text-ink capitalize">
                {format(resultado.fim, "EEEE, d 'de' MMMM 'de' yyyy", { locale: ptBR })}
              </p>
              <div className="mt-4 flex flex-wrap items-center gap-2">
                <Badge tone="primary">
                  <IconFunction className="size-3" fill="currentColor" />
                  {dias} dias {contagem === "uteis" ? "úteis" : "corridos"}
                </Badge>
                {resultado.pulados.length > 0 && (
                  <Badge tone="neutral">{resultado.pulados.length} dias não úteis ignorados</Badge>
                )}
              </div>
            </>
          ) : (
            <p className="text-14 mt-1 text-ink-muted">Informe a data e a quantidade de dias.</p>
          )}
        </div>

        <p className="flex items-start gap-2 text-12 text-ink-muted">
          <IconInfoCircle className="mt-0.5 size-3.5 shrink-0" fill="currentColor" />
          Considera feriados nacionais de 2026. Confira feriados locais e suspensões de prazo no tribunal.
        </p>
      </div>
    </Modal>
  );
}
