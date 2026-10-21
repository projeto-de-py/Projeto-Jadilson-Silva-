import * as Dialog from "@radix-ui/react-dialog";
import { AnimatePresence, motion } from "motion/react";
import { spring } from "@/lib/motion";

export function ModalConfirmacaoLogout({
  open,
  onOpenChange,
  onConfirmar,
  loading = false,
}) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <AnimatePresence>
        {open && (
          <Dialog.Portal forceMount>
            <Dialog.Overlay asChild forceMount>
              <motion.div
                className="bg-black/60 fixed inset-0 z-50 backdrop-blur-sm"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
              />
            </Dialog.Overlay>
            <Dialog.Content asChild forceMount aria-describedby={undefined}>
              <div className="fixed inset-0 z-50 flex items-center justify-center p-4 focus:outline-none">
                <motion.div
                  className="bg-surface/95 border-border w-full max-w-[340px] rounded-modal border p-6 text-center shadow-[0_24px_70px_rgba(0,0,0,0.85)] backdrop-blur-2xl"
                  initial={{ opacity: 0, scale: 0.94, y: 10 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{
                    opacity: 0,
                    scale: 0.96,
                    y: 6,
                    transition: { duration: 0.12 },
                  }}
                  transition={spring.bouncy}
                >
                  <Dialog.Title className="text-18 font-medium text-ink px-2 pt-2 leading-snug">
                    Tem certeza de que deseja sair da conta?
                  </Dialog.Title>

                  <div className="mt-6 flex items-center gap-4">
                    <button
                      type="button"
                      disabled={loading}
                      onClick={onConfirmar}
                      className="bg-surface-muted hover:bg-border active:scale-[0.98] text-status-vencido-ink font-medium h-12 w-full rounded-card text-15 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
                    >
                      {loading ? "Saindo..." : "Sair"}
                    </button>
                    <button
                      type="button"
                      disabled={loading}
                      onClick={() => onOpenChange(false)}
                      className="bg-surface-muted hover:bg-border active:scale-[0.98] text-ink font-medium h-12 w-full rounded-card text-15 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      Cancelar
                    </button>
                  </div>
                </motion.div>
              </div>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  );
}
