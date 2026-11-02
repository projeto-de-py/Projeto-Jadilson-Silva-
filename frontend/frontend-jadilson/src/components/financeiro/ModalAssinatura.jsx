import { useState } from "react";
import { Button, Field, Input, Modal, Textarea, useToast } from "@/components/ui";
import { SeletorCliente } from "@/components/financeiro/SeletorCliente";
import { apiJson } from "@/lib/api";
import { gerarPdfBase64 } from "@/lib/documentos";
import { useSessao } from "@/context/sessao";

/**
 * Envia o documento aberto no editor para assinatura eletrônica (ZapSign):
 * gera o PDF no navegador e manda para POST /api/assinaturas, que entrega o link
 * ao WhatsApp/e-mail do cliente cadastrado.
 */
export function ModalAssinatura({ open, onOpenChange, tituloInicial, obterHtml }) {
  const { csrf } = useSessao();
  const { toast } = useToast();
  const [clienteId, setClienteId] = useState("");
  const [titulo, setTitulo] = useState(tituloInicial);
  const [mensagem, setMensagem] = useState("");
  const [etapa, setEtapa] = useState(""); // "" | "gerando" | "enviando"
  const [erro, setErro] = useState("");

  async function enviar(e) {
    e.preventDefault();
    setErro("");
    if (!clienteId) return setErro("Escolha o cliente que vai assinar.");
    try {
      setEtapa("gerando");
      const pdf = await gerarPdfBase64(obterHtml());
      setEtapa("enviando");
      const criada = await apiJson("assinaturas", {
        method: "POST",
        csrf,
        body: { titulo: titulo.trim() || tituloInicial, cliente_id: Number(clienteId), pdf_base64: pdf, mensagem: mensagem.trim() || null },
      });
      toast({ tipo: "sucesso", titulo: "Enviado para assinatura", descricao: `Acompanhe em Financeiro > Assinaturas (#${criada.id}).` });
      onOpenChange(false);
    } catch (falha) {
      setErro(falha.message || "Não foi possível enviar o documento.");
    } finally {
      setEtapa("");
    }
  }

  const ocupado = etapa !== "";

  return (
    <Modal open={open} onOpenChange={(v) => !ocupado && onOpenChange(v)} titulo="Enviar para assinatura" descricao="O cliente recebe o link pelo WhatsApp ou e-mail cadastrados e assina pelo celular." className="max-w-xl">
      <form onSubmit={enviar} className="space-y-6">
        <SeletorCliente valor={clienteId} aoMudar={setClienteId} id="ass-cliente" />
        <Field label="Título do documento" id="ass-titulo">
          <Input id="ass-titulo" maxLength={200} value={titulo} onChange={(e) => setTitulo(e.target.value)} required />
        </Field>
        <Field label="Mensagem para o cliente (opcional)" id="ass-msg">
          <Textarea id="ass-msg" maxLength={500} value={mensagem} onChange={(e) => setMensagem(e.target.value)} />
        </Field>

        <p className="text-12 text-ink-muted">
          O documento sai como PDF do jeito que está no editor. Revise o texto antes de enviar: depois de assinado, não há como alterá-lo.
        </p>

        {erro && <p role="alert" className="text-status-vencido-ink text-13">{erro}</p>}

        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => onOpenChange(false)} disabled={ocupado}>Cancelar</Button>
          <Button type="submit" loading={ocupado}>
            {etapa === "gerando" ? "Gerando PDF…" : etapa === "enviando" ? "Enviando…" : "Enviar para assinar"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
