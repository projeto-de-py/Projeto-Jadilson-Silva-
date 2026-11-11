import { useMemo, useState } from "react";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { IconBanknote, IconArrowUpRight, IconPlus, IconDocumentOnDocument } from "symbols-react";
import { Badge, Button, Card, EmptyState, Tabs } from "@/components/ui";
import { ModalNovaCobranca } from "@/components/financeiro/ModalNovaCobranca";
import { useApiDados } from "@/hooks/useApiDados";

const brl = (v) => Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const dia = (iso) => format(new Date(`${iso}T12:00:00`), "dd/MM/yyyy", { locale: ptBR });

const TOM_COBRANCA = { PENDENTE: "atencao", RECEBIDA: "ok", VENCIDA: "vencido", CANCELADA: "cumprido" };
const ROTULO_COBRANCA = { PENDENTE: "Pendente", RECEBIDA: "Recebida", VENCIDA: "Vencida", CANCELADA: "Cancelada" };
const TOM_ASSINATURA = { ENVIADO: "atencao", ASSINADO: "ok", RECUSADO: "vencido", ERRO: "vencido" };
const ROTULO_ASSINATURA = { ENVIADO: "Aguardando assinatura", ASSINADO: "Assinado", RECUSADO: "Recusado", ERRO: "Erro no envio" };

// Só abre links https (a fatura vem do provedor, mas nunca confiamos em URL cega).
const linkSeguro = (url) => (typeof url === "string" && url.startsWith("https://") ? url : null);

function Erro({ erro }) {
  const restrito = erro.status === 403;
  return (
    <EmptyState
      icon={IconBanknote}
      titulo={restrito ? "Área do advogado principal" : "Não foi possível carregar"}
      descricao={restrito ? "O financeiro e as assinaturas só aparecem para o advogado principal do escritório." : erro.message}
    />
  );
}

function Cobrancas({ aoNova }) {
  const cobrancas = useApiDados("financeiro/cobrancas?limite=200");
  const clientes = useApiDados("clientes?limite=100");

  const nomes = useMemo(() => Object.fromEntries((clientes.dados?.itens ?? []).map((c) => [c.id, c.nome])), [clientes.dados]);
  const itens = cobrancas.dados ?? [];
  const soma = (st) => itens.filter((c) => c.status === st).reduce((t, c) => t + Number(c.valor), 0);

  if (cobrancas.erro) return <Erro erro={cobrancas.erro} />;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        {[
          { rotulo: "A receber", valor: soma("PENDENTE"), tom: "text-ink" },
          { rotulo: "Vencido", valor: soma("VENCIDA"), tom: "text-status-vencido-ink" },
          { rotulo: "Recebido", valor: soma("RECEBIDA"), tom: "text-status-ok-ink" },
        ].map((t) => (
          <Card key={t.rotulo} className="p-6">
            <p className="text-13 text-ink-muted">{t.rotulo}</p>
            <p className={`font-heading text-24 mt-2 font-bold tabular-nums ${t.tom}`}>{brl(t.valor)}</p>
          </Card>
        ))}
      </div>

      {cobrancas.carregando ? (
        <p role="status" className="text-14 text-ink-muted">Carregando cobranças…</p>
      ) : itens.length === 0 ? (
        <EmptyState icon={IconBanknote} titulo="Nenhuma cobrança ainda" descricao="Emita a primeira cobrança de honorários por Pix ou boleto." acao={<Button onClick={aoNova}>Nova cobrança</Button>} />
      ) : (
        <Card>
          <ul className="divide-border divide-y">
            {itens.map((c) => {
              const fatura = linkSeguro(c.link_fatura);
              return (
                <li key={c.id} className="flex flex-col gap-3 p-6 sm:flex-row sm:items-center">
                  <div className="min-w-0 flex-1">
                    <p className="text-14 text-ink truncate font-semibold">{nomes[c.cliente_id] ?? `Cliente #${c.cliente_id}`}</p>
                    <p className="text-12 text-ink-muted truncate">
                      {c.descricao || "Honorários"} · {c.forma === "PIX" ? "Pix" : "Boleto"}
                      {c.total_parcelas > 1 ? ` · parcela ${c.parcela}/${c.total_parcelas}` : ""}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-14 text-ink font-semibold tabular-nums">{brl(c.valor)}</p>
                    <p className="text-12 text-ink-muted tabular-nums">vence {dia(c.vencimento)}</p>
                  </div>
                  <Badge tone={TOM_COBRANCA[c.status] ?? "neutral"} className="self-start sm:self-center">{ROTULO_COBRANCA[c.status] ?? c.status}</Badge>
                  {fatura && (
                    <a href={fatura} target="_blank" rel="noopener noreferrer" className="text-13 text-primary hover:text-primary-hover inline-flex items-center gap-1 font-medium">
                      Fatura <IconArrowUpRight className="size-3.5" fill="currentColor" />
                    </a>
                  )}
                </li>
              );
            })}
          </ul>
        </Card>
      )}
    </div>
  );
}

function Assinaturas() {
  const { dados, carregando, erro } = useApiDados("assinaturas?limite=200");
  const clientes = useApiDados("clientes?limite=100");
  const nomes = useMemo(() => Object.fromEntries((clientes.dados?.itens ?? []).map((c) => [c.id, c.nome])), [clientes.dados]);

  if (erro) return <Erro erro={erro} />;
  if (carregando) return <p role="status" className="text-14 text-ink-muted">Carregando assinaturas…</p>;
  if (!dados?.length) {
    return <EmptyState icon={IconDocumentOnDocument} titulo="Nenhum documento enviado para assinatura" descricao="Abra um documento no editor e use “Enviar para assinatura”." />;
  }
  return (
    <Card>
      <ul className="divide-border divide-y">
        {dados.map((a) => {
          const link = linkSeguro(a.link_assinatura);
          return (
            <li key={a.id} className="flex flex-col gap-3 p-6 sm:flex-row sm:items-center">
              <div className="min-w-0 flex-1">
                <p className="text-14 text-ink truncate font-semibold">{a.titulo}</p>
                <p className="text-12 text-ink-muted truncate">
                  {nomes[a.cliente_id] ?? a.signatario_nome} · enviado em {format(new Date(a.criado_em), "dd/MM/yyyy HH:mm", { locale: ptBR })}
                </p>
              </div>
              <Badge tone={TOM_ASSINATURA[a.status] ?? "neutral"}>{ROTULO_ASSINATURA[a.status] ?? a.status}</Badge>
              {link && a.status === "ENVIADO" && (
                <a href={link} target="_blank" rel="noopener noreferrer" className="text-13 text-primary hover:text-primary-hover inline-flex items-center gap-1 font-medium">
                  Link do cliente <IconArrowUpRight className="size-3.5" fill="currentColor" />
                </a>
              )}
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

export function Financeiro() {
  const [modalAberto, setModalAberto] = useState(false);
  const [versao, setVersao] = useState(0);

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="font-heading text-24 font-bold tracking-tight text-ink">Financeiro</h2>
          <p className="text-14 text-ink-muted">Cobrança de honorários (Pix e boleto) e documentos enviados para assinatura.</p>
        </div>
        <Button variant="primary" className="gap-2" onClick={() => setModalAberto(true)}>
          <IconPlus className="size-4" fill="currentColor" />
          Nova cobrança
        </Button>
      </div>

      <Tabs
        tabs={[
          { value: "cobrancas", rotulo: "Cobranças", conteudo: <Cobrancas key={versao} aoNova={() => setModalAberto(true)} /> },
          { value: "assinaturas", rotulo: "Assinaturas", conteudo: <Assinaturas /> },
        ]}
      />

      <ModalNovaCobranca open={modalAberto} onOpenChange={setModalAberto} aoCriada={() => setVersao((v) => v + 1)} />
    </div>
  );
}
