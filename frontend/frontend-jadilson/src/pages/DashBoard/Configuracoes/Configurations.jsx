import { useEffect, useState } from "react";
import {
  IconBuildingColumns,
  IconScalemass,
  IconBell,
  IconLock,
  IconCheckmark,
  IconTrash,
} from "symbols-react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Button,
  Input,
  Textarea,
  Field,
  Switch,
  Tabs,
  useToast,
} from "@/components/ui";
import { useSessao } from "@/context/sessao";
import { apiJson } from "@/lib/api";

const AREAS_ATUACAO = [
  {
    id: "bancario",
    campoApi: "area_bancario",
    titulo: "Direito Bancário",
    descricao: "Revisão de contratos, juros abusivos e execuções bancárias.",
  },
  {
    id: "previdenciario",
    campoApi: "area_previdenciario",
    titulo: "Direito Previdenciário",
    descricao: "Aposentadorias, benefícios por incapacidade e revisões junto ao INSS.",
  },
  {
    id: "consumidor",
    campoApi: "area_consumidor",
    titulo: "Direito do Consumidor",
    descricao: "Negativação indevida, práticas abusivas e reparação de danos.",
  },
];

function PainelEscritorio() {
  const { csrf } = useSessao();
  const { toast } = useToast();
  const [salvando, setSalvando] = useState(false);
  const [form, setForm] = useState({
    nome: "Jadilson Silva Advocacia",
    oab: "OAB/AL 00.000",
    email: "contato@jadilsonsilva.adv.br",
    telefone: "(82) 3221-0000",
    endereco: "Paulo Afonso/BA",
    assinatura: "Atenciosamente,\nJadilson Silva Advocacia\nOAB/AL 00.000",
  });

  useEffect(() => {
    apiJson("auth/escritorio")
      .then((dados) => {
        if (!dados) return;
        setForm({
          nome: dados.nome ?? "Jadilson Silva Advocacia",
          oab: dados.oab ?? "OAB/AL 00.000",
          email: dados.email ?? "contato@jadilsonsilva.adv.br",
          telefone: dados.telefone ?? "(82) 3221-0000",
          endereco: dados.endereco ?? "Paulo Afonso/BA",
          assinatura:
            dados.assinatura ??
            "Atenciosamente,\nJadilson Silva Advocacia\nOAB/AL 00.000",
        });
      })
      .catch(() => {});
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setSalvando(true);
    try {
      await apiJson("auth/escritorio", {
        method: "PUT",
        csrf,
        body: form,
      });
      toast({
        tipo: "sucesso",
        titulo: "Dados do escritório salvos no banco de dados",
      });
    } catch (erro) {
      toast({
        tipo: "erro",
        titulo: "Falha ao salvar dados do escritório",
        descricao: erro.message || "Tente novamente em instantes.",
      });
    } finally {
      setSalvando(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="space-y-1">
          <CardTitle className="flex items-center gap-2 text-18">
            <IconBuildingColumns className="size-5 text-accent" fill="currentColor" />
            Dados do Escritório
          </CardTitle>
          <CardDescription>Informações exibidas em relatórios e minutas geradas.</CardDescription>
        </div>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Nome do Escritório" id="cfg-nome">
              <Input
                id="cfg-nome"
                value={form.nome}
                onChange={(e) => setForm((p) => ({ ...p, nome: e.target.value }))}
              />
            </Field>
            <Field label="OAB Responsável" id="cfg-oab">
              <Input
                id="cfg-oab"
                value={form.oab}
                onChange={(e) => setForm((p) => ({ ...p, oab: e.target.value }))}
              />
            </Field>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="E-mail de Contato" id="cfg-email">
              <Input
                id="cfg-email"
                type="email"
                value={form.email}
                onChange={(e) => setForm((p) => ({ ...p, email: e.target.value }))}
              />
            </Field>
            <Field label="Telefone / WhatsApp" id="cfg-telefone">
              <Input
                id="cfg-telefone"
                value={form.telefone}
                onChange={(e) => setForm((p) => ({ ...p, telefone: e.target.value }))}
              />
            </Field>
          </div>

          <Field label="Endereço" id="cfg-endereco">
            <Input
              id="cfg-endereco"
              value={form.endereco}
              onChange={(e) => setForm((p) => ({ ...p, endereco: e.target.value }))}
            />
          </Field>

          <Field
            label="Assinatura padrão em documentos"
            id="cfg-assinatura"
            hint="Usada ao final de minutas e relatórios gerados pelo Redator IA"
          >
            <Textarea
              id="cfg-assinatura"
              rows={3}
              value={form.assinatura}
              onChange={(e) => setForm((p) => ({ ...p, assinatura: e.target.value }))}
            />
          </Field>

          <div className="flex justify-end pt-2">
            <Button variant="primary" type="submit" loading={salvando} className="gap-2">
              <IconCheckmark className="size-4" fill="currentColor" />
              Salvar alterações
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function PainelAreas() {
  const { csrf } = useSessao();
  const { toast } = useToast();
  const [ativas, setAtivas] = useState({ bancario: true, previdenciario: true, consumidor: true });

  useEffect(() => {
    apiJson("auth/escritorio")
      .then((dados) => {
        if (!dados) return;
        setAtivas({
          bancario: dados.area_bancario ?? true,
          previdenciario: dados.area_previdenciario ?? true,
          consumidor: dados.area_consumidor ?? true,
        });
      })
      .catch(() => {});
  }, []);

  async function alternar(id) {
    const areaObj = AREAS_ATUACAO.find((a) => a.id === id);
    if (!areaObj) return;
    const novoValor = !ativas[id];
    setAtivas((prev) => ({ ...prev, [id]: novoValor }));

    try {
      await apiJson("auth/escritorio", {
        method: "PUT",
        csrf,
        body: { [areaObj.campoApi]: novoValor },
      });
      toast({
        tipo: "info",
        titulo: novoValor ? "Área ativada" : "Área desativada",
        descricao: areaObj.titulo,
      });
    } catch {
      setAtivas((prev) => ({ ...prev, [id]: !novoValor }));
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="space-y-1">
          <CardTitle className="flex items-center gap-2 text-18">
            <IconScalemass className="size-5 text-accent" fill="currentColor" />
            Áreas de Atuação
          </CardTitle>
          <CardDescription>
            Defina as especialidades do escritório — usadas para sugerir tipos de ação e minutas.
          </CardDescription>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {AREAS_ATUACAO.map((area) => (
          <div
            key={area.id}
            className="border-border bg-surface-muted/40 flex items-center justify-between gap-4 rounded-input border p-4"
          >
            <div>
              <p className="text-14 font-semibold text-ink">{area.titulo}</p>
              <p className="text-13 text-ink-muted">{area.descricao}</p>
            </div>
            <Switch
              checked={ativas[area.id]}
              onCheckedChange={() => alternar(area.id)}
              aria-label={`Ativar ${area.titulo}`}
            />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

const PREFERENCIAS_PADRAO = [
  { id: "prazoHoje", titulo: "Prazos que vencem hoje", descricao: "Alerta diário sobre prazos fatais do dia.", ativo: true },
  { id: "prazo3dias", titulo: "Prazos nos próximos 3 dias", descricao: "Resumo com prazos que se aproximam.", ativo: true },
  { id: "audiencias", titulo: "Audiências agendadas", descricao: "Lembrete 24h antes de cada audiência.", ativo: true },
  { id: "novosClientes", titulo: "Novos clientes cadastrados", descricao: "Notificação quando um cliente é adicionado.", ativo: false },
  { id: "relatorioSemanal", titulo: "Relatório semanal por e-mail", descricao: "Resumo da carteira enviado toda sexta-feira.", ativo: false },
];

const STORAGE_PREFS_KEY = "preferencias_notificacoes";

function carregarPreferenciasNotificacoes() {
  try {
    const salvo = JSON.parse(localStorage.getItem(STORAGE_PREFS_KEY) || "null");
    if (!salvo || typeof salvo !== "object") return PREFERENCIAS_PADRAO;
    return PREFERENCIAS_PADRAO.map((item) => ({
      ...item,
      ativo: typeof salvo[item.id] === "boolean" ? salvo[item.id] : item.ativo,
    }));
  } catch {
    return PREFERENCIAS_PADRAO;
  }
}

function PainelNotificacoes() {
  const { csrf } = useSessao();
  const { toast } = useToast();
  const [preferencias, setPreferencias] = useState(carregarPreferenciasNotificacoes);
  const [testandoId, setTestandoId] = useState(null);
  const [limpando, setLimpando] = useState(false);

  function alternar(id) {
    setPreferencias((prev) => {
      const proximo = prev.map((p) => (p.id === id ? { ...p, ativo: !p.ativo } : p));
      try {
        const mapa = Object.fromEntries(proximo.map((p) => [p.id, p.ativo]));
        localStorage.setItem(STORAGE_PREFS_KEY, JSON.stringify(mapa));
      } catch {
        /* sem persistência local */
      }
      return proximo;
    });
  }

  async function dispararTeste(idEspecifico = null) {
    const tipos = idEspecifico
      ? [idEspecifico]
      : preferencias.filter((p) => p.ativo).map((p) => p.id);

    if (tipos.length === 0) {
      toast({
        tipo: "info",
        titulo: "Nenhuma notificação ativa",
        descricao: "Ative pelo menos uma opção ou teste um item individualmente.",
      });
      return;
    }

    setTestandoId(idEspecifico || "todas");
    try {
      await apiJson("notificacoes/testar", {
        method: "POST",
        csrf,
        body: { tipos },
      });
      window.dispatchEvent(new CustomEvent("notificacoes:atualizar"));
    } catch (erro) {
      toast({
        tipo: "erro",
        titulo: "Falha ao testar notificação",
        descricao: erro.message || "Não foi possível criar a notificação de teste.",
      });
    } finally {
      setTestandoId(null);
    }
  }

  async function limparNotificacoes() {
    setLimpando(true);
    try {
      const res = await apiJson("notificacoes/limpar", {
        method: "POST",
        csrf,
        body: {},
      });
      window.dispatchEvent(new CustomEvent("notificacoes:atualizar"));
      toast({
        tipo: "sucesso",
        titulo: "Notificações limpas",
        descricao:
          res?.removidas > 0
            ? `${res.removidas} notificação(ões) removida(s) do painel.`
            : "O painel já estava sem notificações.",
      });
    } catch (erro) {
      toast({
        tipo: "erro",
        titulo: "Falha ao limpar notificações",
        descricao: erro.message || "Não foi possível limpar as notificações.",
      });
    } finally {
      setLimpando(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2 text-18">
              <IconBell className="size-5 text-accent" fill="currentColor" />
              Notificações
            </CardTitle>
            <CardDescription>Escolha o que deve gerar alertas no painel e por e-mail.</CardDescription>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              loading={limpando}
              onClick={limparNotificacoes}
              className="gap-2"
            >
              <IconTrash className="size-4" fill="currentColor" />
              Limpar notificações
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              loading={testandoId === "todas"}
              onClick={() => dispararTeste(null)}
              className="gap-2"
            >
              <IconBell className="size-4" fill="currentColor" />
              Testar notificações ativas
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {preferencias.map((pref) => (
          <div
            key={pref.id}
            className="border-border bg-surface-muted/40 flex items-center justify-between gap-4 rounded-input border p-4"
          >
            <div>
              <p className="text-14 font-semibold text-ink">{pref.titulo}</p>
              <p className="text-13 text-ink-muted">{pref.descricao}</p>
            </div>
            <div className="flex items-center gap-3">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                loading={testandoId === pref.id}
                onClick={() => dispararTeste(pref.id)}
                aria-label={`Testar notificação: ${pref.titulo}`}
              >
                Testar
              </Button>
              <Switch
                checked={pref.ativo}
                onCheckedChange={() => alternar(pref.id)}
                aria-label={`Ativar ${pref.titulo}`}
              />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function PainelSeguranca() {
  const { csrf } = useSessao();
  const { toast } = useToast();
  const [salvando, setSalvando] = useState(false);
  const [senhaAtual, setSenhaAtual] = useState("");
  const [novaSenha, setNovaSenha] = useState("");
  const [confirmarSenha, setConfirmarSenha] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    if (novaSenha.length < 8) {
      toast({
        tipo: "erro",
        titulo: "Nova senha muito curta",
        descricao: "A nova senha deve ter no mínimo 8 caracteres.",
      });
      return;
    }
    if (novaSenha !== confirmarSenha) {
      toast({
        tipo: "erro",
        titulo: "Confirmação divergente",
        descricao: "A confirmação da nova senha não coincide.",
      });
      return;
    }

    setSalvando(true);
    try {
      await apiJson("auth/senha", {
        method: "POST",
        csrf,
        body: {
          senha_atual: senhaAtual,
          nova_senha: novaSenha,
        },
      });
      setSenhaAtual("");
      setNovaSenha("");
      setConfirmarSenha("");
      toast({
        tipo: "sucesso",
        titulo: "Senha atualizada no banco de dados",
      });
    } catch (erro) {
      toast({
        tipo: "erro",
        titulo: "Não foi possível alterar a senha",
        descricao: erro.message || "Verifique sua senha atual e tente novamente.",
      });
    } finally {
      setSalvando(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="space-y-1">
          <CardTitle className="flex items-center gap-2 text-18">
            <IconLock className="size-5 text-accent" fill="currentColor" />
            Segurança
          </CardTitle>
          <CardDescription>Atualize sua senha de acesso ao sistema.</CardDescription>
        </div>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="max-w-md space-y-4">
          <Field label="Senha atual" id="cfg-senha-atual">
            <Input
              id="cfg-senha-atual"
              type="password"
              placeholder="••••••••"
              value={senhaAtual}
              onChange={(e) => setSenhaAtual(e.target.value)}
              required
            />
          </Field>
          <Field label="Nova senha" id="cfg-senha-nova" hint="Mínimo de 8 caracteres">
            <Input
              id="cfg-senha-nova"
              type="password"
              placeholder="••••••••"
              value={novaSenha}
              onChange={(e) => setNovaSenha(e.target.value)}
              required
            />
          </Field>
          <Field label="Confirmar nova senha" id="cfg-senha-confirma">
            <Input
              id="cfg-senha-confirma"
              type="password"
              placeholder="••••••••"
              value={confirmarSenha}
              onChange={(e) => setConfirmarSenha(e.target.value)}
              required
            />
          </Field>
          <div className="flex justify-end pt-2">
            <Button variant="primary" type="submit" loading={salvando}>
              Atualizar senha
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

export function Configuracoes() {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="font-heading text-24 font-bold tracking-tight text-ink">Configurações</h2>
        <p className="text-14 text-ink-muted">
          Dados do escritório, áreas de atuação, notificações e segurança da conta.
        </p>
      </div>

      <Tabs
        defaultValue="escritorio"
        tabs={[
          { value: "escritorio", rotulo: "Escritório", conteudo: <PainelEscritorio /> },
          { value: "areas", rotulo: "Áreas de Atuação", conteudo: <PainelAreas /> },
          { value: "notificacoes", rotulo: "Notificações", conteudo: <PainelNotificacoes /> },
          { value: "seguranca", rotulo: "Segurança", conteudo: <PainelSeguranca /> },
        ]}
      />
    </div>
  );
}
