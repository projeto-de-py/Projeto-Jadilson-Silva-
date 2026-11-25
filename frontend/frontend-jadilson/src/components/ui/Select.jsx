import { Children, isValidElement, useId, useState } from "react";
import * as RadixSelect from "@radix-ui/react-select";
import { AnimatePresence, motion } from "motion/react";
import { IconCheckmark, IconChevronDown } from "symbols-react";
import { Field } from "./Field";
import { spring } from "@/lib/motion";
import { cn } from "@/lib/cn";

// Radix não aceita valor "" em um item (ele é reservado para "limpar").
const VAZIO = "__vazio__";
const paraRadix = (v) => (v === "" || v == null ? VAZIO : String(v));
const dePradix = (v) => (v === VAZIO ? "" : v);

const gatilho = [
  "border-input bg-surface text-ink flex h-10 w-full items-center justify-between gap-2 rounded-input border px-4 text-14 transition-colors",
  "hover:border-primary/40 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
  "disabled:cursor-not-allowed disabled:opacity-50 data-[placeholder]:text-ink-muted",
].join(" ");

// Lê as <option> (como no <select> nativo) e devolve [{ valor, rotulo, desabilitada }].
function lerOpcoes(children) {
  const itens = [];
  const visitar = (no) => {
    Children.forEach(no, (filho) => {
      if (!isValidElement(filho)) return;
      if (filho.type === "option") {
        const rotulo = Children.toArray(filho.props.children).join("");
        itens.push({
          valor: filho.props.value !== undefined ? String(filho.props.value) : rotulo,
          rotulo,
          desabilitada: !!filho.props.disabled,
        });
      } else if (filho.props?.children) {
        visitar(filho.props.children);
      }
    });
  };
  visitar(children);
  return itens;
}

/**
 * Mesma API do <select> nativo (value, onChange(e), <option>), mas com a lista
 * aberta estilizada no tema do app.
 */
export function Select({
  label,
  hint,
  error,
  id,
  className,
  children,
  value: valorControlado,
  defaultValue,
  onChange,
  disabled,
  required,
  name,
  "aria-label": ariaLabel,
  placeholder,
}) {
  const uid = useId();
  const [interno, setInterno] = useState(defaultValue ?? "");
  const [aberto, setAberto] = useState(false);
  const [destaque, setDestaque] = useState(null);
  const value = valorControlado !== undefined ? valorControlado : interno;
  const opcoes = lerOpcoes(children);
  const atual = opcoes.find((o) => o.valor === String(value ?? ""));

  const aoMudarAberto = (proximo) => {
    setAberto(proximo);
    if (proximo) {
      setDestaque(paraRadix(value));
    }
  };

  const select = (
    <RadixSelect.Root
      open={aberto}
      onOpenChange={aoMudarAberto}
      value={paraRadix(value)}
      onValueChange={(v) => {
        setInterno(dePradix(v));
        onChange?.({ target: { value: dePradix(v), name } });
      }}
      disabled={disabled}
      required={required}
      name={name}
    >
      <RadixSelect.Trigger
        id={id}
        aria-label={ariaLabel}
        aria-invalid={error ? true : undefined}
        className={cn(gatilho, error && "border-status-vencido focus-visible:ring-status-vencido", className)}
      >
        <span className={cn("truncate", !atual && "text-ink-muted")}>{atual?.rotulo || placeholder || ""}</span>
        <RadixSelect.Icon asChild>
          <motion.span
            animate={{ rotate: aberto ? 180 : 0 }}
            transition={spring.snappy}
            className="text-ink-muted inline-flex shrink-0"
          >
            <IconChevronDown aria-hidden="true" fill="currentColor" className="size-4" />
          </motion.span>
        </RadixSelect.Icon>
      </RadixSelect.Trigger>

      <AnimatePresence>
        {aberto && (
          <RadixSelect.Portal forceMount>
            <RadixSelect.Content
              position="popper"
              sideOffset={6}
              collisionPadding={16}
              className="z-[80] w-(--radix-select-trigger-width) min-w-40 outline-none"
            >
              <motion.div
                initial={{ opacity: 0, y: -6, scale: 0.97 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -4, scale: 0.98 }}
                transition={spring.snappy}
                style={{ transformOrigin: "top center" }}
                className="bg-surface border-border text-ink shadow-popover max-h-[min(320px,var(--radix-select-content-available-height))] overflow-hidden rounded-card border"
              >
                <RadixSelect.Viewport className="max-h-[min(320px,var(--radix-select-content-available-height))] overflow-y-auto p-1.5">
                  {opcoes.map((o) => {
                    const valorRadix = paraRadix(o.valor);
                    const estaDestacada = destaque === valorRadix;

                    return (
                      <RadixSelect.Item
                        key={`${o.valor}`}
                        value={valorRadix}
                        disabled={o.desabilitada}
                        onPointerMove={() => setDestaque(valorRadix)}
                        onFocus={() => setDestaque(valorRadix)}
                        className="text-14 text-ink-muted data-highlighted:text-ink data-[state=checked]:text-ink data-[state=checked]:font-medium relative flex min-h-10 cursor-pointer items-center rounded-input py-2 ps-3 pe-9 transition-colors outline-none select-none data-disabled:opacity-40"
                      >
                        {estaDestacada && (
                          <motion.span
                            layoutId={`${uid}-highlight`}
                            transition={spring.snappy}
                            aria-hidden="true"
                            className="bg-surface-muted absolute inset-0 rounded-input"
                          />
                        )}
                        <span className="relative z-10 min-w-0 flex-1 leading-snug">
                          <RadixSelect.ItemText>{o.rotulo}</RadixSelect.ItemText>
                        </span>
                        <RadixSelect.ItemIndicator asChild>
                          <motion.span
                            initial={{ scale: 0.4, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            transition={spring.snappy}
                            className="absolute inset-e-3 z-10 inline-flex text-primary"
                          >
                            <IconCheckmark className="size-3.5" fill="currentColor" />
                          </motion.span>
                        </RadixSelect.ItemIndicator>
                      </RadixSelect.Item>
                    );
                  })}
                </RadixSelect.Viewport>
              </motion.div>
            </RadixSelect.Content>
          </RadixSelect.Portal>
        )}
      </AnimatePresence>
    </RadixSelect.Root>
  );

  if (!label && !hint && !error) {
    return select;
  }

  return (
    <Field label={label} hint={hint} error={error} id={id}>
      {select}
    </Field>
  );
}
