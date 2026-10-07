import { useContext } from "react";
import { ToastContext } from "@/components/ui/toastContext";

/**
 * Uso: const { toast } = useToast();
 * toast({ tipo: "sucesso", titulo: "Processo salvo" });
 * tipos: "sucesso" | "erro" | "info"
 */
export function useToast() {
  const contexto = useContext(ToastContext);

  if (!contexto) {
    throw new Error("useToast precisa estar dentro de <ToastProvider>");
  }

  return contexto;
}
