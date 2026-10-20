import * as Dialog from "@radix-ui/react-dialog";
import { IconXmark } from "symbols-react";
import { AnimatePresence, motion } from "motion/react";
import { spring } from "@/lib/motion";
import { cn } from "@/lib/cn";

export function Drawer({
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
                className="bg-black/60 fixed inset-0 z-50 backdrop-blur-sm"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
              />
            </Dialog.Overlay>
            <Dialog.Content asChild forceMount aria-describedby={undefined}>
              <motion.div
                className={cn(
                  "bg-surface border-border fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col",
                  "border-l shadow-popover focus:outline-none",
                  className,
                )}
                initial={{ x: "100%" }}
                animate={{ x: 0 }}
                exit={{ x: "100%", transition: { duration: 0.2 } }}
                transition={spring.gentle}
              >
                <header className="border-border flex items-start justify-between gap-4 border-b p-8 pb-6">
                  <div className="space-y-2">
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
                    className="text-ink-muted hover:text-ink hover:bg-surface-muted rounded-input p-2 transition-colors"
                  >
                    <IconXmark className="size-4" fill="currentColor" />
                  </Dialog.Close>
                </header>

                <div className="flex-1 overflow-y-auto p-8">{children}</div>

                {footer && (
                  <footer className="border-border flex justify-end gap-2 border-t p-4">
                    {footer}
                  </footer>
                )}
              </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  );
}
