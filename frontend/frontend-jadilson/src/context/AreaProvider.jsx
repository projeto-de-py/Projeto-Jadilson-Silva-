import { useCallback, useMemo, useState } from "react";
import { AREAS, AreaContext } from "@/context/area-context";

const CHAVE = "area_selecionada";

function areaSalva() {
  try {
    const salva = localStorage.getItem(CHAVE);
    return AREAS.some((a) => a.id === salva) ? salva : "todas";
  } catch {
    return "todas";
  }
}

export function AreaProvider({ children }) {
  const [area, setAreaEstado] = useState(areaSalva);

  const setArea = useCallback((nova) => {
    setAreaEstado(nova);
    try {
      localStorage.setItem(CHAVE, nova);
    } catch {
      /* sem persistência local */
    }
  }, []);

  const valor = useMemo(() => ({ area, setArea }), [area, setArea]);
  return <AreaContext.Provider value={valor}>{children}</AreaContext.Provider>;
}

