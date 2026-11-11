import { useState } from "react";
import { Button, Field, Input, Modal, Select, useToast } from "@/components/ui";
import { SeletorCliente } from "@/components/financeiro/SeletorCliente";
import { apiJson } from "@/lib/api";
import { useSessao } from "@/context/sessao";
import { cn } from "@/lib/cn";

const hojeIso = () => new Date().toISOString().slice(0, 10);

// "1.500,00" ou "1500.5" -> "1500.50"
function valorParaApi(texto) {
  const limpo = texto.trim().replace(/\s|R\$/g, "");
  const normal = limpo.includes(",") ? limpo.replace(/\./g, "").replace(",", ".") : limpo;
  const n = Number(normal);
  return Number.isFinite(n) && n > 0 ? n.toFixed(2) : null;
}

export function ModalNovaCobranca({ open, onOpenChange, aoCriada }) {
  const { csrf } = useSessao();
  const { toast } = useToast();
  const [clienteId, setClienteId] = useState("");
  const [valor, setValor] = useState("");
  const [vencimento, setVencimento] = useState(hojeIso());
  const [forma, setForma] = useState("PIX");
  const [parcelas, setParcelas] = useState("1");
  const [descricao, setDescricao] = useState("Honorários advocatícios");
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function emitir(e) {
    e.preventDefault();
    setErro("");
    const valorApi = valorParaApi(valor);
    if (!clienteId) return setErro("Escolha o cliente.");
    if (!valorApi) return setErro("Informe um valor maior que zero. Ex.: 1.500,00");
    setEnviando(true);
    try {
      const criadas = await apiJson("financeiro/cobrancas", {
        method: "POST",
        csrf,
        body: { cliente_id: Number(clienteId), valor: valorApi, vencimento, forma, parcelas: Number(parcelas), descricao: descricao.trim() || null },
      });
      toast({ tipo: "sucesso", titulo: criadas.length > 1 ? `${criadas.length} parcelas emitidas` : "Cobrança emitida", descricao: "O cliente já pode pagar pelo link da fatura." });
      aoCriada();
      onOpenChange(false);
      setValor("");
    } catch (falha) {
      setErro(falha.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Modal open={open} onOpenChange={onOpenChange} titulo="Nova cobrança" descricao="Honorários por Pix ou boleto, à vista ou parcelados." className="max-w-xl">
      <form onSubmit={emitir} className="space-y-6">
        <SeletorCliente valor={clienteId} aoMudar={setClienteId} id="cob-cliente" />

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Valor total (R$)" id="cob-valor">
            <Input id="cob-valor" inputMode="decimal" placeholder="1.500,00" value={valor} onChange={(e) => setValor(e.target.value)} required />
          </Field>
          <Field label="1º vencimento" id="cob-venc">
            <Input id="cob-venc" type="date" min={hojeIso()} value={vencimento} onChange={(e) => setVencimento(e.target.value)} required />
          </Field>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <p className="text-14 font-medium">Forma de pagamento</p>
            <div role="group" aria-label="Forma de pagamento" className="bg-surface-muted border-border flex rounded-input border p-1">
              {["PIX", "BOLETO"].map((f) => (
                <button key={f} type="button" aria-pressed={forma === f} onClick={() => setForma(f)}
                  className={cn("text-13 h-8 flex-1 rounded-input font-medium transition-colors", forma === f ? "bg-primary text-primary-foreground" : "text-ink-muted hover:text-ink")}>
                  {f === "PIX" ? "Pix" : "Boleto"}
                </button>
              ))}
            </div>
          </div>
          <Field label="Parcelas" id="cob-parcelas">
            <Select id="cob-parcelas" value={parcelas} onChange={(e) => setParcelas(e.target.value)}>
              {Array.from({ length: 24 }, (_, i) => i + 1).map((n) => (
                <option key={n} value={String(n)}>{n === 1 ? "À vista" : `${n}x`}</option>
              ))}
            </Select>
          </Field>
        </div>

        <Field label="Descrição" id="cob-desc" hint="Aparece na fatura do cliente.">
          <Input id="cob-desc" maxLength={200} value={descricao} onChange={(e) => setDescricao(e.target.value)} />
        </Field>

        {erro && <p role="alert" className="text-status-vencido-ink text-13">{erro}</p>}

        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => onOpenChange(false)}>Cancelar</Button>
          <Button type="submit" loading={enviando}>Emitir cobrança</Button>
        </div>
      </form>
    </Modal>
  );
}
