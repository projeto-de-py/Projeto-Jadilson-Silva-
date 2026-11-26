import { useEffect, useMemo, useState } from "react";
import {
  Badge,
  Button,
  Checkbox,
  Field,
  Modal,
  Select,
  useToast,
} from "@/components/ui";
import { useSessao } from "@/context/sessao";
import { apiJson } from "@/lib/api";

const PERMISSOES = [
  {
    id: "pode_visualizar",
    rotulo: "Visualizar o caso",
    descricao: "Concessão mínima — sempre ativa",
    fixa: true,
  },
  { id: "pode_registrar_andamento", rotulo: "Registrar andamentos" },
  { id: "pode_gerenciar_prazos", rotulo: "Gerenciar prazos" },
  { id: "pode_gerenciar_processos", rotulo: "Gerenciar processos" },
  { id: "pode_gerenciar_compromissos", rotulo: "Gerenciar compromissos da agenda" },
];

function permissoesPadrao() {
  return PERMISSOES.reduce((acc, p) => ({ ...acc, [p.id]: p.fixa }), {});
}

/** Acesso de usuários a um caso (RF03/RF04) — apenas administradores.
 *
 * A API já impõe o escopo: fora dele os recursos respondem 404. Aqui o admin
 * concede/revoga o vínculo e escolhe as quatro permissões de escrita.
 */
export function ModalAcessoCaso({ open, onOpenChange, casoId, casoTitulo }) {
  const { csrf } = useSessao();
  const { toast } = useToast();
  const [usuarios, setUsuarios] = useState([]);
  const [concessoes, setConcessoes] = useState([]);
  const [carregando, setCarregando] = useState(Boolean(open && casoId));
  const [erro, setErro] = useState("");
  const [usuarioId, setUsuarioId] = useState("");
  const [flags, setFlags] = useState(permissoesPadrao);
  const [salvando, setSalvando] = useState(false);
  const [revogandoId, setRevogandoId] = useState(null);

  useEffect(() => {
    if (!open || !casoId) return undefined;
    let cancelado = false;
    Promise.all([
      apiJson("usuarios"),
      apiJson(`casos/${casoId}/usuarios`),
    ])
      .then(([todos, acessos]) => {
        if (cancelado) return;
        setUsuarios(Array.isArray(todos) ? todos : []);
        setConcessoes(Array.isArray(acessos) ? acessos : []);
        setErro("");
      })
      .catch((falha) => {
        if (!cancelado) {
          setErro(falha.message || "Não foi possível carregar os acessos do caso.");
        }
      })
      .finally(() => {
        if (!cancelado) setCarregando(false);
      });
    return () => {
      cancelado = true;
    };
  }, [open, casoId]);

  const disponiveis = useMemo(
    () =>
      usuarios.filter(
        (u) =>
          !u.administrador &&
          !concessoes.some((c) => c.ativo && c.usuario?.id === u.id),
      ),
    [usuarios, concessoes],
  );

  async function conceder(evento) {
    evento.preventDefault();
    if (!usuarioId || salvando) return;
    setSalvando(true);
    try {
      const criado = await apiJson(`casos/${casoId}/usuarios`, {
        method: "POST",
        csrf,
        body: { usuario_id: Number(usuarioId), ...flags },
      });
      setConcessoes((prev) => [criado, ...prev]);
      setUsuarioId("");
      setFlags(permissoesPadrao());
      toast({
        tipo: "sucesso",
        titulo: "Acesso concedido",
        descricao: `${criado.usuario?.nome || "Usuário"} agora pode acessar o caso.`,
      });
    } catch (falha) {
      toast({
        tipo: "erro",
        titulo: "Não foi possível conceder o acesso",
        descricao: falha.message || "Tente novamente em instantes.",
      });
    } finally {
      setSalvando(false);
    }
  }

  async function revogar(concessao) {
    setRevogandoId(concessao.usuario?.id);
    try {
      await apiJson(`casos/${casoId}/usuarios/${concessao.usuario.id}`, {
        method: "DELETE",
        csrf,
      });
      setConcessoes((prev) => prev.filter((c) => c !== concessao));
      toast({
        tipo: "sucesso",
        titulo: "Acesso revogado",
        descricao: `${concessao.usuario?.nome || "Usuário"} não acessa mais o caso.`,
      });
    } catch (falha) {
      toast({
        tipo: "erro",
        titulo: "Não foi possível revogar o acesso",
        descricao: falha.message || "Tente novamente em instantes.",
      });
    } finally {
      setRevogandoId(null);
    }
  }

  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      titulo="Acesso ao caso"
      descricao={casoTitulo || "Escolha quem pode acompanhar este caso e o que pode fazer."}
      className="max-w-2xl"
    >
      {erro && (
        <p role="alert" className="text-13 text-status-vencido-ink mb-4">
          {erro}
        </p>
      )}
      {carregando ? (
        <p role="status" className="text-14 text-ink-muted py-8 text-center">
          Carregando acessos…
        </p>
      ) : (
        <div className="space-y-6 pt-2">
          <section className="space-y-3">
            <h3 className="text-13 font-semibold text-ink">
              Usuários com acesso
            </h3>
            {concessoes.length === 0 ? (
              <p className="text-13 text-ink-muted">
                Nenhum usuário foi atribuído a este caso.
              </p>
            ) : (
              <ul className="divide-border divide-y rounded-card border border-border">
                {concessoes.map((concessao) => (
                  <li
                    key={concessao.usuario?.id}
                    className="flex flex-wrap items-center justify-between gap-3 px-4 py-3"
                  >
                    <div>
                      <p className="text-14 font-medium text-ink">
                        {concessao.usuario?.nome}
                      </p>
                      <p className="text-12 text-ink-muted">
                        {concessao.usuario?.email}
                      </p>
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {PERMISSOES.filter((p) => concessao[p.id]).map((p) => (
                          <Badge key={p.id} tone="primary">
                            {p.rotulo}
                          </Badge>
                        ))}
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      className="h-8 px-3 text-12 text-status-vencido-ink"
                      loading={revogandoId === concessao.usuario?.id}
                      disabled={revogandoId !== null}
                      onClick={() => revogar(concessao)}
                    >
                      Revogar
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <form
            onSubmit={conceder}
            className="border-border bg-surface-muted/30 space-y-4 rounded-card border p-4"
          >
            <h3 className="text-13 font-semibold text-ink">
              Conceder acesso
            </h3>
            <Field label="Usuário" id="acesso-usuario">
              <Select
                id="acesso-usuario"
                value={usuarioId}
                onChange={(e) => setUsuarioId(e.target.value)}
                disabled={salvando}
              >
                <option value="">Selecione um usuário…</option>
                {disponiveis.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.nome} — {u.email}
                  </option>
                ))}
              </Select>
            </Field>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {PERMISSOES.map((permissao) => (
                <label
                  key={permissao.id}
                  className="flex items-start gap-2.5 text-13 text-ink"
                >
                  <Checkbox
                    className="mt-0.5"
                    checked={Boolean(flags[permissao.id])}
                    disabled={permissao.fixa || salvando}
                    onCheckedChange={(valor) =>
                      setFlags((prev) => ({ ...prev, [permissao.id]: valor === true }))
                    }
                  />
                  <span>
                    {permissao.rotulo}
                    {permissao.descricao && (
                      <span className="text-ink-muted block text-12">
                        {permissao.descricao}
                      </span>
                    )}
                  </span>
                </label>
              ))}
            </div>

            <div className="flex justify-end">
              <Button
                type="submit"
                variant="primary"
                loading={salvando}
                disabled={!usuarioId}
              >
                Conceder acesso
              </Button>
            </div>
          </form>
        </div>
      )}
    </Modal>
  );
}
