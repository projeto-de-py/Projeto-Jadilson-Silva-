# Frontend — Jadilson Silva Adv.

Cliente React 19 + Vite do **Sistema de Gestão de Casos e Agenda**. Fala com o
backend FastAPI (porta 8000) pelo proxy `/api` do Vite, então cookies de
sessão e CSRF funcionam na mesma origem — nenhum `fetch` direto para outra
porta.

## Como rodar

```powershell
npm install        # uma vez
npm run dev        # http://127.0.0.1:5173 (strictPort: 5173)
```

O backend precisa estar no ar (ver `backend/README.md`):

```powershell
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Scripts

| Comando | O que faz |
|---|---|
| `npm run dev` | servidor de desenvolvimento (HMR) na 5173 |
| `npm run build` | build de produção em `dist/` |
| `npm run preview` | serve o build de produção |
| `npm run lint` | ESLint — **deve ficar em 0 erros** |
| `npm run format` / `format:check` | Prettier |

Não há `npm run test` — os testes de integração ficam no backend (pytest).

## Estrutura

```
src/
  main.jsx                 # root React (StrictMode)
  App.jsx                  # rotas + gate de sessão (sem sessão → /)
  index.css                # tokens @theme Tailwind
  app/navigation.js        # itens de menu (Configurações = somente admin)
  app/layouts/DashboardLayout.jsx   # sidebar + topbar + Outlet
  components/
    layout/                # Sidebar, Topbar, BuscaGlobal, PainelNotificacoes
    modais/                # cadastro de cliente/caso/prazo/contribuidor
    ui/                    # design system (barrel index.js)
  context/                 # sessão (csrf), área de atuação
  data/escritorio.js       # mapeadores API ↔ telas + hook useCarteira
  hooks/                   # useNotificacoes, useDocumentos, useToast…
  lib/api.js               # cliente HTTP único (apiJson/api/apiIA)
  pages/                   # Login, DashBoard/{Home,Processos,Prazos,…}
```

## Padrões importantes

- **Cliente HTTP único:** `src/lib/api.js` (`apiJson("casos", {...})` →
  `/api/casos`). Mutações POST/PUT/PATCH/DELETE enviam o header
  `X-CSRF-Token` (o backend valida cookie + header).
- **Sessão:** restaurada em `GET /api/auth/me` no `App.jsx`; 401 → login.
- **Estados de dados:** telas usam `useCarteira` (`carregando`/`erro`) e
  mostram estado vazio só quando não há erro — nunca fingir "sem dados" com a
  API fora.
- **Guards:** rotas exigem sessão; `/configuracoes` exige `administrador`
  (rota + menu) — **o backend também exige** (é o controle que vale).
- **Lint:** `react-hooks/set-state-in-effect` proíbe `setState` síncrono em
  `useEffect` — use `.then()` com flag `cancelado` (padrão em `Agenda.jsx`).
- **Código morto confirmado (não usar):** `src/api/client.js`,
  `src/context/AuthProvider.jsx`, `auth-context.js` — legado de um segundo
  sistema de sessão; o ativo é `src/lib/api.js`.
- `pages/DashBoard` usa grafia **`DashBoard`** (B maiúsculo) — invariante.

## Limitação conhecida

A tela **Documentos** salva o conteúdo no backend (`/api/documentos`); apenas
as **pastas personalizadas** continuam em `localStorage`. A **IA** usa
`PRAZOS = []` estático no resumo. Ambos estão registrados em
`docs/ROTEIRO_PRE_ENTREGA.md`.
