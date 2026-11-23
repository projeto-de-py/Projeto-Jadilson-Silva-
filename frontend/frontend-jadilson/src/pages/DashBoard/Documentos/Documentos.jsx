import { useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  IconDocumentBadgePlus,
  IconArrowUpDocument,
  IconChevronLeft,
  IconFolderBadgePlus,
  IconMagnifyingglass,
  IconCheckmarkCircleFill,
  IconSquareAndPencil,
} from "symbols-react";
import { Button, Field, Input, Modal, Select, useToast, HairlineEmptyState } from "@/components/ui";
import { CartaoDocumento } from "@/components/documentos/CartaoDocumento";
import { CartaoPasta } from "@/components/documentos/CartaoPasta";
import { ModalMoverDocumento } from "@/components/documentos/ModalMoverDocumento";
import { ModalPasta } from "@/components/documentos/ModalPasta";
import { AREAS_DOC, MODELOS, modelosPorArea, preencherModelo } from "@/data/modelos";
import { useCarteira } from "@/data/escritorio";
import { useDocumentos } from "@/lib/documentos";
import { agruparEmPastas, agruparPorProcesso, destinoDoDocumento, maisRecentesPrimeiro } from "@/lib/pastasDocumentos";
import { usePastasPersonalizadas } from "@/lib/pastasPersonalizadas";
import { cn } from "@/lib/cn";

const clienteDaPasta = (pasta) => (pasta?.tipo === "cliente" ? Number(pasta.id) : undefined);
const personalizadaDaPasta = (pasta) => (pasta?.tipo === "personalizada" ? pasta.id : undefined);

export function Documentos() {
  const { docs, criar, excluir, mover } = useDocumentos();
  const { processos, clientes, carregando } = useCarteira();
  const minhas = usePastasPersonalizadas();
  const navegar = useNavigate();
  const [params, setParams] = useSearchParams();
  const { toast } = useToast();
  const [busca, setBusca] = useState("");
  const [filtro, setFiltro] = useState("todas");
  const [novoAberto, setNovoAberto] = useState(false);
  const [paraExcluir, setParaExcluir] = useState(null);
  const [paraMover, setParaMover] = useState(null);
  const [editandoPasta, setEditandoPasta] = useState(null); // { pasta } (pasta nula = nova)
  const arquivo = useRef(null);

  const pastas = useMemo(
    () => agruparEmPastas(docs, processos, clientes, minhas.personalizadas, minhas.cores),
    [docs, processos, clientes, minhas.personalizadas, minhas.cores],
  );
  const pastaId = params.get("cliente");
  const pasta = pastaId ? pastas.find((p) => p.id === pastaId) : null;
  const dosClientes = maisRecentesPrimeiro(pastas.filter((p) => p.tipo !== "personalizada"));
  const dasMinhas = maisRecentesPrimeiro(pastas.filter((p) => p.tipo === "personalizada"));
  const nomeDaPastaDoDocumento = useMemo(() => new Map(pastas.flatMap((p) => p.docs.map((d) => [d.id, p.nome]))), [pastas]);
  const buscando = busca.trim() !== "" || filtro !== "todas";

  const corresponde = (d) => {
    const termo = busca.toLowerCase();
    return (filtro === "todas" || d.area === filtro) && (d.titulo.toLowerCase().includes(termo) || d.tipo.toLowerCase().includes(termo));
  };
  const ordenados = (lista) => lista.filter(corresponde).sort((a, b) => b.atualizadoEm - a.atualizadoEm);

  function abrirPasta(id) {
    setParams(id ? { cliente: id } : {});
    setBusca("");
    setFiltro("todas");
  }

  function salvarPasta({ nome, cor }) {
    const atual = editandoPasta.pasta;
    if (!atual) {
      const nova = minhas.criar(nome, cor);
      toast({ tipo: "sucesso", titulo: "Pasta criada", descricao: `“${nova.nome}” está em Minhas pastas.` });
    } else if (atual.tipo === "personalizada") {
      minhas.atualizar(atual.id, { nome, cor });
    } else {
      minhas.definirCor(atual.id, cor);
    }
    setEditandoPasta(null);
  }

  function excluirPasta() {
    const { pasta: alvo } = editandoPasta;
    minhas.excluir(alvo.id);
    if (pastaId === alvo.id) abrirPasta(null);
    setEditandoPasta(null);
    toast({ tipo: "sucesso", titulo: "Pasta excluída", descricao: "Os documentos voltaram para a pasta do cliente deles." });
  }

  function pastaAtualDoDocumento(doc) {
    if (minhas.personalizadas.some((p) => p.id === doc.pastaId)) return doc.pastaId;
    return doc.clienteId != null ? String(doc.clienteId) : null;
  }

  async function importar(e) {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    const nome = f.name.replace(/\.[^.]+$/, "");
    try {
      let html;
      if (/\.docx$/i.test(f.name)) {
        const mammoth = await import("mammoth/mammoth.browser");
        const { value } = await mammoth.convertToHtml({ arrayBuffer: await f.arrayBuffer() });
        html = value;
      } else if (/\.(txt|html?)$/i.test(f.name)) {
        const texto = await f.text();
        html = /\.html?$/i.test(f.name) ? texto : texto.split(/\n{2,}/).map((p) => `<p>${p.replace(/&/g, "&amp;").replace(/</g, "&lt;")}</p>`).join("");
      } else {
        toast({ tipo: "info", titulo: "Formato não editável", descricao: "PDF não pode ser editado. Envie o arquivo em .docx, .txt ou .html." });
        return;
      }
      const doc = criar({ titulo: nome, area: "geral", tipo: "Documento importado", html: html || "<p></p>", clienteId: clienteDaPasta(pasta), pastaId: personalizadaDaPasta(pasta) });
      toast({ tipo: "sucesso", titulo: "Documento importado" });
      navegar(`/documentos/${doc.id}`);
    } catch {
      toast({ tipo: "erro", titulo: "Não foi possível ler o arquivo" });
    }
  }

  const abrirDocumento = (d) => navegar(`/documentos/${d.id}`);

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0">
          {pasta ? (
            <>
              <button type="button" onClick={() => abrirPasta(null)} className="text-13 text-ink-muted hover:text-ink inline-flex items-center gap-1 transition-colors">
                <IconChevronLeft className="size-3.5" fill="currentColor" />
                Todas as pastas
              </button>
              <h2 className="font-heading text-24 text-ink truncate font-bold tracking-tight">{pasta.nome}</h2>
              <p className="text-14 text-ink-muted">{pasta.tipo === "cliente" ? "Documentos deste cliente, organizados por processo." : "Documentos desta pasta."}</p>
            </>
          ) : (
            <>
              <h2 className="font-heading text-24 text-ink font-bold tracking-tight">Documentos</h2>
              <p className="text-14 text-ink-muted">Uma pasta por cliente com processo, mais as suas próprias pastas. Abra uma para ver e redigir as peças.</p>
            </>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          {pasta ? (
            <Button variant="secondary" className="gap-2" onClick={() => setEditandoPasta({ pasta })}>
              <IconSquareAndPencil className="size-4" fill="currentColor" />
              Personalizar pasta
            </Button>
          ) : (
            <Button variant="secondary" className="gap-2" onClick={() => setEditandoPasta({ pasta: null })}>
              <IconFolderBadgePlus className="size-4" fill="currentColor" />
              Nova pasta
            </Button>
          )}
          <input ref={arquivo} type="file" accept=".docx,.txt,.html,.htm,.pdf" className="hidden" onChange={importar} />
          <Button variant="secondary" className="gap-2" onClick={() => arquivo.current?.click()}>
            <IconArrowUpDocument className="size-4" fill="currentColor" />
            Importar documento
          </Button>
          <Button variant="primary" className="gap-2" onClick={() => setNovoAberto(true)}>
            <IconDocumentBadgePlus className="size-4" fill="currentColor" />
            Novo documento
          </Button>
        </div>
      </div>

      <div className="bg-surface border-border flex flex-col gap-4 rounded-card border p-4 xl:flex-row xl:items-center">
        <div className="relative flex-1">
          <IconMagnifyingglass fill="currentColor" className="text-ink-muted pointer-events-none absolute top-1/2 left-4 size-4 -translate-y-1/2" />
          <Input placeholder={pasta ? "Buscar nesta pasta…" : "Buscar em todos os documentos…"} className="ps-10" value={busca} onChange={(e) => setBusca(e.target.value)} />
        </div>
        <div className="flex flex-wrap gap-2" role="group" aria-label="Filtrar por área">
          {[{ id: "todas", rotulo: "Todas" }, ...AREAS_DOC].map((a) => (
            <button
              key={a.id}
              type="button"
              aria-pressed={filtro === a.id}
              onClick={() => setFiltro(a.id)}
              className={cn("text-13 h-10 rounded-full border px-4 font-medium transition-colors", filtro === a.id ? "bg-primary text-primary-foreground border-transparent" : "border-border text-ink-muted hover:text-ink")}
            >
              {a.rotulo}
            </button>
          ))}
        </div>
      </div>

      {pastaId && !pasta ? (
        <HairlineEmptyState
          titulo={carregando ? "Abrindo a pasta…" : "Pasta não encontrada"}
          descricao={carregando ? "Carregando os clientes." : "Essa pasta não existe mais ou você não tem acesso a ela."}
          acao={carregando ? null : <Button onClick={() => abrirPasta(null)}>Ver todas as pastas</Button>}
        />
      ) : pasta ? (
        <ConteudoDaPasta pasta={pasta} processos={processos} docs={ordenados(pasta.docs)} aoAbrir={abrirDocumento} aoMover={setParaMover} aoExcluir={setParaExcluir} aoCriar={() => setNovoAberto(true)} />
      ) : buscando ? (
        <ResultadosDaBusca docs={ordenados(docs)} pastaDe={(d) => nomeDaPastaDoDocumento.get(d.id)} aoAbrir={abrirDocumento} aoMover={setParaMover} aoExcluir={setParaExcluir} />
      ) : (
        <div className="space-y-10">
          <SecaoDePastas titulo="Clientes" vazio={carregando ? "Carregando os clientes…" : "Nenhum cliente com processo ainda. A pasta aparece quando o primeiro processo for cadastrado."}>
            {dosClientes.map((p) => (
              <li key={p.id}>
                <CartaoPasta pasta={p} aoAbrir={() => abrirPasta(p.id)} aoPersonalizar={() => setEditandoPasta({ pasta: p })} />
              </li>
            ))}
          </SecaoDePastas>
          <SecaoDePastas titulo="Minhas pastas" vazio="Crie pastas para organizar do seu jeito, como Modelos ou Contratos.">
            {dasMinhas.map((p) => (
              <li key={p.id}>
                <CartaoPasta pasta={p} aoAbrir={() => abrirPasta(p.id)} aoPersonalizar={() => setEditandoPasta({ pasta: p })} />
              </li>
            ))}
            <li>
              <button
                type="button"
                onClick={() => setEditandoPasta({ pasta: null })}
                className="border-border text-ink-muted hover:text-ink hover:border-ink/40 flex h-full min-h-56 w-full flex-col items-center justify-center gap-3 rounded-card border border-dashed transition-colors"
              >
                <IconFolderBadgePlus className="size-6" fill="currentColor" />
                <span className="text-14 font-medium">Nova pasta</span>
              </button>
            </li>
          </SecaoDePastas>
        </div>
      )}

      <ModalNovoDocumento
        key={pasta?.id ?? "raiz"}
        open={novoAberto}
        onOpenChange={setNovoAberto}
        clienteInicial={clienteDaPasta(pasta)}
        pastaInicial={personalizadaDaPasta(pasta)}
        processosDaPasta={pasta?.processos}
        aoCriar={(dados) => {
          const doc = criar(dados);
          setNovoAberto(false);
          navegar(`/documentos/${doc.id}`);
        }}
      />

      {editandoPasta && <ModalPasta key={editandoPasta.pasta?.id ?? "nova"} pasta={editandoPasta.pasta} aoSalvar={salvarPasta} aoExcluir={excluirPasta} aoFechar={() => setEditandoPasta(null)} />}

      <ModalMoverDocumento
        doc={paraMover}
        pastas={pastas}
        pastaAtualId={paraMover ? pastaAtualDoDocumento(paraMover) : null}
        aoFechar={() => setParaMover(null)}
        aoEscolher={(destino) => {
          mover(paraMover.id, destinoDoDocumento(destino));
          toast({ tipo: "sucesso", titulo: "Documento movido", descricao: destino ? `Agora está em “${destino.nome}”.` : "Voltou para a pasta automática." });
          setParaMover(null);
        }}
      />

      <Modal
        open={!!paraExcluir}
        onOpenChange={(v) => !v && setParaExcluir(null)}
        titulo="Excluir documento?"
        descricao={paraExcluir ? `“${paraExcluir.titulo}” será removido deste navegador.` : undefined}
        footer={
          <>
            <Button variant="secondary" onClick={() => setParaExcluir(null)}>Cancelar</Button>
            <Button variant="danger" onClick={() => { excluir(paraExcluir.id); setParaExcluir(null); }}>Excluir</Button>
          </>
        }
      />
    </div>
  );
}

function SecaoDePastas({ titulo, vazio, children }) {
  const itens = Array.isArray(children) ? children.flat() : [children];
  const semPastas = itens.every((c) => !c || (Array.isArray(c) && c.length === 0));
  return (
    <section className="space-y-4" aria-label={titulo}>
      <h3 className="text-14 text-ink-muted border-border border-b pb-2 font-semibold">{titulo}</h3>
      {semPastas && <p className="text-13 text-ink-muted">{vazio}</p>}
      <ul className="grid gap-x-6 gap-y-8 sm:grid-cols-2 xl:grid-cols-3">{children}</ul>
    </section>
  );
}

function ConteudoDaPasta({ pasta, processos, docs, aoAbrir, aoMover, aoExcluir, aoCriar }) {
  if (docs.length === 0) {
    return (
      <HairlineEmptyState
        titulo={pasta.docs.length === 0 ? "Esta pasta ainda não tem documentos" : "Nenhum documento corresponde à busca"}
        descricao={pasta.docs.length === 0 ? "Crie uma peça a partir de um modelo, importe um arquivo ou mova um documento para cá." : "Tente outro termo ou limpe o filtro de área."}
        acao={pasta.docs.length === 0 ? <Button onClick={aoCriar}>Novo documento</Button> : null}
      />
    );
  }
  return (
    <div className="space-y-8">
      {agruparPorProcesso(docs, processos).map(({ chave, processo, docs: doProcesso }) => (
        <section key={chave} className="space-y-4" aria-label={processo ? `Processo ${processo.numero}` : "Sem processo vinculado"}>
          <div className="border-border flex flex-wrap items-baseline gap-x-3 border-b pb-2">
            <h3 className="text-14 text-ink font-semibold">{processo ? processo.numero : "Sem processo vinculado"}</h3>
            {processo && <span className="text-12 text-ink-muted">{processo.tipoAcao}</span>}
            <span className="text-12 text-ink-muted ml-auto tabular-nums">{doProcesso.length}</span>
          </div>
          <ul className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
            {doProcesso.map((d) => (
              <CartaoDocumento key={d.id} doc={d} aoAbrir={() => aoAbrir(d)} aoMover={() => aoMover(d)} aoExcluir={() => aoExcluir(d)} />
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

function ResultadosDaBusca({ docs, pastaDe, aoAbrir, aoMover, aoExcluir }) {
  if (docs.length === 0) {
    return <HairlineEmptyState titulo="Nenhum documento encontrado" descricao="Nenhum documento corresponde à busca." />;
  }
  return (
    <ul className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
      {docs.map((d) => (
        <CartaoDocumento key={d.id} doc={d} cliente={pastaDe(d)} aoAbrir={() => aoAbrir(d)} aoMover={() => aoMover(d)} aoExcluir={() => aoExcluir(d)} />
      ))}
    </ul>
  );
}

function ModalNovoDocumento({ open, onOpenChange, aoCriar, clienteInicial, pastaInicial, processosDaPasta }) {
  const { processos: todos } = useCarteira(open);
  const processos = processosDaPasta?.length ? processosDaPasta : todos;
  const [area, setArea] = useState("trabalhista");
  const [modeloId, setModeloId] = useState("reclamacao-trabalhista");
  const [processoId, setProcessoId] = useState(() => (processosDaPasta?.length === 1 ? String(processosDaPasta[0].id) : ""));
  const [titulo, setTitulo] = useState("");

  const modelos = modelosPorArea(area);
  const modelo = MODELOS.find((m) => m.id === modeloId);
  const processo = processos.find((p) => String(p.id) === processoId);

  function escolherArea(id) {
    setArea(id);
    setModeloId(modelosPorArea(id)[0]?.id ?? "");
  }

  function criarDocumento(e) {
    e.preventDefault();
    if (!modelo) return;
    aoCriar({
      processoId: processo?.id,
      pastaId: pastaInicial,
      clienteId: pastaInicial ? undefined : processo?.clienteId ?? clienteInicial,
      titulo: titulo.trim() || `${modelo.rotulo}${processo ? ` – ${processo.cliente}` : ""}`,
      area: modelo.area,
      tipo: modelo.rotulo,
      html: preencherModelo(modelo.html, processo ? { cliente: processo.cliente, numero: processo.numero, vara: processo.vara } : {}),
    });
    setTitulo("");
    setProcessoId("");
  }

  return (
    <Modal open={open} onOpenChange={onOpenChange} titulo="Novo documento" descricao="Escolha a área e o tipo de peça. O modelo já vem no padrão de formatação do escritório." className="max-w-2xl">
      <form onSubmit={criarDocumento} className="space-y-6">
        <div className="flex flex-wrap gap-2" role="group" aria-label="Área do direito">
          {AREAS_DOC.map((a) => (
            <button key={a.id} type="button" aria-pressed={area === a.id} onClick={() => escolherArea(a.id)}
              className={cn("text-13 h-10 rounded-full border px-4 font-medium transition-colors", area === a.id ? "bg-primary text-primary-foreground border-transparent" : "border-border text-ink-muted hover:text-ink")}>
              {a.rotulo}
            </button>
          ))}
        </div>

        <ul className="grid gap-2 sm:grid-cols-2" role="radiogroup" aria-label="Tipo de documento">
          {modelos.map((m) => {
            const ativo = m.id === modeloId;
            return (
              <li key={m.id}>
                <button type="button" role="radio" aria-checked={ativo} onClick={() => setModeloId(m.id)}
                  className={cn("flex h-full w-full items-start gap-3 rounded-input border p-4 text-left transition-colors", ativo ? "border-primary bg-primary-soft" : "border-border hover:bg-surface-muted")}>
                  <span className="min-w-0 flex-1">
                    <span className="text-14 text-ink block font-medium">{m.rotulo}</span>
                    <span className="text-12 text-ink-muted mt-1 block">{m.descricao}</span>
                  </span>
                  {ativo && <IconCheckmarkCircleFill className="text-primary mt-0.5 size-4 shrink-0" fill="currentColor" />}
                </button>
              </li>
            );
          })}
        </ul>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Processo (opcional)" id="nd-processo" hint="Preenche cliente e número do processo.">
            <Select id="nd-processo" value={processoId} onChange={(e) => setProcessoId(e.target.value)}>
              <option value="">Sem vínculo</option>
              {processos.map((p) => <option key={p.id} value={p.id}>{processosDaPasta?.length ? p.numero : p.cliente}</option>)}
            </Select>
          </Field>
          <Field label="Título" id="nd-titulo">
            <Input id="nd-titulo" maxLength={120} value={titulo} onChange={(e) => setTitulo(e.target.value)} placeholder={modelo?.rotulo} />
          </Field>
        </div>

        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => onOpenChange(false)}>Cancelar</Button>
          <Button type="submit" disabled={!modelo}>Criar documento</Button>
        </div>
      </form>
    </Modal>
  );
}
