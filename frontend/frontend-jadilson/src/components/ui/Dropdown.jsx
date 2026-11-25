import { useEffect, useId, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Check, ChevronDown, Search, Plus } from "lucide-react";
import { spring } from "@/lib/motion";
import { cn } from "@/lib/cn";

function normalizar(texto = "") {
  return String(texto)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function normalizarOpcoes(options = []) {
  return options.map((opt) =>
    typeof opt === "string" || typeof opt === "number"
      ? { value: String(opt), label: String(opt) }
      : { ...opt, value: String(opt.value) },
  );
}

/**
 * Dropdown estilizado com seleção smooth (indicador deslizante via layoutId).
 *
 * Modos de uso:
 * - Filtro / Seleção padrão: <Dropdown options={...} value={...} onChange={...} />
 * - Seleção com busca: <Dropdown searchable options={...} value={...} onChange={...} />
 * - Combobox (digitar ou escolher): <Dropdown searchable allowCustom options={...} value={...} onChange={...} />
 */
export function Dropdown({
  id,
  options = [],
  value = "",
  onChange,
  placeholder = "Selecione...",
  searchable = false,
  allowCustom = false,
  emptyText = "Nenhuma opção encontrada.",
  disabled = false,
  error = false,
  className,
  menuClassName,
  "aria-label": ariaLabel,
}) {
  const uid = useId();
  const containerRef = useRef(null);
  const inputRef = useRef(null);
  const [aberto, setAberto] = useState(false);
  const [busca, setBusca] = useState("");
  const [ativoIdx, setAtivoIdx] = useState(0);

  const listaNormalizada = useMemo(() => normalizarOpcoes(options), [options]);

  const selecionada = useMemo(
    () => listaNormalizada.find((o) => o.value === String(value ?? "")),
    [listaNormalizada, value],
  );

  const termoBusca = allowCustom ? String(value ?? "") : busca;

  const opcoesFiltradas = useMemo(() => {
    const t = normalizar(termoBusca.trim());
    if (!t || (!searchable && !allowCustom)) return listaNormalizada;
    return listaNormalizada.filter(
      (o) =>
        normalizar(o.label).includes(t) ||
        (o.description && normalizar(o.description).includes(t)),
    );
  }, [listaNormalizada, termoBusca, searchable, allowCustom]);

  useEffect(() => {
    if (!aberto) return;
    function aoClicarFora(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setAberto(false);
        if (!allowCustom) setBusca("");
      }
    }
    document.addEventListener("pointerdown", aoClicarFora);
    return () => document.removeEventListener("pointerdown", aoClicarFora);
  }, [aberto, allowCustom]);

  function selecionar(opcao) {
    onChange?.(opcao.value, opcao);
    setAberto(false);
    if (!allowCustom) {
      setBusca("");
    }
  }

  function aoPressionarTecla(e) {
    if (disabled) return;
    if (!aberto) {
      if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") {
        if (!allowCustom || e.key === "ArrowDown") {
          e.preventDefault();
          setAtivoIdx(0);
          setAberto(true);
        }
      }
      return;
    }

    if (e.key === "Escape") {
      e.preventDefault();
      setAberto(false);
      if (!allowCustom) setBusca("");
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setAtivoIdx((i) => (opcoesFiltradas.length ? (i + 1) % opcoesFiltradas.length : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setAtivoIdx((i) =>
        opcoesFiltradas.length
          ? (i - 1 + opcoesFiltradas.length) % opcoesFiltradas.length
          : 0,
      );
    } else if (e.key === "Enter") {
      if (opcoesFiltradas[ativoIdx]) {
        e.preventDefault();
        selecionar(opcoesFiltradas[ativoIdx]);
      } else if (allowCustom) {
        setAberto(false);
      }
    } else if (e.key === "Tab") {
      setAberto(false);
    }
  }

  const textoExibido = selecionada ? selecionada.label : value || "";
  const temCorrespondenciaExata =
    allowCustom &&
    termoBusca.trim() !== "" &&
    listaNormalizada.some(
      (o) => normalizar(o.label) === normalizar(termoBusca.trim()),
    );

  return (
    <div ref={containerRef} className={cn("relative w-full", className)}>
      {allowCustom ? (
        <div
          className={cn(
            "border-input bg-surface text-ink flex h-10 w-full items-center gap-2 rounded-input border px-3.5 text-14 transition-colors",
            "focus-within:ring-2 focus-within:ring-ring",
            error && "border-status-vencido focus-within:ring-status-vencido",
            disabled && "cursor-not-allowed opacity-50",
          )}
        >
          <input
            ref={inputRef}
            id={id}
            type="text"
            role="combobox"
            aria-expanded={aberto}
            aria-controls={`${uid}-listbox`}
            aria-label={ariaLabel}
            autoComplete="off"
            disabled={disabled}
            placeholder={placeholder}
            value={value}
            onFocus={() => {
              setAtivoIdx(0);
              setAberto(true);
            }}
            onChange={(e) => {
              onChange?.(e.target.value, null);
              setAtivoIdx(0);
              if (!aberto) setAberto(true);
            }}
            onKeyDown={aoPressionarTecla}
            className="placeholder:text-ink-muted min-w-0 flex-1 bg-transparent text-14 text-ink outline-none"
          />
          <button
            type="button"
            tabIndex={-1}
            disabled={disabled}
            aria-label={aberto ? "Fechar opções" : "Abrir opções"}
            onClick={() => {
              setAtivoIdx(0);
              setAberto((v) => !v);
              inputRef.current?.focus();
            }}
            className="text-ink-muted hover:text-ink flex size-6 shrink-0 items-center justify-center rounded-md transition-colors"
          >
            <motion.span
              animate={{ rotate: aberto ? 180 : 0 }}
              transition={spring.snappy}
              className="inline-flex"
            >
              <ChevronDown className="size-4" />
            </motion.span>
          </button>
        </div>
      ) : (
        <button
          id={id}
          type="button"
          role="combobox"
          aria-expanded={aberto}
          aria-controls={`${uid}-listbox`}
          aria-label={ariaLabel}
          aria-invalid={error ? true : undefined}
          disabled={disabled}
          onClick={() => {
            setAtivoIdx(0);
            setAberto((v) => !v);
          }}
          onKeyDown={aoPressionarTecla}
          className={cn(
            "border-input bg-surface text-ink flex h-10 w-full items-center justify-between gap-2 rounded-input border px-4 text-14 transition-colors",
            "focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
            "hover:border-primary/40 disabled:cursor-not-allowed disabled:opacity-50",
            error && "border-status-vencido focus-visible:ring-status-vencido",
          )}
        >
          <span className={cn("truncate", !textoExibido && "text-ink-muted")}>
            {textoExibido || placeholder}
          </span>
          <motion.span
            animate={{ rotate: aberto ? 180 : 0 }}
            transition={spring.snappy}
            className="text-ink-muted inline-flex shrink-0"
          >
            <ChevronDown className="size-4" />
          </motion.span>
        </button>
      )}

      <AnimatePresence>
        {aberto && (
          <motion.div
            id={`${uid}-listbox`}
            role="listbox"
            initial={{ opacity: 0, y: -6, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.98 }}
            transition={spring.snappy}
            style={{ transformOrigin: "top center" }}
            className={cn(
              "bg-surface border-border shadow-popover absolute top-full right-0 left-0 z-[80] mt-2 overflow-hidden rounded-card border",
              menuClassName,
            )}
          >
            {searchable && !allowCustom && (
              <div className="border-border flex items-center gap-2 border-b px-3 py-2">
                <Search className="text-ink-muted size-3.5 shrink-0" />
                <input
                  type="text"
                  autoFocus
                  value={busca}
                  onChange={(e) => {
                    setBusca(e.target.value);
                    setAtivoIdx(0);
                  }}
                  onKeyDown={aoPressionarTecla}
                  placeholder="Filtrar..."
                  className="text-13 text-ink placeholder:text-ink-muted w-full bg-transparent outline-none"
                />
              </div>
            )}

            <div className="max-h-60 overflow-y-auto p-1.5">
              {opcoesFiltradas.length === 0 && !temCorrespondenciaExata ? (
                <div className="px-3 py-2.5 text-13 text-ink-muted">
                  {allowCustom && termoBusca.trim() ? (
                    <button
                      type="button"
                      onClick={() => setAberto(false)}
                      className="text-ink hover:bg-surface-muted flex w-full items-center gap-2 rounded-input px-2 py-1.5 text-left transition-colors"
                    >
                      <Plus className="size-3.5 shrink-0 text-primary" />
                      <span>
                        Usar novo cadastro:{" "}
                        <strong className="font-semibold">
                          “{termoBusca.trim()}”
                        </strong>
                      </span>
                    </button>
                  ) : (
                    emptyText
                  )}
                </div>
              ) : (
                <ul className="space-y-0.5">
                  {opcoesFiltradas.map((opcao, idx) => {
                    const estaSelecionada = String(value ?? "") === opcao.value;
                    const estaDestacada = ativoIdx === idx;

                    return (
                      <li key={opcao.value}>
                        <button
                          type="button"
                          role="option"
                          aria-selected={estaSelecionada}
                          onMouseEnter={() => setAtivoIdx(idx)}
                          onClick={() => selecionar(opcao)}
                          className={cn(
                            "relative flex w-full items-center justify-between gap-2 rounded-input px-3 py-2 text-left text-14 transition-colors",
                            estaSelecionada
                              ? "font-medium text-ink"
                              : "text-ink-muted hover:text-ink",
                          )}
                        >
                          {estaDestacada && (
                            <motion.span
                              layoutId={`${uid}-highlight`}
                              transition={spring.snappy}
                              aria-hidden="true"
                              className="bg-surface-muted absolute inset-0 rounded-input"
                            />
                          )}

                          <span className="relative z-10 min-w-0 flex-1">
                            <span className="block truncate">{opcao.label}</span>
                            {opcao.description && (
                              <span className="text-12 text-ink-muted block truncate">
                                {opcao.description}
                              </span>
                            )}
                          </span>

                          <span className="relative z-10 flex size-4 shrink-0 items-center justify-center">
                            <AnimatePresence initial={false}>
                              {estaSelecionada && (
                                <motion.span
                                  initial={{ scale: 0.4, opacity: 0 }}
                                  animate={{ scale: 1, opacity: 1 }}
                                  exit={{ scale: 0.4, opacity: 0 }}
                                  transition={spring.snappy}
                                  className="text-primary inline-flex"
                                >
                                  <Check className="size-3.5" strokeWidth={2.5} />
                                </motion.span>
                              )}
                            </AnimatePresence>
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
