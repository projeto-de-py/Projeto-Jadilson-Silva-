import { useState } from "react";
import { IconFolderBadgePlus } from "symbols-react";
import {
  Modal,
  Button,
  Input,
  Select,
  Textarea,
  Field,
  useToast,
} from "@/components/ui";

const TIPOS_ACAO = [
  "Bancário - Revisional de Contrato",
  "Bancário - Execução de Contrato",
  "Previdenciário - Concessão de Benefício",
  "Previdenciário - Benefício por Incapacidade",
  "Previdenciário - Revisão de Aposentadoria",
  "Consumidor - Reparação de Danos",
  "Consumidor - Prática Abusiva",
  "Outro",
];

const VARAS_COMUNS = [
  "1ª Vara Cível",
  "2ª Vara Cível",
  "Vara Cível Empresarial",
  "Vara Federal Previdenciária",
  "Juizado Especial Federal",
  "Juizado Especial Cível",
  "Vara da Fazenda Pública",
];

export function ModalCadastrarProcesso({ open, onOpenChange, onProcessoSalvo }) {
  const { toast } = useToast();
  const [salvando, setSalvando] = useState(false);
  const [form, setForm] = useState({
    numeroProcesso: "",
    cliente: "",
    tipoAcao: TIPOS_ACAO[0],
    vara: VARAS_COMUNS[0],
    status: "Petição inicial",
    valorCausa: "",
    descricao: "",
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
    if (!form.numeroProcesso.trim()) {
      novosErros.numeroProcesso = "Informe o número do processo (CNJ).";
    }
    if (!form.cliente.trim()) {
      novosErros.cliente = "Informe o nome do cliente vinculado.";
    }
    setErros(novosErros);
    return Object.keys(novosErros).length === 0;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!validar()) return;

    setSalvando(true);
    try {
      const novoProcesso = {
        id: Date.now(),
        numero: form.numeroProcesso.trim(),
        cliente: form.cliente.trim(),
        tipoAcao: form.tipoAcao,
        vara: form.vara,
        status: form.status,
        valorCausa: form.valorCausa.trim() || "A definir",
        descricao: form.descricao.trim(),
        criadoEm: new Date().toLocaleDateString("pt-BR"),
      };

      if (onProcessoSalvo) {
        onProcessoSalvo(novoProcesso);
      }

      toast({
        tipo: "sucesso",
        titulo: "Processo cadastrado com sucesso!",
        descricao: `O processo ${novoProcesso.numero} foi adicionado à carteira.`,
      });

      setForm({
        numeroProcesso: "",
        cliente: "",
        tipoAcao: TIPOS_ACAO[0],
        vara: VARAS_COMUNS[0],
        status: "Petição inicial",
        valorCausa: "",
        descricao: "",
      });
      onOpenChange(false);
    } catch {
      toast({
        tipo: "erro",
        titulo: "Erro ao cadastrar processo",
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
      titulo="Novo Processo"
      descricao="Cadastre uma nova ação judicial ou procedimento para acompanhamento de prazos."
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
            form="form-cadastrar-processo"
            loading={salvando}
          >
            <IconFolderBadgePlus className="size-4" fill="currentColor" />
            Cadastrar Processo
          </Button>
        </>
      }
    >
      <form
        id="form-cadastrar-processo"
        onSubmit={handleSubmit}
        className="space-y-4 pt-2"
      >
        {/* Número do Processo (CNJ) */}
        <Field
          label="Número do Processo (CNJ)"
          id="proc-numero"
          hint="Formato: 0000000-00.0000.0.00.0000"
          error={erros.numeroProcesso}
        >
          <Input
            id="proc-numero"
            placeholder="0000042-30.2026.8.00.0100"
            value={form.numeroProcesso}
            onChange={(e) => handleChange("numeroProcesso", e.target.value)}
            disabled={salvando}
            autoFocus
          />
        </Field>

        {/* Cliente e Valor da Causa */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field
            label="Cliente / Parte"
            id="proc-cliente"
            error={erros.cliente}
          >
            <Input
              id="proc-cliente"
              placeholder="Nome do cliente"
              value={form.cliente}
              onChange={(e) => handleChange("cliente", e.target.value)}
              disabled={salvando}
            />
          </Field>

          <Field label="Valor da Causa" id="proc-valor" hint="Opcional">
            <Input
              id="proc-valor"
              placeholder="R$ 50.000,00"
              value={form.valorCausa}
              onChange={(e) => handleChange("valorCausa", e.target.value)}
              disabled={salvando}
            />
          </Field>
        </div>

        {/* Tipo de Ação e Vara */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Área / Tipo de Ação" id="proc-tipo">
            <Select
              id="proc-tipo"
              value={form.tipoAcao}
              onChange={(e) => handleChange("tipoAcao", e.target.value)}
              disabled={salvando}
            >
              {TIPOS_ACAO.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </Select>
          </Field>

          <Field label="Vara / Foro" id="proc-vara">
            <Select
              id="proc-vara"
              value={form.vara}
              onChange={(e) => handleChange("vara", e.target.value)}
              disabled={salvando}
            >
              {VARAS_COMUNS.map((v) => (
                <option key={v} value={v}>
                  {v}
                </option>
              ))}
            </Select>
          </Field>
        </div>

        {/* Estágio Inicial */}
        <Field label="Estágio do Processo" id="proc-status">
          <Select
            id="proc-status"
            value={form.status}
            onChange={(e) => handleChange("status", e.target.value)}
            disabled={salvando}
          >
            <option value="Petição inicial">Petição inicial (36%)</option>
            <option value="Instrução">Instrução processual (31%)</option>
            <option value="Sentença">Aguardando sentença (19%)</option>
            <option value="Recursal">Fase recursal (14%)</option>
            <option value="Execução">Cumprimento de sentença</option>
            <option value="Concluído">Concluído / Arquivado</option>
          </Select>
        </Field>

        {/* Resumo dos Fatos */}
        <Field
          label="Objeto da Ação / Descrição Sumária"
          id="proc-desc"
          hint="Breve contextualização para a equipe e para geração de minutas"
        >
          <Textarea
            id="proc-desc"
            placeholder="Resumo dos fatos, pedidos principais e observações relevantes..."
            value={form.descricao}
            onChange={(e) => handleChange("descricao", e.target.value)}
            disabled={salvando}
            rows={3}
          />
        </Field>
      </form>
    </Modal>
  );
}
