import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { Bell, CalendarDays, Menu, Search } from "lucide-react";
import { Avatar } from "@/components/ui";

export function Topbar({ titulo, aoAbrirMenu }) {
  const hoje = format(new Date(), "dd 'de' MMMM 'de' yyyy", { locale: ptBR });

  return (
    <header className="bg-bg/80 border-border sticky top-0 z-30 flex h-16 items-center gap-4 border-b backdrop-blur">
      <button
        type="button"
        onClick={aoAbrirMenu}
        aria-label="Abrir menu de navegação"
        className="hover:bg-surface-muted rounded-input p-2 transition-colors lg:hidden"
      >
        <Menu className="size-5" aria-hidden="true" />
      </button>

      <h1 className="font-heading text-20 font-semibold">{titulo}</h1>

      <span className="border-border bg-surface-muted text-ink-muted hidden items-center gap-2 rounded-badge border px-3 py-1.5 text-14 sm:inline-flex">
        <CalendarDays className="size-3.5" aria-hidden="true" />
        {hoje}
      </span>

      <div className="ml-auto flex items-center gap-2">
        <label className="relative hidden md:block">
          <span className="sr-only">Buscar</span>
          <Search
            aria-hidden="true"
            className="text-ink-muted pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2"
          />
          <input
            type="search"
            placeholder="Buscar processo, cliente…"
            className="bg-surface-muted border-border text-ink placeholder:text-ink-muted focus:ring-ring h-10 w-64 rounded-input border ps-9 pe-3 text-14 focus:ring-2 focus:outline-none"
          />
        </label>

        <button
          type="button"
          aria-label="Notificações"
          className="text-ink-muted hover:bg-surface-muted hover:text-ink relative rounded-input p-2 transition-colors"
        >
          <Bell className="size-5" aria-hidden="true" />
          <span
            aria-hidden="true"
            className="bg-status-vencido absolute top-1.5 right-1.5 size-2 rounded-badge"
          />
        </button>

        <Avatar nome="Jadilson Silva" size="sm" />
      </div>
    </header>
  );
}
