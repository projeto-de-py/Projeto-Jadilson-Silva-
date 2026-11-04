import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Check, ChevronDown, User } from "lucide-react";

/* ══ Assignees ════════════════════════════════════════════
   A pill that opens a list, and fills up with faces as you
   assign them. One, two, four — the pill grows to hold them
   and they overlap into a stack rather than a row.

   It was called "People picker", which named the widget
   rather than the job. What this is FOR is putting names
   against a thing — assigning a task, adding contributors —
   and the pill is the answer to "who is on this".

   THE PILL IS THE READOUT. There is no count badge and no
   "3 selected" caption: the faces themselves say who, which
   is the thing a person actually wants back. */

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

/* Contribuidores padrão de demonstração / fallback do escritório */
const CAST_PADRAO = [
  { id: "jadilson", name: "Jadilson Silva", role: "Sócio Diretor" },
  { id: "ana", name: "Ana Beatriz", role: "Advogada Cível" },
  { id: "carlos", name: "Carlos Eduardo", role: "Advogado Trabalhista" },
  { id: "mariana", name: "Mariana Souza", role: "Assistente Jurídico" },
];

/* the block's own box */
const W = 264;
const H = 268;

/* the faces in the pill */
const FACE = 28;
const CORNER = 20;
/* how much of each face the next one covers, px */
const LAP = 10;

/* ── the other way to stack (quad) ───────────────────────── */
const quad = (n, gut) => {
  const cell = (FACE - gut) / 2;
  const s = cell / FACE;
  const a = cell / 2;
  const b = FACE - cell / 2;
  const m = FACE / 2;
  if (n <= 1) return [{ cx: m, cy: m, s: 1 }];
  if (n === 2) return [{ cx: a, cy: m, s }, { cx: b, cy: m, s }];
  if (n === 3) return [{ cx: a, cy: a, s }, { cx: b, cy: a, s }, { cx: a, cy: b, s }];
  return [
    { cx: a, cy: a, s }, { cx: b, cy: a, s },
    { cx: a, cy: b, s }, { cx: b, cy: b, s },
  ];
};

function iniciais(nome = "") {
  return nome
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p[0])
    .join("")
    .toUpperCase() || "?";
}

export function Assignees({
  corner = CORNER,
  overlap = LAP,
  stack = "Row",
  contribuidores = CAST_PADRAO,
  selecionados,
  onChange,
  placeholder = "Adicionar colaboradores",
  className = "",
}) {
  const [open, setOpen] = useState(false);
  const [internalPicked, setInternalPicked] = useState(["jadilson", "ana"]);

  const isControlled = selecionados !== undefined;
  const picked = isControlled ? selecionados : internalPicked;

  const r = clamp(corner, 0, 26);
  const lap = clamp(overlap, 0, 22);
  const grid = stack === "Grid";

  const spots = quad(picked.length, 4 - (lap / 22) * 2);

  const rail = !picked.length
    ? 0
    : grid
      ? FACE
      : FACE + (picked.length - 1) * (FACE - lap);

  const toggle = (id) => {
    const next = picked.includes(id)
      ? picked.filter((x) => x !== id)
      : [...picked, id];

    if (!isControlled) {
      setInternalPicked(next);
    }
    onChange?.(next);
  };

  const getPessoa = (id) =>
    contribuidores.find((c) => String(c.id) === String(id)) || {
      id,
      name: `Colaborador #${id}`,
      role: "Equipe",
    };

  return (
    <div
      className={`pik ${className}`}
      style={{
        width: W,
        height: open ? H : "auto",
        "--pik-row-r": `${Math.max(0, r - 6)}px`,
      }}
    >
      <button
        type="button"
        className="pik-pill"
        style={{ borderRadius: r }}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="listbox"
      >
        <span className="pik-rail" style={{ width: rail }}>
          <AnimatePresence initial={false}>
            {picked.map((id, i) => {
              const spot = grid ? spots[Math.min(i, spots.length - 1)] : null;
              const tx = spot ? spot.cx - FACE / 2 : i * (FACE - lap);
              const ty = spot ? spot.cy - FACE / 2 : 0;
              const sc = spot ? spot.s : 1;
              const pessoa = getPessoa(id);

              return (
                <motion.span
                  key={id}
                  className="pik-face bg-surface-muted text-ink"
                  style={{ zIndex: contribuidores.length - i }}
                  initial={{
                    scale: 0.2 * sc,
                    opacity: 0,
                    x: tx,
                    y: ty - 10,
                    rotate: -22,
                  }}
                  animate={{ scale: sc, opacity: 1, x: tx, y: ty, rotate: 0 }}
                  exit={{
                    scale: 0.2 * sc,
                    opacity: 0,
                    x: tx,
                    y: ty - 6,
                    rotate: 14,
                  }}
                  transition={{
                    type: "spring",
                    stiffness: 500,
                    damping: 18,
                    mass: 0.8,
                    x: { type: "spring", stiffness: 380, damping: 34, mass: 0.7 },
                    y: { type: "spring", stiffness: 380, damping: 34, mass: 0.7 },
                    scale: {
                      type: "spring",
                      stiffness: 380,
                      damping: 34,
                      mass: 0.7,
                    },
                    opacity: { duration: 0.16 },
                  }}
                >
                  {pessoa.foto || pessoa.avatar ? (
                    <img
                      src={pessoa.foto || pessoa.avatar}
                      alt={pessoa.name || pessoa.nome}
                      draggable={false}
                    />
                  ) : (
                    <span className="text-11 font-semibold select-none">
                      {iniciais(pessoa.name || pessoa.nome)}
                    </span>
                  )}
                </motion.span>
              );
            })}
          </AnimatePresence>
        </span>

        {picked.length === 0 && (
          <span className="pik-say flex items-center gap-1.5 text-ink-muted">
            <User size={14} className="shrink-0" />
            <span>{placeholder}</span>
          </span>
        )}

        <ChevronDown
          className="pik-chev"
          size={16}
          strokeWidth={2}
          aria-hidden="true"
        />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            className="pik-card rounded-card"
            style={{ borderRadius: r }}
            role="listbox"
            aria-multiselectable="true"
            initial={{ opacity: 0, y: -10, scaleX: 0.86, scaleY: 0.72 }}
            animate={{ opacity: 1, y: 0, scaleX: 1, scaleY: 1 }}
            exit={{ opacity: 0, y: -8, scaleX: 0.92, scaleY: 0.86 }}
            transition={{
              type: "spring",
              stiffness: 500,
              damping: 18,
              mass: 0.9,
              opacity: { duration: 0.16 },
            }}
          >
            {contribuidores.map((p, index) => {
              const on = picked.map(String).includes(String(p.id));
              const nome = p.name || p.nome || "Colaborador";
              const cargo = p.role || p.perfil || "Equipe";

              return (
                <motion.button
                  key={p.id}
                  type="button"
                  className="pik-row"
                  role="option"
                  aria-selected={on}
                  data-on={on || undefined}
                  onClick={() => toggle(p.id)}
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{
                    type: "spring",
                    stiffness: 380,
                    damping: 34,
                    mass: 0.7,
                    delay: 0.04 * index + 0.03,
                  }}
                >
                  {p.foto || p.avatar ? (
                    <img
                      className="pik-av"
                      src={p.foto || p.avatar}
                      alt={nome}
                      draggable={false}
                    />
                  ) : (
                    <span className="pik-av bg-surface-muted text-ink flex items-center justify-center text-12 font-semibold">
                      {iniciais(nome)}
                    </span>
                  )}
                  <span className="pik-who">
                    <span className="pik-name">{nome}</span>
                    <span className="pik-role">{cargo}</span>
                  </span>
                  <span className="pik-mark">
                    <AnimatePresence initial={false}>
                      {on && (
                        <motion.span
                          className="pik-tick"
                          initial={{ scale: 0.4, opacity: 0 }}
                          animate={{ scale: 1, opacity: 1 }}
                          exit={{ scale: 0.4, opacity: 0 }}
                          transition={{
                            type: "spring",
                            stiffness: 500,
                            damping: 18,
                            mass: 0.6,
                          }}
                        >
                          <Check size={14} strokeWidth={2} />
                        </motion.span>
                      )}
                    </AnimatePresence>
                  </span>
                </motion.button>
              );
            })}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export { Assignees as Picker };

