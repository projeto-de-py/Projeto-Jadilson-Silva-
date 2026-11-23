import { useEffect, useState } from "react";
import { IconFolderBadgePlus } from "symbols-react";
import {
  Modal,
  Button,
  Input,
  Select,
  Textarea,
  Field,
  Dropdown,
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

const FORM_VAZIO = {
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
};

function formDoProcesso(processo) {
  if (!processo) return FORM_VAZIO;
  return {
    ...FORM_VAZIO,
    numeroProcesso: processo.numero.startsWith("CASO-") ? "" : processo.numero,
    cliente: processo.cliente,
    tipoAcao: processo.tipoAcao,
    vara: processo.vara,
    status: processo.status,
    valorCausa: processo.valorCausa === "A definir" ? "" : processo.valorCausa,
    descricao: processo.descricao,
  };
}

const comAtual = (opcoes, atual) => (opcoes.includes(atual) ? opcoes : [atual, ...opcoes]);

/**
 * Cadastra um processo novo ou, com `processo`, edita o existente (o formulário abre preenchido
 * e só os campos alterados vão ao servidor). Para editar, monte o modal só enquanto ele estiver
 * aberto (`key` = id do processo): o formulário nasce com os dados do processo escolhido.
 */
export function ModalCadastrarProcesso({ open, onOpenChange, onProcessoSalvo, processo = null }) {
  const { csrf } = useSessao();
  const { toast } = useToast();
  const editando = Boolean(processo);
  const [salvando, setSalvando] = useState(false);
  const [clientesExistentes, setClientesExistentes] = useState([]);
  const [form, setForm] = useState(() => formDoProcesso(processo));
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

  async function salvarEdicao() {
    const inicial = formDoProcesso(processo);
    const mudou = (campo) => form[campo] !== inicial[campo];
    const corpo = {};
    if (mudou("cliente")) corpo.cliente_id = await resolverClienteId(form.cliente);
    if (mudou("numeroProcesso")) corpo.numero_processo = form.numeroProcesso.trim() || null;
    if (mudou("tipoAcao")) {
      corpo.titulo = form.tipoAcao;
      corpo.area = extrairAreaCodigo(form.tipoAcao);
    }
    if (mudou("status")) corpo.status = ETAPA_PARA_STATUS_API[form.status] || "NOVO";
    if (mudou("vara")) corpo.vara = form.vara;
    if (mudou("valorCausa")) corpo.observacoes = form.valorCausa.trim() || null;
    if (mudou("descricao")) corpo.descricao = form.descricao.trim() || null;

    if (Object.keys(corpo).length === 0) {
      onOpenChange(false);
      return;
    }
    const atualizado = mapearCasoApi(await apiJson(`casos/${processo.id}`, { method: "PATCH", csrf, body: corpo }));
    onProcessoSalvo?.(atualizado);
    notificarAtualizacaoDados();
    toast({ tipo: "sucesso", titulo: "Processo atualizado", descricao: `As alterações em ${atualizado.numero} foram salvas.` });
    onOpenChange(false);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!validar()) return;

    setSalvando(true);
    try {
      if (editando) {
        await salvarEdicao();
        return;
      }
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

      let erroPrazo = null;
      if (form.prazoTitulo.trim() && form.prazoData) {
        try {
          await apiJson("prazos", {
            method: "POST",
            csrf,
            body: {
              caso_id: criado.id,
              titulo: form.prazoTitulo.trim(),
              data_limite: form.prazoData,
              tipo: form.prazoTipo,
            },
          });
        } catch (falha) {
          erroPrazo = falha;
        }
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
      if (erroPrazo) {
        toast({
          tipo: "erro",
          titulo: "O processo foi salvo, mas o prazo não",
          descricao: erroPrazo.message || "Cadastre o prazo novamente na tela de Prazos.",
        });
      }

      setForm(FORM_VAZIO);
      onOpenChange(false);
    } catch (erro) {
      toast({
        tipo: "erro",
        titulo: editando ? "Erro ao salvar o processo" : "Erro ao cadastrar processo",
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
      titulo={editando ? "Editar processo" : "Novo Processo"}
      descricao={editando ? "Altere os dados do processo. Só o que mudar é salvo." : "Cadastre uma nova ação judicial ou procedimento no banco de dados para acompanhamento."}
      className="max-w-2xl"
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
            {!editando && <IconFolderBadgePlus className="size-4" fill="currentColor" />}
            {editando ? "Salvar alterações" : "Cadastrar Processo"}
          </Button>
        </>
      }
    >
      <form
        id="form-cadastrar-processo"
        onSubmit={handleSubmit}
        className="space-y-5 pt-2"
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
            <Dropdown
              id="proc-cliente"
              searchable
              allowCustom
              placeholder="Selecione ou digite o nome"
              options={clientesExistentes.map((c) => ({
                value: c.nome,
                label: c.nome,
                description: c.documento || c.email || undefined,
              }))}
              value={form.cliente}
              onChange={(val) => handleChange("cliente", val)}
              disabled={salvando}
              error={!!erros.cliente}
            />
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
              {comAtual(TIPOS_ACAO, form.tipoAcao).map((t) => (
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
              {comAtual(VARAS_COMUNS, form.vara).map((v) => (
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

        {!editando && (
          <div className="rounded-card border border-border bg-surface-muted/30 p-4 sm:p-5 space-y-4">
            <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
              <span className="text-13 font-semibold text-ink">
                Primeiro prazo (opcional)
              </span>
              <span className="text-12 text-ink-muted">
                Cria automaticamente um alerta na Central de Prazos
              </span>
            </div>

            <Field label="Título do prazo" id="proc-prazo-titulo">
              <Input
                id="proc-prazo-titulo"
                placeholder="Ex.: Contestação, Réplica, Audiência..."
                value={form.prazoTitulo}
                onChange={(e) => handleChange("prazoTitulo", e.target.value)}
                disabled={salvando}
              />
            </Field>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Field label="Data limite" id="proc-prazo-data">
                <Input
                  id="proc-prazo-data"
                  type="date"
                  value={form.prazoData}
                  onChange={(e) => handleChange("prazoData", e.target.value)}
                  disabled={salvando}
                />
              </Field>

              <Field label="Tipo de prazo" id="proc-prazo-tipo">
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
          </div>
        )}

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
