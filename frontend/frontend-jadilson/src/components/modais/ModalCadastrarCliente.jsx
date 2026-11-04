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
import { useSessao } from "@/context/sessao";
import { apiJson } from "@/lib/api";
import { mapearClienteApi, notificarAtualizacaoDados } from "@/data/escritorio";

function formatarDocumento(valor, pessoaFisica) {
  const digitos = valor.replace(/\D/g, "").slice(0, pessoaFisica ? 11 : 14);
  if (pessoaFisica) {
    return digitos
      .replace(/^(\d{3})(\d)/, "$1.$2")
      .replace(/^(\d{3})\.(\d{3})(\d)/, "$1.$2.$3")
      .replace(/(\.\d{3})(\d)/, "$1-$2");
  }
  return digitos
    .replace(/^(\d{2})(\d)/, "$1.$2")
    .replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3")
    .replace(/(\.\d{3})(\d)/, "$1/$2")
    .replace(/(\/\d{4})(\d)/, "$1-$2");
}

function formatarTelefone(valor) {
  const digitos = valor.replace(/\D/g, "").slice(0, 11);
  if (digitos.length <= 2) return digitos ? `(${digitos}` : "";
  if (digitos.length <= 6) return digitos.replace(/^(\d{2})(\d+)/, "($1) $2");
  if (digitos.length <= 10) {
    return digitos.replace(/^(\d{2})(\d{4})(\d+)/, "($1) $2-$3");
  }
  return digitos.replace(/^(\d{2})(\d{5})(\d{1,4}).*/, "($1) $2-$3");
}

export function ModalCadastrarCliente({ open, onOpenChange, onClienteSalvo }) {
  const { csrf } = useSessao();
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
    const digitosTel = form.telefone.replace(/\D/g, "");
    if (!digitosTel || (digitosTel.length !== 10 && digitosTel.length !== 11)) {
      novosErros.telefone = "Informe um telefone com DDD (10 ou 11 dígitos).";
    }
    setErros(novosErros);
    return Object.keys(novosErros).length === 0;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!validar()) return;

    setSalvando(true);
    try {
      const payload = {
        nome: form.nome.trim(),
        cpf_cnpj: form.documento.replace(/\D/g, "") || null,
        email: form.email.trim() || null,
        telefone: form.telefone.replace(/\D/g, "") || null,
      };

      const criado = await apiJson("clientes", {
        method: "POST",
        csrf,
        body: payload,
      });

      const novoCliente = {
        ...mapearClienteApi(criado),
        tipo,
        cidade: form.cidade.trim() || "Paulo Afonso - BA",
        observacoes: form.observacoes.trim(),
      };

      if (onClienteSalvo) {
        onClienteSalvo(novoCliente);
      }

      notificarAtualizacaoDados();
      window.dispatchEvent(new CustomEvent("notificacoes:atualizar"));

      toast({
        tipo: "sucesso",
        titulo: "Cliente salvo no banco de dados",
        descricao: `${novoCliente.nome} já está disponível para vinculação a processos.`,
      });

      setForm({
        nome: "",
        documento: "",
        email: "",
        telefone: "",
        cidade: "",
        observacoes: "",
      });
      onOpenChange(false);
    } catch (erro) {
      toast({
        tipo: "erro",
        titulo: "Erro ao cadastrar cliente",
        descricao: erro.message || "Verifique os dados informados (como CPF/CNPJ válido) e tente novamente.",
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
      descricao="Cadastre uma pessoa física ou jurídica no banco de dados do escritório."
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
        <div className="grid grid-cols-2 gap-2 rounded-input border border-border bg-surface-muted p-1">
          <button
            type="button"
            onClick={() => {
              setTipo("PF");
              handleChange("documento", formatarDocumento(form.documento, true));
            }}
            className={`flex items-center justify-center gap-2 rounded-input py-2 text-14 font-medium transition-colors ${
              tipo === "PF"
                ? "border border-border bg-surface text-ink shadow-xs"
                : "text-ink-muted hover:text-ink"
            }`}
          >
            <IconPerson className="size-4" fill="currentColor" />
            Pessoa Física (PF)
          </button>
          <button
            type="button"
            onClick={() => {
              setTipo("PJ");
              handleChange("documento", formatarDocumento(form.documento, false));
            }}
            className={`flex items-center justify-center gap-2 rounded-input py-2 text-14 font-medium transition-colors ${
              tipo === "PJ"
                ? "border border-border bg-surface text-ink shadow-xs"
                : "text-ink-muted hover:text-ink"
            }`}
          >
            <IconBuilding2 className="size-4" fill="currentColor" />
            Pessoa Jurídica (PJ)
          </button>
        </div>

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

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field
            label={tipo === "PF" ? "CPF" : "CNPJ"}
            id="cliente-documento"
            hint="Opcional no primeiro contato"
          >
            <Input
              id="cliente-documento"
              placeholder={tipo === "PF" ? "000.000.000-00" : "00.000.000/0001-00"}
              value={form.documento}
              inputMode="numeric"
              autoComplete="off"
              onChange={(e) => handleChange("documento", formatarDocumento(e.target.value, tipo === "PF"))}
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
              inputMode="numeric"
              autoComplete="tel"
              maxLength={15}
              onChange={(e) => handleChange("telefone", formatarTelefone(e.target.value))}
              disabled={salvando}
            />
          </Field>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
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
