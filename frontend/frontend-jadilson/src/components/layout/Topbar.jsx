import { useState } from "react";
import { IconMagnifyingglass, IconBell, IconLine3Horizontal, IconSunMax, IconMoon } from "symbols-react";
import { Avatar, KineticTextReveal } from "@/components/ui";

function temaInicial() {
  try {
    return localStorage.getItem("tema") === "light" ? "light" : "dark";
  } catch {
    return "dark";
  }
}

export function Topbar({ titulo, aoAbrirMenu, aoAbrirBusca, user, onLogout, loading }) {
  const [tema, setTema] = useState(() => {
    const t = temaInicial();
    document.documentElement.dataset.theme = t;
    return t;
  });

  function alternarTema() {
    const novo = tema === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = novo;
    try {
      localStorage.setItem("tema", novo);
    } catch {
      /* sem persistência */
    }
    setTema(novo);
  }

  return (
    <header className="bg-bg/80 border-border sticky top-0 z-30 flex h-24 items-center gap-12 border-b px-6 backdrop-blur lg:px-12">
      <button
        type="button"
        onClick={aoAbrirMenu}
        aria-label="Abrir menu de navegação"
        className="hover:bg-surface-muted flex size-12 items-center justify-center rounded-input transition-colors duration-fast ease-out lg:hidden"
      >
        <IconLine3Horizontal className="size-5" fill="currentColor" aria-hidden="true" />
      </button>

      <h1 className="font-heading text-20 font-semibold">
        <KineticTextReveal
          key={titulo}
          text={titulo}
          distance={14}
          stagger={0.06}
          delay={0.05}
        />
      </h1>

      <div className="ml-auto flex items-center gap-6">
        <button
          type="button"
          onClick={aoAbrirBusca}
          className="bg-surface-muted border-border text-ink-muted hover:text-ink hover:border-primary/50 hidden h-10 w-80 items-center gap-3 rounded-input border px-4 text-14 whitespace-nowrap transition-colors md:flex"
        >
          <IconMagnifyingglass aria-hidden="true" fill="currentColor" className="size-4 shrink-0" />
          <span className="flex-1 truncate text-left">Buscar processo, cliente…</span>
          <kbd className="border-border shrink-0 rounded-md border px-2 py-1 text-11">Ctrl K</kbd>
        </button>

        <button
          type="button"
          onClick={alternarTema}
          aria-label={tema === "dark" ? "Usar tema claro" : "Usar tema escuro"}
          className="text-ink-muted hover:bg-surface-muted hover:text-ink flex size-12 items-center justify-center rounded-input transition-colors duration-fast ease-out"
        >
          {tema === "dark" ? (
            <IconSunMax className="size-5 shrink-0" fill="currentColor" aria-hidden="true" />
          ) : (
            <IconMoon className="size-5 shrink-0" fill="currentColor" aria-hidden="true" />
          )}
        </button>

        <button
          type="button"
          aria-label="Notificações"
          className="text-ink-muted hover:bg-surface-muted hover:text-ink relative flex size-12 items-center justify-center rounded-input transition-colors duration-fast ease-out"
        >
          <IconBell className="size-5 shrink-0" fill="currentColor" aria-hidden="true" />
          <span
            aria-hidden="true"
            className="bg-status-vencido absolute top-3 right-3 size-2 rounded-badge"
          />
        </button>

        <Avatar nome={user.nome} size="sm" />
        <button type="button" onClick={onLogout} disabled={loading} className="text-ink-muted hover:text-ink rounded-input p-2 lg:hidden">{loading ? "Saindo…" : "Sair"}</button>
      </div>
    </header>
  );
}
