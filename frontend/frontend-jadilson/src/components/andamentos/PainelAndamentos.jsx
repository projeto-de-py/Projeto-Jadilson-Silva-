import { useCallback, useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
  Badge,
  Button,
  Field,
  HairlineEmptyState,
  Input,
  Skeleton,
  Textarea,
  useToast,
} from "@/components/ui";
import { apiJson } from "@/lib/api";

const LIMITE = 20;

/** `ocorrido_em` vem como horario local naive do escritorio (Brasilia). */
function formatarQuando(iso) {
  if (!iso) return "—";
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return iso;
  return format(data, "dd/MM/yyyy 'às' HH:mm", { locale: ptBR });
}

/**
 * Linha do tempo REAL de andamentos de um caso (RF06) + registro de nova
 * movimentacao. Fonte unica: a API (`/api/casos/{id}/andamentos`) - sem
 * dados ficticios nem localStorage. O responsavel vem da sessao (backend);
 * o formulario envia apenas titulo, descricao e a data/horario da ocorrencia.
 *
 * Permissoes sao controladas pelo backend: um 403/404/422 vira toast com a
 * mensagem do servidor - o frontend nunca decide quem pode registrar.
 */
export function PainelAndamentos({ casoId }) {
  const { csrf } = useOutletContext();
  const { toast } = useToast();

  const [itens, setItens] = useState([]);
  const [total, setTotal] = useState(0);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [salvando, setSalvando] = useState(false);

  const [titulo, setTitulo] = useState("");
  const [descricao, setDescricao] = useState("");
  const [ocorridoEm, setOcorridoEm] = useState("");

  const buscarPagina = useCallback(
    (pagina) =>
      apiJson(
        `casos/${casoId}/andamentos?pagina=${pagina}&limite=${LIMITE}&ordem=desc`,
      ),
    [casoId],
  );

  // Carga inicial: o `key={casoId}` no ponto de montagem zera itens/total ao
  // trocar de caso; aqui so aplicamos a resposta nos callbacks (padrao da
  // Agenda - nunca setState sincrono no corpo do efeito).
  useEffect(() => {
    let cancelado = false;
    buscarPagina(1)
      .then((corpo) => {
        if (cancelado) return;
        setItens(corpo.itens);
        setTotal(corpo.total);
        setErro("");
      })
      .catch((falha) => {
        if (cancelado) return;
        setErro(falha.message);
      })
      .finally(() => {
        if (!cancelado) setCarregando(false);
      });
    return () => {
      cancelado = true;
    };
  }, [buscarPagina]);

  // Recarga por acao do usuario (botoes "tentar de novo"/"carregar mais"):
  // setState sincrono aqui e permitido (handler de evento, nao efeito).
  async function carregar(pagina = 1) {
    setErro("");
    if (pagina === 1) setCarregando(true);
    try {
      const corpo = await buscarPagina(pagina);
      setItens((prev) =>
        pagina === 1 ? corpo.itens : [...prev, ...corpo.itens],
      );
      setTotal(corpo.total);
    } catch (falha) {
      setErro(falha.message);
    } finally {
      setCarregando(false);
    }
  }

  async function registrar(event) {
    event.preventDefault();
    const tituloTrim = titulo.trim();
    if (tituloTrim.length < 3) {
      toast({
        tipo: "erro",
        titulo: "Título muito curto",
        descricao: "Informe ao menos 3 caracteres.",
      });
      return;
    }
    setSalvando(true);
    try {
      const registro = await apiJson(`casos/${casoId}/andamentos`, {
        method: "POST",
        csrf,
        body: {
          titulo: tituloTrim,
          ...(descricao.trim() ? { descricao: descricao.trim() } : {}),
          ...(ocorridoEm ? { ocorrido_em: ocorridoEm } : {}),
        },
      });
      // Atualizacao imediata: o novo registro entra no topo (ordem desc).
      setItens((prev) => [registro, ...prev]);
      setTotal((valor) => valor + 1);
      setTitulo("");
      setDescricao("");
      setOcorridoEm("");
      toast({
        tipo: "sucesso",
        titulo: "Andamento registrado",
        descricao: tituloTrim,
      });
    } catch (falha) {
      toast({
        tipo: "erro",
        titulo:
          falha.status === 403
            ? "Sem permissão para registrar"
            : "Não foi possível registrar",
        descricao: falha.message,
      });
    } finally {
      setSalvando(false);
    }
  }

  const temMais = itens.length < total;

  return (
    <section className="space-y-6" aria-labelledby="titulo-andamentos">
      <div>
        <h3 id="titulo-andamentos" className="text-14 text-ink font-semibold">
          Linha do tempo do caso
        </h3>
        <p className="text-12 text-ink-muted mt-1">
          Movimentações registradas pelo escritório, da mais recente para a
          mais antiga.
        </p>
      </div>

      {/* Registro de nova movimentacao */}
      <form
        onSubmit={registrar}
        className="border-border bg-surface-muted/40 space-y-4 rounded-card border p-4"
      >
        <Field label="Título do andamento" id="andamento-titulo">
          <Input
            id="andamento-titulo"
            placeholder="Ex.: Petição inicial protocolada"
            value={titulo}
            onChange={(e) => setTitulo(e.target.value)}
            maxLength={160}
            required
          />
        </Field>
        <Field label="Descrição" id="andamento-descricao" hint="Opcional">
          <Textarea
            id="andamento-descricao"
            placeholder="Detalhes da movimentação..."
            value={descricao}
            onChange={(e) => setDescricao(e.target.value)}
            maxLength={4000}
            rows={3}
          />
        </Field>
        <Field
          label="Data e hora da movimentação"
          id="andamento-ocorrido"
          hint="Opcional — sem informação, registra o horário atual."
        >
          <Input
            id="andamento-ocorrido"
            type="datetime-local"
            value={ocorridoEm}
            onChange={(e) => setOcorridoEm(e.target.value)}
          />
        </Field>
        <Button type="submit" loading={salvando} className="w-full">
          Registrar andamento
        </Button>
      </form>

      {/* Estados: carregando / erro / vazio */}
      {carregando && (
        <div className="space-y-4" aria-label="Carregando andamentos">
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-2/3" />
        </div>
      )}

      {!carregando && erro && (
        <div role="alert" className="space-y-3">
          <p className="text-13 text-status-vencido-ink">{erro}</p>
          <Button variant="secondary" onClick={() => carregar(1)}>
            Tentar de novo
          </Button>
        </div>
      )}

      {!carregando && !erro && itens.length === 0 && (
        <HairlineEmptyState
          titulo="Nenhum andamento registrado"
          descricao="Registre a primeira movimentação deste caso no formulário acima."
        />
      )}

      {!carregando && !erro && itens.length > 0 && (
        <>
          <ol className="relative space-y-6 border-l border-border pl-6">
            {itens.map((item, indice) => (
              <li key={item.id} className="relative">
                <span
                  className={
                    indice === 0
                      ? "bg-primary absolute top-1 -left-[31px] size-3 rounded-full border-2 border-surface ring-4 ring-primary/25"
                      : "bg-border absolute top-1 -left-[31px] size-3 rounded-full border-2 border-surface"
                  }
                />
                <p className="text-14 text-ink font-medium">{item.titulo}</p>
                {item.descricao && (
                  <p className="text-13 text-ink-muted mt-1 whitespace-pre-line">
                    {item.descricao}
                  </p>
                )}
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  <span className="text-12 text-ink-muted tabular-nums">
                    {formatarQuando(item.ocorrido_em)}
                  </span>
                  <Badge tone="neutral">
                    {item.criado_por_nome || "Usuário removido"}
                  </Badge>
                </div>
              </li>
            ))}
          </ol>
          {temMais && (
            <Button
              variant="secondary"
              className="w-full"
              onClick={() => carregar(Math.ceil(itens.length / LIMITE) + 1)}
            >
              Carregar mais ({total - itens.length} restantes)
            </Button>
          )}
        </>
      )}
    </section>
  );
}
