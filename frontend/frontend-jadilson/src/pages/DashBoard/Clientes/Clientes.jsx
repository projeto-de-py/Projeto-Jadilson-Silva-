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
  IconTrash,
  IconSquareAndPencil,
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
  Modal,
  useToast,
} from "@/components/ui";
import { ModalCadastrarCliente } from "@/components/modais/ModalCadastrarCliente";
import { useSessao } from "@/context/sessao";
import { notificarAtualizacaoDados, useCarteira } from "@/data/escritorio";
import { apiJson } from "@/lib/api";

export function Clientes() {
  const { csrf } = useSessao();
  const { toast } = useToast();
  const { clientes, setClientes } = useCarteira();
  const [modalAberto, setModalAberto] = useState(false);
  const [clienteEmEdicao, setClienteEmEdicao] = useState(null);
  const [paraRemover, setParaRemover] = useState(null);
  const [removendo, setRemovendo] = useState(false);
  const [busca, setBusca] = useState("");
  const [filtroTipo, setFiltroTipo] = useState("TODOS");

  const clientesFiltrados = useMemo(() => {
    return clientes.filter((c) => {
      const matchTipo = filtroTipo === "TODOS" || c.tipo === filtroTipo;
      const termo = busca.toLowerCase();
      const matchBusca =
        c.nome.toLowerCase().includes(termo) ||
        c.documento.toLowerCase().includes(termo) ||
        c.email.toLowerCase().includes(termo) ||
        c.cidade.toLowerCase().includes(termo);
      return matchTipo && matchBusca;
    });
  }, [clientes, busca, filtroTipo]);

  function handleAbrirCriacao() {
    setClienteEmEdicao(null);
    setModalAberto(true);
  }

  function handleAbrirEdicao(cliente) {
    setClienteEmEdicao(cliente);
    setModalAberto(true);
  }

  function handleClienteSalvo(clienteSalvo) {
    setClientes((prev) => {
      const index = prev.findIndex((c) => c.id === clienteSalvo.id);
      if (index >= 0) {
        const atualizados = [...prev];
        atualizados[index] = { ...prev[index], ...clienteSalvo };
        return atualizados;
      }
      return [clienteSalvo, ...prev];
    });
  }

  async function confirmarRemocao() {
    if (!paraRemover) return;
    setRemovendo(true);
    try {
      await apiJson(`clientes/${paraRemover.id}`, {
        method: "DELETE",
        csrf,
      });
      setClientes((prev) => prev.filter((c) => c.id !== paraRemover.id));
      notificarAtualizacaoDados();
      toast({
        tipo: "sucesso",
        titulo: "Cliente removido",
        descricao: `${paraRemover.nome} foi removido do banco de dados.`,
      });
      setParaRemover(null);
    } catch (erro) {
      toast({
        tipo: "erro",
        titulo: "Não foi possível remover o cliente",
        descricao: erro.message || "Tente novamente em instantes.",
      });
    } finally {
      setRemovendo(false);
    }
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
            Cadastre, edite e acompanhe os clientes vinculados aos casos do escritório no banco de dados.
          </p>
        </div>

        <Button
          variant="primary"
          onClick={handleAbrirCriacao}
          className="shrink-0 gap-2"
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
                  <div className="flex min-w-0 items-center gap-4">
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

                  <div className="flex shrink-0 items-center gap-1.5">
                    <Badge
                      tone={cliente.tipo === "PF" ? "neutral" : "primary"}
                      className="text-12 font-medium"
                    >
                      {cliente.tipo}
                    </Badge>
                    <button
                      type="button"
                      onClick={() => handleAbrirEdicao(cliente)}
                      aria-label={`Editar cliente ${cliente.nome}`}
                      title="Editar cliente"
                      className="text-ink-muted hover:text-ink hover:bg-surface-muted flex size-8 items-center justify-center rounded-input transition-colors"
                    >
                      <IconSquareAndPencil className="size-4" fill="currentColor" />
                    </button>
                    <button
                      type="button"
                      onClick={() => setParaRemover(cliente)}
                      aria-label={`Remover cliente ${cliente.nome}`}
                      title="Remover cliente"
                      className="text-ink-muted hover:text-status-vencido hover:bg-surface-muted flex size-8 items-center justify-center rounded-input transition-colors"
                    >
                      <IconTrash className="size-4" fill="currentColor" />
                    </button>
                  </div>
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

      {/* Modal Reutilizável de Cadastro/Edição de Cliente */}
      <ModalCadastrarCliente
        open={modalAberto}
        onOpenChange={(aberto) => {
          setModalAberto(aberto);
          if (!aberto) setClienteEmEdicao(null);
        }}
        clienteEmEdicao={clienteEmEdicao}
        onClienteSalvo={handleClienteSalvo}
      />

      {/* Modal de Confirmação de Remoção */}
      <Modal
        open={!!paraRemover}
        onOpenChange={(aberto) => !aberto && !removendo && setParaRemover(null)}
        titulo="Remover cliente?"
        descricao={
          paraRemover
            ? `Tem certeza de que deseja remover "${paraRemover.nome}" do banco de dados?`
            : undefined
        }
        footer={
          <>
            <Button
              variant="secondary"
              type="button"
              onClick={() => setParaRemover(null)}
              disabled={removendo}
            >
              Cancelar
            </Button>
            <Button
              variant="danger"
              type="button"
              loading={removendo}
              onClick={confirmarRemocao}
              className="gap-2"
            >
              <IconTrash className="size-4" fill="currentColor" />
              Remover cliente
            </Button>
          </>
        }
      />
    </div>
  );
}
