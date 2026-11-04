import { useCallback, useEffect, useRef, useState } from "react";
import { apiJson } from "@/lib/api";
import { useToast } from "@/components/ui";
import { tocarSomNotificacao } from "@/lib/somNotificacao";

const STORAGE_ALERTADOS_KEY = "notificacoes_alertadas_ids";

function carregarIdsAlertados() {
  try {
    const salvos = localStorage.getItem(STORAGE_ALERTADOS_KEY);
    if (!salvos) return new Set();
    const lista = JSON.parse(salvos);
    return new Set(Array.isArray(lista) ? lista : []);
  } catch {
    return new Set();
  }
}

function salvarIdsAlertados(setIds) {
  try {
    const lista = Array.from(setIds).slice(-200);
    localStorage.setItem(STORAGE_ALERTADOS_KEY, JSON.stringify(lista));
  } catch {
    // ignora falhas de storage
  }
}

export function useNotificacoes(csrf) {
  const { toast } = useToast();
  const [itens, setItens] = useState([]);
  const [naoLidas, setNaoLidas] = useState(0);
  const [erro, setErro] = useState("");
  const alertadosRef = useRef(carregarIdsAlertados());

  const atualizar = useCallback(async () => {
    try {
      const [pagina, contagem] = await Promise.all([
        apiJson("notificacoes?pagina=1&limite=50"),
        apiJson("notificacoes/nao-lidas/contagem"),
      ]);

      const listaItens = Array.isArray(pagina?.itens) ? pagina.itens : [];

      // Notificações não lidas que ainda não receberam alerta em toast nesta máquina
      const novasParaAlertar = listaItens.filter(
        (item) => !item.lida_em && !alertadosRef.current.has(item.id)
      );

      if (novasParaAlertar.length > 0) {
        // Dispara os toasts para as novas notificações (até 4 por lote para não poluir a viewport)
        const paraExibir = novasParaAlertar.slice(0, 4);
        for (const item of paraExibir) {
          toast({
            tipo:
              item.severidade === "critica"
                ? "erro"
                : item.severidade === "atencao"
                  ? "info"
                  : "info",
            titulo: item.titulo,
            descricao: item.mensagem,
            som: false,
          });
        }

        // Toca o som de notificação EXATAMENTE 1 VEZ para o lote
        tocarSomNotificacao();

        // Registra todos os novos IDs como alertados
        for (const item of novasParaAlertar) {
          alertadosRef.current.add(item.id);
        }
        salvarIdsAlertados(alertadosRef.current);
      }

      setItens(listaItens);
      setNaoLidas(contagem?.nao_lidas ?? 0);
      setErro("");
    } catch (falha) {
      setErro(falha.message || "Não foi possível carregar as notificações.");
    }
  }, [toast]);

  useEffect(() => {
    const inicial = window.setTimeout(() => atualizar(), 0);
    const intervalo = window.setInterval(atualizar, 15_000);
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
    alertadosRef.current.clear();
    salvarIdsAlertados(alertadosRef.current);
    await atualizar();
  }, [atualizar, csrf]);

  return { itens, naoLidas, erro, atualizar, marcarLida, marcarTodas, limparTodas };
}
