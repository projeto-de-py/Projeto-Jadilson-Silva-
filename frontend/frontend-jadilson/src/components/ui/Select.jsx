import { Children, isValidElement, useState } from "react";
import * as RadixSelect from "@radix-ui/react-select";
import { IconCheckmark, IconChevronDown } from "symbols-react";
import { Field } from "./Field";
import { cn } from "@/lib/cn";

// Radix não aceita valor "" em um item (ele é reservado para "limpar").
const VAZIO = "__vazio__";
const paraRadix = (v) => (v === "" || v == null ? VAZIO : String(v));
const dePradix = (v) => (v === VAZIO ? "" : v);

const gatilho = [
  "border-input bg-surface text-ink flex h-10 w-full items-center justify-between gap-2 rounded-input border px-4 text-14",
  "focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
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
  const [interno, setInterno] = useState(defaultValue ?? "");
  const value = valorControlado !== undefined ? valorControlado : interno;
  const opcoes = lerOpcoes(children);
  const atual = opcoes.find((o) => o.valor === String(value ?? ""));

  const select = (
    <RadixSelect.Root
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
          <IconChevronDown aria-hidden="true" fill="currentColor" className="text-ink-muted size-4 shrink-0" />
        </RadixSelect.Icon>
      </RadixSelect.Trigger>

      <RadixSelect.Portal>
        <RadixSelect.Content
          position="popper"
          sideOffset={6}
          collisionPadding={16}
          className="bg-surface border-border text-ink shadow-popover z-[70] max-h-[min(320px,var(--radix-select-content-available-height))] w-[var(--radix-select-trigger-width)] min-w-40 overflow-hidden rounded-input border"
        >
          <RadixSelect.Viewport className="p-2">
            {opcoes.map((o) => (
              <RadixSelect.Item
                key={`${o.valor}`}
                value={paraRadix(o.valor)}
                disabled={o.desabilitada}
                className="text-14 data-[highlighted]:bg-surface-muted data-[state=checked]:font-medium relative flex min-h-10 cursor-pointer items-center rounded-[8px] py-2 ps-3 pe-9 outline-none select-none data-[disabled]:opacity-40"
              >
                <RadixSelect.ItemText>{o.rotulo}</RadixSelect.ItemText>
                <RadixSelect.ItemIndicator className="absolute end-3 inline-flex">
                  <IconCheckmark className="text-ink size-3.5" fill="currentColor" />
                </RadixSelect.ItemIndicator>
              </RadixSelect.Item>
            ))}
          </RadixSelect.Viewport>
        </RadixSelect.Content>
      </RadixSelect.Portal>
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
