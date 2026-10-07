import { Settings } from "lucide-react";
import { EmptyState } from "@/components/ui";

export function Configuracoes() {
  return (
    <div className="space-y-4">
      <p className="text-16 text-ink-muted">
        Dados do escritório, preferências de alertas e integrações.
      </p>
      <EmptyState
        icon={Settings}
        titulo="Configurações em construção"
        descricao="Preferências de notificação, dados do escritório e assinatura chegam nas próximas fases."
      />
    </div>
  );
}
