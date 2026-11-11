import { useEffect, useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { NavList, Sidebar } from "@/components/layout/Sidebar";
import { SessaoContext } from "@/context/sessao";
import { Topbar } from "@/components/layout/Topbar";
import { Drawer } from "@/components/ui";
import { tituloDaRota } from "@/app/navigation";
import { BuscaGlobal } from "@/components/layout/BuscaGlobal";
import { ModalConfirmacaoLogout } from "@/components/modais/ModalConfirmacaoLogout";
import { ModalNovoContribuidor } from "@/components/modais/ModalNovoContribuidor";
import { ModalCadastrarProcesso } from "@/components/modais/ModalCadastrarProcesso";
import { ModalCadastrarCliente } from "@/components/modais/ModalCadastrarCliente";
import { AreaProvider } from "@/context/AreaProvider";
import { spring } from "@/lib/motion";

function LayoutInterno({ user, csrf, onLogout, loading, error }) {
  const navegar = useNavigate();
  const [menuAberto, setMenuAberto] = useState(false);
  const [modalLogoutAberto, setModalLogoutAberto] = useState(false);
  const [modalContribuidorAberto, setModalContribuidorAberto] = useState(false);
  const [modalProcessoAberto, setModalProcessoAberto] = useState(false);
  const [modalClienteAberto, setModalClienteAberto] = useState(false);
  const [buscaAberta, setBuscaAberta] = useState(false);
  const { pathname } = useLocation();
  const titulo = tituloDaRota(pathname);

  useEffect(() => {
    function atalho(e) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setBuscaAberta((v) => !v);
      }
    }
    window.addEventListener("keydown", atalho);
    return () => window.removeEventListener("keydown", atalho);
  }, []);

  useEffect(() => {
    document.title = `${titulo} — Jadilson Silva Adv.`;
  }, [titulo]);

  return (
    <div className="min-h-screen lg:h-screen lg:overflow-hidden">
      <div className="bg-bg flex min-h-screen flex-col lg:h-full lg:min-h-0 lg:overflow-hidden">
        <div className="flex min-h-0 flex-1">
          <div className="hidden lg:block">
            <Sidebar
              indicador="nav-ativo-desktop"
              user={user}
              onLogout={() => setModalLogoutAberto(true)}
              onAdicionarContribuidor={() => setModalContribuidorAberto(true)}
              loading={loading}
            />
          </div>

          <div className="flex min-w-0 flex-1 flex-col lg:overflow-y-auto">
            <Topbar
              titulo={titulo}
              aoAbrirMenu={() => setMenuAberto(true)}
              aoAbrirBusca={() => setBuscaAberta(true)}
              user={user}
              onLogout={() => setModalLogoutAberto(true)}
              loading={loading}
              csrf={csrf}
              onNovoProcesso={() => setModalProcessoAberto(true)}
              onNovoCliente={() => setModalClienteAberto(true)}
              onNovoPrazo={() => navegar("/prazos")}
              onNovaAudiencia={() => navegar("/agenda")}
              onNovoContribuidor={() => setModalContribuidorAberto(true)}
            />
            {error && <p role="alert" className="text-destructive px-6 py-2 text-sm">{error}</p>}
            <motion.main
              key={pathname}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={spring.gentle}
              className="mx-auto w-full max-w-content px-6 py-8 sm:px-8 lg:px-12 lg:py-10"
            >
              <SessaoContext.Provider value={{ csrf }}>
                <Outlet context={{ user, csrf }} />
              </SessaoContext.Provider>
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
        <div className="-mx-8 -mt-8">
          <NavList
            indicador="nav-ativo-mobile"
            aoNavegar={() => setMenuAberto(false)}
          />
        </div>
      </Drawer>

      <BuscaGlobal
        open={buscaAberta}
        onOpenChange={setBuscaAberta}
      />

      <ModalConfirmacaoLogout
        open={modalLogoutAberto}
        onOpenChange={setModalLogoutAberto}
        loading={loading}
        onConfirmar={() => {
          setModalLogoutAberto(false);
          onLogout();
        }}
      />
      <ModalNovoContribuidor
        open={modalContribuidorAberto}
        onOpenChange={setModalContribuidorAberto}
        csrf={csrf}
      />
      <ModalCadastrarProcesso
        open={modalProcessoAberto}
        onOpenChange={setModalProcessoAberto}
      />
      <ModalCadastrarCliente
        open={modalClienteAberto}
        onOpenChange={setModalClienteAberto}
      />
    </div>
  );
}

/** A área escolhida na sidebar vale para todas as telas do painel. */
export function DashboardLayout(props) {
  return (
    <AreaProvider>
      <LayoutInterno {...props} />
    </AreaProvider>
  );
}
