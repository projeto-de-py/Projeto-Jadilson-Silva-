import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import { FileText, Folder, Plus, Calendar, Clock, UserPlus } from "lucide-react";

/* ══ Liquid ═══════════════════════════════════════════════
   Three metaball studies: a toggle, a reorderable list, and
   a create menu.

   RECONSTRUCTED. The original file was destroyed; this is
   rebuilt against the surviving stylesheet, which specifies
   the geometry, the layering and the timing exactly. The
   behaviour matches what index.css and the catalog demos
   require. The original's internal reasoning is not
   recoverable and is not reproduced here.

   ── the shared constraint ───────────────────────────────
   Everything on a filtered layer must be OPAQUE. The goo
   filter thresholds alpha, so a translucent fill under it
   disappears. That is why each of these has two layers: an
   opaque blob layer that carries the filter, and an unfiltered
   layer above it carrying the text — antialiased type would
   be eaten by the same threshold. */

/* the elastic, as specified: ζ = 14 / (2·√(220·0.5)) ≈ 0.67,
   so it overshoots about 6% before it settles. A deliberate
   bounce, not a wobble. */
const LIQUID = {
  type: "spring",
  stiffness: 220,
  damping: 14,
  mass: 0.5,
};

/* Non-drag blocks reuse the same feel without the overshoot,
   so a toggle does not bounce like a dragged card. */
/* ── the same liquid, without the overshoot ────────────────
   For shapes whose corner radius is animating: a spring that
   passes its target drags the radius past it too, and corners
   that dip under and come back read as a wobble rather than
   as a bounce.

   NOT just LIQUID with more damping, which is what this was.
   Raising damping alone to 30 against the same stiffness put
   ζ at 1.43 — comfortably overdamped, so it stopped
   overshooting by creeping: about 470ms to settle, against
   LIQUID's 290ms. It read as slow because it was.

   Stiffness comes up with the damping instead, which holds ζ
   at 1.03 — no overshoot, and it lands in about 180ms. */
const LIQUID_STILL = { ...LIQUID, stiffness: 420, damping: 30 };

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

/* ══ 3 · Create ═══════════════════════════════════════════
   One shape, and no filter on it — the other studies fuse two
   or more shapes, this has exactly one, so a blur could only
   damage it. The liquid here is entirely in the timing: the
   press sinks, and the spread starts while the sink is still
   running so there is never a still frame.

   The pill's width is measured from its own label and written
   back as --pill-w, so the label can change without the shape
   jumping. */

const ITENS_PADRAO = [
  { icon: Folder, label: "Novo Processo" },
  { icon: UserPlus, label: "Novo Cliente" },
  { icon: Clock, label: "Novo Prazo" },
  { icon: Calendar, label: "Nova Audiência" },
];

/* ── the menu's corners, and there are three ───────────────
   The panel is 28, the rows inside it are cut to 28 less the
   10px inset — concentric, which is what makes a row look like
   it belongs in the panel rather than merely sitting in one —
   and the shut pill is a 38px button, so 19 is round for it.

   One knob moves all three because they are one relationship:
   turn it down and the panel, the pill and the rows square off
   together. Each is capped at half its own height, past which
   a bigger number draws the same shape. */
const CRT_CORNER = 20;
const CRT_MAX = 40;

export function CreateMenu({
  corner = CRT_CORNER,
  label = "Novo",
  items = ITENS_PADRAO,
  onSelect,
}) {
  const [open, setOpen] = useState(false);
  const [sink, setSink] = useState(false);

  const panel = useRef(null);
  const say = useRef(null);
  const beat = useRef(0);

  const [sayW, setSayW] = useState(96);

  /* ── MEASURE TWICE: ONCE NOW, ONCE THE FONT IS REAL ────────
     .crt-say clips whatever it cannot fit, so this width being
     even slightly short takes the right edge off the last
     letter — and it was short two different ways. */
  useLayoutEffect(() => {
    const el = say.current;
    if (!el) return;
    let live = true;
    const measure = () => {
      if (live) setSayW(el.offsetWidth + 1);
    };
    measure();
    document.fonts?.ready.then(measure).catch(() => {});
    return () => {
      live = false;
    };
  }, [label]);

  useEffect(() => () => {
    window.clearTimeout(beat.current);
  }, []);

  /* No close button and no title bar — anywhere but the menu
     puts it away. Registered only while it is open, and in an
     effect, so the very press that opened it cannot close it
     on the same click. */
  useEffect(() => {
    if (!open) return;
    const away = (e) => {
      if (!e.isTrusted) return;
      const box = panel.current
        ?.querySelector(".crt-panel")
        ?.getBoundingClientRect();
      const on =
        !!box &&
        e.clientX >= box.left &&
        e.clientX <= box.right &&
        e.clientY >= box.top &&
        e.clientY <= box.bottom;
      if (!on) {
        setOpen(false);
      }
    };
    document.addEventListener("pointerdown", away);
    return () => document.removeEventListener("pointerdown", away);
  }, [open]);

  const press = () => {
    setSink(true);
    window.clearTimeout(beat.current);
    /* 60ms handoff against a 120ms sink: the spread begins
       while the press is still running. */
    beat.current = window.setTimeout(() => {
      setSink(false);
      setOpen(true);
    }, 60);
  };

  /* glyph + gap + label + the padding either side */
  const pillW = 18 + 8 + sayW + 34;

  /* the two the animation needs as NUMBERS — Framer writes
     borderRadius inline, so it cannot read a css variable */
  const panelR = clamp(corner, 0, CRT_MAX);
  const shutR = Math.min(19, panelR * (19 / CRT_CORNER));

  const alturaPainel = Math.max(166, items.length * 36 + 24);

  return (
    <motion.div
      className="crt-stage"
      data-open={open || undefined}
      data-sink={sink || undefined}
      ref={panel}
      style={{
        "--pill-w": `${pillW}px`,
        "--crt-r": `${clamp(corner, 0, CRT_MAX)}px`,
        /* the shut pill is 38 tall, so 19 is as round as it goes */
        "--crt-shut-r": `${Math.min(19, clamp(corner, 0, CRT_MAX) * (19 / CRT_CORNER)).toFixed(2)}px`,
        /* concentric: the panel's corner less its 10px inset,
           and no rounder than the 34px row's own half */
        "--crt-row-r": `${Math.min(17, Math.max(0, clamp(corner, 0, CRT_MAX) - 10)).toFixed(2)}px`,
        "--panel-h": `${alturaPainel}px`,
      }}
    >
      <div className="crt-blobs" aria-hidden="true">
        {/* LIQUID_STILL, not LIQUID. A spring past the target
            takes the corner radius with it — the corners dip
            under 28 and come back, which is a wobble, not a
            bounce. This is the one shape here that must not
            overshoot. */}
        <motion.div
          className="crt-body"
          animate={{
            width: open ? 212 : pillW,
            height: open ? alturaPainel : 38,
            borderRadius: open ? panelR : shutR,
          }}
          transition={LIQUID_STILL}
        />
      </div>

      <button className="crt-pill" onClick={press} aria-expanded={open} type="button">
        <span className="crt-glyph" aria-hidden="true">
          <Plus size={16} strokeWidth={2} />
        </span>
        <span className="crt-say" style={{ width: sayW || undefined }}>
          <span ref={say}>{label}</span>
        </span>
      </button>

      <div className="crt-panel">
        <ul className="crt-menu">
          {items.map((it, i) => {
            const Icone = it.icon || FileText;
            return (
              <li
                className="crt-item"
                key={it.label}
                style={{ transitionDelay: open ? `${30 + i * 22}ms` : "0ms" }}
              >
                <button
                  type="button"
                  onClick={() => {
                    setOpen(false);
                    it.onClick?.();
                    onSelect?.(it);
                  }}
                >
                  <Icone size={16} strokeWidth={2} />
                  <span>{it.label}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </motion.div>
  );
}
export { CreateMenu as Create };

