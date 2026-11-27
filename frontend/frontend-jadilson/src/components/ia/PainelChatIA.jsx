import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import {
  ChatComposer,
  ChatLayout,
  ChatMessage,
  ChatMessageBubble,
  ChatMessageList,
  ChatMessageMetadata,
} from "@astryxdesign/core/Chat";
import { IconClock, IconPlus, IconTrash, IconXmark } from "symbols-react";
import { LogoIA } from "@/components/ia/LogoIA";
import { conversarComIA } from "@/lib/ia";
import { useSessao } from "@/context/sessao";
import { cn } from "@/lib/cn";

const LIMITE_TROCAS = 8; // 8 perguntas + 8 respostas = 16 mensagens
const LIMITE_MENSAGENS = LIMITE_TROCAS * 2;
const LIMITE_CARACTERES = 18_000;
const MAX_CONVERSAS_SALVAS = 20;

const ATALHOS_CHAT = [
  "Revise erros de grafia e reescreva os trechos com problema",
  "Resuma os principais pontos deste documento",
  "O que ainda falta nesta peça?",
];

const CURVA_SUAVE = [0.22, 1, 0.36, 1];

function horaAgora() {
  return new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

function chaveStorage(docId) {
  return `jadilson-chat-ia:${docId || "geral"}`;
}

function carregarConversas(docId) {
  try {
    const bruto = localStorage.getItem(chaveStorage(docId));
    const lista = bruto ? JSON.parse(bruto) : [];
    return Array.isArray(lista) ? lista : [];
  } catch {
    return [];
  }
}

function salvarConversas(docId, conversas) {
  try {
    localStorage.setItem(chaveStorage(docId), JSON.stringify(conversas.slice(0, MAX_CONVERSAS_SALVAS)));
  } catch {
    // Ignora se o storage estiver cheio ou indisponível.
  }
}

function criarNovaConversa() {
  return {
    id: `conv-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    titulo: "Nova conversa",
    atualizadaEm: new Date().toISOString(),
    mensagens: [],
  };
}

function formatarDataCurta(iso) {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }) + " · " + d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

/**
 * Painel de chat conversacional (Astryx Chat + animações Motion) com:
 * - Conversas salvas por documento (histórico + nova conversa);
 * - Limite de contexto por conversa para manter a precisão da IA;
 * - Integração direta com o diff inline vermelho/verde da folha A4.
 */
export function PainelChatIA({ docId, processo, textoDocumento, area, tipoPeca, aoSugerir, aoFechar }) {
  const { csrf } = useSessao();
  const [conversas, setConversas] = useState(() => carregarConversas(docId));
  const [conversaAtivaId, setConversaAtivaId] = useState(() => carregarConversas(docId)[0]?.id ?? null);
  const [historicoAberto, setHistoricoAberto] = useState(false);
  const [rascunho, setRascunho] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState(null);
  const abortarRef = useRef(null);

  const conversaAtiva = useMemo(
    () => conversas.find((c) => c.id === conversaAtivaId) ?? null,
    [conversas, conversaAtivaId],
  );
  const mensagens = useMemo(() => conversaAtiva?.mensagens ?? [], [conversaAtiva]);

  useEffect(() => {
    salvarConversas(docId, conversas);
  }, [docId, conversas]);

  const totalChars = useMemo(
    () => mensagens.reduce((acc, m) => acc + (m.conteudo?.length || 0), 0),
    [mensagens],
  );
  const trocasFeitas = Math.floor(mensagens.filter((m) => m.papel === "user").length);
  const limiteAtingido = mensagens.length >= LIMITE_MENSAGENS || totalChars >= LIMITE_CARACTERES;
  const percentualUso = Math.min(100, Math.round(Math.max(mensagens.length / LIMITE_MENSAGENS, totalChars / LIMITE_CARACTERES) * 100));

  function iniciarNovaConversa() {
    parar();
    const nova = criarNovaConversa();
    setConversaAtivaId(nova.id);
    setHistoricoAberto(false);
    setErro(null);
    setRascunho("");
  }

  function abrirConversa(id) {
    parar();
    setConversaAtivaId(id);
    setHistoricoAberto(false);
    setErro(null);
  }

  function excluirConversa(id, e) {
    e.stopPropagation();
    setConversas((atual) => {
      const restante = atual.filter((c) => c.id !== id);
      if (conversaAtivaId === id) {
        setConversaAtivaId(restante[0]?.id ?? null);
      }
      return restante;
    });
  }

  function gravarMensagensNaConversa(idAlvo, novasMensagens, tituloSugerido) {
    const agora = new Date().toISOString();
    setConversas((atual) => {
      const existe = atual.some((c) => c.id === idAlvo);
      const atualizada = existe
        ? atual.map((c) =>
            c.id === idAlvo
              ? {
                  ...c,
                  titulo: c.titulo === "Nova conversa" && tituloSugerido ? tituloSugerido : c.titulo,
                  atualizadaEm: agora,
                  mensagens: novasMensagens,
                }
              : c,
          )
        : [
            {
              id: idAlvo,
              titulo: tituloSugerido || "Nova conversa",
              atualizadaEm: agora,
              mensagens: novasMensagens,
            },
            ...atual,
          ];
      return [...atualizada].sort((a, b) => (a.atualizadaEm < b.atualizadaEm ? 1 : -1));
    });
  }

  async function enviar(textoBruto) {
    const conteudo = (textoBruto ?? rascunho).trim();
    if (!conteudo || carregando || limiteAtingido) return;

    const idAlvo = conversaAtiva?.id ?? criarNovaConversa().id;
    if (!conversaAtiva) setConversaAtivaId(idAlvo);

    const msgUsuario = { id: `u-${Date.now()}`, papel: "user", conteudo, hora: horaAgora() };
    const historicoAtualizado = [...mensagens, msgUsuario];
    const tituloSugerido = conteudo.length > 42 ? `${conteudo.slice(0, 42)}…` : conteudo;

    gravarMensagensNaConversa(idAlvo, historicoAtualizado, tituloSugerido);
    setRascunho("");
    setErro(null);
    setHistoricoAberto(false);
    setCarregando(true);

    const ctrl = new AbortController();
    abortarRef.current = ctrl;

    try {
      const resp = await conversarComIA({
        mensagens: historicoAtualizado,
        processo,
        textoDocumento,
        area,
        tipoPeca,
        csrf,
        sinal: ctrl.signal,
      });

      const nSug = resp.sugestoes?.length || 0;
      const msgIA = {
        id: `a-${Date.now()}`,
        papel: "assistant",
        conteudo: resp.resposta,
        hora: horaAgora(),
        alteracoes: nSug,
      };
      gravarMensagensNaConversa(idAlvo, [...historicoAtualizado, msgIA], tituloSugerido);

      if (nSug > 0 || resp.avisos?.length) {
        aoSugerir?.({ sugestoes: resp.sugestoes || [], avisos: resp.avisos || [] });
      }
    } catch (e) {
      if (e?.name !== "AbortError") {
        setErro(e?.message || "Não foi possível obter resposta da IA agora.");
      }
    } finally {
      if (abortarRef.current === ctrl) abortarRef.current = null;
      setCarregando(false);
    }
  }

  function parar() {
    abortarRef.current?.abort();
    abortarRef.current = null;
    setCarregando(false);
  }

  const estadoVazio = (
    <motion.div
      key="vazio"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -6 }}
      transition={{ duration: 0.24, ease: CURVA_SUAVE }}
      className="flex flex-col items-center justify-center gap-3 px-2 py-8 text-center"
    >
      <span className="bg-surface-muted border-border flex size-12 items-center justify-center rounded-2xl border shadow-sm">
        <LogoIA tamanho={26} />
      </span>
      <div className="space-y-1">
        <p className="text-14 text-ink font-semibold">Assistente Jurídico</p>
        <p className="text-12 text-ink-muted mx-auto max-w-[270px] leading-relaxed">
          Converse sobre a peça ou peça para reescrever e corrigir trechos direto no documento.
        </p>
      </div>
      <div className="mt-2 flex w-full flex-col gap-2">
        {ATALHOS_CHAT.map((sug, idx) => (
          <motion.button
            key={sug}
            type="button"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.22, delay: 0.05 * idx, ease: CURVA_SUAVE }}
            whileHover={{ y: -1 }}
            whileTap={{ scale: 0.985 }}
            onClick={() => enviar(sug)}
            className="border-border bg-surface-muted/50 hover:bg-surface-muted text-12 text-ink rounded-xl border px-3.5 py-2.5 text-left transition-colors"
          >
            {sug}
          </motion.button>
        ))}
      </div>
    </motion.div>
  );

  return (
    <div
      data-astryx-theme="neutral"
      style={{ colorScheme: "dark" }}
      className="chat-ia-astryx flex h-full min-h-[420px] flex-col overflow-hidden"
    >
      {/* Cabeçalho do Chat IA: título + histórico + nova conversa + fechar */}
      <div className="border-border flex shrink-0 items-center justify-between gap-2 border-b px-3.5 py-2.5">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setHistoricoAberto((v) => !v)}
            className={cn(
              "text-12 flex items-center gap-1.5 rounded-lg px-2 py-1 font-medium transition-colors",
              historicoAberto ? "bg-surface-muted text-ink" : "text-ink-muted hover:bg-surface-muted/60 hover:text-ink",
            )}
            title="Ver conversas salvas deste documento"
          >
            <IconClock className="size-3.5" fill="currentColor" />
            <span>Conversas</span>
            {conversas.length > 0 && (
              <span className="bg-surface-muted text-ink-muted rounded-full px-1.5 py-0.5 text-[10px] tabular-nums">
                {conversas.length}
              </span>
            )}
          </button>
        </div>

        <div className="flex items-center gap-1.5">
          {mensagens.length > 0 && (
            <span
              title={`Contexto usado nesta conversa: ${trocasFeitas} de ${LIMITE_TROCAS} trocas`}
              className={cn(
                "mr-1 text-[11px] tabular-nums",
                limiteAtingido ? "font-semibold text-amber-400" : percentualUso >= 75 ? "text-amber-300" : "text-ink-muted",
              )}
            >
              {trocasFeitas}/{LIMITE_TROCAS}
            </span>
          )}
          <button
            type="button"
            onClick={iniciarNovaConversa}
            className="border-border bg-surface-muted/60 hover:bg-surface-muted text-12 text-ink flex items-center gap-1 rounded-lg border px-2.5 py-1 font-medium transition-colors"
            title="Iniciar nova conversa"
          >
            <IconPlus className="size-3" fill="currentColor" />
            <span>Nova</span>
          </button>
          {aoFechar && (
            <button
              type="button"
              onClick={aoFechar}
              className="text-ink-muted hover:bg-surface-muted hover:text-ink flex size-7 items-center justify-center rounded-lg transition-colors"
              title="Voltar ao painel do documento"
              aria-label="Fechar Chat IA"
            >
              <IconXmark className="size-3.5" fill="currentColor" />
            </button>
          )}
        </div>
      </div>

      {/* Gaveta animada de conversas salvas */}
      <AnimatePresence initial={false}>
        {historicoAberto && (
          <motion.div
            key="historico"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: CURVA_SUAVE }}
            className="border-border bg-surface-muted/30 shrink-0 overflow-hidden border-b"
          >
            <div className="max-h-52 space-y-1 overflow-y-auto p-2.5">
              <div className="mb-1 flex items-center justify-between px-1">
                <span className="text-[11px] font-medium text-ink-muted">Conversas salvas neste documento</span>
                <button
                  type="button"
                  onClick={() => setHistoricoAberto(false)}
                  className="text-ink-muted hover:text-ink rounded p-0.5"
                  aria-label="Fechar histórico"
                >
                  <IconXmark className="size-3" fill="currentColor" />
                </button>
              </div>
              {conversas.length === 0 ? (
                <p className="text-12 text-ink-muted px-1 py-2">Nenhuma conversa salva ainda.</p>
              ) : (
                conversas.map((c) => {
                  const ativa = c.id === conversaAtiva?.id;
                  return (
                    <div
                      key={c.id}
                      onClick={() => abrirConversa(c.id)}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => e.key === "Enter" && abrirConversa(c.id)}
                      className={cn(
                        "group flex cursor-pointer items-center justify-between gap-2 rounded-lg px-2.5 py-2 transition-colors",
                        ativa ? "bg-surface-muted text-ink" : "text-ink-muted hover:bg-surface-muted/60 hover:text-ink",
                      )}
                    >
                      <div className="min-w-0 flex-1">
                        <p className="text-12 truncate font-medium">{c.titulo}</p>
                        <p className="text-[10px] opacity-70">
                          {formatarDataCurta(c.atualizadaEm)} · {Math.ceil(c.mensagens.length / 2)} msg
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={(e) => excluirConversa(c.id, e)}
                        className="text-ink-muted hover:text-status-vencido-ink rounded p-1 opacity-0 transition-opacity group-hover:opacity-100"
                        title="Excluir conversa"
                        aria-label="Excluir conversa"
                      >
                        <IconTrash className="size-3.5" fill="currentColor" />
                      </button>
                    </div>
                  );
                })
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Área principal do Chat (Astryx ChatLayout + ChatMessage + ChatComposer) */}
      <div className="min-h-0 flex-1 overflow-hidden">
        <ChatLayout
          density="compact"
          style={{ height: "100%", paddingInline: 14 }}
          composer={
            <div className="w-full space-y-2 pt-3 pb-3.5">
              <AnimatePresence>
                {limiteAtingido && (
                  <motion.div
                    key="aviso-limite"
                    initial={{ opacity: 0, y: 8, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 4 }}
                    transition={{ duration: 0.22, ease: CURVA_SUAVE }}
                    className="rounded-xl border border-amber-500/35 bg-amber-500/10 p-3 text-left"
                  >
                    <p className="text-12 font-semibold text-amber-300">Limite desta conversa atingido</p>
                    <p className="text-[11px] leading-relaxed text-amber-200/80 mt-0.5">
                      Para evitar que a IA perca contexto ou misture assuntos, inicie uma nova conversa. Esta fica salva no histórico.
                    </p>
                    <button
                      type="button"
                      onClick={iniciarNovaConversa}
                      className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-amber-400 px-3 py-1.5 text-[12px] font-semibold text-neutral-950 transition-colors hover:bg-amber-300"
                    >
                      <IconPlus className="size-3" fill="currentColor" />
                      Iniciar nova conversa
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>

              <ChatComposer
                density="compact"
                elevation="none"
                value={rascunho}
                onChange={setRascunho}
                onSubmit={enviar}
                onStop={parar}
                isStopShown={carregando}
                isDisabled={limiteAtingido}
                placeholder={
                  limiteAtingido
                    ? "Limite atingido — inicie uma nova conversa acima."
                    : "Pergunte ou peça para editar um trecho..."
                }
                status={erro ? { type: "error", message: erro } : undefined}
              />
            </div>
          }
        >
          <AnimatePresence mode="wait" initial={false}>
            {mensagens.length === 0 && !carregando ? (
              estadoVazio
            ) : (
              <motion.div
                key={conversaAtiva?.id || "lista"}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.16 }}
                className="pt-3 pb-6"
              >
                <ChatMessageList density="compact" gap={4} align="top" isStreaming={carregando}>
                  {mensagens.map((m) => (
                    <motion.div
                      key={m.id}
                      initial={{ opacity: 0, y: 10, scale: 0.985 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      transition={{ duration: 0.24, ease: CURVA_SUAVE }}
                      className="w-full"
                    >
                      <ChatMessage
                        sender={m.papel === "user" ? "user" : "assistant"}
                        avatar={
                          m.papel === "assistant" ? (
                            <span className="bg-surface-muted border-border mt-0.5 flex size-7 items-center justify-center rounded-full border">
                              <LogoIA tamanho={15} />
                            </span>
                          ) : undefined
                        }
                      >
                        <ChatMessageBubble
                          name={
                            m.papel === "assistant" ? (
                              <span className="mb-1 inline-block text-[11px] font-medium text-neutral-400">Assistente IA</span>
                            ) : undefined
                          }
                          metadata={<ChatMessageMetadata timestamp={m.hora} />}
                        >
                          <div className="break-words whitespace-pre-wrap text-[13px] leading-relaxed">{m.conteudo}</div>
                          {m.alteracoes > 0 && (
                            <p className="mt-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1.5 text-[11px] font-medium text-emerald-300">
                              {m.alteracoes === 1
                                ? "1 alteração marcada no texto — aprove no ✓ ou recuse no ✕."
                                : `${m.alteracoes} alterações marcadas no texto — aprove no ✓ ou recuse no ✕.`}
                            </p>
                          )}
                        </ChatMessageBubble>
                      </ChatMessage>
                    </motion.div>
                  ))}

                  {carregando && (
                    <motion.div
                      key="pensando"
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.2, ease: CURVA_SUAVE }}
                      className="w-full"
                    >
                      <ChatMessage
                        sender="assistant"
                        avatar={
                          <span className="bg-surface-muted border-border flex size-7 items-center justify-center rounded-full border">
                            <LogoIA estado="trabalhando" tamanho={15} />
                          </span>
                        }
                      >
                        <ChatMessageBubble name="Assistente IA">
                          <div className="flex items-center gap-2 text-[12px] text-ink-muted">
                            <span>Analisando o documento e redigindo</span>
                            <span className="inline-flex gap-1" aria-hidden="true">
                              {[0, 1, 2].map((i) => (
                                <motion.span
                                  key={i}
                                  className="inline-block size-1 rounded-full bg-current"
                                  animate={{ opacity: [0.25, 1, 0.25], y: [0, -2, 0] }}
                                  transition={{ duration: 0.9, repeat: Infinity, delay: i * 0.18 }}
                                />
                              ))}
                            </span>
                          </div>
                        </ChatMessageBubble>
                      </ChatMessage>
                    </motion.div>
                  )}
                </ChatMessageList>
              </motion.div>
            )}
          </AnimatePresence>
        </ChatLayout>
      </div>
    </div>
  );
}
