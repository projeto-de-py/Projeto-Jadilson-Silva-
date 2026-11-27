import { Extension } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";

export const chaveBlocos = new PluginKey("sugestoesIA");

export const SugestoesIA = Extension.create({
  name: "sugestoesIA",
  addOptions() {
    return { aoRegistrar: () => {} };
  },
  addProseMirrorPlugins() {
    const { aoRegistrar } = this.options;
    return [
      new Plugin({
        key: chaveBlocos,
        state: {
          init: () => [],
          apply(tr, itens) {
            let atual = itens;
            const meta = tr.getMeta(chaveBlocos);
            if (tr.docChanged) {
              atual = atual
                .map((i) => {
                  const pos = tr.mapping.map(i.pos);
                  if (i.modo !== "diff") return { ...i, pos };
                  const from = tr.mapping.map(i.from, 1);
                  const to = tr.mapping.map(i.to, -1);
                  return { ...i, pos: to, from, to };
                })
                .filter((i) => i.modo !== "diff" || i.from < i.to);
            }
            if (meta?.adicionar) atual = [...atual, ...meta.adicionar];
            if (meta?.remover) atual = atual.filter((i) => i.id !== meta.remover);
            return atual;
          },
        },
        props: {
          decorations(state) {
            const itens = chaveBlocos.getState(state);
            if (!itens.length) return DecorationSet.empty;
            const limite = state.doc.content.size;
            const decoracoes = [];

            for (const i of itens) {
              if (i.modo === "diff") {
                const from = Math.max(0, Math.min(i.from, limite));
                const to = Math.max(from, Math.min(i.to, limite));
                if (from < to) {
                  decoracoes.push(Decoration.inline(from, to, { class: "sug-diff-antigo" }));
                }
                let widgetPos = to;
                if (!i.inline) {
                  const $to = state.doc.resolve(to);
                  widgetPos = $to.depth >= 1 ? Math.min($to.after(1), limite) : to;
                }
                decoracoes.push(
                  Decoration.widget(
                    widgetPos,
                    () => {
                      const el = document.createElement(i.inline ? "span" : "div");
                      el.className = i.inline ? "sug-diff-widget-inline" : "sug-diff-widget-bloco";
                      el.contentEditable = "false";
                      aoRegistrar(i.id, el);
                      return el;
                    },
                    { key: `sug-${i.id}`, side: 1, ignoreSelection: true, stopEvent: () => true, destroy: () => aoRegistrar(i.id, null) },
                  ),
                );
              } else {
                decoracoes.push(
                  Decoration.widget(
                    Math.max(0, Math.min(i.pos, limite)),
                    () => {
                      const el = document.createElement("div");
                      el.className = "sug-bloco";
                      el.contentEditable = "false";
                      aoRegistrar(i.id, el);
                      return el;
                    },
                    { key: `sug-${i.id}`, side: 1, ignoreSelection: true, stopEvent: () => true, destroy: () => aoRegistrar(i.id, null) },
                  ),
                );
              }
            }

            return DecorationSet.create(state.doc, decoracoes);
          },
        },
      }),
    ];
  },
})
export function posicaoDoBloco(state) {
  const $p = state.selection.$to;
  return $p.depth >= 1 ? $p.after(1) : $p.pos;
}

export function adicionarBlocos(editor, itens) {
  editor.view.dispatch(editor.state.tr.setMeta(chaveBlocos, { adicionar: itens }));
}

export function removerBloco(editor, id) {
  editor.view.dispatch(editor.state.tr.setMeta(chaveBlocos, { remover: id }));
}

export function obterItemSugestao(editor, id) {
  return chaveBlocos.getState(editor.state).find((i) => i.id === id) ?? null;
}

export function posicaoDoBlocoSalvo(editor, id) {
  return obterItemSugestao(editor, id)?.pos ?? null;
}

/**
 * Localiza o intervalo exato (from, to) de `trecho` no documento ProseMirror,
 * mesmo que o trecho atravesse formatações inline (negrito/itálico) ou tenha
 * pequenas diferenças de espaçamento.
 */
export function localizarIntervaloNoDoc(doc, trecho, ocupados = []) {
  // Remove aspas e reticencias que o modelo eventualmente coloca nas pontas do trecho.
  const alvo = (trecho || "")
    .trim()
    .replace(/^["""'«(\s.…]+/, "")
    .replace(/["""'»)\s…]+$/, "")
    .trim();
  if (!alvo) return null;

  // Constrói texto plano + mapa caractere -> posição real no doc ProseMirror.
  const chars = [];
  const mapaPos = [];
  let primeiroBloco = true;

  doc.descendants((no, pos) => {
    if (no.isTextblock && !primeiroBloco) {
      chars.push("\n");
      mapaPos.push(-1);
    }
    if (no.isTextblock) primeiroBloco = false;
    if (no.isText) {
      for (let k = 0; k < no.text.length; k++) {
        chars.push(no.text[k]);
        mapaPos.push(pos + k);
      }
    }
  });

  const textoPlano = chars.join("");
  const sobrepoe = (from, to) => ocupados.some((o) => from < o.to && to > o.from);

  // 1) Busca literal exata
  let idx = textoPlano.indexOf(alvo);
  while (idx !== -1) {
    const fimIdx = idx + alvo.length - 1;
    const from = mapaPos[idx];
    const toBase = mapaPos[fimIdx];
    if (from >= 0 && toBase >= 0) {
      const to = toBase + 1;
      if (!sobrepoe(from, to)) {
        return _montarResultadoIntervalo(doc, from, to);
      }
    }
    idx = textoPlano.indexOf(alvo, idx + 1);
  }

  // 2) Busca tolerante a espaços/quebras de linha e maiúsculas/minúsculas
  const normChars = [];
  const normMapa = [];
  let emEspaco = false;
  for (let i = 0; i < chars.length; i++) {
    if (/\s/.test(chars[i])) {
      if (!emEspaco && normChars.length > 0) {
        normChars.push(" ");
        normMapa.push(mapaPos[i]);
        emEspaco = true;
      }
    } else {
      normChars.push(chars[i].toLowerCase());
      normMapa.push(mapaPos[i]);
      emEspaco = false;
    }
  }
  const textoNorm = normChars.join("");
  const alvoNorm = alvo.replace(/\s+/g, " ").toLowerCase();
  let nIdx = textoNorm.indexOf(alvoNorm);
  while (nIdx !== -1) {
    const nFim = nIdx + alvoNorm.length - 1;
    const from = normMapa[nIdx];
    const toBase = normMapa[nFim];
    if (from >= 0 && toBase >= 0) {
      const to = toBase + 1;
      if (!sobrepoe(from, to)) {
        return _montarResultadoIntervalo(doc, from, to);
      }
    }
    nIdx = textoNorm.indexOf(alvoNorm, nIdx + 1);
  }

  // 3) Fallback por similaridade de palavras no parágrafo (caso o modelo tenha corrigido 1 palavra no próprio trecho)
  const palavrasAlvo = new Set(
    alvoNorm
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .split(/[^a-z0-9]+/)
      .filter((w) => w.length >= 3),
  );
  if (palavrasAlvo.size >= 3) {
    let melhor = null;
    doc.descendants((no, pos) => {
      if (!no.isTextblock || !no.textContent.trim()) return;
      const from = pos + 1;
      const to = pos + no.nodeSize - 1;
      if (from >= to || sobrepoe(from, to)) return;
      const palavrasNo = new Set(
        no.textContent
          .toLowerCase()
          .normalize("NFD")
          .replace(/[\u0300-\u036f]/g, "")
          .split(/[^a-z0-9]+/)
          .filter((w) => w.length >= 3),
      );
      let comuns = 0;
      for (const p of palavrasAlvo) if (palavrasNo.has(p)) comuns += 1;
      const taxa = comuns / palavrasAlvo.size;
      if (taxa >= 0.55 && (!melhor || taxa > melhor.taxa)) {
        melhor = { from, to, taxa };
      }
    });
    if (melhor) return _montarResultadoIntervalo(doc, melhor.from, melhor.to);
  }

  return null;
}

function _montarResultadoIntervalo(doc, from, to) {
  const $from = doc.resolve(from);
  const $to = doc.resolve(to);
  const mesmoBloco = $from.sameParent($to) && $from.parent.isTextblock;
  const cobreBlocoTodo =
    mesmoBloco &&
    doc.textBetween($from.start(), from).trim() === "" &&
    doc.textBetween(to, $to.end()).trim() === "";
  return { from, to, inline: mesmoBloco && !cobreBlocoTodo };
}

/* ------------------------------------------------------------------ *
 * 2) Texto fantasma (como o Copilot): sugestão em cinza após o        *
 *    cursor. Tab aceita, Esc descarta, Ctrl+→ aceita uma palavra.     *
 *    Qualquer edição ou movimento do cursor descarta a sugestão.      *
 * ------------------------------------------------------------------ */

export const chaveFantasma = new PluginKey("textoFantasma");

export const TextoFantasma = Extension.create({
  name: "textoFantasma",
  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: chaveFantasma,
        state: {
          init: () => null,
          apply(tr, atual) {
            const meta = tr.getMeta(chaveFantasma);
            if (meta !== undefined) return meta; // objeto {texto,pos} ou null
            if (tr.docChanged || tr.selectionSet) return null;
            return atual;
          },
        },
        props: {
          decorations(state) {
            const g = chaveFantasma.getState(state);
            if (!g) return DecorationSet.empty;
            return DecorationSet.create(state.doc, [
              Decoration.widget(
                g.pos,
                () => {
                  const span = document.createElement("span");
                  span.className = "ghost-ia";
                  span.contentEditable = "false";
                  span.textContent = g.texto;
                  const dica = document.createElement("kbd");
                  dica.textContent = "Tab";
                  span.appendChild(dica);
                  return span;
                },
                { side: 1, ignoreSelection: true, key: `ghost-${g.pos}-${g.texto}` },
              ),
            ]);
          },
          handleKeyDown(view, evento) {
            const g = chaveFantasma.getState(view.state);
            if (!g) return false;
            if (evento.key === "Tab" && !evento.shiftKey) {
              evento.preventDefault();
              view.dispatch(view.state.tr.insertText(g.texto, g.pos).setMeta(chaveFantasma, null));
              return true;
            }
            if (evento.key === "Escape") {
              view.dispatch(view.state.tr.setMeta(chaveFantasma, null));
              return true;
            }
            if (evento.key === "ArrowRight" && (evento.ctrlKey || evento.metaKey)) {
              evento.preventDefault();
              const m = g.texto.match(/^\s*\S+/);
              const palavra = m ? m[0] : g.texto;
              const resto = g.texto.slice(palavra.length);
              const tr = view.state.tr.insertText(palavra, g.pos);
              tr.setMeta(chaveFantasma, resto.trim() ? { texto: resto, pos: g.pos + palavra.length } : null);
              view.dispatch(tr);
              return true;
            }
            return false;
          },
        },
      }),
    ];
  },
});

export function definirFantasma(editor, valor) {
  editor.view.dispatch(editor.state.tr.setMeta(chaveFantasma, valor));
}
