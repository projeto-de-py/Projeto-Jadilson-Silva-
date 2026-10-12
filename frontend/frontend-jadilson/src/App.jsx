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
  return (
    <MotionConfig reducedMotion="user">
      <ToastProvider>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<LoginOuRedirect />} />
              <Route path="/login" element={<Navigate to="/" replace />} />
              <Route path="/design-system" element={<DesignSystemPage />} />

              <Route element={<Protegida><DashboardLayout /></Protegida>}>
                <Route path="/home" element={<Home />} />
                <Route path="/processos" element={<Processos />} />
                <Route path="/prazos" element={<Prazos />} />
                <Route path="/agenda" element={<Agenda />} />
                <Route path="/clientes" element={<Clientes />} />
                <Route path="/configuracoes" element={<Configuracoes />} />
              </Route>

              <Route path="*" element={<Navigate to="/home" replace />} />
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </ToastProvider>
    </MotionConfig>
  );
}

export default App;
