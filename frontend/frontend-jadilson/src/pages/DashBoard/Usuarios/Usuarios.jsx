import { useCallback, useEffect, useMemo, useState } from "react";
import {
  IconPerson2,
  IconPersonBadgePlus,
  IconMagnifyingglass,
} from "symbols-react";
import {
  Badge,
  Button,
  EmptyState,
  Field,
  Input,
  Modal,
  Select,
  Table,
  useToast,
} from "@/components/ui";
import { useSessao } from "@/context/sessao";
import { apiJson } from "@/lib/api";

const PERFIS = { ADVOGADO: "Advogado", FUNCIONARIO: "Funcionário" };
const FORM_VAZIO = { nome: "", email: "", senha: "", perfil: "ADVOGADO" };

/** Gestão de contas — exclusiva do advogado principal (RF02/RF03).
 *
 * A API não aceita `administrador` nem senha em PATCH: esta tela apenas cria
 * usuários comuns e altera `ativo`/`perfil`, preservando a trava de privilégio.
 */
export function Usuarios() {
  const { csrf } = useSessao();
  const { toast } = useToast();
  const [usuarios, setUsuarios] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [busca, setBusca] = useState("");
  const [modalAberto, setModalAberto] = useState(false);
  const [form, setForm] = useState(FORM_VAZIO);
  const [formErro, setFormErro] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [processandoId, setProcessandoId] = useState(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro("");
    try {
      const dados = await apiJson("usuarios");
      setUsuarios(Array.isArray(dados) ? dados : []);
    } catch (falha) {
      setErro(falha.message || "Não foi possível carregar os usuários.");
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    let cancelado = false;
    apiJson("usuarios")
      .then((dados) => {
        if (cancelado) return;
        setUsuarios(Array.isArray(dados) ? dados : []);
        setErro("");
      })
      .catch((falha) => {
        if (!cancelado) setErro(falha.message || "Não foi possível carregar os usuários.");
      })
      .finally(() => {
        if (!cancelado) setCarregando(false);
      });
    return () => {
      cancelado = true;
    };
  }, []);

  const filtrados = useMemo(() => {
    const termo = busca.trim().toLowerCase();
    if (!termo) return usuarios;
    return usuarios.filter(
      (u) =>
        u.nome?.toLowerCase().includes(termo) ||
        u.email?.toLowerCase().includes(termo),
    );
  }, [usuarios, busca]);

  async function criar(evento) {
    evento.preventDefault();
    if (salvando) return;
    setSalvando(true);
    setFormErro("");
    try {
      const criado = await apiJson("usuarios", {
        method: "POST",
        csrf,
        body: { ...form, senha: form.senha },
      });
      setUsuarios((prev) => [criado, ...prev]);
      setModalAberto(false);
      setForm(FORM_VAZIO);
      toast({
        tipo: "sucesso",
        titulo: "Usuário criado",
        descricao: `${criado.nome} já pode acessar o sistema.`,
      });
    } catch (falha) {
      setFormErro(falha.message || "Não foi possível criar o usuário.");
    } finally {
      setSalvando(false);
    }
  }

  async function alterar(usuario, corpo, descricao) {
    setProcessandoId(usuario.id);
    try {
      const atualizado = await apiJson(`usuarios/${usuario.id}`, {
        method: "PATCH",
        csrf,
        body: corpo,
      });
      setUsuarios((prev) =>
        prev.map((u) => (u.id === atualizado.id ? atualizado : u)),
      );
      toast({ tipo: "sucesso", titulo: "Usuário atualizado", descricao });
    } catch (falha) {
      toast({
        tipo: "erro",
        titulo: "Não foi possível atualizar o usuário",
        descricao: falha.message || "Tente novamente em instantes.",
      });
    } finally {
      setProcessandoId(null);
    }
  }

  const colunas = [
    {
      id: "nome",
      rotulo: "Usuário",
      render: (u) => (
        <div>
          <p className="font-medium text-ink">{u.nome}</p>
          <p className="text-12 text-ink-muted">{u.email}</p>
        </div>
      ),
    },
    {
      id: "perfil",
      rotulo: "Perfil",
      render: (u) => (
        <Select
          aria-label={`Perfil de ${u.nome}`}
          value={u.perfil}
          disabled={processandoId === u.id}
          onChange={(e) => alterar(u, { perfil: e.target.value }, `Perfil de ${u.nome} alterado.`)}
          className="h-9 w-36 text-12"
        >
          <option value="ADVOGADO">Advogado</option>
          <option value="FUNCIONARIO">Funcionário</option>
        </Select>
      ),
    },
    {
      id: "situacao",
      rotulo: "Situação",
      render: (u) => (
        <div className="flex flex-wrap gap-2">
          {u.administrador && <Badge tone="primary">Administrador</Badge>}
          <Badge tone={u.ativo ? "ok" : "vencido"}>
            {u.ativo ? "Ativo" : "Inativo"}
          </Badge>
        </div>
      ),
    },
    {
      id: "acoes",
      rotulo: "Ações",
      alinhar: "direita",
      render: (u) => (
        <Button
          variant="secondary"
          className="h-8 px-3 text-12"
          disabled={processandoId === u.id || u.administrador}
          onClick={() =>
            alterar(
              u,
              { ativo: !u.ativo },
              `${u.nome} ${u.ativo ? "foi desativado" : "foi reativado"}.`,
            )
          }
        >
          {u.ativo ? "Desativar" : "Reativar"}
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-heading text-24 font-bold tracking-tight text-ink">
            Gestão de Usuários
          </h2>
          <p className="text-14 text-ink-muted">
            Crie contas, defina o perfil e controle quem pode acessar o escritório.
            Acesso restrito ao advogado principal.
          </p>
        </div>
        <Button
          variant="primary"
          onClick={() => {
            setForm(FORM_VAZIO);
            setFormErro("");
            setModalAberto(true);
          }}
          className="shrink-0 gap-2"
        >
          <IconPersonBadgePlus className="size-4" fill="currentColor" />
          Novo Usuário
        </Button>
      </div>

      <div className="bg-surface border-border flex items-center gap-4 rounded-card border p-4">
        <div className="relative flex-1">
          <IconMagnifyingglass
            fill="currentColor"
            className="text-ink-muted pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2"
          />
          <Input
            aria-label="Buscar usuários"
            placeholder="Buscar por nome ou e-mail..."
            className="ps-9"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
          />
        </div>
      </div>

      {erro ? (
        <div role="alert" className="border-border rounded-card border px-6 py-10 text-center">
          <p className="text-14 font-medium text-status-vencido-ink">
            Não foi possível carregar os usuários
          </p>
          <p className="text-13 text-ink-muted mt-1">{erro}</p>
          <Button variant="secondary" className="mt-4" onClick={carregar}>
            Tentar novamente
          </Button>
        </div>
      ) : (
        <Table
          colunas={colunas}
          dados={filtrados}
          carregando={carregando}
          vazio={
            <EmptyState
              icon={IconPerson2}
              titulo="Nenhum usuário encontrado"
              descricao={
                busca
                  ? "Nenhum usuário corresponde à busca."
                  : "Cadastre o primeiro usuário do escritório."
              }
            />
          }
        />
      )}

      <Modal
        open={modalAberto}
        onOpenChange={setModalAberto}
        titulo="Novo Usuário"
        descricao="A conta é criada sem privilégios administrativos."
        footer={
          <>
            <Button
              variant="ghost"
              type="button"
              onClick={() => setModalAberto(false)}
              disabled={salvando}
            >
              Cancelar
            </Button>
            <Button
              variant="primary"
              type="submit"
              form="form-criar-usuario"
              loading={salvando}
            >
              Criar Usuário
            </Button>
          </>
        }
      >
        <form
          id="form-criar-usuario"
          onSubmit={criar}
          className="space-y-4 pt-2"
        >
          <Field label="Nome completo" id="user-nome">
            <Input
              id="user-nome"
              value={form.nome}
              onChange={(e) => setForm((prev) => ({ ...prev, nome: e.target.value }))}
              autoFocus
              disabled={salvando}
            />
          </Field>
          <Field label="E-mail" id="user-email">
            <Input
              id="user-email"
              type="email"
              value={form.email}
              onChange={(e) => setForm((prev) => ({ ...prev, email: e.target.value }))}
              disabled={salvando}
            />
          </Field>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Senha inicial" id="user-senha" hint="Mínimo de 6 caracteres">
              <Input
                id="user-senha"
                type="password"
                value={form.senha}
                onChange={(e) => setForm((prev) => ({ ...prev, senha: e.target.value }))}
                disabled={salvando}
              />
            </Field>
            <Field label="Perfil" id="user-perfil">
              <Select
                id="user-perfil"
                value={form.perfil}
                onChange={(e) => setForm((prev) => ({ ...prev, perfil: e.target.value }))}
                disabled={salvando}
              >
                {Object.entries(PERFIS).map(([valor, rotulo]) => (
                  <option key={valor} value={valor}>
                    {rotulo}
                  </option>
                ))}
              </Select>
            </Field>
          </div>
          {formErro && (
            <p role="alert" className="text-13 text-status-vencido-ink">
              {formErro}
            </p>
          )}
        </form>
      </Modal>
    </div>
  );
}
