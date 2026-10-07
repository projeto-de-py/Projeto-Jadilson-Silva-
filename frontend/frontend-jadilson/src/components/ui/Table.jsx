import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { Skeleton } from "./Skeleton";
import { cn } from "@/lib/cn";

const alinhamentos = {
  esquerda: "text-left",
  direita: "text-right",
  centro: "text-center",
};

function OrdenarBotao({ coluna, ordenacao, onOrdenar }) {
  const ativa = ordenacao?.campo === coluna.id;
  const Icone = !ativa
    ? ArrowUpDown
    : ordenacao?.direcao === "asc"
      ? ArrowUp
      : ArrowDown;

  return (
    <button
      type="button"
      onClick={() => onOrdenar(coluna.id)}
      className="inline-flex items-center gap-1.5 font-medium text-inherit transition-colors hover:text-primary"
    >
      {coluna.rotulo}
      <Icone aria-hidden="true" className="size-3.5 opacity-60" />
    </button>
  );
}

export function Table({
  colunas,
  dados,
  carregando = false,
  vazio,
  chave = (linha, indice) => linha?.id ?? indice,
  ordenacao,
  onOrdenar,
  onLinhaClique,
  className,
}) {
  if (carregando) {
    return (
      <div
        className={cn(
          "overflow-hidden rounded-card border border-border",
          className,
        )}
      >
        <div className="divide-y divide-border">
          {Array.from({ length: 4 }).map((_, indice) => (
            <div key={indice} className="flex items-center gap-4 p-4">
              <Skeleton className="h-4 flex-1" />
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-6 w-20 rounded-badge" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!dados?.length) {
    return (
      <div
        className={cn(
          "border-border flex min-h-48 items-center justify-center rounded-card border p-6",
          className,
        )}
      >
        {vazio ?? (
          <p className="text-ink-muted text-14">Nenhum registro encontrado.</p>
        )}
      </div>
    );
  }

  return (
    <div
      className={cn(
        "overflow-x-auto rounded-card border border-border",
        className,
      )}
    >
      <table className="w-full border-collapse text-14">
        <thead>
          <tr className="bg-surface-muted border-border border-b">
            {colunas.map((coluna) => (
              <th
                key={coluna.id}
                scope="col"
                aria-sort={
                  ordenacao?.campo === coluna.id
                    ? ordenacao.direcao === "asc"
                      ? "ascending"
                      : "descending"
                    : undefined
                }
                className={cn(
                  "text-ink-muted px-4 py-3 text-12 font-semibold tracking-wide uppercase",
                  alinhamentos[coluna.alinhar ?? "esquerda"],
                  coluna.largura,
                )}
              >
                {coluna.ordenavel && onOrdenar ? (
                  <OrdenarBotao
                    coluna={coluna}
                    ordenacao={ordenacao}
                    onOrdenar={onOrdenar}
                  />
                ) : (
                  coluna.rotulo
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {dados.map((linha, indice) => (
            <tr
              key={chave(linha, indice)}
              tabIndex={onLinhaClique ? 0 : undefined}
              onClick={onLinhaClique ? () => onLinhaClique(linha) : undefined}
              onKeyDown={
                onLinhaClique
                  ? (evento) => {
                      if (evento.key === "Enter" || evento.key === " ") {
                        evento.preventDefault();
                        onLinhaClique(linha);
                      }
                    }
                  : undefined
              }
              className={cn(
                "transition-colors",
                onLinhaClique &&
                  "hover:bg-surface-muted cursor-pointer focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
              )}
            >
              {colunas.map((coluna) => (
                <td
                  key={coluna.id}
                  className={cn(
                    "text-ink px-4 py-3",
                    alinhamentos[coluna.alinhar ?? "esquerda"],
                  )}
                >
                  {coluna.render ? coluna.render(linha) : linha[coluna.id]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
