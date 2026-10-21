import { useState, useMemo } from "react";
import {
  IconPerson2,
  IconPersonBadgePlus,
  IconMagnifyingglass,
  IconPhone,
  IconEnvelope,
  IconBuilding2,
  IconPerson,
  IconMappin,
  IconFolder,
} from "symbols-react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Button,
  Badge,
  Input,
  Select,
  EmptyState,
} from "@/components/ui";
import { ModalCadastrarCliente } from "@/components/modais/ModalCadastrarCliente";

const CLIENTES_INICIAIS = [
  {
    id: 1,
    nome: "Maria da Conceição Silva",
    tipo: "PF",
    documento: "123.456.789-00",
    telefone: "(82) 99876-5432",
    email: "maria.conceicao@email.com",
    cidade: "Paulo Afonso - BA",
    processosAtivos: 2,
    criadoEm: "10/10/2026",
    observacoes: "Revisional de contrato bancário em andamento.",
  },
  {
    id: 2,
    nome: "João Pereira dos Santos",
    tipo: "PF",
    documento: "987.654.321-11",
    telefone: "(82) 99123-4567",
    email: "joao.pereira@email.com",
    cidade: "Arapiraca - AL",
    processosAtivos: 1,
    criadoEm: "12/10/2026",
    observacoes: "Ação de indenização por negativação indevida (consumidor).",
  },
  {
    id: 3,
    nome: "Construtora Alagoas Ltda.",
    tipo: "PJ",
    documento: "12.345.678/0001-90",
    telefone: "(82) 3221-0099",
    email: "juridico@construtoraalagoas.com.br",
    cidade: "Paulo Afonso - BA",
    processosAtivos: 5,
    criadoEm: "05/10/2026",
    observacoes: "Assessoria jurídica em contratos bancários e financiamentos.",
  },
  {
    id: 4,
    nome: "Ana Lúcia Santos",
    tipo: "PF",
    documento: "456.789.123-44",
    telefone: "(82) 98888-1122",
    email: "ana.lucia@email.com",
    cidade: "Delmiro Gouveia - AL",
    processosAtivos: 1,
    criadoEm: "01/10/2026",
    observacoes: "Processo previdenciário de aposentadoria por tempo de contribuição.",
  },
  {
    id: 5,
    nome: "Carlos Eduardo Lima",
    tipo: "PF",
    documento: "321.654.987-22",
    telefone: "(82) 99654-3311",
    email: "carlos.lima@email.com",
    cidade: "Paulo Afonso - BA",
    processosAtivos: 1,
    criadoEm: "14/10/2026",
    observacoes: "Restabelecimento de benefício por incapacidade junto ao INSS.",
  },
  {
    id: 6,
    nome: "Patrícia Gomes Barreto",
    tipo: "PF",
    documento: "741.852.963-15",
    telefone: "(82) 99221-7744",
    email: "patricia.gomes@email.com",
    cidade: "Paulo Afonso - BA",
    processosAtivos: 1,
    criadoEm: "16/10/2026",
    observacoes: "Cobrança indevida de tarifas bancárias.",
  },
];

export function Clientes() {
  const [clientes, setClientes] = useState(CLIENTES_INICIAIS);
  const [modalAberto, setModalAberto] = useState(false);
  const [busca, setBusca] = useState("");
  const [filtroTipo, setFiltroTipo] = useState("TODOS");

  const clientesFiltrados = useMemo(() => {
    return clientes.filter((c) => {
      const matchTipo =
        filtroTipo === "TODOS" || c.tipo === filtroTipo;
      const termo = busca.toLowerCase();
      const matchBusca =
        c.nome.toLowerCase().includes(termo) ||
        c.documento.toLowerCase().includes(termo) ||
        c.email.toLowerCase().includes(termo) ||
        c.cidade.toLowerCase().includes(termo);
      return matchTipo && matchBusca;
    });
  }, [clientes, busca, filtroTipo]);

  function handleClienteSalvo(novoCliente) {
    setClientes((prev) => [novoCliente, ...prev]);
  }

  return (
    <div className="space-y-8">
      {/* Cabeçalho da Página com Ações */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-heading text-24 font-bold tracking-tight text-ink">
            Gestão de Clientes
          </h2>
          <p className="text-14 text-ink-muted">
            Cadastre e acompanhe os clientes vinculados aos casos do escritório.
          </p>
        </div>

        <Button
          variant="primary"
          onClick={() => setModalAberto(true)}
          className="gap-2 shrink-0"
        >
          <IconPersonBadgePlus className="size-4" fill="currentColor" />
          Novo Cliente
        </Button>
      </div>

      {/* Barra de Filtros e Busca */}
      <div className="bg-surface border-border flex flex-col gap-4 rounded-card border p-4 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <IconMagnifyingglass
            fill="currentColor"
            className="text-ink-muted pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2"
          />
          <Input
            placeholder="Buscar por nome, CPF/CNPJ, e-mail ou cidade..."
            className="ps-9"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
          />
        </div>

        <div className="flex items-center gap-2 sm:w-52">
          <Select
            value={filtroTipo}
            onChange={(e) => setFiltroTipo(e.target.value)}
            className="h-10 text-14"
          >
            <option value="TODOS">Todos os tipos</option>
            <option value="PF">Pessoa Física (PF)</option>
            <option value="PJ">Pessoa Jurídica (PJ)</option>
          </Select>
        </div>
      </div>

      {/* Grid de Cards de Clientes */}
      {clientesFiltrados.length === 0 ? (
        <EmptyState
          icon={IconPerson2}
          titulo="Nenhum cliente encontrado"
          descricao={
            busca
              ? "Nenhum cliente corresponde ao termo pesquisado. Tente outra busca ou limpe o filtro."
              : "Você ainda não possui clientes cadastrados. Clique no botão acima para adicionar o primeiro."
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3">
          {clientesFiltrados.map((cliente) => (
            <Card
              key={cliente.id}
              className="hover:border-accent/40 transition-colors duration-fast flex flex-col justify-between"
            >
              <CardHeader className="pb-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-4">
                    <div className="bg-surface-muted border-border text-primary flex size-12 shrink-0 items-center justify-center rounded-badge border text-16 font-semibold">
                      {cliente.tipo === "PF" ? (
                        <IconPerson className="size-5" fill="currentColor" />
                      ) : (
                        <IconBuilding2 className="size-5" fill="currentColor" />
                      )}
                    </div>
                    <div className="min-w-0">
                      <CardTitle className="truncate text-16 font-semibold">
                        {cliente.nome}
                      </CardTitle>
                      <CardDescription className="text-12">
                        {cliente.tipo === "PF" ? "Pessoa Física" : "Pessoa Jurídica"} · {cliente.documento}
                      </CardDescription>
                    </div>
                  </div>

                  <Badge
                    tone={cliente.tipo === "PF" ? "neutral" : "primary"}
                    className="shrink-0 text-12 font-medium"
                  >
                    {cliente.tipo}
                  </Badge>
                </div>
              </CardHeader>

              <CardContent className="space-y-4 pt-0 text-13">
                <div className="space-y-2 border-t border-border/60 pt-4 text-ink-muted">
                  <div className="flex items-center gap-2">
                    <IconPhone className="size-3.5 shrink-0 text-accent" fill="currentColor" />
                    <span className="truncate">{cliente.telefone}</span>
                  </div>
                  {cliente.email && (
                    <div className="flex items-center gap-2">
                      <IconEnvelope className="size-3.5 shrink-0" fill="currentColor" />
                      <span className="truncate">{cliente.email}</span>
                    </div>
                  )}
                  <div className="flex items-center gap-2">
                    <IconMappin className="size-3.5 shrink-0" fill="currentColor" />
                    <span className="truncate">{cliente.cidade}</span>
                  </div>
                  {cliente.observacoes && (
                    <p className="text-12 text-ink-muted/80 pt-1 line-clamp-2">
                      {cliente.observacoes}
                    </p>
                  )}
                </div>

                <div className="bg-surface-muted/60 flex items-center justify-between rounded-input px-4 py-2 text-12">
                  <span className="text-ink-muted flex items-center gap-2">
                    <IconFolder className="size-3.5" fill="currentColor" />
                    Processos Ativos
                  </span>
                  <span className="font-semibold text-ink">
                    {cliente.processosAtivos}
                  </span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Modal Reutilizável de Cadastro de Cliente */}
      <ModalCadastrarCliente
        open={modalAberto}
        onOpenChange={setModalAberto}
        onClienteSalvo={handleClienteSalvo}
      />
    </div>
  );
}
