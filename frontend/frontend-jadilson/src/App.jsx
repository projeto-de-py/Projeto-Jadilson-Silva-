import { useEffect, useRef, useState } from 'react';
import { api } from './lib/api';
import { MotionConfig } from "motion/react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { DashboardLayout } from "./app/layouts/DashboardLayout";
import { ToastProvider } from "./components/ui";
import { AuthProvider } from "./context/AuthProvider";
import { useAuth } from "./context/auth-context";
import { AuthPage } from "./pages/Login/AuthPage";
import { DesignSystemPage } from "./pages/DesignSystem/DesignSystemPage";
import { Home } from "./pages/DashBoard/Home/Home";
import { Processos } from "./pages/DashBoard/Processos/Processos";
import { Prazos } from "./pages/DashBoard/Prazos/Prazos";
import { Documentos } from "./pages/DashBoard/Documentos/Documentos";
import { EditorDocumento } from "./pages/DashBoard/Documentos/EditorDocumento";
import { Agenda } from "./pages/DashBoard/Agenda/Agenda";
import { Clientes } from "./pages/DashBoard/Clientes/Clientes";
import { Configuracoes } from "./pages/DashBoard/Configuracoes/Configurations";

function Carregando() {
  return (
    <div className="flex min-h-screen items-center justify-center text-muted-foreground">
      Carregando...
    </div>
  );
}

// Exige sessao: sem login valido -> volta para a tela de login
function Protegida({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <Carregando />;
  if (!user) return <Navigate to="/" replace />;
  return children;
}

// Ja logado? Nao mostra o login de novo
function LoginOuRedirect() {
  const { user, loading } = useAuth();
  if (loading) return <Carregando />;
  return user ? <Navigate to="/home" replace /> : <AuthPage />;
}

function App() {
  const [session, setSession] = useState(null);
  const [checking, setChecking] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const busy = useRef(false);
  const revision = useRef(0);

  useEffect(() => {
    let active = true;
    async function restore() {
      if (busy.current) return;
      const currentRevision = revision.current;
      try {
        const current = await api('session');
        if (active && !busy.current && revision.current === currentRevision) { setSession(current); setError(''); }
      } catch (failure) {
        if (active && !busy.current && revision.current === currentRevision && failure.status === 401) setSession(null);
        else if (active && !busy.current && revision.current === currentRevision) setError(failure.message);
      } finally {
        if (active) setChecking(false);
      }
    }
    restore();
    const timer = setInterval(restore, 30000);
    const visible = () => { if (document.visibilityState === 'visible') restore(); };
    document.addEventListener('visibilitychange', visible);
    return () => { active = false; clearInterval(timer); document.removeEventListener('visibilitychange', visible); };
  }, []);

  async function login(event) {
    event.preventDefault();
    if (busy.current || checking) return;
    busy.current = true; revision.current += 1;
    setLoading(true); setError('');
    const form = event.currentTarget;
    const values = new FormData(form);
    try {
      const current = await api('login', { method: 'POST', body: { email: values.get('email'), senha: values.get('password') } });
      form.reset();
      setSession(current);
    } catch (failure) {
      form.elements.password.value = '';
      setError(failure.message);
    } finally { busy.current = false; setLoading(false); }
  }

  async function logout() {
    if (busy.current) return;
    busy.current = true; revision.current += 1;
    setLoading(true); setError('');
    try {
      await api('logout', { method: 'POST', csrf: session.csrf_token });
      setSession(null);
    } catch (failure) {
      if (failure.status === 401) setSession(null);
      setError(failure.message);
    } finally { busy.current = false; setLoading(false); }
  }


  return (
    <MotionConfig reducedMotion="user">
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={session ? <Navigate to="/home" replace /> : <AuthPage onLogin={login} loading={loading} checking={checking} error={error} />} />
            <Route path="/login" element={<Navigate to="/" replace />} />
            <Route path="/design-system" element={checking ? <AuthPage checking /> : session ? <DesignSystemPage /> : <Navigate to="/" replace />} />

            <Route element={checking ? <AuthPage checking /> : session ? <DashboardLayout user={session.usuario} onLogout={logout} loading={loading} error={error} /> : <Navigate to="/" replace />}>
              <Route path="/home" element={<Home />} />
              <Route path="/processos" element={<Processos />} />
              <Route path="/prazos" element={<Prazos />} />
              <Route path="/agenda" element={<Agenda />} />
              <Route path="/documentos" element={<Documentos />} />
              <Route path="/documentos/:id" element={<EditorDocumento />} />
              <Route path="/clientes" element={<Clientes />} />
              <Route path="/configuracoes" element={<Configuracoes />} />
            </Route>

            <Route path="*" element={<Navigate to={session ? "/home" : "/"} replace />} />
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </MotionConfig>
  );
}

export default App;
