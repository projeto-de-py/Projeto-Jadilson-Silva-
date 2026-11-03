import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { useNavigate } from "react-router-dom";
import { isToday } from "date-fns";
import { IconBell } from "symbols-react";
import { useNotificacoes } from "@/hooks/useNotificacoes";
import { spring } from "@/lib/motion";
import { cn } from "@/lib/cn";

export function PainelNotificacoes({ csrf }) {
  const [aberto, setAberto] = useState(false);
  const ref = useRef(null);
  const navigate = useNavigate();
  const { itens, naoLidas, erro, marcarLida, marcarTodas } = useNotificacoes(csrf);
  const hoje = itens.filter((item) => isToday(new Date(item.criado_em)));
  const anteriores = itens.filter((item) => !isToday(new Date(item.criado_em)));

  useEffect(() => {
    function fora(event) {
      if (!ref.current?.contains(event.target)) setAberto(false);
    }
    function escape(event) {
      if (event.key === "Escape") setAberto(false);
    }
    document.addEventListener("pointerdown", fora);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("pointerdown", fora);
      document.removeEventListener("keydown", escape);
    };
  }, []);

  async function abrirItem(item) {
    try {
      if (!item.lida_em) await marcarLida(item.id);
      setAberto(false);
      navigate(item.link?.startsWith("/") && !item.link.startsWith("//") ? item.link : "/home");
    } catch {
      // Mantém o painel aberto para que a pessoa possa tentar de novo.
    }
  }

  return (
    <div ref={ref} className="relative">
      <button type="button" aria-label={`Notificações${naoLidas ? `, ${naoLidas} não lidas` : ""}`} aria-expanded={aberto} aria-haspopup="dialog" onClick={() => setAberto((atual) => !atual)} className="text-ink-muted hover:bg-surface-muted hover:text-ink relative flex size-12 items-center justify-center rounded-input transition-colors duration-fast ease-out">
        <IconBell className="size-5 shrink-0" fill="currentColor" aria-hidden="true" />
        {naoLidas > 0 && <span aria-hidden="true" className="bg-status-vencido text-white absolute -top-0.5 -right-0.5 flex h-5 min-w-5 items-center justify-center rounded-full px-1 text-[10px] font-bold leading-none">{naoLidas > 99 ? "99+" : naoLidas}</span>}
      </button>
      <AnimatePresence>
        {aberto && (
          <motion.section role="dialog" aria-label="Notificações" initial={{ opacity: 0, y: -8, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -6, scale: 0.98 }} transition={spring.snappy} className="bg-surface border-border shadow-popover absolute top-full right-0 z-50 mt-2 flex max-h-[min(560px,calc(100vh-8rem))] w-[min(22rem,calc(100vw-2rem))] flex-col overflow-hidden rounded-card border">
            <div className="border-border flex items-center justify-between gap-3 border-b px-4 py-3">
              <h2 className="text-14 font-semibold text-ink">Notificações</h2>
              <button type="button" disabled={!naoLidas} onClick={() => marcarTodas().catch(() => {})} className="text-primary hover:text-ink text-12 font-medium disabled:opacity-50">Marcar todas como lidas</button>
            </div>
            <div className="overflow-y-auto p-2">
              {erro && <p role="alert" className="text-status-vencido-ink px-3 py-2 text-12">{erro}</p>}
              {!erro && itens.length === 0 && <p className="text-ink-muted px-3 py-8 text-center text-13">Você não tem notificações.</p>}
              {[["Hoje", hoje], ["Anteriores", anteriores]].map(([grupo, lista]) => lista.length > 0 && (
                <div key={grupo} className="mb-2 last:mb-0">
                  <p className="text-ink-muted px-3 py-2 text-11 font-semibold tracking-wide uppercase">{grupo}</p>
                  <ul className="space-y-1">
                    {lista.map((item) => (
                      <li key={item.id}>
                        <button type="button" onClick={() => abrirItem(item)} className={cn("hover:bg-surface-muted flex w-full items-start gap-3 rounded-input p-3 text-left transition-colors", !item.lida_em && "bg-surface-muted/60")}>
                          <span aria-hidden="true" className={cn("mt-1.5 size-2 shrink-0 rounded-full", item.severidade === "critica" ? "bg-status-vencido" : item.severidade === "atencao" ? "bg-status-atencao" : "bg-primary")} />
                          <span className="min-w-0 flex-1">
                            <span className="text-13 font-semibold text-ink block">{item.titulo}</span>
                            <span className="text-12 text-ink-muted mt-1 block">{item.mensagem}</span>
                            <time className="text-11 text-ink-muted mt-2 block" dateTime={item.criado_em}>{new Date(item.criado_em).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}</time>
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </motion.section>
        )}
      </AnimatePresence>
    </div>
  );
}
