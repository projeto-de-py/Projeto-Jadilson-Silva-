import { FolderOpen } from "lucide-react";
import { EmptyState } from "@/components/ui";

export function Processos() {
  return (
    <div className="space-y-4">
      <p className="text-16 text-ink-muted">
        Listagem, busca e cadastro de processos.
      </p>
      <EmptyState
        icon={FolderOpen}
        titulo="Nenhum processo por aqui ainda"
        descricao="A tabela de processos com filtros e detalhes será implementada na próxima fase."
      />
    </div>
  );
}
