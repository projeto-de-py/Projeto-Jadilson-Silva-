import { useState } from "react";
import { apiJson } from "@/lib/api";
import { Button, Input, Modal, Select } from "@/components/ui";
import { useId } from "react";

const FORM_INICIAL = { nome: "", email: "", senha: "", perfil: "ADVOGADO" };

export function ModalNovoContribuidor({ open, onOpenChange, csrf }) {
  const perfilId = useId();
  const [form, setForm] = useState(FORM_INICIAL);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  function atualizar(campo, valor) {
    setForm((atual) => ({ ...atual, [campo]: valor }));
    setErro("");
    setSucesso("");
  }
  async function cadastrar(event) {
    event.preventDefault();
    setSalvando(true);
    setErro("");
    setSucesso("");
    try {
      await apiJson("usuarios", { method: "POST", body: form, csrf });
      setSucesso("Contribuidor cadastrado com sucesso.");
      setForm(FORM_INICIAL);
    } catch (error) {
      setErro(error.message || "Não foi possível cadastrar o contribuidor.");
    } finally {
      setSalvando(false);
    }
  }
  function fechar(aberto) {
    onOpenChange(aberto);
    if (!aberto) {
      setForm(FORM_INICIAL);
      setErro("");
      setSucesso("");
    }
  }
  return (
    <Modal open={open} onOpenChange={fechar} titulo="Adicionar novo contribuidor" descricao="Cadastre um advogado ou funcionário para acessar o escritório.">
      <form onSubmit={cadastrar} className="space-y-4">
        <Input id="contribuidor-nome" label="Nome completo" autoComplete="name" maxLength={120} required value={form.nome} onChange={(event) => atualizar("nome", event.target.value)} />
        <Input id="contribuidor-email" label="E-mail" type="email" autoComplete="email" required value={form.email} onChange={(event) => atualizar("email", event.target.value)} />
        <Input id="contribuidor-senha" label="Senha inicial" type="password" autoComplete="new-password" minLength={6} maxLength={72} hint="A senha deve ter pelo menos 6 caracteres." required value={form.senha} onChange={(event) => atualizar("senha", event.target.value)} />
        <Select id={perfilId} label="Tipo de acesso" value={form.perfil} onChange={(event) => atualizar("perfil", event.target.value)}>
          <option value="ADVOGADO">Advogado</option>
          <option value="FUNCIONARIO">Funcionário</option>
        </Select>
        {erro && <p role="alert" className="text-status-vencido-ink text-13">{erro}</p>}
        {sucesso && <p role="status" className="text-status-ok-ink text-13">{sucesso}</p>}
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={() => fechar(false)} disabled={salvando}>Fechar</Button>
          <Button type="submit" loading={salvando}>Cadastrar contribuidor</Button>
        </div>
      </form>
    </Modal>
  );
}
