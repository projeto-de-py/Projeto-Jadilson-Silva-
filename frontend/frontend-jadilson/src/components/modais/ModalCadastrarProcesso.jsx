import { useEffect, useState } from "react";
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
import { useSessao } from "@/context/sessao";
import { apiJson } from "@/lib/api";
import {
  ETAPA_PARA_STATUS_API,
  extrairAreaCodigo,
  mapearCasoApi,
  notificarAtualizacaoDados,
} from "@/data/escritorio";

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

function formatarNumeroProcesso(valor) {
  const digitos = valor.replace(/\D/g, "").slice(0, 20);
  const numero = digitos.slice(0, 7);
  const digito = digitos.slice(7, 9);
  const ano = digitos.slice(9, 13);
  const ramo = digitos.slice(13, 14);
  const tribunal = digitos.slice(14, 16);
  const origem = digitos.slice(16, 20);

  return `${numero}${digitos.length > 7 ? `-${digito}` : ""}${digitos.length > 9 ? `.${ano}` : ""}${digitos.length > 13 ? `.${ramo}` : ""}${digitos.length > 14 ? `.${tribunal}` : ""}${digitos.length > 16 ? `.${origem}` : ""}`;
}

function formatarValorCausa(valor) {
  const digitos = valor.replace(/\D/g, "").slice(0, 15);
  if (!digitos) return "";
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(Number(digitos) / 100);
}

export function ModalCadastrarProcesso({ open, onOpenChange, onProcessoSalvo }) {
  const { csrf } = useSessao();
  const { toast } = useToast();
  const [salvando, setSalvando] = useState(false);
  const [clientesExistentes, setClientesExistentes] = useState([]);
  const [form, setForm] = useState({
    numeroProcesso: "",
    cliente: "",
    tipoAcao: TIPOS_ACAO[0],
    vara: VARAS_COMUNS[0],
    status: "Petição inicial",
    valorCausa: "",
    descricao: "",
    prazoTitulo: "",
    prazoData: "",
    prazoTipo: "PROCESSUAL",
  });
  const [erros, setErros] = useState({});

  useEffect(() => {
    if (!open) return;
    apiJson("clientes?pagina=1&limite=100")
      .then((res) => {
        const itens = Array.isArray(res?.itens)
          ? res.itens
          : Array.isArray(res)
            ? res
            : [];
        setClientesExistentes(itens);
      })
      .catch(() => setClientesExistentes([]));
  }, [open]);

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

  async function resolverClienteId(nomeCliente) {
    const limpo = nomeCliente.trim().toLowerCase();
    const existente = clientesExistentes.find(
      (c) => c.nome?.trim().toLowerCase() === limpo,
    );
    if (existente) return existente.id;

    const novoCli = await apiJson("clientes", {
      method: "POST",
      csrf,
      body: { nome: nomeCliente.trim() },
    });
    return novoCli.id;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!validar()) return;

    setSalvando(true);
    try {
      const clienteId = await resolverClienteId(form.cliente);

      const criado = await apiJson("casos", {
        method: "POST",
        csrf,
        body: {
          titulo: form.tipoAcao,
          cliente_id: clienteId,
          numero_processo: form.numeroProcesso.trim() || null,
          area: extrairAreaCodigo(form.tipoAcao),
          tipo_demanda: "JUDICIAL",
          status: ETAPA_PARA_STATUS_API[form.status] || "NOVO",
          vara: form.vara,
          observacoes: form.valorCausa.trim() || null,
          descricao: form.descricao.trim() || null,
        },
      });

      if (form.prazoTitulo.trim() && form.prazoData) {
        await apiJson("prazos", {
          method: "POST",
          csrf,
          body: {
            caso_id: criado.id,
            titulo: form.prazoTitulo.trim(),
            data_limite: form.prazoData,
            tipo: form.prazoTipo,
          },
        }).catch(() => {});
      }

      const novoProcesso = mapearCasoApi(criado);

      if (onProcessoSalvo) {
        onProcessoSalvo(novoProcesso);
      }

      notificarAtualizacaoDados();
      window.dispatchEvent(new CustomEvent("notificacoes:atualizar"));

      toast({
        tipo: "sucesso",
        titulo: "Processo salvo no banco de dados",
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
        prazoTitulo: "",
        prazoData: "",
        prazoTipo: "PROCESSUAL",
      });
      onOpenChange(false);
    } catch (erro) {
      toast({
        tipo: "erro",
        titulo: "Erro ao cadastrar processo",
        descricao: erro.message || "Verifique os dados informados e tente novamente.",
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
      descricao="Cadastre uma nova ação judicial ou procedimento no banco de dados para acompanhamento."
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
            inputMode="numeric"
            autoComplete="off"
            maxLength={25}
            onChange={(e) => handleChange("numeroProcesso", formatarNumeroProcesso(e.target.value))}
            disabled={salvando}
            autoFocus
          />
        </Field>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field
            label="Cliente / Parte"
            id="proc-cliente"
            error={erros.cliente}
          >
            <Input
              id="proc-cliente"
              list="lista-clientes-cadastrados"
              placeholder="Selecione ou digite o nome"
              value={form.cliente}
              onChange={(e) => handleChange("cliente", e.target.value)}
              disabled={salvando}
            />
            <datalist id="lista-clientes-cadastrados">
              {clientesExistentes.map((c) => (
                <option key={c.id} value={c.nome} />
              ))}
            </datalist>
          </Field>

          <Field label="Valor da Causa" id="proc-valor" hint="Opcional">
            <Input
              id="proc-valor"
              placeholder="R$ 50.000,00"
              value={form.valorCausa}
              inputMode="numeric"
              onChange={(e) => handleChange("valorCausa", formatarValorCausa(e.target.value))}
              disabled={salvando}
            />
          </Field>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
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

        <Field label="Estágio do Processo" id="proc-status">
          <Select
            id="proc-status"
            value={form.status}
            onChange={(e) => handleChange("status", e.target.value)}
            disabled={salvando}
          >
            <option value="Petição inicial">Petição inicial</option>
            <option value="Instrução">Instrução processual</option>
            <option value="Sentença">Aguardando sentença</option>
            <option value="Recursal">Fase recursal</option>
            <option value="Execução">Cumprimento de sentença</option>
            <option value="Concluído">Concluído / Arquivado</option>
          </Select>
        </Field>

        <div className="grid grid-cols-1 gap-4 rounded-input border border-border bg-surface-muted/40 p-3.5 sm:grid-cols-3">
          <Field label="Primeiro prazo (opcional)" id="proc-prazo-titulo">
            <Input
              id="proc-prazo-titulo"
              placeholder="Ex.: Contestação"
              value={form.prazoTitulo}
              onChange={(e) => handleChange("prazoTitulo", e.target.value)}
              disabled={salvando}
            />
          </Field>
          <Field label="Data limite" id="proc-prazo-data">
            <Input
              id="proc-prazo-data"
              type="date"
              value={form.prazoData}
              onChange={(e) => handleChange("prazoData", e.target.value)}
              disabled={salvando}
            />
          </Field>
          <Field label="Tipo" id="proc-prazo-tipo">
            <Select
              id="proc-prazo-tipo"
              value={form.prazoTipo}
              onChange={(e) => handleChange("prazoTipo", e.target.value)}
              disabled={salvando}
            >
              <option value="PROCESSUAL">Prazo processual</option>
              <option value="AUDIENCIA">Audiência</option>
            </Select>
          </Field>
        </div>

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
