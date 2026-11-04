import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { RotatingText } from "@/components/ui/RotatingText";
import { cn } from "@/lib/cn";
import logo from "@/assets/images/Logo_Juridico_Jadilson_Silva.png";
import imagemLogin from "@/assets/images/Login_imagem.png";

import {
  IconEye,
  IconEyeSlash,
  IconCalendarBadgeCheckmark,
  IconWandAndSparkles,
  IconScalemass,
} from "symbols-react";

function SFSymbol({ icon: Icon, className, ...props }) {
  return (
    <Icon
      fill="currentColor"
      className={cn("size-4 shrink-0", className)}
      aria-hidden="true"
      {...props}
    />
  );
}

const RECURSOS = [
  {
    icone: IconCalendarBadgeCheckmark,
    titulo: "Prazos monitorados todo dia",
    descricao: "Vencidos, de hoje e dos próximos 7 dias, sempre em primeiro plano.",
  },
  {
    icone: IconWandAndSparkles,
    titulo: "Redator IA para suas peças",
    descricao: "Rascunhos de contestação, recurso e manifestação prontos para revisar.",
  },
  {
    icone: IconScalemass,
    titulo: "Bancário, previdenciário e consumidor",
    descricao: "Toda a carteira do escritório organizada por área, em um só lugar.",
  },
];

const pilula = [
  "squircle bg-surface-muted text-ink placeholder:text-ink-muted h-14 w-full rounded-input border border-border px-5 text-16",
  "transition-shadow focus:ring-2 focus:ring-ink/40 focus:outline-none",
  "disabled:cursor-not-allowed disabled:opacity-50",
].join(" ");

const FOCOS = ["prioridade", "prazo", "área", "cliente"];

export function AuthPage({ user, onLogin, onLogout, loading, checking, error }) {
  const [showPassword, setShowPassword] = useState(false);
  const [notice, setNotice] = useState("");
  function unavailable(event, message) { event.preventDefault(); setNotice(message); }

  return (
    <main className="bg-black relative md:h-screen md:overflow-hidden lg:grid lg:grid-cols-2">
      {/* Painel esquerdo: imagem + identidade + o que o sistema faz */}
      <div className="border-border relative hidden h-full flex-col justify-between overflow-hidden border-r p-12 lg:flex">
        <img
          src={imagemLogin}
          alt=""
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 size-full object-cover object-[20%_center]"
        />
        <div aria-hidden="true" className="pointer-events-none absolute inset-0 bg-black/45" />
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 bg-linear-to-r from-transparent to-black/60"
        />

        <img
          src={logo}
          alt="Jadilson Silva Advocacia"
          className="relative z-10 h-14 w-auto object-contain object-left"
        />

        <div className="relative z-10 max-w-sm space-y-8">
          <h2 className="font-heading text-28 font-bold tracking-tight text-white leading-tight">
            Sua carteira processual, organizada por{" "}
            <RotatingText textos={FOCOS} />.
          </h2>
          <ul className="space-y-6">
            {RECURSOS.map((r) => (
              <li key={r.titulo} className="flex items-start gap-4">
                <span className="bg-black/40 border-white/15 text-white/80 flex size-10 shrink-0 items-center justify-center rounded-badge border backdrop-blur">
                  <SFSymbol icon={r.icone} className="size-4" />
                </span>
                <div>
                  <p className="text-14 font-semibold text-white">{r.titulo}</p>
                  <p className="text-13 text-white/65 mt-1">{r.descricao}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <p className="text-12 relative z-10 text-white/60">
          Escritório de advocacia · Paulo Afonso/BA
        </p>
      </div>

      {/* Painel direito: formulário centralizado */}
      <div className="relative flex min-h-screen flex-col items-center justify-center p-6">
        <div className="w-full max-w-sm">
          <div className="flex flex-col items-center text-center">
            <img
              src={logo}
              alt="Jadilson Silva Advocacia"
              className="logo-marca h-16 w-auto object-contain"
            />
            <h1 className="font-heading text-28 font-bold tracking-tight text-ink mt-6">
              {user ? `Bem-vindo, ${user.nome}` : "Entrar"}
            </h1>
            <p className="text-ink-muted text-14 mt-2">
              {user ? "Você está conectado ao portal." : "Use seu e-mail e senha do escritório."}
            </p>
          </div>

          <div className="mt-6 space-y-2 text-center empty:hidden">
            {error && <p id="auth-error" role="alert" className="text-status-vencido-ink text-13">{error}</p>}
            {notice && !user && <p role="status" className="text-ink-muted text-13">{notice}</p>}
          </div>

          {user ? (
            <div className="mt-8 space-y-4">
              <div className="border-border bg-surface-muted/40 rounded-card border p-4 text-center">
                <p className="text-14 font-semibold">{user.nome}</p>
                <p className="text-ink-muted text-12 mt-0.5">{user.email}</p>
              </div>
              <Button
                variant="secondary"
                onClick={onLogout}
                loading={loading}
                className="h-14 w-full rounded-input text-16 font-semibold"
              >
                Sair da conta
              </Button>
            </div>
          ) : (
            <form
              onSubmit={(event) => {
                setNotice("");
                onLogin(event);
              }}
              className="mt-8 space-y-4"
            >
              <div>
                <label htmlFor="auth-email" className="sr-only">
                  E-mail
                </label>
                <input
                  id="auth-email"
                  name="email"
                  type="email"
                  required
                  autoComplete="email"
                  placeholder="E-mail profissional"
                  disabled={loading || checking}
                  aria-describedby={error ? "auth-error" : undefined}
                  className={pilula}
                />
              </div>

              <div className="relative">
                <label htmlFor="auth-password" className="sr-only">
                  Senha
                </label>
                <input
                  id="auth-password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  required
                  autoComplete="current-password"
                  placeholder="Senha"
                  disabled={loading || checking}
                  aria-describedby={error ? "auth-error" : undefined}
                  className={cn(pilula, "pr-14")}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((current) => !current)}
                  aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}
                  className="text-ink-muted hover:text-ink absolute top-1/2 right-4 -translate-y-1/2 rounded-full p-2 transition-colors"
                >
                  <SFSymbol icon={showPassword ? IconEyeSlash : IconEye} />
                </button>
              </div>

              <div className="flex justify-end">
                <a
                  href="#recuperar"
                  onClick={(e) =>
                    unavailable(
                      e,
                      "Procure o administrador do escritório para redefinir sua senha.",
                    )
                  }
                  className="text-ink-muted hover:text-ink text-13 transition-colors"
                >
                  Esqueceu a senha?
                </a>
              </div>

              <Button
                type="submit"
                variant="primary"
                loading={loading || checking}
                className="h-14 w-full rounded-input text-16 font-semibold"
              >
                Entrar
              </Button>
            </form>
          )}
        </div>
      </div>
    </main>
  );
}
