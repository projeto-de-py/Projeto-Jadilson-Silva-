import { Users } from "lucide-react";
import { EmptyState } from "@/components/ui";

export function Clientes() {
  return (
    <div className="space-y-4">
      <p className="text-16 text-ink-muted">
        Cadastro de clientes e seus processos vinculados.
      </p>
      <EmptyState
        icon={Users}
        titulo="Nenhum cliente por aqui ainda"
        descricao="A lista de clientes com busca e ficha completa chega na próxima fase."
      />
    </div>
  );
}
