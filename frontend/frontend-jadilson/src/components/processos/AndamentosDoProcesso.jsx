import { useState } from "react";
import { format } from "date-fns";
import { IconPlus } from "symbols-react";
import { Badge, Button, Field, Input, Textarea, useToast } from "@/components/ui";
import { apiJson } from "@/lib/api";
import { useApiDados } from "@/hooks/useApiDados";
import { useSessao } from "@/context/sessao";
import { cn } from "@/lib/cn";

const ORIGEM = {
  DATAJUD: { rotulo: "Tribunal", tom: "primary" },
  MANUAL: { rotulo: "Registrado", tom: "neutral" },
};
const hoje = () => new Date().toISOString().slice(0, 10);
const dia = (iso) => format(new Date(iso), "dd/MM/yyyy");
const temNumeroCnj = (numero) => !String(numero).startsWith("CASO-");

/**
 * Histórico real do processo: o que o advogado registra e o que vem do tribunal (DataJud).
 * "Atualizar pelo tribunal" grava só as movimentações novas; repetir não duplica.
 */
export function AndamentosDoProcesso({ processo }) {
  const { csrf } = useSessao();
  const { toast } = useToast();
  const { dados, carregando, erro, recarregar } = useApiDados(`casos/${processo.id}/andamentos`);
  const [formAberto, setFormAberto] = useState(false);
  const [form, setForm] = useState({ titulo: "", ocorrido_em: hoje(), descricao: "" });
  const [salvando, setSalvando] = useState(false);
  const [sincronizando, setSincronizando] = useState(false);
  const [apagando, setApagando] = useState(null);

  const base = `casos/${processo.id}/andamentos`;
  const andamentos = dados ?? [];

  async function registrar(e) {
    e.preventDefault();
    setSalvando(true);
    try {
      await apiJson(base, {
        method: "POST",
        csrf,
        body: { titulo: form.titulo.trim(), ocorrido_em: form.ocorrido_em, descricao: form.descricao.trim() || null },
      });
      setForm({ titulo: "", ocorrido_em: hoje(), descricao: "" });
      setFormAberto(false);
      recarregar();
    } catch (falha) {
      toast({ tipo: "erro", titulo: "Não foi possível registrar", descricao: falha.message });
    } finally {
      setSalvando(false);
    }
  }

  async function sincronizar() {
    setSincronizando(true);
    try {
      const r = await apiJson(`${base}/sincronizar`, { method: "POST", csrf });
      toast({ tipo: r.encontrado ? "sucesso" : "info", titulo: r.encontrado ? "Tribunal consultado" : "Processo não encontrado", descricao: r.mensagem });
      if (r.novos) recarregar();
    } catch (falha) {
      toast({ tipo: "erro", titulo: "Não foi possível consultar o tribunal", descricao: falha.message });
    } finally {
      setSincronizando(false);
    }
  }

  async function apagar(id) {
    setApagando(id);
    try {
      await apiJson(`${base}/${id}`, { method: "DELETE", csrf });
      recarregar();
    } catch (falha) {
      toast({ tipo: "erro", titulo: "Não foi possível apagar", descricao: falha.message });
    } finally {
      setApagando(null);
    }
  }

  return (
    <section className="space-y-4" aria-labelledby="titulo-andamentos">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 id="titulo-andamentos" className="text-14 text-ink font-semibold">Andamentos ({andamentos.length})</h3>
        <div className="flex gap-2">
          <Button
            variant="secondary"
            className="h-8 px-3 text-12"
            onClick={sincronizar}
            loading={sincronizando}
            disabled={!temNumeroCnj(processo.numero)}
            title={temNumeroCnj(processo.numero) ? "Busca as movimentações no DataJud (CNJ)" : "Cadastre o número CNJ do processo para consultar o tribunal"}
          >
            Atualizar pelo tribunal
          </Button>
          <Button variant="secondary" className="h-8 gap-1.5 px-3 text-12" onClick={() => setFormAberto((v) => !v)} aria-expanded={formAberto}>
            <IconPlus className="size-3.5" fill="currentColor" />
            Registrar
          </Button>
        </div>
      </div>

      {formAberto && (
        <form onSubmit={registrar} className="border-border bg-surface-muted/40 space-y-3 rounded-card border p-4">
          <Field label="O que aconteceu" id="andamento-titulo">
            <Input id="andamento-titulo" required minLength={2} maxLength={160} autoFocus placeholder="Ex.: Audiência realizada" value={form.titulo} onChange={(e) => setForm({ ...form, titulo: e.target.value })} />
          </Field>
          <Field label="Data" id="andamento-data">
            <Input id="andamento-data" type="date" required max={hoje()} value={form.ocorrido_em} onChange={(e) => setForm({ ...form, ocorrido_em: e.target.value })} />
          </Field>
          <Field label="Detalhes (opcional)" id="andamento-descricao">
            <Textarea id="andamento-descricao" maxLength={4000} value={form.descricao} onChange={(e) => setForm({ ...form, descricao: e.target.value })} />
          </Field>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={() => setFormAberto(false)} disabled={salvando}>Cancelar</Button>
            <Button type="submit" loading={salvando}>Salvar andamento</Button>
          </div>
        </form>
      )}

      {erro && <p role="alert" className="text-status-vencido-ink text-13">{erro.message}</p>}
      {carregando && <p className="text-12 text-ink-muted">Carregando andamentos…</p>}
      {!carregando && !erro && andamentos.length === 0 && (
        <p className="border-border text-ink-muted rounded-input border border-dashed px-4 py-3 text-12">
          Nenhum andamento ainda. Registre o primeiro ou use "Atualizar pelo tribunal".
        </p>
      )}

      <ol className="relative space-y-5 border-l border-border pl-6">
        {andamentos.map((a, i) => {
          const origem = ORIGEM[a.origem] ?? ORIGEM.MANUAL;
          return (
            <li key={a.id} className="relative">
              <span className={cn("absolute top-1 -left-7.75 size-3 rounded-full border-2 border-surface", i === 0 ? "bg-primary ring-4 ring-primary/25" : "bg-border")} />
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-14 text-ink font-medium">{a.titulo}</p>
                  <p className="text-12 text-ink-muted mt-0.5 flex items-center gap-2 tabular-nums">
                    {dia(a.ocorrido_em)}
                    <Badge tone={origem.tom} className="px-2 py-0.5">{origem.rotulo}</Badge>
                  </p>
                  {a.descricao && <p className="text-12 text-ink-muted mt-1 whitespace-pre-line">{a.descricao}</p>}
                </div>
                {a.origem === "MANUAL" && (
                  <button type="button" onClick={() => apagar(a.id)} disabled={apagando === a.id} className="text-12 text-ink-muted hover:text-status-vencido-ink shrink-0 transition-colors">
                    Apagar
                  </button>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
