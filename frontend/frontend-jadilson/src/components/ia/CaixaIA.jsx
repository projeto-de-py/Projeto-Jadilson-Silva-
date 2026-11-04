import { useEffect, useRef, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { AnimatePresence, motion } from "motion/react";
import { IconArrowUp, IconCheckmark, IconExclamationmarkCircleFill, IconQuestionmarkCircle, IconXmark } from "symbols-react";
import { ATALHOS_IA, solicitarSugestoes } from "@/lib/ia";
import { useSessao } from "@/context/sessao";
import { Select } from "@/components/ui";
import { LogoIA } from "@/components/ia/LogoIA";
import { useCarteira } from "@/data/escritorio";
import { cn } from "@/lib/cn";

function etapasDe(processo) {
  return [
    { rotulo: "Entendendo o pedido" },
    { rotulo: processo ? `Consultando o processo ${processo.numero}` : "Lendo o documento aberto" },
    { rotulo: "Redigindo a sugestão" },
    { rotulo: "Revisando o texto" },
  ];
}

const espera = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export function CaixaIA({ open, onOpenChange, processoId, aoMudarProcesso, textoDocumento, area, tipoPeca, nomeUsuario = "Dr. Jadilson", aoSugerir }) {
  const { csrf } = useSessao();
  const { processos } = useCarteira(open);
  const [pedido, setPedido] = useState("");
  const [fase, setFase] = useState("pedido");
  const [etapa, setEtapa] = useState(0);
  const [mensagem, setMensagem] = useState(null);
  const timers = useRef([]);
  const cancelado = useRef(false);

  const processo = processos.find((p) => String(p.id) === String(processoId)) ?? null;
  const etapas = etapasDe(processo);

  function limpar() {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  }

  useEffect(() => limpar, []);

  function fechar(v) {
    if (!v) {
      cancelado.current = true;
      limpar();
      setFase("pedido");
      setEtapa(0);
      setPedido("");
      setMensagem(null);
    }
    onOpenChange(v);
  }

  async function enviar(texto, acaoEscolhida) {
    const pedidoFinal = (texto ?? pedido).trim();
    if (!pedidoFinal) return;
    cancelado.current = false;
    setMensagem(null);
    setFase("trabalhando");
    setEtapa(0);
    timers.current.push(setTimeout(() => setEtapa(1), 700));
    timers.current.push(setTimeout(() => setEtapa(2), 1500));

    let resultado = null;
    let erro = null;
    const [resposta] = await Promise.all([
      solicitarSugestoes({ pedido: pedidoFinal, acao: acaoEscolhida, processo, textoDocumento, area, tipoPeca, csrf }).catch((e) => ({ erro: e })),
      espera(1500),
    ]);
    if (cancelado.current) return;
    if (resposta?.erro) erro = resposta.erro;
    else resultado = resposta;

    if (erro) {
      setMensagem({ tipo: "erro", textos: [erro.message] });
      setFase("resposta");
      return;
    }
    if (resultado.perguntas.length > 0) {
      setMensagem({ tipo: "pergunta", textos: resultado.perguntas });
      setFase("resposta");
      return;
    }
    setEtapa(3);
    await espera(600);
    if (cancelado.current) return;
    setFase("pronto");
    timers.current.push(
      setTimeout(() => {
        if (cancelado.current) return;
        aoSugerir(resultado);
        fechar(false);
      }, 700),
    );
  }

  const trabalhando = fase === "trabalhando" || fase === "pronto";

  return (
    <Dialog.Root open={open} onOpenChange={fechar}>
      <AnimatePresence>
        {open && (
          <Dialog.Portal forceMount>
            <Dialog.Overlay asChild forceMount>
              <motion.div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-md" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.18 }} />
            </Dialog.Overlay>
            <Dialog.Content asChild forceMount aria-describedby={undefined}>
              <div className="fixed inset-0 z-50 flex items-center justify-center p-4 focus:outline-none" onClick={() => !trabalhando && fechar(false)}>
                <motion.div
                  onClick={(e) => e.stopPropagation()}
                  initial={{ opacity: 0, scale: 0.97, y: 12 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.98, transition: { duration: 0.12 } }}
                  transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
                  className="bg-surface border-border relative w-full max-w-2xl overflow-hidden rounded-modal border shadow-popover"
                >
                  <div
                    aria-hidden="true"
                    className="pointer-events-none absolute inset-x-0 top-0 h-72"
                    style={{ background: "radial-gradient(60% 100% at 50% 0%, color-mix(in srgb, var(--color-ink) 12%, transparent), transparent 75%)" }}
                  />
                  <Dialog.Title className="sr-only">Assistente de IA</Dialog.Title>
                  <Dialog.Close
                    aria-label="Fechar"
                    className="text-ink-muted hover:text-ink hover:bg-surface-muted absolute top-4 right-4 z-10 flex size-10 items-center justify-center rounded-input transition-colors"
                  >
                    <IconXmark className="size-4" fill="currentColor" />
                  </Dialog.Close>

                  <div className="relative px-8 pt-12 pb-8">
                    <div className="flex flex-col items-center text-center">
                      <span className="bg-surface-muted border-border flex size-16 items-center justify-center rounded-[20px] border shadow-[0_8px_24px_rgb(0_0_0/0.35)]">
                        <LogoIA estado={fase === "pronto" ? "pronto" : fase === "trabalhando" ? "trabalhando" : "parado"} tamanho={36} />
                      </span>

                      <AnimatePresence mode="wait" initial={false}>
                        {fase === "pedido" ? (
                          <motion.div key="saudacao" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.2 }}>
                            <h2 className="font-heading text-28 mt-6 font-bold tracking-tight">
                              <span className="text-ink-muted block">Olá, {nomeUsuario}.</span>
                              <span className="text-ink block">O que vamos redigir hoje?</span>
                            </h2>
                            <p className="text-14 text-ink-muted mt-3">Eu leio o processo e sugiro trechos. Você decide o que entra no documento.</p>
                          </motion.div>
                        ) : fase === "resposta" ? (
                          <motion.div key="resposta" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }} className="mx-auto mt-8 w-full max-w-md" role="alert">
                            <div className="flex items-start gap-3 text-left">
                              {mensagem?.tipo === "erro" ? (
                                <IconExclamationmarkCircleFill className="text-status-vencido mt-0.5 size-5 shrink-0" fill="currentColor" />
                              ) : (
                                <IconQuestionmarkCircle className="text-accent mt-0.5 size-5 shrink-0" fill="currentColor" />
                              )}
                              <div className="space-y-2">
                                <p className="text-16 text-ink font-medium">
                                  {mensagem?.tipo === "erro" ? "Não consegui concluir o pedido" : "Preciso de mais uma informação"}
                                </p>
                                {mensagem?.textos.map((t) => (
                                  <p key={t} className="text-14 text-ink-muted">{t}</p>
                                ))}
                              </div>
                            </div>
                            <div className="mt-6 flex justify-center">
                              <button type="button" onClick={() => setFase("pedido")} className="border-border text-13 text-ink hover:border-ink/40 h-10 rounded-full border px-4 transition-colors">
                                {mensagem?.tipo === "erro" ? "Ajustar o pedido" : "Responder"}
                              </button>
                            </div>
                          </motion.div>
                        ) : (
                          <motion.div key="trabalho" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }} className="w-full">
                            <ol className="mx-auto mt-8 max-w-sm space-y-3 text-left" aria-live="polite">
                              {etapas.map((e, i) => {
                                const feita = i < etapa || fase === "pronto";
                                const atual = i === etapa && fase === "trabalhando";
                                const futura = i > etapa && fase !== "pronto";
                                if (futura) return null;
                                return (
                                  <motion.li key={e.rotulo} initial={{ opacity: 0, y: 10 }} animate={{ opacity: atual ? 1 : 0.45, y: 0 }} transition={{ duration: 0.3 }} className="flex items-center gap-3">
                                    <span className={cn("flex size-5 shrink-0 items-center justify-center rounded-full", feita ? "bg-status-ok-soft text-status-ok" : "bg-surface-muted")}>
                                      {feita ? <IconCheckmark className="size-3" fill="currentColor" /> : <span className="bg-ink size-1.5 animate-pulse rounded-full" />}
                                    </span>
                                    <span className={cn("text-16", atual ? "texto-shimmer font-medium" : "text-ink-muted")}>{e.rotulo}{atual && "…"}</span>
                                  </motion.li>
                                );
                              })}
                              {fase === "pronto" && (
                                <motion.li initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="text-ink flex items-center gap-3 font-medium">
                                  <span className="bg-status-ok text-bg flex size-5 shrink-0 items-center justify-center rounded-full"><IconCheckmark className="size-3" fill="currentColor" /></span>
                                  <span className="text-16">Sugestões prontas para revisar</span>
                                </motion.li>
                              )}
                            </ol>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>

                    {fase === "pedido" && (
                      <div className="mt-8">
                        <div className="bg-bg/60 border-border focus-within:border-ink/40 rounded-card border p-2 transition-colors">
                          <div className="text-12 text-ink-muted flex flex-wrap items-center justify-between gap-2 px-2 pt-1 pb-2">
                            <div className="flex items-center gap-2">
                              <span className={cn("size-2 rounded-full", processo ? "bg-status-ok" : "bg-ink-muted")} />
                              <Select
                                value={processoId ?? ""}
                                onChange={(e) => aoMudarProcesso(e.target.value)}
                                className="text-13 h-8 w-64 rounded-[8px] px-3"
                              >
                                <option value="">Sem processo vinculado</option>
                                {processos.map((p) => <option key={p.id} value={p.id}>{p.cliente}</option>)}
                              </Select>
                            </div>
                            <span>Revisão humana antes de qualquer inclusão</span>
                          </div>
                          <form
                            className="flex items-center gap-2"
                            onSubmit={(e) => { e.preventDefault(); enviar(); }}
                          >
                            <input
                              autoFocus
                              value={pedido}
                              onChange={(e) => setPedido(e.target.value)}
                              placeholder="Peça algo à IA…  ex.: resuma o processo"
                              className="text-16 text-ink placeholder:text-ink-muted h-12 min-w-0 flex-1 bg-transparent px-2 focus:outline-none"
                            />
                            <button
                              type="submit"
                              disabled={!pedido.trim()}
                              aria-label="Enviar pedido"
                              className="bg-primary text-primary-foreground flex size-10 shrink-0 items-center justify-center rounded-full transition-opacity disabled:opacity-30"
                            >
                              <IconArrowUp className="size-4" fill="currentColor" />
                            </button>
                          </form>
                        </div>

                        <ul className="mt-4 flex flex-wrap justify-center gap-2">
                          {ATALHOS_IA.map((a) => (
                            <li key={a.id}>
                              <button
                                type="button"
                                onClick={() => enviar(a.rotulo, a.id)}
                                className="border-border text-13 text-ink-muted hover:text-ink hover:border-ink/40 h-10 rounded-full border px-4 transition-colors"
                              >
                                {a.rotulo}
                              </button>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {fase === "trabalhando" && (
                      <div className="mt-8 flex justify-center">
                        <button type="button" onClick={() => fechar(false)} className="text-13 text-ink-muted hover:text-ink h-10 rounded-full px-4 transition-colors">
                          Parar
                        </button>
                      </div>
                    )}
                  </div>
                </motion.div>
              </div>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  );
}
