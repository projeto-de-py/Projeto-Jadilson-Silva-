import { useCallback, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { IconCheckmarkCircleFill, IconExclamationmarkCircleFill, IconInfoCircleFill, IconXmark } from "symbols-react";
import { ToastContext } from "./toastContext";
import { spring } from "@/lib/motion";
import { cn } from "@/lib/cn";

const tons = {
  sucesso: { Icone: IconCheckmarkCircleFill, cor: "text-status-ok" },
  erro: { Icone: IconExclamationmarkCircleFill, cor: "text-status-vencido" },
  info: { Icone: IconInfoCircleFill, cor: "text-primary" },
};

function ToastItem({ tipo = "info", titulo, descricao, acao, onFechar }) {
  const { Icone, cor } = tons[tipo] ?? tons.info;

  return (
    <motion.div
      layout
      className="bg-surface border-border flex items-start gap-4 rounded-card border p-4 shadow-popover"
      initial={{ opacity: 0, y: 24, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.97, transition: { duration: 0.15 } }}
      transition={spring.bouncy}
    >
      <Icone aria-hidden="true" fill="currentColor" className={cn("mt-0.5 size-5 shrink-0", cor)} />
      <div className="min-w-0 flex-1 space-y-1">
        <p className="text-14 font-semibold">{titulo}</p>
        {descricao && <p className="text-14 text-ink-muted">{descricao}</p>}
        {acao && <div className="pt-1">{acao}</div>}
      </div>
      <button
        type="button"
        onClick={onFechar}
        aria-label="Fechar aviso"
        className="text-ink-muted hover:text-ink rounded-input p-1 transition-colors"
      >
        <IconXmark className="size-4" fill="currentColor" />
      </button>
    </motion.div>
  );
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const fechar = useCallback((id) => {
    setToasts((atual) => atual.filter((item) => item.id !== id));
  }, []);

  const toast = useCallback(
    ({ tipo = "info", titulo, descricao, acao }) => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
      setToasts((atual) => [...atual, { id, tipo, titulo, descricao, acao }]);
      setTimeout(() => fechar(id), 4000);
      return id;
    },
    [fechar],
  );

  return (
    <ToastContext.Provider value={{ toast, fechar }}>
      {children}
      <div
        aria-live="polite"
        className="fixed right-4 bottom-4 z-[60] flex w-[calc(100%-2rem)] max-w-sm flex-col gap-2"
      >
        <AnimatePresence initial={false}>
          {toasts.map((item) => (
            <ToastItem
              key={item.id}
              {...item}
              onFechar={() => fechar(item.id)}
            />
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}
