// Modelos de peças por área. Os campos [ENTRE COLCHETES] são preenchidos pelo
// advogado; os de dados do processo são trocados automaticamente ao criar.

export const AREAS_DOC = [
  { id: "trabalhista", rotulo: "Trabalhista", tom: "primary" },
  { id: "bancario", rotulo: "Bancário", tom: "atencao" },
  { id: "previdenciario", rotulo: "Previdenciário", tom: "ok" },
  { id: "geral", rotulo: "Geral", tom: "neutral" },
];

const enderecamento = (orgao) =>
  `<p style="text-align:left;text-indent:0"><strong>EXCELENTÍSSIMO(A) SENHOR(A) DOUTOR(A) JUIZ(A) ${orgao}</strong></p><p style="text-align:left"><br></p><p style="text-align:left"><br></p>`;

const identificacao = `<p style="text-align:left;text-indent:0"><strong>Processo nº {{numero}}</strong></p>`;

const qualificacao = (papel) =>
  `<p><strong>{{cliente}}</strong>, [nacionalidade], [estado civil], [profissão], portador(a) do CPF nº [CPF] e do RG nº [RG], residente e domiciliado(a) em [ENDEREÇO COMPLETO], por seu advogado que esta subscreve (procuração anexa), vem, respeitosamente, à presença de Vossa Excelência, ${papel}`;

const fecho = `<p style="text-align:left">Nestes termos,<br>pede deferimento.</p><p style="text-align:left">Paulo Afonso/BA, [DATA].</p><p style="text-align:center;text-indent:0"><br>_______________________________<br><strong>[NOME DO ADVOGADO]</strong><br>OAB/BA nº [NÚMERO]</p>`;

const h = (t) => `<h2>${t}</h2>`;

export const MODELOS = [
  {
    id: "em-branco",
    area: "geral",
    rotulo: "Documento em branco",
    descricao: "Página A4 vazia com o padrão de formatação do escritório.",
    html: "<p></p>",
  },
  {
    id: "procuracao",
    area: "geral",
    rotulo: "Procuração ad judicia",
    descricao: "Outorga de poderes gerais para o foro.",
    html: `<h1>PROCURAÇÃO AD JUDICIA</h1>
<p><strong>OUTORGANTE:</strong> {{cliente}}, [nacionalidade], [estado civil], [profissão], CPF nº [CPF], RG nº [RG], residente em [ENDEREÇO].</p>
<p><strong>OUTORGADO:</strong> [NOME DO ADVOGADO], advogado(a), inscrito(a) na OAB/BA sob o nº [NÚMERO], com escritório em Paulo Afonso/BA.</p>
<p><strong>PODERES:</strong> pelo presente instrumento, o(a) outorgante nomeia o(a) outorgado(a) seu procurador, conferindo-lhe os poderes da cláusula <em>ad judicia et extra</em>, para o foro em geral, em qualquer juízo, instância ou tribunal, podendo propor ações, contestar, recorrer, transigir, desistir, firmar compromissos, receber e dar quitação, substabelecer com ou sem reserva de poderes, e praticar todos os atos necessários ao bom desempenho deste mandato.</p>
<p style="text-align:left">Paulo Afonso/BA, [DATA].</p>
<p style="text-align:center;text-indent:0"><br>_______________________________<br>{{cliente}}</p>`,
  },
  {
    id: "contrato-honorarios",
    area: "geral",
    rotulo: "Contrato de honorários",
    descricao: "Prestação de serviços advocatícios com forma de pagamento.",
    html: `<h1>CONTRATO DE PRESTAÇÃO DE SERVIÇOS ADVOCATÍCIOS</h1>
<p><strong>CONTRATANTE:</strong> {{cliente}}, CPF/CNPJ nº [CPF/CNPJ], residente em [ENDEREÇO].</p>
<p><strong>CONTRATADO:</strong> [NOME DO ADVOGADO], OAB/BA nº [NÚMERO].</p>
${h("CLÁUSULA 1ª – DO OBJETO")}
<p>O contratado prestará serviços de assessoria e patrocínio jurídico ao contratante em [DESCRIÇÃO DA CAUSA], até decisão final em [INSTÂNCIA].</p>
${h("CLÁUSULA 2ª – DOS HONORÁRIOS")}
<p>Pelos serviços, o contratante pagará honorários de [VALOR / PERCENTUAL], da seguinte forma: [FORMA DE PAGAMENTO].</p>
${h("CLÁUSULA 3ª – DAS DESPESAS")}
<p>Custas, emolumentos, diligências e demais despesas processuais correrão por conta do contratante.</p>
${h("CLÁUSULA 4ª – DO FORO")}
<p>Fica eleito o foro da Comarca de Paulo Afonso/BA para dirimir quaisquer controvérsias deste contrato.</p>
<p style="text-align:left">Paulo Afonso/BA, [DATA].</p>
<p style="text-align:center;text-indent:0"><br>_______________________________<br>{{cliente}}<br><br>_______________________________<br>[NOME DO ADVOGADO]</p>`,
  },

  // ---------- Trabalhista ----------
  {
    id: "reclamacao-trabalhista",
    area: "trabalhista",
    rotulo: "Reclamação trabalhista",
    descricao: "Petição inicial no rito ordinário ou sumaríssimo.",
    html: `${enderecamento("DA [NÚMERO]ª VARA DO TRABALHO DE PAULO AFONSO/BA")}
${qualificacao("propor a presente")}</p>
<h1>RECLAMAÇÃO TRABALHISTA</h1>
<p>em face de <strong>[NOME DA RECLAMADA]</strong>, [qualificação], com sede em [ENDEREÇO], pelos fatos e fundamentos a seguir expostos.</p>
${h("I – DOS FATOS")}
<p>O(A) reclamante foi admitido(a) em [DATA DE ADMISSÃO] para exercer a função de [FUNÇÃO], com remuneração de R$ [VALOR], tendo sido dispensado(a) em [DATA DA DISPENSA], [sem justa causa / outra modalidade].</p>
<p>[Descrever a jornada praticada, as verbas não pagas e as irregularidades ocorridas durante o contrato.]</p>
${h("II – DO DIREITO")}
<p>[Fundamentar com a CLT, a Constituição Federal (art. 7º) e a jurisprudência do TST aplicável: horas extras, verbas rescisórias, FGTS, adicionais, estabilidade etc.]</p>
${h("III – DA JUSTIÇA GRATUITA")}
<p>O(A) reclamante declara não possuir condições de arcar com as custas do processo sem prejuízo do próprio sustento, requerendo os benefícios da justiça gratuita, nos termos do art. 790, §§ 3º e 4º, da CLT.</p>
${h("IV – DOS PEDIDOS")}
<p>Ante o exposto, requer:</p>
<ol><li><p>a notificação da reclamada para comparecer à audiência e apresentar defesa, sob pena de revelia e confissão;</p></li><li><p>a procedência dos pedidos para condenar a reclamada ao pagamento de [LISTAR VERBAS E REFLEXOS];</p></li><li><p>a condenação em honorários advocatícios sucumbenciais e juros e correção monetária na forma da lei;</p></li><li><p>a produção de todos os meios de prova em direito admitidos.</p></li></ol>
<p>Dá-se à causa o valor de R$ [VALOR DA CAUSA].</p>
${fecho}`,
  },
  {
    id: "contestacao-trabalhista",
    area: "trabalhista",
    rotulo: "Contestação trabalhista",
    descricao: "Defesa da reclamada com preliminares e mérito.",
    html: `${enderecamento("DA [NÚMERO]ª VARA DO TRABALHO DE PAULO AFONSO/BA")}
${identificacao}
${qualificacao("apresentar")}</p>
<h1>CONTESTAÇÃO</h1>
<p>à reclamação trabalhista proposta por [NOME DO RECLAMANTE], pelos motivos de fato e de direito a seguir.</p>
${h("I – SÍNTESE DA INICIAL")}
<p>[Resumir as alegações do reclamante.]</p>
${h("II – PRELIMINARES")}
<p>[Inépcia, ilegitimidade, prescrição bienal e quinquenal, quando cabíveis.]</p>
${h("III – DO MÉRITO")}
<p>[Impugnar cada pedido de forma específica, com base nos documentos e na CLT.]</p>
${h("IV – DOS PEDIDOS")}
<p>Requer o acolhimento das preliminares e a improcedência total dos pedidos, protestando por todos os meios de prova admitidos.</p>
${fecho}`,
  },
  {
    id: "recurso-ordinario",
    area: "trabalhista",
    rotulo: "Recurso ordinário",
    descricao: "Recurso ao TRT contra sentença (8 dias).",
    html: `${enderecamento("DA [NÚMERO]ª VARA DO TRABALHO DE PAULO AFONSO/BA")}
${identificacao}
${qualificacao("interpor")}</p>
<h1>RECURSO ORDINÁRIO</h1>
<p>com fundamento no art. 895, I, da CLT, contra a r. sentença proferida nos autos, requerendo o seu recebimento e o encaminhamento ao Egrégio Tribunal Regional do Trabalho da 5ª Região.</p>
${h("I – DA TEMPESTIVIDADE")}
<p>A sentença foi publicada em [DATA], sendo tempestivo o recurso, interposto dentro do octídio legal.</p>
${h("II – DO PREPARO")}
<p>[Comprovar o recolhimento das custas e do depósito recursal, ou a isenção por justiça gratuita.]</p>
${h("III – DAS RAZÕES DO RECURSO")}
<p>[Apontar os erros da sentença, capítulo por capítulo, com fundamentação legal e jurisprudencial.]</p>
${h("IV – DO PEDIDO")}
<p>Requer o conhecimento e o provimento do recurso para reformar a sentença, nos termos expostos.</p>
${fecho}`,
  },

  // ---------- Bancário ----------
  {
    id: "revisional-contrato",
    area: "bancario",
    rotulo: "Ação revisional de contrato",
    descricao: "Revisão de juros e encargos abusivos em financiamento.",
    html: `${enderecamento("DE DIREITO DA [NÚMERO]ª VARA CÍVEL DA COMARCA DE PAULO AFONSO/BA")}
${qualificacao("propor a presente")}</p>
<h1>AÇÃO REVISIONAL DE CONTRATO BANCÁRIO</h1>
<p>em face de <strong>[NOME DA INSTITUIÇÃO FINANCEIRA]</strong>, CNPJ nº [CNPJ], com sede em [ENDEREÇO], pelas razões a seguir.</p>
${h("I – DOS FATOS")}
<p>Em [DATA], o(a) autor(a) celebrou o contrato de [MODALIDADE] nº [NÚMERO], no valor de R$ [VALOR], a ser pago em [Nº] parcelas de R$ [VALOR], com taxa de juros de [TAXA]% ao mês.</p>
${h("II – DO DIREITO")}
<p>A taxa contratada supera de forma relevante a taxa média de mercado divulgada pelo Banco Central do Brasil para a modalidade, o que caracteriza abusividade, nos termos do Código de Defesa do Consumidor (arts. 6º, V, e 51, IV) e da jurisprudência do Superior Tribunal de Justiça (Tema 27 dos recursos repetitivos).</p>
<p>[Demonstrar demais abusividades: capitalização de juros, tarifas, seguros embutidos, comissão de permanência.]</p>
${h("III – DA TUTELA DE URGÊNCIA")}
<p>[Requerer, se for o caso, a consignação das parcelas no valor incontroverso e a proibição de negativação.]</p>
${h("IV – DOS PEDIDOS")}
<ol><li><p>a inversão do ônus da prova e a concessão da justiça gratuita;</p></li><li><p>a citação da ré para responder aos termos da ação;</p></li><li><p>a procedência do pedido para revisar o contrato, adequando os encargos à taxa média de mercado;</p></li><li><p>a restituição, em dobro, dos valores pagos a maior;</p></li><li><p>a condenação da ré em custas e honorários advocatícios.</p></li></ol>
<p>Dá-se à causa o valor de R$ [VALOR DA CAUSA].</p>
${fecho}`,
  },
  {
    id: "exibicao-documentos",
    area: "bancario",
    rotulo: "Exibição de documentos",
    descricao: "Cautelar para obter contrato e extratos do banco.",
    html: `${enderecamento("DE DIREITO DA [NÚMERO]ª VARA CÍVEL DA COMARCA DE PAULO AFONSO/BA")}
${qualificacao("propor")}</p>
<h1>AÇÃO DE EXIBIÇÃO DE DOCUMENTOS</h1>
<p>em face de <strong>[NOME DA INSTITUIÇÃO FINANCEIRA]</strong>, pelos fundamentos a seguir.</p>
${h("I – DOS FATOS")}
<p>[Relatar a relação com a instituição e a solicitação administrativa dos documentos, anexando o protocolo.]</p>
${h("II – DO DIREITO")}
<p>O direito à exibição decorre dos arts. 396 a 404 do CPC e do dever de informação previsto no art. 6º, III, do CDC.</p>
${h("III – DOS PEDIDOS")}
<p>Requer a citação da ré para apresentar, no prazo legal, [CONTRATO, EXTRATOS E DEMAIS DOCUMENTOS], sob pena de busca e apreensão e das medidas do art. 400 do CPC.</p>
${fecho}`,
  },
  {
    id: "negativacao-indevida",
    area: "bancario",
    rotulo: "Indenização por negativação indevida",
    descricao: "Danos morais por inscrição indevida em cadastro de inadimplentes.",
    html: `${enderecamento("DO JUIZADO ESPECIAL CÍVEL DA COMARCA DE PAULO AFONSO/BA")}
${qualificacao("propor")}</p>
<h1>AÇÃO DECLARATÓRIA DE INEXIGIBILIDADE DE DÉBITO C/C INDENIZAÇÃO POR DANOS MORAIS</h1>
<p>em face de <strong>[NOME DA EMPRESA]</strong>, CNPJ nº [CNPJ], pelos fatos a seguir.</p>
${h("I – DOS FATOS")}
<p>O(A) autor(a) foi surpreendido(a) com a inscrição de seu nome nos cadastros de proteção ao crédito, em [DATA], por suposto débito de R$ [VALOR], decorrente do contrato nº [NÚMERO], que desconhece.</p>
${h("II – DO DIREITO")}
<p>A inscrição indevida configura dano moral presumido (<em>in re ipsa</em>), conforme jurisprudência consolidada do STJ, e a responsabilidade do fornecedor é objetiva (art. 14 do CDC).</p>
${h("III – DOS PEDIDOS")}
<ol><li><p>a declaração de inexistência do débito e a exclusão do nome do(a) autor(a) dos cadastros restritivos;</p></li><li><p>a condenação da ré ao pagamento de indenização por danos morais, em valor não inferior a R$ [VALOR];</p></li><li><p>a inversão do ônus da prova.</p></li></ol>
${fecho}`,
  },

  // ---------- Previdenciário ----------
  {
    id: "aposentadoria",
    area: "previdenciario",
    rotulo: "Concessão de aposentadoria",
    descricao: "Aposentadoria por tempo de contribuição, idade ou transição.",
    html: `${enderecamento("FEDERAL DA SUBSEÇÃO JUDICIÁRIA DE [CIDADE]/BA")}
${qualificacao("propor")}</p>
<h1>AÇÃO DE CONCESSÃO DE APOSENTADORIA</h1>
<p>em face do <strong>INSTITUTO NACIONAL DO SEGURO SOCIAL – INSS</strong>, autarquia federal, pelos fundamentos a seguir.</p>
${h("I – DOS FATOS")}
<p>O(A) autor(a) requereu administrativamente o benefício de aposentadoria em [DER], NB [NÚMERO], que foi indeferido sob o fundamento de [MOTIVO]. Contudo, conta com [TEMPO] de contribuição, conforme CNIS e documentos anexos.</p>
${h("II – DO DIREITO")}
<p>[Fundamentar com a regra aplicável: art. 201 da CF, Lei nº 8.213/91, EC nº 103/2019 e regras de transição; reconhecimento de tempo rural ou especial, se for o caso.]</p>
${h("III – DOS PEDIDOS")}
<ol><li><p>a concessão da gratuidade de justiça;</p></li><li><p>a citação do INSS;</p></li><li><p>a procedência do pedido para conceder a aposentadoria desde a DER, com o pagamento das parcelas vencidas, corrigidas e acrescidas de juros;</p></li><li><p>a condenação do réu em honorários advocatícios.</p></li></ol>
${fecho}`,
  },
  {
    id: "auxilio-incapacidade",
    area: "previdenciario",
    rotulo: "Auxílio por incapacidade temporária",
    descricao: "Restabelecimento ou concessão de auxílio-doença.",
    html: `${enderecamento("FEDERAL DO JUIZADO ESPECIAL FEDERAL DE [CIDADE]/BA")}
${qualificacao("propor")}</p>
<h1>AÇÃO DE CONCESSÃO/RESTABELECIMENTO DE AUXÍLIO POR INCAPACIDADE TEMPORÁRIA</h1>
<p>em face do <strong>INSS</strong>, pelos motivos a seguir.</p>
${h("I – DOS FATOS")}
<p>O(A) autor(a) é portador(a) de [DOENÇA/CID], que o(a) incapacita para o exercício de sua atividade habitual de [PROFISSÃO]. O benefício NB [NÚMERO] foi [indeferido / cessado] em [DATA], embora persistente a incapacidade, conforme laudos e atestados anexos.</p>
${h("II – DO DIREITO")}
<p>Estão presentes os requisitos dos arts. 59 e seguintes da Lei nº 8.213/91: qualidade de segurado, carência e incapacidade para o trabalho.</p>
${h("III – DOS PEDIDOS")}
<ol><li><p>a realização de perícia médica judicial;</p></li><li><p>a concessão da tutela de urgência para implantação imediata do benefício;</p></li><li><p>a procedência do pedido, com o pagamento das parcelas desde a data da cessação ou do requerimento.</p></li></ol>
${fecho}`,
  },
  {
    id: "bpc-loas",
    area: "previdenciario",
    rotulo: "BPC/LOAS",
    descricao: "Benefício assistencial à pessoa com deficiência ou idosa.",
    html: `${enderecamento("FEDERAL DO JUIZADO ESPECIAL FEDERAL DE [CIDADE]/BA")}
${qualificacao("propor")}</p>
<h1>AÇÃO DE CONCESSÃO DE BENEFÍCIO DE PRESTAÇÃO CONTINUADA (BPC/LOAS)</h1>
<p>em face do <strong>INSS</strong>, pelos fundamentos a seguir.</p>
${h("I – DOS FATOS")}
<p>O(A) autor(a) [é pessoa com deficiência / possui 65 anos ou mais] e vive em situação de vulnerabilidade, com renda familiar per capita inferior a 1/4 do salário mínimo. O requerimento administrativo NB [NÚMERO] foi indeferido em [DATA].</p>
${h("II – DO DIREITO")}
<p>O benefício está previsto no art. 203, V, da Constituição Federal e no art. 20 da Lei nº 8.742/93 (LOAS).</p>
${h("III – DOS PEDIDOS")}
<ol><li><p>a realização de perícia social e, se for o caso, médica;</p></li><li><p>a procedência do pedido para conceder o BPC desde a DER, com o pagamento das parcelas vencidas.</p></li></ol>
${fecho}`,
  },
];

export const modelosPorArea = (area) => MODELOS.filter((m) => m.area === area);

/** Troca {{campos}} pelos dados do processo; o que faltar vira [COLCHETES]. */
export function preencherModelo(html, dados = {}) {
  const mapa = {
    cliente: dados.cliente || "[NOME DO CLIENTE]",
    numero: dados.numero || "[NÚMERO DO PROCESSO]",
    vara: dados.vara || "[VARA]",
  };
  return html.replace(/\{\{(\w+)\}\}/g, (_, chave) => mapa[chave] ?? `[${chave.toUpperCase()}]`);
}
