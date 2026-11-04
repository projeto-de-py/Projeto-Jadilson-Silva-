import { useCallback, useEffect, useRef, useState } from "react";
import { apiJson } from "@/lib/api";
import { useToast } from "@/components/ui";

export function useNotificacoes(csrf) {
  const { toast } = useToast();
  const [itens, setItens] = useState([]);
  const [naoLidas, setNaoLidas] = useState(0);
  const [erro, setErro] = useState("");
  const vistos = useRef(null);

  const atualizar = useCallback(async () => {
    try {
      const [pagina, contagem] = await Promise.all([
        apiJson("notificacoes?pagina=1&limite=50"),
        apiJson("notificacoes/nao-lidas/contagem"),
      ]);
      const atuais = new Set(pagina.itens.map((item) => item.id));
      if (vistos.current) {
        for (const item of pagina.itens) {
          if (!vistos.current.has(item.id)) {
            toast({ tipo: item.severidade === "critica" ? "erro" : item.severidade === "atencao" ? "info" : "info", titulo: item.titulo, descricao: item.mensagem });
          }
        }
      }
      vistos.current = atuais;
      setItens(pagina.itens);
      setNaoLidas(contagem.nao_lidas);
      setErro("");
    } catch (falha) {
      setErro(falha.message || "Não foi possível carregar as notificações.");
    }
  }, [toast]);

  useEffect(() => {
    const inicial = window.setTimeout(() => atualizar(), 0);
    const intervalo = window.setInterval(atualizar, 30_000);
    window.addEventListener("notificacoes:atualizar", atualizar);
    return () => {
      window.clearTimeout(inicial);
      window.clearInterval(intervalo);
      window.removeEventListener("notificacoes:atualizar", atualizar);
    };
  }, [atualizar]);

  const marcarLida = useCallback(async (id) => {
    await apiJson(`notificacoes/${id}/lida`, { method: "POST", csrf, body: {} });
    await atualizar();
  }, [atualizar, csrf]);

  const marcarTodas = useCallback(async () => {
    await apiJson("notificacoes/lidas", { method: "POST", csrf, body: {} });
    await atualizar();
  }, [atualizar, csrf]);

  const limparTodas = useCallback(async () => {
    await apiJson("notificacoes/limpar", { method: "POST", csrf, body: {} });
    await atualizar();
  }, [atualizar, csrf]);

  return { itens, naoLidas, erro, atualizar, marcarLida, marcarTodas, limparTodas };
}
