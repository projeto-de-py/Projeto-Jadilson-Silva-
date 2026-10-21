import { useState } from "react";
import {
  IconBuildingColumns,
  IconScalemass,
  IconBell,
  IconLock,
  IconCheckmark,
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

const AREAS_ATUACAO = [
  {
    id: "bancario",
    titulo: "Direito Bancário",
    descricao: "Revisão de contratos, juros abusivos e execuções bancárias.",
  },
  {
    id: "previdenciario",
    titulo: "Direito Previdenciário",
    descricao: "Aposentadorias, benefícios por incapacidade e revisões junto ao INSS.",
  },
  {
    id: "consumidor",
    titulo: "Direito do Consumidor",
    descricao: "Negativação indevida, práticas abusivas e reparação de danos.",
  },
];

function PainelEscritorio() {
  const { toast } = useToast();
  const [salvando, setSalvando] = useState(false);

  function handleSubmit(e) {
    e.preventDefault();
    setSalvando(true);
    setTimeout(() => {
      setSalvando(false);
      toast({ tipo: "sucesso", titulo: "Dados do escritório atualizados" });
    }, 700);
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
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Nome do Escritório" id="cfg-nome">
              <Input id="cfg-nome" defaultValue="Jadilson Silva Advocacia" />
            </Field>
            <Field label="OAB Responsável" id="cfg-oab">
              <Input id="cfg-oab" defaultValue="OAB/AL 00.000" />
            </Field>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="E-mail de Contato" id="cfg-email">
              <Input id="cfg-email" type="email" defaultValue="contato@jadilsonsilva.adv.br" />
            </Field>
            <Field label="Telefone / WhatsApp" id="cfg-telefone">
              <Input id="cfg-telefone" defaultValue="(82) 3221-0000" />
            </Field>
          </div>

          <Field label="Endereço" id="cfg-endereco">
            <Input id="cfg-endereco" defaultValue="Paulo Afonso/BA" />
          </Field>

          <Field
            label="Assinatura padrão em documentos"
            id="cfg-assinatura"
            hint="Usada ao final de minutas e relatórios gerados pelo Redator IA"
          >
            <Textarea
              id="cfg-assinatura"
              rows={3}
              defaultValue={"Atenciosamente,\nJadilson Silva Advocacia\nOAB/AL 00.000"}
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
  const { toast } = useToast();
  const [ativas, setAtivas] = useState({ bancario: true, previdenciario: true, consumidor: true });

  function alternar(id) {
    setAtivas((prev) => {
      const novo = { ...prev, [id]: !prev[id] };
      toast({
        tipo: "info",
        titulo: novo[id] ? "Área ativada" : "Área desativada",
        descricao: AREAS_ATUACAO.find((a) => a.id === id)?.titulo,
      });
      return novo;
    });
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

function PainelNotificacoes() {
  const [preferencias, setPreferencias] = useState(PREFERENCIAS_PADRAO);

  function alternar(id) {
    setPreferencias((prev) =>
      prev.map((p) => (p.id === id ? { ...p, ativo: !p.ativo } : p)),
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="space-y-1">
          <CardTitle className="flex items-center gap-2 text-18">
            <IconBell className="size-5 text-accent" fill="currentColor" />
            Notificações
          </CardTitle>
          <CardDescription>Escolha o que deve gerar alertas no painel e por e-mail.</CardDescription>
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
            <Switch
              checked={pref.ativo}
              onCheckedChange={() => alternar(pref.id)}
              aria-label={`Ativar ${pref.titulo}`}
            />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function PainelSeguranca() {
  const { toast } = useToast();
  const [salvando, setSalvando] = useState(false);

  function handleSubmit(e) {
    e.preventDefault();
    setSalvando(true);
    setTimeout(() => {
      setSalvando(false);
      toast({ tipo: "sucesso", titulo: "Senha atualizada com sucesso" });
    }, 700);
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
            <Input id="cfg-senha-atual" type="password" placeholder="••••••••" />
          </Field>
          <Field label="Nova senha" id="cfg-senha-nova" hint="Mínimo de 8 caracteres">
            <Input id="cfg-senha-nova" type="password" placeholder="••••••••" />
          </Field>
          <Field label="Confirmar nova senha" id="cfg-senha-confirma">
            <Input id="cfg-senha-confirma" type="password" placeholder="••••••••" />
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
