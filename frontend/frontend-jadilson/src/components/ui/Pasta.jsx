import { BASES_DE_PASTA, misturar } from "@/lib/tonsDePasta";

/**
 * Pasta animada (adaptada do componente "folder" do 21st.dev, de @ravikatiyar162): ao passar o
 * mouse, a frente abre em 3D e as folhas aparecem. Quem usa precisa de um ancestral com a classe
 * `group`, que dispara a animação. As medidas são fixas (240 × 160 px) porque a geometria da
 * aba e da frente depende delas. `contagem` aparece na frente da pasta.
 *
 * As cores vêm dos tokens da plataforma (tema claro e escuro): o `tom` escolhe a cor-base e três
 * variáveis CSS (fundo, frente de baixo, frente de cima) são derivadas dela.
 */
export function Pasta({ contagem, tom = "neutro" }) {
  const [token, fundo, frenteBaixo, frenteCima, textoNumero] = BASES_DE_PASTA[tom] ?? BASES_DE_PASTA.neutro;
  const cores = {
    "--pasta-fundo": misturar(token, fundo),
    "--pasta-baixo": misturar(token, frenteBaixo),
    "--pasta-cima": misturar(token, frenteCima),
  };
  return (
    <div className="relative z-10 h-40 w-60 origin-bottom [perspective:1500px]" style={cores} aria-hidden="true">
      <div className="relative h-full w-full origin-top rounded-2xl rounded-tl-none bg-(--pasta-fundo) transition-all duration-300 ease-out group-hover:shadow-[0_20px_40px_rgba(0,0,0,.2)] motion-reduce:transition-none after:absolute after:bottom-[99%] after:left-0 after:h-4 after:w-20 after:rounded-t-2xl after:bg-(--pasta-fundo) after:content-[''] before:absolute before:-top-[15px] before:left-[75.5px] before:h-4 before:w-4 before:bg-(--pasta-fundo) before:content-[''] before:[clip-path:polygon(0_35%,0%_100%,50%_100%)]" />
      <div className="absolute inset-1 origin-bottom rounded-2xl bg-zinc-400 transition-all duration-300 ease-out select-none group-hover:[transform:rotateX(-20deg)] motion-reduce:transition-none" />
      <div className="absolute inset-1 origin-bottom rounded-2xl bg-zinc-300 transition-all duration-300 ease-out group-hover:[transform:rotateX(-30deg)] motion-reduce:transition-none" />
      <div className="absolute inset-1 origin-bottom rounded-2xl bg-zinc-200 transition-all duration-300 ease-out group-hover:[transform:rotateX(-38deg)] motion-reduce:transition-none" />
      <div className="absolute bottom-0 flex h-[156px] w-full origin-bottom items-end rounded-2xl rounded-tr-none bg-linear-to-t from-(--pasta-baixo) to-(--pasta-cima) transition-all duration-300 ease-out group-hover:shadow-[inset_0_20px_40px_var(--pasta-cima),inset_0_-20px_40px_var(--pasta-fundo)] group-hover:[transform:rotateX(-46deg)_translateY(1px)] motion-reduce:transition-none after:absolute after:bottom-[99%] after:right-0 after:h-[16px] after:w-[146px] after:rounded-t-2xl after:bg-(--pasta-cima) after:content-[''] before:absolute before:-top-[10px] before:right-[142px] before:size-3 before:bg-(--pasta-cima) before:content-[''] before:[clip-path:polygon(100%_14%,50%_100%,100%_100%)]">
        {contagem !== undefined && (
          <span className="text-14 m-4 font-bold tabular-nums" style={{ color: textoNumero }}>
            {contagem}
          </span>
        )}
      </div>
    </div>
  );
}
