import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { spring } from "@/lib/motion";
import { cn } from "@/lib/cn";

export function Modal({
  open,
  onOpenChange,
  titulo,
  descricao,
  children,
  footer,
  className,
}) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <AnimatePresence>
        {open && (
          <Dialog.Portal forceMount>
            <Dialog.Overlay asChild forceMount>
              <motion.div
                className="bg-ink/40 fixed inset-0 z-50"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
              />
            </Dialog.Overlay>
            <Dialog.Content asChild forceMount aria-describedby={undefined}>
              <div className="fixed inset-0 z-50 flex items-center justify-center p-4 focus:outline-none">
                <motion.div
                  className={cn(
                    "bg-surface border-border max-h-[calc(100vh-2rem)] w-full max-w-lg",
                    "overflow-y-auto rounded-modal border p-7 shadow-popover",
                    className,
                  )}
                  initial={{ opacity: 0, scale: 0.94, y: 12 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{
                    opacity: 0,
                    scale: 0.97,
                    y: 6,
                    transition: { duration: 0.12 },
                  }}
                  transition={spring.bouncy}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-1.5">
                      <Dialog.Title className="text-20 font-semibold">
                        {titulo}
                      </Dialog.Title>
                      {descricao && (
                        <Dialog.Description className="text-14 text-ink-muted">
                          {descricao}
                        </Dialog.Description>
                      )}
                    </div>
                    <Dialog.Close
                      aria-label="Fechar"
                      className="text-ink-muted hover:text-ink hover:bg-surface-muted rounded-input p-1.5 transition-colors"
                    >
                      <X className="size-4" />
                    </Dialog.Close>
                  </div>

                  <div className="mt-4">{children}</div>

                  {footer && (
                    <div className="mt-6 flex justify-end gap-2">{footer}</div>
                  )}
                </motion.div>
              </div>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  );
}
