import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { RotatingText } from "@/components/ui/RotatingText";
import { cn } from "@/lib/cn";
import logo from "@/assets/images/Logo_Jadilson.png";
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
  "bg-surface-muted text-ink placeholder:text-ink-muted h-14 w-full rounded-full border-0 px-6 text-16",
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
          className="pointer-events-none absolute inset-0 bg-gradient-to-r from-transparent to-black/60"
        />

        <p className="font-heading text-24 relative z-10 font-bold tracking-tight text-white">
          Jadilson Silva Adv.
        </p>

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

      {/* Painel direito: formulário centralizado, em pílulas */}
      <div className="relative flex min-h-screen flex-col items-center justify-center p-6">
        <div className="w-full max-w-sm">
          <div className="flex flex-col items-center text-center">
            <img src={logo} alt="" aria-hidden="true" className="size-12" />
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

          {checking ? (
            <p role="status" className="text-ink-muted text-14 mt-8 text-center">Verificando sessão…</p>
          ) : user ? (
            <Button className="mt-8 h-14 w-full rounded-full text-[16px]" onClick={onLogout} disabled={loading}>
              {loading ? "Saindo…" : "Sair"}
            </Button>
          ) : (
            <form
              className="mt-8 space-y-4"
              onSubmit={(event) => { setShowPassword(false); onLogin(event); }}
              aria-busy={loading}
              aria-describedby={error ? "auth-error" : undefined}
            >
              <div>
                <label htmlFor="email" className="sr-only">E-mail</label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  placeholder="E-mail"
                  autoComplete="email"
                  className={pilula}
                  onInvalid={(event) => event.currentTarget.setCustomValidity("Informe um e-mail válido.")}
                  onInput={(event) => event.currentTarget.setCustomValidity("")}
                  disabled={loading}
                  maxLength={254}
                  required
                />
              </div>

              <div className="relative">
                <label htmlFor="password" className="sr-only">Senha</label>
                <input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Senha"
                  autoComplete="current-password"
                  className={cn(pilula, "pr-14")}
                  onInvalid={(event) => event.currentTarget.setCustomValidity("Informe sua senha.")}
                  onInput={(event) => event.currentTarget.setCustomValidity("")}
                  disabled={loading}
                  maxLength={1024}
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((visible) => !visible)}
                  aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}
                  className="text-ink-muted hover:text-ink absolute inset-y-0 right-0 flex items-center justify-center pr-6 transition-colors"
                >
                  <SFSymbol icon={showPassword ? IconEye : IconEyeSlash} />
                </button>
              </div>

              <Button type="submit" className="h-14 w-full rounded-full text-[16px] font-semibold" disabled={loading}>
                {loading ? "Entrando…" : "Entrar"}
              </Button>

              <p className="text-center">
                <a
                  href="#"
                  onClick={(event) => unavailable(event, "A recuperação de senha ainda não está disponível. Procure o administrador.")}
                  className="text-ink-muted hover:text-ink text-14 transition-colors"
                >
                  Esqueceu a senha?
                </a>
              </p>
            </form>
          )}
        </div>

        <p className="text-ink-muted text-12 absolute inset-x-6 bottom-8 text-center">
          Ao continuar, você concorda com os Termos de Serviço e a Política de Privacidade.
        </p>
      </div>
    </main>
  );
}
