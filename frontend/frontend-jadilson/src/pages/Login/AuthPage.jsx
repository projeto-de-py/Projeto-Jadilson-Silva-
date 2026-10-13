import { useState } from "react";
import { BorderBeam } from "border-beam";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { cn } from "@/lib/cn";
import { useAuth } from "@/context/auth-context";
import logo from "@/assets/images/Logo_Jadilson.png";

import { IconAt, IconEye, IconEyeSlash, IconLock } from "symbols-react";

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

export function AuthPage({ user, onLogin, onLogout, loading, checking, error }) {
  const [showPassword, setShowPassword] = useState(false);
  const [notice, setNotice] = useState("");
  function unavailable(event, message) { event.preventDefault(); setNotice(message); }

  return (
    <main className="relative md:h-screen md:overflow-hidden lg:grid lg:grid-cols-2">
      <div className="bg-muted/60 relative hidden h-full flex-col border-r p-10 lg:flex">
        <div className="from-background absolute inset-0 z-10 bg-linear-to-t to-transparent" />
        <div className="z-10 flex items-center gap-3">
          <img src={logo} alt="" aria-hidden="true" className="size-10" />
          <p className="text-xl font-semibold">Jadilson Silva Adv.</p>
        </div>
        <div className="absolute inset-0">
          <FloatingPaths position={1} />
          <FloatingPaths position={-1} />
        </div>
      </div>
      <div className="relative flex min-h-screen flex-col justify-center p-4">
        <div
          aria-hidden
          className="absolute inset-0 isolate contain-strict -z-10 opacity-60"
        >
          <div className="absolute top-0 right-0 h-320 w-140 translate-y-[-87.5%] rounded-full bg-[radial-gradient(68.54%_68.72%_at_55.02%_31.46%,rgba(148,163,184,0.06)_0,rgba(148,163,184,0.02)_50%,rgba(148,163,184,0.01)_80%)]" />
          <div className="absolute top-0 right-0 h-320 w-60 [translate:5%_-50%] rounded-full bg-[radial-gradient(50%_50%_at_50%_50%,rgba(148,163,184,0.04)_0,rgba(148,163,184,0.01)_80%,transparent_100%)]" />
          <div className="absolute top-0 right-0 h-320 w-60 translate-y-[-87.5%] rounded-full bg-[radial-gradient(50%_50%_at_50%_50%,rgba(148,163,184,0.04)_0,rgba(148,163,184,0.01)_80%,transparent_100%)]" />
        </div>
        <div className="mx-auto space-y-4 sm:w-sm">
          <div className="flex items-center gap-3 lg:hidden">
            <img src={logo} alt="" aria-hidden="true" className="size-10" />
            <p className="text-xl font-semibold">Jadilson Silva Adv.</p>
          </div>
          {error && <p id="auth-error" role="alert" className="text-destructive text-sm">{error}</p>}
          {notice && !user && <p role="status" className="text-muted-foreground text-sm">{notice}</p>}
          {checking ? <p role="status" className="text-muted-foreground">Verificando sessão…</p> : user ? (
            <div className="space-y-4">
              <h1 className="font-heading text-2xl font-bold tracking-wide">Bem-vindo, {user.nome}</h1>
              <p className="text-muted-foreground text-base">Você está conectado ao portal.</p>
              <Button size="lg" className="w-full" onClick={onLogout} disabled={loading}>{loading ? 'Saindo…' : 'Sair'}</Button>
            </div>
          ) : (<>
          <div className="flex flex-col space-y-1">
            <h1 className="font-heading text-2xl font-bold tracking-wide">
              Entre na sua conta
            </h1>
            <p className="text-muted-foreground text-base">
              Utilize seu e-mail e senha para acessar o portal.
            </p>
          </div>

          <form className="space-y-3" onSubmit={(event) => { setShowPassword(false); onLogin(event); }} aria-busy={loading} aria-describedby={error ? "auth-error" : undefined}>
            <div className="space-y-1.5">
              <label
                htmlFor="email"
                className="text-foreground block text-xs font-medium"
              >
                E-mail
              </label>
              <div className="relative h-max">
                <Input
                  id="email"
                  name="email"
                  placeholder="seu.email@exemplo.com"
                  className="peer ps-9"
                  type="email"
                  autoComplete="email"
                  onInvalid={(event) => event.currentTarget.setCustomValidity("Informe um e-mail válido.")}
                  onInput={(event) => event.currentTarget.setCustomValidity("")}
                  disabled={loading}
                  maxLength={254}
                  required
                />
                <div className="text-muted-foreground pointer-events-none absolute inset-y-0 inset-s-0 flex items-center justify-center ps-3 peer-disabled:opacity-50">
                  <SFSymbol icon={IconAt} />
                </div>
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label
                  htmlFor="password"
                  className="text-foreground block text-xs font-medium"
                >
                  Senha
                </label>
                <a
                  href="#"
                  onClick={(event) => unavailable(event, "A recuperação de senha ainda não está disponível. Procure o administrador.")}
                  className="text-muted-foreground hover:text-primary text-xs underline underline-offset-4"
                >
                  Esqueceu a senha?
                </a>
              </div>
              <div className="relative h-max">
                <Input
                  id="password"
                  name="password"
                  placeholder="••••••••"
                  className="peer ps-9 pe-10"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  onInvalid={(event) => event.currentTarget.setCustomValidity("Informe sua senha.")}
                  onInput={(event) => event.currentTarget.setCustomValidity("")}
                  disabled={loading}
                  maxLength={1024}
                  required
                />
                <div className="text-muted-foreground pointer-events-none absolute inset-y-0 inset-s-0 flex items-center justify-center ps-3 peer-disabled:opacity-50">
                  <SFSymbol icon={IconLock} />
                </div>
                <button
                  type="button"
                  onClick={() => setShowPassword((visible) => !visible)}
                  aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}
                  className="text-muted-foreground hover:text-foreground absolute inset-y-0 inset-e-0 flex items-center justify-center pe-3 transition-colors"
                >
                  <SFSymbol icon={showPassword ? IconEyeSlash : IconEye} />
                </button>
              </div>
            </div>

            <BorderBeam
              className="w-full"
              colorVariant="ocean"
              size="md"
              strength={0.6}
              theme="dark"
              duration={7}
            >
              <Button type="submit" className="w-full" disabled={loading}>
                <span>{loading ? "Entrando…" : "Entrar"}</span>
              </Button>
            </BorderBeam>
          </form>
          </>)}
          <p className="text-muted-foreground mt-4 text-center text-sm">
            Ao continuar, você concorda com nossos{" "}
            <a
              href="#"
              className="hover:text-primary underline underline-offset-4"
            >
              Termos de Serviço
            </a>{" "}
            e{" "}
            <a
              href="#"
              className="hover:text-primary underline underline-offset-4"
            >
              Política de Privacidade
            </a>
            .
          </p>
        </div>
      </div>
    </main>
  );
}

const floatingPathsCache = new Map();

function getFloatingPaths(position) {
  const cached = floatingPathsCache.get(position);
  if (cached) return cached;

  const paths = Array.from({ length: 36 }, (_, i) => ({
    id: i,
    d: `M-${380 - i * 5 * position} -${189 + i * 6}C-${
      380 - i * 5 * position
    } -${189 + i * 6} -${312 - i * 5 * position} ${216 - i * 6} ${
      152 - i * 5 * position
    } ${343 - i * 6}C${616 - i * 5 * position} ${470 - i * 6} ${
      684 - i * 5 * position
    } ${875 - i * 6} ${684 - i * 5 * position} ${875 - i * 6}`,
    width: 0.5 + i * 0.03,
    strokeOpacity: 0.1 + i * 0.03,
    style: {
      "--draw-duration": `${2.2 + (i % 7) * 0.4}s`,
      "--draw-delay": `${i * 0.07 + (position === 1 ? 0 : 0.4)}s`,
    },
  }));

  floatingPathsCache.set(position, paths);
  return paths;
}

function FloatingPaths({ position }) {
  const paths = getFloatingPaths(position);

  return (
    <div className="pointer-events-none absolute inset-0">
      <svg
        className="h-full w-full text-slate-200/60"
        viewBox="0 0 696 316"
        fill="none"
      >
        <title>Caminhos decorativos</title>
        {paths.map((path) => (
          <path
            key={path.id}
            d={path.d}
            className="floating-path"
            pathLength="1"
            stroke="currentColor"
            strokeWidth={path.width}
            strokeOpacity={path.strokeOpacity}
            style={path.style}
          />
        ))}
      </svg>
    </div>
  );
}
