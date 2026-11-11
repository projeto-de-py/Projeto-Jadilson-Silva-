import { Drawer } from "@lucasmarkes/hairline/react";
import { cn } from "@/lib/cn";

export function HairlineEmptyState({
  titulo = "Nenhum item encontrado",
  descricao = "Não encontramos nenhum registro correspondente aos filtros aplicados.",
  acao,
  className,
  tamanho = 180,
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-card border border-dashed border-border bg-surface px-8 py-10 text-center transition-colors",
        className,
      )}
    >
      <div
        className="text-ink relative flex items-center justify-center opacity-85 hover:opacity-100 transition-opacity"
        style={{ width: tamanho, height: tamanho }}
      >
        <Drawer
          theme="dark"
          style={{ width: tamanho, height: tamanho }}
          label="Arquivo de processos e documentos"
        />
      </div>

      <div className="space-y-1">
        <p className="text-16 font-semibold text-ink">{titulo}</p>
        {descricao && (
          <p className="text-14 text-ink-muted mx-auto max-w-md">
            {descricao}
          </p>
        )}
      </div>

      {acao && <div className="pt-2">{acao}</div>}
    </div>
  );
}

