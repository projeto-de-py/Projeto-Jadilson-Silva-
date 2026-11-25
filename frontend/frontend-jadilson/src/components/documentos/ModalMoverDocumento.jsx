import { IconCheckmarkCircleFill } from "symbols-react";
import { Modal } from "@/components/ui";
import { corDoTom } from "@/lib/tonsDePasta";
import { cn } from "@/lib/cn";

/** Escolhe a pasta de um documento. "Automática" devolve o documento ao cliente do processo dele. */
export function ModalMoverDocumento({ doc, pastas, pastaAtualId, aoEscolher, aoFechar }) {
  const opcoes = pastas.filter((p) => p.tipo !== "avulsa");
  const automatica = pastaAtualId == null;

  return (
    <Modal open={!!doc} onOpenChange={(aberto) => !aberto && aoFechar()} titulo="Mover para a pasta" descricao={doc ? `“${doc.titulo}”` : undefined}>
      <ul className="space-y-2" role="radiogroup" aria-label="Pastas">
        <li>
          <Opcao ativa={automatica} onClick={() => aoEscolher(null)} titulo="Automática" detalhe="Pasta do cliente do processo vinculado" />
        </li>
        {opcoes.map((p) => (
          <li key={p.id}>
            <Opcao ativa={pastaAtualId === p.id} onClick={() => aoEscolher(p)} titulo={p.nome} detalhe={p.tipo === "personalizada" ? "Minha pasta" : "Cliente"} cor={corDoTom(p.cor)} />
          </li>
        ))}
      </ul>
    </Modal>
  );
}

function Opcao({ ativa, onClick, titulo, detalhe, cor }) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={ativa}
      onClick={onClick}
      className={cn("flex w-full items-center gap-3 rounded-input border p-3 text-left transition-colors", ativa ? "border-primary bg-primary-soft" : "border-border hover:bg-surface-muted")}
    >
      <span className="size-3.5 shrink-0 rounded-full border border-border" style={cor ? { background: cor } : undefined} aria-hidden="true" />
      <span className="min-w-0 flex-1">
        <span className="text-14 text-ink block truncate font-medium">{titulo}</span>
        <span className="text-12 text-ink-muted block truncate">{detalhe}</span>
      </span>
      {ativa && <IconCheckmarkCircleFill className="text-primary size-4 shrink-0" fill="currentColor" />}
    </button>
  );
}
