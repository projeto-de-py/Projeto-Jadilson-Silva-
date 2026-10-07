import { CalendarClock } from "lucide-react";
import { EmptyState } from "@/components/ui";

export function Prazos() {
  return (
    <div className="space-y-4">
      <p className="text-16 text-ink-muted">
        Central de prazos: vencidos, de hoje e próximos, ordenada por urgência.
      </p>
      <EmptyState
        icon={CalendarClock}
        titulo="Nenhum prazo por aqui ainda"
        descricao="A priorização automática de prazos é o coração do sistema e chega na próxima fase."
      />
    </div>
  );
}
