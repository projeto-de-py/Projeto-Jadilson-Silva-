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
  ETAPA_PARA_STATUS_PROCESSO,
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

function digitosDoCnj(valor) {
  return String(valor || "").replace(/\D/g, "");
}

// Mesmo módulo 97 do backend (`app/core/validacao.py`). BigInt é obrigatório:
// 20 dígitos ultrapassam a precisão inteira de `Number` no JavaScript.
function cnjEhValido(valor) {
  const digitos = digitosDoCnj(valor);
  if (digitos.length !== 20 || /^(\d)\1{19}$/.test(digitos)) return false;
  let resto = 0n;
  for (const digito of digitos) resto = (resto * 10n + BigInt(digito)) % 97n;
  return resto === 1n;
}

function formatarCnj(valor) {
  const digitos = digitosDoCnj(valor);
  if (digitos.length !== 20) return String(valor || "").trim();
  return `${digitos.slice(0, 7)}-${digitos.slice(7, 9)}.${digitos.slice(9, 13)}.${digitos.slice(13, 14)}.${digitos.slice(14, 16)}.${digitos.slice(16, 20)}`;
}

function formatarValorCausa(valor) {
  const digitos = valor.replace(/\D/g, "").slice(0, 15);
  if (!digitos) return "";
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(Number(digitos) / 100);
}

// A máscara de valor guarda centavos; a API espera Decimal (reais).
function valorDaCausa(valor) {
  const digitos = digitosDoCnj(valor).slice(0, 15);
  if (!digitos) return null;
  const reais = Number(digitos) / 100;
  return reais > 0 ? reais : null;
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
    const digitos = digitosDoCnj(form.numeroProcesso);
    if (!digitos) {
      novosErros.numeroProcesso = "Informe o número do processo (CNJ).";
    } else if (!cnjEhValido(digitos)) {
      novosErros.numeroProcesso =
        digitos.length !== 20
          ? "O CNJ deve ter 20 dígitos (formato 0000000-00.0000.0.00.0000)."
          : "CNJ inválido: os dígitos verificadores não conferem.";
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
      const digitos = digitosDoCnj(form.numeroProcesso);
      const numeroFormatado = formatarCnj(digitos);

      // Unicidade conferida ANTES de criar o Caso: sem isso um CNJ duplicado
      // deixaria um Caso órfão (a API não tem DELETE de caso, só arquivar).
      try {
        const consulta = await apiJson(`processos?q=${digitos}&limite=1`);
        if (Number(consulta?.total) > 0) {
          setErros((prev) => ({
            ...prev,
            numeroProcesso: "Já existe um processo com este número CNJ.",
          }));
          setSalvando(false);
          return;
        }
      } catch {
        // Consulta de unicidade é best-effort; o POST valida novamente no banco.
      }

      const clienteId = await resolverClienteId(form.cliente);

      // O Caso continua sendo a unidade que alimenta a listagem de Processos
      // do dashboard; guardamos o CNJ formatado nele para exibição.
      const criado = await apiJson("casos", {
        method: "POST",
        csrf,
        body: {
          titulo: form.tipoAcao,
          cliente_id: clienteId,
          numero_processo: numeroFormatado,
          area: extrairAreaCodigo(form.tipoAcao),
          tipo_demanda: "JUDICIAL",
          status: ETAPA_PARA_STATUS_API[form.status] || "NOVO",
          vara: form.vara,
          observacoes: form.valorCausa.trim() || null,
          descricao: form.descricao.trim() || null,
        },
      });

      // Processo judicial REAL (antes o CNJ era só texto do Caso e nunca
      // virava registro em `processos_judiciais`).
      const codigoTribunal = digitos.slice(14, 16);
      const processo = await apiJson(`casos/${criado.id}/processos`, {
        method: "POST",
        csrf,
        body: {
          numero_processo: digitos,
          tribunal: codigoTribunal ? `Tribunal ${codigoTribunal}` : null,
          orgao_julgador: form.vara,
          instancia: "PRIMEIRA_INSTANCIA",
          assunto: form.tipoAcao,
          status: ETAPA_PARA_STATUS_PROCESSO[form.status] || "DISTRIBUIDO",
          valor_causa: valorDaCausa(form.valorCausa),
          observacoes: form.descricao.trim() || null,
        },
      });

      if (form.prazoTitulo.trim() && form.prazoData) {
        try {
          await apiJson("prazos", {
            method: "POST",
            csrf,
            body: {
              caso_id: criado.id,
              processo_id: processo.id,
              titulo: form.prazoTitulo.trim(),
              // Contrato de PrazoCreate: `data_vencimento` (nao ha `data_limite`
              // nem tipo AUDIENCIA - ambos respondem 422 com extra="forbid").
              data_vencimento: form.prazoData,
              tipo: form.prazoTipo,
            },
          });
        } catch (falha) {
          // O caso e o processo já foram salvos; avisa que o prazo opcional falhou
          // (antes o `.catch(() => {})` engolia o erro e o usuario via
          // "Processo salvo" mesmo sem o prazo criado).
          toast({
            tipo: "erro",
            titulo: "Processo salvo, mas o prazo não foi criado",
            descricao:
              falha.message ||
              "Não foi possível criar o prazo vinculado. Cadastre-o manualmente na tela de Prazos.",
          });
        }
      }

      const novoProcesso = {
        ...mapearCasoApi(criado),
        numero: processo.numero_formatado || numeroFormatado,
        processoJudicialId: processo.id,
        statusProcesso: processo.status,
      };

      if (onProcessoSalvo) {
        onProcessoSalvo(novoProcesso);
      }

      notificarAtualizacaoDados();
      window.dispatchEvent(new CustomEvent("notificacoes:atualizar"));

      toast({
        tipo: "sucesso",
        titulo: "Processo salvo no banco de dados",
        descricao: `CNJ ${novoProcesso.numero} cadastrado e vinculado ao caso.`,
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
      // 422 de CNJ/duplicidade volta com a mensagem do servidor: devolve o
      // detalhe para o campo em vez de só mostrar um toast genérico.
      if (erro.status === 422 && /cnj|numero_processo/i.test(erro.message || "")) {
        setErros((prev) => ({ ...prev, numeroProcesso: erro.message }));
      }
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
            <IconFolderBadgePlus className="size-4" fill="currentColor" />
            Cadastrar Processo
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
            <Field label="Data de vencimento" id="proc-prazo-data">
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
                <option value="ADMINISTRATIVO">Administrativo</option>
                <option value="CONTRATUAL">Contratual</option>
                <option value="INTERNO">Interno</option>
                <option value="OUTRO">Outro</option>
              </Select>
            </Field>
          </div>
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
