import { useState } from "react";
import { IconPersonBadgePlus, IconBuilding2, IconPerson } from "symbols-react";
import {
  Modal,
  Button,
  Input,
  Textarea,
  Field,
  useToast,
} from "@/components/ui";

export function ModalCadastrarCliente({ open, onOpenChange, onClienteSalvo }) {
  const { toast } = useToast();
  const [salvando, setSalvando] = useState(false);
  const [tipo, setTipo] = useState("PF");
  const [form, setForm] = useState({
    nome: "",
    documento: "",
    email: "",
    telefone: "",
    cidade: "",
    observacoes: "",
  });
  const [erros, setErros] = useState({});

  function handleChange(campo, valor) {
    setForm((prev) => ({ ...prev, [campo]: valor }));
    if (erros[campo]) {
      setErros((prev) => ({ ...prev, [campo]: undefined }));
    }
  }

  function validar() {
    const novosErros = {};
    if (!form.nome.trim()) {
      novosErros.nome = "Informe o nome ou razão social do cliente.";
    }
    if (!form.telefone.trim()) {
      novosErros.telefone = "Informe um telefone de contato.";
    }
    setErros(novosErros);
    return Object.keys(novosErros).length === 0;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!validar()) return;

    setSalvando(true);
    // Simula salvamento rápido com feedback de qualidade
    try {
      const novoCliente = {
        id: Date.now(),
        nome: form.nome.trim(),
        tipo,
        documento: form.documento.trim() || (tipo === "PF" ? "000.000.000-00" : "00.000.000/0001-00"),
        email: form.email.trim(),
        telefone: form.telefone.trim(),
        cidade: form.cidade.trim() || "Paulo Afonso - BA",
        observacoes: form.observacoes.trim(),
        processosAtivos: 0,
        criadoEm: new Date().toLocaleDateString("pt-BR"),
      };

      if (onClienteSalvo) {
        onClienteSalvo(novoCliente);
      }

      toast({
        tipo: "sucesso",
        titulo: "Cliente cadastrado com sucesso!",
        descricao: `${novoCliente.nome} já está disponível para vinculação a processos.`,
      });

      // Reset form
      setForm({
        nome: "",
        documento: "",
        email: "",
        telefone: "",
        cidade: "",
        observacoes: "",
      });
      onOpenChange(false);
    } catch {
      toast({
        tipo: "erro",
        titulo: "Erro ao cadastrar cliente",
        descricao: "Verifique os dados informados e tente novamente.",
      });
    } finally {
      setSalvando(false);
    }
  }

  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      titulo="Novo Cliente"
      descricao="Cadastre uma pessoa física ou jurídica para vincular a processos e prazos."
      className="max-w-xl"
      footer={
        <>
          <Button
            variant="ghost"
            type="button"
            onClick={() => onOpenChange(false)}
            disabled={salvando}
          >
            Cancelar
          </Button>
          <Button
            variant="primary"
            type="submit"
            form="form-cadastrar-cliente"
            loading={salvando}
          >
            <IconPersonBadgePlus className="size-4" fill="currentColor" />
            Cadastrar Cliente
          </Button>
        </>
      }
    >
      <form
        id="form-cadastrar-cliente"
        onSubmit={handleSubmit}
        className="space-y-4 pt-2"
      >
        {/* Seletor de Tipo (Pessoa Física / Pessoa Jurídica) */}
        <div className="grid grid-cols-2 gap-2 p-1 bg-surface-muted rounded-input border border-border">
          <button
            type="button"
            onClick={() => setTipo("PF")}
            className={`flex items-center justify-center gap-2 py-2 text-14 font-medium rounded-input transition-colors ${
              tipo === "PF"
                ? "bg-surface text-ink shadow-xs border border-border"
                : "text-ink-muted hover:text-ink"
            }`}
          >
            <IconPerson className="size-4" fill="currentColor" />
            Pessoa Física (PF)
          </button>
          <button
            type="button"
            onClick={() => setTipo("PJ")}
            className={`flex items-center justify-center gap-2 py-2 text-14 font-medium rounded-input transition-colors ${
              tipo === "PJ"
                ? "bg-surface text-ink shadow-xs border border-border"
                : "text-ink-muted hover:text-ink"
            }`}
          >
            <IconBuilding2 className="size-4" fill="currentColor" />
            Pessoa Jurídica (PJ)
          </button>
        </div>

        {/* Nome / Razão Social */}
        <Field
          label={tipo === "PF" ? "Nome Completo" : "Razão Social / Nome Fantasia"}
          id="cliente-nome"
          error={erros.nome}
        >
          <Input
            id="cliente-nome"
            placeholder={tipo === "PF" ? "Ex.: Maria da Conceição Silva" : "Ex.: Construtora Alagoas Ltda."}
            value={form.nome}
            onChange={(e) => handleChange("nome", e.target.value)}
            disabled={salvando}
            autoFocus
          />
        </Field>

        {/* Documento (CPF / CNPJ) e Telefone */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field
            label={tipo === "PF" ? "CPF" : "CNPJ"}
            id="cliente-documento"
            hint="Opcional no primeiro contato"
          >
            <Input
              id="cliente-documento"
              placeholder={tipo === "PF" ? "000.000.000-00" : "00.000.000/0001-00"}
              value={form.documento}
              onChange={(e) => handleChange("documento", e.target.value)}
              disabled={salvando}
            />
          </Field>

          <Field
            label="Telefone / WhatsApp"
            id="cliente-telefone"
            error={erros.telefone}
          >
            <Input
              id="cliente-telefone"
              placeholder="(82) 99999-9999"
              value={form.telefone}
              onChange={(e) => handleChange("telefone", e.target.value)}
              disabled={salvando}
            />
          </Field>
        </div>

        {/* E-mail e Cidade */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="E-mail de Contato" id="cliente-email">
            <Input
              id="cliente-email"
              type="email"
              placeholder="cliente@email.com"
              value={form.email}
              onChange={(e) => handleChange("email", e.target.value)}
              disabled={salvando}
            />
          </Field>

          <Field label="Cidade / UF" id="cliente-cidade">
            <Input
              id="cliente-cidade"
              placeholder="Paulo Afonso - BA"
              value={form.cidade}
              onChange={(e) => handleChange("cidade", e.target.value)}
              disabled={salvando}
            />
          </Field>
        </div>

        {/* Observações / Anotações */}
        <Field
          label="Observações / Detalhes"
          id="cliente-observacoes"
          hint="Notas do primeiro atendimento ou indicação"
        >
          <Textarea
            id="cliente-observacoes"
            placeholder="Informações adicionais sobre o cliente ou o caso inicial..."
            value={form.observacoes}
            onChange={(e) => handleChange("observacoes", e.target.value)}
            disabled={salvando}
            rows={3}
          />
        </Field>
      </form>
    </Modal>
  );
}
