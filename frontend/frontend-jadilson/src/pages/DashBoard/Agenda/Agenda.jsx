import { CalendarDays } from "lucide-react";
import { EmptyState } from "@/components/ui";

export function Agenda() {
  return (
    <div className="space-y-4">
      <p className="text-16 text-ink-muted">
        Audiências, reuniões e compromissos em visão semanal e mensal.
      </p>
      <EmptyState
        icon={CalendarDays}
        titulo="Agenda em construção"
        descricao="O calendário com audiências e alertas será implementado na próxima fase."
      />
    </div>
  );
}
