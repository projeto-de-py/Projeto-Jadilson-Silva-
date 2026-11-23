import { useState } from "react";
import { Button, Field, Input, Modal } from "@/components/ui";
import { TONS_DE_PASTA, corDoTom } from "@/lib/tonsDePasta";
import { cn } from "@/lib/cn";

/**
 * Cria uma pasta nova (`pasta` nulo) ou personaliza uma existente. Só as pastas do próprio
 * advogado têm nome editável e podem ser excluídas; nas de cliente só a cor muda.
 * Monte este modal apenas enquanto ele estiver aberto: o formulário nasce da `pasta` recebida.
 */
export function ModalPasta({ pasta, aoSalvar, aoExcluir, aoFechar }) {
  const personalizada = !pasta || pasta.tipo === "personalizada";
  const [nome, setNome] = useState(pasta?.nome ?? "");
  const [cor, setCor] = useState(pasta?.cor ?? "neutro");
  const [confirmandoExclusao, setConfirmandoExclusao] = useState(false);

  function salvar(e) {
    e.preventDefault();
    aoSalvar({ nome: nome.trim(), cor });
  }

  return (
    <Modal
      open
      onOpenChange={(aberto) => !aberto && aoFechar()}
      titulo={pasta ? "Personalizar pasta" : "Nova pasta"}
      descricao={personalizada ? "Dê um nome e escolha uma cor. Depois é só mover documentos para ela." : "O nome vem do cadastro do cliente. Aqui você escolhe a cor."}
    >
      <form onSubmit={salvar} className="space-y-6">
        <Field label="Nome da pasta" id="pasta-nome">
          <Input id="pasta-nome" value={nome} onChange={(e) => setNome(e.target.value)} maxLength={60} required disabled={!personalizada} autoFocus={personalizada} placeholder="Ex.: Modelos, Contratos, Pessoal" />
        </Field>

        <div role="radiogroup" aria-label="Cor da pasta" className="space-y-2">
          <p className="text-13 text-ink font-medium">Cor</p>
          <div className="flex flex-wrap gap-2">
            {TONS_DE_PASTA.map((tom) => (
              <button
                key={tom.id}
                type="button"
                role="radio"
                aria-checked={cor === tom.id}
                onClick={() => setCor(tom.id)}
                className={cn("text-13 flex h-10 items-center gap-2 rounded-full border px-4 transition-colors", cor === tom.id ? "border-primary text-ink" : "border-border text-ink-muted hover:text-ink")}
              >
                <span className="size-3.5 rounded-full" style={{ background: corDoTom(tom.id) }} aria-hidden="true" />
                {tom.rotulo}
              </button>
            ))}
          </div>
        </div>

        {confirmandoExclusao && (
          <p role="alert" className="text-13 text-status-vencido-ink">
            Os documentos desta pasta não são apagados: voltam para a pasta do cliente deles. Confirme para excluir.
          </p>
        )}

        <div className="flex flex-wrap items-center justify-between gap-2">
          {pasta?.tipo === "personalizada" ? (
            <Button type="button" variant="ghost" className="text-status-vencido-ink" onClick={() => (confirmandoExclusao ? aoExcluir() : setConfirmandoExclusao(true))}>
              {confirmandoExclusao ? "Confirmar exclusão" : "Excluir pasta"}
            </Button>
          ) : (
            <span />
          )}
          <div className="flex gap-2">
            <Button type="button" variant="secondary" onClick={aoFechar}>Cancelar</Button>
            <Button type="submit" disabled={personalizada && !nome.trim()}>{pasta ? "Salvar" : "Criar pasta"}</Button>
          </div>
        </div>
      </form>
    </Modal>
  );
}
