import { Extension } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";

/* ------------------------------------------------------------------ *
 * 1) Sugestões em bloco: cartões que aparecem DENTRO do documento,    *
 *    logo abaixo do parágrafo de referência (nada fica na lateral).   *
 *    O ProseMirror só reserva o lugar; quem desenha o cartão é o      *
 *    React, via portal, no elemento entregue por `aoRegistrar`.       *
 * ------------------------------------------------------------------ */

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
            if (tr.docChanged) atual = atual.map((i) => ({ ...i, pos: tr.mapping.map(i.pos) }));
            if (meta?.adicionar) atual = [...atual, ...meta.adicionar];
            if (meta?.remover) atual = atual.filter((i) => i.id !== meta.remover);
            return atual;
          },
        },
        props: {
          decorations(state) {
            const itens = chaveBlocos.getState(state);
            if (!itens.length) return DecorationSet.empty;
            return DecorationSet.create(
              state.doc,
              itens.map((i) =>
                Decoration.widget(
                  Math.max(0, Math.min(i.pos, state.doc.content.size)),
                  () => {
                    const el = document.createElement("div");
                    el.className = "sug-bloco";
                    el.contentEditable = "false";
                    aoRegistrar(i.id, el);
                    return el;
                  },
                  { key: `sug-${i.id}`, side: 1, ignoreSelection: true, stopEvent: () => true, destroy: () => aoRegistrar(i.id, null) },
                ),
              ),
            );
          },
        },
      }),
    ];
  },
});

/** Posição (fim do bloco de topo) onde o cartão deve aparecer, a partir da seleção. */
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

export function posicaoDoBlocoSalvo(editor, id) {
  return chaveBlocos.getState(editor.state).find((i) => i.id === id)?.pos ?? null;
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
