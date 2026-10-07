import { NavLink, useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { LogOut, Scale } from "lucide-react";
import { navegacao } from "@/app/navigation";
import { spring } from "@/lib/motion";
import { cn } from "@/lib/cn";

export function NavList({ aoNavegar, indicador = "nav-ativo" }) {
  return (
    <nav aria-label="Navegação principal" className="space-y-1 px-3 py-4">
      {navegacao.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end
          onClick={aoNavegar}
          className={({ isActive }) =>
            cn(
              "relative flex items-center gap-3 rounded-input px-3 py-2.5 text-14 font-medium transition-colors",
              "focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
              isActive
                ? "text-ink"
                : "text-ink-muted hover:bg-white/5 hover:text-ink",
            )
          }
        >
          {({ isActive }) => (
            <>
              {isActive && (
                <>
                  <motion.span
                    aria-hidden="true"
                    layoutId={indicador}
                    className="bg-surface-muted absolute inset-0 rounded-input"
                    transition={spring.snappy}
                  />
                  <span
                    aria-hidden="true"
                    className="bg-accent absolute inset-y-1.5 -left-2 w-0.5 rounded-badge"
                  />
                </>
              )}
              <item.icone className="relative z-10 size-4" aria-hidden="true" />
              <span className="relative z-10">{item.rotulo}</span>
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
}

export function Sidebar({ aoNavegar, indicador }) {
  const navigate = useNavigate();

  return (
    <aside className="bg-bg border-border flex h-full w-64 shrink-0 flex-col border-r">
      <div className="flex h-16 items-center gap-2.5 border-b border-border px-5">
        <span className="bg-ink text-bg flex size-8 shrink-0 items-center justify-center rounded-input">
          <Scale className="size-4" aria-hidden="true" />
        </span>
        <div className="min-w-0 leading-tight">
          <p className="font-heading text-16 font-bold">Jadilson Silva Adv.</p>
          <p className="text-ink-muted text-12">Escritório de advocacia</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        <NavList aoNavegar={aoNavegar} indicador={indicador} />
      </div>

      <div className="flex items-center justify-between gap-2 border-t border-border p-4">
        <div className="min-w-0">
          <p className="truncate text-14 font-medium">Jadilson Silva</p>
          <p className="text-ink-muted truncate text-12">
            jadilson@escritorio.adv.br
          </p>
        </div>
        <button
          type="button"
          onClick={() => navigate("/")}
          aria-label="Sair da conta"
          className="text-ink-muted hover:bg-surface-muted hover:text-ink rounded-input p-2 transition-colors focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
        >
          <LogOut className="size-4" aria-hidden="true" />
        </button>
      </div>
    </aside>
  );
}
