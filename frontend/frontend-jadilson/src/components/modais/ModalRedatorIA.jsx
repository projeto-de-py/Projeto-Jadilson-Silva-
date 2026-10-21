import { useState } from "react";
import { IconWandAndSparkles, IconDocumentOnDocument, IconArrowClockwise, IconArrowDownDocument } from "symbols-react";
import { ThinkingOrb } from "thinking-orbs";
import {
  Modal,
  Button,
  Select,
  Textarea,
  Field,
  useToast,
} from "@/components/ui";

const TIPOS_PECA = [
  "Contestação",
  "Petição inicial",
  "Recurso / Apelação",
  "Manifestação sobre documentos",
  "Relatório de andamento para o cliente",
];

function gerarMinuta(processo, tipoPeca) {
  const cabecalho = `${tipoPeca.toUpperCase()}\nProcesso nº ${processo?.numero ?? "[número do processo]"}\n${processo?.vara ?? "[vara / foro]"}\n\n`;

  const corpo = {
    "Contestação": `Excelentíssimo(a) Senhor(a) Doutor(a) Juiz(a) de Direito,\n\n${processo?.cliente ?? "A parte requerida"}, já qualificado(a) nos autos do processo em epígrafe, vem, respeitosamente, apresentar CONTESTAÇÃO à ação proposta, pelos fatos e fundamentos a seguir expostos.\n\nI – DOS FATOS\n${processo?.descricao || "Breve resumo dos fatos narrados na inicial e dos pontos controvertidos."}\n\nII – DO DIREITO\nAssiste razão à parte requerida, uma vez que os fatos narrados não encontram amparo na prova produzida até o momento, conforme será demonstrado.\n\nIII – DOS PEDIDOS\nAnte o exposto, requer-se o acolhimento da presente contestação, com a improcedência total dos pedidos formulados na inicial, condenando-se a parte autora ao pagamento das custas e honorários advocatícios.\n\nNestes termos,\nPede deferimento.`,
    "Petição inicial": `Excelentíssimo(a) Senhor(a) Doutor(a) Juiz(a) de Direito,\n\n${processo?.cliente ?? "A parte autora"}, por seu(sua) advogado(a) que esta subscreve, vem, respeitosamente, propor a presente ação em face da parte ré, pelos motivos a seguir expostos.\n\nI – DOS FATOS\n${processo?.descricao || "Resumo dos fatos que fundamentam o pedido."}\n\nII – DO DIREITO\nO pedido encontra amparo legal, conforme a legislação aplicável à matéria em questão.\n\nIII – DOS PEDIDOS\nDiante do exposto, requer-se a citação da parte ré e, ao final, a procedência total dos pedidos.\n\nDá-se à causa o valor de ${processo?.valorCausa ?? "[valor da causa]"}.\n\nNestes termos,\nPede deferimento.`,
    "Recurso / Apelação": `Excelentíssimo(a) Senhor(a) Doutor(a) Desembargador(a) Relator(a),\n\n${processo?.cliente ?? "A parte recorrente"}, inconformada com a r. sentença proferida nos autos em epígrafe, vem interpor o presente RECURSO, pelas razões a seguir.\n\nI – DA SÍNTESE DA DEMANDA\n${processo?.descricao || "Resumo do processo e da decisão recorrida."}\n\nII – DAS RAZÕES DE REFORMA\nA decisão merece reforma pelos fundamentos a seguir expostos, uma vez que não observou adequadamente a prova produzida e o direito aplicável à espécie.\n\nIII – DO PEDIDO\nRequer-se o conhecimento e provimento do presente recurso, para reformar a decisão recorrida nos termos aqui expostos.\n\nNestes termos,\nPede deferimento.`,
    "Manifestação sobre documentos": `Excelentíssimo(a) Senhor(a) Doutor(a) Juiz(a) de Direito,\n\n${processo?.cliente ?? "A parte"}, nos autos do processo em epígrafe, vem manifestar-se sobre os documentos juntados aos autos.\n\n${processo?.descricao || "Síntese dos documentos apresentados e da posição da parte quanto a eles."}\n\nNestes termos, requer-se seja a presente manifestação juntada aos autos e considerada por ocasião do julgamento.\n\nPede deferimento.`,
    "Relatório de andamento para o cliente": `Prezado(a) ${processo?.cliente ?? "Cliente"},\n\nSegue breve relatório sobre o andamento do processo nº ${processo?.numero ?? "[número do processo]"}, atualmente na fase de "${processo?.status ?? "andamento"}".\n\nResumo do caso: ${processo?.descricao || "Sem observações adicionais registradas até o momento."}\n\nPermanecemos à disposição para esclarecimentos adicionais.\n\nAtenciosamente,\nEquipe Jadilson Silva Advocacia`,
  };

  return cabecalho + (corpo[tipoPeca] ?? corpo["Contestação"]);
}

export function ModalRedatorIA({ open, onOpenChange, processo, aoInserir }) {
  const { toast } = useToast();
  const [tipoPeca, setTipoPeca] = useState(TIPOS_PECA[0]);
  const [gerando, setGerando] = useState(false);
  const [texto, setTexto] = useState("");

  function handleGerar() {
    setGerando(true);
    setTexto("");
    setTimeout(() => {
      setTexto(gerarMinuta(processo, tipoPeca));
      setGerando(false);
    }, 1100);
  }

  async function handleCopiar() {
    try {
      await navigator.clipboard.writeText(texto);
      toast({ tipo: "sucesso", titulo: "Texto copiado para a área de transferência" });
    } catch {
      toast({ tipo: "erro", titulo: "Não foi possível copiar o texto" });
    }
  }

  return (
    <Modal
      open={open}
      onOpenChange={(v) => {
        onOpenChange(v);
        if (!v) {
          setTexto("");
          setTipoPeca(TIPOS_PECA[0]);
        }
      }}
      titulo="Redator IA"
      descricao={`Gere um rascunho de peça processual para o processo ${processo?.numero ?? ""} com apoio de inteligência artificial.`}
      className="max-w-2xl"
      footer={
        <>
          <Button variant="ghost" type="button" onClick={() => onOpenChange(false)}>
            Fechar
          </Button>
          {texto && aoInserir && (
            <Button
              variant="secondary"
              type="button"
              className="gap-2"
              onClick={() => {
                aoInserir(texto);
                onOpenChange(false);
              }}
            >
              <IconArrowDownDocument className="size-4" fill="currentColor" />
              Inserir no documento
            </Button>
          )}
          {texto && (
            <Button variant="secondary" type="button" onClick={handleCopiar} className="gap-2">
              <IconDocumentOnDocument className="size-4" fill="currentColor" />
              Copiar texto
            </Button>
          )}
          <Button
            variant="primary"
            type="button"
            onClick={handleGerar}
            disabled={gerando}
            className="gap-2"
          >
            {gerando ? (
              <ThinkingOrb state="working" size={20} theme="dark" />
            ) : texto ? (
              <IconArrowClockwise className="size-4" fill="currentColor" />
            ) : (
              <IconWandAndSparkles className="size-4" fill="currentColor" />
            )}
            {texto ? "Gerar novamente" : "Gerar com IA"}
          </Button>
        </>
      }
    >
      <div className="space-y-4 pt-2">
        <Field label="Tipo de peça" id="redator-tipo" hint="Selecione o documento que a IA deve redigir">
          <Select
            id="redator-tipo"
            value={tipoPeca}
            onChange={(e) => setTipoPeca(e.target.value)}
            disabled={gerando}
          >
            {TIPOS_PECA.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </Select>
        </Field>

        <Field
          label="Pré-visualização"
          id="redator-texto"
          hint={texto ? "Edite livremente o texto gerado antes de usar." : "Clique em “Gerar com IA” para criar o rascunho."}
        >
          <Textarea
            id="redator-texto"
            value={gerando ? "" : texto}
            onChange={(e) => setTexto(e.target.value)}
            placeholder={gerando ? "Gerando rascunho com IA..." : "O texto gerado pela IA aparecerá aqui, pronto para edição."}
            disabled={gerando}
            rows={14}
            className="font-mono text-13 leading-relaxed"
          />
        </Field>
      </div>
    </Modal>
  );
}
