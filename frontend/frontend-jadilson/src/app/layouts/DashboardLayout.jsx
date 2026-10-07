import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { motion } from "motion/react";
import { NavList, Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { Drawer } from "@/components/ui";
import { tituloDaRota } from "@/app/navigation";
import { spring } from "@/lib/motion";

export function DashboardLayout() {
  const [menuAberto, setMenuAberto] = useState(false);
  const { pathname } = useLocation();
  const titulo = tituloDaRota(pathname);

  useEffect(() => {
    document.title = `${titulo} — Jadilson Silva Adv.`;
  }, [titulo]);

  return (
    <div className="bg-bg min-h-screen">
      <div className="fixed inset-y-0 left-0 z-40 hidden lg:flex">
        <Sidebar indicador="nav-ativo-desktop" />
      </div>

      <Drawer
        open={menuAberto}
        onOpenChange={setMenuAberto}
        titulo="Menu"
        className="bg-bg text-ink max-w-xs border-border"
      >
        <div className="-mx-6 -mt-6">
          <NavList
            indicador="nav-ativo-mobile"
            aoNavegar={() => setMenuAberto(false)}
          />
        </div>
      </Drawer>

      <div className="lg:pl-64">
        <Topbar titulo={titulo} aoAbrirMenu={() => setMenuAberto(true)} />
        <motion.main
          key={pathname}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={spring.gentle}
          className="mx-auto w-full max-w-content px-4 py-6 lg:px-8"
        >
          <Outlet />
        </motion.main>
      </div>
    </div>
  );
}
