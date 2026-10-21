import { useEffect, useMemo, useRef, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "motion/react";
import {
  IconMagnifyingglass,
  IconFolder,
  IconClock,
  IconPerson,
  IconFunction,
  IconReturn,
} from "symbols-react";
import { navegacao } from "@/app/navigation";
import { PROCESSOS_INICIAIS, PRAZOS } from "@/data/escritorio";
import { cn } from "@/lib/cn";

const norm = (t) => t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

export function BuscaGlobal({ open, onOpenChange, aoAbrirCalculadora }) {
  const [termo, setTermo] = useState("");
  const [ativo, setAtivo] = useState(0);
  const navegar = useNavigate();
  const lista = useRef(null);

  const itens = useMemo(() => {
    const clientes = [...new Set(PROCESSOS_INICIAIS.map((p) => p.cliente))];
    const todos = [
      { grupo: "Ações", rotulo: "Calcular prazo (dias úteis)", sub: "Calculadora de prazos", icone: IconFunction, acao: aoAbrirCalculadora },
      ...navegacao.map((n) => ({ grupo: "Páginas", rotulo: n.rotulo, sub: n.grupo, icone: n.icone, ir: n.to })),
      ...PROCESSOS_INICIAIS.map((p) => ({ grupo: "Processos", rotulo: p.numero, sub: `${p.cliente} · ${p.tipoAcao}`, icone: IconFolder, ir: "/processos" })),
      ...PRAZOS.map((p) => ({ grupo: "Prazos", rotulo: p.titulo, sub: `${p.cliente} · ${p.processo}`, icone: IconClock, ir: "/prazos" })),
      ...clientes.map((c) => ({ grupo: "Clientes", rotulo: c, sub: "Cliente", icone: IconPerson, ir: "/clientes" })),
    ];
    const t = norm(termo.trim());
    if (!t) return todos.filter((i) => i.grupo === "Ações" || i.grupo === "Páginas");
    return todos.filter((i) => norm(`${i.rotulo} ${i.sub}`).includes(t)).slice(0, 30);
  }, [termo, aoAbrirCalculadora]);

  useEffect(() => {
    lista.current?.querySelector(`[data-i="${ativo}"]`)?.scrollIntoView({ block: "nearest" });
  }, [ativo]);

  function fechar(v) {
    onOpenChange(v);
    if (!v) {
      setTermo("");
      setAtivo(0);
    }
  }

  function escolher(item) {
    fechar(false);
    if (item.acao) item.acao();
    else if (item.ir) navegar(item.ir);
  }

  function teclado(e) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setAtivo((a) => Math.min(a + 1, itens.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setAtivo((a) => Math.max(a - 1, 0));
    } else if (e.key === "Enter" && itens[ativo]) {
      e.preventDefault();
      escolher(itens[ativo]);
    }
  }

  let ultimoGrupo = null;
  return (
    <Dialog.Root open={open} onOpenChange={fechar}>
      <AnimatePresence>
        {open && (
          <Dialog.Portal forceMount>
            <Dialog.Overlay asChild forceMount>
              <motion.div
                className="bg-black/60 fixed inset-0 z-50 backdrop-blur-sm"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.12 }}
              />
            </Dialog.Overlay>
            <Dialog.Content asChild forceMount aria-describedby={undefined}>
              <div
                className="fixed inset-0 z-50 flex items-start justify-center p-4 pt-[14vh] focus:outline-none"
                onClick={() => fechar(false)}
              >
                <motion.div
                  onClick={(e) => e.stopPropagation()}
                  className="bg-surface border-border w-full max-w-xl overflow-hidden rounded-modal border shadow-popover"
                  initial={{ opacity: 0, scale: 0.96, y: -8 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.98, transition: { duration: 0.1 } }}
                  transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
                >
                  <Dialog.Title className="sr-only">Busca global</Dialog.Title>
                  <div className="border-border flex items-center gap-4 border-b px-6">
                    <IconMagnifyingglass className="text-ink-muted size-4 shrink-0" fill="currentColor" />
                    <input
                      autoFocus
                      value={termo}
                      onChange={(e) => {
                        setTermo(e.target.value);
                        setAtivo(0);
                      }}
                      onKeyDown={teclado}
                      placeholder="Buscar processo, cliente, prazo ou página…"
                      className="text-ink placeholder:text-ink-muted h-14 w-full bg-transparent text-16 focus:outline-none"
                    />
                    <kbd className="border-border text-ink-muted rounded-md border px-2 py-0.5 text-11">Esc</kbd>
                  </div>

                  <div ref={lista} className="max-h-[52vh] overflow-y-auto p-2">
                    {itens.length === 0 && (
                      <p className="text-14 text-ink-muted px-4 py-10 text-center">
                        Nada encontrado para “{termo}”.
                      </p>
                    )}
                    {itens.map((item, i) => {
                      const cabecalho = item.grupo !== ultimoGrupo;
                      ultimoGrupo = item.grupo;
                      const Icone = item.icone;
                      return (
                        <div key={`${item.grupo}-${item.rotulo}-${i}`}>
                          {cabecalho && (
                            <p className="text-11 text-ink-muted px-4 pt-4 pb-1 font-semibold tracking-wide uppercase">
                              {item.grupo}
                            </p>
                          )}
                          <button
                            type="button"
                            data-i={i}
                            onMouseMove={() => setAtivo(i)}
                            onClick={() => escolher(item)}
                            className={cn(
                              "flex w-full items-center gap-4 rounded-input px-4 py-2 text-left transition-colors",
                              i === ativo ? "bg-primary-soft" : "hover:bg-surface-muted",
                            )}
                          >
                            <span
                              className={cn(
                                "flex size-8 shrink-0 items-center justify-center rounded-input",
                                i === ativo ? "bg-primary text-primary-foreground" : "bg-surface-muted text-accent",
                              )}
                            >
                              <Icone className="size-4" fill="currentColor" />
                            </span>
                            <span className="min-w-0 flex-1">
                              <span className="text-14 text-ink block truncate font-medium">{item.rotulo}</span>
                              <span className="text-12 text-ink-muted block truncate">{item.sub}</span>
                            </span>
                            {i === ativo && <IconReturn className="text-ink-muted size-3.5" fill="currentColor" />}
                          </button>
                        </div>
                      );
                    })}
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
