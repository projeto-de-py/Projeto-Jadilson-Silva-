import { useState } from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { motion } from "motion/react";
import { spring } from "@/lib/motion";
import { cn } from "@/lib/cn";

export function Tabs({ tabs, defaultValue, value, onValueChange, className }) {
  const [interno, setInterno] = useState(defaultValue ?? tabs[0]?.value);
  const atual = value ?? interno;

  function mudar(novo) {
    setInterno(novo);
    onValueChange?.(novo);
  }

  return (
    <TabsPrimitive.Root
      value={atual}
      onValueChange={mudar}
      className={cn("space-y-4", className)}
    >
      <TabsPrimitive.List className="bg-surface-muted border-border inline-flex rounded-input border p-1">
        {tabs.map((tab) => (
          <TabsPrimitive.Trigger
            key={tab.value}
            value={tab.value}
            className="relative rounded-input px-3 py-1.5 text-14 font-medium text-ink-muted transition-colors data-[state=active]:text-primary focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
          >
            {tab.value === atual && (
              <motion.span
                layoutId="tabs-indicator"
                className="bg-surface border-border absolute inset-0 rounded-input border"
                transition={spring.snappy}
              />
            )}
            <span className="relative z-10">{tab.rotulo}</span>
          </TabsPrimitive.Trigger>
        ))}
      </TabsPrimitive.List>

      {tabs.map((tab) => (
        <TabsPrimitive.Content
          key={tab.value}
          value={tab.value}
          className="focus:outline-none"
        >
          {tab.conteudo}
        </TabsPrimitive.Content>
      ))}
    </TabsPrimitive.Root>
  );
}
