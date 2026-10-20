import { useState } from "react";
import { NavLink } from "react-router-dom";
import { motion, AnimatePresence } from "motion/react";
import {
  IconChevronDown,
  IconChevronUpChevronDown,
  IconSparkles,
  IconQuestionmarkCircle,
  IconDocument,
} from "symbols-react";
import { navegacaoAgrupada } from "@/app/navigation";
import { spring } from "@/lib/motion";
import { cn } from "@/lib/cn";
import { Avatar } from "@/components/ui";
import logo from "@/assets/images/Logo_Jadilson.png";

const AREAS = [
  { id: "todas", rotulo: "Todas as áreas", cor: "bg-ink-muted" },
  { id: "bancario", rotulo: "Bancário", cor: "bg-primary" },
  { id: "previdenciario", rotulo: "Previdenciário", cor: "bg-accent" },
  { id: "consumidor", rotulo: "Consumidor", cor: "bg-status-ok" },
];

function SeletorArea({ area, onChange }) {
  const [aberto, setAberto] = useState(false);
  const atual = AREAS.find((a) => a.id === area) ?? AREAS[0];

  return (
    <div className="relative px-4 pb-4">
      <button
        type="button"
        onClick={() => setAberto((v) => !v)}
        className="border-border bg-surface-muted/60 hover:bg-surface-muted flex w-full items-center gap-2 rounded-card border p-2 text-left transition-colors focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
      >
        <span className={cn("size-2.5 shrink-0 rounded-full", atual.cor)} aria-hidden="true" />
        <span className="min-w-0 flex-1 truncate text-13 font-semibold text-ink">
          {atual.rotulo}
        </span>
        <IconChevronDown fill="currentColor" className="text-ink-muted size-3.5 shrink-0" />
      </button>

      <AnimatePresence>
        {aberto && (
          <>
            <button
              type="button"
              aria-label="Fechar seletor de área"
              onClick={() => setAberto(false)}
              className="fixed inset-0 z-40 cursor-default"
            />
            <motion.div
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.12 }}
              className="border-border bg-surface absolute inset-x-3 top-full z-50 mt-2 space-y-0.5 rounded-card border p-2 shadow-popover"
            >
              {AREAS.map((a) => (
                <button
                  key={a.id}
                  type="button"
                  onClick={() => {
                    onChange(a.id);
                    setAberto(false);
                  }}
                  className={cn(
                    "flex w-full items-center gap-2 rounded-input px-2 py-2 text-13 font-medium transition-colors",
                    a.id === atual.id ? "bg-surface-muted text-ink" : "text-ink-muted hover:bg-surface-muted hover:text-ink",
                  )}
                >
                  <span className={cn("size-2 shrink-0 rounded-full", a.cor)} aria-hidden="true" />
                  {a.rotulo}
                </button>
              ))}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

function GrupoNav({ grupo, aoNavegar, indicador }) {
  const [aberto, setAberto] = useState(true);

  return (
    <div className="space-y-0.5">
      <button
        type="button"
        onClick={() => setAberto((v) => !v)}
        className="text-ink-muted/55 hover:text-ink-muted flex w-full items-center justify-between px-4 py-2 text-11 font-semibold tracking-wider uppercase transition-colors"
      >
        {grupo.nome}
        <IconChevronDown
          fill="currentColor"
          className={cn(
            "size-3 shrink-0 transition-transform duration-fast",
            !aberto && "-rotate-90",
          )}
        />
      </button>

      <AnimatePresence initial={false}>
        {aberto && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
          >
            <div className="space-y-0.5 pt-0.5 pb-1">
              {grupo.itens.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end
                  onClick={aoNavegar}
                  className={({ isActive }) =>
                    cn(
                      "relative flex items-center gap-4 rounded-input px-4 py-2 text-14 font-medium",
                      "transition-colors duration-fast ease-out",
                      "focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
                      isActive
                        ? "text-ink"
                        : "text-ink-muted hover:bg-surface-muted hover:text-ink",
                    )
                  }
                >
                  {({ isActive }) => (
                    <>
                      {isActive && (
                        <motion.span
                          aria-hidden="true"
                          layoutId={indicador}
                          className="bg-surface-muted absolute inset-0 rounded-input"
                          transition={spring.snappy}
                        />
                      )}
                      <item.icone
                        fill="currentColor"
                        className="relative z-10 size-[18px] shrink-0"
                        aria-hidden="true"
                      />
                      <span className="relative z-10">{item.rotulo}</span>
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function NavList({ aoNavegar, indicador = "nav-ativo" }) {
  const grupos = navegacaoAgrupada();

  return (
    <nav aria-label="Navegação principal" className="space-y-4 px-4 py-4">
      {grupos.map((grupo) => (
        <GrupoNav
          key={grupo.nome}
          grupo={grupo}
          aoNavegar={aoNavegar}
          indicador={indicador}
        />
      ))}
    </nav>
  );
}

export function Sidebar({ aoNavegar, indicador, user, onLogout, loading }) {
  const [area, setArea] = useState("todas");

  return (
    <aside className="bg-bg border-border flex h-full w-64 shrink-0 flex-col border-r">
      <div className="flex h-18 items-center gap-2 px-6">
        <img src={logo} alt="" aria-hidden="true" className="size-6 shrink-0" />
        <p className="font-heading text-14 font-bold truncate">Jadilson Silva Adv.</p>
      </div>

      <SeletorArea area={area} onChange={setArea} />

      <div className="border-border flex-1 overflow-y-auto border-t">
        <NavList aoNavegar={aoNavegar} indicador={indicador} />
      </div>

      <div className="border-border space-y-4 border-t p-4">
        <div className="border-border bg-surface-muted/40 space-y-2 rounded-card border p-4">
          <p className="text-ink-muted/80 flex items-center gap-2 text-11 font-semibold tracking-wide uppercase">
            <IconSparkles fill="currentColor" className="size-3" />
            Novidades
          </p>
          <p className="text-13 font-medium text-ink leading-snug">
            Redator IA e exportação em PDF chegaram aos processos.
          </p>
          <NavLink to="/processos" className="text-primary hover:text-primary-hover text-12 font-medium">
            Experimentar
          </NavLink>
        </div>

        <div className="space-y-0.5">
          <button
            type="button"
            className="text-ink-muted hover:bg-surface-muted hover:text-ink flex w-full items-center gap-2 rounded-input px-2 py-2 text-13 font-medium transition-colors"
          >
            <IconQuestionmarkCircle fill="currentColor" className="size-4 shrink-0" />
            Central de ajuda
          </button>
          <button
            type="button"
            className="text-ink-muted hover:bg-surface-muted hover:text-ink flex w-full items-center gap-2 rounded-input px-2 py-2 text-13 font-medium transition-colors"
          >
            <IconDocument fill="currentColor" className="size-4 shrink-0" />
            Documentação
          </button>
        </div>

        <button
          type="button"
          onClick={onLogout}
          disabled={loading}
          className="border-border bg-surface-muted/60 hover:bg-surface-muted flex w-full items-center gap-2 rounded-card border p-2 text-left transition-colors focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
        >
          <Avatar nome={user.nome} size="sm" className="shrink-0" />
          <div className="min-w-0 flex-1 leading-tight">
            <p className="truncate text-13 font-semibold text-ink">{user.nome}</p>
            <p className="text-ink-muted truncate text-12">{user.email}</p>
          </div>
          <IconChevronUpChevronDown
            fill="currentColor"
            className="text-ink-muted size-3.5 shrink-0"
            aria-hidden="true"
          />
        </button>
      </div>
    </aside>
  );
}
