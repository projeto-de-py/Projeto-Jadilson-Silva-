import { useEffect, useRef, useState } from "react";
import { NavLink } from "react-router-dom";
import { motion } from "motion/react";
import { animated, useSpring, useTransition } from "@react-spring/web";
import { IconChevronDown, IconChevronUpChevronDown, IconPlus } from "symbols-react";
import { LogOut } from "lucide-react";
import { navegacaoAgrupada } from "@/app/navigation";
import { AREAS, useArea } from "@/context/area-context";
import { reactSpring, spring } from "@/lib/motion";
import { cn } from "@/lib/cn";
import { Avatar } from "@/components/ui";
import logo from "@/assets/images/Logo_Juridico_Jadilson_Silva.png";

/** Filtro global: a área escolhida vale para Início, Processos, Prazos e Documentos. */
function SeletorArea() {
  const { area, setArea } = useArea();
  const [aberto, setAberto] = useState(false);
  const atual = AREAS.find((a) => a.id === area) ?? AREAS[0];

  const seta = useSpring({
    rotate: aberto ? 180 : 0,
    config: reactSpring.snappy,
  });

  const transicaoMenu = useTransition(aberto, {
    from: { opacity: 0, y: -8, scale: 0.96 },
    enter: { opacity: 1, y: 0, scale: 1 },
    leave: { opacity: 0, y: -6, scale: 0.97 },
    config: reactSpring.fluid,
  });

  return (
    <div className="relative px-5 pb-5">
      <p className="text-ink-muted/70 px-1 pb-2 text-11 font-semibold tracking-wider uppercase select-none">
        Área de atuação
      </p>
      <button
        type="button"
        onClick={() => setAberto((v) => !v)}
        aria-expanded={aberto}
        aria-haspopup="listbox"
        aria-label={`Filtrar por área de atuação. Atual: ${atual.rotulo}`}
        className="squircle border-border bg-surface-muted/60 hover:bg-surface-muted hover:border-primary/30 flex w-full items-center gap-2.5 rounded-input border px-3.5 py-2.5 text-left transition-colors focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
      >
        <span className={cn("size-2.5 shrink-0 rounded-full", atual.cor)} aria-hidden="true" />
        <span className="min-w-0 flex-1 truncate text-13 font-semibold text-ink">{atual.rotulo}</span>
        <animated.span
          style={{ transform: seta.rotate.to((r) => `rotate(${r}deg)`) }}
          className="text-ink-muted inline-flex shrink-0"
          aria-hidden="true"
        >
          <IconChevronDown fill="currentColor" className="size-3.5" />
        </animated.span>
      </button>

      {transicaoMenu((estilo, visivel) =>
        visivel ? (
          <>
            <button
              type="button"
              aria-label="Fechar seletor de área"
              onClick={() => setAberto(false)}
              className="fixed inset-0 z-40 cursor-default"
            />
            <animated.div
              role="listbox"
              aria-label="Áreas de atuação"
              style={{
                opacity: estilo.opacity,
                transform: estilo.y.to(
                  (y) => `translate3d(0, ${y}px, 0) scale(${estilo.scale.get()})`,
                ),
              }}
              className="squircle border-border bg-surface absolute inset-x-4 top-full z-50 mt-2 space-y-1 rounded-card border p-2 shadow-popover"
            >
              {AREAS.map((a) => (
                <button
                  key={a.id}
                  type="button"
                  role="option"
                  aria-selected={a.id === atual.id}
                  onClick={() => {
                    setArea(a.id);
                    setAberto(false);
                  }}
                  className={cn(
                    "squircle flex w-full items-center gap-2.5 rounded-input px-3 py-2 text-13 font-medium transition-colors",
                    a.id === atual.id
                      ? "bg-surface-muted text-ink font-semibold"
                      : "text-ink-muted hover:bg-surface-muted/70 hover:text-ink",
                  )}
                >
                  <span className={cn("size-2 shrink-0 rounded-full", a.cor)} aria-hidden="true" />
                  {a.rotulo}
                </button>
              ))}
            </animated.div>
          </>
        ) : null,
      )}
    </div>
  );
}

/** Grupo de links. O título é só um rótulo fixo para não confundir com botão. */
function GrupoNav({ grupo, aoNavegar, indicador }) {
  return (
    <div className="space-y-1">
      <p className="text-ink-muted/60 px-3.5 py-1.5 text-11 font-semibold tracking-wider uppercase select-none">
        {grupo.nome}
      </p>
      <div className="space-y-1">
        {grupo.itens.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end
            onClick={aoNavegar}
            className={({ isActive }) =>
              cn(
                "squircle relative flex items-center gap-3.5 rounded-input px-3.5 py-2.5 text-14 font-medium",
                "transition-colors duration-fast ease-out",
                "focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
                isActive ? "text-ink font-semibold" : "text-ink-muted hover:bg-surface-muted/60 hover:text-ink",
              )
            }
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <motion.span
                    aria-hidden="true"
                    layoutId={indicador}
                    className="squircle bg-surface-muted border-border/80 absolute inset-0 rounded-input border"
                    transition={spring.snappy}
                  />
                )}
                <item.icone fill="currentColor" className="relative z-10 size-[18px] shrink-0" aria-hidden="true" />
                <span className="relative z-10">{item.rotulo}</span>
              </>
            )}
          </NavLink>
        ))}
      </div>
    </div>
  );
}

export function NavList({ aoNavegar, indicador = "nav-ativo" }) {
  const grupos = navegacaoAgrupada();

  return (
    <nav aria-label="Navegação principal" className="space-y-6 px-4 py-5">
      {grupos.map((grupo) => (
        <GrupoNav key={grupo.nome} grupo={grupo} aoNavegar={aoNavegar} indicador={indicador} />
      ))}
    </nav>
  );
}

export function Sidebar({ aoNavegar, indicador, user, onLogout, onAdicionarContribuidor, loading }) {
  const [contaAberta, setContaAberta] = useState(false);
  const contaRef = useRef(null);

  const transicaoConta = useTransition(contaAberta, {
    from: { opacity: 0, y: 10, scale: 0.96 },
    enter: { opacity: 1, y: 0, scale: 1 },
    leave: { opacity: 0, y: 6, scale: 0.97 },
    config: reactSpring.fluid,
  });

  useEffect(() => {
    function fecharAoClicarFora(event) {
      if (!contaRef.current?.contains(event.target)) setContaAberta(false);
    }
    function fecharComEscape(event) {
      if (event.key === "Escape") setContaAberta(false);
    }
    document.addEventListener("pointerdown", fecharAoClicarFora);
    document.addEventListener("keydown", fecharComEscape);
    return () => {
      document.removeEventListener("pointerdown", fecharAoClicarFora);
      document.removeEventListener("keydown", fecharComEscape);
    };
  }, []);

  return (
    <aside className="bg-bg border-border flex h-full w-68 shrink-0 flex-col border-r">
      {/* Cabeçalho institucional: apenas a marca gráfica oficial, sem repetir o nome do usuário */}
      <div className="flex h-24 items-center px-5 select-none">
        <img
          src={logo}
          alt="Jadilson Silva Advocacia"
          className="logo-marca h-12 w-auto max-w-full object-contain object-left"
        />
      </div>

      <SeletorArea />

      <div className="border-border flex-1 overflow-y-auto border-t">
        <NavList aoNavegar={aoNavegar} indicador={indicador} />
      </div>

      {/* Único card de perfil do advogado: botão interativo com menu da conta */}
      <div className="border-border border-t p-4">
        <div ref={contaRef} className="relative">
          <button
            type="button"
            onClick={() => setContaAberta((aberta) => !aberta)}
            aria-expanded={contaAberta}
            aria-haspopup="menu"
            aria-label={`Opções da conta de ${user.nome}`}
            className="squircle border-border bg-surface-muted/60 hover:bg-surface-muted hover:border-primary/30 flex w-full items-center gap-3 rounded-card border p-2.5 text-left transition-colors focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
          >
            <Avatar nome={user.nome} size="sm" className="shrink-0" />
            <div className="min-w-0 flex-1 leading-tight">
              <p className="truncate text-13 font-semibold text-ink">{user.nome}</p>
              <p className="text-ink-muted truncate text-12">{user.email}</p>
            </div>
            <IconChevronUpChevronDown fill="currentColor" className="text-ink-muted size-3.5 shrink-0" aria-hidden="true" />
          </button>

          {transicaoConta((estilo, visivel) =>
            visivel ? (
              <animated.div
                role="menu"
                aria-label="Opções da conta"
                style={{
                  opacity: estilo.opacity,
                  transform: estilo.y.to(
                    (y) => `translate3d(0, ${y}px, 0) scale(${estilo.scale.get()})`,
                  ),
                }}
                className="squircle border-border bg-surface absolute inset-x-0 bottom-full z-50 mb-2 space-y-1 rounded-card border p-1.5 shadow-popover"
              >
                {user.administrador && (
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setContaAberta(false);
                      onAdicionarContribuidor();
                    }}
                    className="squircle text-ink-muted hover:bg-surface-muted hover:text-ink flex w-full items-center gap-2.5 rounded-input px-3 py-2.5 text-left text-13 font-medium transition-colors"
                  >
                    <IconPlus fill="currentColor" className="size-4 shrink-0" />
                    Adicionar novo contribuidor
                  </button>
                )}
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    setContaAberta(false);
                    onLogout();
                  }}
                  disabled={loading}
                  className="squircle text-ink-muted hover:bg-surface-muted hover:text-ink flex w-full items-center gap-2.5 rounded-input px-3 py-2.5 text-left text-13 font-medium transition-colors"
                >
                  <LogOut aria-hidden="true" className="size-4 shrink-0" />
                  Sair da conta
                </button>
              </animated.div>
            ) : null,
          )}
        </div>
      </div>
    </aside>
  );
}
