import { useState } from "react";
import { Inbox, Plus, Trash2 } from "lucide-react";
import {
  Avatar,
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Checkbox,
  Drawer,
  EmptyState,
  Input,
  Modal,
  Pagination,
  Popover,
  Select,
  Skeleton,
  Spinner,
  Switch,
  Table,
  Tabs,
  Textarea,
  Tooltip,
} from "@/components/ui";
import { useToast } from "@/hooks/useToast";

const cores = [
  { token: "--color-bg", group: "Superfícies" },
  { token: "--color-surface", group: "Superfícies" },
  { token: "--color-surface-muted", group: "Superfícies" },
  { token: "--color-border", group: "Superfícies" },
  { token: "--color-ink", group: "Texto" },
  { token: "--color-ink-muted", group: "Texto" },
  { token: "--color-primary", group: "Marca" },
  { token: "--color-primary-hover", group: "Marca" },
  { token: "--color-primary-soft", group: "Marca" },
  { token: "--color-accent", group: "Marca" },
];

const status = [
  { token: "--color-status-vencido", rotulo: "Vencido" },
  { token: "--color-status-hoje", rotulo: "Vence hoje" },
  { token: "--color-status-critico", rotulo: "Crítico (1–2 dias)" },
  { token: "--color-status-atencao", rotulo: "Atenção (3–7 dias)" },
  { token: "--color-status-ok", rotulo: "Tranquilo" },
  { token: "--color-status-cumprido", rotulo: "Cumprido" },
];

const escala = [
  { px: 12, exemplo: "Label de campo" },
  { px: 14, exemplo: "Corpo de tabela" },
  { px: 16, exemplo: "Texto corrido" },
  { px: 20, exemplo: "Subtítulo de seção" },
  { px: 28, exemplo: "Título de página" },
  { px: 40, exemplo: "Número de KPI" },
];

const raios = [
  { token: "--radius-input", rotulo: "Inputs e botões (8px)" },
  { token: "--radius-card", rotulo: "Cards (12px)" },
  { token: "--radius-modal", rotulo: "Modais e drawers (16px)" },
  { token: "--radius-badge", rotulo: "Badges (999px)" },
];

const espacamentos = [4, 8, 12, 16, 24, 32, 48, 64];

function Secao({ titulo, children }) {
  return (
    <section className="space-y-4">
      <h2 className="text-20 font-semibold">{titulo}</h2>
      {children}
    </section>
  );
}

function Swatch({ token, nome }) {
  return (
    <div className="space-y-2">
      <div
        className="border-border h-16 rounded-card border"
        style={{ background: `var(${token})` }}
      />
      <p className="text-12 text-ink-muted font-medium">{nome ?? token}</p>
    </div>
  );
}

const processosDemo = [
  {
    id: 1,
    numero: "0000001-12.2026.8.00.0100",
    cliente: "Maria Conceição",
    comarca: "Maceió",
    status: "Ativo",
    prazo: "10/10/2026",
    tom: "hoje",
  },
  {
    id: 2,
    numero: "0000042-30.2026.8.00.0100",
    cliente: "João Pereira",
    comarca: "Arapiraca",
    status: "Ativo",
    prazo: "15/10/2026",
    tom: "atencao",
  },
  {
    id: 3,
    numero: "0000110-05.2026.8.00.0100",
    cliente: "Construtora Alagoas",
    comarca: "Maceió",
    status: "Suspenso",
    prazo: "28/10/2026",
    tom: "ok",
  },
  {
    id: 4,
    numero: "0000233-77.2025.8.00.0100",
    cliente: "Ana Lúcia Santos",
    comarca: "Penedo",
    status: "Ativo",
    prazo: "01/10/2026",
    tom: "vencido",
  },
];

function Sobreposicoes() {
  const [modalAberto, setModalAberto] = useState(false);
  const [drawerAberto, setDrawerAberto] = useState(false);
  const { toast } = useToast();

  return (
    <Secao titulo="Sobreposições: Modal, Drawer, Popover, Tooltip e Toast">
      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={() => setModalAberto(true)}>Abrir modal</Button>
        <Button variant="secondary" onClick={() => setDrawerAberto(true)}>
          Abrir drawer
        </Button>
        <Popover
          trigger={<Button variant="secondary">Abrir popover</Button>}
          align="start"
        >
          <div className="space-y-3">
            <p className="text-14 font-medium">Ações rápidas</p>
            <p className="text-14 text-ink-muted">
              Anexar peça, gerar minuta ou exportar o processo.
            </p>
            <Button className="w-full">Continuar</Button>
          </div>
        </Popover>
        <Tooltip label="Gerencia as configurações da conta">
          <Button variant="ghost">Passe o mouse</Button>
        </Tooltip>
        <Button
          variant="secondary"
          onClick={() =>
            toast({
              tipo: "sucesso",
              titulo: "Processo salvo",
              descricao: "As alterações foram registradas com sucesso.",
            })
          }
        >
          Toast de sucesso
        </Button>
        <Button
          variant="danger"
          onClick={() =>
            toast({
              tipo: "erro",
              titulo: "Falha ao salvar",
              descricao: "Verifique a conexão e tente novamente.",
            })
          }
        >
          Toast de erro
        </Button>
      </div>

      <Modal
        open={modalAberto}
        onOpenChange={setModalAberto}
        titulo="Excluir processo?"
        descricao="Esta ação não pode ser desfeita. Os prazos vinculados também serão removidos."
        footer={
          <>
            <Button variant="secondary" onClick={() => setModalAberto(false)}>
              Cancelar
            </Button>
            <Button variant="danger" onClick={() => setModalAberto(false)}>
              Excluir
            </Button>
          </>
        }
      >
        <Input
          label='Digite "EXCLUIR" para confirmar'
          id="ds-confirmar"
          placeholder="EXCLUIR"
        />
      </Modal>

      <Drawer
        open={drawerAberto}
        onOpenChange={setDrawerAberto}
        titulo="Novo prazo"
        descricao="0000001-12.2026.8.00.0100"
        footer={
          <>
            <Button variant="ghost" onClick={() => setDrawerAberto(false)}>
              Cancelar
            </Button>
            <Button onClick={() => setDrawerAberto(false)}>Salvar prazo</Button>
          </>
        }
      >
        <div className="space-y-4">
          <Input
            label="Tipo de prazo"
            id="ds-prazo-tipo"
            placeholder="Contestação"
          />
          <Input
            label="Data limite"
            id="ds-prazo-data"
            type="date"
            defaultValue="2026-10-15"
          />
          <Textarea label="Observações" id="ds-prazo-obs" rows={4} />
        </div>
      </Drawer>
    </Secao>
  );
}

function TabsDemo() {
  return (
    <Secao titulo="Tabs, Switch e Checkbox">
      <Tabs
        defaultValue="resumo"
        tabs={[
          {
            value: "resumo",
            rotulo: "Resumo",
            conteudo: (
              <p className="text-14 text-ink-muted">
                Aba padrão: indicador desliza com mola snappy (layoutId).
              </p>
            ),
          },
          {
            value: "prazos",
            rotulo: "Prazos",
            conteudo: (
              <p className="text-14 text-ink-muted">
                Aqui entra a lista de prazos do processo (Fase 6).
              </p>
            ),
          },
          {
            value: "historico",
            rotulo: "Histórico",
            conteudo: (
              <p className="text-14 text-ink-muted">
                Linha do tempo de movimentações (Fase 8).
              </p>
            ),
          },
        ]}
      />
      <div className="flex flex-wrap items-center gap-6 pt-2">
        <label className="flex items-center gap-3 text-14">
          <Switch id="ds-switch" defaultChecked />
          Alertas de prazo por e-mail
        </label>
        <label className="flex items-center gap-3 text-14">
          <Checkbox id="ds-checkbox" defaultChecked />
          Lembrar 7 dias antes
        </label>
        <label className="flex items-center gap-3 text-14">
          <Checkbox id="ds-checkbox-2" />
          Incluir feriados de Maceió
        </label>
      </div>
    </Secao>
  );
}

function TabelaDemo() {
  const [ordenacao, setOrdenacao] = useState({
    campo: "prazo",
    direcao: "asc",
  });
  const [carregando, setCarregando] = useState(false);
  const [vazia, setVazia] = useState(false);
  const [pagina, setPagina] = useState(3);

  function ordenar(campo) {
    setOrdenacao((atual) => ({
      campo,
      direcao:
        atual.campo === campo && atual.direcao === "asc" ? "desc" : "asc",
    }));
  }

  function simularCarregamento() {
    setCarregando(true);
    setTimeout(() => setCarregando(false), 1500);
  }

  const colunas = [
    { id: "numero", rotulo: "Processo", ordenavel: true },
    { id: "cliente", rotulo: "Cliente", ordenavel: true },
    { id: "comarca", rotulo: "Comarca" },
    {
      id: "status",
      rotulo: "Status",
      render: (linha) => <Badge tone="primary">{linha.status}</Badge>,
    },
    {
      id: "prazo",
      rotulo: "Próximo prazo",
      alinhar: "direita",
      ordenavel: true,
      render: (linha) => <Badge tone={linha.tom}>{linha.prazo}</Badge>,
    },
  ];

  const dados = vazia
    ? []
    : [...processosDemo].sort((a, b) => {
        const resultado = String(a[ordenacao.campo]).localeCompare(
          String(b[ordenacao.campo]),
          "pt-BR",
        );
        return ordenacao.direcao === "asc" ? resultado : -resultado;
      });

  return (
    <Secao titulo="Table e Pagination">
      <div className="flex flex-wrap gap-3">
        <Button variant="secondary" onClick={simularCarregamento}>
          Simular carregamento
        </Button>
        <Button variant="ghost" onClick={() => setVazia((v) => !v)}>
          {vazia ? "Voltar aos dados" : "Simular lista vazia"}
        </Button>
      </div>

      <Table
        colunas={colunas}
        dados={dados}
        carregando={carregando}
        ordenacao={ordenacao}
        onOrdenar={ordenar}
        onLinhaClique={(linha) =>
          alert(`Abrir processo ${linha.numero} (Fase 5)`)
        }
        vazio={
          <EmptyState
            icon={Inbox}
            titulo="Nenhum processo encontrado."
            descricao="Ajuste os filtros ou cadastre um novo processo."
            acao={<Button>Novo processo</Button>}
          />
        }
      />

      <Pagination
        pagina={pagina}
        totalPaginas={7}
        totalItens={64}
        porPagina={10}
        onMudar={setPagina}
      />
    </Secao>
  );
}

export function DesignSystemPage() {
  return (
    <main className="bg-bg text-ink min-h-screen">
      <div className="mx-auto max-w-content space-y-12 px-6 py-10">
        <header className="space-y-2">
          <h1 className="font-heading text-40 font-bold">
            Design System — Tokens
          </h1>
          <p className="text-16 text-ink-muted">
            Página de teste das Fases 1 a 3: tokens, componentes base e
            componentes de sobreposição/dados.
          </p>
        </header>

        <Secao titulo="Cores">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
            {cores.map((cor) => (
              <Swatch key={cor.token} token={cor.token} />
            ))}
          </div>
        </Secao>

        <Secao titulo="Status de prazo">
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-6">
              {status.map((item) => (
                <Swatch key={item.token} token={item.token} />
              ))}
            </div>
            <div className="flex flex-wrap gap-2">
              {status.map((item) => (
                <span
                  key={item.token}
                  className="rounded-badge px-3 py-1 text-12 font-medium"
                  style={{
                    background: `var(${item.token}-soft)`,
                    color: `var(${item.token}-ink)`,
                  }}
                >
                  {item.rotulo}
                </span>
              ))}
            </div>
          </div>
        </Secao>

        <Secao titulo="Tipografia">
          <div className="space-y-3">
            <p className="font-heading text-28 font-bold">
              Inter Bold — H1 e títulos de página
            </p>
            <p className="text-16">
              SF Pro — textos menores, corpo, tabelas, botões e labels (Inter
              como fallback fora dos aparelhos Apple).
            </p>
            <div className="border-border space-y-2 border-t pt-4">
              {escala.map((item) => (
                <p
                  key={item.px}
                  className="text-ink-muted leading-tight"
                  style={{ fontSize: `${item.px}px` }}
                >
                  {item.px}px — {item.exemplo}
                </p>
              ))}
            </div>
            <p className="text-16 tabular-nums">
              Números tabulares: 1.234,56 · 0000000-00.0000.0.00.0000
            </p>
          </div>
        </Secao>

        <Secao titulo="Raios e elevação">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {raios.map((item) => (
              <div key={item.token} className="space-y-2">
                <div
                  className="border-border bg-surface h-20 border"
                  style={{ borderRadius: `var(${item.token})` }}
                />
                <p className="text-12 text-ink-muted">{item.rotulo}</p>
              </div>
            ))}
            <div className="space-y-2">
              <div className="bg-surface border-border shadow-popover h-20 rounded-modal border" />
              <p className="text-12 text-ink-muted">
                Sombra só em sobreposições
              </p>
            </div>
          </div>
        </Secao>

        <Secao titulo="Espaçamento (grade de 4px)">
          <div className="space-y-2">
            {espacamentos.map((px) => (
              <div key={px} className="flex items-center gap-3">
                <span className="text-12 text-ink-muted w-10 tabular-nums">
                  {px}px
                </span>
                <div
                  className="bg-primary-soft h-4 rounded-badge"
                  style={{ width: `${px * 4}px` }}
                />
              </div>
            ))}
          </div>
        </Secao>

        <Secao titulo="Button">
          <div className="flex flex-wrap items-center gap-3">
            <Button>Salvar processo</Button>
            <Button variant="secondary">Cancelar</Button>
            <Button variant="ghost">Voltar</Button>
            <Button variant="danger">
              <Trash2 className="size-4" />
              Excluir processo
            </Button>
            <Button loading>Salvando</Button>
            <Button disabled>Indisponível</Button>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Button className="h-9 px-3">Pequeno</Button>
            <Button>Médio</Button>
            <Button className="h-11 px-6 text-16">Grande</Button>
            <Button className="h-11 px-6 text-16">
              <Plus className="size-4" />
              Novo prazo
            </Button>
          </div>
        </Secao>

        <Secao titulo="Formulários">
          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="E-mail"
              id="ds-email"
              placeholder="voce@exemplo.com"
              hint="Usamos o e-mail apenas para alertas de prazo."
            />
            <Input
              label="Número do processo"
              id="ds-numero"
              defaultValue="12345-00.0000.0.00.0000"
              error="Número do processo inválido. Use o formato 0000000-00.0000.0.00.0000."
            />
            <Select label="Status" id="ds-status" defaultValue="ativo">
              <option value="ativo">Ativo</option>
              <option value="suspenso">Suspenso</option>
              <option value="arquivado">Arquivado</option>
            </Select>
            <Textarea
              label="Observações"
              id="ds-obs"
              placeholder="Anotações sobre o processo…"
            />
          </div>
        </Secao>

        <Secao titulo="Badge">
          <div className="flex flex-wrap gap-2">
            <Badge>Neutro</Badge>
            <Badge tone="primary">Ativo</Badge>
            <Badge tone="vencido">Vencido há 2 dias</Badge>
            <Badge tone="hoje">Vence hoje</Badge>
            <Badge tone="critico">Faltam 2 dias</Badge>
            <Badge tone="atencao">Faltam 5 dias</Badge>
            <Badge tone="ok">Faltam 12 dias</Badge>
            <Badge tone="cumprido">Cumprido</Badge>
          </div>
        </Secao>

        <Secao titulo="Card">
          <div className="grid gap-4 sm:grid-cols-2">
            <Card>
              <CardHeader>
                <div className="space-y-1">
                  <CardTitle>Ação de cobrança</CardTitle>
                  <CardDescription>
                    0000000-00.0000.0.00.0000 · Comarca de Maceió
                  </CardDescription>
                </div>
                <Badge tone="primary">Ativo</Badge>
              </CardHeader>
              <CardContent>
                <p className="text-14 text-ink-muted">
                  Card padrão: borda de 1px, sem sombra.
                </p>
              </CardContent>
            </Card>
            <Card interactive>
              <CardHeader>
                <div className="space-y-1">
                  <CardTitle>Card interativo</CardTitle>
                  <CardDescription>
                    Sobe 2px no hover com mola snappy.
                  </CardDescription>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-14 text-ink-muted">
                  Use só nos cards que são clicáveis.
                </p>
              </CardContent>
            </Card>
          </div>
        </Secao>

        <Secao titulo="Skeleton, Spinner, Avatar e EmptyState">
          <div className="grid gap-6 sm:grid-cols-2">
            <div className="space-y-5">
              <div className="space-y-2">
                <Skeleton className="h-4 w-1/3" />
                <Skeleton className="h-4 w-2/3" />
                <Skeleton className="h-20 w-full" />
              </div>
              <div className="flex items-center gap-4">
                <Spinner />
                <Spinner className="text-primary size-8" />
                <span className="text-14 text-ink-muted">
                  rótulo próprio via aria-label
                </span>
              </div>
              <div className="flex items-center gap-3">
                <Avatar nome="Jadilson Silva" size="sm" />
                <Avatar nome="Jadilson Silva" />
                <Avatar nome="Maria Conceição" size="lg" />
              </div>
            </div>
            <EmptyState
              icon={Inbox}
              titulo="Nenhum prazo cadastrado."
              descricao="Adicione o primeiro prazo deste processo."
              acao={
                <Button>
                  <Plus className="size-4" />
                  Novo prazo
                </Button>
              }
            />
          </div>
        </Secao>

        <Sobreposicoes />
        <TabsDemo />
        <TabelaDemo />
      </div>
    </main>
  );
}
