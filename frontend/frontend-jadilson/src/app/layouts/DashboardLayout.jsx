import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { motion } from "motion/react";
import { NavList, Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { Drawer } from "@/components/ui";
import { tituloDaRota } from "@/app/navigation";

export function DashboardLayout({ user, onLogout, loading, error }) {
  const [menuAberto, setMenuAberto] = useState(false);
  const { pathname } = useLocation();
  const titulo = tituloDaRota(pathname);

  useEffect(() => {
    document.title = `${titulo} — Jadilson Silva Adv.`;
  }, [titulo]);

  return (
    <div className="min-h-screen lg:p-4">
      {/* Janela flutuante sobre o glow azul (referência visual) */}
      <div className="border-border/70 bg-bg flex min-h-screen flex-col lg:h-[calc(100vh-2rem)] lg:overflow-hidden lg:rounded-modal lg:border lg:shadow-[0_24px_80px_rgb(0_0_0/0.55)]">
        <div className="flex min-h-0 flex-1">
          <div className="hidden lg:block">
            <Sidebar indicador="nav-ativo-desktop" user={user} onLogout={onLogout} loading={loading} />
          </div>

          <div className="flex min-w-0 flex-1 flex-col lg:overflow-y-auto">
            <Topbar titulo={titulo} aoAbrirMenu={() => setMenuAberto(true)} user={user} onLogout={onLogout} loading={loading} />
            {error && <p role="alert" className="text-destructive px-5 py-2 text-sm">{error}</p>}
            <motion.main
              key={pathname}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
              className="mx-auto w-full max-w-content px-5 py-8 lg:px-10 lg:py-10"
            >
              <Outlet />
            </motion.main>
          </div>
        </div>
      </div>

      <Drawer
        open={menuAberto}
        onOpenChange={setMenuAberto}
        titulo="Menu"
        className="bg-bg text-ink max-w-xs border-border"
      >
        <div className="-mx-7 -mt-7">
          <NavList
            indicador="nav-ativo-mobile"
            aoNavegar={() => setMenuAberto(false)}
          />
        </div>
      </Drawer>
    </div>
  );
}
